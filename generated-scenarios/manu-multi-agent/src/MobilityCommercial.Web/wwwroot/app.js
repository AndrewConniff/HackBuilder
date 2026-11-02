"use strict";
const byId = id => document.getElementById(id);
let opportunities = [], products = [], receipt = null;
const status = (text, error = false) => {
    byId("status").textContent = text;
    byId("status").dataset.error = String(error);
};
function element(tag, text) {
    const node = document.createElement(tag);
    node.textContent = text;
    return node;
}
async function api(path, body) {
    const response = await fetch(path, {
        method: body ? "POST" : "GET",
        headers: body ? { "Content-Type": "application/json" } : {},
        body: body ? JSON.stringify(body) : undefined
    });
    const data = await response.json();
    if (!response.ok) throw new Error(`${data.code || "request_failed"} / correlation ${data.correlationId || response.headers.get("x-correlation-id")}`);
    return data;
}
function showEvidence() {
    const opportunity = opportunities.find(item => item.opportunityId === byId("opportunity").value);
    const target = byId("sales-evidence");
    target.replaceChildren();
    if (!opportunity) return;
    const product = products.find(item => item.sourceId === opportunity.productId);
    target.append(element("p", `Audience: ${opportunity.audience}. Required use: ${opportunity.requiredUse || "Missing; Sales clarification required"}.`));
    target.append(element("p", product ? `${product.name}: ${product.rangeStatement}` : "Unapproved product: this handoff must fail before agent invocation."));
}
function showPacket() {
    const packet = receipt.packet;
    const brief = byId("brief");
    brief.replaceChildren(element("h3", `Review required / ${packet.fit}`));
    for (const [label, values] of [["Approved draft", packet.draft], ["Caveats", packet.caveats], ["Unknowns", packet.unknowns]]) {
        brief.append(element("h3", label));
        const list = document.createElement("ul");
        for (const value of values) list.append(element("li", value));
        if (!values.length) list.append(element("li", "None recorded."));
        brief.append(list);
    }
    brief.append(element("p", `Sources: ${packet.sources.map(source => `${source.sourceId} v${source.version}`).join(", ")}`));
    brief.append(element("p", `Packet SHA-256: ${receipt.sha256}`));
    brief.append(element("p", `Key: ${receipt.keyId}. Signature: ${receipt.algorithm}.`));
    const rows = byId("trace-rows");
    rows.replaceChildren();
    for (const trace of packet.trace) {
        const row = document.createElement("tr");
        for (const text of [`${trace.agentName} v${trace.agentVersion} (${trace.agentId})`, trace.responseId,
            trace.tools.join(", ") || "Final structured response", String(trace.inputTokens + trace.outputTokens)]) {
            row.append(element("td", text));
        }
        rows.append(row);
    }
    byId("verify").disabled = false;
}
byId("handoff-form").addEventListener("submit", async event => {
    event.preventDefault();
    receipt = null;
    byId("verify").disabled = true;
    byId("submit").disabled = true;
    byId("brief").replaceChildren(element("p", "Running Sales Fit, Marketing Claims and Handoff Coordinator..."));
    byId("trace-rows").replaceChildren();
    status("Running bounded handoff. No campaign will be sent.");
    try {
        receipt = await api("/api/handoffs", { opportunityId: byId("opportunity").value, request: byId("request").value });
        showPacket();
        status(`Packet ready for human review / correlation ${receipt.packet.correlationId}`);
    } catch (error) {
        byId("brief").replaceChildren(element("p", "No completed packet. Correct the reported issue and retry."));
        status(error.message, true);
    } finally { byId("submit").disabled = false; }
});
byId("verify").addEventListener("click", async () => {
    byId("verify").disabled = true;
    try {
        await api("/api/receipts/verify", receipt);
        status("Integrity verified against the configured versioned signing key. Human review is still required.");
    } catch (error) { status(error.message, true); }
    finally { byId("verify").disabled = !receipt; }
});
byId("opportunity").addEventListener("change", showEvidence);
for (const link of document.querySelectorAll("nav a")) link.addEventListener("click", () => {
    for (const item of document.querySelectorAll("nav a")) item.removeAttribute("aria-current");
    link.setAttribute("aria-current", "page");
});
Promise.all([api("/api/opportunities"), api("/api/products"), api("/api/claims")]).then(([items, catalog, claims]) => {
    opportunities = items;
    products = catalog;
    const select = byId("opportunity");
    select.replaceChildren();
    for (const item of opportunities) {
        const option = element("option", `${item.opportunityId} / ${item.audience}`);
        option.value = item.opportunityId;
        select.append(option);
    }
    select.disabled = !items.length;
    byId("submit").disabled = !items.length;
    byId("counts").textContent = `${items.length} opportunities / ${catalog.length} products / ${claims.length} approved claim documents`;
    status(items.length ? "Versioned synthetic evidence loaded. Select a handoff." : "No opportunities are available.", !items.length);
    showEvidence();
}).catch(error => status(`Evidence unavailable: ${error.message}. No local or mock fallback is enabled.`, true));
