"""Local boundary, starter-state and archive checks. All failures are blocking."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGES = HERE.parent
SCENARIO = PACKAGES.parent
REPO = Path.cwd()
ROOTS = ("coach", "participant", "hack", "coach-guide")
EXCLUDE_DIRS = {"bin", "obj", "node_modules", "__pycache__", ".azure", ".git"}
EXCLUDE_FILES = {"main.json", "agent-installation.json"}
TEXT = {".json", ".cs", ".csproj", ".md", ".ps1", ".yaml", ".yml", ".js", ".bicep", ".config", ".txt"}


def files(root):
    return sorted(path for path in root.rglob("*") if path.is_file()
                  and not (set(path.relative_to(root).parts) & EXCLUDE_DIRS)
                  and path.name not in EXCLUDE_FILES)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def starter():
    result = subprocess.run([sys.executable, str(PACKAGES / "participant/scripts/status.py")],
                            text=True, capture_output=True, check=True)
    status = json.loads(result.stdout)
    assert status["status"] == "not-configured"
    assert status["chatAvailable"] is False and status["applicationUrl"] is None
    assert status["industry"] == "Hospitality & Travel" and status["businessUnits"] == ["sales"]
    print(result.stdout.strip())
    assert not list((PACKAGES / "participant").rglob("*.cs"))
    print("Starter reports intended incomplete state; no app or completed agent implementation.")


def boundaries():
    authored = [SCENARIO / "08-hack-package-contract.md", SCENARIO / "nextsteps.MD",
                PACKAGES / "coach/README.md", PACKAGES / "participant/README.md"]
    for name in ("hack", "coach-guide"):
        authored += list((PACKAGES / name).rglob("*.md"))
    for path in authored:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            assert len(line) <= 120, f"Markdown line exceeds 120 characters: {path}:{number}"
    compiled = json.loads((PACKAGES / "participant/infra/main.json").read_text(encoding="utf-8-sig"))
    resources = compiled["resources"]
    assert len(resources) == 1 and resources[0]["type"].lower() == "microsoft.resources/resourcegroups"
    assert compiled["parameters"]["location"].get("defaultValue") is None
    assert compiled["parameters"]["environmentName"].get("defaultValue") is None
    assert set(compiled["outputs"]) == {"AZURE_RESOURCE_GROUP"}
    source = (PACKAGES / "participant/infra/main.bicep").read_text(encoding="utf-8")
    for token in ("CognitiveServices", "storageAccounts", "serverfarms", "roleAssignments", "module ", "existing "):
        assert token.lower() not in source.lower(), token
    for name in ("main.bicep", "resources.bicep", "main.parameters.json"):
        coach = (PACKAGES / "coach/infra" / name).read_bytes()
        assert coach == (SCENARIO / "infra" / name).read_bytes(), f"Coach IaC changed: {name}"
    for path in (SCENARIO / "src/CoffeeShop.Web/Services").glob("*.cs"):
        assert path.read_bytes() == (PACKAGES / "coach/src/CoffeeShop.Web/Services" / path.name).read_bytes()
    for path in (SCENARIO / "src/CoffeeShop.Web/Agents").glob("*.md"):
        assert path.read_bytes() == (PACKAGES / "coach/src/CoffeeShop.Web/Agents" / path.name).read_bytes()
    assert (SCENARIO / "tests/CoffeeShop.Tests/ScenarioTests.cs").read_bytes() == (
        PACKAGES / "coach/tests/CoffeeShop.Tests/ScenarioTests.cs").read_bytes()

    with (REPO / "fictitious_company_names.csv").open(encoding="utf-8-sig", newline="") as stream:
        companies = list(csv.reader(stream))
    assert companies[14] == ["Fourth Coffee", "fourthcoffee.com"]
    malformed = [i for i, row in enumerate(companies) if len(row) != 2]
    print(f"Malformed company catalog records rejected, not repaired: {malformed}")
    with (REPO / "fictitious_people_names.csv").open(encoding="utf-8-sig", newline="") as stream:
        people = list(csv.DictReader(stream))
    assert [x["FullName"] for x in people[:4]] == [
        "Airi Ilves", "Hasan Ibrahimov", "Nemanja Milatovic", "Nino Kapanadze"]
    fixture = SCENARIO / "src/CoffeeShop.Web/SeedData/stores.json"
    snapshots = json.loads(fixture.read_text(encoding="utf-8"))
    assert len(snapshots) == 3 and sum(len(s["Stock"]) for s in snapshots) == 12
    for s, person in zip(snapshots, [people[0], people[1], people[3]]):
        assert s["Store"]["Manager"] == person["FullName"]
        assert s["Version"] and s["Stock"] and s["Ledger"]
        assert not re.search(r"[/\\#?\x00-\x1f]", s["Store"]["StoreId"])
    for destination in ("coach/src/CoffeeShop.Web/SeedData", "participant/data", "hack/Allfiles",
                        "coach-guide/Allfiles"):
        assert digest(fixture) == digest(PACKAGES / destination / "stores.json")
    cases = json.loads((PACKAGES / "hack/Allfiles/evaluation-cases.json").read_text(encoding="utf-8"))
    assert len(cases["cases"]) == len({c["id"] for c in cases["cases"]}) == 6
    assert cases["industry"] == "Hospitality & Travel" and cases["businessUnits"] == ["sales"]

    manifest = json.loads((SCENARIO / "09-hack-event-manifest.json").read_text(encoding="utf-8"))
    assert manifest["teamCount"] == len(manifest["teams"]) == 1
    entries = [manifest["coach"], *manifest["teams"]]
    assert len({x["azdEnvironment"] for x in entries}) == len(entries)
    assert len({x["resourceGroup"] for x in entries}) == len(entries)
    assert all(x["deploymentStatus"] == "planned" and x["applicationUrl"] is None for x in entries)
    for entry in entries:
        assert entry["resourceGroup"] == "rg-" + entry["azdEnvironment"]
    assert manifest["teams"][0]["id"] == "01"

    # Concrete reference identifiers are prohibited; built-in RBAC definition GUIDs are portable APIs.
    observation = json.loads((REPO / ".abcbuilder-portal/system-identity.json").read_text(encoding="utf-8-sig"))
    ids = observation["identity"]["scope"]
    forbidden = [ids["subscriptionId"], ids["tenantId"], ids["account"], "coffee-shop-ref", "swedencentral",
                 "web-fc-keegvmxonq3wc", "fc-coffee-shop-keegvmxo", "stfckeegvmxonq3wc",
                 "a03f1a03-1b4b-402d-a807-0334996b560e"]
    for name in ROOTS:
        root = PACKAGES / name
        for path in files(root):
            relative = path.relative_to(root)
            assert not path.name.startswith(".env"), path
            assert path.name not in {"workflow-state.json", "scenario-validation.json", "local-checks.json"}, path
            if path.suffix.lower() not in TEXT:
                continue
            text = path.read_text(encoding="utf-8-sig")
            for token in forbidden:
                assert token.lower() not in text.lower(), f"Reference leak {token}: {relative}"
            # Browser-standard fake upload path is library logic, not workstation evidence.
            path_scan = text.replace(r"C:\\fakepath\\", "")
            assert not re.search(r"[A-Za-z]:\\", path_scan), f"Local path: {relative}"
            if name in {"participant", "hack"}:
                for token in ("99-finale", "solution-overview", "Foundry__stock__Name", "GetProjectResponsesClientForAgentEndpoint"):
                    assert token not in text, f"Public implementation leak: {relative}"
            if path.suffix == ".md":
                for target in re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", text):
                    target = target.split("#")[0]
                    if target and not target.startswith(("http:", "https:", "mailto:", "{{")):
                        assert (path.parent / target).is_file(), f"Broken local link {target}: {relative}"
    public = PACKAGES / "hack"
    private = PACKAGES / "coach-guide"
    for path in (public / "Allfiles").rglob("*"):
        if path.is_file():
            assert path.read_bytes() == (private / path.relative_to(public)).read_bytes()
    for path in (public / "Instructions").rglob("*.md"):
        assert path.read_bytes() == (private / path.relative_to(public)).read_bytes()
    assert len(list((public / "Instructions/hospitality-travel").glob("*.md"))) == 5
    print("Source/compiled starter denylist, exact fixtures/catalogs, coach baseline equality, "
          "isolation, sanitization, links and public/private parity passed.")


def archives():
    release = PACKAGES / "release"
    release.mkdir(exist_ok=True)
    reports = []
    for filename, roots in (
        ("coffee-shop-learner.zip", ("participant", "hack")),
        ("coffee-shop-private-coach.zip", ("coach", "coach-guide")),
    ):
        archive = release / filename
        expected = {f"{root}/{path.relative_to(PACKAGES / root).as_posix()}": path
                    for root in roots for path in files(PACKAGES / root)}
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for name, path in sorted(expected.items()):
                bundle.write(path, name)
        with zipfile.ZipFile(archive) as bundle:
            assert bundle.testzip() is None
            assert set(bundle.namelist()) == set(expected)
            for name in bundle.namelist():
                assert bundle.read(name) == expected[name].read_bytes()
                assert ".." not in Path(name).parts
            if "learner" in filename:
                assert not any("99-finale" in name or name.startswith(("coach/", "coach-guide/"))
                               for name in bundle.namelist())
        reports.append({
            "filename": filename, "sha256": digest(archive), "files": len(expected),
            "roots": list(roots), "visibility": "public-safe" if "learner" in filename else "private",
        })
        print(f"{filename}: CRC/manifest/byte-parity passed; {len(expected)} files")
    (release / "archive-manifest.json").write_text(json.dumps({
        "eventDeployed": False, "archives": reports,
        "limitations": "Local ZIP validation only; not published or deployed. Fresh destination readiness required."
    }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("check", choices=("starter", "boundaries", "archives"))
    args = parser.parse_args()
    {"starter": starter, "boundaries": boundaries, "archives": archives}[args.check]()
