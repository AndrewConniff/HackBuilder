# Private coach access instructions

This guide documents reference operation only; it is not a pre-approval hack package.

Open the [deployed application's login page](https://fc-web-kvjmo565tswuy.azurewebsites.net/Login)
using the organizer-delivered
`.private/coach-access.json`. That private file contains the actual generated
coach username/password. The account has CampaignOperator, ProductManager,
ConflictResolutionSpecialist and ControlAdmin roles for reference acceptance.
Do not distribute it with participant instructions.

The separate `.private/participant-access.json` contains the three restricted
participant accounts. Supply only the intended participant credentials through a
private channel. Both files are gitignored, excluded from public portal/catalog
exports and outside the published application source. Keep protected backups;
passwords cannot be recovered from the salted hashes in Azure Tables.

`python scripts\setup_lab_accounts.py install` verifies and reuses the installed
credentials; it does not silently reset passwords or elevate participant roles.
If private files are lost, restore them or arrange an explicitly reviewed reset.
Each new deployment must generate its own credentials. Do not copy this reference's
files into source packages, learner archives or another environment.

Use participant accounts to test wrong-role denial. Do not edit Entra role
assignments or request tenant consent: the local sample no longer uses that flow.
Persistent App Service session keys live outside published content under
`HOME/data/feedback-campaign-keys`. This single-instance synthetic lab is not an
enterprise SSO/MFA or production identity design.

Azure runtime access remains managed identity. The signed-in Azure deployer needs
the reviewed scenario-scoped control/data-plane roles to initialize and validate
resources; local app credentials are never Azure credentials.

The deployer has Table Data Contributor on this scenario's storage, Azure AI User
on its Foundry project, Sender and Receiver on `posts`, and Receiver on `replies`.
These allow initialization, direct inference, stream inspection and DLQ inspection
without service keys or directory administration. They do not authorize deleting
resources, changing tenant policy or publishing credentials. Runtime identities
have separate scoped assignments; installer success is not proof of runtime access.
