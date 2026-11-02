"""Render the provisional reference architecture and runtime flow without accessing Azure."""

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.azure.compute import ContainerApps, ContainerRegistries
from diagrams.azure.database import CosmosDb
from diagrams.azure.identity import ManagedIdentities
from diagrams.azure.integration import APIManagement
from diagrams.azure.ml import CognitiveServices
from diagrams.azure.monitor import LogAnalyticsWorkspaces
from diagrams.azure.security import KeyVaults
from diagrams.azure.storage import BlobStorage
from diagrams.onprem.client import Users

ROOT = Path(__file__).resolve().parent
GRAPH = {"dpi": "140", "pad": "0.5", "nodesep": "0.7", "ranksep": "0.9", "fontsize": "18"}


def render_architecture() -> None:
    """Show the actual module resources; names use the same deployment suffix notation as Bicep."""
    with Diagram(
        "Brokerage education - provisional, not deployed",
        filename=str(ROOT / "03-architect-diagram"),
        show=False,
        direction="LR",
        graph_attr=GRAPH,
        node_attr={"fontsize": "11"},
    ):
        n_ext_customer = Users("Anonymous customer")
        with Cluster("Resource group: rg-{environment}"):
            n_edge_gateway = APIManagement("apim-fin-{suffix}\nStandard v2 / public HTTPS")
            n_id_workloads = ManagedIdentities("Gateway + app identities\nseparate least-privilege roles")
            n_ops_logs = LogAnalyticsWorkspaces("log-fin-{suffix}\nplatform diagnostic export")
            with Cluster("vnet-fin-{suffix} / 10.73.0.0/16 (provisional)"):
                with Cluster("apps /23; gateway /24; agents /24; endpoints /24"):
                    n_app_chat = ContainerApps("ca-fin-{suffix}\nInternal environment")
                    n_app_agent = CognitiveServices("ai-fin-{suffix}\nProject: brokerage / one agent")
                    n_data_faq = BlobStorage("stfin{suffix}\nSynthetic FAQs + agent files")
                    n_data_threads = CosmosDb("cosmos-fin-{suffix}\nAgent thread persistence")
                    n_data_search = CognitiveServices("srch-fin-{suffix}\nStandard setup vector store")
                    n_sec_vault = KeyVaults("kv-fin-{suffix}\nReceipt signing / no API keys")
                    n_ops_images = ContainerRegistries("acrfin{suffix}\nPrivate image delivery")
            n_ext_customer >> Edge(label="request: public HTTPS") >> n_edge_gateway
            n_edge_gateway >> Edge(label="request: private + MI token") >> n_app_chat
            n_app_chat >> Edge(label="request: private + MI") >> n_app_agent
            n_app_chat >> Edge(label="read: private + MI") >> n_data_faq
            n_app_chat >> Edge(label="request: sign digest + MI") >> n_sec_vault
            n_app_agent >> Edge(label="read/write: private + project MI") >> [
                n_data_faq, n_data_threads, n_data_search
            ]
            n_ops_images >> Edge(label="read: MI image pull", style="dashed") >> n_app_chat
            n_id_workloads >> Edge(label="auth: scoped RBAC", style="dashed") >> [n_app_chat, n_edge_gateway]
            n_app_chat >> Edge(label="telemetry: no prompts", style="dashed") >> n_ops_logs


def render_runtime() -> None:
    """Show each identity boundary separately from public customer anonymity."""
    with Diagram(
        "Brokerage runtime - intended flow, not live evidence",
        filename=str(ROOT / "04-runtime-diagram"),
        show=False,
        direction="LR",
        graph_attr=GRAPH,
    ):
        customer = Users("1. Public customer")
        gateway = APIManagement("2. APIM\nIP + global rate limit")
        app = ContainerApps("3. Private app\nJWT issuer/audience/oid/tid")
        source = BlobStorage("4. Private FAQ\nBlob Data Reader")
        agent = CognitiveServices("5. Version-pinned agent\nFoundry Agent Consumer")
        key = KeyVaults("6. Sign answer digest\nKey-scoped Crypto User")
        customer >> Edge(label="request: no customer login") >> gateway
        gateway >> Edge(label="auth/request: gateway MI") >> app
        app >> Edge(label="read: app MI") >> source
        app >> Edge(label="request: app MI + source context") >> agent
        app >> Edge(label="request: SHA-256 / app MI") >> key
        key >> Edge(label="response: signature + key version") >> app
        app >> Edge(label="response: answer/citations/receipt") >> gateway


if __name__ == "__main__":
    render_architecture()
    render_runtime()
