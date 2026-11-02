"""Run scenario-local checks and persist actual exit codes, never cloud success."""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = Path(r"C:\HackBuilder")
sys.path.insert(0, str(REPO / "scripts"))
from check_prerequisites import execution_environment


def run(args: list[str]) -> dict:
    result = subprocess.run([shutil.which(args[0]) or args[0], *args[1:]], cwd=ROOT,
                            env=execution_environment(REPO), capture_output=True, text=True, check=False)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return {"command": args, "exitCode": result.returncode, "passed": result.returncode == 0,
            "stdout": result.stdout, "stderr": result.stderr}


def validate_fixtures() -> dict:
    with (REPO / "fictitious_people_names.csv").open(encoding="utf-8-sig", newline="") as stream:
        people = {row["FullName"] for row in csv.DictReader(stream)}
    with (REPO / "fictitious_company_names.csv").open(encoding="utf-8-sig", newline="") as stream:
        companies = {row["Company Name"] for row in csv.DictReader(stream)}
    posts = json.loads((ROOT / "src/FeedbackCampaign.Web/SeedData/posts.json").read_text(encoding="utf-8"))
    assert "Adatum Corporation" in companies
    assert len(posts) == 10 and len({p["sourceId"] for p in posts}) == 10
    assert all(p["posterName"] in people and p["contact"].endswith("@example.test") for p in posts)
    request = json.loads((REPO / ".abcbuilder-portal/scenarios/feedback-campaign/request.json").read_text())
    assert request["industry"] == "Media & Communications" and request["businessUnits"] == ["sales", "marketing"]
    return {"passed": True, "postCount": len(posts), "catalogCompany": "Adatum Corporation",
            "businessUnits": request["businessUnits"], "industry": request["industry"]}


def main() -> None:
    checks = [
        run(["dotnet", "build", "src/FeedbackCampaign.Web", "-c", "Release", "--nologo"]),
        run(["dotnet", "test", "tests/FeedbackCampaign.Tests.csproj", "-c", "Release", "--nologo",
             "--logger", "trx;LogFileName=local-tests.trx", "--results-directory", "evidence/tests"]),
        run(["az", "bicep", "build", "--file", "infra/main.bicep"]),
        run(["az", "bicep", "lint", "--file", "infra/main.bicep"]),
        run(["az", "bicep", "build", "--file", "infra/review.bicep"]),
        run(["az", "bicep", "lint", "--file", "infra/review.bicep"]),
        run(["dotnet", "publish", "src/FeedbackCampaign.Web", "-c", "Release", "--nologo",
             "--output", "src/FeedbackCampaign.Web/bin/publish-check"]),
        run(["node", "--check", "src/FeedbackCampaign.Web/wwwroot/app.js"]),
        run([sys.executable, "-m", "compileall", "-q", "scripts"]),
        run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"]),
        run([str(REPO / ".venv/Scripts/python.exe"), "03-architect-diagram.py"]),
        run([str(REPO / ".venv/Scripts/python.exe"), "04-runtime-diagram.py"]),
    ]
    counters = ET.parse(ROOT / "evidence/tests/local-tests.trx").find(
        ".//{http://microsoft.com/schemas/VisualStudio/TeamTest/2010}Counters")
    publish = ROOT / "src/FeedbackCampaign.Web/bin/publish-check"
    assert (publish / "Policy/campaign-policy.md").is_file() and (publish / "Policy/agent-instructions.txt").is_file()
    assert (publish / "SeedData/posts.json").is_file()
    evidence = {"checkedAtUtc": datetime.now(timezone.utc).isoformat(), "evidenceType": "local-only",
                "passed": all(c["passed"] for c in checks), "checks": checks,
                "fixtures": validate_fixtures(), "applicationTests": counters.attrib if counters is not None else None,
                "cloudOperationsExecuted": False, "runtimeAcceptance": "not-run",
                "publishPolicyAndFixtures": True}
    (ROOT / "evidence/local-validation.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    if not evidence["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
