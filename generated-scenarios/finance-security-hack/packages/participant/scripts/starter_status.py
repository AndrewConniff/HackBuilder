"""Local status only: no cloud calls, keys, app or completed agent."""
import json

if __name__ == "__main__":
    print(json.dumps({
        "status": "not-configured",
        "applicationIncluded": False,
        "applicationUrl": None,
        "preprovided": ["team isolation/access contract", "synthetic FAQ fixture"],
        "learnerBuildRequired": ["identity-backed model", "agent", "grounding", "authenticated receipt", "hardening"]
    }, indent=2))
