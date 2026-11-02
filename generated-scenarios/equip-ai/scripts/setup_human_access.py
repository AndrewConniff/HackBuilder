"""Prepare private desktop credentials and execute only the separately approved guest installation."""

import base64
from contextlib import ExitStack
import hashlib
import json
import secrets

from install_identity import command, save
from private_runner import GROUP, ROOT, SUBSCRIPTION, invoke, stage_artifact
from validate_live import values


def main() -> None:
    config = values()
    if config.get("EQUIP_ENABLE_HUMAN_MANAGEMENT") != "true":
        raise ValueError("Human access is not enabled under the separate scope approval.")
    bastion = command(["az", "network", "bastion", "show", "--subscription", SUBSCRIPTION,
                       "--resource-group", GROUP, "--name", "bas-equip-equip-ai"])
    if (bastion["provisioningState"] not in ("Creating", "Updating", "Succeeded")
            or bastion["sku"]["name"] != "Standard" or not bastion["enableTunneling"]):
        raise ValueError("The approved Standard Bastion with native tunneling must exist; failed access provisioning is not ready.")
    path = ROOT / ".private" / "management-access.json"
    if path.exists():
        credentials = json.loads(path.read_text())
        if credentials.get("vmName") != "vm-equip-management-equip-ai" or credentials.get("username") != "equipoperator":
            raise ValueError("Private desktop notes do not match the approved host.")
    else:
        credentials = {
            "vmName": "vm-equip-management-equip-ai", "username": "equipoperator",
            "password": secrets.token_urlsafe(32), "bastionName": "bas-equip-equip-ai",
            "credentialHandling": "VM-local desktop only; separate from sample-app and own-user Azure login.",
        }
        save(path, credentials)
    seed = json.dumps({key: credentials[key] for key in ("username", "password")}).encode()
    guest = (ROOT / "scripts" / "desktop_guest.py").read_bytes()
    helper = (ROOT / "scripts" / "runner_guest.py").read_bytes()
    artifacts = [(hashlib.sha256(payload).hexdigest(), payload) for payload in (seed, guest, helper)]
    with ExitStack() as cleanup:
        for digest, payload in artifacts:
            stage_artifact("app-equip-web-equipai-kex72v", digest, payload)
            cleanup.callback(stage_artifact, "app-equip-web-equipai-kex72v", digest, None)
        seed_digest, guest_digest, helper_digest = [item[0] for item in artifacts]
        bootstrap = f'''
import pathlib,urllib.request,urllib.parse,json,hashlib,subprocess
root=pathlib.Path("/var/lib/equip-ai-desktop")
root.mkdir(mode=0o700,exist_ok=True)
query=urllib.parse.urlencode({{"api-version":"2018-02-01","resource":"https://management.azure.com/"}})
request=urllib.request.Request("http://169.254.169.254/metadata/identity/oauth2/token?"+query,headers={{"Metadata":"true"}})
with urllib.request.build_opener(urllib.request.ProxyHandler({{}})).open(request,timeout=30) as response:
    bearer=json.load(response)["access_token"]
for digest,name in [("{guest_digest}","desktop_guest.py"),("{helper_digest}","runner_guest.py")]:
    request=urllib.request.Request("https://app-equip-web-equipai-kex72v.scm.azurewebsites.net/api/vfs/data/equip-ai-"+digest+".zip",
        headers={{"Authorization":"Bearer "+bearer}})
    with urllib.request.urlopen(request,timeout=90) as response: data=response.read()
    if hashlib.sha256(data).hexdigest()!=digest: raise ValueError("Guest setup digest mismatch.")
    (root/name).write_bytes(data)
result=subprocess.run(["python3",str(root/"desktop_guest.py"),"{seed_digest}"],capture_output=True,text=True,timeout=4200)
print(result.stdout[-2800:])
if result.returncode: raise RuntimeError("Desktop setup failed: "+result.stderr[-1000:])
'''
        encoded = base64.b64encode(bootstrap.encode()).decode()
        result = invoke(f"set -eu\numask 077\nprintf '%s' '{encoded}' | base64 -d | python3\n")
        save(ROOT / "local-evidence" / "resume-20261028" / "desktop-installation.json", {"output": result})
        if "EQUIP_DESKTOP_READY" not in result:
            raise RuntimeError("Private desktop installation failed; inspect redacted evidence.")
    print("Private desktop installed; credentials are in the protected management access file. Human Azure sign-in still required.")


if __name__ == "__main__":
    main()
