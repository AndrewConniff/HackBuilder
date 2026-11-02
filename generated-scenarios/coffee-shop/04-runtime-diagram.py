"""Generate the bounded close and separate human order gate."""

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.generic.compute import Rack
from diagrams.generic.storage import Storage
from diagrams.onprem.client import Users

ROOT = Path(__file__).resolve().parent
with Diagram(
    "Fourth Coffee / scoped daily close and replenishment",
    filename=str(ROOT / "04-runtime-diagram"),
    show=False,
    direction="TB",
    graph_attr={"pad": "0.5", "nodesep": "0.7", "ranksep": "0.9", "fontsize": "18"},
):
    manager = Users("Assigned manager")
    gate = Rack("Protected cookie + account stamp + CSRF\nreject unauthorized stores BEFORE business reads")
    evidence = Storage("Scoped versioned snapshots\ncode computes P&L and shortfalls")
    with Cluster("90 seconds / no workflow retries / 800 output tokens per call"):
        stock = Rack("Foundry stock agent\nstock rows only")
        margin = Rack("Foundry margin agent\nledger rows only")
        close = Rack("Foundry close coordinator\nonly after both branches succeed")
    result = Rack("Advisory close + authoritative totals\nsource / correlation / response IDs")
    draft = Rack("Deterministic internal draft\none key per store + stock version")
    human = Users("Explicit human confirmation")
    order = Storage("ETag-protected approval\nactor + timestamp / replay safe\nNO supplier transmission")
    manager >> gate >> evidence
    evidence >> [stock, margin]
    [stock, margin] >> close >> result
    evidence >> draft >> human
    human >> Edge(label="recheck scope / version / expiry") >> order
