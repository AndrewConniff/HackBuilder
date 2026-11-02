"""Local synthetic installation checks; no cloud execution or real installed credentials."""

import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import setup_staff as setup


class StaffInstallationTests(unittest.TestCase):
    def test_install_reuses_fixtures_hashes_passwords_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = setup.install(Path(directory))
            before = runtime.read_bytes()
            self.assertEqual(runtime, setup.install(Path(directory)))
            self.assertEqual(before, runtime.read_bytes())
            config = json.loads(before)
            passwords = json.loads((Path(directory) / "demo-passwords.json").read_text())
            self.assertEqual({"Manager", "Host", "Server", "Kitchen"}, {a["Role"] for a in config["Employees"]})
            for account, credentials in zip(config["Employees"], passwords["Employees"], strict=True):
                encoded = base64.b64decode(account["PasswordHash"])
                self.assertEqual(encoded[29:], hashlib.pbkdf2_hmac(
                    "sha512", credentials["Password"].encode(), encoded[13:29], 210_000, dklen=32))
                self.assertNotIn(credentials["Password"], before.decode())
            names = {p["Name"] for p in json.loads(
                (ROOT / "src/Restaurant.Web/SeedData/catalog.json").read_text())[1]["Provenance"]["People"]}
            self.assertTrue(all(a["Name"] in names for a in config["Employees"]))
            if os.name != "nt":
                self.assertEqual(0o700, Path(directory).stat().st_mode & 0o777)
                self.assertEqual(0o600, runtime.stat().st_mode & 0o777)
            else:
                result = subprocess.run(["icacls", directory], capture_output=True, text=True, check=True)
                # No inherited ACEs survive; a new ACL contains only the current operator.
                self.assertNotIn("(I)", result.stdout)

    def test_explicit_reset_rotates_passwords_key_and_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = setup.install(Path(directory))
            before = json.loads(runtime.read_bytes())
            setup.install(Path(directory), reset_all=True)
            after = json.loads(runtime.read_bytes())
            for key in ("Generation", "SigningKey", "Employees"):
                self.assertNotEqual(before[key], after[key])

    def test_incomplete_install_and_checkout_secret_output_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "demo-passwords.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                setup.install(Path(directory))
        with self.assertRaisesRegex(ValueError, "outside"):
            setup.private_directory(ROOT / "evidence" / "should-not-exist")

    def test_verification_hook_has_no_azure_or_directory_dependencies_and_no_secret_output(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = setup.install(Path(directory))
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/setup_staff.py"), "--verify"],
                env=os.environ | {"STAFF_AUTH_FILE": str(runtime)},
                capture_output=True, text=True, check=True,
            )
            self.assertIn("No directory or Azure operations", result.stdout)
            self.assertNotIn(json.loads(runtime.read_bytes())["SigningKey"], result.stdout + result.stderr)
        yaml = (ROOT / "azure.yaml").read_text()
        self.assertNotIn("setup_staff.py", yaml)
        self.assertIn("install_reference.py", yaml)

    def test_legacy_directory_entry_point_fails_closed_without_subprocess(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/setup_identity.py"), "--authorize-directory-install"],
            capture_output=True, text=True,
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("--scope", result.stderr)

    def test_denied_acl_setup_does_not_write_credentials(self):
        if os.name != "nt":
            self.skipTest("Windows ACL denial contract")
        with tempfile.TemporaryDirectory() as directory, patch.object(setup.subprocess, "run") as run:
            run.return_value.returncode = 1
            with self.assertRaisesRegex(RuntimeError, "no secrets written"):
                setup.install(Path(directory))
            self.assertEqual([], list(Path(directory).iterdir()))


if __name__ == "__main__":
    unittest.main()
