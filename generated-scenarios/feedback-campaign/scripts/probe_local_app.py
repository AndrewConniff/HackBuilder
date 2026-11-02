"""Exercise the real local-account/managed-identity path; never log passwords, cookies or CSRF tokens."""

from __future__ import annotations

import html
import http.cookiejar
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone

from cloud_io import ROOT, cli, environment, receipt, verify_target


class Session:
    def __init__(self, url: str):
        self.url = url.rstrip("/")
        self.browser = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )
        self.csrf: str | None = None

    def call(self, path: str, body: dict | None = None, form: bool = False,
             protected: bool = True) -> tuple[int, object]:
        headers = {}
        if body is not None:
            headers["Origin"] = self.url
            headers["Content-Type"] = "application/x-www-form-urlencoded" if form else "application/json"
            if protected and not form:
                if self.csrf is None:
                    _, tokens = self.call("/api/csrf")
                    self.csrf = tokens["token"]
                headers["X-CSRF-TOKEN"] = self.csrf
        data = None if body is None else (
            urllib.parse.urlencode(body).encode() if form else json.dumps(body).encode()
        )
        request = urllib.request.Request(self.url + path, data=data, headers=headers)
        try:
            with self.browser.open(request, timeout=80) as response:
                content = response.read().decode()
                return response.status, json.loads(content) if "application/json" in response.headers.get("Content-Type", "") else content
        except urllib.error.HTTPError as error:
            return error.code, None

    def login(self, account: dict, password: str | None = None) -> int:
        status, page = self.call("/Login")
        require(status == 200, "Local login page must be reachable without Entra.")
        token = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', page)
        require(token is not None, "Login must issue an antiforgery token.")
        status, _ = self.call("/Login", {
            "Username": account["username"], "Password": password if password is not None else account["password"],
            "__RequestVerificationToken": html.unescape(token.group(1)),
        }, form=True)
        self.csrf = None
        return status


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def wait_case(session: Session, case_id: str, statuses: set[str], limit: int = 160) -> dict:
    for _ in range(limit // 4):
        status, rows = session.call("/api/cases")
        if status == 200:
            row = next((r for r in rows if r["value"]["id"] == case_id), None)
            if row and row["value"]["status"] in statuses:
                return row
            if row and row["value"]["status"] == "Failed" and "Failed" not in statuses:
                raise RuntimeError("Real workflow persisted Failed; inspect the scoped error receipt, not passwords.")
        elif status not in (502, 503):
            raise RuntimeError(f"Authenticated case polling failed with HTTP {status}.")
        time.sleep(4)
    raise RuntimeError("Timed out waiting for the actual durable case transition.")


def main() -> None:
    verify_target()
    env = environment()
    participants = json.loads((ROOT / ".private" / "participant-access.json").read_text())
    coach_file = json.loads((ROOT / ".private" / "coach-access.json").read_text())
    accounts = {a["username"]: a for a in participants["accounts"] + coach_file["accounts"]}
    checks = {}
    details = {}
    result = {"checkedAtUtc": None, "checks": checks, "details": details, "completeScenarioAcceptance": False}
    try:
        anonymous = Session(env["APP_URL"])
        require(anonymous.call("/api/cases")[0] == 401, "Anonymous API access must be denied.")
        checks["anonymousDenial"] = True
        require(anonymous.login(accounts["product-manager"], "invalid-test-password") == 401, "Wrong password must be denied.")
        require(anonymous.call("/api/me")[0] == 401, "A rejected login cannot create a session.")
        checks["invalidLogin"] = True
        sessions = {}
        for name, account in accounts.items():
            session = Session(env["APP_URL"])
            require(session.login(account) == 200, "Issued local credential must sign in without external consent.")
            code, me = session.call("/api/me")
            require(code == 200 and set(me["roles"]) == set(account["roles"]), "Server roles must match the private receipt.")
            sessions[name] = session
        checks["localLogin"] = True
        coach = sessions["coach"]
        require(sessions["product-manager"].call("/api/rules/promote", {
            "version": "v1", "reason": "Wrong-role negative test", "etag": "not-used"
        })[0] == 403, "Product Manager cannot promote Control rules.")
        require(coach.call("/api/logout", {}, protected=False)[0] == 403, "Authenticated writes without CSRF must fail.")
        checks["wrongRoleDenial"] = checks["csrfDenial"] = True
        code, chat = coach.call("/api/chat", {"message": "Can Sales promise a refund from this campaign?"})
        require(code == 200 and chat.get("responseId") and "refund" in chat.get("text", "").lower(),
                "Actual app managed identity must invoke the Foundry agent.")
        require("campaign-policy-v1" in chat["text"] and any(
            word in chat["text"].lower() for word in ("cannot", "not authorized", "not promise", "does not", "no refund")
        ), "Grounded chat must refuse unsupported refund entitlement.")
        checks["applicationChat"] = checks["grounding"] = True
        details["applicationChat"] = {"responseId": chat["responseId"], "text": chat["text"], "identity": "app managed identity"}
        posts = json.loads((ROOT / "src/FeedbackCampaign.Web/SeedData/posts.json").read_text())
        run = "acceptance-" + uuid.uuid4().hex[:10]
        cases = []
        for index, post in enumerate(posts[:4]):
            payload = post | {"sourceId": f"{run}-{index}"}
            status, created = coach.call("/api/posts", payload)
            require(status == 200, "Authenticated intake must create a durable case.")
            row = wait_case(coach, created["value"]["id"], {"AwaitingHuman", "Queued"})
            item = row["value"]
            positive = item["analysis"]["overall"]["positive"]
            negative = item["analysis"]["overall"]["negative"]
            expected = "Auto" if positive >= .8 else "ProductManager" if negative >= .89 else "ConflictResolutionSpecialist"
            require(item["owner"] == expected and item["agentResponseId"], "Actual scores must drive exact deterministic routing.")
            cases.append(row | {"initialETag": created["eTag"]})
        details["cases"] = [{"id": r["value"]["id"], "owner": r["value"]["owner"], "status": r["value"]["status"],
                             "responseId": r["value"]["agentResponseId"], "scores": r["value"]["analysis"]["overall"]} for r in cases]
        require(any(r["value"]["owner"] == "Auto" for r in cases), "A real positive example must demonstrate auto reply.")
        require(any(r["value"]["owner"] == "ConflictResolutionSpecialist" for r in cases),
                "A real ambiguous/neutral example must reach Conflict Resolution.")
        pending = next((r for r in cases if r["value"]["status"] == "AwaitingHuman"), None)
        require(pending is not None, "A real human review case is required.")
        item = pending["value"]
        reviewer_name = "product-manager" if item["owner"] == "ProductManager" else "conflict-specialist"
        wrong_name = "conflict-specialist" if reviewer_name == "product-manager" else "product-manager"
        path = f"/api/cases/{item['id']}/review"
        decision = {"etag": pending["eTag"], "reply": "Thank you for your feedback. We have recorded the issue for investigation. No refund entitlement is promised."}
        require(sessions[wrong_name].call(path, decision)[0] == 403, "An unassigned reviewer must not approve the case.")
        require(sessions[reviewer_name].call(path, decision | {"etag": pending["initialETag"]})[0] == 409,
                "A stale human decision must be rejected.")
        checks["staleDecisionDenial"] = True
        cli("az", "webapp", "restart", "--subscription", env["AZURE_SUBSCRIPTION_ID"],
            "--resource-group", env["AZURE_RESOURCE_GROUP"], "--name", env["AZURE_WEBAPP_NAME"])
        resumed = wait_case(coach, item["id"], {"AwaitingHuman"})
        require(resumed["value"] == item and resumed["eTag"] == pending["eTag"],
                "Human case and signed-in cookie must survive actual App Service restart.")
        checks["persistentWorkflow"] = True
        require(sessions[reviewer_name].call(path, decision)[0] == 202, "The assigned human's edited reply must be accepted.")
        require(sessions[reviewer_name].call(path, decision)[0] == 409, "Repeated approval cannot create an independent send.")
        sent = wait_case(coach, item["id"], {"Queued"})
        require(sent["value"]["reply"] == decision["reply"] and any(
            a["action"] == "AcceptedByReplyStream" for a in sent["value"]["audit"]), "Actual worker must publish the approved reply.")
        checks["humanReview"] = checks["replyStream"] = checks["agenticWorkflow"] = True
        details["humanReview"] = {"caseId": item["id"], "reviewer": reviewer_name,
                                  "replyReceipt": "AcceptedByReplyStream", "restartVerified": True}
        conflict = next(r for r in cases if r["value"]["owner"] == "ConflictResolutionSpecialist")
        conflict_path = f"/api/cases/{conflict['value']['id']}/review"
        conflict_decision = {"etag": conflict["eTag"], "reply": "Thank you. We will investigate your preview-access question before suggesting further action."}
        require(sessions["conflict-specialist"].call(conflict_path, conflict_decision)[0] == 202,
                "Conflict Resolution must be able to approve its assigned investigation reply.")
        wait_case(coach, conflict["value"]["id"], {"Queued"})
        checks["conflictReview"] = True
        details["conflictReview"] = {"caseId": conflict["value"]["id"], "replyReceipt": "AcceptedByReplyStream"}
        status, rules = coach.call("/api/rules")
        require(status == 200, "Coach must be able to inspect the durable Control rules.")
        original_version = rules["active"]["value"]["version"]
        original_rules = next(r["value"] for r in rules["versions"] if r["value"]["version"] == original_version)
        proposed = original_rules | {"version": f"v-{run}", "productRouting": True,
                                     "reason": "Temporary real acceptance of human-controlled promotion; restore afterward."}
        require(coach.call("/api/rules", proposed)[0] == 201, "Coach must save a new immutable rule version.")
        promoted = False
        try:
            require(coach.call("/api/rules/promote", {"version": proposed["version"], "etag": rules["active"]["eTag"],
                    "reason": "Explicit acceptance promotion"})[0] == 202, "Coach must explicitly promote the new version.")
            promoted = True
            _, active = coach.call("/api/rules")
            require(active["active"]["value"]["version"] == proposed["version"], "Promoted pointer must be durable.")
            _, existing_cases = coach.call("/api/cases")
            require(next(r for r in existing_cases if r["value"]["id"] == item["id"])["value"]["rules"]["version"] == item["rules"]["version"],
                    "Promotion must not rewrite existing cases' rule snapshots.")
            checks["humanRulePromotion"] = True
        finally:
            if promoted:
                _, current = coach.call("/api/rules")
                require(coach.call("/api/rules/promote", {"version": original_version,
                        "etag": current["active"]["eTag"], "reason": "Restore original version after real acceptance"})[0] == 202,
                        "Original Control pointer must be restored after acceptance.")
        require(sessions["product-manager"].call("/api/logout", {})[0] == 200, "Logout must succeed with CSRF.")
        require(sessions["product-manager"].call("/api/me")[0] == 401, "Logout must end the actual session.")
        checks["logout"] = True
        checks["negativeCase"] = True
        result["completeScenarioAcceptance"] = True
    finally:
        result["checkedAtUtc"] = datetime.now(timezone.utc).isoformat()
        receipt("local-app-runtime.json", result)
    print("Real local-account, managed-identity chat, routing, human review, reply receipt and restart checks passed.")


if __name__ == "__main__":
    main()
