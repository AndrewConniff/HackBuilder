# Adatum campaign listener — complete coach reference

Private, sanitized deployable reference for Media & Communications.
Business units: `["sales", "marketing"]`. Target framework: .NET 10.
Native Foundry prompt agent; application-hosted durable routing and HITL.
This package is locally validated, not deployed.

Read [deployment](deployment.md), [participant access](docs/participant-access.md)
and [coach access](docs/coach-access.md). Do not share this completed source
as the learner starter. No provider/email delivery adapter is implemented.
Model scores are estimates, not calibrated probabilities.

Build: `dotnet build src/FeedbackCampaign.Web -c Release`.
Test: `dotnet test tests/FeedbackCampaign.Tests.csproj -c Release`.
Installation guards: `python -m unittest discover -s tests -p "test_*.py"`.
