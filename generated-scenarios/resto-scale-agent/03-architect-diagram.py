"""Render the confirmed, not-yet-deployed Fourth Coffee reference architecture."""

from functools import partial
from pathlib import Path

from diagrams import Cluster, Diagram, Edge, Node
from diagrams.azure.compute import ContainerApps
from diagrams.azure.database import CosmosDb
from diagrams.azure.integration import ServiceBus
from diagrams.azure.security import KeyVaults
from diagrams.onprem.client import Users

OUTPUT = Path(__file__).resolve().with_suffix("")
text_node = partial(Node, fixedsize="false", width="0", height="0", labelloc="c", margin="0.18")

with Diagram(
    "Fourth Coffee | restaurant scale reference\nConfirmed local design; not deployed",
    filename=str(OUTPUT),
    show=False,
    direction="TB",
    graph_attr={
        "bgcolor": "white",
        "pad": "0.6",
        "nodesep": "0.9",
        "ranksep": "1.2",
        "splines": "spline",
        "fontname": "Arial",
        "fontsize": "22",
        "dpi": "150",
    },
    node_attr={"fontname": "Arial", "fontsize": "12"},
    edge_attr={"fontname": "Arial", "fontsize": "11"},
):
    n_edge_users_guests = Users("Guests\nown visit only")
    n_edge_users_staff = Users("Staff / kitchen\nEntra roles + floors")

    with Cluster("Scenario resource group | target not selected", graph_attr={"margin": "28"}):
        with Cluster("VNet-integrated, zone-enabled Container Apps environment | dedicated /23 subnet"):
            n_web_aca_transactions = ContainerApps("Web + transaction API\nHTTPS; 3-12 replicas")
            n_app_aca_chat = ContainerApps("Internal chat API\n3-6 replicas")
            n_app_aca_worker = ContainerApps("Outbox + ticket worker\n3-10 replicas")
            n_id_mi_runtime = text_node(
                "Separate managed identities\nweb / chat / worker / scaler / image pull",
                shape="box",
                style="rounded",
            )

        n_data_cosmos_business = CosmosDb("Cosmos NoSQL\nvisits / slots / outbox / inbox\nshared autoscale max 4k RU/s")
        n_int_bus_tickets = ServiceBus("Premium Service Bus\nper-ticket sessions / DLQ")
        n_sec_vault_signing = KeyVaults("Key Vault\nRSA guest-session signing")
        with Cluster("Foundry account AIServices S0 | direct child project | Basic setup"):
            n_app_foundry_agents = text_node(
                "Guest Concierge / Service Coordinator\nbounded Kitchen Advisor\none configurable model deployment",
                shape="box",
                style="rounded",
            )
        n_ops_acr_images = text_node("ACR Basic\nadmin disabled / AcrPull", shape="box", style="rounded")
        n_ops_monitor_evidence = text_node(
            "Application Insights + Log Analytics\nredacted latency / RU / backlog / agent traces",
            shape="box",
            style="rounded",
        )

    n_edge_users_guests >> Edge(label="request: scoped session") >> n_web_aca_transactions
    n_edge_users_staff >> Edge(label="auth: Entra") >> n_web_aca_transactions
    n_web_aca_transactions >> Edge(label="request: caller proof") >> n_app_aca_chat
    n_web_aca_transactions >> Edge(label="write: atomic batch") >> n_data_cosmos_business
    n_web_aca_transactions >> Edge(label="auth: MI sign", style="dashed") >> n_sec_vault_signing
    n_app_aca_chat >> Edge(label="request: MI agent") >> n_app_foundry_agents
    n_app_aca_chat >> Edge(label="request: scoped tools", style="dashed") >> n_web_aca_transactions
    n_app_aca_worker >> Edge(label="read/write: MI") >> n_data_cosmos_business
    n_app_aca_worker >> Edge(label="event: send/receive MI") >> n_int_bus_tickets
    n_id_mi_runtime >> Edge(label="auth: least privilege", style="dashed") >> n_ops_acr_images
    [n_web_aca_transactions, n_app_aca_chat, n_app_aca_worker] >> Edge(
        label="telemetry", style="dotted"
    ) >> n_ops_monitor_evidence
