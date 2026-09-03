# Scenario supporting-artifact inventory

## Purpose

Every scenario requires a scenario-level `nextsteps.MD` that inventories the
synthetic data, documents, media, contracts, evaluation sets, and installation
scripts needed by the challenges and deployable applications.

The inventory is written during HackCreator plan mode. It is updated during
package mode and after deployment. It specifies future work without allowing a
runtime dependency to remain missing when deployment testing begins.

## Artifact detail contract

Create one `ART-NNN` entry for each logical artifact. A collection may use one
entry only when the entry enumerates every proposed filename and gives one
shared schema, target, creation method, and acceptance test.

Every entry must provide:

| Detail | Required content |
| --- | --- |
| Purpose and challenge use | Business purpose and exact setup or challenge dependency |
| Deployment classification | `deployment-critical` or `release-enrichment` |
| Status | `planned`, `created`, `validated`, `packaged`, or `azure-verified` |
| Proposed filename | Exact filename or an enumerated list of exact filenames |
| Repository destinations | Every package-relative destination for the created file |
| Package visibility | Public learner-safe, private coach, or deployable package only |
| Artifact type and format | File format, encoding, MIME type, and top-level shape |
| Azure target | Service, database or container, table, path, index, queue, or topic |
| Structure | Schema, document outline, or media composition |
| Required fields or sections | Names, types, required rules, and allowed values |
| Quantity or size | Record, file, page, message, and approximate byte-size expectations |
| Synthetic content | Categories, ranges, edge cases, deterministic IDs, and privacy rules |
| Generation | Creation method, source inputs, dependencies, and reproducibility |
| Installation | Idempotent upload, import, seed, or install method and `azd` hook |
| Identity | Managed identity or `DefaultAzureCredential` flow and minimum RBAC |
| Local validation | Schema, count, checksum, parser, rendering, and safety checks |
| Azure validation | Loaded count, representative query, negative test, and rerun check |
| Acceptance | Observable pass conditions used by the application or challenge |
| Ownership | Responsible role and creation priority or milestone |

Do not use a generic row such as “sample data.” Name the exact files, explain
their content, and identify the Azure destination and validation evidence.

## Deployment classification

Use `deployment-critical` when any of these statements is true:

- The coach or participant application reads the artifact.
- A seed or installation step is required for `azd up` acceptance.
- A challenge prerequisite assumes the data, index content, document, API
  contract, message, or media exists.
- The coach solution cannot prove grounding, tool use, routing, evaluation, or
  another required behavior without it.

A deployment-critical entry must reach `packaged` before handoff to the Deploy
agent. Its repository destinations must exist, and deployment must load or
install it through an idempotent script or application initializer.

Use `release-enrichment` only when the scenario deploys and passes its required
acceptance path without the artifact. Examples include an optional screenshot,
an additional stretch dataset, or supplemental reading not referenced by a
required challenge step.

Deferred release-enrichment work does not authorize skipping `azd up`. If a
challenge starts depending on it, reclassify it as deployment-critical.

## Service-specific specifications

### Azure Cosmos DB for NoSQL

Specify all of these details for a Cosmos DB JSON or JSONL artifact:

- Account API, database, container, partition-key path, and expected item count.
- Top-level array, JSON Lines, or one-document-per-file representation.
- An `id` value for every item and the partition-key property on every item.
- Partition-key cardinality and its alignment with representative queries.
- Exact field names, JSON types, required and optional fields, nested objects,
  arrays, date format, allowed values, and null handling.
- Deterministic fake identifiers, balanced categories, normal records, boundary
  values, and negative or incomplete records required by tests.
- Idempotent upsert behavior plus count, point-read, and representative-query
  validation.

Cosmos DB requires an item ID and partition-key value. Choose a stable,
high-cardinality partition key that distributes storage and request units while
supporting the application's query pattern.

### Azure Table Storage

Specify all of these details for a table entity dataset:

- Exact table name and whether the source file is CSV, JSON, or JSONL.
- `PartitionKey` and `RowKey` generation rules and uniqueness expectations.
- Every custom property name, supported type, required rule, and value range.
- The fact that `Timestamp` is server-managed and must not be seeded.
- Key restrictions, including no slash, backslash, number sign, question mark,
  or control characters in `PartitionKey` and `RowKey` values.
- Entity count by partition plus one point query and one partition query used
  for validation.
- Idempotent upsert and rerun behavior.

Table Storage is schema-less at the service boundary. The scenario must still
define and validate a client-side schema so every deployment is deterministic.

### Azure Blob Storage and document grounding

For each document collection, enumerate every exact filename. Specify:

- Container and virtual path, file type, MIME type, language, page or word
  count, and approximate file size.
- Required headings, tables, diagrams, metadata, dates, revision labels, and
  cross-document references.
- The scenario facts each document must support and facts it must not imply.
- OCR or text-extraction quality, accessibility, sanitization, and checksum
  checks.
- Indexer parsing mode, chunking assumptions, metadata mapping, and expected
  source and chunk counts when search is used.

Use synthetic organizations, people, locations, events, and measurements.
Avoid logos, copyrighted customer material, operational secrets, and plausible
real-world personal identifiers.

### Azure AI Search

Treat index definitions, synonym maps, skillsets, data-source definitions,
indexers, and pushed document batches as separate artifacts when separate files
will be created.

Specify:

- Source artifact IDs and whether data is pushed or pulled by an indexer.
- Index name, document key, field names, Azure AI Search data types, and each
  field's searchable, filterable, sortable, facetable, retrievable, and vector
  behavior where applicable.
- Field mappings, parsing mode, skillset or integrated-vectorization dependency,
  indexer schedule or on-demand run, and managed-identity access.
- Expected source document count, indexed document or chunk count, one positive
  query, one no-result query, and citation or grounding evidence.

JSON pushed to a search index must conform to the index schema. Push batches
are limited by the service, so record batch strategy when the planned volume is
large. Integrated vectorization and AI enrichment require an indexer pipeline.

### APIs, tools, and messages

For OpenAPI documents, mock responses, queue messages, Service Bus messages, or
Event Hubs events, specify:

- Exact operation, path, method, request, response, and error contracts.
- Required headers without values, payload schema, correlation identifier,
  version, timestamps, and idempotency key where applicable.
- Normal, boundary, unauthorized, not-found, throttled, malformed, duplicate,
  and retry examples used by the scenario.
- Target API, queue, topic, subscription, or event stream plus the producer and
  consumer.
- Installation, replay, dead-letter or failure behavior, and observable test.

Never place a real token, key, connection string, endpoint, tenant ID, or
subscription ID in a supporting artifact.

### Evaluation and safety datasets

Specify:

- Exact JSONL or CSV filename and one record per evaluation case.
- Prompt, expected intent or route, required facts, prohibited claims,
  citation expectation, safety category, and pass rule.
- Normal, ambiguous, off-topic, prompt-injection, unauthorized-action, and
  missing-data cases appropriate to the scenario.
- Minimum case count by category and deterministic expected outcomes.
- Evaluation command or script, output report path, and acceptance threshold
  based on verified project requirements.

Do not invent compliance claims or use real conversations as evaluation data.

## Package placement

Use the smallest safe distribution:

- Deployable runtime assets belong in `packages/coach/` and, when the starter
  requires them, `packages/participant/`.
- Learner downloads belong in `packages/hack/Allfiles/` and must be copied byte
  for byte to `packages/coach-guide/Allfiles/`.
- Coach-only answer material belongs only in `packages/coach-guide/`.
- Secrets, resolved endpoints, deployment state, and local environment files do
  not belong in any package.

List every destination in `nextsteps.MD`. A status of `packaged` means every
listed destination exists, not merely that a source copy was created.

## Creation, GitHub, and deployment workflow

1. HackCreator plan mode creates `nextsteps.MD` with every known artifact at
   `planned` status.
1. Artifact owners create and locally validate deployment-critical files.
1. HackCreator package mode places the files, validates parity and safety, and
   changes their status to `packaged`.
1. The package validator blocks deployment handoff when a deployment-critical
   artifact is missing or not packaged.
1. The Deploy agent still runs `azd up` for the coach and every participant
   manifest entry. Load scripts run through the selected `azd` lifecycle hook.
1. Post-deployment checks validate Azure counts, queries, search results,
   messages, evaluations, and application behavior. Successful entries become
   `azure-verified`.
1. Contributors commit and push the scenario and its artifacts together, then
   attach package and deployment validation evidence to the GitHub pull request.

## Official references

These sources were reviewed on 2026-09-03. Recheck them when authoring a
scenario because service behavior can change.

- [Partitioning and horizontal scaling in Azure Cosmos DB][cosmos-partitioning]
- [Understanding the Table service data model][table-data-model]
- [Data import in Azure AI Search][search-data-import]
- [Customize Azure Developer CLI workflows with hooks][azd-hooks]

[cosmos-partitioning]: https://learn.microsoft.com/azure/cosmos-db/partitioning
[table-data-model]: https://learn.microsoft.com/rest/api/storageservices/understanding-the-table-service-data-model
[search-data-import]: https://learn.microsoft.com/azure/search/search-what-is-data-import
[azd-hooks]: https://learn.microsoft.com/azure/developer/azure-developer-cli/azd-extensibility
