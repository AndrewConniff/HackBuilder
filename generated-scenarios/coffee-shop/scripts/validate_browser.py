"""Exercise the deployed manager UI with real local login and agent calls; never capture credentials."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import Error, expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
URL = "https://web-fc-keegvmxonq3wc.azurewebsites.net/"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorized", action="store_true")
    args = parser.parse_args()
    if not args.authorized:
        parser.error("Recorded scenario runtime-test authorization is required.")
    evidence = ROOT / "evidence"
    results: dict = {
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "applicationUrl": URL,
        "status": "running",
        "checks": {},
        "screenshots": [],
    }
    step = "opening the public login page"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            page.set_default_timeout(120000)
            page.goto(URL)
            expect(page.locator("#login")).to_be_visible()
            expect(page.locator("#stores button")).to_have_count(0)
            page.screenshot(path=str(evidence / "browser-login.png"), full_page=True)
            results["screenshots"].append("evidence/browser-login.png")
            for username, variable, stores in [
                ("storeman001", "COFFEE_STORE_PASSWORD", 1),
                ("petender", "COFFEE_AREA_PASSWORD", 2),
            ]:
                step = f"signing in as {username}"
                page.locator("#username").fill(username)
                page.locator("#password").fill(os.environ[variable])
                page.locator("#signin").click()
                expect(page.locator("#login")).to_be_hidden()
                expect(page.locator("#password")).to_have_value("")
                expect(page.locator("#identity")).to_have_text(username)
                expect(page.locator("#stores button")).to_have_count(stores)
                expect(page.locator("#store-title")).to_contain_text("Harbor")
                expect(page.locator("#metrics")).to_contain_text("$1,000.00")
                if username == "storeman001":
                    step = "checking the scoped store workspace"
                    assert page.evaluate("async () => (await fetch('/api/stores/002')).status") == 403
                    page.locator("#draft").click()
                    expect(page.locator("#order")).to_contain_text("$230.35")
                    page.screenshot(path=str(evidence / "browser-store001.png"), full_page=True)
                    results["screenshots"].append("evidence/browser-store001.png")
                    results["checks"]["storeUiAndCrossStoreDenial"] = True
                else:
                    step = "running the area-manager daily close"
                    page.locator("#chat").click()
                    expect(page.locator("#answer .receipt")).to_have_count(3, timeout=100000)
                    expect(page.locator("#status")).to_contain_text("Completed")
                    expect(page.locator("#status")).to_contain_text("$1,485.00")
                    receipts = page.locator("#answer small").all_text_contents()
                    assert all(receipt.startswith("Response resp_") for receipt in receipts), receipts
                    results["agentReceipts"] = receipts
                    page.screenshot(path=str(evidence / "browser-area-close.png"), full_page=True)
                    results["screenshots"].append("evidence/browser-area-close.png")
                    results["checks"]["areaUiAndRealAgentClose"] = True
                page.locator("#signout").click()
                expect(page.locator("#login")).to_be_visible()
                expect(page.locator("#stores button")).to_have_count(0)
            browser.close()
        results["status"] = "passed"
        return 0
    except (AssertionError, Error, KeyError) as error:
        results["status"] = "failed"
        results["failure"] = f"{type(error).__name__} while {step}; browser error text omitted to protect login inputs."
        print(f"Browser acceptance failed: {results['failure']}")
        return 1
    finally:
        (evidence / "browser-checks.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": results["status"], "checks": results["checks"]}))


if __name__ == "__main__":
    raise SystemExit(main())
