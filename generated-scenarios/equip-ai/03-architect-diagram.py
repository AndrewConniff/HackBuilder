"""Render the confirmed equip-ai resource boundaries; this is not deployment evidence."""

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.azure.compute import AppServices
from diagrams.azure.iot import IotHub
from diagrams.azure.ml import CognitiveServices
from diagrams.azure.monitor import Monitor
from diagrams.azure.network import PrivateEndpoint
from diagrams.azure.storage import BlobStorage
from diagrams.onprem.client import Users
from diagrams.onprem.compute import Server

OUTPUT = Path(__file__).resolve().parent

with Diagram(
    "Adatum Corporation: private equipment Operations reference",
    filename=str(OUTPUT / "03-architect-diagram"),
    show=False,
    direction="TB",
    graph_attr={"dpi": "150", "pad": "0.6", "nodesep": "0.9", "ranksep": "1.1", "bgcolor": "white"},
    node_attr={"fontsize": "11"},
):
    n_web_users = Users("Operations support\nLocal app accounts")
    n_ops_admin = Users("Deploying administrator\nOwn Azure credentials / MFA")
    n_int_devices = Server("WA equipment\nPer-device X.509")
    with Cluster("rg-equip-ai / Central US (restored reference)"):
        n_int_hub = IotHub("IoT Hub B2\nPublic TLS ingress")
        n_data_blob = BlobStorage("Hot LRS Blob\nDefault deny + trusted IoT\nNo keys / anonymous access")
        n_id_accounts = BlobStorage("Separate accounts container\nSalted hashes / lockout\nDurable session keys")
        n_app_foundry = CognitiveServices("Foundry S0\nDirect child project\nBasic agent + model")
        n_ops_monitor = Monitor("Sanitized diagnostics\nNo chat / event bodies")
        with Cluster("Scenario VNet 10.247.0.0/24 (saved regional conflict check; not peering certification)"):
            n_ops_runner = Server("D2als_v7 private VM\nDesktop / browser / CLI\nSeparate automation MI")
            with Cluster("AzureBastionSubnet 10.247.0.192/26"):
                n_ops_bastion = Server("Bastion Standard\nNative tunnel / HTTPS\nHuman acceptance pending")
            with Cluster("Delegated App Service integration subnet"):
                n_web_api = AppServices("Public HTTPS web/API\nRead-only telemetry identity")
                n_app_cleaner = AppServices("Private cleanup app\nSeparate delete identity")
            with Cluster("Private endpoint subnet + private DNS"):
                n_data_endpoint = PrivateEndpoint("Blob Private Link")
                n_app_endpoint = PrivateEndpoint("Foundry Private Link")
                n_ops_endpoint = PrivateEndpoint("Cleaner + SCM\nPrivate deployment")
    n_ops_admin >> Edge(label="auth: Azure IAM / HTTPS") >> n_ops_bastion
    n_ops_bastion >> Edge(label="private RDP 3389\nNo VM public IP / no SSH") >> n_ops_runner
    n_ops_admin >> Edge(label="automation: ARM Run Command\nsmall bootstrap / no credentials", style="dashed") >> n_ops_runner
    n_ops_admin >> Edge(label="admin: stage/clean ZIP\nSCM data outside wwwroot", style="dashed") >> n_web_api
    n_ops_runner >> Edge(label="human: own Azure identity\nbrowser / CLI administration", style="dashed") >> n_app_endpoint
    n_ops_runner >> Edge(label="human: own-user Blob CRUD", style="dashed") >> n_data_endpoint
    n_ops_runner >> Edge(label="read: MI / SCM artifact\nSHA-256 verification", style="dashed") >> n_web_api
    n_ops_runner >> Edge(label="publish: MI / private SCM", style="dashed") >> n_ops_endpoint
    n_ops_runner >> Edge(label="initialize: MI / real agent", style="dashed") >> n_app_endpoint
    n_web_users >> Edge(label="auth: local login / HTTPS\nSecure session + CSRF") >> n_web_api
    n_int_devices >> Edge(label="event: MQTT/TLS") >> n_int_hub
    n_int_hub >> Edge(label="write: MI / trusted-service exception") >> n_data_blob
    n_web_api >> Edge(label="read: MI") >> n_data_endpoint >> n_data_blob
    n_data_endpoint >> Edge(label="auth state: web MI / scoped RW") >> n_id_accounts
    n_ops_runner >> Edge(label="initialize: MI / salted seed only", style="dashed") >> n_id_accounts
    n_app_cleaner >> Edge(label="write: ETag delete") >> n_data_endpoint
    n_ops_endpoint >> Edge(label="admin: VNet-connected installer", style="dashed") >> n_app_cleaner
    n_web_api >> Edge(label="request: MI / bounded agent") >> n_app_endpoint >> n_app_foundry
    [n_web_api, n_app_cleaner, n_int_hub] >> Edge(label="telemetry: counts/errors", style="dashed") >> n_ops_monitor
