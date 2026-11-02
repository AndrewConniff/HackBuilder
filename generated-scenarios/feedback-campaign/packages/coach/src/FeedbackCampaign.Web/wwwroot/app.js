"use strict";
let activeETag;
let csrfToken;
const el = id => document.getElementById(id);
async function api(path, body) {
  if (body && !csrfToken) csrfToken = (await api("/api/csrf")).token;
  const response = await fetch(path, {method: body ? "POST" : "GET", headers: body ? {"Content-Type":"application/json", "X-CSRF-TOKEN":csrfToken} : {}, body: body ? JSON.stringify(body) : undefined});
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${await response.text() || "Sign in / verify your assigned role."}`);
  return response.status === 202 || response.status === 201 ? null : response.json();
}
async function action(task) {
  try { el("status").className = ""; await task(); el("status").textContent = "Operation completed. Refresh to inspect durable state."; }
  catch (error) { el("status").textContent = error.message; el("status").className = "error"; }
}
async function refresh() {
  const cases = await api("/api/cases"); el("cases").replaceChildren();
  for (const row of cases) {
    const item = row.value, card = document.createElement("article"); card.className = "case";
    const heading = document.createElement("h3"); heading.textContent = `${item.post.subject} · ${item.status} · ${item.owner}`;
    const data = document.createElement("pre"); data.textContent = JSON.stringify(item, null, 2);
    card.append(heading, data);
    if (item.status === "AwaitingHuman") {
      const draft = document.createElement("textarea"); draft.value = item.analysis?.draft || ""; draft.maxLength = 4000;
      draft.setAttribute("aria-label", "Editable reply for assigned reviewer");
      const send = document.createElement("button"); send.textContent = "Approve edited reply and queue send";
      send.onclick = () => action(async () => { await api(`/api/cases/${item.id}/review`, {etag:row.eTag, reply:draft.value}); await refresh(); });
      card.append(draft, send);
    }
    if (item.status === "Failed") {
      const retry = document.createElement("button"); retry.textContent = "Retry failed analysis";
      retry.onclick = () => action(async () => { await api(`/api/cases/${item.id}/retry`, {etag:row.eTag}); await refresh(); });
      card.append(retry);
    }
    el("cases").append(card);
  }
}
el("intake").onsubmit = event => { event.preventDefault(); action(async () => { await api("/api/posts", Object.fromEntries(new FormData(event.target))); await refresh(); }); };
el("logout").onclick = () => action(async () => { await api("/api/logout", {}); window.location.assign("/Login"); });
el("refresh").onclick = () => action(refresh);
el("loadRules").onclick = () => action(async () => {
  const data = await api("/api/rules"); activeETag = data.active.eTag;
  el("rulesView").textContent = JSON.stringify(data, null, 2);
  const current = data.versions.find(r => r.value.version === data.active.value.version).value;
  el("ruleJson").value = JSON.stringify({...current, version:`v-${Date.now()}`, reason:"Describe reviewed business change"}, null, 2);
});
el("saveRules").onsubmit = event => { event.preventDefault(); action(async () => { await api("/api/rules", JSON.parse(el("ruleJson").value)); }); };
el("promote").onsubmit = event => { event.preventDefault(); action(async () => {
  if (!activeETag) throw new Error("Load the active pointer before promotion.");
  await api("/api/rules/promote", {...Object.fromEntries(new FormData(event.target)), etag:activeETag});
  activeETag = undefined;
}); };
el("chat").onsubmit = event => { event.preventDefault(); action(async () => {
  const data = await api("/api/chat", Object.fromEntries(new FormData(event.target)));
  el("chatReply").textContent = `${data.text}\nResponse: ${data.responseId}\nGrounding: ${data.grounding}`;
}); };
api("/api/me").then(me => { el("identity").textContent = `${me.name || "Authenticated user"} · ${me.roles.join(", ")}`; }).catch(error => { el("identity").textContent = error.message; });
