"""
AVEVA SimCentral REST API Server (Windows side).

Copy this entire directory to your Windows machine and run:
    python api_server.py
"""

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src import aveva_tools
from src.config import HOST, PORT
from src.schemas import (
    # Simulation
    CreateSimulationArgs,
    OpenSimulationArgs,
    SaveSimulationArgs,
    CloseSimulationArgs,
    DeleteSimulationArgs,
    RenameSimulationArgs,
    # Models
    AddModelArgs,
    RemoveModelArgs,
    RenameModelArgs,
    RemoveMultipleModelsArgs,
    # Connectors
    ConnectModelsArgs,
    RemoveConnectorArgs,
    RemoveMultipleConnectorsArgs,
    # Variables
    GetVariableArgs,
    SetVariableArgs,
    GetMultipleVariablesArgs,
    SetMultipleVariablesArgs,
    # Parameters
    UpdateParameterArgs,
    UpdateParametersArgs,
    # Fluids
    CreateFluidArgs,
    SetFluidOfSourceArgs,
    # Shared
    SimNameArgs,
    SimNameTimeoutArgs,
    ModelNameArgs,
)

app = FastAPI(title="AVEVA SimCentral REST API")


@app.exception_handler(Exception)
async def _general_exception_handler(request, exc):
    return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})


@app.on_event("startup")
def startup_connect():
    aveva_tools.connect_to_aveva()


# ── Connection & session ──────────────────────────────────────────────────


@app.post("/connect")
def connect():
    return aveva_tools.connect_to_aveva()


@app.get("/status")
def status():
    return aveva_tools.get_connection_status()


@app.get("/simulations")
def simulations():
    return aveva_tools.get_available_simulations()


# ── Simulation management ─────────────────────────────────────────────────


@app.post("/simulation/create")
def create_simulation(req: CreateSimulationArgs):
    return aveva_tools.create_simulation(req.sim_name, req.owner)


@app.post("/simulation/open")
def open_simulation(req: OpenSimulationArgs):
    return aveva_tools.open_simulation(req.sim_name)


@app.post("/simulation/save")
def save_simulation(req: SaveSimulationArgs):
    return aveva_tools.save_simulation(req.sim_name, req.timeout)


@app.post("/simulation/close")
def close_simulation(req: CloseSimulationArgs):
    return aveva_tools.close_simulation(req.sim_name)


@app.post("/simulation/delete")
def delete_simulation(req: DeleteSimulationArgs):
    return aveva_tools.delete_simulation(req.sim_name, req.timeout)


@app.post("/simulation/rename")
def rename_simulation(req: RenameSimulationArgs):
    return aveva_tools.rename_simulation(req.old_name, req.new_name, req.timeout)


@app.post("/simulation/status")
def simulation_status(req: SimNameArgs):
    return aveva_tools.get_simulation_status(req.sim_name)


# ── Model management ──────────────────────────────────────────────────────


@app.post("/model/add")
def add_model(req: AddModelArgs):
    return aveva_tools.add_model(
        req.model_type, req.x, req.y, req.sim_name, req.model_name
    )


@app.post("/model/remove")
def remove_model(req: RemoveModelArgs):
    return aveva_tools.remove_model(req.model_name, req.sim_name, req.timeout)


@app.post("/model/remove-many")
def remove_multiple_models(req: RemoveMultipleModelsArgs):
    return aveva_tools.remove_multiple_models(
        req.model_names, req.sim_name, req.timeout
    )


@app.post("/model/rename")
def rename_model(req: RenameModelArgs):
    return aveva_tools.rename_model(
        req.old_model_name, req.new_model_name, req.sim_name, req.timeout
    )


@app.post("/model/params")
def show_one_model_param(req: ModelNameArgs):
    return aveva_tools.show_one_model_param(req.sim_name, req.model_name)


@app.post("/model/vars")
def show_one_model_var(req: ModelNameArgs):
    return aveva_tools.show_one_model_var(req.sim_name, req.model_name)


# ── Flowsheet queries ─────────────────────────────────────────────────────


@app.post("/flowsheet/models")
def show_models_on_flowsheet(req: SimNameArgs):
    return aveva_tools.show_models_on_flowsheet(req.sim_name)


@app.post("/flowsheet/connectors")
def show_connectors_on_flowsheet(req: SimNameArgs):
    return aveva_tools.show_connectors_on_flowsheet(req.sim_name)


@app.post("/flowsheet/ports")
def show_all_ports(req: SimNameArgs):
    return aveva_tools.show_all_ports(req.sim_name)


# ── Connector management ──────────────────────────────────────────────────


@app.post("/connector/connect")
def connect_models(req: ConnectModelsArgs):
    return aveva_tools.connect_models(req.from_port, req.to_port, req.sim_name)


@app.post("/connector/remove")
def remove_connector(req: RemoveConnectorArgs):
    return aveva_tools.remove_connector(req.connector_name, req.sim_name, req.timeout)


@app.post("/connector/remove-many")
def remove_multiple_connectors(req: RemoveMultipleConnectorsArgs):
    return aveva_tools.remove_multiple_connectors(
        req.connector_names, req.sim_name, req.timeout
    )


@app.post("/connector/list")
def get_connector_list(req: SimNameArgs):
    return aveva_tools.get_connector_list(req.sim_name)


# ── Variable access ───────────────────────────────────────────────────────


@app.post("/variable/get")
def get_variable(req: GetVariableArgs):
    return aveva_tools.get_variable_value(req.variable_path, req.sim_name)


@app.post("/variable/set")
def set_variable(req: SetVariableArgs):
    return aveva_tools.set_variable_value(
        req.variable_path, req.value, req.unit, req.sim_name
    )


@app.post("/variable/get-many")
def get_multiple_variables(req: GetMultipleVariablesArgs):
    return aveva_tools.get_multiple_variables(req.variables, req.sim_name)


@app.post("/variable/set-many")
def set_multiple_variables(req: SetMultipleVariablesArgs):
    return aveva_tools.set_multiple_variables(
        [v.model_dump() for v in req.variable_data], req.sim_name
    )


# ── Parameter management ──────────────────────────────────────────────────


@app.post("/parameter/set")
def update_parameter(req: UpdateParameterArgs):
    return aveva_tools.update_parameter(
        req.parameter_path, req.value, req.sim_name, req.timeout
    )


@app.post("/parameter/set-many")
def update_parameters(req: UpdateParametersArgs):
    return aveva_tools.update_parameters(req.parameter_data, req.sim_name, req.timeout)


# ── Fluid management ──────────────────────────────────────────────────────


@app.post("/fluid/create")
def create_fluid(req: CreateFluidArgs):
    return aveva_tools.create_fluid_complete(
        req.library_name,
        req.fluid_name,
        req.components,
        req.thermo_method,
        req.phases,
        req.databank,
        req.timeout,
    )


@app.post("/fluid/assign")
def set_fluid_of_source(req: SetFluidOfSourceArgs):
    return aveva_tools.set_fluid_of_source(
        req.fluid_name, req.source_name, req.sim_name, req.timeout
    )


# ── Snapshot management ───────────────────────────────────────────────────


@app.post("/snapshot/create")
def create_snapshot(req: SimNameTimeoutArgs):
    return aveva_tools.create_snapshot(req.sim_name, req.timeout)


@app.post("/snapshot/list")
def get_all_snapshots(req: SimNameArgs):
    return aveva_tools.get_all_snapshots(req.sim_name)


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
