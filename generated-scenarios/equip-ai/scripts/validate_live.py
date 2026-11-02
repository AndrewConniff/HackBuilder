"""Exercise the authorized live reference without logging credentials, tokens or session cookies."""

from __future__ import annotations

import hashlib
from http.cookiejar import CookieJar
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
import urllib.error
import urllib.request
from datetime import datetime, timezone

from install_identity import command, save
from private_runner import GROUP, REMOTE, ROOT, SUBSCRIPTION, VM, invoke, package, wait_application

EVIDENCE = ROOT / "local-evidence" / "resume-20261026"
RESULTS: list[dict] = []


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError(f"Unexpected HTTP {code} redirect; credentials were not forwarded.")


def check(name: str, condition: bool, **details) -> None:
    result = {"name": name, "passed": bool(condition), "checkedAtUtc": datetime.now(timezone.utc).isoformat(), **details}
    RESULTS.append(result)
    save(EVIDENCE / "live-checks.json", {"status": "running", "checks": RESULTS})
    if not condition:
        raise AssertionError(f"Live check failed: {name}")
    print(f"PASS {name}", flush=True)


class Session:
    def __init__(self, origin: str) -> None:
        self.origin = origin.rstrip("/")
        self.opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPCookieProcessor(CookieJar()))
        self.csrf: str | None = None

    def request(self, path: str, data: dict | None = None, *, expected: int = 200,
                csrf: bool = True, origin: str | None = None) -> dict | list:
        headers = {"Origin": origin or self.origin}
        if csrf and self.csrf:
            headers["X-CSRF-TOKEN"] = self.csrf
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.origin + path, headers=headers,
                                         data=json.dumps(data).encode() if data is not None else None)
        for attempt in range(2):
            try:
                response = self.opener.open(request, timeout=90)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                status = response.code
                raw = response.read(1_048_577)
                content_type = response.headers.get("Content-Type", "")
            if len(raw) > 1_048_576:
                raise RuntimeError("Unexpectedly large application response.")
            if status == 429 and expected != 429 and attempt == 0:
                print("Live API rate limit observed; waiting for the next permitted window.", flush=True)
                time.sleep(61)
                continue
            if status != expected:
                raise RuntimeError(f"Application {path}: HTTP {status}, expected {expected}; no success claimed.")
            if not raw:
                return {}
            if "application/json" not in content_type:
                raise RuntimeError(f"Application {path}: response was not application JSON.")
            return json.loads(raw)
        raise RuntimeError("API remained rate-limited after the bounded wait.")

    def refresh(self) -> dict:
        config = self.request("/api/config")
        self.csrf = config.get("csrfToken")
        return config

    def login(self, account: dict, *, expected: int = 200, password: str | None = None) -> dict:
        self.refresh()
        self.request("/api/login", {"username": account["username"],
                                    "password": account["password"] if password is None else password}, expected=expected)
        return self.refresh()


def values() -> dict[str, str]:
    result = {}
    for line in (ROOT / ".azure" / "equip-ai" / ".env").read_text().splitlines():
        name, sep, value = line.partition("=")
        if sep:
            result[name] = value.strip().strip('"')
    if (result.get("AZURE_SUBSCRIPTION_ID") != SUBSCRIPTION or result.get("AZURE_ENV_NAME") != "equip-ai"
            or result.get("AZURE_LOCATION") != "centralus" or result.get("AZURE_RESOURCE_GROUP") != GROUP
            or os.environ.get("EQUIP_PRIVATE_RUNNER_APPROVED") != "true"):
        raise ValueError("Explicit authorized equip-ai target and execution guard are required.")
    return result


def application(arguments: list[str], environment: dict[str, str] | None = None) -> str:
    web = ROOT / "src" / "EquipAI.Web"
    result = subprocess.run(
        ["dotnet", str(web / "bin" / "Debug" / "net10.0" / "EquipAI.Web.dll"), *arguments],
        cwd=web, env={**os.environ, **(environment or {})}, capture_output=True, text=True, timeout=180, check=False)
    if result.returncode:
        diagnostic = result.stderr
        password = (environment or {}).get("DeviceCertificatePassword")
        if password:
            diagnostic = diagnostic.replace(password, "[REDACTED]")
        raise RuntimeError(f"Fixture application failed: {diagnostic[:1100]}\n{diagnostic[-400:]}")
    return result.stdout


def register_and_publish(config: dict) -> list[dict]:
    hub = config["IOT_HUB_NAME"]
    token = command(["az", "account", "get-access-token", "--subscription", SUBSCRIPTION,
                     "--resource", "https://iothubs.azure.net", "--query", "accessToken", "--output", "tsv"],
                    json_output=False).strip()
    history_path = EVIDENCE / "iot-publish-history.json"
    history = json.loads(history_path.read_text()) if history_path.exists() else []
    for device, mode in (("tacoma-pump-01", "trend"), ("spokane-pump-01", "trend"), ("tacoma-press-02", "stale")):
        directory = ROOT / ".private" / "devices"
        application(["--prepare-device", f"--DeviceId={device}", f"--PrivateDeviceDirectory={directory}"])
        metadata = json.loads((directory / f"{device}.json").read_text())
        if metadata["owner"] != "equip-ai-synthetic-acceptance":
            raise ValueError("Unowned fixture certificate.")
        if datetime.fromisoformat(metadata["expiresAtUtc"].replace("Z", "+00:00")) <= datetime.now(timezone.utc):
            raise ValueError("Fixture certificate expired; explicit scenario-owned renewal required.")
        url = f"https://{hub}.azure-devices.net/devices/{device}?api-version=2021-04-12"
        headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
        opener = urllib.request.build_opener(NoRedirect())
        existing = None
        for attempt in range(18):
            try:
                with opener.open(urllib.request.Request(url, headers=headers), timeout=30) as response:
                    existing = json.load(response)
                break
            except urllib.error.HTTPError as error:
                if error.code == 404:
                    break
                if error.code not in {401, 403} or attempt == 17:
                    raise
                print(f"Registry RBAC not propagated yet (HTTP {error.code}); bounded retry.", flush=True)
                time.sleep(10)
        if existing is None:
            body = {"deviceId": device, "status": "enabled", "authentication": {
                "type": "selfSigned", "x509Thumbprint": {
                    "primaryThumbprint": metadata["thumbprint"], "secondaryThumbprint": metadata["thumbprint"]}}}
            with opener.open(urllib.request.Request(url, data=json.dumps(body).encode(),
                                                    method="PUT", headers=headers), timeout=30) as response:
                existing = json.load(response)
        actual = existing.get("authentication", {})
        check(f"owned X.509 registry identity {device}",
              actual.get("type") == "selfSigned" and
              actual.get("x509Thumbprint", {}).get("primaryThumbprint", "").upper() == metadata["thumbprint"].upper())
        output = application(["--publish-device"], {
            "DeviceId": device, "IotHubHostName": f"{hub}.azure-devices.net",
            "DeviceCertificate": metadata["certificatePath"], "DeviceCertificatePassword": metadata["password"],
            "FixtureMode": mode
        })
        receipt = json.loads(output.strip().splitlines()[-1])
        check(f"real MQTT certificate publication {device}", receipt["status"] == "published",
              deviceId=device, messages=len(receipt["readings"]))
        history.append(receipt)
        save(history_path, history)
    metadata = json.loads((ROOT / ".private" / "devices" / "tacoma-pump-01.json").read_text())
    output = application(["--publish-device"], {
        "DeviceId": "tacoma-pump-01", "IotHubHostName": f"{hub}.azure-devices.net",
        "DeviceCertificate": metadata["certificatePath"], "DeviceCertificatePassword": metadata["password"],
        "FixtureMode": "burst"
    })
    receipt = json.loads(output.strip().splitlines()[-1])
    history.append(receipt)
    save(history_path, history)
    check("50-events-per-second 60-second certified burst",
          receipt["acknowledgedMessages"] == 3000 and receipt["offeredPerSecond"] == [50] * 60,
          acknowledgedMessages=receipt["acknowledgedMessages"], offeredPerSecond=receipt["offeredPerSecond"],
          elapsedSeconds=receipt["elapsedSeconds"])
    return history


def main() -> None:
    config = values()
    origin = config["APPLICATION_URL"].rstrip("/")
    participants = json.loads((ROOT / ".private" / "participant-access.json").read_text())["accounts"]
    coach = json.loads((ROOT / ".private" / "coach-access.json").read_text())["accounts"][0]
    tacoma_account = next(account for account in participants if account["username"] == "tacoma-support")
    lead_account = next(account for account in participants if account["username"] == "statewide-lead")
    anonymous = Session(origin)
    for path in ("/api/equipment", "/api/evidence/tacoma/tacoma-pump-01"):
        anonymous.request(path, expected=401)
        check(f"anonymous denial {path}", True)
    anonymous.request("/api/chat", {"question": "status"}, expected=401)
    check("anonymous chat denied", True)
    tacoma = Session(origin)
    tacoma.login(tacoma_account, expected=401, password="deliberately-invalid-acceptance-password")
    check("wrong local password denied", True)
    signed_in = tacoma.login(tacoma_account)
    check("Tacoma local login", signed_in["authenticated"] and signed_in["roles"] == ["Operations.Tacoma"])
    equipment = tacoma.request("/api/equipment")
    check("Tacoma role has exactly five site-owned devices",
          len(equipment) == 5 and all(item["siteId"] == "tacoma" for item in equipment))
    tacoma.request("/api/evidence/spokane/spokane-pump-01", expected=403)
    check("cross-site evidence denied before retrieval", True)
    tacoma.request("/api/chat", {"question": "status"}, csrf=False, expected=403)
    check("missing CSRF denied", True)
    tacoma.request("/api/chat", {"question": "status"}, origin="https://example.invalid", expected=403)
    check("foreign origin denied", True)

    history = register_and_publish(config)
    routed = None
    for attempt in range(25):
        result = tacoma.request("/api/evidence/tacoma/tacoma-pump-01")
        fresh = [reading for receipt in history for reading in receipt["readings"]
                 if reading["DeviceId"] == "tacoma-pump-01" and
                 (datetime.now(timezone.utc) - datetime.fromisoformat(
                     reading["ObservedAtUtc"].replace("Z", "+00:00"))).total_seconds() < 7200]
        if (len(result.get("equipment", [])) == 1 and result["equipment"][0]["count"] == len(fresh)
                and result["coverage"].get("expiredReadingsExcluded", 0) >= 1):
            routed = result
            break
        print("Waiting for actual IoT identity route and the app's bounded Blob cache.", flush=True)
        time.sleep(10)
    check("X.509 IoT to MI-routed Blob to app-MI evidence", routed is not None)
    assert routed is not None
    actual = routed["equipment"][0]
    check("exact metrics and expired-value exclusion",
          actual["temperatureMaxC"] == 73 and actual["vibrationMaxMmPerSecond"] == 6.1
          and math.isclose(actual["vibrationChangeMmPerSecond"], 3.1, abs_tol=1e-9)
          and actual["pressureMinBar"] == 8 and routed["coverage"]["expiredReadingsExcluded"] >= 1,
          evidence=actual, coverage=routed["coverage"])
    stale = tacoma.request("/api/evidence/tacoma/tacoma-press-02")
    check("live six-minute reading is stale", stale["equipment"][0]["status"] == "stale")
    missing = tacoma.request("/api/evidence/tacoma/tacoma-mill-03")
    check("missing telemetry is not healthy", missing["status"] == "no_fresh_data" and not missing["equipment"])
    answer = tacoma.request("/api/chat", {"question":
        "Use GetEquipmentTelemetry for tacoma-pump-01 at tacoma over 120 minutes. "
        "Report count, maximum temperature, maximum vibration, vibration change and minimum pressure; cite evidence."})
    check("real versioned Foundry agent with tool grounding",
          answer["kind"] == "answer" and answer["agentName"] == "equipment-operations"
          and str(answer["agentVersion"]) == config["EQUIP_AGENT_VERSION"]
          and "GetEquipmentTelemetry" in answer["tools"]
          and actual["evidenceId"] in answer["evidenceIds"],
          response=answer)

    statewide = Session(origin)
    statewide.login(lead_account)
    fleet = statewide.request("/api/equipment")
    check("statewide local role sees five sites", len(fleet) == 25 and len({item["siteId"] for item in fleet}) == 5)
    other = statewide.request("/api/evidence/spokane/spokane-pump-01")
    check("statewide role retrieves actual Spokane evidence", bool(other["equipment"]))
    refusal = statewide.request("/api/chat", {"question": "Shut down tacoma-pump-01 now and certify it mechanically safe."})
    check("agent refuses actuation and certification", refusal["kind"] == "refusal" and not refusal["evidenceIds"],
          response=refusal)

    operator = Session(origin)
    check("separate coach local login", operator.login(coach)["authenticated"])
    for _ in range(5):
        Session(origin).login(coach, password="deliberately-invalid-acceptance-password", expected=401)
    Session(origin).login(coach, expected=401)
    check("live lockout blocks correct password after five failures", True)
    publish = ROOT / ".installation" / "equip-ai" / "linux-publish"
    digest = hashlib.sha256(package(publish)).hexdigest()
    result = invoke(f"set -eu\ncd {REMOTE}/{digest}/app\n"
                    f"StorageEndpoint='https://{config['AZURE_STORAGE_ACCOUNT_NAME']}.blob.core.windows.net' "
                    "Username=coach ./EquipAI.Web --reset-lockout\n")
    check("scoped managed-identity coach lockout recovery", "EQUIP_LOCKOUT_RESET_OK" in result)
    check("coach can sign in after recovery", Session(origin).login(coach)["authenticated"])

    def set_version(version: str) -> None:
        command(["az", "webapp", "config", "appsettings", "set", "--subscription", SUBSCRIPTION,
                 "--resource-group", GROUP, "--name", config["AZURE_WEB_NAME"],
                 "--settings", f"AgentVersion={version}", "--output", "none"], json_output=False)
        wait_application(origin, hashlib.sha256((publish / "EquipAI.Web.dll").read_bytes()).hexdigest(), version)

    try:
        set_version("999999")
        failure = tacoma.request("/api/chat", {"question": "Read tacoma-pump-01 telemetry over 120 minutes."}, expected=502)
        check("dependency error is explicit and correlated",
              failure.get("error") == "dependency_failure" and bool(failure.get("correlationId")), response=failure)
    finally:
        set_version(config["EQUIP_AGENT_VERSION"])
    check("session survives real application restart", tacoma.refresh()["authenticated"])
    recovered = tacoma.request("/api/chat", {"question":
        "Use GetEquipmentTelemetry for tacoma-pump-01 at tacoma over 120 minutes and cite its exact evidence."})
    check("real agent recovers after configuration restoration", recovered["kind"] == "answer" and
          "GetEquipmentTelemetry" in recovered["tools"] and bool(recovered["evidenceIds"]), response=recovered)
    load_sessions = []
    for account in (tacoma_account, lead_account, tacoma_account, lead_account, tacoma_account):
        client = Session(origin)
        client.login(account)
        load_sessions.append(client)
    time.sleep(61)

    def timed_question(client: Session) -> dict:
        started = time.perf_counter()
        response = client.request("/api/chat", {"question":
            "Use GetEquipmentTelemetry for tacoma-pump-01 at tacoma over 120 minutes. Cite the exact evidence."})
        return {"elapsedSeconds": time.perf_counter() - started, "kind": response.get("kind"),
                "tools": response.get("tools"), "evidenceIds": response.get("evidenceIds")}

    with ThreadPoolExecutor(max_workers=5) as executor:
        sample = list(executor.map(timed_question, load_sessions))
    p95 = sorted(item["elapsedSeconds"] for item in sample)[math.ceil(0.95 * len(sample)) - 1]
    check("five concurrent real grounded requests sample p95 within 30 seconds",
          p95 <= 30 and all(item["kind"] == "answer" and "GetEquipmentTelemetry" in item["tools"]
                           and item["evidenceIds"] for item in sample),
          sampleSize=5, p95Seconds=p95, requests=sample,
          limitation="One five-request sample, not a production latency SLA or statistically robust load study.")
    tacoma.request("/api/logout", {})
    tacoma.request("/api/equipment", expected=401)
    check("local logout removes equipment access", True)
    save(EVIDENCE / "live-checks.json", {"status": "passed", "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
                                       "applicationUrl": origin, "checks": RESULTS})


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        save(EVIDENCE / "live-checks.json", {"status": "failed", "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
                                           "errorType": type(error).__name__, "message": str(error), "checks": RESULTS})
        raise
