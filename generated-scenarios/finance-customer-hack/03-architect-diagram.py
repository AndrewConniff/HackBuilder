"""Render the provisional operator architecture and bounded banking runtime without cloud calls."""

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.azure.compute import AppServices
from diagrams.azure.identity import ManagedIdentities
from diagrams.azure.ml import CognitiveServices
from diagrams.azure.monitor import ApplicationInsights, LogAnalyticsWorkspaces
from diagrams.azure.storage import StorageAccounts
from diagrams.onprem.client import Users

ROOT = Path(__file__).resolve().parent
GRAPH = {"bgcolor": "white", "pad": "0.5", "nodesep": "0.6", "ranksep": "0.9", "dpi": "140"}
NODE = {"fontname": "Arial", "fontsize": "11", "labelloc": "t"}

with Diagram(
    "Adatum Corporation: provisional operator reference",
    filename=str(ROOT / "03-architect-diagram"), show=False, direction="LR",
    graph_attr=GRAPH, node_attr=NODE,
):
    n_ext_customer = Users("Customers / reps")
    n_ext_operator = Users("Operator browser / CLI")
    with Cluster("rg-finance-customer-hack / region not yet validated"):
        n_web_app = AppServices("app-bank / Linux B1")
        n_id_workload = ManagedIdentities("Workload identity")
        n_data_table = StorageAccounts("stbank / Tables")
        with Cluster("ai-bank / direct child banking"):
            n_app_foundry = CognitiveServices("Two saved agents\nbank-model")
        n_ops_insights = ApplicationInsights("appi-bank")
        n_ops_logs = LogAnalyticsWorkspaces("log-bank")
    n_ext_customer >> Edge(label="request: HTTPS + local login") >> n_web_app
    n_web_app >> Edge(label="auth: managed identity") >> n_id_workload
    n_id_workload >> Edge(label="read/write: scoped data") >> n_data_table
    n_id_workload >> Edge(label="request: Responses") >> n_app_foundry
    n_web_app >> Edge(label="telemetry: Entra") >> n_ops_insights >> n_ops_logs
    n_ext_operator >> Edge(label="admin: user Entra / scoped RBAC", style="dashed") >> [
        n_data_table, n_app_foundry, n_web_app
    ]

with Diagram(
    "Banking runtime: triage, grounding and human ownership",
    filename=str(ROOT / "04-runtime-diagram"), show=False, direction="LR",
    graph_attr=GRAPH, node_attr=NODE,
):
    n_ext_customer = Users("Signed-in customer")
    n_web_guard = AppServices("Authorize + reserve\ncase ETag/version")
    n_app_triage = CognitiveServices("bank-triage\nfaq / account / human")
    n_data_evidence = StorageAccounts("Policies + own\nsynthetic records")
    n_app_knowledge = CognitiveServices("bank-knowledge\nvalidated source IDs")
    n_data_cases = StorageAccounts("Durable human queue\nclaim / reply / close")
    n_ext_rep = Users("Assigned representative")
    n_ext_customer >> Edge(label="request: bounded message") >> n_web_guard
    n_web_guard >> Edge(label="request: message only") >> n_app_triage
    n_app_triage >> Edge(label="read: authorized route") >> n_data_evidence
    n_data_evidence >> Edge(label="request: bounded evidence") >> n_app_knowledge
    n_app_knowledge >> Edge(label="response: grounded answer") >> n_ext_customer
    n_app_triage >> Edge(label="write: escalation") >> n_data_cases
    n_app_knowledge >> Edge(label="write: missing evidence") >> n_data_cases
    n_ext_rep >> Edge(label="write: atomic claim / reply") >> n_data_cases
    n_data_cases >> Edge(label="response: human-owned thread") >> n_ext_customer
