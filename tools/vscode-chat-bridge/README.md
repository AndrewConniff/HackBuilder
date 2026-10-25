# ABC Builder Scenario Chat

Local editor bridge for reopening existing conversations from the ABC Builder portal.
It never sends prompts, approves tools, changes editor security settings or starts an agent.

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
Titles are not used, and editor databases are opened read-only for identity fields, not conversation messages.
On Windows, the portal uses the registered editor protocol directly and waits for a native acknowledgement.

**ABC Builder: Link Existing Chat to Scenario** remains an optional advanced repair command, not normal portal flow.
It accepts only native `agent-host-session://` links. Missing or ambiguous history is an explicit error;
the bridge never invents an association or creates a replacement conversation.

## Continuation

The portal sends an extension URI containing the workspace, scenario slug, phase and a unique request ID.
The extension accepts only the currently open trusted repository, loads the saved session link and uses
the native `vscode.open` command to reopen it. A local receipt acknowledges the command's completion or failure.
The portal never falls back to a new chat when the bridge is missing or reopening fails.

Links are stored under the scenario's local portal state, not the reference or exported learner materials.
The reference and composition contexts remain separate. The portal exposes only one scenario-chat navigation action.
If a saved link must be corrected, use the editor linking command; the portal never offers a replacement chat.
History and session-only permissions are not copied. Existing approvals remain subject to their actual scope.

## Validation

Run `npm test` in this folder. Tests mock the editor API; reopening a real chat additionally requires
associating an existing supported chat and checking that the editor displays its retained history.
Run `python -m unittest scripts.tests.test_scenario_chat scripts.tests.test_portal_visualizer`
from the repository root to test discovery, persisted tracing and portal routing.
