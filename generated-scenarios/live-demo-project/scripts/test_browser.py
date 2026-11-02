"""Exercise real local HTTPS, account isolation and human takeover; never simulate Foundry success."""

import json
import os
import shutil
import socket
import ssl
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    """Run a bounded owned web process and persist local-only browser evidence."""
    project = Path(__file__).resolve().parents[1]
    web = project / "src" / "Brokerage.Web"
    temporary = Path(tempfile.mkdtemp(prefix="brokerage-browser-"))
    environment = {
        **os.environ,
        "ASPNETCORE_ENVIRONMENT": "Development",
        "DataPath": str(temporary / "data"),
        "PrivateAccessPath": str(temporary / "private"),
    }
    dll = web / "bin" / "Debug" / "net10.0" / "Brokerage.Web.dll"
    process = None
    try:
        subprocess.run(["dotnet", str(dll), "--initialize"], cwd=web, env=environment, check=True, capture_output=True)
        with socket.socket() as available:
            available.bind(("127.0.0.1", 0))
            port = available.getsockname()[1]
        base = f"https://127.0.0.1:{port}"
        environment["ASPNETCORE_URLS"] = base
        with (temporary / "server.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(["dotnet", str(dll)], cwd=web, env=environment, stdout=log, stderr=log)
            for attempt in range(60):
                if process.poll() is not None:
                    raise RuntimeError("Owned web process exited: " + (temporary / "server.log").read_text())
                try:
                    with urllib.request.urlopen(base + "/Login", context=ssl._create_unverified_context()) as response:
                        if response.status == 200:
                            break
                except (urllib.error.URLError, ConnectionError):
                    time.sleep(0.5)
            else:
                raise TimeoutError("Owned HTTPS application did not become ready.")
            participant = json.loads((temporary / "private" / "participant-access.json").read_text())
            coach = json.loads((temporary / "private" / "coach-access.json").read_text())
            images = project / "demoguide" / "images"
            images.mkdir(parents=True, exist_ok=True)
            checks = []
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel="msedge", headless=True)
                customer_context = browser.new_context(ignore_https_errors=True)
                customer = customer_context.new_page()
                customer.goto(base)
                assert customer.url.endswith("/Login?ReturnUrl=%2F"), customer.url
                checks.append("anonymous redirected to local sign-in")
                customer.get_by_label("Username").fill(participant["username"])
                customer.get_by_label("Password", exact=True).fill(participant["password"])
                customer.get_by_role("button", name="Sign in", exact=True).click()
                customer.get_by_role("heading", name="Your conversation").wait_for()
                checks.append("participant sign-in and customer workflow")
                customer.goto(base + "/Desk")
                assert customer.get_by_role("heading", name="Access denied").is_visible()
                checks.append("participant cannot access representative desk")
                customer.goto(base)
                customer.get_by_label("Your service question").fill("How do I open an investment account?")
                with customer.expect_response(lambda response: "?handler=Ask" in response.url) as failure:
                    customer.get_by_role("button", name="Ask company knowledge").click()
                assert failure.value.status == 503
                assert customer.get_by_role("alert").is_visible()
                checks.append("missing Foundry configuration returns visible 503, not mock success")
                customer.get_by_role("button", name="Request a representative").click()
                assert customer.get_by_text("AI answers are paused.", exact=False).is_visible()
                customer.get_by_label("Message for your representative").fill("Please explain the onboarding service.")
                customer.get_by_role("button", name="Send to representative").click()
                checks.append("explicit takeover and customer human-queue message")
                representative_context = browser.new_context(ignore_https_errors=True)
                representative = representative_context.new_page()
                representative.goto(base + "/Login")
                representative.get_by_label("Username").fill(coach["username"])
                representative.get_by_label("Password", exact=True).fill(coach["password"])
                representative.get_by_role("button", name="Sign in", exact=True).click()
                representative.get_by_role("button", name="Claim case").click()
                representative.get_by_label("Representative reply").fill(
                    "I can help explain the service and required next steps."
                )
                representative.get_by_role("button", name="Send reply").click()
                customer.reload()
                assert customer.get_by_text("I can help explain the service and required next steps.").is_visible()
                checks.append("human claims, replies and customer reads durable response")
                customer.screenshot(path=str(images / "local-customer-desktop.png"), full_page=True)
                customer.set_viewport_size({"width": 390, "height": 844})
                assert customer.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                customer.screenshot(path=str(images / "local-customer-mobile.png"), full_page=True)
                checks.append("390px layout has no horizontal overflow")
                csrf = customer_context.request.post(base + "/?handler=Escalate", form={"revision": "0"})
                assert csrf.status == 400
                checks.append("missing CSRF token denied")
                customer.get_by_role("button", name="Sign out", exact=True).click()
                customer.goto(base)
                assert "/Login" in customer.url
                checks.append("logout removes customer browser access")
                browser.close()
            print(json.dumps({"status": "passed", "evidenceType": "local-browser-not-Azure-runtime",
                              "checks": checks}, indent=2))
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=15)
        shutil.rmtree(temporary)


if __name__ == "__main__":
    main()
