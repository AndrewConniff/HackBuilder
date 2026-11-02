"""Offline local verification and private evidence capture; no Azure CLI invocation."""
from pathlib import Path
from datetime import datetime, timezone
import json
import os
import subprocess
import sys
import hashlib
import re
import zipfile

REPO = Path.cwd()
ROOT = REPO / "generated-scenarios/finance-security-hack"
P = ROOT / "packages"
V = P / "validation"
DOTNET = (Path.home() / ".copilot/session-state/c325fe77-0030-44d6-8b42-65777dcb3064/"
          "files/tools/dotnet/dotnet.exe")
BICEP = Path.home() / ".azure/bin/bicep.exe"
results = []
env = os.environ.copy()
env["DOTNET_ROOT"] = str(DOTNET.parent)
env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
env["DOTNET_SKIP_FIRST_TIME_EXPERIENCE"] = "1"
env["DOTNET_NOLOGO"] = "1"
env["PATH"] = str(DOTNET.parent) + os.pathsep + env.get("PATH", "")


def run(name, args, cwd=REPO):
    print(f"START {name}", flush=True)
    started = datetime.now(timezone.utc)
    r = subprocess.run([str(a) for a in args], cwd=cwd, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    (V / f"{name}.log").write_text(r.stdout + r.stderr, encoding="utf-8")
    result = {"name": name, "command": [str(a) for a in args], "exitCode": r.returncode,
              "startedAtUtc": started.isoformat(), "durationSeconds": elapsed}
    results.append(result)
    print(f"{name}: exit {r.returncode}, {elapsed:.1f}s", flush=True)
    if r.returncode:
        print((r.stdout + r.stderr)[-12000:], flush=True)
    save()
    return r.returncode == 0


def save():
    (V / "local-checks.json").write_text(json.dumps({
        "scope": "Local offline package authoring only; no Azure operations or runtime certification.",
        "historicalEvidence": "User attestation only; URL, exact time and logs unavailable.",
        "checks": results,
        "allCommandsPassed": bool(results) and all(r["exitCode"] == 0 for r in results),
        "eventDeployed": False,
    }, indent=2), encoding="utf-8")


all_ok = run("approval-before-validation", [sys.executable, "scripts/hack_workflow.py",
             "check-approval", ROOT])
for package in ("coach", "participant"):
    main = P / package / "infra/main.bicep"
    all_ok &= run(f"{package}-bicep-build", [BICEP, "build", main, "--no-restore",
                  "--outfile", V / f"{package}.arm.json"])
    all_ok &= run(f"{package}-bicep-lint", [BICEP, "lint", main, "--no-restore"])

app = P / "coach/src/Brokerage.Web/Brokerage.Web.csproj"
tests = P / "coach/tests/Brokerage.Tests/Brokerage.Tests.csproj"
all_ok &= run("coach-offline-restore", [DOTNET, "restore", tests,
              "--configfile", V / "NuGet.Config", "-p:NuGetAudit=false"])
all_ok &= run("coach-build", [DOTNET, "build", app, "-c", "Release", "--no-restore"])
all_ok &= run("coach-tests", [DOTNET, "test", tests, "-c", "Release", "--no-restore",
              "--logger", "trx;LogFileName=coach-tests.trx", "--results-directory", V])
all_ok &= run("coach-script-guards", ["pwsh", "-NoProfile", "-File",
              P / "coach/scripts/Test-LocalScripts.ps1"])
all_ok &= run("starter-status", [sys.executable, P / "participant/scripts/starter_status.py"])
all_ok &= run("package-boundaries", [sys.executable, V / "verify_boundaries.py"])
all_ok &= run("skillable", [sys.executable,
              ".github/skills/skillable-lod-authoring/scripts/validate_skillable_package.py",
              P, "--industry", "financial-services"])
all_ok &= run("skillable-authoring-resources", [sys.executable,
              ".github/skills/skillable-lod-authoring/scripts/validate_skillable_package.py", "--check-skill"])
all_ok &= run("approval-final", [sys.executable, "scripts/hack_workflow.py", "check-approval", ROOT])

# Archive only sanitized package source. Never export validation records, compiled ARM or caches.
if all_ok:
    release = V / "release"
    release.mkdir(exist_ok=True)
    exported = {}
    for package in ("coach", "participant", "hack", "coach-guide"):
        files = []
        archive = release / f"{package}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            for file in sorted((P / package).rglob("*")):
                if not file.is_file():
                    continue
                rel = file.relative_to(P / package)
                if any(part in {"bin", "obj", ".azure", "__pycache__", "artifacts", "TestResults"}
                       for part in rel.parts):
                    continue
                assert file.name not in {"workflow-state.json", "scenario-validation.json"}
                z.write(file, str(rel).replace("\\", "/"))
                files.append({"path": str(rel).replace("\\", "/"),
                              "sha256": hashlib.sha256(file.read_bytes()).hexdigest()})
        exported[package] = {"visibility": "public-candidate" if package in {"participant", "hack"} else "private",
                             "archiveSha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                             "files": files}
    (release / "release-inventory.json").write_text(json.dumps(exported, indent=2), encoding="utf-8")
    archive_assertions = 0
    for package, record in exported.items():
        with zipfile.ZipFile(release / f"{package}.zip") as z:
            assert z.testzip() is None
            archive_assertions += 1
            assert set(z.namelist()) == {f["path"] for f in record["files"]}
            archive_assertions += 1
            for file in record["files"]:
                assert hashlib.sha256(z.read(file["path"])).hexdigest() == file["sha256"]
                assert not {"bin", "obj", ".azure", ".env", "__pycache__", "artifacts"} & set(
                    Path(file["path"]).parts)
                archive_assertions += 2
            if package in {"participant", "hack"}:
                assert not any(s in name.lower() for name in z.namelist()
                               for s in ("99-finale", "solution-overview", "deployment-guide", "agent-instructions"))
                archive_assertions += 1
            if package == "coach-guide":
                assert "media/03-architect-diagram.png" in z.namelist()
                assert "Instructions/financial-services/99-finale.md" in z.namelist()
                archive_assertions += 2
    results.append({"name": "release-archives", "command": ["local ZIP integrity, hash and visibility assertions"],
                    "exitCode": 0, "assertions": archive_assertions})
    save()
    print("Sanitized source release archives created; private/public roots remain separate.")
print("PASS: packages validated; event not deployed" if all_ok else "FAIL: package validation incomplete")
sys.exit(0 if all_ok else 1)
