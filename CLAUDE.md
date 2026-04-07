# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Windows-only FastAPI REST server that wraps the AVEVA SimCentral .NET API. It is called remotely by an AI agent to programmatically build and control process simulations (flowsheets, models, connectors, variables, parameters, fluids, snapshots).

The server bridges Python and .NET via `pythonnet` (`clr`) and the `simcentralconnect` package. Both must be installed and available on the Windows host running AVEVA SimCentral.

## Running the server

```bash
python main.py
```

Listens on `0.0.0.0:8000` by default (see `src/config.py`).

The server connects to AVEVA SimCentral on startup (`startup_connect`). AVEVA SimCentral must already be running on the same machine.

## Key files

| File | Purpose |
|------|---------|
| `main.py` | Entry point — starts uvicorn |
| `src/api_server.py` | All FastAPI route definitions |
| `src/aveva_tools.py` | All business logic; wraps AVEVA .NET managers |
| `src/schemas.py` | Pydantic v2 request bodies for every endpoint |
| `src/config.py` | Host, port, timeout, and `AVEVA_MODEL_TYPES` mapping |
| `print_all_ports.py` | Standalone diagnostic script to dump port info for a simulation |

## Architecture

```
AI agent (remote)
      │  HTTP POST/GET
      ▼
FastAPI routes  (src/api_server.py)
      │  plain function calls
      ▼
aveva_tools.py  — thin Python wrappers around .NET managers
      │  pythonnet / clr
      ▼
AVEVA SimCentral .NET API  (simcentralconnect + IXxxManager services)
```

`aveva_tools.py` holds a single module-level `AVEVAConnection` instance. All route handlers call free functions in that module which delegate to the connection object.

### Manager services

Obtained once at connect time via `sc.GetService(...)`:

| Key | .NET interface |
|-----|---------------|
| `simulation` | `ISimulationManager` |
| `model` | `IModelManager` |
| `connector` | `IConnectorManager` |
| `diagram` | `IDiagramManager` |
| `variable` | `IVariableManager` |
| `parameter` | `IParameterManager` |
| `library` | `ILibraryManager` |
| `flowsheet` | `IFlowsheetManager` |
| `helpers` | `IHelpersManager` |
| `copy_paste` | `ICopyPasteManager` |
| `snapshot` | `ISnapshotManager` |

### Model types

Short names (e.g. `"Source"`, `"Column"`) are resolved to full library paths (e.g. `"Lib:Process.Column"`) using `AVEVA_MODEL_TYPES` in `src/config.py`. When adding a model, a full `Lib:` path can also be passed directly.

### Port naming convention

Ports are referenced as `"<ModelName>.<PortName>"` (e.g. `"SRC1.Out"`, `"COL1.Fin[S1]"`). Use `print_all_ports.py` to discover actual port names for any simulation.

### .NET interop patterns

- All AVEVA API calls return awaitables; results are obtained via `.Result`.
- Python dicts must be converted to `Dictionary[String, Object]` before passing to Query APIs (see `convert()` in `print_all_ports.py`).
- Arrays use `System.Array[String]` / `System.Array[Object]`.

## API surface (endpoint groups)

- `/connect`, `/status`, `/simulations` — connection & session
- `/simulation/{create,open,save,close,delete,rename,status}` — simulation lifecycle
- `/model/{add,remove,remove-many,rename,list,params,vars}` — model management
- `/flowsheet/{models,connectors}` — flowsheet queries
- `/connector/{connect,remove,remove-many,list}` — connector management
- `/variable/{get,set,get-many,set-many}` — variable read/write
- `/parameter/{set,set-many}` — parameter updates
- `/fluid/{create,assign}` — fluid package management
- `/snapshot/{create,list,take}` — snapshot management

All responses follow `{"success": bool, ...}` or raise a 500 with `{"success": false, "error": "..."}` via the global exception handler.

## Dependencies

```
fastapi
uvicorn[standard]
pydantic>=2.0.0
pythonnet   # provides clr
simcentralconnect  # AVEVA-provided Python connector
```

No test suite exists yet. Manual testing is done by hitting endpoints while AVEVA SimCentral is open.
