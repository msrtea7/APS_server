"""Pydantic input schemas for the AVEVA SimCentral REST API."""

from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field
from src.config import DEFAULT_TIMEOUT


# ---------------------------------------------------------------------------
# Shared / reusable bases
# ---------------------------------------------------------------------------


class SimNameArgs(BaseModel):
    """Any request that only needs an optional sim_name."""

    sim_name: Optional[str] = Field(
        None, description="Target simulation (defaults to current)"
    )


class SimNameTimeoutArgs(BaseModel):
    sim_name: Optional[str] = Field(
        None, description="Target simulation (defaults to current)"
    )
    timeout: Optional[int] = Field(None, description="Timeout in milliseconds")


class ModelNameArgs(BaseModel):
    """Requests that target a specific model inside a simulation."""

    sim_name: Optional[str] = Field(
        None, description="Target simulation (defaults to current)"
    )
    model_name: str = Field(..., description="Name of the model")


# ---------------------------------------------------------------------------
# Simulation management
# ---------------------------------------------------------------------------


class CreateSimulationArgs(BaseModel):
    sim_name: str = Field(..., description="Name for the new simulation")
    owner: Optional[str] = Field(
        None, description="Owner (defaults to current OS user)"
    )


class OpenSimulationArgs(BaseModel):
    sim_name: str = Field(..., description="Name of the existing simulation to open")


class SaveSimulationArgs(SimNameTimeoutArgs):
    pass


class CloseSimulationArgs(SimNameArgs):
    pass


class DeleteSimulationArgs(BaseModel):
    sim_name: str = Field(..., description="Name of simulation to delete permanently")
    timeout: Optional[int] = Field(None, description="Timeout in milliseconds")


class RenameSimulationArgs(BaseModel):
    old_name: str = Field(..., description="Current simulation name")
    new_name: str = Field(..., description="New simulation name")
    timeout: Optional[int] = Field(None, description="Timeout in milliseconds")


# ---------------------------------------------------------------------------
# Model management
# ---------------------------------------------------------------------------


class AddModelArgs(BaseModel):
    model_type: str = Field(
        ..., description="Model type e.g. 'Source', 'Sink', or full Lib: path"
    )
    x: float = Field(100, description="X coordinate on flowsheet")
    y: float = Field(100, description="Y coordinate on flowsheet")
    sim_name: Optional[str] = Field(
        None, description="Target simulation (defaults to current)"
    )
    model_name: Optional[str] = Field(
        None, description="Custom name; model is renamed after creation"
    )


class RemoveModelArgs(BaseModel):
    model_name: str = Field(..., description="Name of the model to remove")
    sim_name: Optional[str] = Field(
        None, description="Target simulation (defaults to current)"
    )
    timeout: Optional[int] = Field(None, description="Timeout in milliseconds")


class RenameModelArgs(BaseModel):
    old_model_name: str = Field(..., description="Current model name")
    new_model_name: str = Field(..., description="New model name")
    sim_name: Optional[str] = Field(
        None, description="Target simulation (defaults to current)"
    )
    timeout: Optional[int] = Field(None, description="Timeout in milliseconds")


class RemoveMultipleModelsArgs(BaseModel):
    model_names: List[str] = Field(..., description="List of model names to remove")
    sim_name: Optional[str] = Field(
        None, description="Target simulation (defaults to current)"
    )
    timeout: Optional[int] = Field(None, description="Timeout in milliseconds")


# ---------------------------------------------------------------------------
# Connector management
# ---------------------------------------------------------------------------


class ConnectModelsArgs(BaseModel):
    from_port: str = Field(..., description="Source port e.g. 'SRC1.Out'")
    to_port: str = Field(..., description="Destination port e.g. 'SNK1.In'")
    sim_name: Optional[str] = Field(
        None, description="Target simulation (defaults to current)"
    )


class RemoveConnectorArgs(BaseModel):
    connector_name: str = Field(..., description="Name of the connector to remove")
    sim_name: Optional[str] = Field(
        None, description="Target simulation (defaults to current)"
    )
    timeout: Optional[int] = Field(None, description="Timeout in milliseconds")


class RemoveMultipleConnectorsArgs(BaseModel):
    connector_names: List[str] = Field(
        ..., description="List of connector names to remove"
    )
    sim_name: Optional[str] = Field(
        None, description="Target simulation (defaults to current)"
    )
    timeout: Optional[int] = Field(None, description="Timeout in milliseconds")


# ---------------------------------------------------------------------------
# Variable access
# ---------------------------------------------------------------------------


class GetVariableArgs(BaseModel):
    variable_path: str = Field(..., description="Full path e.g. 'Tank1.Temperature'")
    sim_name: Optional[str] = Field(
        None, description="Target simulation (defaults to current)"
    )


class SetVariableArgs(BaseModel):
    variable_path: str = Field(..., description="Full path e.g. 'Tank1.Temperature'")
    value: float = Field(..., description="New numerical value")
    unit: Optional[str] = Field(None, description="Unit e.g. 'K', 'bar', 'kg/h'")
    sim_name: Optional[str] = Field(
        None, description="Target simulation (defaults to current)"
    )


class GetMultipleVariablesArgs(BaseModel):
    variables: List[str] = Field(..., description="List of variable paths to retrieve")
    sim_name: Optional[str] = Field(
        None, description="Target simulation (defaults to current)"
    )


class VariableData(BaseModel):
    path: str = Field(..., description="Variable path")
    value: float = Field(..., description="Variable value")
    unit: Optional[str] = Field(None, description="Unit of measurement")


class SetMultipleVariablesArgs(BaseModel):
    variable_data: List[VariableData] = Field(..., description="Variables to set")
    sim_name: Optional[str] = Field(
        None, description="Target simulation (defaults to current)"
    )


# ---------------------------------------------------------------------------
# Parameter management
# ---------------------------------------------------------------------------


class UpdateParameterArgs(BaseModel):
    parameter_path: str = Field(..., description="Full path to the parameter")
    value: str = Field(..., description="New value (as string)")
    sim_name: Optional[str] = Field(
        None, description="Target simulation (defaults to current)"
    )
    timeout: int = Field(DEFAULT_TIMEOUT, description="Timeout in milliseconds")


class UpdateParametersArgs(BaseModel):
    parameter_data: List[Dict[str, Any]] = Field(
        ..., description="List of dicts with 'path' and 'value' keys"
    )
    sim_name: Optional[str] = Field(
        None, description="Target simulation (defaults to current)"
    )
    timeout: int = Field(DEFAULT_TIMEOUT, description="Timeout in milliseconds")


# ---------------------------------------------------------------------------
# Fluid management
# ---------------------------------------------------------------------------


class CreateFluidArgs(BaseModel):
    library_name: str = Field(
        ..., description="Library name (typically same as simulation name)"
    )
    fluid_name: str = Field(..., description="Name for the fluid package")
    components: List[str] = Field(
        ..., description="Component names e.g. ['Water', 'Methanol']"
    )
    thermo_method: str = Field(
        "Non-Random Two-Liquid (NRTL)", description="Thermodynamic method"
    )
    phases: str = Field("Vapor/Liquid (VLE)", description="Phase configuration")
    databank: str = Field("System:SIMSCI", description="Component databank")
    timeout: int = Field(DEFAULT_TIMEOUT, description="Timeout in milliseconds")


class SetFluidOfSourceArgs(BaseModel):
    fluid_name: str = Field(..., description="Name of the fluid package to assign")
    source_name: str = Field(..., description="Name of the source model")
    sim_name: Optional[str] = Field(
        None, description="Target simulation (defaults to current)"
    )
    timeout: int = Field(DEFAULT_TIMEOUT, description="Timeout in milliseconds")


# ---------------------------------------------------------------------------
# Snapshot management
# ---------------------------------------------------------------------------


class TakeSnapshotArgs(BaseModel):
    snapshot_name: str = Field(..., description="Name for the snapshot")
    sim_name: Optional[str] = Field(
        None, description="Target simulation (defaults to current)"
    )
