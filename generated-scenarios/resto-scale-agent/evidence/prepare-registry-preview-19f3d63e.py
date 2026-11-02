"""Prepare an independent registry-only preview, explicitly excluding identity grants."""

import copy
import json
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parent


def main() -> None:
    source = json.loads((DIRECTORY / "what-if-main-19f3d63e.arm.json").read_text(encoding="utf-8-sig"))
    modules = source["resources"]
    modules = list(modules.values()) if isinstance(modules, dict) else modules
    registry = next(item for item in modules if item["name"] == "registry")
    parameters = copy.deepcopy(registry["properties"]["parameters"])
    parameters["name"] = {"value": "acrresto4tvlzr5zf2rxi"}
    parameters["location"] = {"value": "eastus2"}
    parameters["tags"] = {"value": {
        "Environment": "resto-scale-agent", "ManagedBy": "Bicep",
        "Project": "resto-scale-agent", "SecurityControl": "Ignore",
    }}
    parameters["roleAssignments"] = {"value": []}
    assert parameters["networkRuleSetDefaultAction"]["value"] == "Allow"
    wrapper = json.loads((DIRECTORY / "what-if-subscription-19f3d63e.arm.json").read_text(encoding="utf-8"))
    deployment = wrapper["resources"][1]
    deployment["name"] = "registry-independent-19f3d63e"
    deployment["properties"]["parameters"] = parameters
    deployment["properties"]["template"] = registry["properties"]["template"]
    (DIRECTORY / "registry-independent-19f3d63e.arm.json").write_text(
        json.dumps(wrapper, indent=2) + "\n", encoding="utf-8"
    )
    print("Prepared actual compiled AVM registry-only preview for the saved owned name and group.")
    print("Only group + registry previewed. All four role assignments excluded, not validated or authorized.")
    print("This is not the full reference preview or a replacement production template. No Azure operation.")


if __name__ == "__main__":
    main()
