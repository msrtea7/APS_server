"""Windows REST server configuration."""

HOST = "0.0.0.0"
PORT = 8000
DEFAULT_TIMEOUT = 30_000

AVEVA_MODEL_TYPES = {
    "sources_sinks": {
        "Source": "Lib:Process.Source",
        "Sink": "Lib:Process.Sink",
    },
    "heat_exchangers": {
        "HeatExchanger": "Lib:Process.HX",
    },
    "separators": {
        "Drum": "Lib:Process.Drum",
        "Column": "Lib:Process.Column",
    },
    "reactors": {
        "CSTR": "Lib:Process.CSTR",
        "PFR": "Lib:Process.PFR",
        "Equilibrium": "Lib:Process.EQR",
    },
    "pumps_compressors": {
        "Pump": "Lib:Process.Pump",
        "Compressor": "Lib:Process.Compressor",
    },
}
