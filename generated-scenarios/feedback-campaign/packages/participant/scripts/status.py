"""Local expected-incomplete check; performs no network or model request."""
import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
posts = json.loads((root / "fixtures/posts.json").read_text(encoding="utf-8"))
assert len(posts) == 10 and len({p["sourceId"] for p in posts}) == 10
assert all(p["contact"].endswith("@example.test") for p in posts)
assert not (root / "src").exists()
print(json.dumps({"status": "not-configured", "agentPresent": False,
                  "businessUnits": ["sales", "marketing"], "fixtureCount": len(posts),
                  "reason": "Build your agent and authenticated action in the challenges."}))
