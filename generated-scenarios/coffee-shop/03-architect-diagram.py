"""Generate the approved local-login Fourth Coffee architecture; not deployment evidence."""

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.azure.compute import AppServices
from diagrams.azure.identity import ManagedIdentities
from diagrams.azure.ml import CognitiveServices
from diagrams.azure.storage import StorageAccounts
from diagrams.onprem.client import Users

ROOT = Path(__file__).resolve().parent
with Diagram(
    "Fourth Coffee / authenticated public TLS reference",
    filename=str(ROOT / "03-architect-diagram"),
    show=False,
    direction="TB",
    graph_attr={"pad": "0.5", "nodesep": "0.7", "ranksep": "1.1", "fontsize": "18"},
):
    users = Users("Store / area managers\nsales")
    with Cluster("rg-coffee-shop-ref / Sweden Central"):
        web = AppServices(".NET 10 Razor + API\nP0v3 / 1–3 workers\nserver store entitlements")
        identity = ManagedIdentities("System identity\nno API keys")
        table = StorageAccounts("Table Storage / LRS\naccounts + lockout\nstock + order ETags")
        with Cluster("Foundry AIServices S0 / direct child backoffice"):
            agents = CognitiveServices("Versioned stock, margin, close agents\ngpt-4.1-mini / GlobalStandard")
    users >> Edge(label="HTTPS / local login\nsecure cookie + CSRF") >> web
    web >> Edge(label="credential") >> identity
    identity >> Edge(label="Table contributor") >> table
    identity >> Edge(label="Agent Consumer / project") >> agents
    web >> Edge(label="scoped evidence / response IDs") >> agents
