"""Exercise actual Razor output in Chromium with explicitly intercepted offline API fixtures."""

import json
import os
from pathlib import Path

from playwright.sync_api import Route, expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
UI = Path(os.environ.get("ABCBUILDER_APPLICATION_UI_EXPORT", ROOT / ".application-evidence" / "ui"))
WEB = ROOT / "src" / "MobilityCommercial.Web" / "wwwroot"


def main() -> None:
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for width in (1280, 390):
            for mode in ("success", "error", "empty", "handoff-error"):
                page = browser.new_page(viewport={"width": width, "height": 900})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))

                def route_request(route: Route) -> None:
                    path = route.request.url.removeprefix("http://application.test")
                    if path == "/":
                        route.fulfill(path=str(UI / "index.html"), content_type="text/html")
                    elif path in ("/app.css", "/app.js"):
                        route.fulfill(path=str(WEB / path[1:]))
                    elif path == "/favicon.ico":
                        route.fulfill(status=204)
                    elif path.startswith("/api/"):
                        if mode == "error" or (mode == "handoff-error" and path == "/api/handoffs"):
                            route.fulfill(status=503, json={
                                "code": "azure_dependency_unavailable", "correlationId": "explicit-ui-test"
                            })
                        elif path == "/api/receipts/verify":
                            route.fulfill(json={"valid": True})
                        elif path == "/api/handoffs":
                            route.fulfill(json=json.loads((UI / "receipt.json").read_text()))
                        else:
                            name = path.removeprefix("/api/") + ".json"
                            route.fulfill(json=[] if mode == "empty" else
                                          json.loads((UI / name).read_text()))
                    else:
                        raise AssertionError(f"Unexpected UI request: {path}")

                page.route("**/*", route_request)
                page.goto("http://application.test/")
                expect(page.get_by_role("heading", level=1)).to_be_visible()
                if mode == "error":
                    expect(page.get_by_role("status")).to_contain_text("No local or mock fallback")
                    expect(page.get_by_role("button", name="Create review packet")).to_be_disabled()
                elif mode == "empty":
                    expect(page.get_by_role("status")).to_contain_text("No opportunities")
                else:
                    expect(page.get_by_role("status")).to_contain_text("Versioned synthetic evidence loaded")
                    page.get_by_label("Synthetic opportunity", exact=True).select_option("opp-002")
                    page.get_by_role("button", name="Create review packet").click()
                    if mode == "handoff-error":
                        expect(page.get_by_role("status")).to_contain_text("azure_dependency_unavailable")
                        expect(page.locator("#brief")).to_contain_text("No completed packet")
                        expect(page.locator("#verify")).to_be_disabled()
                    else:
                        expect(page.get_by_role("status")).to_contain_text("Packet ready for human review")
                        expect(page.locator("#trace-rows tr")).to_have_count(5)
                        page.get_by_role("button", name="Verify packet integrity").click()
                        expect(page.get_by_role("status")).to_contain_text("Integrity verified")
                page.get_by_role("link", name="Marketing brief", exact=True).click()
                expect(page.get_by_role("link", name="Marketing brief", exact=True)).to_have_attribute(
                    "aria-current", "page"
                )
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
                    f"Page overflow: width={width}, mode={mode}"
                )
                page.keyboard.press("Tab")
                assert not errors, errors
                page.screenshot(path=str(UI / f"{width}-{mode}.png"), full_page=True)
                results.append({"width": width, "mode": mode, "passed": True})
                page.close()
        browser.close()
    (UI / "browser-checks.json").write_text(json.dumps({
        "evidenceType": "offline_ui_test_with_intercepted_api_fixtures",
        "liveFoundryVerified": False, "checks": results
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Passed {len(results)} Chromium desktop/mobile UI cases; intercepted test APIs, not live agents.")


if __name__ == "__main__":
    main()
