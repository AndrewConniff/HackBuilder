# Finance security hack — Phase B recovery

## Progress

2026-10-22: initial approval passed; package contract and inventory persisted before authoring.
Approval rechecked before package. Four package roots and one-team planned manifest created locally.
Local validation and source release archive checks passed; evidence is saved under `packages/validation/`.
No approved reference source, infrastructure, fixtures or evidence was edited.

## Saved checks

| Check | Result |
| --- | --- |
| Approval before plan, package and at release gate | Passed; approved fingerprint unchanged |
| Bicep 0.48.1 coach build/lint | Passed offline with `--no-restore` |
| Bicep 0.48.1 participant build/lint | Passed offline; only resource-group baseline |
| .NET SDK 10.0.402 offline restore/build | Passed; build has zero warnings and errors |
| Copied deterministic application tests | 18 passed; zero failed or skipped |
| Copied operator-script syntax/consent guards | 17 passed; zero real Azure commands/installer invocations |
| Intended-incomplete starter | `not-configured`, no app or URL, no prebuilt Foundry services |
| Catalog, omission, source parity, safety and boundary checks | Passed; see `boundaries.json` |
| Skillable package and authoring-resource validators | Passed |
| Four source ZIP archives | Integrity, file hashes and public/private separation passed |

The final source packages are also archived separately in `packages/validation/release/`.
Only `participant.zip` and `hack.zip` are public release candidates.
`coach.zip`, `coach-guide.zip`, the scenario root and validation evidence remain private.
Build caches, compiled ARM, operational evidence and validation logs are excluded from all four archives.
No license terms were invented, no GitHub publication occurred, and no live Skillable import was attempted.

## Recovery log

- Plan persisted promptly after the first successful approval check.
- First composition attempt encountered the existing workspace junction while resolving skill assets.
  Corrected asset lookup to the repository working directory; the workspace was not relocated.
- First completed Skillable pass found one overlong inventory line; split it and revalidated.
- First boundary gate found absolute paths in a copied script example and two scanner false positives.
  Sanitized only the example comment, distinguished C# newline escapes, and recognized Jekyll-generated links.
- Added private diagram media to the private release include list and validated exact archive content/hashes.
- Re-ran the complete local gate successfully; no source design, fixtures or approval evidence were changed.
- Each executed check's start time, duration, command and exit code is saved in `local-checks.json`.

## Artifacts

- `08-hack-package-contract.md`: private approval fingerprint, omission matrix and learning contract.
- `nextsteps.MD`: exact supporting-artifact specification and installation inventory.
- `09-hack-event-manifest.json`: one planned coach and one planned isolated team; null URLs.
- `packages/coach/`: private sanitized deployable reference and tests.
- `packages/participant/`: empty resource-group starter, access contract and FAQ.
- `packages/hack/`: public Skillable learner source.
- `packages/coach-guide/`: private architecture, deployment guide, exact learner copies and Finale.
- `packages/validation/`: local composition, verification and evidence; private, never public release.

## Limitations

Reference runtime history is explicit user attestation from a deleted inaccessible one-off lab,
not independently verified tests. URL, exact time, targets and logs are unavailable.
No new environment, cloud acceptance, capacity, cost, publication or event deployment is claimed.
Cold private multi-service setup may exceed the build timer; event preparation remains future work.

## Completion

**packages validated; event not deployed**

10-minute kickoff + five progressive challenges totaling 150 minutes + 20-minute wrap = 180 minutes.
The signing increment is a workload action, not a new agent tool.
Optional authenticated public chat remains outside the core timer.
The manifest retains planned statuses and null URLs.
Rollout, runtime acceptance and publication need separate decisions.
