"""Authorized real probes only. Partial receipts can never become complete scenario acceptance."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone

from cloud_io import ROOT, environment, receipt, request, verify_target


def output(response: dict) -> str:
    if response.get("status") != "completed" or not response.get("id"):
        raise RuntimeError("Inference did not return a completed real response with ID.")
    text = "".join(part.get("text", "") for item in response.get("output", [])
                   for part in item.get("content", []) if part.get("type") == "output_text")
    if not text:
        raise RuntimeError("Inference had no response text.")
    return text


def main() -> None:
    verify_target()
    env = environment()
    endpoint = env["FOUNDRY_PROJECT_ENDPOINT"].rstrip("/") + "/openai/v1/responses"
    checks = {}
    details = {}
    for name, body in [
        ("modelInference", {"model": env["FOUNDRY_MODEL_DEPLOYMENT"], "input": "Reply with the word READY.", "max_output_tokens": 64, "store": False}),
        ("agentInvocation", {"agent_reference": {"name": "campaign-listener", "type": "agent_reference",
                                               "version": env["FOUNDRY_AGENT_VERSION"]},
                             "input": json.dumps({"task": "chat", "question": "Can Sales promise a refund from this campaign?",
                                                 "policy": (ROOT / "src/FeedbackCampaign.Web/Policy/campaign-policy.md").read_text()}),
                             "max_output_tokens": 500, "store": False}),
    ]:
        try:
            response = request("POST", endpoint, "https://ai.azure.com", body)
            text = output(response)
            checks[name] = True
            details[name] = {"responseId": response["id"], "text": text, "identity": "authorized installer, not app MI"}
        except Exception as error:
            checks[name] = False
            details[name] = {"error": type(error).__name__}
    try:
        with urllib.request.urlopen(env["APP_URL"] + "/api/cases", timeout=30) as response:
            checks["anonymousDenial"] = False
            details["anonymousDenial"] = {"unexpectedStatus": response.status}
    except urllib.error.HTTPError as error:
        checks["anonymousDenial"] = error.code == 401
        details["anonymousDenial"] = {"status": error.code}
    receipt("runtime-probes.json", {"checkedAtUtc": datetime.now(timezone.utc).isoformat(),
            "checks": checks, "details": details, "completeScenarioAcceptance": False,
            "pending": ["Deployed ARM account/direct child project verification", "App MI-backed signed-in chat",
                        "Semantic grounding review", "Human review with edited reply", "Real reply stream receipt",
                        "Restart persistence", "Wrong-role and stale-decision denial", "Error/recovery and DLQ"]})
    if not all(checks.values()):
        raise SystemExit("One or more real runtime probes failed; see non-secret receipt.")
    print("Real direct inference/agent/anonymous-denial probes passed; full app/HITL acceptance remains pending.")


if __name__ == "__main__":
    main()
