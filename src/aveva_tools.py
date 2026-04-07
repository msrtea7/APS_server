#!/usr/bin/env python3
"""
AVEVA SimCentral Tools for Multi-Agent System
Core functions for interacting with AVEVA Process Simulation
"""

import simcentralconnect
import clr

clr.AddReference("System")
import System
import time
import os
import json
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging
from src.config import AVEVA_MODEL_TYPES

# Import required .NET types
import System
from System import Array, String, Object

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AVEVAConnection:
    """Manages connection to AVEVA SimCentral"""

    def __init__(self):
        self.sc = None
        self.managers = {}
        self.current_simulation = None

    def connect(self) -> bool:
        """Establish connection to AVEVA SimCentral"""
        try:
            self.sc = simcentralconnect.connect().Result

            # Initialize all managers
            self.managers = {
                "simulation": self.sc.GetService("ISimulationManager"),
                "model": self.sc.GetService("IModelManager"),
                "connector": self.sc.GetService("IConnectorManager"),
                "diagram": self.sc.GetService("IDiagramManager"),
                "variable": self.sc.GetService("IVariableManager"),
                "parameter": self.sc.GetService("IParameterManager"),
                "library": self.sc.GetService("ILibraryManager"),
                "flowsheet": self.sc.GetService("IFlowsheetManager"),
                "helpers": self.sc.GetService("IHelpersManager"),
                "copy_paste": self.sc.GetService("ICopyPasteManager"),
                "snapshot": self.sc.GetService("ISnapshotManager"),
            }

            # Set API options
            options = {
                "Timeout": 40000,
                "EnableApiLogging": "true",
                "WaitForNoSimulationActivity": "true",
            }
            self.sc.SetOptions(repr(options))

            logger.info("✅ Successfully connected to AVEVA SimCentral")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to connect to AVEVA: {e}")
            return False

    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status and open simulations"""
        try:
            if not self.sc:
                return {"connected": False, "error": "No connection established"}

            sim_mgr = self.managers["simulation"]
            open_sims = sim_mgr.GetOpenSimulations().Result

            # Safely convert simulation names to strings
            sim_names = []
            if open_sims:
                logger.info(f"Found {len(open_sims)} open simulations")
                for i, sim in enumerate(open_sims):
                    try:
                        if hasattr(sim, "ToString"):
                            sim_names.append(sim.ToString())
                            logger.debug(f"Simulation {i}: Used ToString() method")
                        elif isinstance(sim, str):
                            sim_names.append(sim)
                            logger.debug(f"Simulation {i}: Already a string")
                        else:
                            sim_names.append(str(sim))
                            logger.debug(
                                f"Simulation {i}: Converted to string, type was {type(sim)}"
                            )
                    except Exception as sim_error:
                        logger.warning(f"Error processing simulation {i}: {sim_error}")
                        sim_names.append(f"Unknown_Simulation_{i}")
            else:
                logger.info("No open simulations found")

            return {
                "connected": True,
                "open_simulations": len(open_sims) if open_sims else 0,
                "simulation_names": sim_names,
                "current_simulation": self.current_simulation,
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}

    def _safe_float(self, value) -> float:
        """Safely convert value to float, handling .NET types"""
        try:
            if value is None:
                return 0.0
            if hasattr(value, "Value"):  # JValue object
                return float(value.Value)
            if hasattr(value, "ToString"):
                return float(value.ToString())
            return float(value)
        except (ValueError, TypeError, AttributeError):
            return 0.0


# Global connection instance
aveva_conn = AVEVAConnection()


def get_aveva_model_type(model_type: str) -> str:
    """Map common model names to full AVEVA library paths"""
    # First check if it's already a full path
    if "Lib:" in model_type:
        return model_type

    # Create a flat mapping of all model types
    type_mapping = {}
    for category, models in AVEVA_MODEL_TYPES.items():
        type_mapping.update(models)

    # Return the full path if found, otherwise return the original
    return type_mapping.get(model_type, model_type)


def connect_to_aveva() -> Dict[str, Any]:
    """Tool: Connect to AVEVA SimCentral"""
    success = aveva_conn.connect()
    return aveva_conn.get_connection_status()


def get_connection_status() -> Dict[str, Any]:
    """Tool: Get current connection status"""
    return aveva_conn.get_connection_status()


def get_available_simulations() -> Dict[str, Any]:
    """Tool: Get list of all available simulations in AVEVA SimCentral"""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_mgr = aveva_conn.managers["simulation"]

        # Get all available simulations
        all_sims = sim_mgr.GetAvailableSimulations().Result

        # Process simulation list
        simulation_list = []
        if all_sims:
            logger.info(f"Found {len(all_sims)} available simulations")
            for i, sim in enumerate(all_sims):
                try:
                    # Safely extract simulation name
                    if hasattr(sim, "ToString"):
                        sim_name = sim.ToString()
                    elif isinstance(sim, str):
                        sim_name = sim
                    else:
                        sim_name = str(sim)

                    simulation_list.append(sim_name)
                    logger.debug(f"Available simulation {i}: {sim_name}")

                except Exception as sim_error:
                    logger.warning(f"Error processing simulation {i}: {sim_error}")
                    simulation_list.append(f"Unknown_Simulation_{i}")
        else:
            logger.info("No available simulations found")

        # Get currently open simulations for comparison
        open_sims = sim_mgr.GetOpenSimulations().Result
        open_sim_names = []
        if open_sims:
            for sim in open_sims:
                try:
                    if hasattr(sim, "ToString"):
                        open_sim_names.append(sim.ToString())
                    elif isinstance(sim, str):
                        open_sim_names.append(sim)
                    else:
                        open_sim_names.append(str(sim))
                except:
                    pass

        return {
            "success": True,
            "total_simulations": len(simulation_list),
            "available_simulations": simulation_list,
            "open_simulations": open_sim_names,
            "closed_simulations": [
                sim for sim in simulation_list if sim not in open_sim_names
            ],
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def create_simulation(sim_name: str, owner: str = None) -> Dict[str, Any]:
    """Tool: Create a new simulation"""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_mgr = aveva_conn.managers["simulation"]

        # Check if simulation already exists
        try:
            existing = sim_mgr.OpenSimulation(sim_name).Result
            if existing:
                sim_mgr.CloseSimulation(sim_name).Result
                logger.info(f"Closed existing simulation: {sim_name}")
        except:
            pass  # Simulation doesn't exist, which is what we want

        # Create new simulation
        if owner is None:
            owner = os.getlogin()
        template = "ProcessTemplate"
        temp_name = sim_mgr.CreateSim(owner, template).Result
        sim_mgr.RenameSim(temp_name, sim_name).Result

        aveva_conn.current_simulation = sim_name

        return {
            "success": True,
            "simulation_name": sim_name,
            "owner": owner,
            "message": f"Created simulation: {sim_name}",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def open_simulation(sim_name: str) -> Dict[str, Any]:
    """Tool: Open an existing simulation"""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_mgr = aveva_conn.managers["simulation"]
        opened = sim_mgr.OpenSimulation(sim_name).Result

        if opened:
            aveva_conn.current_simulation = sim_name
            return {"success": True, "message": f"Opened simulation: {sim_name}"}
        else:
            return {"success": False, "error": f"Failed to open simulation: {sim_name}"}

    except System.AggregateException as ex:
        if "simulation doesn't exists" in str(ex.InnerException.Message):
            return {
                "success": False,
                "error": f"Simulation '{sim_name}' does not exist",
            }
        return {"success": False, "error": str(ex)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def add_model(
    model_type: str,
    x: float = 100,
    y: float = 100,
    sim_name: str = None,
    model_name: str = None,
) -> Dict[str, Any]:
    """Tool: Add a model to the simulation

    Args:
        model_type: Type of model to add. Valid options are:
                   • Sources/Sinks: Source, Sink
                   • Heat Exchangers: HeatExchanger
                   • Separators: Drum, Column
                   • Reactors: CSTR, PFR, Equilibrium
                   • Pumps/Compressors: Pump, Compressor
        x: X position on flowsheet (default: 100)
        y: Y position on flowsheet (default: 100)
        sim_name: Target simulation (defaults to current simulation)
        model_name: Custom name for the model (optional). If provided, model will be renamed after creation.

    Returns:
        Dict with success status, model_name, model_type, position, and message

    Example:
        add_model("Source", 100, 100, "MySim")  # ✓ Valid - uses default name
        add_model("Source", 100, 100, "MySim", "FeedTank")  # ✓ Valid - custom name
        add_model("Tank", 100, 100, "MySim")    # ✗ Invalid - use "Source" or "Sink"
    """
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_name = sim_name or aveva_conn.current_simulation
        if not sim_name:
            return {"success": False, "error": "No simulation specified or open"}

        # Map common model names to full AVEVA library paths
        full_model_type = get_aveva_model_type(model_type)
        logger.info(f"Mapped model type '{model_type}' to '{full_model_type}'")

        model_mgr = aveva_conn.managers["model"]
        default_model_name = model_mgr.AddModel(
            sim_name, None, full_model_type, x, y
        ).Result

        final_model_name = default_model_name
        rename_message = ""

        # If custom name provided, rename the model
        if model_name and model_name != default_model_name:
            try:
                time.sleep(0.5)
                renamed = model_mgr.RenameModel(
                    sim_name, default_model_name, model_name
                ).Result
                if renamed:
                    final_model_name = model_name
                    rename_message = f" and renamed to '{model_name}'"
                else:
                    rename_message = (
                        f" (rename to '{model_name}' failed - keeping default name)"
                    )
            except Exception as rename_error:
                rename_message = (
                    f" (rename to '{model_name}' failed: {str(rename_error)})"
                )

        return {
            "success": True,
            "model_name": final_model_name,
            "model_type": model_type,
            "full_model_type": full_model_type,
            "position": {"x": x, "y": y},
            "default_name": default_model_name,
            "custom_name_requested": model_name,
            "renamed": final_model_name != default_model_name,
            "message": f"Added {model_type} model: {default_model_name}{rename_message}",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def connect_models(
    from_port: str, to_port: str, sim_name: str = None
) -> Dict[str, Any]:
    """Tool: Connect two model ports with robust validation"""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_name = sim_name or aveva_conn.current_simulation
        if not sim_name:
            return {"success": False, "error": "No simulation specified or open"}

        conn_mgr = aveva_conn.managers["connector"]
        var_mgr = aveva_conn.managers["variable"]

        # Get initial connector count to identify new connector
        initial_connectors = conn_mgr.GetConnectorList(sim_name).Result
        initial_count = len(initial_connectors) if initial_connectors else 0

        # Attempt to create the connection
        connector = conn_mgr.AddConnector(sim_name, None, from_port, to_port).Result

        # Get updated connector list to find the new connector
        updated_connectors = conn_mgr.GetConnectorList(sim_name).Result
        updated_count = len(updated_connectors) if updated_connectors else 0

        if updated_count <= initial_count:
            return {
                "success": False,
                "connection": f"{from_port} -> {to_port}",
                "error": "No connector was created - check if ports exist and are compatible",
            }

        # Find the new connector (should be the last one added)
        new_connector_name = None
        if updated_connectors:
            # Get the connector that wasn't in the initial list
            initial_set = (
                set(str(c) for c in initial_connectors) if initial_connectors else set()
            )
            updated_set = (
                set(str(c) for c in updated_connectors) if updated_connectors else set()
            )
            new_connectors = updated_set - initial_set

            if new_connectors:
                new_connector_name = list(new_connectors)[0]
            else:
                # Fallback: assume last connector is the new one
                new_connector_name = str(updated_connectors[-1])

        if not new_connector_name:
            return {
                "success": False,
                "connection": f"{from_port} -> {to_port}",
                "error": "Could not identify the created connector",
            }

        # Validate the connection by checking stream flow property
        try:
            flow_variable = f"{new_connector_name}.F"
            flow_result = var_mgr.GetVariableValue(sim_name, flow_variable).Result
            flow_value = str(flow_result) if flow_result is not None else None

            # Check if we have a real flow value (not None, not empty, not "None" string)
            if flow_value and flow_value.lower() != "none" and flow_value.strip() != "":
                try:
                    # Try to convert to float to ensure it's a real number
                    float_value = float(flow_value)
                    return {
                        "success": True,
                        "connection": f"{from_port} -> {to_port}",
                        "connector_name": new_connector_name,
                        "stream_flow": flow_value,
                        "message": f"Successfully connected {from_port} to {to_port} (Stream: {new_connector_name}, Flow: {flow_value})",
                    }
                except ValueError:
                    # Flow value exists but is not numeric - still might be valid
                    return {
                        "success": True,
                        "connection": f"{from_port} -> {to_port}",
                        "connector_name": new_connector_name,
                        "stream_flow": flow_value,
                        "message": f"Connected {from_port} to {to_port} (Stream: {new_connector_name}, Flow: {flow_value})",
                    }
            else:
                # Phantom connector detected - clean it up
                try:
                    conn_mgr.RemoveConnector(sim_name, new_connector_name).Result
                    cleanup_msg = (
                        f" (cleaned up phantom connector {new_connector_name})"
                    )
                except:
                    cleanup_msg = f" (phantom connector {new_connector_name} may need manual cleanup)"

                return {
                    "success": False,
                    "connection": f"{from_port} -> {to_port}",
                    "error": f"Connection created phantom connector with no flow - ports likely don't exist{cleanup_msg}",
                    "suggestion": "Check port names. Common ports: '.Out', '.In' for streams; '.Outlet', '.Inlet' may not exist",
                }

        except Exception as validation_error:
            # Could not validate - connection might still be good, but we can't verify
            return {
                "success": False,
                "connection": f"{from_port} -> {to_port}",
                "connector_name": new_connector_name,
                "error": f"Connection created but validation failed: {str(validation_error)}",
                "warning": "Connection may be valid but could not verify stream properties",
            }

    except Exception as e:
        return {
            "success": False,
            "connection": f"{from_port} -> {to_port}",
            "error": f"Connection failed: {str(e)}",
        }


def get_variable_value(variable_path: str, sim_name: str = None) -> Dict[str, Any]:
    """Tool: Get value of a simulation variable"""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_name = sim_name or aveva_conn.current_simulation
        if not sim_name:
            return {"success": False, "error": "No simulation specified or open"}

        var_mgr = aveva_conn.managers["variable"]
        value = var_mgr.GetVariableValue(sim_name, variable_path).Result

        return {
            "success": True,
            "variable": variable_path,
            "value": str(value),
            "simulation": sim_name,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def set_variable_value(
    variable_path: str, value: float, unit: str = None, sim_name: str = None
) -> Dict[str, Any]:
    """Tool: Set value of a simulation variable"""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_name = sim_name or aveva_conn.current_simulation
        if not sim_name:
            return {"success": False, "error": "No simulation specified or open"}

        var_mgr = aveva_conn.managers["variable"]
        var_mgr.SetVariableValue(sim_name, variable_path, value, unit).Result

        return {
            "success": True,
            "variable": variable_path,
            "value": value,
            "unit": unit,
            "simulation": sim_name,
            "message": f"Set {variable_path} = {value} {unit or ''}",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def get_simulation_status(sim_name: str = None) -> Dict[str, Any]:
    """Tool: Get simulation convergence status"""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_name = sim_name or aveva_conn.current_simulation
        if not sim_name:
            return {"success": False, "error": "No simulation specified or open"}

        sim_mgr = aveva_conn.managers["simulation"]
        status = sim_mgr.GetSimulationStatus(sim_name).Result

        return {
            "success": True,
            "simulation": sim_name,
            "has_required_data": status[0] if len(status) > 0 else False,
            "properly_specified": status[1] if len(status) > 1 else False,
            "solved": status[2] if len(status) > 2 else False,
            "status_summary": f"Data: {status[0]}, Specified: {status[1]}, Solved: {status[2]}"
            if len(status) >= 3
            else "Unknown",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def close_simulation(sim_name: str = None) -> Dict[str, Any]:
    """Tool: Close a simulation"""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_mgr = aveva_conn.managers["simulation"]

        if sim_name:
            sim_mgr.CloseSimulation(sim_name).Result
            if aveva_conn.current_simulation == sim_name:
                aveva_conn.current_simulation = None
        else:
            sim_mgr.CloseOpenSimulations().Result
            aveva_conn.current_simulation = None

        return {
            "success": True,
            "message": f"Closed simulation: {sim_name or 'all simulations'}",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# UTILITY FUNCTIONS FOR AVEVA API QUERIES
# =============================================================================


def convert(dict_obj):
    """Convert Python dict to .NET Dictionary[String, Object] for AVEVA API"""
    try:
        import System
        from System.Collections.Generic import Dictionary

        ndict = Dictionary[System.String, System.Object]()
        for k, v in dict_obj.items():
            ndict[k] = v
        return ndict
    except Exception as e:
        logger.error(f"Error converting dict to .NET Dictionary: {e}")
        return None


def show_models_on_flowsheet(sim_name: str = None) -> Dict[str, Any]:
    """Tool: Get detailed information about models on the flowsheet using AVEVA Query API"""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_name = sim_name or aveva_conn.current_simulation
        if not sim_name:
            return {"success": False, "error": "No simulation specified or open"}

        # Get simulation manager
        sim_mgr = aveva_conn.managers["simulation"]

        # Create resource array with simulation name
        resource = Array[String]([sim_name])

        # Define what fields we want from each model
        child_types = Array[Object](
            [
                convert(
                    {
                        "type": "model",
                        "fields": Array[String](["name", "modelType", "description"]),
                    }
                )
            ]
        )

        # Execute the query
        result = sim_mgr.Query("simulation", resource, child_types).Result

        # Process results
        models_info = []
        if hasattr(result, "model") and result.model:
            for model in result.model:
                try:
                    model_info = {
                        "name": str(model.name)
                        if hasattr(model, "name")
                        else "Unknown",
                        "model_type": str(model.modeltype)
                        if hasattr(model, "modeltype")
                        else "Unknown",
                        "description": str(model.description)
                        if hasattr(model, "description")
                        else "No description",
                    }
                    models_info.append(model_info)
                    logger.debug(
                        f"Model: {model_info['name']}, Type: {model_info['model_type']}, Description: {model_info['description']}"
                    )
                except Exception as model_error:
                    logger.warning(f"Error processing model: {model_error}")
                    models_info.append(
                        {
                            "name": "Error reading model",
                            "model_type": "Unknown",
                            "description": f"Error: {str(model_error)}",
                        }
                    )

        return {
            "success": True,
            "simulation": sim_name,
            "models": models_info,
            "count": len(models_info),
            "message": f"Found {len(models_info)} models on flowsheet in simulation '{sim_name}'",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def show_connectors_on_flowsheet(sim_name: str = None) -> Dict[str, Any]:
    """Tool: Get detailed information about connectors on the flowsheet using AVEVA Query API"""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_name = sim_name or aveva_conn.current_simulation
        if not sim_name:
            return {"success": False, "error": "No simulation specified or open"}

        # Get simulation manager
        sim_mgr = aveva_conn.managers["simulation"]

        # Create resource array with simulation name
        resource = Array[String]([sim_name])

        # Define what fields we want from each connector
        child_types = Array[Object](
            [
                convert(
                    {
                        "type": "connector",
                        "fields": Array[String](
                            ["name", "connectorType", "from", "to", "description"]
                        ),
                    }
                )
            ]
        )

        # Execute the query
        result = sim_mgr.Query("simulation", resource, child_types).Result

        # Process results
        connectors_info = []
        if hasattr(result, "connector") and result.connector:
            for connector in result.connector:
                try:
                    # Use getattr for 'from' since it's a Python keyword
                    from_port = getattr(connector, "from", "Unknown")
                    to_port = getattr(connector, "to", "Unknown")

                    connector_info = {
                        "name": str(connector.name)
                        if hasattr(connector, "name")
                        else "Unknown",
                        "connector_type": str(connector.connectortype)
                        if hasattr(connector, "connectortype")
                        else "Unknown",
                        "from_port": str(from_port) if from_port else "Unknown",
                        "to_port": str(to_port) if to_port else "Unknown",
                        "description": str(connector.description)
                        if hasattr(connector, "description")
                        else "No description",
                    }
                    connectors_info.append(connector_info)
                    logger.debug(
                        f"Connector: {connector_info['name']}, Type: {connector_info['connector_type']}, From: {connector_info['from_port']}, To: {connector_info['to_port']}"
                    )
                except Exception as connector_error:
                    logger.warning(f"Error processing connector: {connector_error}")
                    connectors_info.append(
                        {
                            "name": "Error reading connector",
                            "connector_type": "Unknown",
                            "from_port": "Unknown",
                            "to_port": "Unknown",
                            "description": f"Error: {str(connector_error)}",
                        }
                    )

        return {
            "success": True,
            "simulation": sim_name,
            "connectors": connectors_info,
            "count": len(connectors_info),
            "message": f"Found {len(connectors_info)} connectors on flowsheet in simulation '{sim_name}'",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def show_all_ports(sim_name: str = None) -> Dict[str, Any]:
    """Tool: Get all port information for every model in the simulation."""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_name = sim_name or aveva_conn.current_simulation
        if not sim_name:
            return {"success": False, "error": "No simulation specified or open"}

        sim_mgr = aveva_conn.managers["simulation"]

        # Step 1: query all model names in the simulation
        resource = Array[String]([sim_name])
        model_child_types = Array[Object](
            [convert({"type": "model", "fields": Array[String](["name"])})]
        )
        model_result = sim_mgr.Query("simulation", resource, model_child_types).Result

        if not hasattr(model_result, "model") or not model_result.model:
            return {"success": True, "simulation": sim_name, "models": [], "count": 0}

        model_names = [
            str(m.name) for m in model_result.model if hasattr(m, "name")
        ]

        # Step 2: for each model, query its ports
        port_child_types = Array[Object](
            [
                convert(
                    {
                        "type": "port",
                        "fields": Array[String](
                            ["name", "fullname", "direction", "porttype", "ismultiple", "description"]
                        ),
                    }
                )
            ]
        )

        models_info = []
        for model_name in model_names:
            model_resource = Array[String]([sim_name, model_name])
            try:
                port_result = sim_mgr.Query(
                    "simulation", model_resource, port_child_types
                ).Result

                ports = []
                if hasattr(port_result, "port") and port_result.port:
                    for port in port_result.port:
                        ports.append(
                            {
                                "name": str(getattr(port, "name", "")),
                                "fullname": str(getattr(port, "fullname", "")),
                                "direction": str(getattr(port, "direction", "")),
                                "porttype": str(getattr(port, "porttype", "")),
                                "ismultiple": bool(getattr(port, "ismultiple", False)),
                                "description": str(getattr(port, "description", "")),
                            }
                        )
                models_info.append({"model": model_name, "ports": ports})
            except Exception as e:
                logger.warning(f"Error querying ports for model '{model_name}': {e}")
                models_info.append({"model": model_name, "ports": [], "error": str(e)})

        return {
            "success": True,
            "simulation": sim_name,
            "models": models_info,
            "count": len(models_info),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def show_one_model_param(
    sim_name: str = None, model_name: str = None
) -> Dict[str, Any]:
    """Tool: Get detailed parameter information for a specific model using AVEVA Query API"""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_name = sim_name or aveva_conn.current_simulation
        if not sim_name:
            return {"success": False, "error": "No simulation specified or open"}

        if not model_name:
            return {"success": False, "error": "Model name is required"}

        # Get simulation manager
        sim_mgr = aveva_conn.managers["simulation"]

        # Create resource array with simulation name and model name
        resource = Array[String]([sim_name, model_name])

        # Define what fields we want from each parameter
        child_types = Array[Object](
            [
                convert(
                    {
                        "type": "parameter",
                        "fields": Array[String](
                            ["name", "paramtype", "value", "uom", "description"]
                        ),
                    }
                )
            ]
        )

        # Execute the query
        result = sim_mgr.Query("simulation", resource, child_types).Result

        # Process results into efficient grouped structure
        parameter_groups = {}
        parameter_values = {}
        total_count = 0

        if hasattr(result, "parameter") and result.parameter:
            for parameter in result.parameter:
                try:
                    name = (
                        str(parameter.name) if hasattr(parameter, "name") else "Unknown"
                    )
                    param_type = (
                        str(parameter.paramtype)
                        if hasattr(parameter, "paramtype")
                        else "Unknown"
                    )
                    value = (
                        str(parameter.value)
                        if hasattr(parameter, "value")
                        else "Unknown"
                    )
                    uom = str(parameter.uom) if hasattr(parameter, "uom") else "Unknown"
                    description = (
                        str(parameter.description)
                        if hasattr(parameter, "description")
                        else "No description"
                    )

                    # Store the value separately
                    parameter_values[name] = value

                    # Group by parameter type first
                    if param_type not in parameter_groups:
                        parameter_groups[param_type] = {}

                    # Then sub-group by units of measurement
                    if uom not in parameter_groups[param_type]:
                        parameter_groups[param_type][uom] = {
                            "description": description,
                            "parameters": [],
                        }

                    # Add parameter name to the appropriate group
                    parameter_groups[param_type][uom]["parameters"].append(name)
                    total_count += 1

                    logger.debug(
                        f"Parameter: {name}, Type: {param_type}, Value: {value}, UOM: {uom}"
                    )

                except Exception as parameter_error:
                    logger.warning(f"Error processing parameter: {parameter_error}")
                    # Handle errors in the grouped structure
                    error_type = "Error"
                    if error_type not in parameter_groups:
                        parameter_groups[error_type] = {}
                    if "Unknown" not in parameter_groups[error_type]:
                        parameter_groups[error_type]["Unknown"] = {
                            "description": "Error reading parameter",
                            "parameters": [],
                        }
                    parameter_groups[error_type]["Unknown"]["parameters"].append(
                        f"Error_Parameter_{total_count}"
                    )
                    parameter_values[f"Error_Parameter_{total_count}"] = (
                        f"Error: {str(parameter_error)}"
                    )
                    total_count += 1

        unique_types = len(parameter_groups)

        return {
            "success": True,
            "simulation": sim_name,
            "model_name": model_name,
            "parameter_groups": parameter_groups,
            "parameter_values": parameter_values,
            "total_count": total_count,
            "unique_types": unique_types,
            "message": f"Found {total_count} parameters in {unique_types} types for model '{model_name}' in simulation '{sim_name}'",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def show_one_model_var(sim_name: str = None, model_name: str = None) -> Dict[str, Any]:
    """Tool: Get detailed variable information for a specific model using AVEVA Query API"""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_name = sim_name or aveva_conn.current_simulation
        if not sim_name:
            return {"success": False, "error": "No simulation specified or open"}

        if not model_name:
            return {"success": False, "error": "Model name is required"}

        # Get simulation manager
        sim_mgr = aveva_conn.managers["simulation"]

        # Create resource array with simulation name and model name
        resource = Array[String]([sim_name, model_name])

        # Define what fields we want from each variable
        child_types = Array[Object](
            [
                convert(
                    {
                        "type": "variable",
                        "fields": Array[String](
                            ["name", "varType", "value", "uom", "description"]
                        ),
                    }
                )
            ]
        )

        # Execute the query with timeout as in the original code
        try:
            result = sim_mgr.Query("simulation", resource, child_types, 5000).Result
        except Exception as query_error:
            logger.error(
                f"Error: Unable to query variables of {model_name} in {sim_name}: {query_error}"
            )
            return {
                "success": False,
                "error": f"Unable to query variables of {model_name} in {sim_name}: {str(query_error)}",
            }

        # Process results into efficient grouped structure
        variable_groups = {}
        variable_values = {}
        total_count = 0

        if hasattr(result, "variable") and result.variable:
            for variable in result.variable:
                try:
                    name = (
                        str(variable.name) if hasattr(variable, "name") else "Unknown"
                    )
                    var_type = (
                        str(variable.vartype)
                        if hasattr(variable, "vartype")
                        else "Unknown"
                    )
                    value = (
                        str(variable.value) if hasattr(variable, "value") else "Unknown"
                    )
                    uom = str(variable.uom) if hasattr(variable, "uom") else "Unknown"
                    description = (
                        str(variable.description)
                        if hasattr(variable, "description")
                        else "No description"
                    )

                    # Store the value separately
                    variable_values[name] = value

                    # Group by variable type first
                    if var_type not in variable_groups:
                        variable_groups[var_type] = {}

                    # Then sub-group by units of measurement
                    if uom not in variable_groups[var_type]:
                        variable_groups[var_type][uom] = {
                            "description": description,
                            "variables": [],
                        }

                    # Add variable name to the appropriate group
                    variable_groups[var_type][uom]["variables"].append(name)
                    total_count += 1

                    logger.debug(
                        f"Variable: {name}, Type: {var_type}, Value: {value}, UOM: {uom}"
                    )

                except Exception as variable_error:
                    logger.warning(f"Error processing variable: {variable_error}")
                    # Handle errors in the grouped structure
                    error_type = "Error"
                    if error_type not in variable_groups:
                        variable_groups[error_type] = {}
                    if "Unknown" not in variable_groups[error_type]:
                        variable_groups[error_type]["Unknown"] = {
                            "description": "Error reading variable",
                            "variables": [],
                        }
                    variable_groups[error_type]["Unknown"]["variables"].append(
                        f"Error_Variable_{total_count}"
                    )
                    variable_values[f"Error_Variable_{total_count}"] = (
                        f"Error: {str(variable_error)}"
                    )
                    total_count += 1

        unique_types = len(variable_groups)

        return {
            "success": True,
            "simulation": sim_name,
            "model_name": model_name,
            "variable_groups": variable_groups,
            "variable_values": variable_values,
            "total_count": total_count,
            "unique_types": unique_types,
            "message": f"Found {total_count} variables in {unique_types} types for model '{model_name}' in simulation '{sim_name}'",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# Utility functions for multi-variable operations
def get_multiple_variables(
    variable_paths: List[str], sim_name: str = None
) -> Dict[str, Any]:
    """Tool: Get multiple variable values at once"""
    results = {}
    errors = []

    for var_path in variable_paths:
        result = get_variable_value(var_path, sim_name)
        if result["success"]:
            results[var_path] = result["value"]
        else:
            errors.append(f"{var_path}: {result['error']}")

    return {
        "success": len(errors) == 0,
        "variables": results,
        "errors": errors,
        "simulation": sim_name or aveva_conn.current_simulation,
    }


def set_multiple_variables(
    variable_data: List[Dict[str, Any]], sim_name: str = None
) -> Dict[str, Any]:
    """Tool: Set multiple variables at once
    variable_data format: [{"path": "Model1.T", "value": 300, "unit": "K"}, ...]
    """
    results = []
    errors = []

    for var_data in variable_data:
        result = set_variable_value(
            var_data["path"], var_data["value"], var_data.get("unit"), sim_name
        )
        if result["success"]:
            results.append(result)
        else:
            errors.append(f"{var_data['path']}: {result['error']}")

    return {
        "success": len(errors) == 0,
        "set_variables": len(results),
        "errors": errors,
        "simulation": sim_name or aveva_conn.current_simulation,
    }


# =============================================================================
# HIGH-PRIORITY MISSING FUNCTIONS - SIMULATION MANAGEMENT
# =============================================================================


def delete_simulation(sim_name: str, timeout: int = None) -> Dict[str, Any]:
    """Tool: Delete a simulation permanently"""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_mgr = aveva_conn.managers["simulation"]

        # Use timeout if provided, otherwise use default API behavior
        if timeout:
            deleted = sim_mgr.DeleteSim(sim_name, timeout).Result
        else:
            deleted = sim_mgr.DeleteSim(sim_name).Result

        if deleted:
            # Clear current simulation if it was the one deleted
            if aveva_conn.current_simulation == sim_name:
                aveva_conn.current_simulation = None

            return {
                "success": True,
                "simulation_name": sim_name,
                "message": f"Successfully deleted simulation: {sim_name}",
            }
        else:
            return {
                "success": False,
                "error": f"Failed to delete simulation: {sim_name}",
            }

    except Exception as e:
        return {"success": False, "error": str(e)}


def rename_simulation(
    old_name: str, new_name: str, timeout: int = None
) -> Dict[str, Any]:
    """Tool: Rename an open simulation"""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_mgr = aveva_conn.managers["simulation"]

        # Use timeout if provided, otherwise use default API behavior
        if timeout:
            renamed = sim_mgr.RenameSim(old_name, new_name, timeout).Result
        else:
            renamed = sim_mgr.RenameSim(old_name, new_name).Result

        if renamed:
            # Update current simulation if it was the one renamed
            if aveva_conn.current_simulation == old_name:
                aveva_conn.current_simulation = new_name

            return {
                "success": True,
                "old_name": old_name,
                "new_name": new_name,
                "message": f"Successfully renamed simulation from '{old_name}' to '{new_name}'",
            }
        else:
            return {
                "success": False,
                "error": f"Failed to rename simulation from '{old_name}' to '{new_name}'",
            }

    except Exception as e:
        return {"success": False, "error": str(e)}


def save_simulation(sim_name: str = None, timeout: int = None) -> Dict[str, Any]:
    """Tool: Save a simulation"""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_name = sim_name or aveva_conn.current_simulation
        if not sim_name:
            return {"success": False, "error": "No simulation specified or open"}

        sim_mgr = aveva_conn.managers["simulation"]

        # Use timeout if provided, otherwise use default API behavior
        if timeout:
            saved = sim_mgr.SaveSimulation(sim_name, timeout).Result
        else:
            saved = sim_mgr.SaveSimulation(sim_name).Result

        if saved:
            return {
                "success": True,
                "simulation_name": sim_name,
                "message": f"Successfully saved simulation: {sim_name}",
            }
        else:
            return {"success": False, "error": f"Failed to save simulation: {sim_name}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# HIGH-PRIORITY MISSING FUNCTIONS - MODEL MANAGEMENT
# =============================================================================


def remove_model(
    model_name: str, sim_name: str = None, timeout: int = None
) -> Dict[str, Any]:
    """Tool: Remove a model from the simulation"""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_name = sim_name or aveva_conn.current_simulation
        if not sim_name:
            return {"success": False, "error": "No simulation specified or open"}

        model_mgr = aveva_conn.managers["model"]

        # Use timeout if provided, otherwise use default API behavior
        if timeout:
            removed = model_mgr.RemoveModel(sim_name, model_name, timeout).Result
        else:
            removed = model_mgr.RemoveModel(sim_name, model_name).Result

        if removed:
            return {
                "success": True,
                "model_name": model_name,
                "simulation": sim_name,
                "message": f"Successfully removed model: {model_name}",
            }
        else:
            return {
                "success": False,
                "error": f"Failed to remove model: {model_name} (model may not exist)",
            }

    except Exception as e:
        return {"success": False, "error": str(e)}


def rename_model(
    old_model_name: str, new_model_name: str, sim_name: str = None, timeout: int = None
) -> Dict[str, Any]:
    """Tool: Rename a model in the simulation"""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_name = sim_name or aveva_conn.current_simulation
        if not sim_name:
            return {"success": False, "error": "No simulation specified or open"}

        model_mgr = aveva_conn.managers["model"]

        # Use timeout if provided, otherwise use default API behavior
        if timeout:
            renamed = model_mgr.RenameModel(
                sim_name, old_model_name, new_model_name, timeout
            ).Result
        else:
            renamed = model_mgr.RenameModel(
                sim_name, old_model_name, new_model_name
            ).Result

        if renamed:
            return {
                "success": True,
                "old_name": old_model_name,
                "new_name": new_model_name,
                "simulation": sim_name,
                "message": f"Successfully renamed model from '{old_model_name}' to '{new_model_name}'",
            }
        else:
            return {
                "success": False,
                "error": f"Failed to rename model from '{old_model_name}' to '{new_model_name}'",
            }

    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# FLUID PACKAGE MANAGEMENT FUNCTIONS
# =============================================================================


def create_fluid_complete(
    library_name: str,
    fluid_name: str,
    components: List[str],
    thermo_method: str = "Non-Random Two-Liquid (NRTL)",
    phases: str = "Vapor/Liquid (VLE)",
    databank: str = "System:SIMSCI",
    timeout: int = 30000,
) -> Dict[str, Any]:
    """Tool: Create a complete fluid package with components and thermodynamic settings"""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        library_name = library_name or aveva_conn.current_simulation
        if not library_name:
            return {"success": False, "error": "Library name is required"}

        if not fluid_name:
            return {"success": False, "error": "Fluid name is required"}

        if not components:
            return {"success": False, "error": "At least one component is required"}

        library_mgr = aveva_conn.managers["library"]
        results = []
        warnings = []

        # Step 1: Check if fluid already exists
        existing_fluid_names = []
        fluid_already_exists = False
        try:
            fluids = library_mgr.GetFluids(library_name).Result
            fluid_list = list(fluids)
            existing_fluid_names = [fluid.name for fluid in fluid_list]
            results.append(
                f"Found {len(existing_fluid_names)} existing fluids in library '{library_name}'"
            )

            if fluid_name in existing_fluid_names:
                results.append(f"Fluid '{fluid_name}' already exists, reusing it")
                fluid_created = True
                fluid_already_exists = True
            else:
                results.append(f"Fluid '{fluid_name}' doesn't exist, creating new one")
                fluid_created = library_mgr.CreateFluid(
                    library_name, fluid_name, timeout
                ).Result
                fluid_already_exists = False
        except Exception as e:
            warnings.append(f"Could not check existing fluids: {e}")
            results.append(f"Creating new fluid '{fluid_name}'")
            fluid_created = library_mgr.CreateFluid(
                library_name, fluid_name, timeout
            ).Result
            fluid_already_exists = False

        if not fluid_created:
            return {
                "success": False,
                "error": f"Failed to create fluid '{fluid_name}'",
                "results": results,
                "warnings": warnings,
            }

        if fluid_already_exists:
            results.append(
                f"Using existing fluid '{fluid_name}' with its current configuration"
            )
        else:
            results.append(f"Fluid '{fluid_name}' created successfully")

            # Step 2: Add components
            component_results = []
            component_errors = []

            for component in components:
                try:
                    component_added = library_mgr.AddComponent(
                        library_name, fluid_name, databank, component, timeout
                    ).Result

                    if component_added:
                        component_results.append(
                            f"Successfully added component: {component}"
                        )
                    else:
                        component_errors.append(f"Failed to add component: {component}")

                except Exception as e:
                    component_errors.append(
                        f"Error adding component {component}: {str(e)}"
                    )

            results.extend(component_results)

            # Step 3: Set thermodynamic method
            try:
                thermo_set = library_mgr.UpdateFluidMethodData(
                    library_name, fluid_name, "System", thermo_method, timeout
                ).Result

                if thermo_set:
                    results.append(f"Thermodynamic method set to: {thermo_method}")
                else:
                    warnings.append(
                        f"Failed to set thermodynamic method to: {thermo_method}"
                    )

            except Exception as e:
                warnings.append(f"Error setting thermodynamic method: {str(e)}")

            # Step 4: Set phases
            try:
                phases_set = library_mgr.UpdateFluidMethodData(
                    library_name, fluid_name, "Phases", phases, timeout
                ).Result

                if phases_set:
                    results.append(f"Phases set to: {phases}")
                else:
                    warnings.append(f"Failed to set phases to: {phases}")

            except Exception as e:
                warnings.append(f"Error setting phases: {str(e)}")

            # Report component addition results
            if component_errors:
                warnings.extend(component_errors)

        # Determine overall success
        success = len([w for w in warnings if "Failed" in w or "Error" in w]) == 0

        return {
            "success": success,
            "library_name": library_name,
            "fluid_name": fluid_name,
            "components_requested": components,
            "components_added": len(
                [r for r in results if "Successfully added component" in r]
            ),
            "thermo_method": thermo_method,
            "phases": phases,
            "fluid_existed": fluid_already_exists,
            "results": results,
            "warnings": warnings,
            "message": f"Fluid package '{fluid_name}' configured with {len(components)} components",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def set_fluid_of_source(
    fluid_name: str, source_name: str, sim_name: str = None, timeout: int = 30000
) -> Dict[str, Any]:
    """Tool: Set fluid type for a source model"""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_name = sim_name or aveva_conn.current_simulation
        if not sim_name:
            return {"success": False, "error": "No simulation specified or open"}

        if not fluid_name:
            return {"success": False, "error": "Fluid name is required"}

        if not source_name:
            return {"success": False, "error": "Source name is required"}

        # Get parameter manager
        param_mgr = aveva_conn.managers.get("parameter")
        if not param_mgr:
            return {"success": False, "error": "Parameter manager not available"}

        # Build the fluid type path: {sim_name}.Models.{fluid_name}
        fluid_type_path = f"{sim_name}.Models.{fluid_name}"

        # Build the parameter path: {source_name}.FluidType
        parameter_path = f"{source_name}.FluidType"

        # Set the fluid type using parameter manager
        fluid_set = param_mgr.UpdateParameterValue(
            sim_name, parameter_path, fluid_type_path, timeout
        ).Result

        if fluid_set:
            return {
                "success": True,
                "simulation": sim_name,
                "source_name": source_name,
                "fluid_name": fluid_name,
                "fluid_type_path": fluid_type_path,
                "parameter_path": parameter_path,
                "message": f"Fluid type '{fluid_name}' assigned to source '{source_name}'",
            }
        else:
            return {
                "success": False,
                "simulation": sim_name,
                "source_name": source_name,
                "fluid_name": fluid_name,
                "error": f"Failed to set fluid type '{fluid_name}' for source '{source_name}'",
            }

    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# BATCH MODEL MANAGEMENT FUNCTIONS
# =============================================================================


def remove_multiple_models(
    model_names: List[str], sim_name: str = None, timeout: int = None
) -> Dict[str, Any]:
    """Tool: Remove multiple models from the simulation"""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_name = sim_name or aveva_conn.current_simulation
        if not sim_name:
            return {"success": False, "error": "No simulation specified or open"}

        if not model_names:
            return {"success": False, "error": "No model names provided"}

        model_mgr = aveva_conn.managers["model"]
        results = []
        errors = []

        for model_name in model_names:
            try:
                # Use timeout if provided, otherwise use default API behavior
                if timeout:
                    removed = model_mgr.RemoveModel(
                        sim_name, model_name, timeout
                    ).Result
                else:
                    removed = model_mgr.RemoveModel(sim_name, model_name).Result

                if removed:
                    results.append(f"Successfully removed model: {model_name}")
                else:
                    errors.append(
                        f"Failed to remove model: {model_name} (model may not exist)"
                    )

            except Exception as e:
                errors.append(f"Error removing model {model_name}: {str(e)}")

        success = len(errors) == 0
        return {
            "success": success,
            "simulation": sim_name,
            "removed_models": len(results),
            "total_requested": len(model_names),
            "results": results,
            "errors": errors,
            "message": f"Removed {len(results)}/{len(model_names)} models successfully",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# HIGH-PRIORITY MISSING FUNCTIONS - CONNECTOR MANAGEMENT
# =============================================================================


def remove_connector(
    connector_name: str, sim_name: str = None, timeout: int = None
) -> Dict[str, Any]:
    """Tool: Remove a connector from the simulation"""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_name = sim_name or aveva_conn.current_simulation
        if not sim_name:
            return {"success": False, "error": "No simulation specified or open"}

        conn_mgr = aveva_conn.managers["connector"]

        # Use timeout if provided, otherwise use default API behavior
        if timeout:
            removed = conn_mgr.RemoveConnector(sim_name, connector_name, timeout).Result
        else:
            removed = conn_mgr.RemoveConnector(sim_name, connector_name).Result

        if removed:
            return {
                "success": True,
                "connector_name": connector_name,
                "simulation": sim_name,
                "message": f"Successfully removed connector: {connector_name}",
            }
        else:
            return {
                "success": False,
                "error": f"Failed to remove connector: {connector_name} (connector may not exist)",
            }

    except Exception as e:
        return {"success": False, "error": str(e)}


def get_connector_list(sim_name: str = None) -> Dict[str, Any]:
    """Tool: Get list of all connectors in the simulation"""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_name = sim_name or aveva_conn.current_simulation
        if not sim_name:
            return {"success": False, "error": "No simulation specified or open"}

        conn_mgr = aveva_conn.managers["connector"]
        connectors = conn_mgr.GetConnectorList(sim_name).Result

        connector_list = []
        if connectors:
            for connector in connectors:
                # Safely extract connector information
                if hasattr(connector, "ToString"):
                    connector_name = connector.ToString()
                elif isinstance(connector, str):
                    connector_name = connector
                else:
                    connector_name = str(connector)

                connector_list.append(connector_name)

        return {
            "success": True,
            "simulation": sim_name,
            "connectors": connector_list,
            "count": len(connector_list),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def remove_multiple_connectors(
    connector_names: List[str], sim_name: str = None, timeout: int = None
) -> Dict[str, Any]:
    """Tool: Remove multiple connectors from the simulation"""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_name = sim_name or aveva_conn.current_simulation
        if not sim_name:
            return {"success": False, "error": "No simulation specified or open"}

        if not connector_names:
            return {"success": False, "error": "No connector names provided"}

        conn_mgr = aveva_conn.managers["connector"]
        results = []
        errors = []

        for connector_name in connector_names:
            try:
                # Use timeout if provided, otherwise use default API behavior
                if timeout:
                    removed = conn_mgr.RemoveConnector(
                        sim_name, connector_name, timeout
                    ).Result
                else:
                    removed = conn_mgr.RemoveConnector(sim_name, connector_name).Result

                if removed:
                    results.append(f"Successfully removed connector: {connector_name}")
                else:
                    errors.append(
                        f"Failed to remove connector: {connector_name} (connector may not exist)"
                    )

            except Exception as e:
                errors.append(f"Error removing connector {connector_name}: {str(e)}")

        success = len(errors) == 0
        return {
            "success": success,
            "simulation": sim_name,
            "removed_connectors": len(results),
            "total_requested": len(connector_names),
            "results": results,
            "errors": errors,
            "message": f"Removed {len(results)}/{len(connector_names)} connectors successfully",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# HIGH-PRIORITY MISSING FUNCTIONS - SNAPSHOT MANAGEMENT
# =============================================================================


def create_snapshot(sim_name: str = None, timeout: int = None) -> Dict[str, Any]:
    """Tool: Create a snapshot of the current simulation state"""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_name = sim_name or aveva_conn.current_simulation
        if not sim_name:
            return {"success": False, "error": "No simulation specified or open"}

        snapshot_mgr = aveva_conn.managers["snapshot"]

        # Use timeout if provided, otherwise use default API behavior
        if timeout:
            snapshot_name = snapshot_mgr.CreateSnapshot(sim_name, timeout).Result
        else:
            snapshot_name = snapshot_mgr.CreateSnapshot(sim_name).Result

        return {
            "success": True,
            "snapshot_name": snapshot_name,
            "simulation": sim_name,
            "message": f"Successfully created snapshot: {snapshot_name}",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def get_all_snapshots(sim_name: str = None) -> Dict[str, Any]:
    """Tool: Get list of all snapshots for the simulation"""
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_name = sim_name or aveva_conn.current_simulation
        if not sim_name:
            return {"success": False, "error": "No simulation specified or open"}

        snapshot_mgr = aveva_conn.managers["snapshot"]
        snapshots = snapshot_mgr.GetAllSnapshots(sim_name).Result

        snapshot_list = []
        if snapshots:
            for snapshot in snapshots:
                # Safely extract snapshot information
                if hasattr(snapshot, "ToString"):
                    snapshot_name = snapshot.ToString()
                elif isinstance(snapshot, str):
                    snapshot_name = snapshot
                else:
                    snapshot_name = str(snapshot)

                snapshot_list.append(snapshot_name)

        return {
            "success": True,
            "simulation": sim_name,
            "snapshots": snapshot_list,
            "count": len(snapshot_list),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# PARAMETER MANAGEMENT FUNCTIONS
# =============================================================================


def update_parameter(
    parameter_path: str, value: str, sim_name: str = None, timeout: int = 30000
) -> Dict[str, Any]:
    """Tool: Update a parameter value in the simulation

    Args:
        parameter_path: Full path to the parameter (e.g., 'Column1.FeedStage[S1]', 'Source1.FluidType')
        value: New value for the parameter (as string)
        sim_name: Target simulation (defaults to current simulation)
        timeout: Timeout in milliseconds (default: 30000)

    Returns:
        Dict with success status, parameter info, and message
    """
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_name = sim_name or aveva_conn.current_simulation
        if not sim_name:
            return {"success": False, "error": "No simulation specified or open"}

        # Get parameter manager
        param_mgr = aveva_conn.managers.get("parameter")
        if not param_mgr:
            return {"success": False, "error": "Parameter manager not available"}

        # Update the parameter value
        updated = param_mgr.UpdateParameterValue(
            sim_name, parameter_path, value, timeout
        ).Result

        if updated:
            return {
                "success": True,
                "simulation": sim_name,
                "parameter": parameter_path,
                "value": value,
                "message": f"Successfully updated parameter '{parameter_path}' to '{value}'",
            }
        else:
            return {
                "success": False,
                "simulation": sim_name,
                "parameter": parameter_path,
                "error": f"Failed to update parameter '{parameter_path}' (parameter may not exist or value is invalid)",
            }

    except Exception as e:
        return {"success": False, "error": str(e)}


def update_parameters(
    parameter_data: List[Dict[str, Any]], sim_name: str = None, timeout: int = 30000
) -> Dict[str, Any]:
    """Tool: Update multiple parameters at once

    Args:
        parameter_data: List of dicts with 'path' and 'value' keys
            Example: [
                {"path": "Column1.FeedStage[S1]", "value": "7"},
                {"path": "Source1.FluidType", "value": "MySim.Models.feed"}
            ]
        sim_name: Target simulation (defaults to current simulation)
        timeout: Timeout in milliseconds (default: 30000)

    Returns:
        Dict with batch operation results including success count and any errors
    """
    try:
        if not aveva_conn.sc:
            return {"success": False, "error": "Not connected to AVEVA"}

        sim_name = sim_name or aveva_conn.current_simulation
        if not sim_name:
            return {"success": False, "error": "No simulation specified or open"}

        if not parameter_data:
            return {"success": False, "error": "No parameter data provided"}

        results = []
        errors = []

        for param_data in parameter_data:
            try:
                # Extract parameter path and value
                param_path = param_data.get("path")
                param_value = param_data.get("value")

                if not param_path:
                    errors.append("Missing 'path' in parameter data")
                    continue

                if param_value is None:
                    errors.append(f"Missing 'value' for parameter '{param_path}'")
                    continue

                # Convert value to string (AVEVA API expects string)
                param_value_str = str(param_value)

                # Update the parameter
                result = update_parameter(
                    param_path, param_value_str, sim_name, timeout
                )

                if result["success"]:
                    results.append(result["message"])
                else:
                    errors.append(f"{param_path}: {result['error']}")

            except Exception as e:
                errors.append(
                    f"Error processing parameter {param_data.get('path', 'unknown')}: {str(e)}"
                )

        success = len(errors) == 0
        return {
            "success": success,
            "simulation": sim_name,
            "updated_parameters": len(results),
            "total_requested": len(parameter_data),
            "results": results,
            "errors": errors,
            "message": f"Updated {len(results)}/{len(parameter_data)} parameters successfully",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
