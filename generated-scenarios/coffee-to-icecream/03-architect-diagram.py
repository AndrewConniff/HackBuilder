"""Render provisional setup and runtime diagrams from the target architecture, not deployment evidence."""

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.azure.compute import AppServices
from diagrams.azure.identity import ManagedIdentities
from diagrams.azure.ml import CognitiveServices
from diagrams.azure.monitor import LogAnalyticsWorkspaces
from diagrams.azure.storage import StorageAccounts
from diagrams.generic.compute import Rack
from diagrams.generic.storage import Storage
from diagrams.onprem.client import Users

ROOT = Path(__file__).resolve().parent
STYLE = {"pad": "0.5", "nodesep": "1", "ranksep": "1.1", "fontsize": "18",
         "fontname": "Segoe UI", "bgcolor": "white"}

with Diagram(
    "Northwind Traders / provisional ice-cream reference",
    filename=str(ROOT / "03-architect-diagram"),
    show=False,
    direction="TB",
    graph_attr=STYLE,
    node_attr={"fontname": "Segoe UI", "fontsize": "12"},
):
    n_web_users = Users("Store / area managers\noperations / local accounts")
    n_ops_admin = Users("Windows operator\nown Azure browser + CLI")
    with Cluster("Destination rg-${environmentName} / region pending target readiness"):
        n_app_web = AppServices("web-ic + unique suffix\n.NET 10 / Linux P0v3\n1-3 workers")
        n_id_app = ManagedIdentities("Web system identity\nproject consumer + Table contributor")
        n_data_table = StorageAccounts("stic + unique suffix\nIceCreamBackOffice\nsnapshots / orders / closes / accounts")
        n_ops_logs = LogAnalyticsWorkspaces("log-ic + unique suffix\n30 days / 1 GB daily cap")
        with Cluster("ic + environment + suffix / AIServices S0 / direct project backoffice"):
            n_app_foundry = CognitiveServices("Version-selected prompt agents\nstock / margin / close\nparameterized model")
    n_web_users >> Edge(label="request: TLS / cookie / CSRF") >> n_app_web
    n_app_web >> Edge(label="auth: managed identity") >> n_id_app
    n_id_app >> Edge(label="read/write: scoped business rows") >> n_data_table
    n_id_app >> Edge(label="request: Responses endpoints") >> n_app_foundry
    [n_app_web, n_data_table, n_app_foundry] >> Edge(label="telemetry: diagnostics") >> n_ops_logs
    n_ops_admin >> Edge(label="admin: publish / install", style="dashed") >> n_app_web
    n_ops_admin >> Edge(style="dashed") >> [n_data_table, n_app_foundry, n_ops_logs]

with Diagram(
    "Northwind Traders / bounded Orchestrator-Workers",
    filename=str(ROOT / "04-runtime-diagram"),
    show=False,
    direction="TB",
    graph_attr=STYLE,
    node_attr={"fontname": "Segoe UI", "fontsize": "12"},
):
    n_web_manager = Users("Authorized manager")
    n_app_gate = Rack("Cookie / stamp / CSRF\nstore grants checked before reads")
    n_data_evidence = Storage("Versioned store-day snapshots\nrecipe consumption + waste + decimal P&L")
    n_app_orchestrator = Rack("App orchestrator\nN stores -> 2N assignments\n55-second total deadline")
    with Cluster("Four workers/request / 40 calls/instance / 400 output tokens per invocation"):
        n_app_stock = Rack("Foundry stock workers\none scoped store per assignment")
        n_app_margin = Rack("Foundry margin workers\none ledger per assignment")
    n_app_reconcile = Rack("Require every unique receipt\nany failed worker -> no report")
    n_app_close = Rack("Foundry synthesis\nreconciled receipts + authoritative totals")
    n_data_report = Storage("Durable AwaitingReview report\nsnapshot versions / response IDs")
    n_web_reviewer = Users("Explicit manager review\nscope + versions + 15-minute expiry")
    n_data_final = Storage("Reviewed managerial report\nno accounting posting")
    n_data_import = Rack("Complete store CSV packet\nvalidate / hash receipt / atomic update")
    n_data_order = Storage("Positive-shortfall internal draft\nhuman confirmation / ETag / replay safety")
    n_web_manager >> n_app_gate >> n_data_evidence >> n_app_orchestrator
    n_app_orchestrator >> [n_app_stock, n_app_margin]
    [n_app_stock, n_app_margin] >> n_app_reconcile >> n_app_close >> n_data_report
    n_data_report >> n_web_reviewer >> n_data_final
    n_app_gate >> Edge(label="write: validated complete packet") >> n_data_import >> n_data_evidence
    n_data_evidence >> Edge(label="write: draft only") >> n_data_order
    n_web_reviewer >> Edge(label="write: approved internal order only") >> n_data_order
