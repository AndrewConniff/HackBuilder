"use strict";
let accessToken;
let configuration;
const element = id => document.getElementById(id);
const base64url = bytes => btoa(String.fromCharCode(...bytes)).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
const random = () => base64url(crypto.getRandomValues(new Uint8Array(32)));

async function api(path, options = {}) {
    const response = await fetch(path, {
        ...options, headers: { ...options.headers, Authorization: `Bearer ${accessToken}` }, cache: "no-store"
    });
    const body = await response.json().catch(() => ({ message: `HTTP ${response.status}` }));
    if (!response.ok) throw new Error(`${body.message || `HTTP ${response.status}`} ${body.correlationId || ""}`);
    return body;
}

async function initialize() {
    configuration = await (await fetch("/api/config", { cache: "no-store" })).json();
    if (!configuration.configured) {
        element("status").textContent = "Entra configuration is missing. This local shell cannot access telemetry or Foundry.";
        element("login").disabled = true;
        return;
    }
    const params = new URLSearchParams(location.search);
    if (params.has("error")) {
        history.replaceState({}, "", "/");
        throw new Error("Microsoft sign-in failed. Try again or contact your Operations administrator.");
    }
    if (params.has("code")) {
        const state = sessionStorage.getItem("equip-state");
        const verifier = sessionStorage.getItem("equip-verifier");
        sessionStorage.removeItem("equip-state");
        sessionStorage.removeItem("equip-verifier");
        history.replaceState({}, "", "/");
        if (!state || !verifier || params.get("state") !== state) throw new Error("Invalid sign-in state.");
        const response = await fetch(`https://login.microsoftonline.com/${configuration.tenantId}/oauth2/v2.0/token`, {
            method: "POST", body: new URLSearchParams({
                client_id: configuration.spaClientId, grant_type: "authorization_code",
                code: params.get("code"), redirect_uri: location.origin + "/", code_verifier: verifier,
                scope: `api://${configuration.apiClientId}/Equipment.Read`
            })
        });
        if (!response.ok) throw new Error("Token exchange failed. No equipment access granted.");
        const token = await response.json();
        if (!token.access_token) throw new Error("Sign-in returned no access token.");
        accessToken = token.access_token;
        const equipment = await api("/api/equipment");
        element("equipment").textContent = equipment.map(item => `${item.deviceId}: ${item.name} (${item.siteId})`).join("; ");
        element("send").disabled = false;
        element("status").textContent = "Signed in. Access is restricted to your assigned Operations sites.";
        element("login").textContent = "Sign out";
        setTimeout(() => {
            accessToken = undefined;
            element("send").disabled = true;
            element("status").textContent = "Session expired. Sign in again; no token is persisted.";
        }, Math.max(0, Number(token.expires_in) - 60) * 1000);
    } else element("status").textContent = "Sign in with your assigned Operations account to access equipment.";
}

element("login").addEventListener("click", async () => {
    if (accessToken) { accessToken = undefined; location.assign("/"); return; }
    try {
        const verifier = random(), state = random();
        sessionStorage.setItem("equip-verifier", verifier);
        sessionStorage.setItem("equip-state", state);
        const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
        const parameters = new URLSearchParams({
            client_id: configuration.spaClientId, response_type: "code", redirect_uri: location.origin + "/",
            response_mode: "query", scope: `api://${configuration.apiClientId}/Equipment.Read`,
            state, code_challenge: base64url(new Uint8Array(digest)), code_challenge_method: "S256"
        });
        location.assign(`https://login.microsoftonline.com/${configuration.tenantId}/oauth2/v2.0/authorize?${parameters}`);
    } catch (error) { element("status").textContent = error.message; }
});

element("chat").addEventListener("submit", async event => {
    event.preventDefault();
    element("send").disabled = true;
    element("answer").textContent = "Retrieving fresh authorized evidence...";
    element("evidence").textContent = "";
    element("trace").textContent = "";
    try {
        const result = await api("/api/chat", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: element("question").value })
        });
        element("answer").textContent = result.answer;
        element("evidence").textContent = JSON.stringify(result.evidence, null, 2);
        element("trace").textContent = `Agent ${result.agentName}/${result.agentVersion}; tools: ${result.tools.join(", ") || "none"}`;
    } catch (error) { element("answer").textContent = `Unable to answer: ${error.message}`; }
    finally { element("send").disabled = !accessToken; }
});
initialize().catch(error => { element("status").textContent = error.message; });
