#!/usr/bin/env node
// Extracts structural FACTS from Vue SFCs (not verdicts). Claude judges them; see SKILL.md.
// Usage: node analyze-vue.mjs [file-or-dir ...]   (default: current directory)
// shortcut: regex for script/style facts, no JS AST. Upgrade to compileScript if props/emits analysis is needed.
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'

const require = createRequire(import.meta.url)

export function loadSfc(extraPaths = []) {
  // The skill folder has no node_modules, so resolve the compiler from the app being analyzed.
  const paths = [...extraPaths, process.cwd(), path.join(process.cwd(), 'client')]
  try {
    return require(require.resolve('@vue/compiler-sfc', { paths }))
  } catch {
    throw new Error('Cannot find @vue/compiler-sfc. Run `npm install` in the Vue app (client/) first.')
  }
}

const HEAVY = /\.(filter|map|reduce|sort|find|slice|flatMap)\s*\(/
const CALL = /([A-Za-z_$][\w$]*)\s*\(/g
const lineCount = (b) => (b ? b.content.trim().split('\n').length : 0)

function staticClass(node) {
  const p = node.props.find((x) => x.type === 6 && x.name === 'class')
  return p?.value ? p.value.content.split(/\s+/).sort().join('.') : ''
}

// Structural signature of a subtree, used to spot copy-pasted markup inside one file.
function signature(node) {
  if (node.type !== 1) return { sig: 'T', size: 0 }
  let size = 1
  const kids = (node.children || []).map((c) => {
    const k = signature(c)
    size += k.size
    return k.sig
  })
  return { sig: `${node.tag}.${staticClass(node)}(${kids.join(',')})`, size }
}

export function analyzeSource(src, file, sfc) {
  const { descriptor } = sfc.parse(src, { filename: file })
  const script = descriptor.scriptSetup || descriptor.script
  const found = new Map() // kind -> { count, lines, sample }
  const add = (kind, line, sample) => {
    const f = found.get(kind) || { count: 0, lines: [], sample }
    f.count++
    if (f.lines.length < 8) f.lines.push(line)
    found.set(kind, f)
  }

  const calls = {}
  let loopCalls = 0
  let elements = 0
  let maxDepth = 0
  const sigs = new Map()

  const checkExpr = (code, line, inFor) => {
    if (HEAVY.test(code)) add('heavy-expression-in-template', line, code.slice(0, 80))
    for (const m of code.matchAll(CALL)) {
      calls[m[1]] = (calls[m[1]] || 0) + 1
      if (inFor) loopCalls++
    }
  }

  const walk = (node, depth, inFor) => {
    if (node.type === 5 && node.content?.content) checkExpr(node.content.content, node.loc.start.line, inFor)
    // The template AST starts at a ROOT node (type 0); skipping it would scan nothing.
    if (node.type === 0) return node.children.forEach((c) => walk(c, depth, inFor))
    if (node.type !== 1) return
    elements++
    maxDepth = Math.max(maxDepth, depth)
    const dirs = node.props.filter((p) => p.type === 7)
    const forDir = dirs.find((d) => d.name === 'for')
    const ifDir = dirs.find((d) => d.name === 'if')
    const key = dirs.find((d) => d.name === 'bind' && d.arg?.content === 'key')
    if (forDir && node.tag !== 'template') {
      const line = node.loc.start.line
      // 2nd alias: the index for arrays (a key name for objects, where it is a fine :key; Claude must check).
      const alias = forDir.forParseResult?.key?.content
      if (!key) add('v-for-without-key', line, node.tag)
      else if (alias && key.exp?.content.trim() === alias) add('v-for-index-as-key', line, key.exp.content)
    }
    if (forDir && ifDir) add('v-for-with-v-if-same-element', node.loc.start.line, node.tag)
    for (const d of dirs) {
      // Event handlers run on events, not on every render, so their calls are not render cost.
      if (d.exp?.content && d.name !== 'on') checkExpr(d.exp.content, d.loc.start.line, inFor || !!forDir)
    }
    const { sig, size } = signature(node)
    if (size >= 5) {
      const s = sigs.get(sig) || { count: 0, size, tag: node.tag, lines: [] }
      s.count++
      s.lines.push(node.loc.start.line)
      sigs.set(sig, s)
    }
    for (const c of node.children || []) walk(c, depth + 1, inFor || !!forDir)
  }
  if (descriptor.template?.ast) walk(descriptor.template.ast, 0, false)

  const code = script?.content || ''
  const count = (re) => (code.match(re) || []).length
  if (/from\s+['"]axios['"]/.test(code)) add('direct-axios-import', 1, 'use the shared api.js instead')
  if (descriptor.styles.some((s) => !s.scoped)) add('unscoped-style', 1, 'style block without scoped')

  const rules = []
  for (const s of descriptor.styles) {
    const css = s.content.replace(/\/\*[\s\S]*?\*\//g, '')
    for (const m of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
      const decl = m[2].split(';').map((d) => d.trim()).filter(Boolean).join(';')
      if (decl.length >= 30) rules.push(`${m[1].replace(/\s+/g, ' ').trim()}{${decl}}`)
    }
  }
  const functions = [
    ...code.matchAll(/(?:function\s+([A-Za-z_$][\w$]*)|const\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>)/g),
  ].map((m) => m[1] || m[2])

  const tplLines = lineCount(descriptor.template)
  const scriptLines = lineCount(script)
  if (tplLines + scriptLines > 400) add('large-component', 1, `${tplLines} template + ${scriptLines} script lines`)
  const repeated = [...sigs.values()].filter((s) => s.count >= 3).sort((a, b) => b.size * b.count - a.size * a.count).slice(0, 3)
  for (const r of repeated) add('repeated-markup-block', r.lines[0], `<${r.tag}> subtree (${r.size} elements) x${r.count} at lines ${r.lines.join(',')}`)

  return {
    file,
    apiStyle: descriptor.scriptSetup ? 'script-setup' : /\bsetup\s*\(/.test(code) ? 'options+setup()' : 'options',
    lines: { template: tplLines, script: scriptLines, style: descriptor.styles.reduce((n, s) => n + lineCount(s), 0) },
    template: { elements, maxDepth, loopCalls, topCalls: Object.entries(calls).sort((a, b) => b[1] - a[1]).slice(0, 5) },
    script: { computed: count(/\bcomputed\s*\(/g), watchers: count(/\bwatch(?:Effect)?\s*\(/g), deepWatchers: count(/deep:\s*true/g), apiCalls: count(/\bapi\.\w+\(/g) },
    findings: [...found].map(([kind, f]) => ({ kind, ...f })),
    _rules: rules,
    _functions: functions,
  }
}

function collect(target, out) {
  const stat = fs.statSync(target)
  if (stat.isFile()) return target.endsWith('.vue') && out.push(target)
  for (const e of fs.readdirSync(target, { withFileTypes: true })) {
    if (['node_modules', 'dist', '.git'].includes(e.name)) continue
    collect(path.join(target, e.name), out)
  }
}

export function analyzeAll(targets) {
  const files = []
  targets.forEach((t) => collect(path.resolve(t), files))
  const sfc = loadSfc(targets.map((t) => path.resolve(t)))
  const comps = files.map((f) => analyzeSource(fs.readFileSync(f, 'utf8'), path.relative(process.cwd(), f), sfc))

  const group = (pick) => {
    const m = new Map()
    for (const c of comps) for (const k of new Set(c[pick])) m.set(k, [...(m.get(k) || []), c.file])
    return m
  }
  const dupStyles = [...group('_rules')].filter(([, f]) => f.length >= 3).sort((a, b) => b[1].length - a[1].length).slice(0, 15)
  // Same name is only a lead: the bodies may differ, so Claude must diff them before calling it duplication.
  const dupFunctions = [...group('_functions')].filter(([, f]) => f.length >= 2).sort((a, b) => b[1].length - a[1].length).slice(0, 20)
  for (const c of comps) { delete c._rules; delete c._functions }
  comps.sort((a, b) => b.findings.length - a.findings.length || b.lines.template + b.lines.script - (a.lines.template + a.lines.script))

  return {
    summary: { files: comps.length, withFindings: comps.filter((c) => c.findings.length).length },
    components: comps,
    crossFile: {
      duplicatedStyleRules: dupStyles.map(([rule, files]) => ({ rule: rule.slice(0, 120), files })),
      sameNameFunctions: dupFunctions.map(([name, files]) => ({ name, files })),
    },
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    console.log(JSON.stringify(analyzeAll(process.argv.length > 2 ? process.argv.slice(2) : ['.']), null, 2))
  } catch (e) {
    console.error(e.message)
    process.exit(1)
  }
}
