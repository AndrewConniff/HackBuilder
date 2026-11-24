"""Build and validate the private, single-template Skillable delivery archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import BinaryIO

import resource_policy

DELIVERY_FOLDER = "Skillable Deployment Package"
ARCHIVE_NAME = "skillable-deployment.zip"
TEMPLATE_NAME = "azuredeploy.json"
TEMPLATE_SCHEMA = "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#"
MODES = ("learner", "reference")
CORE_FILES = {
    TEMPLATE_NAME, "README.md", "deployment-manifest.json", "scripts/Deploy.ps1",
    *(f"azuredeploy.parameters.{mode}.json" for mode in MODES),
}
FORBIDDEN_PARTS = {
    ".git", ".azure", ".venv", "node_modules", "__pycache__", "bin", "obj", "secrets", "evidence",
}
FORBIDDEN_FILES = {
    "local.settings.json", "appsettings.development.json", "credentials.json", "secrets.json",
    "workflow-state.json", "scenario-validation.json", "installation-receipt.json",
}
FORBIDDEN_SUFFIXES = {".bicep", ".bicepparam", ".tf", ".tfvars", ".pem", ".key", ".pfx", ".p12"}


def read_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object.")
    return value


def safe_relative(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        bool(name) and "\\" not in name and ":" not in name and not path.is_absolute()
        and path.as_posix() == name
        and not any(part in {"..", "."} or part.startswith(".") or part.lower() in FORBIDDEN_PARTS
                    for part in path.parts)
        and path.name.lower() not in FORBIDDEN_FILES
        and path.suffix.lower() not in FORBIDDEN_SUFFIXES
    )


def content_files(content: Path) -> dict[str, Path]:
    if not content.is_dir() or content.is_symlink():
        raise ValueError(f"Missing regular delivery content directory: {content}")
    files = {}
    for path in sorted(content.rglob("*")):
        relative = path.relative_to(content).as_posix()
        if path.is_symlink() or path.resolve() != content.resolve() / path.relative_to(content):
            raise ValueError(f"Linked delivery content is not allowed: {relative}")
        if not safe_relative(relative):
            raise ValueError(f"Unsafe or non-deliverable content: {relative}")
        if path.is_file():
            if not path.stat().st_size:
                raise ValueError(f"Empty delivery file: {relative}")
            files[relative] = path
    missing = CORE_FILES - files.keys()
    if missing:
        raise ValueError(f"Missing delivery files: {', '.join(sorted(missing))}")
    return files


def validate_template(template: dict) -> None:
    if template.get("$schema") != TEMPLATE_SCHEMA:
        raise ValueError("Skillable requires a resource-group ARM template, not subscription-scope deployment.")
    if not isinstance(template.get("resources"), (list, dict)):
        raise ValueError("ARM resources must be an array or symbolic-name object.")

    def inspect(value: object) -> None:
        if isinstance(value, dict):
            if any(key.lower() in {"templatelink", "parameterslink"} for key in value):
                raise ValueError("External templateLink/parametersLink is forbidden; embed templates inline.")
            if str(value.get("type", "")).lower() == "microsoft.resources/deployments":
                if any(key in value for key in ("scope", "subscriptionId", "resourceGroup")):
                    raise ValueError("Nested deployments must stay inside the Skillable resource group.")
                properties = value.get("properties")
                if isinstance(properties, dict) and any(
                    key.lower() in {"templatelink", "parameterslink"} for key in properties
                ):
                    raise ValueError("External templateLink/parametersLink is forbidden; embed templates inline.")
                if not isinstance(properties, dict) or not isinstance(properties.get("template"), dict):
                    raise ValueError("Every nested deployment must contain an inline template.")
                validate_template(properties["template"])
            for child in value.values():
                inspect(child)
        elif isinstance(value, list):
            for child in value:
                inspect(child)

    inspect(template)
    resource_policy.validate_template(template)


def validate_content(packages: Path) -> dict[str, Path]:
    content = packages / DELIVERY_FOLDER / "content"
    files = content_files(content)
    template = read_object(files[TEMPLATE_NAME])
    if files[TEMPLATE_NAME].stat().st_size > 4 * 1024 * 1024:
        raise ValueError("The single ARM template exceeds the 4 MiB template limit.")
    validate_template(template)
    parameters = template.get("parameters", {})
    if not isinstance(parameters, dict) or any(not isinstance(value, dict) for value in parameters.values()):
        raise ValueError("ARM parameters must be an object containing parameter definitions.")
    mode_parameter = parameters.get("deploymentMode", {})
    if (
        mode_parameter.get("type") != "string"
        or mode_parameter.get("defaultValue") != "learner"
        or mode_parameter.get("allowedValues") != list(MODES)
    ):
        raise ValueError("deploymentMode must allow learner/reference and default to learner.")
    body = json.dumps({key: value for key, value in template.items() if key != "parameters"})
    if not re.search(r"parameters\(\s*['\"]deploymentMode['\"]\s*\)", body, re.IGNORECASE):
        raise ValueError("ARM resource selection must use deploymentMode, not just declare it.")

    for name, parameter in parameters.items():
        if str(parameter.get("type", "")).lower() in {"securestring", "secureobject"}:
            if parameter.get("defaultValue") not in (None, "", {}):
                raise ValueError(f"Do not package a secure parameter default: {name}")
    for name, path in files.items():
        if path.suffix.lower() != ".json":
            continue
        document = read_object(path) if name in CORE_FILES else json.loads(path.read_text(encoding="utf-8-sig"))
        if name != TEMPLATE_NAME and isinstance(document, dict) and (
            "deploymenttemplate.json" in str(document.get("$schema", "")).lower()
            or ("resources" in document and "contentVersion" in document)
        ):
            raise ValueError(f"Only one ARM template may be delivered; found {name}.")
    for mode in MODES:
        values = read_object(files[f"azuredeploy.parameters.{mode}.json"]).get("parameters")
        if not isinstance(values, dict) or values.get("deploymentMode") != {"value": mode}:
            raise ValueError(f"The {mode} parameter file must select deploymentMode={mode}.")
        for name, value in values.items():
            if name not in parameters or not isinstance(value, dict) or set(value) != {"value"}:
                raise ValueError(f"Invalid or external parameter value in {mode}: {name}")
            if str(parameters[name].get("type", "")).lower() in {"securestring", "secureobject"}:
                if value["value"] not in ("", {}):
                    raise ValueError(f"Do not package secure parameter values: {name}")

    manifest = read_object(files["deployment-manifest.json"])
    modes = manifest.get("modes")
    if manifest.get("schemaVersion") != 1 or not isinstance(modes, dict) or set(modes) != set(MODES):
        raise ValueError("deployment-manifest.json must declare schemaVersion 1 and both modes.")
    declared = set(CORE_FILES)
    for mode in MODES:
        entry = modes[mode]
        if not isinstance(entry, dict):
            raise ValueError(f"Invalid delivery manifest mode: {mode}")
        for field in ("requiredFiles", "postDeployScripts"):
            paths = entry.get(field)
            if not isinstance(paths, list) or any(not isinstance(path, str) for path in paths):
                raise ValueError(f"Manifest {mode}.{field} must be a list of package-relative file paths.")
            for relative in paths:
                if not safe_relative(relative) or relative not in files:
                    raise ValueError(f"Missing or unsafe manifest dependency for {mode}: {relative}")
                declared.add(relative)
    undeclared = files.keys() - declared
    if undeclared:
        raise ValueError(f"Assign every supporting file to a mode: {', '.join(sorted(undeclared))}")
    return files


def checksum(stream: BinaryIO) -> str:
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def validate_archive(archive_path: Path, files: dict[str, Path]) -> None:
    try:
        with zipfile.ZipFile(archive_path) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)) or set(names) != set(files):
                raise ValueError("Delivery ZIP must contain exactly the content files at its root.")
            for name, path in files.items():
                with archive.open(name) as packed, path.open("rb") as source:
                    if checksum(packed) != checksum(source):
                        raise ValueError(f"Delivery ZIP is stale or differs from content: {name}")
    except zipfile.BadZipFile as error:
        raise ValueError(f"Invalid delivery ZIP: {error}") from error


def validate_delivery(packages: Path) -> Path:
    files = validate_content(packages)
    archive_path = packages / DELIVERY_FOLDER / ARCHIVE_NAME
    validate_archive(archive_path, files)
    return archive_path


def build_delivery(packages: Path) -> Path:
    files = validate_content(packages)
    destination = packages / DELIVERY_FOLDER / ARCHIVE_NAME
    with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".tmp", delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with zipfile.ZipFile(temporary_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, path in files.items():
                archive.write(path, name)
        validate_archive(temporary_path, files)
        temporary_path.replace(destination)
    finally:
        temporary_path.unlink(missing_ok=True)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "validate"))
    parser.add_argument("scenario", type=Path)
    args = parser.parse_args()
    try:
        from hack_workflow import check_approval

        scenario = args.scenario.resolve()
        check_approval(scenario)
        action = build_delivery if args.command == "build" else validate_delivery
        archive = action(scenario / "packages")
    except (OSError, ValueError, TypeError) as error:
        parser.exit(1, f"Skillable delivery blocked: {error}\n")
    print(f"Skillable delivery {args.command}: passed; private archive: {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
