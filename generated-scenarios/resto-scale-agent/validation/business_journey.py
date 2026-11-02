"""Run real authorized HTTPS restaurant journeys; no mocks, cloud setup or credential fallback."""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener


class Journey:
    def __init__(self, base: str, staff_token: str):
        self.base = base.rstrip("/")
        self.staff_token = staff_token
        self.http = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.csrf = ""

    def request(self, path: str, body: dict | None = None, staff: bool = False):
        headers = {"Content-Type": "application/json"}
        if body is not None:
            headers["X-CSRF-TOKEN"] = self.csrf
        if staff:
            headers["Authorization"] = f"Bearer {self.staff_token}"
        request = Request(self.base + path, headers=headers,
                          data=None if body is None else json.dumps(body).encode())
        with self.http.open(request, timeout=35) as response:
            return json.load(response)

    def refresh_csrf(self):
        self.csrf = self.request("/api/session/csrf")["token"]

    def confirm(self, visit_id: str, kind: str, staff: bool = False, **fields):
        visit = self.request(f"/api/visits/{visit_id}", staff=staff)
        preview = self.request("/api/previews", {
            "kind": kind, "visitId": visit_id, "expectedVersion": visit["version"], **fields
        }, staff=staff)
        confirmation = {"visitId": visit_id, "previewId": preview["id"], "requestId": str(uuid.uuid4())}
        receipt = self.request("/api/confirm", confirmation, staff=staff)
        retried = self.request("/api/confirm", confirmation, staff=staff)
        if receipt != retried:
            raise AssertionError("Identical confirmation retry changed its durable receipt.")
        return receipt

    def visit(self, slot: str, floor: int, previous_id: str | None):
        self.refresh_csrf()
        reservation = self.request("/api/reservations", {
            "slot": slot, "floor": floor, "seats": 1, "guestId": "guest-001", "requestId": str(uuid.uuid4())
        })
        visit_id = reservation["visitId"]
        deadline = time.monotonic() + 30
        while True:
            try:
                self.request("/api/session", {"visitId": visit_id, "accessCode": reservation["accessCode"]})
                break
            except HTTPError as error:
                if error.code != 404 or time.monotonic() >= deadline:
                    raise
                time.sleep(0.25)
        self.refresh_csrf()
        if previous_id is not None:
            try:
                self.request(f"/api/visits/{previous_id}")
            except HTTPError as error:
                if error.code != 403:
                    raise
            else:
                raise AssertionError("Guest could read a different authenticated visit.")
        self.confirm(visit_id, "checkin")
        self.confirm(visit_id, "order", items={"1": 1})
        deadline = time.monotonic() + 30
        while True:
            ticket = self.request(f"/api/visits/{visit_id}")["tickets"][0]
            if ticket["dispatched"]:
                break
            if time.monotonic() >= deadline:
                raise AssertionError("Kitchen dispatch exceeded the bounded journey deadline.")
            time.sleep(0.25)
        for status in ("accepted", "preparing", "ready", "served"):
            self.confirm(visit_id, "transition", staff=True, ticketId=ticket["id"], targetStatus=status)
        receipt = self.confirm(visit_id, "settle")
        self.confirm(visit_id, "survey", rating=5)
        final = self.request(f"/api/visits/{visit_id}")
        if not final["settled"] or final["survey"] != 5 or receipt["totalMinor"] != final["totalMinor"]:
            raise AssertionError("Final settlement/survey invariant failed.")
        return visit_id, final["totalMinor"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--date", required=True, help="Unused synthetic service date; never customer data.")
    parser.add_argument("--turns", type=int, choices=(4, 5), default=5)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    if not args.url.startswith("https://"):
        parser.error("Use only the explicitly authorized deployed HTTPS application URL.")
    token = os.environ.get("STAFF_ACCESS_TOKEN")
    if not token:
        parser.error("STAFF_ACCESS_TOKEN must contain a real authorized manager token.")
    client = Journey(args.url, token)
    result = {"status": "running", "covers": 0, "totalMinor": 0, "turns": args.turns}
    output = Path(args.out)
    previous_id = None
    try:
        for turn in range(1, args.turns + 1):
            for floor in range(1, 6):
                for _ in range(50):
                    previous_id, total = client.visit(f"{args.date}:{turn}", floor, previous_id)
                    result["covers"] += 1
                    result["totalMinor"] += total
                output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        if result["covers"] != args.turns * 250:
            raise AssertionError("Daily cover threshold was not reached.")
        result["status"] = "passed"
    except (HTTPError, OSError, AssertionError, ValueError, KeyError) as error:
        result.update(status="failed", failure=f"{type(error).__name__}: {error}")
        raise
    finally:
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
