"""azd hooks: local Linux publication, private VM delivery and generated agent-version capture."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlparse

from install_identity import command, save
from private_runner import ROOT, SUBSCRIPTION, wait_application


def run(arguments: list[str], **kwargs) -> str:
    executable = shutil.which(arguments[0])
    if not executable:
        raise RuntimeError(f"Required existing tool unavailable: {arguments[0]}")
    result = subprocess.run(
        [executable, *arguments[1:]], capture_output=True, text=True, timeout=5600, check=False, **kwargs)
    if result.returncode:
        raise RuntimeError(f"{arguments[0]} failed: {result.stderr[-2000:]}")
    return result.stdout


def main() -> None:
    if os.environ.get("EQUIP_PRIVATE_RUNNER_APPROVED") != "true":
        raise ValueError("Private management addition has not been approved; no deployment or directory call made.")
    for key, value in {
        "AZURE_ENV_NAME": "equip-ai", "AZURE_RESOURCE_GROUP": "rg-equip-ai",
        "AZURE_LOCATION": "centralus", "AZURE_SUBSCRIPTION_ID": SUBSCRIPTION,
        "AZURE_TENANT_ID": "16b3c013-d300-468d-ac64-7eda0820b6d3",
    }.items():
        if os.environ.get(key) != value:
            raise ValueError(f"Explicit authorized target mismatch: {key}")
    if sys.argv[1] == "prepare":
        endpoint = urlparse(os.environ.get("AZURE_AI_PROJECT_ENDPOINT", ""))
        if not endpoint.hostname or not endpoint.hostname.endswith(".services.ai.azure.com"):
            raise ValueError("The retained same-scenario Foundry endpoint is required for restoration.")
        foundry = endpoint.hostname.split(".")[0]
        deleted = command([
            "az", "cognitiveservices", "account", "list-deleted", "--subscription", SUBSCRIPTION,
            "--query", f"[?name=='{foundry}'].{{id:id,name:name,location:location}}", "--output", "json"])
        if len(deleted) > 1 or any(
            item["location"] != "centralus" or "/resourcegroups/rg-equip-ai/" not in item["id"].lower()
            for item in deleted
        ):
            raise ValueError("Deleted Foundry account does not match the exact approved restoration scope.")
        command(["azd", "env", "set", "EQUIP_RESTORE_FOUNDRY", str(bool(deleted)).lower(),
                 "--environment", "equip-ai"], json_output=False)
        save(ROOT / "local-evidence" / "resume-20261026" / "foundry-recovery.json",
             {"restoreRequired": bool(deleted), "observedDeletedAccounts": deleted,
              "purgeAttempted": False, "retainedPrivateSecurity": True})
        # Generate a local installation-only key. It is not used for remote access and is never uploaded.
        key = ROOT / ".installation" / "equip-ai" / "management-ssh"
        key.parent.mkdir(parents=True, exist_ok=True)
        if not key.with_suffix(".pub").exists():
            run(["ssh-keygen", "-t", "ed25519", "-f", str(key), "-N", "", "-C", "equip-ai-management"])
        for name, value in (
            ("EQUIP_ENABLE_MANAGEMENT", "true"),
            ("EQUIP_MANAGEMENT_PUBLIC_KEY", key.with_suffix(".pub").read_text().strip()),
        ):
            command(["azd", "env", "set", name, value, "--environment", "equip-ai"], json_output=False)
        private = ROOT / ".private"
        private.mkdir(exist_ok=True)
        if os.name == "nt":
            owner = run(["whoami"]).strip()
            run(["icacls", str(private), "/inheritance:r", "/grant:r", f"{owner}:(OI)(CI)F"])
        else:
            private.chmod(0o700)
        run(["dotnet", "run", "--project", str(ROOT / "src" / "EquipAI.Web"),
             "--no-launch-profile", "--", "--prepare-accounts", f"--AccessDirectory={private}"], cwd=ROOT)
        return
    if sys.argv[1] != "publish":
        raise ValueError("Only prepare and publish hooks exist.")
    publish = ROOT / ".installation" / "equip-ai" / "linux-publish"
    run(["dotnet", "publish", str(ROOT / "src" / "EquipAI.Web"), "-c", "Release",
         "-r", "linux-x64", "--self-contained", "true", "-o", str(publish)], cwd=ROOT)
    output = run([sys.executable, str(ROOT / "scripts" / "private_runner.py"),
                  "publish", "--publish-directory", str(publish)], cwd=ROOT)
    # Parse the small guest receipt without copying deployment tokens or app bodies into logs.
    receipt = next((json.loads(line) for line in output.splitlines()
                    if line.startswith('{"agent":')), None)
    if not receipt or not receipt["agent"].get("version"):
        raise RuntimeError("No actual generated agent version returned.")
    version = str(receipt["agent"]["version"])
    command(["az", "webapp", "config", "appsettings", "set", "--subscription", SUBSCRIPTION,
             "--resource-group", "rg-equip-ai", "--name", os.environ["AZURE_WEB_NAME"],
             "--settings", f"AgentVersion={version}", "--output", "none"], json_output=False)
    command(["azd", "env", "set", "EQUIP_AGENT_VERSION", version, "--environment", "equip-ai"],
            json_output=False)
    receipt["applicationReadiness"] = wait_application(
        os.environ["APPLICATION_URL"], hashlib.sha256((publish / "EquipAI.Web.dll").read_bytes()).hexdigest(), version)
    save(ROOT / ".installation" / "equip-ai" / "private-installation.json", receipt)
    for name in ("participant-access.json", "coach-access.json"):
        path = ROOT / ".private" / name
        access = json.loads(path.read_text(encoding="utf-8"))
        access["applicationUrl"] = os.environ["APPLICATION_URL"].rstrip("/") + "/"
        save(path, access)
    if os.environ.get("EQUIP_ENABLE_HUMAN_MANAGEMENT") == "true":
        run([sys.executable, str(ROOT / "scripts" / "setup_human_access.py")], cwd=ROOT)
    print("Private publication and agent initialization completed; runtime acceptance still required.")


if __name__ == "__main__":
    main()
