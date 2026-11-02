"""Render durable transaction and bounded real-agent paths for the confirmed design."""

from functools import partial
from pathlib import Path

from diagrams import Cluster, Diagram, Edge, Node
from diagrams.azure.compute import ContainerApps
from diagrams.azure.database import CosmosDb
from diagrams.azure.integration import ServiceBus

OUTPUT = Path(__file__).resolve().with_suffix("")
text_node = partial(Node, fixedsize="false", width="0", height="0", labelloc="c", margin="0.18")

with Diagram(
    "Fourth Coffee | durable handoffs and scoped AI\nProposed runtime; no live results",
    filename=str(OUTPUT),
    show=False,
    direction="TB",
    graph_attr={
        "bgcolor": "white",
        "pad": "0.6",
        "nodesep": "0.9",
        "ranksep": "1.1",
        "splines": "spline",
        "fontname": "Arial",
        "fontsize": "22",
        "dpi": "150",
    },
    node_attr={"fontname": "Arial", "fontsize": "12"},
    edge_attr={"fontname": "Arial", "fontsize": "11"},
):
    n_edge_request_caller = text_node(
        "Guest session / staff Entra proof\nserver validates visit, role, floor",
        shape="box",
        style="rounded",
    )
    with Cluster("Scenario resource boundary | deterministic transaction path"):
        n_web_api_command = ContainerApps("1. Confirm domain action\nversion + idempotency key")
        n_data_cosmos_commit = CosmosDb("2. Atomic partition batch\nstate + receipt + outbox")
        n_app_worker_dispatch = ContainerApps("3. Lease pending outbox\npublish then mark sent")
        n_int_bus_ticket = ServiceBus("4. Durable ticket session\nMessageId = eventId")
        n_app_worker_consume = ContainerApps("5. Inbox + state batch\nthen complete message")
        n_web_board_poll = text_node(
            "6. Kitchen / floor board\n2-second persisted-state polling",
            shape="box",
            style="rounded",
        )
        n_ops_recovery_dlq = text_node(
            "Failure: bounded retry / DLQ\nmanager sees error; audited replay\nstable IDs prevent duplicate effects",
            shape="box",
            style="rounded",
        )

    with Cluster("Scenario + Foundry project boundary | advisory chat path"):
        n_app_chat_admission = ContainerApps("A. Internal chat / MI\ncaller proof revalidated\nbounded admission + 30s deadline")
        n_app_foundry_entry = text_node(
            "B. Real Foundry prompt agent\nGuest Concierge OR Service Coordinator",
            shape="box",
            style="rounded",
        )
        n_app_tools_validate = text_node(
            "C. App-executed typed tools\nvalidate scope + arguments\nread domain API; cite IDs / versions",
            shape="box",
            style="rounded",
        )
        n_app_foundry_advisor = text_node(
            "D. Staff-only Kitchen Advisor\nat most one real specialist call\nno writes / no recursion",
            shape="box",
            style="rounded",
        )
        n_web_preview_confirm = text_node(
            "E. Mutation preview only\nexplicit UI confirmation\nrevalidate before deterministic write",
            shape="box",
            style="rounded",
        )
        n_ops_chat_failure = text_node(
            "Failure: explicit 429 / 503 / timeout\norders remain independent of AI\nno invented settlement / kitchen success",
            shape="box",
            style="rounded",
        )

    n_edge_request_caller >> Edge(label="request: transaction") >> n_web_api_command
    n_web_api_command >> Edge(label="write: MI") >> n_data_cosmos_commit
    n_data_cosmos_commit >> Edge(label="read: pending outbox MI") >> n_app_worker_dispatch
    n_app_worker_dispatch >> Edge(label="event: send MI") >> n_int_bus_ticket
    n_int_bus_ticket >> Edge(label="event: receive MI") >> n_app_worker_consume
    n_app_worker_consume >> Edge(label="write: MI receipt/state") >> n_data_cosmos_commit
    n_data_cosmos_commit >> Edge(label="response: authorized API") >> n_web_board_poll
    n_int_bus_ticket >> Edge(label="event: delivery failure", style="dashed") >> n_ops_recovery_dlq
    n_edge_request_caller >> Edge(label="request: same-origin proxy") >> n_app_chat_admission
    n_app_chat_admission >> Edge(label="request: Agent Consumer MI") >> n_app_foundry_entry
    n_app_foundry_entry >> Edge(label="request: tool call") >> n_app_tools_validate
    n_app_tools_validate >> Edge(label="read: scoped domain API", style="dashed") >> n_web_api_command
    n_app_tools_validate >> Edge(label="request: staff delegation") >> n_app_foundry_advisor
    n_app_tools_validate >> Edge(label="response: proposed action") >> n_web_preview_confirm
    n_web_preview_confirm >> Edge(label="request: confirmed action", style="dashed") >> n_web_api_command
    n_app_chat_admission >> Edge(label="response: dependency error", style="dashed") >> n_ops_chat_failure
