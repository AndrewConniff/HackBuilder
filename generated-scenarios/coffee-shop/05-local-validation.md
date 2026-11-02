# Local validation results

All checks below were executed locally. Exact UTC timestamp, commands, exit codes and captured output
are preserved in `evidence/local-checks.json`.

| Check | Actual result |
| --- | --- |
| Locked production .NET restore | Exit 0 |
| .NET 10 build | Exit 0; 0 warnings, 0 errors |
| Focused HTTP/domain tests | 31 passed; 0 failed; 0 skipped |
| Bicep build, main and referenced AVM modules | Exit 0 |
| Bicep lint, main | Exit 0; no diagnostics |
| Bicep lint, resources | Exit 0; no diagnostics |
| npm locked restore | Exit 0; project-local packages only |
| Local-login browser asset build | Exit 0; no MSAL dependency |
| Browser JavaScript syntax | Exit 0 |
| Release publication | Exit 0; fixtures, agent instructions and local-login UI included |
| PowerShell parser, all 5 deployment/build scripts | Exit 0; parsed without execution of cloud operations |
| CSV identity/industry provenance | Passed; exact Fourth Coffee and people catalog records |
| Architecture/runtime diagram rendering | Both PNGs generated; visually inspected |
| Scenario JSON parsing and Markdown line-length check | Passed |
| Curated manifest refresh | Completed through repository helper; exact intake retained |

## Test coverage

Tests exercise real Razor/HTTP routing, salted password verification, cookie sessions and CSRF validation.
They cover anonymous, invalid credentials, forged cookie/bearer, spoofed-header and cross-store denials;
shared account lockout after five failures, logout and security-stamp revocation, distinct salts and POST CSRF;
own-store/area/server-grant boundaries; positive stock shortfalls and decimal P&L;
explicit order confirmation, replay across managers, expired/stale drafts and optimistic concurrency;
scoped parallel branch/synthesis handoff; missing/mixed-date evidence; cancellation and branch failure;
and the code boundary against prompt-driven scope expansion.

Repository and agent dependencies are test doubles only in the test host. They prove code behavior,
not Azure Table semantics, live inference, model safety or real Foundry receipts.
The production path has no test-authentication switch or fake success.

## Local and live evidence boundary

Read-only Azure/Graph preparation and Sweden Central what-if ran under explicit authorization.
The user subsequently approved deployment with application-local authentication and no directory writes.
Subsequent authorized rollout and functional live checks passed. Actual sign-in, model inference,
agent invocation and application chat are indexed in `scenario-validation.json`, separately from these local tests.
Browser evidence and actual failure/recovery are also recorded. Performance targets remain unmet;
functional passed status must not be presented as ten-user production load acceptance.

The earlier local-only `hack_workflow.py snapshot` invocation exited 1:
`Workflow blocked: Live scenario validation has not passed.`
This is the expected approval guard, not a reason to invent proof or bypass it.
See `evidence/snapshot-guard.json`; that historical refusal was correct.
A fresh snapshot may now request review of the deployed reference and its disclosed limits.
No suitability approval has been recorded.

No shared tools, Azure defaults or unrelated user files were modified.
