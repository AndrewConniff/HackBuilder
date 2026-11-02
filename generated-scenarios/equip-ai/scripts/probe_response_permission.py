"""Temporarily test one native Responses action at the existing project; always remove the diagnostic grant."""

from datetime import datetime, timezone
import json
import time

from install_identity import command, save
from private_runner import GROUP, ROOT, SUBSCRIPTION
from validate_live import Session, values


def main(*, agent_read: bool = False) -> None:
    config = values()
    group = f"/subscriptions/{SUBSCRIPTION}/resourceGroups/{GROUP}"
    project = group + "/providers/Microsoft.CognitiveServices/accounts/ai-equip-equipai-kex72v/projects/equipment-operations"
    role = {
        "Name": "equip-ai temporary agent reader" if agent_read else "equip-ai temporary native Responses writer",
        "IsCustom": True,
        "Description": "Temporary equip-ai native Responses permission isolation; no administration or read permissions.",
        "Actions": [],
        "NotActions": [],
        "DataActions": ["Microsoft.CognitiveServices/accounts/AIServices/agents/read" if agent_read else
                        "Microsoft.CognitiveServices/accounts/OpenAI/responses/write"],
        "NotDataActions": [],
        "AssignableScopes": [group],
    }
    evidence = ROOT / "local-evidence" / "resume-20261028"
    prefix = "agent-read" if agent_read else "response-permission"
    role_file = evidence / f"{prefix}-role.json"
    save(role_file, role)
    access = json.loads((ROOT / ".private" / "participant-access.json").read_text())
    session = Session(config["APPLICATION_URL"])
    session.login(access["accounts"][0])
    session.request("/api/chat", {"question": "Refuse to control equipment."}, expected=502)
    created_role = None
    assignment = None
    results = []
    try:
        created_role = command(["az", "role", "definition", "create", "--subscription", SUBSCRIPTION,
                                "--role-definition", str(role_file)])
        assignment = command([
            "az", "role", "assignment", "create", "--subscription", SUBSCRIPTION,
            "--assignee-object-id", "95e688cf-66f0-4d71-b361-8ab5cb20a890",
            "--assignee-principal-type", "ServicePrincipal", "--role", created_role["id"], "--scope", project])
        for attempt in range(12):
            try:
                response = session.request("/api/chat", {"question": "Refuse to control equipment."})
                results.append({"attempt": attempt + 1, "passed": True, "responseType": type(response).__name__})
                break
            except RuntimeError as error:
                if "HTTP 502, expected 200" not in str(error):
                    raise
                results.append({"attempt": attempt + 1, "passed": False, "applicationStatus": 502})
                if attempt < 11:
                    time.sleep(20)
    finally:
        if assignment:
            command(["az", "role", "assignment", "delete", "--subscription", SUBSCRIPTION,
                     "--ids", assignment["id"]], json_output=False)
        if created_role:
            command(["az", "role", "definition", "delete", "--subscription", SUBSCRIPTION,
                     "--name", created_role["name"]], json_output=False)
        save(evidence / f"{prefix}-probe.json", {
            "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
            "scope": project, "dataAction": role["DataActions"][0], "results": results,
            "diagnosticAssignmentRemoved": assignment is not None, "diagnosticRoleRemoved": created_role is not None,
            "newPaidResources": False, "workloadAdministratorGranted": False,
        })
    print(json.dumps({"attempts": len(results), "passed": any(result["passed"] for result in results),
                      "diagnosticGrantRemoved": True}))


if __name__ == "__main__":
    main()
