"""Prepare the scoped installer and private lab access files without Entra app registration or consent."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from cloud_io import ROOT, cli, environment, verify_target


def main(mode: str) -> None:
    account = verify_target()
    if mode == "prepare":
        object_id = cli("az", "ad", "signed-in-user", "show", "--query", "id", "--output", "tsv")
        if not object_id:
            raise RuntimeError("The authenticated installer did not resolve to a user object.")
        cli("azd", "env", "set", "INSTALLER_OBJECT_ID", object_id)
        cli("azd", "env", "set", "AZURE_TENANT_ID", account["tenantId"])
    elif mode == "install":
        env = environment()
        private = ROOT / ".private"
        private.mkdir(exist_ok=True)
        if os.name == "nt":
            user = f"{os.environ['USERDOMAIN']}\\{os.environ['USERNAME']}"
            subprocess.run(["icacls", str(private), "/grant:r", f"{user}:(OI)(CI)F", "/inheritance:r"],
                           check=True, capture_output=True, text=True)
        else:
            private.chmod(0o700)
        subprocess.run(
            ["dotnet", "run", "--project", str(ROOT / "src" / "FeedbackCampaign.Web"),
             "--configuration", "Release", "--no-launch-profile", "--",
             "--provision-lab-accounts", str(private), env["TABLE_ENDPOINT"], env["APP_URL"]],
            cwd=ROOT, check=True,
        )
    else:
        raise ValueError("Expected prepare or install; no automatic credential rotation is supported.")


if __name__ == "__main__":
    main(sys.argv[1])
