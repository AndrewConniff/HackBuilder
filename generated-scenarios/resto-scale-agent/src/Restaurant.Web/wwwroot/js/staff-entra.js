"use strict";
window.restaurantStaffLogin = async () => {
  const response = await fetch("/api/staff/config", { credentials: "same-origin" });
  const configuration = await response.json();
  if (!response.ok) throw new Error(configuration.detail || "Entra staff sign-in is unavailable.");
  const client = new msal.PublicClientApplication({
    auth: {
      clientId: configuration.clientId,
      authority: `https://login.microsoftonline.com/${configuration.tenantId}`,
      redirectUri: `${location.origin}/auth.html`
    },
    cache: { cacheLocation: "memoryStorage" }
  });
  await client.initialize();
  const result = await client.loginPopup({ scopes: [configuration.scope], prompt: "select_account" });
  if (!result.accessToken) throw new Error("Staff API access token was not issued. No session was created.");
  return result.accessToken;
};
