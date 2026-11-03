// Self-check: run from the Vue app folder (needs @vue/compiler-sfc): node <skill>/scripts/test-analyze.mjs
import assert from 'node:assert/strict'
import { analyzeSource, loadSfc } from './analyze-vue.mjs'

const src = `<template>
  <div>
    <li v-for="(a, i) in items" :key="i">{{ a }}</li>
    <li v-for="b in items">{{ b }}</li>
    <li v-for="c in items" :key="c.id" v-if="c.ok">{{ c.id }}</li>
    <p>{{ items.filter(x => x.ok).length }}</p>
    <section class="card"><h3>t</h3><p>a</p><span>b</span><b>c</b></section>
    <section class="card"><h3>t</h3><p>a</p><span>b</span><b>c</b></section>
    <section class="card"><h3>t</h3><p>a</p><span>b</span><b>c</b></section>
  </div>
</template>
<script setup>
import axios from 'axios'
const fmt = (v) => v
</script>
<style>.card { color: red; background: white; padding: 8px; margin: 4px }</style>`

const r = analyzeSource(src, 'Fixture.vue', loadSfc())
const kinds = r.findings.map((f) => f.kind)
for (const k of [
  'v-for-index-as-key', 'v-for-without-key', 'v-for-with-v-if-same-element',
  'heavy-expression-in-template', 'repeated-markup-block', 'direct-axios-import', 'unscoped-style',
]) assert.ok(kinds.includes(k), `missing finding: ${k}`)
assert.equal(r.apiStyle, 'script-setup')
assert.deepEqual(r._functions, ['fmt'])
console.log('analyze-vue self-check passed')
