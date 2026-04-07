# AVEVA SimCentral — Distillation Skill

## Available Model Types

| Name | AVEVA Path | Purpose |
|------|-----------|---------|
| Source | Lib:Process.Source | Feed boundary |
| Sink | Lib:Process.Sink | Product boundary |
| Column | Lib:Process.Column | Distillation column |
| Drum | Lib:Process.Drum | Flash drum / separator |
| HeatExchanger | Lib:Process.HX | Heat exchanger |

## Column Port Schema

| Port | Direction | Format | Note |
|------|-----------|--------|------|
| Fin | in | Column.Fin[{stream_name}] | Feed inlet, supports multiple feeds |
| Vout | out | Column.Vout | Overhead vapor outlet |
| Lout | out | Column.Lout | Bottoms liquid outlet |

## Source Port Schema

| Port | Direction | Format |
|------|-----------|--------|
| Out | out | Source.Out |

## Sink Port Schema

| Port | Direction | Format |
|------|-----------|--------|
| In | in | Sink.In |

## Typical Variables

| Variable | Unit | Description |
|----------|------|-------------|
| T | K | Temperature |
| P | kPa | Pressure |
| W | kg/s | Mass flow rate |
| F | kmol/s | Molar flow rate |
| z[component] | mole fraction | Molar composition |
| M[component] | - | Unnormalized molar feed amount |
| Mt | - | Normalization basis, set to 1 |

## Verified Connection Patterns

```python
# Feed into column
connect_models("Feed.Out", "DistColumn.Fin[S1]")

# Column bottoms to sink
connect_models("DistColumn.Lout", "Bottoms.In")

# Column overhead vapor to sink
connect_models("DistColumn.Vout", "Distillate.In")
```

## Typical Build Sequence

```python
# 1. Create fluid
create_fluid_complete(library_name, fluid_name, components, thermo_method, phases, databank)

# 2. Add models
add_model("Source", x=100, y=200, sim_name=sim, model_name="Feed")
add_model("Column", x=300, y=200, sim_name=sim, model_name="DistColumn")
add_model("Sink",   x=500, y=100, sim_name=sim, model_name="Distillate")
add_model("Sink",   x=500, y=300, sim_name=sim, model_name="Bottoms")

# 3. Assign fluid to source
set_fluid_of_source(fluid_name, "Feed", sim_name=sim)

# 4. Connect
connect_models("Feed.Out", "DistColumn.Fin[S1]", sim_name=sim)
connect_models("DistColumn.Vout", "Distillate.In", sim_name=sim)
connect_models("DistColumn.Lout", "Bottoms.In", sim_name=sim)

# 5. Set operating conditions on Feed
set_variable_value("Feed.T", value, unit="K", sim_name=sim)
set_variable_value("Feed.P", value, unit="kPa", sim_name=sim)
set_variable_value("Feed.W", value, unit="kg/s", sim_name=sim)
```
