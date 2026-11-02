# Private composition release notes

## Explicit decision and boundaries

User selected **extend-hospitality**:
"Extend Skillable templates and validator support for Hospitality & Travel,
preserving the approved coffee-shop scenario".
Canonical slug is `hospitality-travel`, not Retail.
Shared templates are industry-parameterized and require no duplicate challenge or Finale skeleton.
Catalog, validator, authoring guidance and positive/negative regression coverage now support the exact selection.
Scope remains businessUnits `["sales"]`, Fourth Coffee, store/area personas and reviewed finance handoff only.

The approved reference fingerprint is
`3be67e02fd1b4246759f567203e037070ff9447bf9a634d3f555d545e954871c`.
The approval response is **Approve suitability with disclosed limitations**.
No reference input is changed and no new approval is asserted.
Saved System identity/prerequisite observations are reused; no cloud query, interactive login or default change occurs.
No legacy worker was found before edits.

## Evidence and limitations

This reference has actual functional runtime evidence, not a historical user-attestation exception.
Local coach application tests use dependency doubles and do not prove a newly deployed coach environment.
No deployed URL, installed agent receipt, private runtime screenshot, password or reference target is exported.
No event deployment, publication or destructive cleanup is requested or performed.

Approved limitations remain: ten-read p95 2.41 seconds missed the 1-second target;
only 2 of 10 simultaneous closes completed and 8 returned busy, so ten-user close performance is not met.
One area close took 9.50 seconds; this is not sustained-load or three-worker scale-out certification.
Public authenticated endpoints, no WAF/private networking, non-HA baseline, shared demo local credentials,
preview SDK and legacy model remain. Reported inference deprecation is 14 April 2027.
Reference USD 120–270/month is illustrative, not a future destination quote or cap.

## Local repair history

The first plan invocation exposed the existing generated-scenarios junction:
resolved files live in the adjacent azd-projects directory.
The local composition helper now resolves the repository from its required working directory.
No reference relocation or redesign occurred.

First validation: builds/lints, 31 coach tests, assets, publish, guards and starter passed.
Three local authoring checks failed: an unresolved inventory PROJECT token, the pre-extension six-entry
catalog assertion, and a local-path scanner false positive on a licensed library's browser-standard fake upload path.
The token and focused assertion are corrected; scanner exemption is limited to that exact fakepath string.
Original command results remain in validation/attempts when validation is rerun.
No failing run is a passing receipt; record-packages runs only after the final complete successful validation.

## Final validation outcome

All 19 package commands passed, including both Bicep build/lints, 31 coach tests,
locked restore/build/assets/publish, fail-closed script guards, starter state,
boundaries/parity, Skillable, four hospitality tests, 42 workflow tests and both archives.
Exact commands, executable paths, stdout, stderr and exit codes are in local-checks.json.
The original failed package-check run is retained under attempts/.
Learner archive contains 24 files; private coach archive contains 123 files.

The supplemental repository-wide command ran 331 tests with one failure:
test_system_lifecycle's temporary server fixture omits azure_context.py and fails its import.
That already-dirty test/portal code is outside this composition's changes and remains untouched.
Do not describe the whole repository suite as passing.
Exact command, exit code and observed failure are in repository-regression.json.
This supplemental failure is disclosed separately from the successful required package checks.
