# Allowed Azure resources for every FBC hack

## Authority and change boundary

This is the mandatory resource policy for **all** FBC reference scenarios, adaptations,
learner starters, coach solutions, Skillable packages and event deployments.
The source is the supplied November 10, 2026 workbook, with the owner's explicit
November 24, 2026 maintenance decisions below. It is not a scenario preference.

The [machine-readable constraints][constraints] are used by the local ARM checker.
This document also governs ownership, authentication, synthetic data and operational behavior
that a static resource/SKU check cannot prove.

- Deny unlisted services, resource types, SKUs and configurations. Allow only the listed
  minimum/recommended configurations, subject to the caps and decisions below.
- A hack prompt, saved brief, portal selection, imported manifest, reused scenario, historical
  example, architecture approval or deployment consent cannot override or amend this policy.
  Do not offer a per-hack exception, an override flag or an alternate policy supplied by a brief.
- Changes require an explicit request to maintain the FBC agentic solution's policy, like the
  request that created this file. Update this document, the machine-readable constraints,
  affected intake choices and focused tests together. Never edit policy just to make a hack pass.
- This policy limits the permitted design; it does not authorize provisioning, access grants,
  email, agent publication, policy assignment, purge or other destructive operations.
- Preserve stronger security, identity, residency and tenant requirements. If satisfying them
  needs an unlisted resource, report an incompatible design and stop the affected operation.
  Do not add a VM, Bastion, VNet, private endpoint, DNS zone, APIM, SQL Database, App Service
  or deployment script merely because an older skill/example uses one.
- Audit the complete transitive resource set, including AVM modules, child/extension resources,
  initialization scripts and both learner/reference modes. Existing resources are not an
  unreviewed route around the policy. Inline ARM deployments are packaging envelopes only,
  not permission to hide resources, link external templates or deploy across scopes.
- Historical evidence stays unchanged. Existing scenarios are not grandfathered for further
  deployment or new composition; assess their current design against this policy.
  Retired IDs remain readable as historical catalog metadata, never as new intake permissions.

## Owner decisions and conflict resolution

| Topic | Binding interpretation |
| --- | --- |
| Additions 17-25 | All nine explicitly approved, within the workbook's listed limits. |
| Analysis Services (6) | Denied; omit from hacks. |
| Service Fabric (7) | Denied; use Container Apps where suitable. |
| Prompt flow / ML workspaces (14) | Denied; use Agent Framework workflows where suitable. |
| Service Bus (5) | Basic and Standard allowed; select within scenario requirements. |
| Agent setup (13) | Basic default; standard only if security review requires data in the lab subscription. |
| Email domains (22) | Azure-managed only; the custom-domain suggestion does not override the deny rule. |
| GitHub plan (25) | Free only; the Team upgrade suggestion does not approve Team. |
| Authentication | Individual service entries override the workbook's general keys/identity statement. |
| Publication | Human-reviewed instruction changes; publication still requires explicit task authorization. |
| Key Vault teardown | Disposable-lab settings do not grant permission to purge any vault. |

These remaining inputs were **not** specified by the workbook or the owner's answers:

- **Approved regions:** no region IDs were supplied. "Yes" is not a region ID.
  Propose and verify one common region for a complete hack, but record its approval through
  an explicit policy maintenance edit before provisioning location-bound resources.
  Global service metadata locations do not authorize a workload region.
- **Exact model versions:** the owner selected the pasted model names:
  `gpt-4.1-mini`, `gpt-5-mini`, `gpt-4.1`, `gpt-5`, `text-embedding-3-small`.
  No exact versions were supplied. Do not invent versions or treat current availability as approval.
  Resolve the version allowlist through a policy edit; use `GlobalStandard` only, at most
  50,000 TPM per deployment. Approximately 10,000 TPM is the minimum planning configuration,
  not a reservation or proof of quota. Verify and record tokens per capacity unit for each
  approved model/version in `modelCapacityTpm`; do not assume every model has the same conversion.
- **Cosmos autoscale cap:** the workbook says at least 3,000 RU/s per project for standard
  agent setup, but supplies no numeric maximum account-throughput limit. That is not a
  3,000 RU/s upper cap. Provisioned autoscale stays blocked until a policy edit sets the cap
  and reconciles current service requirements. Single-region serverless remains permitted.

Continue independent local preparation while these are unresolved. Do not claim a deployable
or policy-compliant complete hack when a required configuration remains blocked.

## Resource and SKU register

Every row retains its workbook number. Non-Azure plans are still governed even though Azure Policy
cannot enforce their subscription tier.

| No. | Service and permitted configuration | Deployment owner |
| --- | --- | --- |
| 1 | Blob: one StorageV2 account, Standard_LRS, Hot; TLS 1.2 minimum. | Starter |
| 2 | Storage Queues: reuse the same account as Blob; no second account/SKU. | Starter |
| 3 | Event Grid: Basic custom/system topics and event subscriptions only; no namespaces or domains. | Starter |
| 4 | Container Apps: Consumption only; 0.25 vCPU/0.5 GiB or 0.5 vCPU/1 GiB; maximum 3 replicas. | Starter |
| 5 | Service Bus: Basic queues, or Standard for topics/subscriptions; no Premium. | Starter |
| 6 | Analysis Services: denied by owner decision (workbook had conditional D1). | None |
| 7 | Service Fabric: denied by owner decision (workbook had conditional Basic/3 nodes). | None |
| 8 | Cosmos DB: NoSQL, single region, serverless; provisioned autoscale pending a numeric cap. | Starter |
| 9 | AI Search: basic or standard (S1), exactly 1 replica and 1 partition. | Starter or learners |
| 10 | Key Vault: standard, RBAC, 7-day soft delete, purge protection off for disposable labs only. | Starter |
| 11 | Foundry: AIServices/S0, direct child projects/connections; approved regions only. | Starter/learners |
| 12 | Models: approved names AND exact versions, GlobalStandard, maximum 50,000 TPM each. | Starter or learners |
| 13 | Agent Service: account/project capability hosts; basic default, conditional standard. | Learners/starter |
| 14 | Prompt flow / Machine Learning workspaces and compute: denied by owner decision. | None |
| 15 | Automation: Basic cloud runbooks/schedules/webhooks; no hybrid workers. | Starter or learners |
| 16 | Azure DevOps: Basic free only; prefer GitHub; no Azure billing account. | No automatic setup |
| 17 | User-assigned managed identity and federated identity credentials; no SKU. | Starter |
| 18 | Constrained role assignments: only service roles below; no unrestricted delegation. | Lab profile |
| 19 | Registry: Basic/Standard; no Premium; admin off unless an approved key path is used. | Starter |
| 20 | Log Analytics: PerGB2018, 30 days, explicit daily cap at most 5 GB (minimum plan: 1 GB). | Starter |
| 21 | Application Insights: workspace-based only, no classic components. | Starter |
| 22 | Communication Services Email: pay-as-you-go, Azure-managed domains only. | Starter |
| 23 | Logic Apps: Consumption workflows only; no Standard workflow apps or integration accounts. | Learners |
| 24 | Functions: FC1 Flex Consumption, 512 or 2,048 MB; no Premium/Dedicated plans or web apps. | Learners |
| 25 | GitHub Free with Actions; OIDC to the managed identity; no stored Azure secrets. | Learners or instructors |

The starter deploys the Foundry account; learners create projects.
Learners use basic Agent Service setup; the starter handles standard setup when its review condition is met.

For Container Apps, scale to zero normally; one minimum replica is recommended only during live sessions.
Keep jobs on Consumption and bound their execution scale as well; do not use jobs to bypass container limits.
No Dedicated workload profiles or GPUs.

AI Search excludes Free, S2, S3, L1, L2 and Serverless. Cosmos DB excludes additional regions,
multi-region writes and APIs other than NoSQL. Key Vault excludes Premium and Managed HSM.
Foundry excludes other Cognitive Services kinds and SKUs. Provisioned model throughput
and other model deployment SKUs are denied.

Standard Agent Service, when its security-review condition is satisfied, may use only the
Storage, Cosmos DB and Search configurations in this register; it cannot resolve the pending
Cosmos cap by assumption. Record the review and the required in-subscription storage decision.

## Resource types

The exact allowed ARM type names and field constraints are in [the JSON policy][constraints].
Parent permission never implies permission for every child type. In particular:

- Storage: account, blob service/containers and queue service/queues only.
- Event Grid: topics, system topics and event subscriptions.
- Container Apps: managed environments, container apps and jobs.
- Service Bus: namespaces, queues, topics and topic subscriptions.
- Cosmos DB: database accounts, SQL databases/containers and SQL data-role assignments.
- Foundry: AIServices accounts, direct projects/connections, deployments and capability hosts.
- Automation: accounts, runbooks, schedules and webhooks, not hybrid workers.
- Identity: user-assigned identities/federated credentials and constrained Azure role assignments.
- Monitoring: Log Analytics workspaces and workspace-based Application Insights.
- Email: communication services, email services and Azure-managed email domains.
- Logic/Functions: Consumption workflows, FC1 serverfarms and function apps only.

Unlisted supporting resources require a deliberate policy edit, even if they are cheap or
normally generated automatically. A pre-existing Skillable resource group is deployment scope,
not permission to create another group or other out-of-list infrastructure.

## Identity, data and operations

Use synthetic data and fake events only. Reuse the repository company/person catalogs.
Storage holds synthetic JSON/CSV/documents and RAG sources; Container Apps hosts the synthetic
front end and event generators. Foundry owns agents, RAG, memory and supported actions.
No real email is sent merely because an email resource is permitted.

Prefer managed identity and narrowly scoped access. Shared key access, registry admin access
and other key paths are off unless the approved design explicitly uses that permitted path.
Never commit keys, connection strings, credentials, webhook tokens or signed trigger URLs.
One approved identity option is not a requirement to share an overprivileged identity.

| Service | Keyless access roles / service-native access |
| --- | --- |
| Blob | Storage Blob Data Contributor (write), Storage Blob Data Reader (read) |
| Queue | Storage Queue Data Contributor, Message Sender or Message Processor |
| Event Grid | EventGrid Data Sender; delivery identity gets target-service access |
| Container Apps | AcrPull and the data roles on called services |
| Service Bus | Azure Service Bus Data Sender / Data Receiver |
| Cosmos DB | Cosmos DB Built-in Data Contributor via sqlRoleAssignments; Cosmos DB Operator for setup |
| Search | Search Index Data Contributor / Data Reader; Search Service Contributor for index creation |
| Key Vault | Key Vault Secrets User / Secrets Officer |
| Foundry/models | Foundry User (formerly Azure AI User); Cognitive Services OpenAI User as applicable |
| Agent standard setup | Project identity: Blob Data Contributor, Cosmos DB Operator and required Search roles |
| Automation | Foundry User and the Storage/Cosmos roles needed to read feedback |
| User-assigned identity | Managed Identity Operator to attach the identity |
| Registry | AcrPull for apps, AcrPush for builders/CI |
| Monitoring | Log Analytics Reader; Monitoring Metrics Publisher for supported ingestion |
| Email | Contributor or a narrower custom role on the Communication Services resource |
| Logic Apps | Logic App Contributor for builders; workflow identity gets target data roles |
| Functions | Storage Blob Data Owner for host storage and necessary target data roles |
| GitHub | OIDC federated identity with Foundry User on the target project |

The lab profile may preassign needed roles or use conditioned Role Based Access Control
Administrator rights limited to the listed necessary roles. This does not approve unrestricted
Owner, User Access Administrator, arbitrary role definitions or grant scopes.
Keep workload, learner and deploying-user permissions separate. If the deployment-user access
contract cannot be satisfied within lab-profile permissions, report that conflict rather than broaden rights.

Include content safety, tracing and monitoring in every challenge. Use the approved Foundry
capabilities plus Application Insights and Log Analytics, not an unlisted separate AI account.
For feedback-driven instruction updates, prefer GitHub Free/Actions with OIDC: Automation drafts a PR,
a human reviews it, then an explicitly authorized workflow publishes an agent version.
The workbook's direct-runbook alternative is only for a deliberately selected no-version-control flow;
it never authorizes autonomous publication.

Verify current prices, grants, technical support, model versions, regional availability and quota
before deployment, including the planned scale of up to 300 learners.
Workbook estimates and dates are planning inputs, not verified present-day service facts.
Keep teardown explicit and scoped to a confirmed disposable lab; never purge automatically.

## Validation and enforcement limits

Before deployment and before review/composition, compile the actual Bicep to ARM and run:

```powershell
python scripts\resource_policy.py <compiled-template.json>
```

Run this for reference and starter/coach templates, including all inline modules.
The checker uses only the repository policy: no prompt override or alternate-policy flag.
It rejects unlisted resource types, forbidden SKUs, checked cap violations and unresolved
policy-constrained values. Constrained ARM parameters need bounded `allowedValues`;
a safe default with an unrestricted override is not proof of compliance.
Unsupported expressions fail explicitly, never as assumed-safe values.

Skillable delivery build/validation runs the same check automatically against its single
ARM template, including both modes and conditional resources. A condition is not an exemption.
Local checks do not prove Azure API validity, role/ownership correctness, every runtime script's
behavior, synthetic-data provenance, quota, security-review decisions or actual cloud enforcement.
Review those requirements separately using the existing workflow gates.
Azure-side denial requires Skillable/tenant Azure Policy assignment and RBAC outside this local edit;
the editable checkout is not a tamper-proof security boundary.

[constraints]: ../assets/allowed-azure-resources.json
