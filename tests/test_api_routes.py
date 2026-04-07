"""
Route-level tests for api_server.py.

These tests mock aveva_tools so they run without AVEVA SimCentral running.
Run with:  pytest tests/test_api_routes.py -v
"""

import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app():
    """Import api_server with aveva_tools fully mocked."""
    # Stub out every heavy dependency before importing the module
    for mod in ["simcentralconnect", "clr", "System", "pythonnet"]:
        sys.modules.setdefault(mod, MagicMock())

    # Provide a minimal aveva_tools mock so the router can bind
    mock_tools = MagicMock()
    sys.modules["src.aveva_tools"] = mock_tools

    # Re-import (or re-use cached) api_server
    if "src.api_server" in sys.modules:
        del sys.modules["src.api_server"]
    from src import api_server  # noqa: PLC0415
    return api_server.app, mock_tools


app, mock_tools = _make_app()
client = TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_mocks():
    mock_tools.reset_mock()
    yield


# ---------------------------------------------------------------------------
# /flowsheet/ports  — new endpoint
# ---------------------------------------------------------------------------

class TestShowAllPorts:
    def test_returns_tool_response(self):
        mock_tools.show_all_ports.return_value = {
            "success": True,
            "simulation": "TestSim",
            "models": [
                {
                    "model": "Feed",
                    "ports": [
                        {
                            "name": "Out",
                            "fullname": "Feed.Out",
                            "direction": "out",
                            "porttype": "Material",
                            "ismultiple": False,
                            "description": "",
                        }
                    ],
                }
            ],
            "count": 1,
        }

        resp = client.post("/flowsheet/ports", json={"sim_name": "TestSim"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["simulation"] == "TestSim"
        assert len(body["models"]) == 1
        assert body["models"][0]["model"] == "Feed"
        assert body["models"][0]["ports"][0]["direction"] == "out"
        mock_tools.show_all_ports.assert_called_once_with("TestSim")

    def test_no_sim_name_passes_none(self):
        mock_tools.show_all_ports.return_value = {"success": True, "models": []}
        resp = client.post("/flowsheet/ports", json={})
        assert resp.status_code == 200
        mock_tools.show_all_ports.assert_called_once_with(None)

    def test_tool_failure_propagated(self):
        mock_tools.show_all_ports.return_value = {
            "success": False,
            "error": "Not connected",
        }
        resp = client.post("/flowsheet/ports", json={"sim_name": "X"})
        assert resp.status_code == 200
        assert resp.json()["success"] is False


# ---------------------------------------------------------------------------
# Removed routes must return 404
# ---------------------------------------------------------------------------

class TestRemovedRoutes:
    def test_model_list_gone(self):
        resp = client.post("/model/list", json={"sim_name": "X"})
        assert resp.status_code == 404

    def test_snapshot_take_gone(self):
        resp = client.post(
            "/snapshot/take", json={"snapshot_name": "snap1", "sim_name": "X"}
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Existing flowsheet routes still work
# ---------------------------------------------------------------------------

class TestExistingFlowsheetRoutes:
    def test_flowsheet_models(self):
        mock_tools.show_models_on_flowsheet.return_value = {
            "success": True,
            "models": [],
        }
        resp = client.post("/flowsheet/models", json={"sim_name": "X"})
        assert resp.status_code == 200
        mock_tools.show_models_on_flowsheet.assert_called_once_with("X")

    def test_flowsheet_connectors(self):
        mock_tools.show_connectors_on_flowsheet.return_value = {
            "success": True,
            "connectors": [],
        }
        resp = client.post("/flowsheet/connectors", json={"sim_name": "X"})
        assert resp.status_code == 200
        mock_tools.show_connectors_on_flowsheet.assert_called_once_with("X")
