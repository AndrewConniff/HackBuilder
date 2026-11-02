"""Verify the authorized deployed synthetic reference without recording passwords, cookies or access tokens."""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import shutil
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "https://web-fc-keegvmxonq3wc.azurewebsites.net"
SUBSCRIPTION = "efd64343-6ef4-4926-951f-d3229f38bd76"


class Session:
    """A cookie-bearing real HTTPS client; credentials and session tokens stay in memory."""

    def __init__(self) -> None:
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookies),
            urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        )
        self.csrf: str | None = None

    def request(self, path: str, body: dict | None = None, csrf: bool = True) -> tuple[int, object, float]:
        headers = {"Content-Type": "application/json"}
        if csrf and self.csrf:
            headers["X-CSRF-TOKEN"] = self.csrf
        request = urllib.request.Request(
            URL + path, data=json.dumps(body).encode() if body is not None else None, headers=headers,
        )
        start = time.perf_counter()
        try:
            response = self.opener.open(request, timeout=110)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            raw = response.read().decode()
            data = json.loads(raw) if "application/json" in response.headers.get("Content-Type", "") else raw
            return response.status, data, time.perf_counter() - start

    def login(self, username: str, password: str) -> None:
        code, session, _ = self.request("/api/session")
        assert code == 200 and isinstance(session, dict), (code, session)
        self.csrf = session["csrfToken"]
        code, result, _ = self.request("/api/auth/login", {"username": username, "password": password})
        assert code == 200, (code, result)
        code, session, _ = self.request("/api/session")
        assert code == 200 and isinstance(session, dict) and session["authenticated"], (code, session)
        self.csrf = session["csrfToken"]
        cookies = list(self.cookies)
        assert any(cookie.name == "__Host-CoffeeSession" and cookie.secure for cookie in cookies)


def direct_model() -> dict:
    token = subprocess.run(
        [shutil.which("az") or "az", "account", "get-access-token", "--subscription", SUBSCRIPTION,
         "--resource", "https://cognitiveservices.azure.com/", "--query", "accessToken", "--output", "tsv"],
        capture_output=True, text=True, check=True, timeout=60,
    ).stdout.strip()
    request = urllib.request.Request(
        "https://fc-coffee-shop-keegvmxo.openai.azure.com/openai/v1/responses",
        data=json.dumps({"model": "gpt-4.1-mini", "input": "Reply exactly COFFEE_MODEL_OK",
                         "max_output_tokens": 32, "store": False}).encode(),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        result = json.load(response)
    text = "".join(part.get("text", "") for output in result.get("output", [])
                   for part in output.get("content", []))
    assert result.get("status") == "completed" and "COFFEE_MODEL_OK" in text, result
    return {"responseId": result["id"], "model": result["model"], "status": result["status"], "text": text}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorized", action="store_true", help="Require actual recorded runtime-test authorization.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--branch-failure", action="store_true",
                      help="Expect a real margin-agent fault installed externally; never creates a fault.")
    mode.add_argument("--concurrent-closes", action="store_true",
                      help="Measure ten concurrent closes, including explicit admission rejections.")
    args = parser.parse_args()
    if not args.authorized:
        parser.error("Recorded scenario runtime-test authorization is required.")
    results: dict = {
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(), "applicationUrl": URL,
        "status": "running", "checks": {}, "evidence": {},
    }
    filename = ("live-branch-failure.json" if args.branch_failure else
                "live-concurrency.json" if args.concurrent_closes else "live-checks.json")
    try:
        store = Session()
        store.login("storeman001", os.environ["COFFEE_STORE_PASSWORD"])
        if args.branch_failure:
            code, data, elapsed = store.request("/api/chat", {"storeIds": ["001"], "question": "Explain margin"})
            assert code == 503 and isinstance(data, dict), (code, data)
            assert "agents" not in data and data.get("status") != "Completed", data
            results["evidence"]["branchFailure"] = {"httpStatus": code, "body": data, "elapsedSeconds": elapsed}
            results["checks"]["noSuccessfulCloseOnBranchFailure"] = True
            results["status"] = "passed"
            return 0

        anonymous = Session()
        assert anonymous.request("/api/stores/001")[0] == 401
        assert store.request("/api/stores")[1] == ["001"]
        assert store.request("/api/stores/002")[0] == 403
        assert store.request("/api/stores/003")[0] == 403
        assert store.request("/api/orders/draft", {"storeId": "002"})[0] == 403
        assert store.request("/api/orders/draft", {"storeId": "001"}, csrf=False)[0] == 400
        results["checks"]["negativeCase"] = True

        second = Session()
        second.login("storeman002", os.environ["COFFEE_STORE_PASSWORD"])
        assert second.request("/api/stores")[1] == ["002"]
        assert second.request("/api/stores/001")[0] == 403
        area = Session()
        area.login("petender", os.environ["COFFEE_AREA_PASSWORD"])
        assert area.request("/api/stores")[1] == ["001", "002"]
        assert area.request("/api/stores/003")[0] == 403
        results["checks"]["localLoginAndStoreIsolation"] = True

        if args.concurrent_closes:
            jobs = [(area, ["001", "002"])] * 4 + [(store, ["001"])] * 3 + [(second, ["002"])] * 3

            def close_stores(job: tuple[Session, list[str]]) -> tuple[int, object, float]:
                session, stores = job
                return session.request("/api/chat", {"storeIds": stores, "question": "Explain daily margin."})

            with ThreadPoolExecutor(max_workers=10) as pool:
                closes = list(pool.map(close_stores, jobs))
            samples = []
            for (session, stores), (code, body, elapsed) in zip(jobs, closes):
                assert code in {200, 409, 429}, (code, body)
                sample = {"httpStatus": code, "elapsedSeconds": elapsed, "stores": stores}
                if code == 200:
                    assert isinstance(body, dict) and body["status"] == "Completed", body
                    assert len(body["agents"]) == 3, body
                    expected_profit = 1485 if len(stores) == 2 else 1000 if stores == ["001"] else 485
                    assert body["profit"] == expected_profit, body
                    sample["responseIds"] = [agent["responseId"] for agent in body["agents"]]
                else:
                    assert not isinstance(body, dict) or "agents" not in body, body
                samples.append(sample)
            completed = [sample for sample in samples if sample["httpStatus"] == 200]
            assert completed, samples
            p95 = max(sample["elapsedSeconds"] for sample in completed) if len(completed) == 10 else None
            results["evidence"]["tenConcurrentCloses"] = {
                "count": 10, "completed": len(completed), "rejected": 10 - len(completed),
                "samples": samples, "allUsersP95Seconds": p95, "targetSeconds": 60,
                "targetPassed": len(completed) == 10 and p95 is not None and p95 < 60,
                "limitation": "Admission rejections do not count as successful closes or fast latency samples.",
            }
            results["checks"]["boundedAdmissionAndNoFalseSuccess"] = True
            results["status"] = "passed"
            return 0

        code, snapshot, _ = store.request("/api/stores/001")
        assert code == 200 and isinstance(snapshot, dict) and snapshot["ledger"]["profit"] == 1000, snapshot
        code, draft, _ = store.request("/api/orders/draft", {"storeId": "001"})
        assert code == 200 and isinstance(draft, dict) and draft["total"] == 230.35, draft
        assert all(line["sku"] != "oat-milk" for line in draft["lines"])
        path = f"/api/orders/001/{draft['draftId']}/approve"
        code, approved, _ = store.request(path, {"confirm": True})
        assert code == 200 and isinstance(approved, dict) and approved["status"] == "Approved", approved
        assert store.request(path, {"confirm": True})[1] == approved
        assert area.request(path, {"confirm": True})[1] == approved
        results["evidence"]["internalOrder"] = approved
        results["checks"]["ordersAndReplay"] = True

        results["evidence"]["model"] = direct_model()
        results["checks"]["modelInference"] = True
        code, close, elapsed = area.request("/api/chat", {
            "storeIds": ["001", "002"], "question": "Explain tomorrow's milk risk and today's sales margin.",
        })
        results["evidence"]["close"] = {"httpStatus": code, "elapsedSeconds": elapsed, "body": close}
        assert code == 200 and isinstance(close, dict), (code, close)
        assert close["status"] == "Completed" and close["profit"] == 1485 and close["netSales"] == 4200, close
        assert {receipt["agent"] for receipt in close["agents"]} == {
            "coffee-shop-stock", "coffee-shop-margin", "coffee-shop-close",
        }
        assert all(receipt["responseId"] and receipt["version"] != "test-double" for receipt in close["agents"])
        assert {item["store"]["storeId"] for item in close["evidence"]} == {"001", "002"}
        assert all("Nino Kapanadze" not in receipt["text"] for receipt in close["agents"])
        results["checks"].update(agentInvocation=True, applicationChat=True, grounding=True)
        results["evidence"]["closeLatencyTarget"] = {
            "singleCloseSeconds": elapsed, "singleCloseUnder60Seconds": elapsed < 60,
            "limitation": "One close is not a ten-user close p95 measurement.",
        }
        def read_store(_: int) -> tuple[int, object, float]:
            return area.request("/api/stores/001")
        with ThreadPoolExecutor(max_workers=10) as pool:
            reads = list(pool.map(read_store, range(10)))
        assert all(code == 200 for code, _, _ in reads)
        p95 = sorted(elapsed for _, _, elapsed in reads)[-1]
        results["evidence"]["tenConcurrentReads"] = {
            "count": 10, "p95SecondsNearestRank": p95, "targetSeconds": 1, "targetPassed": p95 < 1,
        }
        assert store.request("/api/auth/logout", {})[0] == 200
        assert store.request("/api/stores/001")[0] == 401
        results["checks"]["logout"] = True
        results["status"] = "passed"
        return 0
    except (AssertionError, urllib.error.URLError, subprocess.SubprocessError, KeyError) as error:
        results["status"] = "failed"
        results["failure"] = str(error)
        print(f"Live acceptance failed: {error}")
        return 1
    finally:
        (ROOT / "evidence" / filename).write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": results["status"], "checks": results["checks"], "evidence": filename}))


if __name__ == "__main__":
    raise SystemExit(main())
