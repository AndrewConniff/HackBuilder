# Participant reference access

This is reference access documentation, not a hack challenge or participant starter package.

Open the [deployed application's login page](https://fc-web-kvjmo565tswuy.azurewebsites.net/Login).
Use the deployment-specific
credentials in the private `.private/participant-access.json` file supplied by the
organizer. No Microsoft sign-in, Entra registration or consent is required.
Never use a corporate password.

| Username | Assigned role | Allowed actions |
| --- | --- | --- |
| campaign-operator | CampaignOperator | Submit synthetic feedback, inspect cases and explicitly retry failures |
| product-manager | ProductManager | Review assigned negative posts and approve an edited reply |
| conflict-specialist | ConflictResolutionSpecialist | Review other assigned posts and investigation recommendations |

Passwords are deliberately absent from this public-safe guide. The private
participant access file contains actual generated passwords for this deployment
only. Do not publish it, commit it, include it in web assets or reuse it in another
environment. Participants must never receive the coach file.

Five failed password attempts lock that account for 15 minutes. Sessions expire
after four hours; signing out clears the browser session. Cookies require HTTPS.
Changing usernames or choosing a role in browser developer tools does not grant
access; the server enforces the installed account's roles.

Replies enter the Service Bus reply stream, not an external email/social channel.
All records are synthetic. The application's Azure access uses managed identity,
not these lab passwords.
