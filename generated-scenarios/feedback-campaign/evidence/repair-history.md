# Local implementation repairs

Observed and fixed during this preparation session (2026-10-25):

- Initial C# build: nullable Azure Table response value; corrected the explicit
  HasValue branch. Final build has zero warnings/errors.
- Initial Bicep: AVM daily quota string schema, unsupported Service Bus `tier`
  property and runtime-output-derived role assignment names. Corrected parameters
  and deployment-time deterministic names; final build/lint is clean.
- Initial diagram invocation: existing Graphviz was outside the tool process PATH.
  Reused `check_prerequisites.execution_environment` to invoke the existing
  installation. No tool installation or shared PATH edit was performed.
- Foundry wire tests: policy markdown was not included in publish output by a
  Content Update glob. Corrected to Content Include with publish/output copying.
  Tests and a real local dotnet publish verify the actual files exist.
- Confirmed current Foundry Responses URL against official SDK `_patch.py`:
  `/openai/v1/responses`; agent administration uses API version v1 separately.
- Metadata helper rejected noneditable `artifacts`/`source` metadata fields.
  Removed them from reviewed inputs; helper derives those fields itself.
- A later simultaneous UI preview and rebuild locked the Windows app executable.
  Stopped the attached local preview after browser checks and reran all local
  checks sequentially. This was an agent-owned local execution conflict, not an
  Azure/tenant/host denial or a reason for a permission handoff.

Current results are in `local-validation.json`; no local repair is live runtime
evidence. The only remaining deployment blocker is missing user authority and the
dependent unexecuted readiness/what-if/runtime checks.
