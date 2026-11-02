"""Local-only unauthenticated browser layout/denial evidence; not deployed acceptance."""
import json
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1360, "height": 1000})
    response = page.goto("http://127.0.0.1:5187/", wait_until="networkidle")
    assert response.status == 200
    assert page.title() == "Adatum Corporation | Campaign Control"
    assert page.locator("#identity").inner_text().startswith("HTTP 401")
    assert page.get_by_role("heading", name="Control rules").count() == 1
    denied = page.request.get("http://127.0.0.1:5187/api/cases")
    assert denied.status == 401
    page.screenshot(path=str(root / "evidence/local-ui-preview.png"), full_page=True)
    browser.close()
result = {"checkedAtUtc": datetime.now(timezone.utc).isoformat(), "evidenceType": "local-unauthenticated-preview",
          "landingPageStatus": 200, "anonymousCasesStatus": 401, "browser": "Chromium",
          "screenshot": "evidence/local-ui-preview.png", "deployedRuntimeAcceptance": False}
(root / "evidence/local-ui-check.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result))
