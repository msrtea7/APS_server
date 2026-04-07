# Development Log

---

## 2026-04-07 — Feature_1.md Implementation (Session 1)

### Completed

**P0: Integrated `show_all_ports` into tool chain**
- Added `show_all_ports(sim_name)` to `src/aveva_tools.py`, following the same Query API pattern as `show_models_on_flowsheet` and `show_connectors_on_flowsheet`
- Ported logic from standalone `src/print_all_ports.py` (two-step query: all models → per-model ports)
- Added `POST /flowsheet/ports` route in `src/api_server.py` (reuses `SimNameArgs`)
- Commit: `3fc8c83`

**P1: Removed dead/redundant tools**
- Deleted `take_snapshot()` from `aveva_tools.py` — empty implementation (API call was commented out)
- Deleted `get_simulation_models()` from `aveva_tools.py` — duplicate of `show_models_on_flowsheet`, which returns richer data
- Removed routes `POST /model/list` and `POST /snapshot/take` from `api_server.py`

**P1: Created `client/` skill folder**
- `client/skills/aveva_base.md` — naming conventions, variable vs parameter rules, session init sequence
- `client/skills/aveva_distillation.md` — model types, port schemas, typical variables, verified connection patterns, build sequence

**Tests**
- Created `tests/test_api_routes.py` — 7 tests, all passing
  - `TestShowAllPorts`: response shape, None sim_name passthrough, tool failure propagation
  - `TestRemovedRoutes`: confirms `/model/list` and `/snapshot/take` return 404
  - `TestExistingFlowsheetRoutes`: confirms `/flowsheet/models` and `/flowsheet/connectors` still work

### Decisions

- `SIMULATION_TEMPLATES` and `AGENT_PROMPTS` were already absent from `config.py` — no action needed
- `src/print_all_ports.py` kept as-is (useful standalone diagnostic tool)
- Tests mock `aveva_tools` entirely so they run without AVEVA SimCentral installed

### Remaining (from Feature_1.md priority list)

- P2: `client/skills/aveva_heat_exchange.md`
- P2: `client/skills/aveva_reaction.md`
