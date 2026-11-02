"use strict";
let csrfToken, activeStore, activeVersion, currentOrder, currentClose;
const byId = id => document.getElementById(id);
const money = value => new Intl.NumberFormat("en-US", {style:"currency",currency:"USD"}).format(value);
async function api(path, body) {
    const response = await fetch(`/api/${path}`, {
        method: body ? "POST" : "GET",
        credentials: "same-origin",
        headers: {"X-CSRF-TOKEN":csrfToken || "", "Content-Type":"application/json"},
        body: body ? JSON.stringify(body) : undefined
    });
    const data = response.headers.get("content-type")?.includes("application/json") ? await response.json() : null;
    if (!response.ok) throw new Error(data?.error || `Request failed (${response.status})`);
    return data;
}
function text(tag, content, parent, className) {
    const node = document.createElement(tag); node.textContent = content;
    if (className) node.className = className;
    parent.append(node); return node;
}
async function guard(action) {
    byId("status").textContent = "";
    try { await action(); } catch (error) { byId("status").textContent = error.message; }
}
async function loadStore(id) {
    activeStore = id; currentOrder = null; byId("approve").hidden = true; byId("order").textContent = "";
    const data = await api(`stores/${id}`);
    activeVersion = data.version;
    byId("store-title").textContent = `${data.store.name} · ${id} · ${data.store.manager}`;
    byId("metrics").replaceChildren();
    for (const [label, value] of [["Net sales",money(data.ledger.netSales)],["Managerial profit",money(data.ledger.profit)],
        ["Sales vs plan",money(data.ledger.salesVariance)],["Spoilage",money(data.ledger.waste)],
        ["Daily evidence",data.ledger.complete ? "Complete" : "Incomplete"]]) {
        const card = text("div",label,byId("metrics"),"metric"); text("strong",value,card);
    }
    byId("stock").replaceChildren();
    for (const row of data.stock) {
        const tr = document.createElement("tr");
        for (const value of [row.sku,`${row.onHand} ${row.unit}`,`${row.target} ${row.unit}`,money(row.unitCost)])
            text("td",value,tr);
        byId("stock").append(tr);
    }
    byId("draft").disabled = false;
    byId("import-day").disabled = false;
    byId("recipe-evidence").textContent = data.input
        ? `${data.input.recipes.length} recipe components; ${data.input.sales.length} sales lines; ` +
          `${data.input.spoilage.length} spoilage lines. Closing stock deducts both recipe usage and spoilage.`
        : "Raw recipe evidence unavailable.";
}
async function session() {
    const state = await api("session");
    csrfToken = state.csrfToken;
    byId("login").hidden = state.authenticated;
    byId("signout").hidden = !state.authenticated;
    byId("identity").textContent = state.authenticated ? state.username : "Authentication required for business data.";
    if (!state.authenticated) return;
    byId("stores").replaceChildren();
    const stores = state.stores;
    if (!stores.length) throw new Error("No server-owned store assignment. Contact the scenario installer.");
    for (const id of stores) {
        const row = text("div","",byId("stores"),"store-choice");
        const check = document.createElement("input"); check.type = "checkbox"; check.value = id; check.checked = true;
        check.setAttribute("aria-label",`Include store ${id} in daily close`); row.append(check);
        const button = text("button",`Store ${id}`,row); button.onclick = () => guard(() => loadStore(id));
    }
    byId("chat").disabled = false; await loadStore(stores[0]);
}
byId("login").onsubmit = event => {
    event.preventDefault();
    guard(async () => {
        byId("signin").disabled = true;
        try {
            if (!csrfToken) await session();
            await api("auth/login", {username:byId("username").value, password:byId("password").value});
            await session();
        } finally {
            byId("password").value = "";
            byId("signin").disabled = false;
        }
    });
};
byId("signout").onclick = () => guard(async () => {
    await api("auth/logout", {});
    location.reload();
});
byId("draft").onclick = () => guard(async () => {
    currentOrder = await api("orders/draft",{storeId:activeStore});
    byId("order").textContent = `${currentOrder.status} ${currentOrder.draftId}\n` +
        currentOrder.lines.map(line => `${line.sku}: ${line.quantity} ${line.unit} / ${money(line.total)}`).join("\n") +
        `\nTotal: ${money(currentOrder.total)}\nExpires: ${currentOrder.expiresAt}`;
    byId("approve").hidden = currentOrder.status === "Approved";
});
byId("approve").onclick = () => guard(async () => {
    const result = await api(`orders/${activeStore}/${currentOrder.draftId}/approve`,{confirm:true});
    byId("order").textContent = `Approved internal order ${result.draftId} · ${money(result.total)}\n` +
        `Approver account: ${result.approvedBy}\nNo supplier transmission.`;
    byId("approve").hidden = true;
});
byId("import-day").onclick = () => guard(async () => {
    const file = byId("csv-file").files[0];
    if (!file || file.size > 24000) throw new Error("Choose a CSV file no larger than 24,000 bytes.");
    byId("import-day").disabled = true;
    try {
        await api(`stores/${activeStore}/import`, {expectedVersion:activeVersion, csv:await file.text()});
        await loadStore(activeStore);
        byId("status").textContent = "Day packet imported atomically. Generate a new report for the updated evidence.";
        currentClose = null; byId("review-close").hidden = true;
    } finally { byId("import-day").disabled = false; }
});
byId("review-close").onclick = () => guard(async () => {
    if (!currentClose) throw new Error("Generate a daily report first.");
    const result = await api(`closes/${currentClose}/review`, {confirm:true});
    byId("status").textContent = `${result.status} by ${result.reviewedBy} at ${result.reviewedAt}. No ledger posting.`;
    byId("review-close").hidden = true;
});
guard(session);
byId("chat").onclick = () => guard(async () => {
    byId("chat").disabled = true; byId("answer").replaceChildren();
    currentClose = null; byId("review-close").hidden = true;
    byId("status").textContent = "Partitioning authorized stores into stock/margin workers, then reconciling receipts...";
    try {
        const result = await api("chat",{storeIds:[...document.querySelectorAll("#stores input:checked")].map(n=>n.value),
            question:byId("question").value});
        byId("status").textContent = `${result.status} · ${result.correlationId} · authoritative profit ${money(result.profit)}`;
        currentClose = result.correlationId; byId("review-close").hidden = false;
        text("p",`${result.assignments.length} store/domain assignments completed. ` +
            "The report is not final until you explicitly review it.",byId("answer"));
        for (const receipt of [...result.assignments.map(assignment => assignment.agent), ...result.agents]) {
            const section = text("section","",byId("answer"),"receipt");
            text("h3",`${receipt.agent} / v${receipt.version}`,section);
            text("p",receipt.text,section); text("small",`Response ${receipt.responseId}`,section);
        }
    } finally { byId("chat").disabled = false; }
});
