"""Validate minimum starter, reference parity and public/private release boundaries."""
from pathlib import Path
import ast
import json
import re
import subprocess
import sys
import hashlib
import csv

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "packages"
errors = []
count = 0


def check(condition, message):
    global count
    count += 1
    if not condition:
        errors.append(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

repo = Path.cwd()
companies = list(csv.reader((repo / "fictitious_company_names.csv").read_text(encoding="utf-8-sig").splitlines()))
check(companies[1] == ["Adatum Corporation", "adatum.com"], "Exact catalog company record drift")
industries = list(csv.reader((repo / "microsoft_industry_verticals.csv").read_text(
    encoding="utf-8-sig").splitlines()))
check(["Financial Services", "Capital Markets"] in industries, "Exact intake industry selection missing")
catalog = json.loads((repo / ".github/skills/skillable-lod-authoring/assets/industry-catalog.json").read_text())
check(any(c["slug"] == "financial-services" and c["displayName"] == "Financial Services" for c in catalog),
      "Exact supported Skillable industry missing")

# Exact approved code, IaC, tests, scripts and runtime data are preserved in private coach.
for folder in ("src", "tests", "infra", "scripts", "data"):
    for file in (ROOT / folder).rglob("*"):
        if not file.is_file() or any(p in {"bin", "obj", ".azure", "__pycache__"} for p in file.parts):
            continue
        target = P / "coach" / file.relative_to(ROOT)
        check(target.exists(), f"Missing coach source {file.relative_to(ROOT)}")
        if target.exists():
            if file.name == "Prepare-WhatIf.ps1":
                expected = file.read_text(encoding="utf-8").replace(
                    r"C:\approved-target.json", "./approved-target.json").replace(r"C:\preview", "./preview")
                check(target.read_text(encoding="utf-8").strip() == expected.strip(),
                      "Coach script differs beyond example-path sanitation")
            else:
                check(sha(target) == sha(file), f"Coach drift {file.relative_to(ROOT)}")

arm = json.loads((P / "validation/participant.arm.json").read_text(encoding="utf-8"))
check([r["type"] for r in arm["resources"]] == ["Microsoft.Resources/resourceGroups"],
      "Starter ARM must contain only the isolated resource group")
check(arm["outputs"]["STARTER_STATUS"]["value"] == "not-configured", "Starter false-success output")
check(not any("url" in name.lower() for name in arm["outputs"]), "Starter must have no app URL output")
for forbidden in ("Microsoft.CognitiveServices", "Microsoft.App", "Microsoft.ApiManagement",
                  "Microsoft.KeyVault", "Microsoft.Storage", "Microsoft.Search", "Microsoft.DocumentDB",
                  "Microsoft.Network", "Microsoft.ManagedIdentity", "Microsoft.Authorization/roleAssignments",
                  "Microsoft.ContainerRegistry"):
    for file in (P / "participant").rglob("*"):
        if file.is_file():
            check(forbidden.lower() not in file.read_text(encoding="utf-8").lower(),
                  f"Forbidden starter service {forbidden}: {file.name}")
    check(forbidden.lower() not in json.dumps(arm).lower(), f"Forbidden compiled starter service {forbidden}")
check(not (P / "participant/src").exists(), "No starter app is justified")
starter_yaml = (P / "participant/azure.yaml").read_text(encoding="utf-8")
check("services:" not in starter_yaml and "hooks:" not in starter_yaml,
      "Starter has no app service or cloud ingestion hook")
params = json.loads((P / "participant/infra/main.parameters.json").read_text(encoding="utf-8"))
check(params["parameters"]["environmentName"]["value"] == "${AZURE_ENV_NAME}"
      and params["parameters"]["location"]["value"] == "${AZURE_LOCATION}",
      "Starter parameters must be unresolved azd environment expressions")
status = subprocess.run([sys.executable, P / "participant/scripts/starter_status.py"],
                        capture_output=True, text=True, check=True)
status = json.loads(status.stdout)
check(status["status"] == "not-configured" and not status["applicationIncluded"]
      and status["applicationUrl"] is None, "Starter must explicitly report incomplete")
check(not list((P / "participant").rglob("agent-instructions.txt")), "Starter leaks complete instructions")

manifest = json.loads((ROOT / "09-hack-event-manifest.json").read_text(encoding="utf-8"))
teams = manifest["teams"]
check(manifest["teamCount"] == len(teams) == 1, "Default manifest must have one team")
check([t["id"] for t in teams] == ["01"], "Contiguous zero-padded IDs required")
targets = [manifest["coach"], *teams]
check(len({t["resourceGroup"] for t in targets}) == len(targets), "Resource groups must be distinct")
check(len({t["azdEnvironment"] for t in targets}) == len(targets), "azd environments must be distinct")
check(all(t["deploymentStatus"] == "planned" and t["applicationUrl"] is None for t in targets),
      "No previous deployment status or URL may be copied")
for t in targets:
    check(t["resourceGroup"] == "rg-" + t["azdEnvironment"], "Naming target drift")

faq = ROOT / "data/brokerage-faq.md"
ids = re.findall(r"^## (FAQ-\d{2})", faq.read_text(encoding="utf-8"), re.M)
check(ids == [f"FAQ-{i:02}" for i in range(1, 13)], "Expected exactly twelve stable FAQ IDs")
for rel in ("coach/data", "participant/data", "hack/Allfiles", "coach-guide/Allfiles"):
    check(sha(P / rel / faq.name) == sha(faq), f"FAQ drift at {rel}")
evaluation = json.loads((P / "hack/Allfiles/evaluation.json").read_text(encoding="utf-8"))
check(len(evaluation["cases"]) == 6 and len(evaluation["infrastructureChecks"]) == 8,
      "Evaluation case count drift")
check(len({c["id"] for c in evaluation["cases"]}) == 6, "Evaluation IDs must be unique")
check(all(set(c["sourceIds"]) <= set(ids) for c in evaluation["cases"]), "Evaluation source ID drift")
for folder in ("Allfiles", "Instructions"):
    public = P / "hack" / folder
    public_files = sorted(p for p in public.rglob("*") if p.is_file())
    for file in public_files:
        target = P / "coach-guide" / file.relative_to(P / "hack")
        check(target.exists() and sha(file) == sha(target), f"Private copy drift {file.name}")
check(not list((P / "hack").rglob("*finale*")), "Finale leaked into public root")
check((P / "coach-guide/Instructions/financial-services/99-finale.md").exists(), "Missing private Finale")
check((P / "coach-guide/media/03-architect-diagram.png").read_bytes().startswith(b"\x89PNG"),
      "Missing valid private architecture diagram")

bad_names = {".azure", ".env", "workflow-state.json", "scenario-validation.json", "phase-a-status.json",
             "local-validation.json", "00-region-availability.json", "06-deployment-summary.md"}
for package in ("coach", "participant", "hack", "coach-guide"):
    for file in (P / package).rglob("*"):
        if any(part in {"bin", "obj", "artifacts"} for part in file.parts):
            continue
        check(file.name not in bad_names, f"Private operational state exported: {file}")
        if not file.is_file() or file.suffix.lower() not in {
                ".md", ".json", ".yaml", ".yml", ".txt", ".ps1", ".cs", ".bicep", ".xml", ".csproj", ".py"}:
            continue
        text = file.read_text(encoding="utf-8")
        check(not re.search(r"(?<![A-Za-z])[A-Za-z]:\\|C:/Users/|C:/HackBuilder/", text),
              f"Local path exported {file}")
        check(not re.search(r"(?i)AccountKey=|SharedAccessSignature=|-----BEGIN.*PRIVATE KEY", text),
              f"Credential pattern exported {file}")
        if package in {"participant", "hack"}:
            check(not re.search(r"(?i)coach notes|answer key|private coach|solution-overview|DeclarativeAgentDefinition|"
                                r"AgentReference\(|AgentAdministrationClient|GetProjectResponsesClientForAgent", text),
                  f"Completed solution or private reference leaked {file}")
            check(not re.search(r"https://[^\s)]+\.(?:azurewebsites\.net|cognitiveservices\.azure\.com|"
                                r"vault\.azure\.net|blob\.core\.windows\.net)", text),
                  f"Concrete data-plane endpoint exported {file}")
        # Check all non-image relative Markdown links; anchors are local section references.
        if file.suffix == ".md":
            for link in re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", text):
                if "://" not in link and not link.startswith("#") and "{{" not in link:
                    check((file.parent / link.split("#")[0]).exists(), f"Broken link {file.name}: {link}")

public_build = (P / "hack/_build.yml").read_text(encoding="utf-8")
check("solution-overview.md" not in public_build and "deployment-guide.md" not in public_build,
      "Public release include list contains private material")
check("Allfiles/**" in public_build and "Instructions/**" in public_build, "Public release missing lab payloads")
check("media/**" in (P / "coach-guide/_build.yml").read_text(encoding="utf-8"),
      "Private release must include solution-overview media")
result = {"checks": count, "passed": not errors, "errors": errors,
          "scope": "Static/local; no runtime cloud acceptance"}
(P / "validation/boundaries.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
for error in errors:
    print("FAIL:", error)
print(f"{count} boundary assertions; {len(errors)} failure(s)")
sys.exit(1 if errors else 0)
