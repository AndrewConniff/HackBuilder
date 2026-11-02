"""Local-only synthetic employee installation. Never logs passwords, hashes or signing material."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ITERATIONS = 210_000


def private_directory(directory: Path) -> Path:
    """Restrict the external operator directory before any secret is written."""
    directory = directory.resolve()
    # Junctions resolve to physical paths; disallow both this scenario and the repository.
    ancestors = [directory, *directory.parents]
    if directory.is_relative_to(ROOT) or any((parent / ".git").exists() for parent in ancestors):
        raise ValueError("Secrets must be stored outside the scenario and repository.")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "nt":
        script = (
            "$ErrorActionPreference='Stop';"
            "$sid=[System.Security.Principal.WindowsIdentity]::GetCurrent().User;"
            "$acl=Get-Acl -LiteralPath $env:ABC_STAFF_PRIVATE_DIR;"
            "$acl.SetAccessRuleProtection($true,$false);"
            "foreach($entry in @($acl.Access)){$null=$acl.RemoveAccessRuleSpecific($entry)};"
            "$rule=[System.Security.AccessControl.FileSystemAccessRule]::new("
            "$sid,'FullControl','ContainerInherit,ObjectInherit','None','Allow');"
            "$acl.AddAccessRule($rule);Set-Acl -LiteralPath $env:ABC_STAFF_PRIVATE_DIR -AclObject $acl"
        )
        result = subprocess.run(
            ["pwsh", "-NoProfile", "-NonInteractive", "-Command", script],
            env=os.environ | {"ABC_STAFF_PRIVATE_DIR": str(directory)},
            capture_output=True, text=True, timeout=30, check=False,
        )
        if result.returncode:
            raise RuntimeError("Could not restrict the staff secret directory; no secrets written.")
    else:
        directory.chmod(0o700)
    return directory


def private_write(path: Path, value: dict) -> None:
    """Atomic private write; parent must already be owner-only."""
    temporary = path.with_name(path.name + ".new")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False)
            stream.write("\n")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def password_hash(password: str) -> str:
    """ASP.NET Identity V3 format: PBKDF2-HMAC-SHA512, random salt, 210,000 iterations."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha512", password.encode(), salt, ITERATIONS, dklen=32)
    return base64.b64encode(b"\x01" + struct.pack(">III", 2, ITERATIONS, len(salt)) + salt + digest).decode()


def validate(config: dict) -> None:
    """Reject incomplete or legacy configuration without displaying its contents."""
    if (len(base64.b64decode(config["SigningKey"], validate=True)) < 32
            or not config["Generation"] or not config["Employees"]):
        raise ValueError("Invalid synthetic staff configuration.")
    ids = set()
    for account in config["Employees"]:
        if (account["EmployeeId"] in ids or not account["EmployeeId"]
                or account["Role"] not in ("Manager", "Host", "Server", "Kitchen")
                or not account["Floors"] or any(f not in range(1, 6) for f in account["Floors"])):
            raise ValueError("Invalid synthetic employee scope.")
        ids.add(account["EmployeeId"])
        encoded = base64.b64decode(account["PasswordHash"], validate=True)
        if len(encoded) != 61 or encoded[:1] != b"\x01" or struct.unpack(">III", encoded[1:13]) != (2, ITERATIONS, 16):
            raise ValueError("Expected ASP.NET Identity V3 PBKDF2-SHA512 hashes.")


def install(directory: Path, reset_all: bool = False) -> Path:
    """Reuse existing credentials, or explicitly reset all accounts and revoke old installation proofs."""
    directory = private_directory(directory)
    runtime = directory / "staff-auth.json"
    credentials = directory / "demo-passwords.json"
    if runtime.exists() and credentials.exists() and not reset_all:
        validate(json.loads(runtime.read_text(encoding="utf-8")))
        return runtime
    if (runtime.exists() or credentials.exists()) and not reset_all:
        raise ValueError("Incomplete installation; use --reset-all to rotate both private files.")
    policy = json.loads((ROOT / "src/Restaurant.Web/SeedData/catalog.json").read_text(encoding="utf-8"))[1]
    people = {p["Id"]: p["Name"] for p in policy["Provenance"]["People"]}
    employees, passwords = [], []
    for employee_id, person_id, role, floors in (
        ("manager-001", "manager-001", "Manager", [1, 2, 3, 4, 5]),
        ("host-001", "host-001", "Host", [3]),
        ("server-001", "host-001", "Server", [3]),
        ("kitchen-001", "kitchen-001", "Kitchen", [3]),
    ):
        password = secrets.token_urlsafe(24)
        employees.append({
            "EmployeeId": employee_id, "Name": people[person_id], "Role": role,
            "Floors": floors, "PasswordHash": password_hash(password),
        })
        passwords.append({"EmployeeId": employee_id, "Password": password})
    config = {
        "SigningKey": base64.b64encode(secrets.token_bytes(32)).decode(),
        "Generation": secrets.token_hex(16), "Employees": employees,
    }
    validate(config)
    private_write(credentials, {"DemoOnly": True, "Employees": passwords})
    private_write(runtime, config)
    return runtime


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, help="Dedicated owner-only directory outside any checkout.")
    parser.add_argument("--reset-all", action="store_true", help="Rotate all passwords and the installation signing key.")
    parser.add_argument("--verify", action="store_true", help="Validate STAFF_AUTH_FILE locally; never invokes az/azd.")
    args = parser.parse_args()
    if args.verify:
        if args.reset_all or args.directory:
            parser.error("--verify only consumes STAFF_AUTH_FILE.")
        path = os.environ.get("STAFF_AUTH_FILE")
        if not path:
            parser.error("Set STAFF_AUTH_FILE to the private local staff-auth.json; organizational IDs are not needed.")
        validate(json.loads(Path(path).read_text(encoding="utf-8")))
        print("Synthetic staff configuration verified locally. No directory or Azure operations performed.")
    else:
        if not args.directory:
            parser.error("--directory is required for local installation.")
        install(args.directory, args.reset_all)
        print("Synthetic staff files prepared in the protected operator directory. No secrets printed; no Azure operations.")


if __name__ == "__main__":
    main()
