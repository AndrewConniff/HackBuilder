"""Render the proposed private-inbound architecture and human-controlled runtime."""

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.azure.compute import AppServices, VMWindows
from diagrams.azure.identity import ManagedIdentities
from diagrams.azure.ml import CognitiveServices
from diagrams.azure.monitor import ApplicationInsights, LogAnalyticsWorkspaces
from diagrams.azure.network import PrivateEndpoint
from diagrams.azure.storage import BlobStorage
from diagrams.generic.compute import Rack
from diagrams.onprem.client import Users

ROOT = Path(__file__).resolve().parent
GRAPH = {"bgcolor": "white", "pad": "0.5", "nodesep": "0.7", "ranksep": "0.9", "dpi": "130"}
NODE = {"fontname": "Segoe UI", "fontsize": "11"}

with Diagram(
    "Bellows College | proposed reference, not deployed",
    filename=str(ROOT / "03-architect-diagram"),
    show=False,
    direction="TB",
    graph_attr=GRAPH,
    node_attr=NODE,
):
    n_ext_teacher = Users("Teacher browser\nLocal app accounts")
    n_ext_operator = Users("Operator browser\nDeploying Azure user")
    with Cluster("Scenario resource group: rg-{environment} | location not selected"):
        n_app_web = AppServices("TeachingReview.Web\nLinux B1")
        n_id_app = ManagedIdentities("App identity\nConsumer + Blob")
        n_ops_insights = ApplicationInsights("Scrubbed telemetry")
        n_ops_logs = LogAnalyticsWorkspaces("Scenario logs")
        with Cluster("VNet 10.71.0.0/16 | proposed; overlap unverified"):
            with Cluster("snet-app 10.71.1.0/26"):
                n_net_integration = Rack("App VNet integration")
            with Cluster("snet-data 10.71.2.0/26"):
                n_net_foundry = PrivateEndpoint("Foundry private endpoint")
                n_net_blob = PrivateEndpoint("Blob private endpoint")
            with Cluster("snet-management 10.71.3.0/27"):
                n_ops_vm = VMWindows("Private operator VM\nBrowser + CLI + initializer")
            with Cluster("AzureBastionSubnet 10.71.4.0/26"):
                n_sec_bastion = Rack("Bastion Basic\nNo VM public IP")
        with Cluster("Private data ingress | public networking disabled"):
            with Cluster("Foundry AIServices account / direct child project"):
                n_app_foundry = CognitiveServices("Basic prompt agents\nCurriculum + Accessibility")
                n_app_model = CognitiveServices("gpt-4.1\nGlobalStandard provisional")
            n_data_blob = BlobStorage("Workflow / accounts / keys\nStandard LRS")
    n_ext_teacher >> Edge(label="request: HTTPS + cookie") >> n_app_web
    n_app_web >> Edge(label="auth: managed identity", style="dashed") >> n_id_app
    n_app_web >> Edge(label="request: VNet egress") >> n_net_integration
    n_net_integration >> [n_net_foundry, n_net_blob]
    n_net_foundry >> n_app_foundry >> n_app_model
    n_net_blob >> Edge(label="read/write: ETag") >> n_data_blob
    n_ext_operator >> Edge(label="admin: Bastion RDP") >> n_sec_bastion >> n_ops_vm
    n_ops_vm >> Edge(label="admin: own Azure sign-in") >> n_net_foundry
    n_ops_vm >> Edge(label="write: private initialization") >> n_net_blob
    n_app_web >> Edge(label="telemetry", style="dotted") >> n_ops_insights >> n_ops_logs

with Diagram(
    "Material review | human ownership and version gates",
    filename=str(ROOT / "04-runtime-diagram"),
    show=False,
    direction="TB",
    graph_attr=GRAPH,
    node_attr=NODE,
):
    n_ext_author = Users("1. Author submits\nSynthetic material + rubric")
    with Cluster("Application coordinator | deterministic state, role and version checks"):
        n_app_intake = AppServices("2. Reserve review attempt\nTwo calls, 120 seconds")
        n_app_curriculum = CognitiveServices("3. Curriculum agent\nEvidence / rubric findings")
        n_app_access = CognitiveServices("4. Accessibility agent\nClarity / structure findings")
        n_app_gate = AppServices("5. Require both receipts\nNo partial-success handoff")
        n_data_state = BlobStorage("Versioned durable state\nETag + audit history")
        n_app_failure = Rack("Failure / stale / denied\nExplicit retry, no approval")
    n_ext_peer = Users("6. Peer teacher\nHuman feedback")
    n_ext_revision = Users("7. Author accepts feedback\nOr revises: new reviews required")
    n_ext_lead = Users("8. Lead teacher\nApprove current version only")
    n_app_release = Rack("9. Internal release state\nNo LMS / publishing")
    n_ext_author >> Edge(label="request") >> n_app_intake
    n_app_intake >> Edge(label="request: MI") >> n_app_curriculum
    n_app_curriculum >> Edge(label="request: same version") >> n_app_access
    n_app_access >> Edge(label="response: receipts") >> n_app_gate
    [n_app_intake, n_app_gate] >> Edge(label="write: conditional") >> n_data_state
    n_app_gate >> Edge(label="request: human handoff") >> n_ext_peer
    n_ext_peer >> Edge(label="response: feedback") >> n_ext_revision
    n_ext_revision >> Edge(label="request: unchanged version") >> n_ext_lead
    n_ext_revision >> Edge(label="write: revision resets review", style="dashed") >> n_app_intake
    n_ext_lead >> Edge(label="write: authorized decision") >> n_app_release
    n_app_gate >> Edge(label="response: failed review", style="dashed") >> n_app_failure
    n_ext_lead >> Edge(label="response: stale / unauthorized", style="dashed") >> n_app_failure
