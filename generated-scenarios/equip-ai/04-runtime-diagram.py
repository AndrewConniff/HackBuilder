"""Render the confirmed single-agent workflow and independent telemetry lifecycle."""

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.azure.compute import AppServices
from diagrams.azure.iot import IotHub
from diagrams.azure.ml import CognitiveServices
from diagrams.azure.storage import BlobStorage
from diagrams.onprem.client import Users
from diagrams.onprem.compute import Server

OUTPUT = Path(__file__).resolve().parent

with Diagram(
    "equip-ai: authorized evidence, not machine control",
    filename=str(OUTPUT / "04-runtime-diagram"),
    show=False,
    direction="TB",
    graph_attr={"dpi": "150", "pad": "0.6", "nodesep": "0.9", "ranksep": "1.0", "bgcolor": "white"},
    node_attr={"fontsize": "11"},
):
    with Cluster("Observed private installation path"):
        n_ops_local = Server("Local azd hooks\nLinux publish / hash ZIP")
        n_ops_runner = Server("ARM Run Command\nPrivate D2als_v7 VM / MI")
        n_ops_local >> Edge(label="ARM Run Command / small bootstrap") >> n_ops_runner
    with Cluster("Approved human administration; own-user acceptance pending"):
        n_ops_admin = Users("Deploying user\nOwn Azure credentials / MFA")
        n_ops_bastion = Server("Bastion Standard\nNative RDP tunnel")
        n_ops_admin >> Edge(label="auth: Azure IAM / HTTPS") >> n_ops_bastion
        n_ops_bastion >> Edge(label="private desktop / browser / CLI\nSame VM, no public IP") >> n_ops_runner
    with Cluster("Independent event path"):
        n_int_device = Server("1. Certified WA device")
        n_int_hub = IotHub("2. Authenticate device\n60-second JSON batches")
        n_data_blob = BlobStorage("3. Hot Blob\nRouted JSON envelopes")
        n_app_cleaner = AppServices("Cleanup every 5 minutes\nETag / fully expired only")
        n_int_device >> Edge(label="event: X.509 / TLS") >> n_int_hub
        n_int_hub >> Edge(label="write: managed identity") >> n_data_blob
        n_app_cleaner >> Edge(label="write: delete; target 130 minutes") >> n_data_blob
    with Cluster("Operations single-agent tool loop; 30 seconds / 3 rounds / 4 tools"):
        n_web_user = Users("Support question\nHuman owns inspection")
        n_id_auth = AppServices("4. Local session + CSRF\nDurable account / role check")
        n_web_api = AppServices("5. API / site authorization\nBounded request")
        n_app_agent = CognitiveServices("6. Real Foundry agent\nAdvisory; no actuation")
        n_app_tools = AppServices("7. Typed read tools\nValidate / deduplicate\nDeterministic statistics")
        n_web_result = Users("8. Cited fresh result\nOr explicit error / gap")
        n_web_user >> Edge(label="auth: local account / HTTPS") >> n_id_auth
        n_id_auth >> Edge(label="request: secure session + question") >> n_web_api
        n_web_api >> Edge(label="request: MI / Private Link") >> n_app_agent
        n_app_agent >> Edge(label="request: typed function") >> n_app_tools
        n_app_tools >> Edge(label="read: authorized; age < 120 min") >> n_data_blob
        n_app_tools >> Edge(label="response: summaries / evidence IDs") >> n_app_agent
        n_app_agent >> Edge(label="response: validate citations/freshness") >> n_web_api
        n_web_api >> Edge(label="response: no stored chat") >> n_web_result
    n_ops_runner >> Edge(label="initialize agent version\nbefore app acceptance", style="dashed") >> n_app_agent
    n_ops_runner >> Edge(label="human: own-user browser / CLI\nSeparate from automation MI", style="dashed") >> n_app_agent
    n_ops_runner >> Edge(label="SCM publish / private DNS", style="dashed") >> n_app_cleaner
    n_ops_local >> Edge(label="stage/clean ZIP: authenticated SCM data", style="dashed") >> n_web_api
    n_ops_runner >> Edge(label="download: MI / SHA-256", style="dashed") >> n_web_api
