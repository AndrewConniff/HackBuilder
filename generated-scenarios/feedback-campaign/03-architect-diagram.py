"""Reproducible architecture diagram, local rendering only."""
from pathlib import Path
from diagrams import Cluster, Diagram, Edge
from diagrams.azure.compute import AppServices
from diagrams.azure.integration import ServiceBus
from diagrams.azure.storage import StorageAccounts
from diagrams.azure.identity import ManagedIdentities
from diagrams.azure.monitor import ApplicationInsights, LogAnalyticsWorkspaces
from diagrams.generic.compute import Rack
from diagrams.onprem.client import Users, Client

root = Path(__file__).resolve().parent
with Diagram("Feedback Campaign - proposed Azure reference", show=False,
             filename=str(root / "03-architect-diagram"), direction="TB",
             graph_attr={"fontsize": "20", "pad": "0.6", "nodesep": "1.5"}):
    people = Users("Marketing / Sales\nhuman reviewers")
    operator = Client("Current workstation\nazd + initialization")
    accounts = Rack("Local app accounts\nsalted hashes / signed cookies\nno Entra consent")
    with Cluster("rg-feedback-campaign - centralus"):
        app = AppServices("B1 Linux / .NET 10\nlocal login + Razor + worker")
        mi = ManagedIdentities("App managed identity\nscoped data roles")
        bus = ServiceBus("Standard\nposts / replies + DLQ")
        state = StorageAccounts("LRS Tables\ncases / rules /\nactive pointer")
        with Cluster("Foundry AIServices S0 - no hub"):
            project = Rack("Direct child: campaign\nCampaign Listener\nprompt agent")
            model = Rack("gpt-4.1-mini\nGlobalStandard capacity 10")
        insights = ApplicationInsights("Sanitized telemetry")
        logs = LogAnalyticsWorkspaces("30-day logs")
    people >> Edge(label="HTTPS + local account") >> app
    app >> Edge(label="server roles / session") >> accounts
    accounts >> state
    operator >> Edge(label="public TLS / approved user") >> [app, project]
    app >> mi
    mi >> Edge(label="MI / RBAC") >> [bus, state, project]
    project >> model
    app >> Edge(style="dotted", label="IDs / error categories") >> insights >> logs
