# Coach access and credential delivery

Open `[destination-app-url]/Login` using newly generated destination coach
credentials from the deployment's private coach access file. ControlAdmin
is separate from the three participant roles and permits rule promotion.
Never distribute coach credentials to participants or publish private files.

Username: `coach`. Password: `[privately-delivered-destination-coach-password]`.
Roles: CampaignOperator, ProductManager, ConflictResolutionSpecialist and ControlAdmin.
Use participant accounts, not this elevated account, for role-boundary acceptance.

`setup_lab_accounts.py install` generates unique passwords on first install,
saves only salted framework hashes in Tables and writes separate protected,
gitignored participant and coach access files outside published app content.
It reuses/verifies installed credentials on rerun; it does not silently reset.
Restore a lost private file or arrange an explicitly reviewed reset.
Do not copy reference credentials. Deliver destination credentials privately.

Session keys persist under HOME/data outside published app content.
Test wrong-role denial with participant accounts, not administrator access.
Azure deployer rights and runtime managed identity are distinct from these
application accounts. No Entra application, consent or directory write is needed.
