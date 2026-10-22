# Archived oil and gas scenario input

This preserves a colleague's original scenario prompt for reuse. It is not an
agent or an active workflow. Extract only the business story and explicit
scenario requirements from this historical source. Disregard its old agent
metadata, automatic package/team rollout, and deployment-completion instructions;
the current workflow contract controls all sequencing and approval.

---
name: oilgas-field-ops-agent
description: oilgas-field-ops-agent
disable-model-invocation: true
---
 ---
description: "Build the oil and gas field operations Foundry agent solution and hack"
agent: "az-01-conductor"
tools:
  - agent
  - edit/createFile
  - edit/editFiles
  - read/readFile
  - search/listDirectory
  - execute/runInTerminal
argument-hint: Optionally describe changes to the saved oil and gas field operations scenario
---

# Build Oil and Gas Field Operations Agent

Run the complete conductor workflow for project `oilgas-field-ops-agent` with two
hacker teams. Preserve the recovered scenario below as the source business prompt,
then apply the current-run overrides that follow it.

## Recovered Original Prompt

create a solution and hack for a scenario where the company (use a fake name for
the company) is an oil and gas company. The solution they want to build is where
they have data in Azure Cosmos DB The database contains the locations for natural
gas wells in latitude and longitude by state. In Azure Storage, they keep pdf
documents that contain the standard operating procedures for field operations for
each location, including local contact information and what type of well and other
machinery is onsite. Field operatives currently have to look this information up.
They want an agentic solution in Azure AI Foundry that will use RAG to provide
answers to the field agents via a web page chat bot. While the bot should
primarily only return results from the data, it will search the internet if
directly asked to
do so - the solution should have a separate agent the main agent or orchestrator
calls to make web calls and another agent that performs RAG operations against an
Azure AI Search resource with two indexes. One to index location data from Azure
Cosmos DB, the other to index the SOP and field manuals from Azure Storage. The
application bot should call different indexes based on the prompt so there
should be an agent for each with the appropriate index name. create everything
needed for
this and load in the seed data and pdf files - to make it easy lets just do 5
locations in Texas and 5 locations in Oklahoma - the supporting documents for
each location should be different slightly. Make sure the deployment script
loads all
the data in the storage and Azure Cosmos DB. Name the hacking resource group
AgentChallenge and the coaches version (the full working version with the agents)
CoachesResources - four each append a 6 digit number. Make sure the Azure
Cosmos DB account uses a minimal-cost configuration suitable for this small
dataset while remaining compatible with Azure AI Foundry and usable as an
Azure AI Search index
source. Deploy all Azure resources in West US 2. If it is possible, create an
MCP server (may need a host) for the application and make that a later
challenge (the learners would move the code from the application for the skills
calls to the MCP )
If it is not applicable don't force it.

## Current Run Overrides

- Treat East US as the requested region instead of West US 2. Validate it against
  the configured subscription before generation or deployment, and recommend a
  different region if every required resource cannot be deployed there.
- Use `gpt-5` version `2025-08-07` instead of GPT-4o. Validate the deployment type,
  SKU, quota, and live capacity before selecting it.
- Use a Foundry resource with a direct child project. Do not create a hub, AI hub,
  hub module, `hubResourceId`, or Azure Machine Learning workspace.
- Build a non-empty coach solution web application for a fictional oil and gas
  company. Use a polished, responsive Fluent 2 interface with the scenario's field
  operations theme, realistic branding and seed content, clear navigation, loading
  and error states, and an immediately usable chatbot as the primary experience.
- Connect the coach web application's backend chat route to the deployed direct
  Foundry project and orchestrator agent using managed identity or
  `DefaultAzureCredential`. The orchestrator must route requests to the
  location, SOP, and web-search specialist agents as designed. Do not use mock,
  canned, placeholder, or client-side-only chatbot responses.
- Treat an empty Container Apps or App Service page, a default framework page,
  a static chatbot shell, missing Foundry configuration, or an unreachable
  agent as a failed deployment. Provisioning the hosting resource alone is not
  completion.
- Run the coach solution web application locally. Use browser automation at
  desktop and mobile widths to verify meaningful themed content, navigation,
  chatbot loading and error states, and a real grounded chatbot response
  returned through the backend from the Foundry orchestrator.
- Repeat the browser acceptance checks against the deployed coach URLs. Record the
  tested URLs, HTTP status, visible page evidence, chat prompt, grounded response,
  invoked agent evidence, and telemetry request or trace ID in the deployment
  summary. Do not report success from a health endpoint alone.
- Deploy the coach package once and the participant package once per team. Do not
  report completion until the coach and both participant deployments are healthy.
