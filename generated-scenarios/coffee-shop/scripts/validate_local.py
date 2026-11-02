"""Run only local build checks and persist actual output; never contacts an Azure subscription."""

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("locked-restore", ["dotnet", "restore", "src/CoffeeShop.Web", "--locked-mode"]),
    ("build", ["dotnet", "build", "src/CoffeeShop.Web", "--no-restore", "--nologo", "-v", "minimal"]),
    ("focused-tests", [
        "dotnet", "test", "tests/CoffeeShop.Tests", "--nologo", "-v", "minimal",
        "--logger", "trx;LogFileName=local-tests.trx", "--results-directory", "evidence",
    ]),
    ("bicep-build", ["az", "bicep", "build", "--file", "infra/main.bicep"]),
    ("bicep-lint-main", ["az", "bicep", "lint", "--file", "infra/main.bicep"]),
    ("bicep-lint-resources", ["az", "bicep", "lint", "--file", "infra/resources.bicep"]),
    ("browser-restore", ["npm", "ci", "--prefix", "src/CoffeeShop.Web", "--ignore-scripts", "--no-audit", "--no-fund"]),
    ("browser-assets", ["npm", "run", "build", "--prefix", "src/CoffeeShop.Web"]),
    ("browser-syntax", ["node", "--check", "src/CoffeeShop.Web/wwwroot/js/workspace.js"]),
    ("publish", [
        "dotnet", "publish", "src/CoffeeShop.Web", "--no-restore", "--nologo",
        "-c", "Release", "-v", "minimal",
    ]),
    ("powershell-syntax", [
        "pwsh", "-NoProfile", "-Command",
        "$failed=$false; Get-ChildItem scripts/*.ps1 | ForEach-Object { "
        "$tokens=$null;$errors=$null;"
        "[System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$tokens,[ref]$errors)|Out-Null;"
        "if($errors){$errors;$failed=$true}else{Write-Output ('Parsed '+$_.Name)} };if($failed){exit 1}",
    ]),
]


def main() -> int:
    records = []
    for name, command in CHECKS:
        command[0] = shutil.which(command[0]) or command[0]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, encoding="utf-8", errors="replace")
        print(f"{name}: exit {result.returncode}")
        print(result.stdout, result.stderr)
        records.append({
            "name": name, "command": command, "exitCode": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr,
        })
    evidence = {
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "scope": "local-only; dependency test doubles do not prove inference or Azure runtime",
        "passed": all(record["exitCode"] == 0 for record in records), "checks": records,
    }
    (ROOT / "evidence").mkdir(exist_ok=True)
    (ROOT / "evidence/local-checks.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
