# Reference implementation and validation plan

## Local artifacts

1. Preserve exact intake, CSV identities and actual phase-specific authorization in requirements.
1. Define store-authorized concurrent analysis + sequential synthesis and human order gate.
1. Pin public AVM account 0.19.1, site 0.24.0, serverfarm 0.7.0 and storage-account 0.33.1.
1. Use native direct child project and RBAC resources where needed around AVM outputs.
   The account AVM interface does not expose a direct child project parameter.
1. Build .NET 10 Razor UI with real local password/cookie authentication, Table SDK and Foundry SDK.
1. Implement insert-only fixture install, immutable version-pinned agents, server grants and approval ETags.
1. Test real HTTP/cookie/password/CSRF boundaries with isolated data/account repositories and agent test doubles.
   Test doubles are never registered by production code and are not inference evidence.
1. Generate architecture/runtime PNGs and persist local checks.

## Installation ordering

`azure.yaml` preprovision verifies exact approved targets; postprovision installs local accounts, data and agents.
`scripts/Build-Assets.ps1` runs locked restores and browser syntax validation as a prepackage hook.
Agent IDs/versions are generated and captured automatically, not manual questionnaire fields.
Bootstrap also configures a Responses endpoint with 100% traffic to each installed immutable version.
The deployed Consumer identity invokes these endpoints rather than project development APIs.
The supplied store password and generated area password enter via process environment only.
Only salted hashes reach Table Storage. No user-login directory registration, consent or Graph write remains.
This reference requires an authenticated Azure operator and the exact reviewed target.
The consent environment guard prevents accidental hook execution but is not itself permission.

## Instruction conflicts resolved

The generic .NET template says not to add authentication middleware. The explicit user requirement for
own-store/area-manager isolation takes precedence: authenticated, server-controlled store access is mandatory.
No shared repository instruction was modified. No HttpClient-based external data scraper is introduced.
Current Foundry guidance/metadata overrides old classic Agents examples.
Sweden Central is approved after actual what-if; metadata and preflight still cannot reserve allocation capacity.

## Executed live acceptance

Read-only target queries and revised what-if passed; deployment was approved with no directory-write phase.
The approved deployment and actual model, three-agent, signed-in browser, grounding, order replay,
store denial and real branch-failure/recovery checks have now passed.
See `scenario-validation.json` and the referenced raw evidence.
The original load/latency targets are not fully met; retain them and disclose the observed results.
A validated snapshot requests review; it does not record suitability approval or authorize composition.
