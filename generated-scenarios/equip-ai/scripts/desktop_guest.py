"""Install the approved private Ubuntu desktop; never log passwords or Azure tokens."""

import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import socket
import ssl
import subprocess
import sys
import urllib.request

from runner_guest import download_artifact


def run(arguments: list[str], *, timeout: int = 1200, input_text: str | None = None) -> str:
    result = subprocess.run(arguments, capture_output=True, text=True, input=input_text,
                            timeout=timeout, env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"})
    if result.returncode:
        raise RuntimeError(f"Guest command {arguments[:2]} failed ({result.returncode}): {result.stderr[-1200:]}")
    return result.stdout


def setting(path: Path, name: str, value: str) -> None:
    text, count = re.subn(rf"(?m)^{re.escape(name)}=.*$", f"{name}={value}", path.read_text())
    if count != 1:
        raise ValueError(f"Expected one {name} in {path.name}.")
    path.write_text(text)


def main() -> None:
    if os.geteuid() != 0:
        raise PermissionError("Approved guest package setup requires Run Command root context.")
    if len(sys.argv) != 2 or not re.fullmatch(r"[a-f0-9]{64}", sys.argv[1]):
        raise ValueError("Supply the private credential seed digest, not a password.")
    seed = json.loads(download_artifact("app-equip-web-equipai-kex72v", sys.argv[1]))
    if seed.get("username") != "equipoperator" or len(seed.get("password", "")) < 32:
        raise ValueError("Unexpected local desktop account seed.")
    account = pwd.getpwnam(seed["username"])
    os_release = Path("/etc/os-release").read_text()
    if 'VERSION_ID="24.04"' not in os_release or 'ID=ubuntu' not in os_release:
        raise ValueError("Guest distribution differs from the reviewed Ubuntu 24.04 design.")
    run(["apt-get", "update"])
    run(["apt-get", "install", "-y", "--no-install-recommends", "ca-certificates", "curl", "gnupg"])
    key_path = Path("/etc/apt/keyrings/equip-microsoft.gpg")
    key_path.parent.mkdir(mode=0o755, exist_ok=True)
    with urllib.request.urlopen("https://packages.microsoft.com/keys/microsoft.asc", timeout=60) as response:
        key = response.read()
    result = subprocess.run(["gpg", "--dearmor"], input=key, capture_output=True, check=True, timeout=30)
    key_path.write_bytes(result.stdout)
    key_path.chmod(0o644)
    fingerprint = run(["gpg", "--show-keys", "--with-colons", str(key_path)])
    if "BC528686B50D79E339D3721CEB3E94ADBE1229CF" not in fingerprint:
        raise ValueError("Microsoft package signing key fingerprint differs from the reviewed source.")
    Path("/etc/apt/sources.list.d/azure-cli.list").write_text(
        "deb [arch=amd64 signed-by=/etc/apt/keyrings/equip-microsoft.gpg] "
        "https://packages.microsoft.com/repos/azure-cli/ noble main\n")
    edge_repository = Path("/etc/apt/sources.list.d/microsoft-edge.list")
    edge_source = (
        "deb [arch=amd64 signed-by=/etc/apt/keyrings/equip-microsoft.gpg] "
        "https://packages.microsoft.com/repos/edge stable main\n")
    edge_repository.write_text(edge_source)
    run(["apt-get", "update"])
    packages = ["xfce4", "xfce4-session", "xrdp", "xorgxrdp", "dbus-x11", "azure-cli", "microsoft-edge-stable"]
    run(["apt-get", "install", "-y", "--no-install-recommends", *packages], timeout=2400)
    edge_repository.write_text(edge_source)
    run(["usermod", "-aG", "ssl-cert", "xrdp"])
    setting(Path("/etc/xrdp/xrdp.ini"), "security_layer", "tls")
    setting(Path("/etc/xrdp/xrdp.ini"), "crypt_level", "high")
    setting(Path("/etc/xrdp/sesman.ini"), "AllowRootLogin", "false")
    session = Path(account.pw_dir) / ".xsession"
    session.write_text("exec startxfce4\n")
    session.chmod(0o700)
    os.chown(session, account.pw_uid, account.pw_gid)
    run(["chpasswd"], input_text=seed["username"] + ":" + seed["password"] + "\n")
    del seed
    ssh = run(["sshd", "-T"])
    if "passwordauthentication no" not in ssh:
        raise ValueError("SSH password authentication must remain disabled.")
    run(["systemctl", "enable", "xrdp"])
    run(["systemctl", "restart", "xrdp"])
    if run(["systemctl", "is-active", "xrdp"]).strip() != "active":
        raise RuntimeError("Private RDP did not start.")
    browser = run(["runuser", "-u", account.pw_name, "--", "microsoft-edge",
                   "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                   "--dump-dom", "data:text/html,<title>equip-management-render-probe</title>"], timeout=90)
    if "<title>equip-management-render-probe</title>" not in browser:
        raise RuntimeError("Installed browser did not render the test document.")
    addresses = {}
    for host in ("ai-equip-equipai-kex72v.services.ai.azure.com", "stequipequipaikex72vu7.blob.core.windows.net"):
        import ipaddress
        ip = socket.gethostbyname(host)
        if not ipaddress.ip_address(ip).is_private:
            raise RuntimeError("Private workload DNS resolved outside the VNet.")
        addresses[host] = ip
    free = os.statvfs("/").f_bavail * os.statvfs("/").f_frsize
    if free < 2 * 1024**3:
        raise RuntimeError("Less than 2 GiB remains after desktop installation; do not claim guest readiness.")
    print(json.dumps({
        "operation": "private-desktop-installation", "rdpActive": True,
        "browserRendered": True, "browserVersion": run(["microsoft-edge", "--version"]).strip(),
        "azureCliVersion": json.loads(run(["az", "version"]))["azure-cli"],
        "privateDns": addresses, "freeDiskBytes": free,
        "certificateSha256": hashlib.sha256(
            ssl.PEM_cert_to_DER_cert(Path("/etc/xrdp/cert.pem").read_text())).hexdigest(),
        "humanAzureSignInObserved": False, "deployingUserDataCrudObserved": False,
    }))
    print("EQUIP_DESKTOP_READY")


if __name__ == "__main__":
    main()
