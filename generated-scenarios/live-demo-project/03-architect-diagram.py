"""Render the provisional reference topology and runtime without implying deployment success."""

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.azure.compute import AppServices, VM
from diagrams.azure.identity import ManagedIdentities
from diagrams.azure.ml import CognitiveServices
from diagrams.azure.network import PrivateEndpoint, VirtualNetworks
from diagrams.azure.networking import Bastions
from diagrams.azure.monitor import LogAnalyticsWorkspaces
from diagrams.generic.storage import Storage
from diagrams.onprem.client import Users

root = Path(__file__).resolve().parent
attributes = {"bgcolor": "white", "pad": "0.5", "nodesep": "0.8", "ranksep": "0.9", "dpi": "130"}

with Diagram("Adatum Corporation - proposed private reference", show=False,
             filename=str(root / "03-architect-diagram"), direction="LR", graph_attr=attributes,
             node_attr={"fontname": "Segoe UI", "fontsize": "11", "labelloc": "t"}):
    n_ext_customer = Users("Customer / representative")
    n_ext_operator = Users("Deploying user")
    with Cluster("rg-live-demo-project (proposed)"):
        n_web_app = AppServices("app-{prefix}\nLinux B2 / .NET 10")
        n_data_state = Storage("Persistent /home\naccounts / sources / cases")
        n_id_workload = ManagedIdentities("App managed identity")
        n_ops_logs = LogAnalyticsWorkspaces("log-{prefix}")
        with Cluster("vnet-{prefix} / 10.84.0.0/16"):
            n_net_vnet = VirtualNetworks("app subnet\n10.84.0.0/24")
            n_net_private = PrivateEndpoint("PE subnet\n10.84.1.0/24")
            n_ops_host = VM("vm-{prefix}\nWindows browser / CLI")
            n_net_entry = Bastions("bas-{prefix}\nBastion Basic")
        n_app_foundry = CognitiveServices("ai-{prefix}\nchild project: brokerage")
    n_ext_customer >> Edge(label="request: authenticated HTTPS") >> n_web_app
    n_web_app >> Edge(label="read/write: durable state") >> n_data_state
    n_web_app >> Edge(label="auth: consumer") >> n_id_workload
    n_web_app >> n_net_vnet >> n_net_private >> n_app_foundry
    n_ext_operator >> Edge(label="admin: browser RDP") >> n_net_entry >> n_ops_host
    n_ops_host >> Edge(label="admin: private browser / CLI\nuser identity separately") >> n_net_private
    n_web_app >> Edge(label="telemetry", style="dotted") >> n_ops_logs
    n_app_foundry >> Edge(label="telemetry", style="dotted") >> n_ops_logs

with Diagram("Company-only answers and human ownership", show=False,
             filename=str(root / "04-runtime-diagram"), direction="LR", graph_attr=attributes,
             node_attr={"fontname": "Segoe UI", "fontsize": "11", "labelloc": "t"}):
    n_ext_customer = Users("Signed-in customer")
    n_web_app = AppServices("App policy / ownership")
    n_app_agent = CognitiveServices("One Foundry agent\nselect source ID")
    n_data_knowledge = Storage("Approved exact wording\nversioned citation")
    n_data_cases = Storage("waiting -> claimed\n-> resolved / revision")
    n_ext_representative = Users("Assigned representative")
    n_ext_customer >> Edge(label="request: question") >> n_web_app
    n_web_app >> Edge(label="request: one bounded call") >> n_app_agent
    n_app_agent >> Edge(label="response: ID only") >> n_web_app
    n_web_app >> Edge(label="read: approved source") >> n_data_knowledge
    n_data_knowledge >> Edge(label="response: exact company text") >> n_ext_customer
    n_ext_customer >> Edge(label="request: human takeover") >> n_data_cases
    n_ext_representative >> Edge(label="write: claim / reply / resolve") >> n_data_cases
    n_data_cases >> Edge(label="response: human reply; AI paused") >> n_ext_customer
