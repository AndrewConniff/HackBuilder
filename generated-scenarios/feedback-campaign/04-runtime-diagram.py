"""Reproducible routing and durable human checkpoint diagram."""
from pathlib import Path
from diagrams import Cluster, Diagram, Edge
from diagrams.azure.compute import AppServices
from diagrams.azure.integration import ServiceBus
from diagrams.azure.storage import StorageAccounts
from diagrams.generic.compute import Rack
from diagrams.onprem.client import Users

root = Path(__file__).resolve().parent
with Diagram("Feedback Campaign - routing with human control", show=False,
             filename=str(root / "04-runtime-diagram"), direction="TB",
             graph_attr={"fontsize": "20", "pad": "0.6", "nodesep": "1.6"}):
    intake = ServiceBus("Stream posts or\nauthenticated intake\nstable source ID")
    persisted = StorageAccounts("Received\nimmutable rule snapshot")
    agent = Rack("Campaign Listener\nFoundry MI invocation / policy grounding")
    control = AppServices("Deterministic Control\nvalidate structured sentiment")
    auto = Rack("Overall positive >=80%\nauto draft")
    pm = Users("Else negative >=89%\nProduct Manager")
    cr = Users("Else Sales\nConflict Resolution Specialist")
    gate = StorageAccounts("AwaitingHuman\nETag + assigned role + edited reply")
    outbox = StorageAccounts("PendingSend\ntransactional case outbox")
    replies = ServiceBus("Reply stream accepted\nNOT external delivery")
    failed = StorageAccounts("Failed / DLQ\nexplicit repair + retry")
    admin = Users("ControlAdmin\nsave immutable version / promote")
    rules = StorageAccounts("Active Control pointer\nETag promotion")
    intake >> persisted >> agent >> control
    rules >> Edge(label="snapshot at intake") >> persisted
    admin >> Edge(label="human-controlled") >> rules
    control >> auto >> outbox
    control >> [pm, cr]
    [pm, cr] >> Edge(label="explicit approval") >> gate >> outbox
    outbox >> Edge(label="stable reply ID / dedupe") >> replies
    agent >> Edge(label="error / invalid schema", color="red") >> failed
    failed >> Edge(label="explicit retry", style="dashed") >> persisted
