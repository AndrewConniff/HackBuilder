"use strict";
const byId = id => document.getElementById(id);
async function api(path, body) {
  const token = byId("token").value.trim();
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`/api/${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
    credentials: "omit"
  });
  const text = await response.text();
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${text}`);
  return JSON.parse(text);
}
byId("ask").addEventListener("click", async () => {
  byId("ask").disabled = true;
  byId("chatStatus").textContent = "Invoking the real Foundry agent…";
  byId("answer").textContent = "";
  byId("citations").replaceChildren();
  byId("envelope").textContent = "";
  try {
    const result = await api("chat", {
      question: byId("question").value, responseLanguage: byId("language").value,
      category: byId("category").value || null
    });
    byId("answer").textContent = result.result.answer;
    for (const citation of result.result.citations) {
      const li = document.createElement("li");
      const button = document.createElement("button");
      button.textContent = citation.feedbackId;
      button.addEventListener("click", async () => {
        try { byId("envelope").textContent = JSON.stringify(await api(`evidence/${citation.feedbackId}`), null, 2); }
        catch (e) { byId("chatStatus").textContent = e.message; }
      });
      li.append(button, document.createTextNode(` — ${citation.quote}`));
      byId("citations").append(li);
    }
    byId("envelope").textContent = JSON.stringify(result, null, 2);
    byId("chatStatus").textContent = result.result.insufficientEvidence
      ? "Agent reported insufficient evidence." : `Agent response ${result.responseId}; citations checked.`;
  } catch (e) { byId("chatStatus").textContent = `Not successful: ${e.message}`; }
  finally { byId("ask").disabled = false; }
});
byId("submit").addEventListener("click", async () => {
  try {
    const result = await api("feedback", JSON.parse(byId("feedback").value));
    byId("ingestResult").textContent = JSON.stringify(result, null, 2);
    await refresh();
  } catch (e) { byId("ingestResult").textContent = `Not successful: ${e.message}`; }
});
async function refresh() {
  try {
    const statuses = await api("status");
    byId("statuses").replaceChildren();
    for (const status of statuses) {
      const row = document.createElement("tr");
      for (const value of [status.feedbackId, status.state, status.correlationId, status.attempts]) {
        const cell = document.createElement("td");
        cell.textContent = String(value);
        row.append(cell);
      }
      byId("statuses").append(row);
    }
  } catch (e) { byId("ingestResult").textContent = e.message; }
}
byId("refresh").addEventListener("click", refresh);
