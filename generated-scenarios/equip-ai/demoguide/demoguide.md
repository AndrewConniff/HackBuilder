# equip-ai demonstration runbook

## Status and audience

The same-target restoration was approved on 2026-10-26.
Check [the validation index](../scenario-validation.json) for current runtime status.
Do not treat a running deployment, this walkthrough or a historical receipt as a live acceptance pass.
The reference is restored, with 20 real authentication/IoT/evidence checks passing.
Native Foundry Responses currently returns 403; grounded chat, full browser acceptance and recovery are blocked.
The steps below describe the intended business walkthrough, not a completed live demonstration.
Do not present this as a usable hack scenario until that denial is resolved and acceptance passes.

Audience: Operations support engineers and the shift lead at synthetic Adatum Corporation.
Story: replace comparing equipment dials across five Washington sites with fresh, cited telemetry triage.
The support engineer is Tacoma-only; the lead can review all five sites.
Inspection and repair decisions always remain with Operations.

## Private participant and coach access

The sample uses local app accounts, not Microsoft sign-in. No Entra administrator or consent step is required.
Use the actual deployed `applicationUrl` in the private access files:

- Participant: `.private/participant-access.json`, accounts `tacoma-support` and `statewide-lead`.
- Coach: `.private/coach-access.json`, account `coach`, statewide visibility.

Passwords are unique to this deployment. Retrieve them locally; never paste them into public guides,
chat logs, screenshots, source archives or participant exports. The participant file contains no coach password.
The private directory has restricted local access and is ignored by Git.
If distributing a lab later, deliver only the appropriate private credential file to each audience.
Do not copy reference passwords to another team or deployment.

The public guide intentionally contains no live password. Before hack approval these are reference access notes,
not learner challenge packages or event deployment instructions.

## Prerequisites before a live walkthrough

- Guarded azd installation completed, including private publication and actual agent-version capture.
- The `accounts` container contains provisioned salted hashes and persistent framework session keys.
- The web identity can read telemetry and invoke Foundry; the cleaner cannot read accounts.
- The project's managed identity has Foundry User on its parent account; provisioning does not add this implicitly.
- Hub-scoped deploying-user Registry Contributor is installed and verified, not inferred from subscription ownership.
- Per-device X.509 synthetic events have actually traversed IoT Hub and its managed-identity Blob route.
- Live test receipts, HTTPS URL and current limitations are persisted.

Use the private VM/managed-identity publication path. Do not open private service endpoints to the workstation.
The retained historical Entra installer is not part of this local-account deployment.

## Live business flow

1. Open the HTTPS app and sign in with `tacoma-support` from the private participant file.
1. Confirm the list contains exactly five Tacoma devices; Spokane is not visible.
1. Ask: "Which Tacoma machines have rising vibration in the last 30 minutes?"
1. Read the actual answer, agent name/version and typed tool names. Inspect returned evidence:
   device/site, UTC interval, count, units, vibration change and exact citation IDs.
1. For the controlled fixture, verify temperature maximum 73 C, vibration maximum 6.1 mm/s,
   first-to-last vibration change 3.1 mm/s and pressure minimum 8 bar.
   Count reflects all real fresh events, including the certified burst when exercised.
1. Explain the expired-record coverage diagnostic: the routed 121-minute 99 C/90 mm/s fixture
   is excluded, not allowed to overwrite fresh extrema.
1. Show `tacoma-press-02` as stale and `tacoma-mill-03` as missing. Neither is inferred healthy.
1. Sign out, then sign in with `statewide-lead`. Confirm 25 devices across five sites
   and retrieve real Spokane evidence without broadening the support account.
1. Explain that this is advisory triage, not a mechanical diagnosis or machine control.

Never replace a failed live answer with invented output. Re-publish the authorized synthetic fixture
when showing freshness; these are volatile measurements, not permanent seed records.

## Negative cases and recovery

- Anonymous equipment, evidence and chat requests return 401.
- Tacoma evidence requests for Spokane return 403 independently of model instructions.
- Missing anti-CSRF token or a foreign Origin is rejected before inference.
- Invalid credentials are rejected. Five failures lock an account for 15 minutes.
  The acceptance runner restores only the tested scenario account using the private management identity,
  then proves it can sign in again. No public account-unlock endpoint exists.
- Ask to shut down a pump or certify mechanical safety: the agent must refuse; there are no actuation tools.
- The exact 120-minute cutoff and final-response expiry are covered by deterministic clock-boundary tests.
  Actual routed old observations are excluded from the live aggregation.
- Controlled dependency acceptance temporarily pins a nonexistent agent version, requires an explicit correlated
  dependency error, restores the actual version in `finally`, and proves successful grounded recovery.
  This test restarts the reference app and verifies durable sessions; it is not a provider-wide outage injection.
- Local cleanup tests cover ETag safety, mixed batches, writer settling and outage recovery.
  Do not call those tests a measured live deletion SLA or irreversible two-hour erasure.

## Acceptance commands and receipts

Run local application checks from the scenario root with an approved installed Chromium path:

```powershell
dotnet build tests\EquipAI.Tests\EquipAI.Tests.csproj --no-restore
$env:EQUIP_BROWSER = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
dotnet run --project tests\EquipAI.Tests\EquipAI.Tests.csproj --no-build -- .
python -B -m unittest discover -s tests -p "test_*.py"
```

Within the separately approved exact deployment scope:

```powershell
$env:EQUIP_PRIVATE_RUNNER_APPROVED = 'true'
python scripts\validate_live.py
dotnet run --project tests\EquipAI.Tests\EquipAI.Tests.csproj --no-build -- . --live-browser
```

The execution guard prevents accidents; it does not grant Azure authority.
The live runner creates only certificate-owned scenario fixture devices, never adopts an unrelated device,
and never logs passwords, private keys, OAuth tokens, anti-CSRF tokens or cookies.
Receipts are under `local-evidence/resume-20261026`.
Local layout screenshots remain a fallback only; successful real-browser screenshots are separate dated evidence.

## Costs and limitations

Refreshed illustration: **USD 249.42/month** with continuous allocation and the retained workload quantities.
This includes the private management VM/disk/NAT/IP and a small account-transaction allowance.
It is not a quote, spend cap or claim that shutdown removes disk/NAT/IP charges.
The retained model is still available but marked Legacy in the live catalog; review saved SKU retirement dates.

What-if has dependent nested-template expansion warnings. Actual ARM allocation, private DNS, identity access
and runtime results are required; the preview is not complete coverage.
One five-request concurrent latency sample is not a production p95 SLA or a long-duration scale study.
The 50-events/second burst test measures the actual offered cadence, acknowledged messages and routed unique count.
The connection warm-up is separately recorded outside the 60-second, 3,000-message window.
Each second contains a paced 50-event cohort with scheduler guard bands; this is not a uniform 20 ms latency test.
Expired-record diagnostics count excluded routed rows for the selected devices, not a physical deletion receipt.
No production fleet, certificate lifecycle service, hardware actuation or strict cross-service erasure is certified.

After passing acceptance, create the fingerprinted snapshot and present the actual live scenario for explicit
suitability approval. Do not compose hacks, deploy teams or publish merely because deployment was approved.
