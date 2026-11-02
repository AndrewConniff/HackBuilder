"""Generate accessible SVG diagrams and render matching PNGs with workspace-local resvg.

The existing diagram skill's grouped-resource patterns are reused. Graphviz is absent
on this host, so SVG plus resvg avoids a global Graphviz install and preserves sources.
"""

import html
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def box(x: int, y: int, width: int, title: str, lines: list[str], color: str = "#e5f2ff") -> str:
    """Render a labeled component with readable multiline content."""
    result = [
        f'<rect x="{x}" y="{y}" width="{width}" height="156" rx="14" fill="{color}" stroke="#356b98" stroke-width="2"/>',
        f'<text x="{x + 20}" y="{y + 35}" font-size="23" font-weight="bold">{html.escape(title)}</text>',
    ]
    for index, line in enumerate(lines):
        result.append(f'<text x="{x + 20}" y="{y + 70 + index * 26}" font-size="18">{html.escape(line)}</text>')
    return "".join(result)


def arrow(x1: int, y1: int, x2: int, y2: int, label: str = "") -> str:
    """Render a directed, labeled data path."""
    return (
        f'<path d="M{x1},{y1} L{x2},{y2}" stroke="#285e87" stroke-width="3" marker-end="url(#arrow)" fill="none"/>'
        f'<text x="{(x1 + x2) // 2}" y="{(y1 + y2) // 2 - 12}" text-anchor="middle" '
        f'font-size="17">{html.escape(label)}</text>'
    )


def draw(kind: str, output: Path) -> None:
    """Generate one architecture or runtime diagram with explicit evidence boundaries."""
    title = "Reference architecture" if kind == "architecture" else "Runtime, recovery and acceptance paths"
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1700" height="1120" viewBox="0 0 1700 1120">',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">'
        '<path d="M0,0 L0,6 L9,3 z" fill="#285e87"/></marker></defs>',
        '<rect width="1700" height="1120" fill="#f5f8fc"/>',
        '<g font-family="Segoe UI, sans-serif" fill="#142f49">',
        f'<text x="50" y="55" font-size="34" font-weight="bold">Margie&apos;s Travel | {title}</text>',
        '<text x="50" y="90" font-size="21">Portable local reference — no live Azure target or capacity verified</text>',
        '<rect x="35" y="120" width="1630" height="880" rx="20" fill="white" stroke="#91abc0" stroke-width="2"/>',
    ]
    if kind == "architecture":
        parts += [
            box(75, 160, 370, "Operator browser", ["Razor Pages + JavaScript", "Entra token held in memory", "Evidence links and queue status"]),
            box(620, 160, 465, ".NET 10 · App Service", ["JWT audience / tenant / operator checks", "Ingestion + chat + background worker", "Linux B1 candidate · Always On"]),
            box(1210, 160, 400, "Foundry Basic", ["AIServices → direct child project", "One persisted prompt agent", "Microsoft-managed agent state"]),
            box(75, 480, 400, "User-assigned identity", ["Azure runtime token credential", "Blob + Queue Contributor", "Project-scoped Foundry User"]),
            box(620, 480, 465, "Storage account · Standard LRS", ["raw / processed / status / audit blobs", "Private containers, OAuth, no keys", "No customer-deployed Cosmos DB"]),
            box(1210, 480, 400, "Azure Queue Storage", ["feedback-ingest + feedback-poison", "Blob references, not feedback bodies", "At-least-once; explicit retry policy"]),
            box(620, 790, 465, "Observability", ["Correlation IDs + durable status", "Blob audit + bounded App Service logs", "No feedback text or tokens in logs"], "#edf6e8"),
            arrow(445, 238, 620, 238, "HTTPS"),
            arrow(1085, 238, 1210, 238, "real agent"),
            arrow(850, 316, 850, 480, "Blob evidence"),
            arrow(1085, 520, 1210, 520, "enqueue"),
            arrow(1400, 480, 1050, 316, "worker receive"),
            arrow(445, 520, 620, 300, "MI"),
            arrow(850, 636, 850, 790, "audit / status"),
            '<text x="75" y="735" font-size="21">Single reference resource group (name and region unresolved).</text>',
            '<text x="75" y="770" font-size="19">Public TLS service endpoints; production policy/private-network suitability needs preflight.</text>',
        ]
    else:
        parts += [
            box(75, 160, 440, "1 · Accept synthetic feedback", ["Validate schema and declared language", "Conditional raw blob create + hash", "Conflicting duplicate → HTTP 409"]),
            box(650, 160, 440, "2 · Queue notification", ["Stable feedback ID + correlation ID", "Raw blob is durable outbox", "30-second reconciliation resends"]),
            box(1200, 160, 410, "3 · Worker", ["90-second visibility / 60-second lease", "Conditional processed evidence write", "Delete message only after durability"]),
            box(1200, 480, 410, "4 · Retry / negative path", ["Transient failure → bounded retry", "Invalid / exhausted → poison + audit", "Malformed JSON never reports success"], "#fff1e5"),
            box(650, 480, 440, "5 · Retrieve Blob evidence", ["Bounded dataset: maximum 100 records", "Filter category and source languages", "Preserve original-language excerpts"]),
            box(75, 480, 440, "6 · Invoke real Foundry agent", ["Agent-scoped Responses API v1", "MI token, no browser service secrets", "Missing endpoint → HTTP 503"]),
            box(75, 790, 440, "7 · Validate response", ["Exact ID + original quote checks", "Unverifiable citation → HTTP 502", "Browser renders safe text, not HTML"]),
            box(650, 790, 440, "8 · Show evidence and audit", ["Response ID + evidence scope", "Correlated status and citation links", "No mock or local model success"], "#edf6e8"),
            arrow(515, 238, 650, 238, "enqueue"),
            arrow(1090, 238, 1200, 238, "receive"),
            arrow(1500, 316, 1500, 480, "failure"),
            '<path d="M1300,316 L1300,390 L870,390 L870,480" stroke="#285e87" stroke-width="3" '
            'marker-end="url(#arrow)" fill="none"/>',
            '<text x="1050" y="375" font-size="18">completed evidence</text>',
            arrow(650, 558, 515, 558, "context"),
            arrow(300, 636, 300, 790, "response"),
            arrow(515, 868, 650, 868, "checked"),
            '<text x="1170" y="820" font-size="20">Local tests exercise Azurite.</text>',
            '<text x="1170" y="855" font-size="20">Foundry / MI / live chat still pending.</text>',
            '<text x="1170" y="890" font-size="20">Diagram is not deployment evidence.</text>',
        ]
    parts += [
        '</g><text x="50" y="1050" font-family="Segoe UI, sans-serif" font-size="21" fill="#294b66">'
        'No Azure operation authorized here. Exact-target preflight → actual what-if review → deployment confirmation.'
        '</text></svg>'
    ]
    svg = output.with_suffix(".svg")
    svg.write_text("".join(parts), encoding="utf-8")
    subprocess.run(["node", str(ROOT / "scripts" / "render-diagram.cjs"), str(svg), str(output)], check=True)
    print(f"Generated {svg.name} and {output.name}")
