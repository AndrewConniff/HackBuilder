"""Validate and persist the stopped partial installation without any further cloud writes."""

import json
import re
import subprocess
import sys

from install import EXPECTED_HASH, ROOT, RUN, SCENARIO, SCOPE, command, infrastructure_fingerprint, read, write

sys.path.insert(0, str(ROOT / "scripts"))
from scenario_catalog import refresh


def main() -> None:
    if infrastructure_fingerprint(SCENARIO) != EXPECTED_HASH:
        raise ValueError("Approved infrastructure changed during installation.")
    deployment = read("deployment-final")["result"]
    if deployment["properties"]["provisioningState"] != "Succeeded":
        raise ValueError("Shared deployment is not successful.")
    if any(item["state"] != "Succeeded" for item in read("deployments-after-provision")["result"]):
        raise ValueError("Nested installation contains a non-successful deployment.")
    resources = read("resources-final")["result"]
    if len(resources) != 14 or any(item["location"] != "centralus" for item in resources):
        raise ValueError("Current installed resource inventory differs from the recorded result.")
    if any(item["tags"].get("Project") != "resto-scale-agent" for item in resources):
        raise ValueError("Current resource ownership did not verify.")
    if len(read("cosmos-installed-grants")["result"]) != 3:
        raise ValueError("Corrected Cosmos grants are missing.")
    for grant in read("cosmos-installed-grants")["result"]:
        if not grant["scope"].endswith("/databaseAccounts/cosmos-resto-4tvlzr5zf2rxi/dbs/restaurant"):
            raise ValueError("Cosmos grant scope differs from reviewed database-only scope.")
    receipt = json.loads((SCENARIO / "evidence" / "identity-installation.json").read_text())
    for kind, expected_role in (
        ("api", receipt["roleIds"]["Manager"]), ("client", "00000000-0000-0000-0000-000000000000"),
    ):
        assignments = read(f"{kind}-assignments-final")["result"]["value"]
        if len(assignments) != 1 or any((
            assignments[0]["principalId"] != "214d672b-df87-4f3b-94fd-7863032546c1",
            assignments[0]["appRoleId"] != expected_role,
            assignments[0]["resourceId"] != receipt[kind]["servicePrincipalId"],
        )):
            raise ValueError("Approved operator assignments did not verify.")
    if read("consent-final")["result"]["value"] != []:
        raise ValueError("Consent state changed; do not report the earlier absence as current.")
    denial = read("operator-access-owned-principal")
    if (denial["exitCode"] != 1 or "Authorization_RequestDenied" not in denial["stderr"]
            or "Insufficient privileges" not in denial["stderr"]):
        raise ValueError("Exact observed authorization denial is not retained.")
    verify_command = [sys.executable, str(RUN / "operator_access.py"), "--verify-only"]
    verified = subprocess.run(
        verify_command, capture_output=True, text=True, encoding="utf-8", check=False, timeout=120,
    )
    result = json.loads(verified.stdout)
    write("consent-verification", {
        "command": subprocess.list2cmdline(verify_command), "exitCode": verified.returncode,
        "result": result, "stderr": verified.stderr,
    })
    if verified.returncode != 1 or result["passed"] is not False or result["matchingApplicationGrantCount"] != 0:
        raise ValueError("Read-only absence verification did not return its required failed result.")
    for name, arguments in (
        ("operator-tests", ["python", "-m", "unittest", "discover", "-s", str(RUN), "-p", "test_operator_access.py"]),
        ("scenario-python-tests", [
            "python", "-m", "unittest", "discover", "-s", str(SCENARIO / "validation"), "-p", "test_*.py",
        ]),
    ):
        if not (RUN / f"{name}.json").exists():
            command(name, arguments)
        elif read(name)["exitCode"] != 0:
            raise ValueError(f"Retained local check did not pass: {name}")
    summary = (SCENARIO / "06-deployment-summary.md").read_text(encoding="utf-8")
    template = (ROOT / ".github" / "skills" / "az-azure-artifacts" / "templates"
                / "06-deployment-summary.template.md").read_text(encoding="utf-8")
    if re.findall(r"^## .+$", summary, re.M) != re.findall(r"^## .+$", template, re.M):
        raise ValueError("Deployment summary no longer preserves its required headings.")
    long_lines = [index for index, line in enumerate(summary.splitlines(), 1) if len(line) > 120]
    if long_lines:
        raise ValueError(f"Deployment summary lines exceed 120 columns: {long_lines}")
    for path in RUN.glob("*.json"):
        json.loads(path.read_text(encoding="utf-8-sig"))
    metadata = json.loads((SCENARIO / "reviewed-metadata.json").read_text())
    manifest = refresh(SCENARIO, metadata=metadata)
    if manifest["metadataStatus"] != "curated":
        raise ValueError("Scenario metadata must remain reviewed and curated.")
    region = json.loads((SCENARIO / "00-region-availability.json").read_text())
    if region["consolidatedInstallation"]["infrastructureFingerprint"] != EXPECTED_HASH:
        raise ValueError("Regional installation evidence does not match actual reviewed infrastructure.")
    write("evidence-integrity", {
        "scope": SCOPE, "infrastructureFingerprint": EXPECTED_HASH,
        "sharedDeployment": "Succeeded", "allNestedDeploymentsSucceeded": True,
        "resourceCount": len(resources), "operatorAssignmentsVerified": True,
        "consentGrantAbsent": True, "actualConsentDenialRetained": True,
        "readOnlyVerification": result, "summaryTemplateAndLineLengthsPassed": True,
        "scenarioManifest": "refreshed locally only; no shared catalog export",
        "operatorTests": "5 passed", "scenarioPythonTests": read("scenario-python-tests")["stderr"],
        "runtimeAcceptancePassed": False, "suitabilitySnapshotCreated": False,
        "cloudWritesAfterConsentDenial": False,
    })
    print("Partial installation evidence verified and persisted; operator consent remains blocked.")


if __name__ == "__main__":
    main()
