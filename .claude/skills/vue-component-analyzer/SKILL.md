---
name: vue-component-analyzer
description: Analyze the structure of Vue 3 single-file components and suggest performance and code-reuse optimizations, with ranked findings and fixes. Use this whenever the user asks to review, audit, optimize, refactor, or "clean up" Vue components, views, or modals; asks why a Vue page is slow or re-renders too much; asks what can be shared, extracted into a component or composable, or deduplicated; or asks about v-for keys, computed vs methods, oversized components, or copy-pasted markup, styles, or helpers in a Vue codebase. Also use it for "what should I refactor in client/" even when the user does not say "analyze".
---

# Vue component analyzer

Find the few changes that make Vue components faster or smaller, and say why each one matters. A script extracts the facts. You judge them, because a fact is not a verdict: the script uses patterns and cannot tell a harmless match from a real problem.

## 1. Collect facts

Run from the Vue app folder (the one with `node_modules`, here `client/`), on the files or folders in scope:

```bash
node ../.claude/skills/vue-component-analyzer/scripts/analyze-vue.mjs src > <scratchpad>/vue-facts.json
```

It prints JSON: per component (size, API style, template depth, watcher and computed counts, `findings`) plus `crossFile` (style rules and function names repeated across files). If it says `@vue/compiler-sfc` is missing, run `npm install` in the app folder and retry. Do not read all of the JSON line by line; start with `findings`, then `crossFile`.

## 2. Verify before you claim

Open the flagged file at the flagged lines. Each finding needs a short read of the code, because:

| Finding | Check before reporting |
|---|---|
| `v-for-index-as-key` | The source must be an array. For an object, `(value, key)` is a fine key. If items have an `id` or `sku`, the key must use it. |
| `v-for-without-key` | Report it unless the list is static and never reorders. |
| `v-for-with-v-if-same-element` | In Vue 3 the `v-if` runs first and cannot see the loop item. Fix: filter in a `computed`, or move the `v-if` to a wrapper `<template>`. |
| `heavy-expression-in-template` | `.filter/.map/.sort/.reduce` in the template re-run on every render. Fix: a `computed`. Skip it if the list is tiny and fixed. |
| `template.loopCalls` / `topCalls` | A method call inside `v-for` runs once per item per render. Cheap formatters (`t()`, `formatCurrency`) are fine. Flag calls that loop or sort. |
| `repeated-markup-block` | Read the lines. If the same block repeats with only data changing, suggest a child component or a `v-for`. |
| `large-component` | Only a problem if there are separable parts (a table, a form, a chart). Name the parts to extract. |
| `direct-axios-import` | This app routes calls through `client/src/api.js`. Suggest moving the call there. |
| `unscoped-style` | Fine in `App.vue` for global styles. Elsewhere it leaks. |
| `crossFile.duplicatedStyleRules` | Real duplication. Suggest a shared stylesheet or a base component. |
| `crossFile.sameNameFunctions` | A name match is only a lead. Read the bodies. Report it only if they do the same job, and suggest a function in `utils/` or a composable. |

Also scan for what patterns cannot see: derived data kept in a `ref` and updated by hand instead of a `computed`, `watch` that should be `computed`, `deep: true` watchers on large objects, large lists rendered with no pagination, and a modal duplicated per page instead of one shared component. Follow `CLAUDE.md` where it states rules (unique keys, date validation, `computed` for derived data, design tokens).

## 3. Report

Answer first: say how many findings matter and which one gives the most benefit. Then a ranked list, at most 10, best value for effort first:

`#. file:line — what is wrong — why it matters (render cost, bytes, or change cost) — the fix — effort S/M/L — risk`

Group reuse findings that share one fix (for example, seven modals sharing one style block counts as one finding). End with one or two lines: what you did not check (for example, runtime profiling, bundle size) and which findings you are least sure about. Do not pad the list with minor items.

## 4. Apply only on request

Do not edit anything in the report step. If the user picks findings to apply:

1. Changes to `.vue` files follow the project rule in `CLAUDE.md`: delegate to the `vue-expert` agent. If that agent type is not registered in the session, run a `general-purpose` agent and tell it to follow `.claude/agents/vue-expert.md`.
2. After the edits, run `npm run build` in the app folder, re-run the script to confirm the finding is gone, and check the changed page in the browser with Playwright when the UI is affected.
3. Report what you checked.

## Limits

The script reads structure, not behaviour. It does not measure render time or bundle size. For a real slow page, suggest profiling with Vue DevTools after fixing the cheap findings.
