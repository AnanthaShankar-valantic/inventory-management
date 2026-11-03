# Handover: Restocking tab

## State
The Restocking feature is built. Backend tests pass (51, 11 new). `npm run build` passes.
Headless Edge screenshots confirm `/restocking` and `/orders` render.
Not done: a real browser click-through. Playwright MCP was not loaded in the last session.

## Steps for you (before restart)
1. Playwright MCP was added with `claude mcp add playwright npx @playwright/mcp@latest` (local config, this project only).
2. Start `claude` again in `inventory-management`.
3. Run `/mcp`. Check that `playwright` shows as connected. The first start can be slow (npx download).
4. Tell Claude: "Continue from HANDOVER.md".

## Steps for Claude (after restart)
1. Restart the backend (`cd server; uv run python main.py`, port 8001). This clears the old test order `RST-2026-0001` from memory. Make sure the frontend runs on port 3000 (`cd client; npm run dev`).
2. With `mcp__playwright__*` tools, open `http://localhost:3000/restocking`.
3. Move the slider. Check that the item list, total cost and remaining budget change.
4. Check that Place Order is disabled while the list is stale (right after a slider move), then enabled.
5. Click Place Order. Check the confirmation: order number, lead time, expected delivery.
6. Open `/orders`. Check the Submitted Orders section at the top shows the new row with lead time.
7. Switch the language to Japanese. Check the layout of both pages.
8. Take a screenshot at each step. Report what was checked.

## Known limits
- Orders are in memory. They reset on backend restart.
- Submitted Orders loads when the Orders page opens, not live.
- `unit_cost`, `stock_on_hand` and `lead_time_days` in `server/data/demand_forecasts.json` are invented. Replace them with real values.
- The budget fill is greedy, not optimal (`shortcut:` comment in `server/main.py`).
- `.vue` files were written by a general-purpose agent, because `vue-expert` was not available. `CLAUDE.md` requires `vue-expert`.
- Nothing is committed or pushed.

## Open decision
Move the "document non-obvious logic" rule from the project `CLAUDE.md` to the global `CLAUDE.md`? Anantha decides.

## Files changed
- `server/main.py`, `server/data/demand_forecasts.json`
- `tests/backend/test_restock.py` (new)
- `client/src/api.js`, `main.js`, `App.vue`, `locales/en.js`, `locales/ja.js`
- `client/src/views/Restocking.vue` (new), `client/src/views/Orders.vue`
- `CLAUDE.md` (Code Comments rule)
