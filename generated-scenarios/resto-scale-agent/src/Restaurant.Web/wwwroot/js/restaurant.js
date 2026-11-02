"use strict";
const state = { visit: null, csrf: "", board: [], connected: false };
const staff = document.body.dataset.workspace === "staff";
const byId = id => document.getElementById(id);
const money = value => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value / 100);
function notice(text, error = false) {
  byId("notice").textContent = text;
  byId("notice").dataset.error = String(error);
}
async function api(path, body, accessToken) {
  const headers = {};
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    headers["X-CSRF-TOKEN"] = state.csrf;
  }
  const response = await fetch(path, { method: body === undefined ? "GET" : "POST", headers,
    credentials: "same-origin", body: body === undefined ? undefined : JSON.stringify(body) });
  const payload = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
  if (response.status === 401 && staff) clearStaff();
  if (!response.ok) throw new Error(payload.detail || payload.title || `Request failed: HTTP ${response.status}`);
  return payload;
}
function run(action) {
  return async event => {
    event?.preventDefault();
    try { await action(event); } catch (error) { notice(error.message, true); }
  };
}
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
async function refresh() {
  if (!state.visit?.id) throw new Error("Connect to a visit first.");
  state.visit = await api(`/api/visits/${encodeURIComponent(state.visit.id)}`);
  const visit = state.visit;
  const view = byId("visit");
  view.replaceChildren(element("p", `Visit ${visit.id} | floor ${visit.floor} | ${visit.status} | version ${visit.version}`));
  if (visit.totalMinor !== undefined)
    view.append(element("p", `Bill ${money(visit.totalMinor)} | ${visit.settled ? "Synthetically settled" : "Not settled"}`));
  for (const ticket of visit.tickets || [])
    view.append(element("p", `${ticket.id}: ${ticket.status}${ticket.dispatched ? "" : " - pending kitchen dispatch"}`));
  byId("checkin").disabled = visit.status !== "Reserved";
  byId("cancel").disabled = visit.status !== "Reserved";
  if (visit.status === "Cancelled")
    view.append(element("p", visit.allocationReleased ? "Capacity released." : "Capacity release pending durable compensation."));
  byId("settle").disabled = visit.settled || visit.totalMinor === undefined;
  document.querySelectorAll("#order button, #survey button").forEach(button => button.disabled = false);
}
async function preview(command) {
  if (!state.visit) throw new Error("Connect to or select a visit first.");
  showPreview(await api("/api/previews", { visitId: state.visit.id, expectedVersion: state.visit.version, ...command }));
}
function showPreview(preview) {
  const panel = byId("previews");
  const box = element("div", undefined, "preview");
  box.append(element("p", `${preview.command.kind} for ${preview.command.visitId}; expected version `
    + `${preview.command.expectedVersion}; resulting total ${money(preview.totalMinor)}. Expires ${preview.expiresAt}.`));
  box.append(element("pre", JSON.stringify(preview.command, null, 2)));
  const button = element("button", "Confirm this action");
  button.type = "button";
  const requestId = crypto.randomUUID();
  button.addEventListener("click", run(async () => {
    button.disabled = true;
    try {
      const receipt = await api("/api/confirm", { visitId: preview.command.visitId, previewId: preview.id, requestId });
      notice(`Committed ${receipt.action}; receipt ${receipt.id}; version ${receipt.version}.`);
      box.replaceChildren(element("p", `Committed receipt ${receipt.id}.`));
      if (state.visit?.id === preview.command.visitId) await refresh();
    } catch (error) { button.disabled = false; throw error; }
  }));
  box.append(button);
  panel.replaceChildren(box);
}
function showReservationPreview(preview) {
  const box = element("div", undefined, "preview");
  box.append(element("p", `Reservation proposal: ${preview.request.seats} seats, floor ${preview.request.floor}, `
    + `slot ${preview.request.slot}. Capacity version ${preview.expectedSlotVersion}. Expires ${preview.expiresAt}.`));
  const button = element("button", "Confirm this reservation");
  button.type = "button";
  button.addEventListener("click", run(async () => {
    button.disabled = true;
    try {
      const result = await api("/api/reservation-confirm", { slot: preview.request.slot, previewId: preview.id });
      box.replaceChildren(element("p", `Visit ${result.visitId}; access code ${result.accessCode || "use the originally issued code"}. `
        + `${result.status}. Keep this code securely; it is issued once.`));
    } catch (error) { button.disabled = false; throw error; }
  }));
  box.append(button);
  byId("previews").append(box);
}
async function board() {
  if (!state.connected) return;
  const floor = byId("floor-filter").value;
  const slot = `${byId("board-date").value}:${byId("board-turn").value}`;
  state.board = await api(`/api/board?slot=${encodeURIComponent(slot)}${floor ? `&floor=${floor}` : ""}`);
  const status = byId("status-filter").value;
  const target = byId("board");
  target.replaceChildren();
  for (const visit of state.board.filter(visit => !status || visit.status === status)) {
    const box = element("div", undefined, "ticket");
    box.append(element("h3", `Floor ${visit.floor} | ${visit.id} | ${visit.status}`));
    const select = element("button", "Select visit");
    select.addEventListener("click", run(async () => { state.visit = { id: visit.id }; await refresh(); }));
    box.append(select);
    for (const ticket of visit.tickets) {
      box.append(element("p", `${ticket.id}: ${ticket.status}; age ${ticket.ageSeconds}s; `
        + `${ticket.dispatched ? "dispatched" : "pending dispatch"}; `
        + ticket.lines.map(line => `${line.quantity} ${line.name}`).join(", ")));
      const next = { submitted: "accepted", accepted: "preparing", preparing: "ready", ready: "served" }[ticket.status];
      if (next) {
        const action = element("button", `Preview ${next}`);
        action.disabled = !ticket.dispatched;
        action.addEventListener("click", run(async () => {
          state.visit = { id: visit.id }; await refresh();
          await preview({ kind: "transition", ticketId: ticket.id, targetStatus: next });
        }));
        box.append(action);
      }
    }
    target.append(box);
  }
  if (!target.childNodes.length) target.append(element("p", "No visits in the selected authorized scope."));
}
byId("refresh")?.addEventListener("click", run(refresh));
byId("checkin")?.addEventListener("click", run(() => preview({ kind: "checkin" })));
byId("cancel")?.addEventListener("click", run(() => preview({ kind: "cancel" })));
byId("settle")?.addEventListener("click", run(() => preview({ kind: "settle" })));
byId("reserve")?.addEventListener("submit", run(async event => {
  const data = new FormData(event.target);
  const reservation = await api("/api/reservations", { slot: `${data.get("date")}:${data.get("turn")}`,
    floor: Number(data.get("floor")), seats: Number(data.get("seats")), guestId: "guest-001", requestId: crypto.randomUUID() });
  byId("reservation-result").textContent = `Visit ${reservation.visitId}\nAccess code ${reservation.accessCode}\n`
    + `${reservation.status}. Keep this code; it will not be returned again.`;
  byId("login").elements.visitId.value = reservation.visitId;
  byId("login").elements.accessCode.value = reservation.accessCode;
  notice("Reservation committed. Wait for projection, then connect.");
}));
byId("login")?.addEventListener("submit", run(async event => {
  const data = new FormData(event.target);
  const result = await api("/api/session", { visitId: data.get("visitId"), accessCode: data.get("accessCode") });
  state.csrf = (await api("/api/session/csrf")).token;
  state.visit = { id: result.visitId };
  await refresh(); notice("Connected to your scoped visit.");
}));
byId("order")?.addEventListener("submit", run(async event => {
  const items = Object.fromEntries([...new FormData(event.target)]
    .filter(([, quantity]) => Number(quantity) > 0).map(([id, quantity]) => [id, Number(quantity)]));
  await preview({ kind: "order", items });
}));
byId("survey")?.addEventListener("submit", run(async event =>
  preview({ kind: "survey", rating: Number(new FormData(event.target).get("rating")) })));
function clearStaff() {
  state.connected = false; state.visit = null; state.board = [];
  for (const id of ["board", "visit", "management", "previews", "chat-result", "staff-identity"])
    if (byId(id)) byId(id).replaceChildren();
  for (const id of ["checkin", "cancel", "settle"]) if (byId(id)) byId(id).disabled = true;
}
async function connectStaff() {
  const identity = await api("/api/staff/session");
  byId("staff-identity").textContent = `${identity.name} (${identity.employeeId}) | ${identity.role} | Floors ${identity.floors.join(", ")}`;
  state.csrf = (await api("/api/session/csrf")).token;
  state.connected = true;
  await board();
  notice("Connected. Every read and action remains server-authorized.");
}
byId("staff-session")?.addEventListener("submit", run(async event => {
  const button = event.target.querySelector("button");
  button.disabled = true;
  try {
    const token = await window.restaurantStaffLogin();
    state.csrf = (await api("/api/session/csrf", undefined, token)).token;
    await api("/api/staff/session", {}, token);
    clearStaff();
    await connectStaff();
  } finally { button.disabled = false; }
}));
byId("staff-logout")?.addEventListener("click", run(async () => {
  await api("/api/staff/logout", {});
  clearStaff();
  state.csrf = (await api("/api/session/csrf")).token;
  notice("Signed out. Staff data cleared.");
}));
byId("board-refresh")?.addEventListener("click", run(board));
byId("floor-filter")?.addEventListener("change", run(board));
byId("status-filter")?.addEventListener("change", run(board));
byId("board-date")?.addEventListener("change", run(board));
byId("board-turn")?.addEventListener("change", run(board));
byId("management-refresh")?.addEventListener("click", run(async () => {
  const result = await api("/api/management");
  byId("management").replaceChildren(
    element("p", `${result.paymentNotice}. ${result.settledVisits} settled visits; total ${money(result.settledTotalMinor)}.`),
    element("p", `Pending outbox: ${result.pendingOutboxReturned} returned (limit ${result.pendingLimit}). `
      + `Oldest: ${result.oldestPendingAt || "none returned"}.`),
    element("p", result.notice),
    element("pre", JSON.stringify({ deadLetters: result.deadLetters, replayRequests: result.replayRequests }, null, 2)));
}));
byId("replay")?.addEventListener("submit", run(async event => {
  const data = new FormData(event.target);
  const request = await api("/api/replay", { messageId: data.get("messageId"), sessionId: data.get("sessionId") });
  notice(`Audited replay request ${request.id} recorded as ${request.status}; refresh manager evidence for its outcome.`);
}));
byId("chat")?.addEventListener("submit", run(async event => {
  const button = event.target.querySelector("button");
  button.disabled = true;
  byId("chat-result").textContent = "Waiting for the real configured agent...";
  try {
    const result = await api("/api/chat", { message: new FormData(event.target).get("message"), visitId: state.visit?.id });
    byId("chat-result").textContent = `${result.answer}\nTrace ${result.correlationId}; tools ${result.toolCalls}; `
      + `Kitchen Advisor ${result.specialistInvoked ? "invoked" : "not invoked"}.`;
    for (const proposal of result.previews || []) showPreview(proposal);
    for (const proposal of result.reservationPreviews || []) showReservationPreview(proposal);
  } catch (error) {
    byId("chat-result").textContent = "Chat unavailable. No agent action or successful answer is claimed.";
    throw error;
  } finally { button.disabled = false; }
}));
run(async () => {
  state.csrf = (await api("/api/session/csrf")).token;
  if (staff) {
    try { await connectStaff(); }
    catch (error) { notice(error.message, true); }
  }
  if (!staff) {
    byId("reserve").elements.date.value = new Date().toISOString().slice(0, 10);
    const menu = await api("/api/menu");
    byId("menu").replaceChildren();
    for (const item of menu) {
      const label = element("label", undefined, "menu-item");
      label.append(element("span", `${item.name} ${money(item.priceMinor)}${item.vegetarian ? " | vegetarian" : ""}`
        + `${item.available ? "" : " | unavailable"} (v${item.version})`));
      const quantity = document.createElement("input");
      Object.assign(quantity, { type: "number", name: String(item.id), min: "0", max: "12", value: "0" });
      quantity.setAttribute("aria-label", `Quantity for ${item.name}`);
      quantity.disabled = !item.available;
      label.append(quantity); byId("menu").append(label);
    }
  }
})();
if (staff) {
  byId("board-date").value = new Date().toISOString().slice(0, 10);
  setInterval(run(board), 2000);
}
