# AVEVA SimCentral — Base Rules

## Naming Conventions

```
Variable path:   {model_name}.{variable_name}         → Feed.T
Parameter path:  {model_name}.{parameter_name}         → Feed.FluidType
Port path:       {model_name}.{port_name}              → Feed.Out
Port with stream:{model_name}.{port_name}[{stream}]   → DistColumn.Fin[S1]
```

## Few-shot Examples

```python
# Read temperature
variable_path = "Feed.T"          # Source model, temperature variable

# Set pressure
variable_path = "Feed.P"          # Source model, pressure variable, unit kPa

# Connect two models
from_port = "Feed.Out"
to_port   = "DistColumn.Fin[S1]"  # S1 is the connector name

# Set parameter
parameter_path = "Feed.FluidType"
```

## Variable vs Parameter

| Type | Meaning | Tool | Example |
|------|---------|------|---------|
| Variable | Operating conditions, runtime values | `variable/set` | T, P, W, F |
| Parameter | Model configuration, enum options | `parameter/set` | FluidType, CompBasis |

## Tool Usage Rules

- **Server is source of truth**: never cache or assume AVEVA state between calls.
- **Building flow**: all `add_model` / `connect_models` results are in context — read them directly.
- **Analysis flow**: on session start, call `open_simulation` → `show_models_on_flowsheet` → `show_connectors_on_flowsheet`, then fetch variables/parameters per model as needed.
- **Port discovery**: call `show_all_ports` when port names are unknown or to verify connectivity.
