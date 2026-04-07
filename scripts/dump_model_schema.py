#!/usr/bin/env python3
"""
Dump variable and parameter schemas for all models in a simulation.

Queries a running APS server and writes:
  - client/resources/{scenario}_schema.json   (machine-readable, for AI tools)
  - client/resources/{scenario}_schema.md     (human-readable reference tables)

Usage:
    python3.12.exe scripts/dump_model_schema.py \
        --sim Sep_MeOHWater_2 \
        --scenario distillation \
        --host http://localhost:8000
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: pip install requests")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def post(host, path, body):
    resp = requests.post(f"{host}{path}", json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_models(host, sim_name):
    data = post(host, "/flowsheet/models", {"sim_name": sim_name})
    if not data.get("success"):
        raise RuntimeError(f"show_models_on_flowsheet failed: {data.get('error')}")
    return data["models"]


def fetch_vars(host, sim_name, model_name):
    data = post(host, "/model/vars", {"sim_name": sim_name, "model_name": model_name})
    if not data.get("success"):
        print(f"  WARN: could not fetch vars for {model_name}: {data.get('error')}")
        return {}
    return data.get("variable_groups", {})


def fetch_params(host, sim_name, model_name):
    data = post(host, "/model/params", {"sim_name": sim_name, "model_name": model_name})
    if not data.get("success"):
        print(f"  WARN: could not fetch params for {model_name}: {data.get('error')}")
        return {}
    return data.get("parameter_groups", {})


# ---------------------------------------------------------------------------
# Schema builder
# ---------------------------------------------------------------------------

def build_schema(host, sim_name):
    """
    Returns a dict keyed by model_type, each containing:
      {
        "variable_groups": { group: { uom: { description, variables } } },
        "parameter_groups": { group: { uom: { description, parameters } } },
        "instances": [model_name, ...]   # which instances were used as source
      }
    """
    models = fetch_models(host, sim_name)
    schema_by_type = {}

    for m in models:
        mtype = m["model_type"]
        mname = m["name"]

        if mtype in schema_by_type:
            # Already have schema for this type; just record additional instance
            schema_by_type[mtype]["instances"].append(mname)
            continue

        print(f"  Querying {mname} ({mtype}) ...")
        var_groups = fetch_vars(host, sim_name, mname)
        param_groups = fetch_params(host, sim_name, mname)

        schema_by_type[mtype] = {
            "instances": [mname],
            "variable_groups": var_groups,
            "parameter_groups": param_groups,
        }

    return schema_by_type


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------

def render_group_table(groups, item_key):
    """Render a variable_groups or parameter_groups dict as markdown tables."""
    lines = []
    for group_name, uom_dict in groups.items():
        for uom, info in uom_dict.items():
            desc = info.get("description", "")
            items = info.get(item_key, [])
            lines.append(f"\n**{group_name}** (`{uom}`)")
            if desc:
                # Take only the first sentence to keep tables concise
                short_desc = desc.split("\n")[0].split(".")[0]
                lines.append(f"> {short_desc}")
            lines.append("")
            lines.append("| Name | Unit |")
            lines.append("|------|------|")
            for name in items:
                lines.append(f"| `{name}` | {uom} |")
    return "\n".join(lines)


def render_markdown(scenario, sim_name, schema_by_type):
    sections = [
        f"# {scenario.capitalize()} Model Schema",
        f"\n> Auto-generated from simulation `{sim_name}`. Do not edit values — schema only.\n",
    ]

    for mtype, data in sorted(schema_by_type.items()):
        instances = ", ".join(data["instances"])
        sections.append(f"\n## {mtype}\n")
        sections.append(f"*Sourced from instance(s): {instances}*\n")

        var_groups = data["variable_groups"]
        param_groups = data["parameter_groups"]

        if var_groups:
            sections.append("\n### Variables\n")
            sections.append(render_group_table(var_groups, "variables"))
        else:
            sections.append("\n*No variables.*\n")

        if param_groups:
            sections.append("\n### Parameters\n")
            sections.append(render_group_table(param_groups, "parameters"))
        else:
            sections.append("\n*No parameters.*\n")

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Dump AVEVA model schema to client/resources/")
    parser.add_argument("--sim",      required=True, help="Simulation name, e.g. Sep_MeOHWater_2")
    parser.add_argument("--scenario", required=True, help="Scenario tag, e.g. distillation")
    parser.add_argument("--host",     default="http://localhost:8000", help="APS server base URL")
    args = parser.parse_args()

    out_dir = Path(__file__).parent.parent / "client" / "resources"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Connecting to {args.host} ...")
    print(f"Fetching model list for simulation '{args.sim}' ...")
    schema = build_schema(args.host, args.sim)

    # Write JSON
    json_path = out_dir / f"{args.scenario}_schema.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"simulation": args.sim, "scenario": args.scenario, "models": schema}, f, indent=2)
    print(f"\nWrote {json_path}")

    # Write Markdown
    md_path = out_dir / f"{args.scenario}_schema.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown(args.scenario, args.sim, schema))
    print(f"Wrote {md_path}")

    print(f"\nDone. Model types captured: {', '.join(sorted(schema.keys()))}")


if __name__ == "__main__":
    main()
