"use strict";
let session;
const element = id => document.getElementById(id);

async function api(path, options = {}) {
    const response = await fetch(path, {
        ...options, credentials: "same-origin", cache: "no-store",
        headers: { "X-CSRF-TOKEN": session?.csrfToken || "", ...options.headers }
    });
    if (response.status === 401 && path !== "/api/login" && session) {
        session.authenticated = false;
        element("login-form").hidden = false;
        element("logout").hidden = true;
        element("send").disabled = true;
        element("equipment").textContent = "Sign in again to view assigned Operations sites.";
        element("status").textContent = "Your local session expired or was revoked. Sign in again.";
    }
    if (!response.headers.get("content-type")?.includes("application/json"))
        throw new Error(`The server returned HTTP ${response.status} without a valid application response.`);
    const body = await response.json();
    if (!response.ok) throw new Error(`${body.message || `HTTP ${response.status}`} ${body.correlationId || ""}`);
    return body;
}

async function initialize() {
    session = await api("/api/config");
    element("login-form").hidden = session.authenticated;
    element("logout").hidden = !session.authenticated;
    element("login").disabled = !session.configured;
    element("send").disabled = !session.authenticated;
    if (!session.configured) {
        element("status").textContent = "Local account storage is missing. Telemetry and Foundry are unavailable.";
        return;
    }
    if (!session.authenticated) {
        element("status").textContent = "Sign in with the local account from your private access guide. No Microsoft consent is needed.";
        element("equipment").textContent = "Sign in to view assigned Operations sites.";
        return;
    }
    const equipment = await api("/api/equipment");
    element("equipment").textContent = equipment.map(item => `${item.deviceId}: ${item.name} (${item.siteId})`).join("; ");
    element("status").textContent = `Signed in as ${session.username}. Access is restricted to your assigned Operations sites.`;
}

element("login-form").addEventListener("submit", async event => {
    event.preventDefault();
    element("login").disabled = true;
    try {
        await api("/api/login", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: element("username").value, password: element("password").value })
        });
        element("password").value = "";
        await initialize();
    } catch (error) { element("status").textContent = error.message; }
    finally { element("login").disabled = !session?.configured; }
});

element("logout").addEventListener("click", async () => {
    try {
        await api("/api/logout", { method: "POST" });
        element("answer").textContent = "Signed out. Sign in again before asking about equipment.";
        element("evidence").textContent = "";
        element("trace").textContent = "";
        await initialize();
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
    finally { element("send").disabled = !session?.authenticated; }
});
initialize().catch(error => { element("status").textContent = error.message; });
