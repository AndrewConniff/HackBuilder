"""Extract embedded ARM templates for local Checkov coverage; never resolve cloud state."""

import argparse
import json
from pathlib import Path


def extract(template: dict, output: Path, name: str = "root") -> int:
    output.mkdir(parents=True, exist_ok=True)
    resources = template.get("resources", [])
    if isinstance(resources, dict):
        resources = list(resources.values())
    audit_view = template | {"resources": resources}
    (output / f"{name}.json").write_text(json.dumps(audit_view, indent=2) + "\n", encoding="utf-8")
    count = 1
    for index, resource in enumerate(resources):
        properties = resource.get("properties", {})
        embedded = properties.get("template") if isinstance(properties, dict) else None
        if isinstance(embedded, dict):
            count += extract(embedded, output, f"{name}-{index}")
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    count = extract(json.loads(args.template.read_text(encoding="utf-8")), args.output)
    print(f"Extracted {count} templates for security scanning, including nested AVM resource definitions.")


if __name__ == "__main__":
    main()
