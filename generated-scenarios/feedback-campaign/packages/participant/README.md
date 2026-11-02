# Adatum campaign listener — minimum starter

Media & Communications; `businessUnits: ["sales", "marketing"]`.
Marketing owns campaign engagement and product review; Sales owns subscriber recovery.
Nino Kapanadze operates campaigns, Petra Bartosova reviews product issues,
and Eesha Chatterjee handles conflict resolution.

This project provides resource-group isolation, destination guards and
indispensable synthetic fixtures only. No app, Foundry account/project/model,
agent, tool, queue, state store or completed routing implementation is included.
Learners choose and build the missing capabilities. No application URL exists.
Run `python scripts/status.py` to verify the intentional not-configured state.

On separately authorized rollout use environment `01-feedback-campaign-hack`
and group `rg-01-feedback-campaign-hack`, with explicit destination subscription,
tenant and region. Set all five azd variables before provision; the guard
refuses coach/unrelated groups and missing values. Use `azd up` for future
destination acceptance, not as an instruction to deploy in this local phase.
The organizer grants scoped control-plane access to your group; request only
the service data roles needed by your chosen runtime identity.
Never use reference accounts, keys, Entra consent shortcuts or shared targets.

Start with the public challenges. Preserve your working prompt checkpoint;
the authenticated durable action is a bounded hybrid/code increment, not
a requirement to recreate a web application during this hack.
See [application access boundaries](docs/participant-access.md) and
`contracts/integration.json`. No credentials are included.
