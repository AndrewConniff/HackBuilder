"""Render the provisional retail reference architecture and agent runtime."""

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.azure.compute import AppServices, VMWindows
from diagrams.azure.identity import ManagedIdentities
from diagrams.azure.ml import CognitiveServices
from diagrams.azure.monitor import ApplicationInsights
from diagrams.azure.network import DNSPrivateZones, PrivateEndpoint
from diagrams.azure.storage import StorageAccounts
from diagrams.generic.blank import Blank
from diagrams.generic.compute import Rack
from diagrams.onprem.client import Users

OUTPUT = Path(__file__).resolve().parent
GRAPH = {
    "bgcolor": "white",
    "pad": "0.5",
    "nodesep": "0.75",
    "ranksep": "0.85",
    "splines": "spline",
    "fontname": "Arial",
    "fontsize": "18",
    "dpi": "120",
}
NODE = {"fontname": "Arial", "fontsize": "12", "labelloc": "t"}
CLUSTER = {"margin": "24", "fontname": "Arial", "fontsize": "15"}
BOX = {
    "shape": "box",
    "style": "rounded,filled",
    "fillcolor": "#ffffff",
    "image": "",
    "labelloc": "c",
    "width": "2.5",
    "height": "0.9",
}


def architecture() -> None:
    """Render the resource boundaries, private access and management paths."""
    with Diagram(
        "Woodgrove Groceries\nProvisional reference architecture - not deployed",
        filename=str(OUTPUT / "03-architect-diagram"),
        show=False,
        direction="TB",
        graph_attr=GRAPH,
        node_attr=NODE,
        edge_attr={"fontname": "Arial", "fontsize": "10"},
    ):
        n_edge_customer = Users("Customer browser\nlocal app accounts")
        n_ops_operator = Users("Deployment operator\nAzure user identity")
        with Cluster("Proposed scenario resource group", graph_attr=CLUSTER):
            with Cluster("App Service platform - outside the VNet", graph_attr=CLUSTER):
                n_web_console = AppServices("Linux B1\n.NET 10 console/API")
                n_id_workload = ManagedIdentities("Workload identity\nscoped data roles")
            with Cluster("VNet 10.42.0.0/16", graph_attr=CLUSTER):
                with Cluster("App integration 10.42.0.0/26", graph_attr=CLUSTER):
                    n_app_integration = Blank("Outbound VNet\nintegration only", **BOX)
                with Cluster("Private endpoints 10.42.1.0/24", graph_attr=CLUSTER):
                    n_data_foundry_pe = PrivateEndpoint("Foundry private\nendpoint")
                    n_data_storage_pe = PrivateEndpoint("Table + Blob\nprivate endpoints")
                    n_ops_dns = DNSPrivateZones("Private DNS\nVNet-linked zones")
                with Cluster("Management 10.42.2.0/24", graph_attr=CLUSTER):
                    n_ops_vm = VMWindows("Private Windows VM\nbrowser + CLI + installer")
                    n_ops_nat = Blank("Standard NAT Gateway\nseparate egress public IP", **BOX)
                with Cluster("AzureBastionSubnet 10.42.3.0/26", graph_attr=CLUSTER):
                    n_sec_bastion = Rack("Bastion Standard\nRDP + native tunnel")
            n_app_foundry = CognitiveServices("Foundry S0 + project\n3 prompt agents + model")
            n_data_business = StorageAccounts("Private LRS Storage\norders + receipts + keys")
            n_ops_telemetry = ApplicationInsights("Application Insights\nLog Analytics")
        with Cluster("Foundry platform-managed boundary", graph_attr=CLUSTER):
            n_data_agent_state = Blank("Basic agent state\npublic platform egress", **BOX)
        n_ext_tooling = Blank("Microsoft tooling / sign-in\noutbound destinations\nnot restricted", **BOX)

        n_edge_customer >> Edge(label="request: HTTPS + session") >> n_web_console
        n_ops_operator >> Edge(label="admin: authenticated TLS") >> n_sec_bastion
        n_sec_bastion >> Edge(label="admin: private RDP / SSH") >> n_ops_vm
        n_ops_vm >> Edge(label="request: explicit outbound") >> n_ops_nat
        n_ops_nat >> Edge(label="request: public TLS") >> n_ext_tooling
        n_ops_operator >> Edge(label="deploy: local build / public SCM", style="dashed") >> n_web_console
        n_web_console >> Edge(label="request: outbound") >> n_app_integration
        n_app_integration >> [n_data_foundry_pe, n_data_storage_pe]
        n_ops_vm >> Edge(label="admin: own Azure credentials") >> n_data_foundry_pe
        n_ops_vm >> Edge(label="admin: full data lifecycle") >> n_data_storage_pe
        n_data_foundry_pe >> Edge(label="request: private TLS") >> n_app_foundry
        n_data_storage_pe >> Edge(label="read/write: private TLS") >> n_data_business
        n_id_workload >> Edge(label="auth: MI + RBAC", style="dashed") >> n_web_console
        n_ops_dns >> Edge(label="read: name resolution", style="dashed") >> n_app_integration
        n_app_foundry >> Edge(label="write: conversations") >> n_data_agent_state
        n_web_console >> Edge(label="telemetry: redacted", style="dotted") >> n_ops_telemetry


def runtime() -> None:
    """Render real agent calls and deterministic customer/action boundaries."""
    with Diagram(
        "Woodgrove Groceries\nProposed agent runtime - all commerce and delivery are synthetic",
        filename=str(OUTPUT / "04-runtime-diagram"),
        show=False,
        direction="TB",
        graph_attr=GRAPH,
        node_attr=NODE,
        edge_attr={"fontname": "Arial", "fontsize": "10"},
    ):
        n_edge_customer = Users("Customer\nown order only")
        with Cluster("Authenticated .NET application - deterministic ownership", graph_attr=CLUSTER):
            n_web_console = AppServices("Chat + timeline\nsession / CSRF checks")
            n_app_coordinator = Blank("Durable coordinator\nversion + budget guards", **BOX)
            n_sec_approval = Blank("Exact proposal approval\n10-minute expiry", **BOX)
            n_app_tools = Blank("Allowlisted tools\npolicy + idempotency", **BOX)
            n_data_state = StorageAccounts("Atomic state + receipts\nsame Table partition")
            n_int_simulation = Blank("Synthetic event adapters\nstock / payment / carrier", **BOX)
        with Cluster("Real Foundry project - separate prompt-agent versions", graph_attr=CLUSTER):
            n_app_order = CognitiveServices("1. Order Assistance\ncatalog / cart")
            n_app_fulfillment = CognitiveServices("2. Fulfillment\nstock / replacement")
            n_app_delivery = CognitiveServices("3. Delivery Coordination\nslot / delay")
        n_ops_evidence = Blank("Correlated evidence\nagent + response + action IDs", **BOX)
        n_sec_hold = Blank("Visible hold / failure\nno false completion", **BOX)

        n_edge_customer >> Edge(label="request: cart / confirmation") >> n_web_console
        n_web_console >> Edge(label="request: validated work") >> n_app_coordinator
        n_app_coordinator >> Edge(label="request/response: stage 1", dir="both") >> n_app_order
        n_app_coordinator >> Edge(label="request/response: stage 2", dir="both") >> n_app_fulfillment
        n_app_coordinator >> Edge(label="request/response: stage 3", dir="both") >> n_app_delivery
        [n_app_order, n_app_fulfillment, n_app_delivery] >> Edge(label="request: scoped function") >> n_app_tools
        n_app_tools >> Edge(label="write: authorized transaction only") >> n_data_state
        n_app_tools >> Edge(label="request: simulation only") >> n_int_simulation
        n_int_simulation >> Edge(label="event: validated", constraint="false") >> n_app_coordinator
        n_app_tools >> Edge(label="response: changed item / total / slot") >> n_sec_approval
        n_sec_approval >> Edge(
            label="response: proposal\nrequest: customer decision", dir="both", constraint="false"
        ) >> n_edge_customer
        n_sec_approval >> Edge(label="write: accepted exact version") >> n_data_state
        n_data_state >> Edge(
            label="read: resume", style="dashed", constraint="false"
        ) >> n_app_coordinator
        n_app_tools >> Edge(label="response: error / invalid approval") >> n_sec_hold
        n_app_tools >> Edge(label="telemetry: call IDs + receipts", style="dotted") >> n_ops_evidence


if __name__ == "__main__":
    architecture()
    runtime()
