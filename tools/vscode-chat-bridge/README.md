# ABC Builder Scenario Chat

Local editor bridge for reopening existing conversations and continuing explicit portal brief responses.
It never approves tools, changes editor security settings or creates replacement conversations.

## Setup

Package this folder with `npx --yes @vscode/vsce package --no-dependencies --skip-license`.
Install the resulting VSIX using **Extensions: Install from VSIX** in the editor window containing ABC Builder.
This bridge requires VS Code 1.143 or later and a trusted local workspace.
If the editor requests permission to open the extension URI, review and allow it yourself.
If a newly installed extension has not activated, use **Developer: Reload Window** before retrying.
The portal does not approve either prompt or treat a missing acknowledgement as a successful reopen.

Select **Open scenario chat** in the portal. No Copy Link or paste step is required.
The portal's [session association helper](../../scripts/scenario_chat.py) matches the exact original handoff,
workspace and native editor/SDK identities. New launches include a unique trace ID.
Older duplicate handoffs use successful scenario progress reports to identify the latest continuation.
The association and its evidence persist in the scenario's `chat-sessions.json`.
Native links identify the AHP backend (`agent-host-session://ahp-session/<editorSessionId>`), not the
SDK session ID or the Copilot provider label. Older automatically generated `copilot` links are repaired
in place after verifying the same workspace and SDK identity; manually linked conversations are left unchanged.
Titles are not used, and editor databases are opened read-only for identity fields, not conversation messages.
On Windows, the portal uses the registered editor protocol directly and waits for a native acknowledgement.

**ABC Builder: Link Existing Chat to Scenario** remains an optional advanced repair command, not normal portal flow.
It accepts only native `agent-host-session://` links. Missing or ambiguous history is an explicit error;
the bridge never invents an association or creates a replacement conversation.

## Continuation

The portal sends an extension URI containing the workspace, scenario slug, phase and a unique request ID.
The extension accepts only the currently open trusted repository, loads the saved session link and uses
the native workbench session-link opener to reopen it. A local receipt acknowledges completion or failure.
The portal never falls back to a new chat when the bridge is missing or reopening fails.

**Confirm brief** and **Save changes** use the separate `/continue` action.
The bridge verifies the exact saved response/request ID and reviewed brief fingerprint, reopens the existing
scenario chat as an editor using `_workbench.open` with `sideBySide`, waits for the chat-tab API to update,
and uses the installed editor's native `workbench.action.chat.submit` command with `inputValue`.
Opening a session link without an explicit editor target prefers the sidebar and is not sufficient for this guard.
Passing `TextDocumentShowOptions` to `vscode.open` bypasses session-link handling and incorrectly opens a text file.
The bridge checks for the native opener command and fails explicitly when it is unavailable.
This is the VS Code 1.143 submit contract, not the sidebar `chat.open` command, which could target another chat.
The existing custom agent, model and permissions are retained.
Fingerprints match the portal's Python text reads: remove the UTF-8 BOM and normalize CRLF/CR to LF before SHA-256.
Line-ending changes alone do not invalidate a reviewed brief; changes to its text still do.
Version 0.2.3 or later is required for Windows-compatible fingerprints and native session-link editor targeting.
After upgrading, run **Developer: Restart Extension Host** in the HackBuilder window to activate it.
The portal checks the running version, which can differ from the installed version.
The fixed message resumes the normal scenario workflow on confirmation, or scoping-only revision on changes;
it never includes arbitrary portal-supplied executable commands.
An active native chat editor is required. A per-request ledger prevents replay; ambiguous dispatches are not resent.
Confirmation and retries use the same **Confirm brief** control; the portal does not expose a separate Continue button.
A dispatch receipt acknowledges only the editor command, not agent execution or completion.
Actual progress still comes from the scenario agent's reports. Azure/deployment and suitability gates are unchanged.

Links are stored under the scenario's local portal state, not the reference or exported learner materials.
The reference and composition contexts remain separate. The portal exposes only one scenario-chat navigation action.
If a saved link must be corrected, use the editor linking command; the portal never offers a replacement chat.
History and session-only permissions are not copied. Existing approvals remain subject to their actual scope.

## Validation

Run `npm test` in this folder. Tests mock the editor API; reopening a real chat additionally requires
associating an existing supported chat and checking that the editor displays its retained history.
Run `python -m unittest scripts.tests.test_scenario_chat scripts.tests.test_portal_visualizer`
from the repository root to test discovery, persisted tracing and portal routing.
