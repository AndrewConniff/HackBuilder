"use strict";
const $ = (id) => document.getElementById(id);
let selected = "";
let scenarios = [];
let busy = false;
let polling = false;
let fileSignature = "";
let selectionVersion = 0;
let reviewContext = null;
let reviewSignature = "";
let scopingDraftSlug = "";
let scopingPendingSlug = "";
let systemBusy = false;
let systemReport = null;
let systemIdentity = null;
let projectSignature = "";
let viewVersion = 0;
let reuseSource = null;
let entryMode = "new";
let reuseDiscoveryEnabled = false;
let matchTimer = null;
let matchVersion = 0;
let dismissedMatchInput = "";
let acceptedMatchTitle = "";
let briefMatchContext = "";
let completedMatchInput = "";
let inFlightMatchInput = "";
let inFlightMatchVersion = 0;
const conversations = new Map();
const conversationDrafts = new Map();
let conversationKey = "";
let conversationSignature = "";
let conversationSending = "";
const views = ["create", "build", "hack", "system"];
const referenceStages = ["requirements", "architecture", "diagrams", "bicep", "application",
  "local-validation", "deployment", "live-validation", "review"];

function showView(view, focus = false) {
  viewVersion++;
  if (!views.includes(view)) view = "create";
  for (const name of views) {
    $(`view-${name}`).hidden = name !== view;
    $(`nav-${name}`).setAttribute("aria-current", name === view ? "page" : "false");
  }
  $("project-switch").hidden = !["build", "hack"].includes(view);
  $("preview").hidden = true;
  drawBoard();
  updateSelectionVisibility();
  if (focus) {
    const title = { create: "intake-title", build: "build-title", hack: "hack-title-heading", system: "system-title" }[view];
    $(title).focus();
  }
}
function navigate(view) {
  location.hash = `#${view}`;
  showView(view, true);
}
function initializeNavigation() {
  showView(location.hash.slice(1));
  for (const view of views) {
    $(`nav-${view}`).addEventListener("click", (event) => {
      event.preventDefault();
      navigate(view);
    });
  }
  addEventListener("hashchange", () => showView(location.hash.slice(1), true));
}

function initializeAppearance() {
  const key = "fbcbuilder-theme";
  const system = matchMedia("(prefers-color-scheme: dark)");
  const selector = $("theme");
  const notice = $("theme-notice");
  const storageError = (value) => {
    if (!["SecurityError", "QuotaExceededError"].includes(value.name)) throw value;
    console.warn("Appearance preference could not be stored by this browser.", value);
    notice.textContent = "Appearance applies to this tab only because browser storage is unavailable.";
    notice.hidden = false;
  };
  const apply = () => {
    document.documentElement.dataset.theme = selector.value === "system"
      ? (system.matches ? "dark" : "light") : selector.value;
  };
  const read = () => {
    selector.value = "system";
    try {
      const saved = localStorage.getItem(key);
      if (saved === "light" || saved === "dark") selector.value = saved;
      else if (saved !== null) console.warn("Ignoring an invalid saved appearance preference; using the system theme.");
    } catch (value) { storageError(value); }
    apply();
  };
  read();
  selector.addEventListener("change", () => {
    apply();
    try {
      if (selector.value === "system") localStorage.removeItem(key);
      else localStorage.setItem(key, selector.value);
      notice.hidden = true;
    } catch (value) { storageError(value); }
  });
  system.addEventListener("change", () => { if (selector.value === "system") apply(); });
  addEventListener("storage", (event) => {
    if (event.key === key || event.key === null) read();
  });
}

async function api(url, body) {
  let response;
  try {
    response = await fetch(url, body === undefined ? {} : {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
  } catch (value) {
    if (value.name !== "TypeError") throw value;
    throw new Error("Cannot reach the local portal. Check that the FBC Builder runtime is running. "
      + "Your last action was not acknowledged; check its status before retrying.");
  }
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || `Request failed (${response.status}).`);
  return value;
}
function error(value) { $("error").textContent = value.message; $("error").hidden = false; }
function group(item) {
  if (item.scoping?.canRespond && item.scoping.responseCurrent
      && item.scoping.response?.continuation?.status === "failed") return "Needs attention";
  if (item.scoping?.canRespond && item.scoping.responseCurrent
      && item.scoping.response?.continuation?.status === "dispatched") return "Starting";
  if (briefConfirmed(item)) return "Ready to start";
  return { running: "Building", in_progress: "Building", handed_off: "Starting",
    waiting_for_user: "Waiting for you", blocked: "Needs attention", failed: "Needs attention",
    completed: "Ready to export", approved: "Scenario approved", saved: "Ready to start" }[item.progress.status]
    || "Status unavailable";
}
function briefConfirmed(item) {
  return Boolean(item.scoping?.canRespond && item.scoping.responseCurrent
    && item.scoping.canConfirm !== false && item.scoping.response?.decision === "confirmed");
}
function renderScopingResponse(item) {
  const canRespond = item.scoping?.canRespond;
  const confirmed = briefConfirmed(item);
  const editing = !$("scoping-editor").hidden;
  const draft = $("scoping-changes").value.trim();
  const response = item.scoping?.response;
  const reusePending = item.scoping?.reuseSelection && item.scoping.canConfirm === false;
  const dispatched = Boolean(item.scoping?.responseCurrent && response?.continuation?.status === "dispatched");
  const confirmationSent = confirmed && dispatched && !draft;
  const needsReview = Boolean(canRespond && !dispatched);
  $("scoping-notes").dataset.attention = String(needsReview);
  $("brief-review-cue").textContent = !canRespond ? "Saved brief / reference copy"
    : scopingPendingSlug === selected ? "Sending your brief response..."
    : reusePending ? "Reuse assessment pending / fresh brief confirmation required"
    : dispatched ? confirmed ? "Brief confirmed / waiting for the agent's next update"
      : "Changes sent / waiting for a revised brief"
    : item.scoping?.responseCurrent && response?.continuation?.status === "failed"
      ? "Action needed: review the brief below, then retry using its confirmation or change controls."
      : "Ready for your review: read the brief below, then choose Modify brief or Confirm brief.";
  for (const id of ["scoping-request-changes", "scoping-open-chat", "scoping-cancel"]) $(id).disabled = busy || !canRespond;
  $("scoping-modify").disabled = busy || !canRespond || editing;
  $("scoping-modify").setAttribute("aria-expanded", String(editing));
  $("scoping-confirm").disabled = busy || !canRespond || item.scoping?.canConfirm === false || editing || confirmationSent;
  $("scoping-confirm").textContent = confirmationSent ? "Brief confirmed" : "Confirm brief";
  $("scoping-open-chat").textContent = "Open scenario chat";
  const changesSaved = canRespond && item.scoping.responseCurrent && response?.decision === "changes_requested";
  const responseText = !response ? ""
    : !item.scoping.responseCurrent ? "The brief changed after your response. Review it again before confirming."
    : response.decision === "confirmed"
      ? dispatched ? "Brief confirmed. Continuation requested in the existing scenario agent; waiting for its next progress report."
        : response.continuation?.status === "failed"
          ? "Brief confirmation was saved, but continuation was not acknowledged. Select Confirm brief to retry."
          : "Brief confirmed. Select Confirm brief to continue the normal workflow without writing a prompt."
      : `Changes requested: ${response.changes}\n${dispatched
        ? "Revision requested in the existing scenario agent. Waiting for the updated brief."
        : "The revision has not been acknowledged. Select Modify brief, then Save changes to retry."}`;
  $("scoping-response-status").textContent = scopingPendingSlug === selected ? "Saving your brief response..." : responseText;
  const context = `${item.projectSlug}:${item.scoping?.fingerprint}`;
  if (briefMatchContext !== context) {
    $("brief-reuse-cards").replaceChildren();
    briefMatchContext = context;
  }
  $("brief-reuse-compare").disabled = busy || !canRespond || dispatched || !reuseDiscoveryEnabled;
  const activeSource = item.scoping?.reuseSelection ? item.scoping.reuseSelection.source : item.reuseSource;
  $("brief-reuse-clear").hidden = !activeSource;
  $("brief-reuse-clear").disabled = busy || !canRespond || dispatched;
  $("brief-reuse-status").textContent = reusePending
    ? "Source decision saved. The agent must assess it and revise this brief before you can confirm. "
      + "If delivery failed, review the saved changes below and use Save changes to retry."
    : item.scoping?.reuseSelection ? "Source decision assessed. Review the revised brief before fresh confirmation."
      : activeSource ? `This brief starts from ${activeSource.scenarioId}. Review the fit, choose another source or build fresh.`
      : "Keep building fresh, or explicitly select a source. Your original request stays unchanged.";
  if (canRespond) {
    $("summary").textContent = confirmed ? responseText
      : changesSaved ? responseText
      : item.progress.summary;
    $("next-action").textContent = confirmed
      ? dispatched ? "The normal scenario workflow has been requested. Progress appears when the existing agent reports it."
        : "Select Confirm brief to continue the normal workflow in the existing scenario agent. No prompt writing is needed."
      : changesSaved ? responseText
      : "Review Your scenario brief in the document box above, then choose Modify brief or Confirm brief.";
  }
  const stages = (item.stages || []).filter((stage) => !stage.id.startsWith("hack-")).map((stage) => {
    if (stage.id !== "requirements" || stage.status !== "waiting_for_user" || (!confirmed && !changesSaved)) {
      return stage;
    }
    return { ...stage, status: confirmed ? "brief_confirmed" : "changes_requested",
      summary: confirmed
        ? responseText
        : "Requested changes saved. The existing scenario agent will revise the brief after the continuation is dispatched.",
      updatedAtUtc: response.recordedAtUtc };
  });
  renderMilestones(stages, "stage-history", "stage-count");
}
function hackEligible(item) {
  if (item.approval?.approved !== true) return false;
  const stages = (item.stages || []).filter((stage) => referenceStages.includes(stage.id));
  if (referenceStages.every((id) => stages.some((stage) => stage.id === id && stage.status === "completed"))) {
    return true;
  }
  return item.composition?.status === "packages_validated"
    && stages.every((stage) => ["completed", "available", "not_reported"].includes(stage.status));
}
function updateSelectionVisibility() {
  const item = scenarios.find((entry) => entry.projectSlug === selected);
  const eligible = Boolean(item && hackEligible(item));
  const visible = Boolean(item && ($("view-hack").hidden || eligible)
    && ($("view-build").hidden || !eligible));
  $("scenario").hidden = !visible;
  $("hack-empty").hidden = eligible;
  $("hack-detail").hidden = !eligible;
  $("open-agent").hidden = !visible;
  $("scenario-chat-link-status").hidden = !visible;
  renderConversation();
}

function conversationScope() {
  const item = scenarios.find((entry) => entry.projectSlug === selected);
  if (!item || (!$("view-hack").hidden && !hackEligible(item))
      || (!$("view-build").hidden && hackEligible(item))
      || ($("view-build").hidden && $("view-hack").hidden)) return null;
  const phase = $("view-hack").hidden ? "scenario" : "composition";
  return { slug: selected, phase, key: `${selected}:${phase}` };
}
function renderConversation() {
  const scope = conversationScope();
  $("conversation").hidden = !scope;
  if (!scope) return;
  const current = conversations.get(scope.key);
  const draft = conversationDrafts.get(scope.key);
  if (conversationKey !== scope.key) {
    $("conversation-input").value = draft?.text || "";
    $("conversation-error").hidden = true;
    conversationKey = scope.key;
  }
  $("conversation-context").textContent = `${scope.slug} / ${scope.phase === "scenario" ? "Scenario" : "Hack composition"}`;
  const signature = JSON.stringify([scope.key, current?.messages]);
  if (signature !== conversationSignature) {
    const history = $("conversation-messages");
    const nearBottom = history.scrollHeight - history.scrollTop - history.clientHeight < 48;
    const firstRender = !conversationSignature || JSON.parse(conversationSignature)[0] !== scope.key;
    $("conversation-messages").replaceChildren(...(current?.messages || []).map((message) => {
      const li = document.createElement("li");
      li.dataset.role = message.role;
      const author = document.createElement("strong");
      author.textContent = message.role === "user" ? "You" : `Agent report / ${message.stage}`;
      const text = document.createElement("p");
      text.textContent = message.text;
      const status = document.createElement("small");
      const labels = { dispatched: "Sent to editor; agent response not yet confirmed",
        dispatching: "Delivery unconfirmed; check agent chat before sending again",
        unknown: "Delivery uncertain; check agent chat before sending again",
        failed: "Not sent; explicit retry is available", pending: "Not yet sent" };
      status.textContent = `${labels[message.status] || message.status.replaceAll("_", " ")}`
        + (message.updatedAtUtc ? ` / ${new Date(message.updatedAtUtc).toLocaleString()}` : "")
        + (message.error ? ` / ${message.error}` : "");
      li.append(author, text, status);
      return li;
    }));
    if (nearBottom || firstRender) history.scrollTop = history.scrollHeight;
    conversationSignature = signature;
  }
  $("conversation-status").textContent = conversationSending === scope.key
    ? "Sending to the existing agent conversation..."
    : current?.canSend ? "Replies go to this phase's existing conversation. Dispatch is not proof of agent execution."
      : "Open or start this phase's conversation using the existing workflow controls before sending a message.";
  $("conversation-input").disabled = conversationSending === scope.key;
  $("conversation-send").disabled = busy || Boolean(conversationSending) || !current?.canSend
    || !$("conversation-input").value.trim();
  $("conversation-open").disabled = busy || Boolean(conversationSending);
}
async function loadConversation() {
  const scope = conversationScope();
  if (!scope) return;
  try {
    const value = await api(`/api/conversation?project=${encodeURIComponent(scope.slug)}&phase=${scope.phase}`);
    conversations.set(scope.key, value);
    if (conversationScope()?.key === scope.key) renderConversation();
  } catch (value) {
    conversations.delete(scope.key);
    if (conversationScope()?.key === scope.key) {
      renderConversation();
      $("conversation-error").textContent = `Conversation unavailable: ${value.message}`;
      $("conversation-error").hidden = false;
    }
  }
}
async function sendConversationMessage() {
  const scope = conversationScope();
  if (!scope || busy || conversationSending || !conversations.get(scope.key)?.canSend) return;
  const text = $("conversation-input").value.trim();
  if (!text) return;
  const previous = conversationDrafts.get(scope.key);
  const draft = previous?.text.trim() === text && previous.requestId ? previous
    : { text, requestId: crypto.randomUUID().replaceAll("-", "") };
  conversationDrafts.set(scope.key, draft);
  conversationSending = scope.key;
  $("conversation-error").hidden = true;
  renderConversation();
  try {
    const value = await api("/api/conversation/send", {
      projectSlug: scope.slug, phase: scope.phase, text, requestId: draft.requestId,
    });
    if (value.status === "dispatched") {
      conversationDrafts.delete(scope.key);
      if (conversationScope()?.key === scope.key) $("conversation-input").value = "";
    } else {
      throw new Error(value.error || "Delivery is unconfirmed. Check the existing agent chat; no automatic retry occurred.");
    }
  } catch (value) {
    if (conversationScope()?.key === scope.key) {
      $("conversation-error").textContent = value.message;
      $("conversation-error").hidden = false;
    }
  } finally {
    conversationSending = "";
    await loadConversation();
    renderConversation();
  }
}
function drawBoard() {
  const hackItems = scenarios.filter(hackEligible);
  const referenceItems = scenarios.filter((item) => !hackEligible(item));
  const items = !$("view-hack").hidden ? hackItems
    : !$("view-build").hidden ? referenceItems : scenarios;
  const options = items.map((item) => [item.projectSlug, `${item.title} - ${group(item)}`]);
  const signature = JSON.stringify(options);
  if (signature !== projectSignature) {
    $("active-project").replaceChildren(new Option("Choose a scenario", ""),
      ...options.map(([slug, title]) => new Option(title, slug)));
    projectSignature = signature;
  }
  $("active-project").value = items.some((item) => item.projectSlug === selected) ? selected : "";
  drawScenarioBoard(referenceItems, "board");
  drawScenarioBoard(hackItems, "hack-board");
}
function drawScenarioBoard(items, id) {
  $(id).replaceChildren(...["Needs attention", "Waiting for you", "Building", "Starting",
    "Ready to start", "Scenario approved", "Ready to export", "Status unavailable"]
    .filter((name) => items.some((item) => group(item) === name)).map((name) => {
    const section = document.createElement("section");
    section.className = "column";
    const grouped = items.filter((item) => group(item) === name);
    const title = document.createElement("h3");
    title.textContent = `${name} (${grouped.length})`;
    section.append(title);
    for (const item of grouped) {
      const button = document.createElement("button");
      button.className = "card";
      button.type = "button";
      button.setAttribute("aria-pressed", String(selected === item.projectSlug));
      const heading = document.createElement("strong");
      heading.textContent = item.projectSlug;
      const stage = document.createElement("small");
      stage.textContent = item.progress.stage
        ? `${item.progress.stage.replaceAll("-", " ")} - ${item.progress.status === "in_progress"
          ? "step completed; scenario still in progress" : group(item)}`
        : item.progress.summary;
      button.append(heading, stage);
      button.addEventListener("click", () => select(item.projectSlug).catch(error));
      section.append(button);
    }
    return section;
  }));
}
async function refresh() {
  if (polling) return;
  polling = true;
  try {
    scenarios = await api("/api/scenarios");
    drawBoard();
    if (selected) await detail();
  } finally { polling = false; }
}
async function select(slug) {
  selectionVersion++;
  selected = slug;
  fileSignature = "";
  reviewContext = null;
  reviewSignature = "";
  $("deployment-review").hidden = true;
  $("scenario-handoff-status").textContent = "";
  $("hack-handoff-status").textContent = "";
  $("preview").hidden = true;
  $("files").replaceChildren();
  $("package-folder-status").textContent = "";
  drawBoard();
  await detail();
}
function renderMilestones(stages, listId, countId) {
  const statuses = { completed: "Completed", running: "Running", waiting_for_user: "Waiting for your input",
    blocked: "Blocked", failed: "Failed", handed_off: "Handed off", available: "Artifacts available",
    brief_confirmed: "Brief confirmed", changes_requested: "Changes saved - revision pending",
    not_reported: "Not started / unreported" };
  $(countId).textContent = stages.length
    ? `${stages.filter((stage) => stage.status === "completed").length} of ${stages.length} milestones completed`
    : "No stage history available";
  $(listId).replaceChildren(...stages.map((stage) => {
    const li = document.createElement("li");
    li.dataset.status = stage.status;
    const icon = document.createElement("span");
    icon.className = "milestone-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = { blocked: "!", failed: "!", waiting_for_user: "?", handed_off: "..." }[stage.status] || "";
    const heading = document.createElement("strong");
    heading.textContent = stage.label;
    const status = document.createElement("span");
    status.className = "tag";
    status.textContent = statuses[stage.status] || stage.status;
    const summary = document.createElement("p");
    summary.textContent = stage.summary;
    li.append(icon, heading, status, summary);
    if (stage.updatedAtUtc) {
      const time = document.createElement("small");
      time.className = "muted";
      time.textContent = `Reported: ${new Date(stage.updatedAtUtc).toLocaleString()}`;
      li.append(time);
    }
    return li;
  }));
}
async function detail() {
  const item = scenarios.find((entry) => entry.projectSlug === selected);
  updateSelectionVisibility();
  if (!item) return;
  $("scenario-title").textContent = item.title;
  $("scenario-status").textContent = group(item);
  $("summary").textContent = item.progress.summary;
  $("updated").textContent = item.progress.updatedAtUtc
    ? `Last agent report: ${new Date(item.progress.updatedAtUtc).toLocaleString()}. This is reported progress, not a process monitor.`
    : "No agent progress report yet. Existing files and old portal worker errors do not establish current agent state.";
  const stages = item.stages || [];
  $("scoping-notes").hidden = !item.scoping?.available;
  if (item.scoping?.available) renderMarkdown($("scoping-content"), item.scoping.text);
  else $("scoping-content").replaceChildren();
  if (scopingDraftSlug !== selected) {
    $("scoping-changes").value = "";
    $("scoping-editor").hidden = true;
    $("scoping-response-error").hidden = true;
    $("scoping-response-error").textContent = "";
    $("scoping-chat-status").textContent = "";
    scopingDraftSlug = selected;
  }
  $("scoping-response").hidden = !item.scoping?.canRespond;
  renderMilestones(stages.filter((stage) => stage.id.startsWith("hack-")), "hack-stage-history", "hack-stage-count");
  $("steps").replaceChildren(...Object.entries(item.progress.steps || {})
    .filter(([stage]) => !stage.startsWith("hack-")).map(([stage, value]) => {
    const li = document.createElement("li");
    li.textContent = `${stage.replaceAll("-", " ")}: ${value.status} - ${value.summary}`;
    return li;
  }));
  const actions = item.actions || {};
  if (!actions.canExport) {
    for (const id of ["export-actions", "export-help", "learner-zip", "coach-zip"]) $(id).hidden = true;
  }
  $("open-agent").textContent = item.progress.status === "saved" ? "Start scenario chat" : "Open scenario chat";
  $("scenario-chat-link-status").textContent = item.progress.status === "saved"
    ? "Starts this scenario's conversation and records its handoff trace."
    : "Automatically finds and reopens this scenario's existing conversation. No copying or new chat is needed.";
  $("package-folder-actions").hidden = !item.packageFolder;
  $("package-folder-path").textContent = item.packageFolder || "";
  $("open-package-folder").disabled = busy;
  $("open-composition").textContent = "Create hack materials";
  $("open-composition").hidden = !actions.canCompose;
  $("composition-help").hidden = !actions.canCompose;
  $("open-hack").hidden = !actions.canCompose && !actions.canExport;
  $("scenario-actions").hidden = !actions.canCompose && !actions.canExport;
  $("hack-project-title").textContent = item.title;
  $("hack-status").textContent = group(item);
  $("hack-guidance").textContent = actions.canCompose
    ? "The working scenario is approved. Create and validate the learner and private coach materials below."
    : actions.canExport ? "Hack materials are validated and ready to export. Event deployment remains a separate request."
    : ["running", "in_progress", "handed_off"].includes(item.progress.status)
      ? "Work is still in progress. Hack creation and exports remain unavailable until their approval and validation requirements are met."
      : `Hack creation and exports depend on scenario approval and package validation. ${
        item.approval?.reason || "Follow the next action in Build & validate."}`;
  $("next-action").textContent = actions.canCompose
    ? "Scenario approved. Open Create hack to compose the learner and private coach materials."
    : actions.canExport ? "Hack materials are validated. Open Create hack to export them. No event deployment is implied."
    : {
      running: "Building is in progress. No action is needed here; respond in the existing agent chat if requested.",
      in_progress: "The latest step is complete, but the scenario is still being built. No action is needed here.",
      handed_off: "Your brief was sent. Check the agent chat if its first progress report does not appear.",
      waiting_for_user: "Your response is needed in the existing agent chat. Follow the request above.",
      saved: "Your brief is saved but building has not started. Select Start scenario chat to begin.",
      unknown: "No current progress is available. Check the existing agent chat before opening another one.",
      blocked: "Building needs attention. Review the issue above in the existing agent chat.",
      failed: "Building reported a failure. Review the issue above in the existing agent chat.",
    }[item.progress.status] || "Check the existing agent chat for the next step.";
  if (!actions.canCompose && item.approval?.reason && item.progress.status === "waiting_for_user") {
    $("next-action").textContent += ` Hack materials are not available: ${item.approval.reason}`;
  }
  renderScopingResponse(item);
  $("open-agent").disabled = busy;
  $("open-composition").disabled = busy;
  const slug = selected, version = selectionVersion;
  await loadConversation();
  if (version !== selectionVersion) return;
  await showDeploymentReview(item, slug, version);
  if (version !== selectionVersion) return;
  const files = await api(`/api/files?project=${encodeURIComponent(slug)}`);
  if (version !== selectionVersion) return;
  let hasExport = false;
  for (const audience of ["learner", "coach"]) {
    const available = actions.canExport && files.some((file) => file.audience === audience);
    $(`${audience}-zip`).hidden = !available;
    hasExport ||= available;
    $(`${audience}-zip`).href = `/api/export?project=${encodeURIComponent(slug)}&audience=${audience}`;
  }
  $("export-actions").hidden = !hasExport;
  $("export-help").hidden = !hasExport;
  const signature = JSON.stringify(files);
  if (signature === fileSignature) return;
  fileSignature = signature;
  $("files").replaceChildren(...fileGroups(files, [["reference", "Reference"]], slug));
}
function fileGroups(files, audiences, slug) {
  return audiences
    .filter(([audience]) => files.some((file) => file.audience === audience))
    .map(([audience, name]) => {
      const section = document.createElement("section");
      const heading = document.createElement("h3");
      heading.textContent = name;
      section.append(heading);
      for (const file of files.filter((entry) => entry.audience === audience)) {
        const button = document.createElement("button");
        button.className = "file";
        button.type = "button";
        button.textContent = file.path;
        button.addEventListener("click", () => preview(slug, file.path).catch(error));
        section.append(button);
      }
      return section;
    });
}
async function showDeploymentReview(item, slug, version) {
  reviewContext = null;
  if (item.progress.status !== "waiting_for_user") {
    $("deployment-review").hidden = true;
    reviewSignature = "";
    return;
  }
  const review = await api(`/api/review?project=${encodeURIComponent(slug)}`);
  if (version !== selectionVersion) return;
  $("deployment-review").hidden = !review.available;
  if (!review.available) {
    reviewSignature = "";
    return;
  }
  if (review.fingerprint !== reviewSignature) {
    renderMarkdown($("review-content"), review.text);
    $("review-path").textContent = review.path;
    reviewSignature = review.fingerprint;
  }
  reviewContext = { slug, fingerprint: review.fingerprint };
  $("next-action").textContent = "Read the review below, then use Open scenario chat above to respond in the existing "
    + "conversation. Matching prior consent is reused; only unresolved scope needs a response.";
}
async function preview(slug, path) {
  const version = selectionVersion, view = viewVersion;
  const url = `/api/file?project=${encodeURIComponent(slug)}&path=${encodeURIComponent(path)}`;
  const response = await fetch(url);
  if (!response.ok) throw new Error((await response.json()).error);
  const image = path.toLowerCase().endsWith(".png");
  const markdown = path.toLowerCase().endsWith(".md");
  const text = image ? "" : await response.text();
  if (version !== selectionVersion || view !== viewVersion) return;
  $("preview").hidden = false;
  $("preview-title").textContent = path;
  $("preview-image").hidden = !image;
  $("preview-text").hidden = image || markdown;
  $("preview-markdown").hidden = !markdown;
  if (image) $("preview-image").src = url;
  else if (markdown) renderMarkdown($("preview-markdown"), text);
  else $("preview-text").textContent = text;
  $("preview").scrollIntoView({ behavior: "smooth", block: "start" });
}
async function handoff(phase) {
  if (!selected) throw new Error("Select a scenario.");
  const request = { projectSlug: selected, phase };
  if (phase === "deployment-review") {
    if (reviewContext?.slug !== selected) throw new Error("Refresh and read the current review before continuing.");
    request.reviewFingerprint = reviewContext.fingerprint;
  }
  const value = await api("/api/handoff", request);
  $("handoff-status").textContent = value.message;
  $("scenario-handoff-status").textContent = value.message;
  $("hack-handoff-status").textContent = value.message;
}
async function reopenChat(phase) {
  if (!selected) throw new Error("Select a scenario.");
  const value = await api("/api/chat-open", { projectSlug: selected, phase });
  $("scenario-chat-link-status").textContent = value.message;
  return value;
}
async function openScenarioChat() {
  const item = scenarios.find((entry) => entry.projectSlug === selected);
  if (!item) throw new Error("Select a scenario.");
  if (item.progress.status === "saved" && !item.chatLinks?.scenario) {
    await handoff(item.intakeMode === "scope" ? "scoping" : "scenario");
  }
  else await reopenChat("scenario");
}
async function respondToScoping(decision) {
  const slug = selected;
  const item = scenarios.find((entry) => entry.projectSlug === selected);
  if (!item?.scoping?.canRespond) throw new Error("Refresh and review a brief that is awaiting your response.");
  const changes = $("scoping-changes").value.trim();
  if (decision === "changes_requested" && !changes) throw new Error("Describe the changes you want before submitting.");
  if (decision === "confirmed" && changes) throw new Error("Submit your requested changes or clear them before confirming.");
  scopingPendingSlug = slug;
  renderScopingResponse(item);
  try {
    const value = await api("/api/scoping-response", {
      projectSlug: slug, fingerprint: item.scoping.fingerprint, decision, changes,
    });
    const current = scenarios.find((entry) => entry.projectSlug === slug);
    if (current?.scoping) {
      current.scoping.response = value.response;
      current.scoping.responseCurrent = value.response.fingerprint === current.scoping.fingerprint;
    }
    if (selected !== slug) return;
    $("scoping-changes").value = "";
    $("scoping-editor").hidden = true;
    drawBoard();
    if (current) $("scenario-status").textContent = group(current);
  } finally {
    scopingPendingSlug = "";
  }
}
async function action(work, scoping = false) {
  if (busy) return;
  const slug = selected;
  busy = true;
  renderConversation();
  $("error").hidden = true;
  if (scoping) $("scoping-response-error").hidden = true;
  const buttons = ["create", "refine", "reuse-source", "reuse-load", "reuse-clear", "open-agent", "open-composition",
    "scoping-confirm", "scoping-modify", "scoping-request-changes", "scoping-cancel", "scoping-open-chat"];
  for (const id of buttons) $(id).disabled = true;
  try { await work(); } catch (value) {
    error(value);
    if (scoping && selected === slug) {
      $("scoping-response-error").textContent = value.message;
      $("scoping-response-error").hidden = false;
      $("scoping-response-error").focus({ preventScroll: true });
      $("scoping-response-error").scrollIntoView({ block: "nearest" });
    }
  }
  finally {
    busy = false;
    for (const id of buttons) $(id).disabled = false;
    const item = scenarios.find((entry) => entry.projectSlug === selected);
    if (item) renderScopingResponse(item);
    renderConversation();
  }
}
function choices(catalog, key) {
  $(key).replaceChildren(...catalog[key].map((entry) => {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox"; input.value = entry.id; input.name = key;
    input.checked = entry.id === "foundry" || entry.id === "generic";
    input.disabled = entry.id === "foundry";
    if (key === "businessUnits") input.addEventListener("change", () => {
      const inputs = [...document.querySelectorAll('input[name="businessUnits"]')];
      if (input.checked) for (const other of inputs) {
        if (other !== input && (input.value === "generic" || other.value === "generic")) other.checked = false;
      }
      if (!inputs.some((other) => other.checked)) inputs.find((other) => other.value === "generic").checked = true;
    });
    label.append(input, document.createTextNode(entry.name));
    return label;
  }));
}
function selectedChoice(name) {
  return document.querySelector(`input[name="${name}"]:checked`)?.value || "";
}
function industryIcon(name) {
  const paths = {
    "Financial Services": "M3 10h18L12 3 3 10M5 10v10m5-10v10m4-10v10m5-10v10M3 21h18",
    "Healthcare / Life Sciences": "M9 3h6v6h6v6h-6v6H9v-6H3V9h6V3Z",
    "Manufacturing & Mobility": "M3 21V10l6 4V8l6 4V3h4v18H3Zm3-4h1m4 0h1m4 0h1",
    "Retail & Consumer Goods": "M3 3h2l3 12h10l3-9H6M9 19a1 1 0 1 0 0 .1m8-.1a1 1 0 1 0 0 .1",
    "Media & Communications": "M12 9v12m-4 0h8M8 5a6 6 0 0 0 0 9m8-9a6 6 0 0 1 0 9M5 2a10 10 0 0 0 0 16m14-16a10 10 0 0 1 0 16M12 6v1",
    "Energy & Resources": "m14 2-9 12h7l-2 8 9-12h-7l2-8Z",
    "Government": "M3 21h18M5 21V9h14v12M3 9h18l-9-6-9 6Zm6 4v4m6-4v4M12 3V1",
    "Education": "m2 9 10-6 10 6-10 6L2 9Zm4 3v6l6 3 6-3v-6m4-3v10",
    "Professional & Business Services": "M9 7V3h6v4M3 7h18v14H3V7Zm0 6 9 3 9-3m-9 0v5",
    "Hospitality & Travel": "m2 12 8 2-3 7 3-1 4-6 5 1 3-2-7-3 2-7-2-2-5 7-6-1-2 3Z",
    "Nonprofit": "M12 21 3 12C-2 5 6 0 12 7c6-7 14-2 9 5l-9 9Z",
  };
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("class", "industry-icon");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", paths[name] || "M3 3h7v7H3V3Zm11 0h7v7h-7V3ZM3 14h7v7H3v-7Zm11 0h7v7h-7v-7Z");
  path.setAttribute("fill", "none");
  path.setAttribute("stroke", "currentColor");
  path.setAttribute("stroke-width", "1.7");
  path.setAttribute("stroke-linejoin", "round");
  path.setAttribute("stroke-linecap", "round");
  svg.append(path);
  return svg;
}
function singleChoiceCards(id, name, entries, initial, onChange) {
  $(id).replaceChildren(...entries.map((entry) => {
    const label = document.createElement("label");
    label.className = "selection-card";
    const input = document.createElement("input");
    input.type = "radio";
    input.name = name;
    input.value = entry.id;
    input.required = true;
    input.checked = entry.id === initial;
    if (onChange) input.addEventListener("change", () => { if (input.checked) onChange(entry); });
    const title = document.createElement("span");
    title.textContent = entry.name;
    label.append(input);
    if (name === "industry") label.append(industryIcon(entry.name));
    label.append(title);
    return label;
  }));
}
function systemButtons() {
  for (const id of ["system-check", "system-identity"]) {
    $(id).disabled = systemBusy || !$("system-consent").checked;
  }
}
function setSystemStatus(text) {
  $("system-status").textContent = text;
  $("system-nav-status").textContent = text;
}
function updateSystemReadiness() {
  setSystemStatus(systemReport?.ready === false || systemIdentity?.status === "failed" ? "Needs attention"
    : !systemReport ? "Not checked"
    : systemIdentity?.status !== "ready" ? "Sign-in not checked" : "Ready");
}
function drawIdentity(value) {
  systemIdentity = value;
  $("system-identity-status").textContent = !value ? "Azure CLI / azd sign-in not checked."
    : value.status !== "ready" ? `Sign-in needs attention: ${value.reason}`
    : `Verified ${value.checkedAtUtc}: ${value.identity.scope.account}; tenant ${value.identity.scope.tenantId}; `
      + `subscription ${value.identity.scope.subscriptionId}. Azure CLI and azd match. No IDs need to be typed.`;
  updateSystemReadiness();
}
function drawSystem(value) {
  const checks = value.report?.checks || value.checks;
  systemReport = value.report;
  $("system-summary").textContent = !value.report ? "Workspace-wide toolchain has not been checked."
    : `${checks.filter((entry) => entry.ok).length}/${checks.length} checks passed. `
      + `Last checked: ${value.report.checkedAtUtc}. Shared by all scenarios; recheck after tool/environment changes.`;
  $("system-checks").replaceChildren(...checks.map((entry) => {
    const li = document.createElement("li");
    li.className = entry.ok === true ? "passed" : entry.ok === false ? "failed" : "";
    const name = document.createElement("strong");
    name.textContent = `${entry.ok === true ? "Passed" : entry.ok === false ? "Needs attention" : "Not checked"}: ${entry.name}`;
    li.append(name);
    for (const text of [entry.detail, entry.fix]) {
      if (!text) continue;
      const detail = document.createElement("small");
      detail.textContent = text;
      li.append(detail);
    }
    const stages = entry.stages || Object.entries(value.plan.stages)
      .filter(([, tools]) => tools.includes(entry.id)).map(([stage]) => stage);
    if (stages.length) {
      const affected = document.createElement("small");
      affected.textContent = `Used by: ${stages.join(", ")}`;
      li.append(affected);
    }
    return li;
  }));
  drawIdentity(value.identity);
}
async function loadSystemPlan() {
  setSystemStatus("Not checked");
  $("system-summary").textContent = "Loading the workspace-wide checklist...";
  $("system-checks").replaceChildren();
  try {
    const value = await api("/api/prerequisites/plan", {});
    drawSystem(value);
  } catch (value) {
    systemReport = null;
    setSystemStatus("Needs attention");
    $("system-summary").textContent = value.message;
    throw value;
  }
}
async function runSystemCheck(identityOnly = false) {
  if (systemBusy || !$("system-consent").checked) return;
  systemBusy = true;
  systemButtons();
  $("error").hidden = true;
  try {
    if (identityOnly) {
      $("system-identity-status").textContent = "Checking existing Azure CLI / azd sign-in...";
      drawIdentity(await api("/api/system/identity", { toolConsent: true }));
    } else {
      setSystemStatus("Checking");
      $("system-summary").textContent = "Checking tools, Python packages, PNG rendering and feed connectivity...";
      await api("/api/prerequisites/check", { toolConsent: true });
      await loadSystemPlan();
    }
  } catch (value) {
    if (identityOnly) drawIdentity({ status: "failed", reason: value.message });
    else {
      systemReport = null;
      setSystemStatus("Check failed");
      $("system-summary").textContent = value.message;
    }
    error(value);
  } finally { systemBusy = false; systemButtons(); }
}
async function loadReuseSources() {
  const sources = await api("/api/reuse-sources");
  $("reuse-source").replaceChildren(new Option("Choose a source", ""), ...sources.scenarios.map((entry) => {
    const option = new Option(`${entry.title} (${entry.id}) - ${entry.metadataStatus}`
      + (entry.available ? "" : " - unavailable"), entry.id);
    option.disabled = !entry.available;
    return option;
  }));
  $("reuse-status").textContent = sources.errors.length
    ? `Some sources could not be read: ${sources.errors.map((entry) => `${entry.id}: ${entry.error}`).join("; ")}`
    : "Select a local source, then modify its brief below. Inferred metadata still needs review.";
}
function matchInput() {
  const value = { prompt: $("prompt").value.trim(), industry: selectedChoice("industry"),
    agenticPattern: selectedChoice("agenticPattern") || "ai-decides" };
  for (const key of ["services", "businessUnits", "pillars", "domains"]) {
    value[key] = [...document.querySelectorAll(`input[name="${key}"]:checked`)].map((input) => input.value).sort();
  }
  return value;
}
function matchValid(version, fingerprint) {
  return version === matchVersion && entryMode === "new" && !reuseSource
    && fingerprint === JSON.stringify(matchInput());
}
function queueMatches(immediate = false) {
  const fingerprint = JSON.stringify(matchInput());
  // Textarea change/blur events fire while clicking a card; keep results for unchanged inputs.
  if (entryMode === "new" && !reuseSource && (completedMatchInput === fingerprint
      || (inFlightMatchInput === fingerprint && inFlightMatchVersion === matchVersion))) return;
  completedMatchInput = "";
  matchVersion++;
  clearTimeout(matchTimer);
  if (!reuseDiscoveryEnabled || entryMode !== "new") {
    $("reuse-suggestions").hidden = true;
    return;
  }
  if (reuseSource) return;
  $("reuse-suggestions").hidden = true;
  $("reuse-suggestion-cards").replaceChildren();
  const value = matchInput();
  if (value.prompt.length < 35 || value.prompt.split(/\s+/).length < 6
      || JSON.stringify(value) === dismissedMatchInput) return;
  matchTimer = setTimeout(() => { void suggestMatches(); }, immediate ? 0 : 900);
}
async function suggestMatches() {
  if (!reuseDiscoveryEnabled || entryMode !== "new" || reuseSource) return;
  const value = matchInput();
  const fingerprint = JSON.stringify(value);
  const version = ++matchVersion;
  if (value.prompt.length < 35 || value.prompt.split(/\s+/).length < 6 || fingerprint === dismissedMatchInput) return;
  inFlightMatchInput = fingerprint;
  inFlightMatchVersion = version;
  try {
    const result = await api("/api/reuse-recommendations", value);
    if (!matchValid(version, fingerprint)) return;
    completedMatchInput = fingerprint;
    $("reuse-suggestions").hidden = !result.matches.length && !result.errors.length;
    $("reuse-suggestions-status").textContent = result.errors.length
      ? `Some catalog metadata could not be read: ${result.errors.map((item) => `${item.id}: ${item.error}`).join("; ")}`
      : "Potential matches based on workflow and architecture signals. Your idea remains unchanged.";
    renderMatches($("reuse-suggestion-cards"), result.matches, () => matchValid(version, fingerprint));
  } catch (value) {
    if (!matchValid(version, fingerprint)) return;
    $("reuse-suggestions").hidden = false;
    $("reuse-suggestions-status").textContent = `Catalog comparison unavailable: ${value.message} `
      + "You can still refine or build your original idea.";
  } finally {
    if (inFlightMatchVersion === version) inFlightMatchInput = "";
  }
}
function renderMatches(host, matches, isCurrent, target = null) {
  host.replaceChildren();
  for (const match of matches) {
    const card = document.createElement("article");
    card.className = "reuse-match";
    const heading = document.createElement("h4");
    heading.textContent = match.title;
    const label = document.createElement("p");
    label.className = "muted";
    label.textContent = `${match.fit} / ${match.available ? "Local files available" : "Inspiration only"} / `
      + `${match.metadataStatus} / profile ${match.profileState}`;
    const summary = document.createElement("p");
    summary.textContent = match.summary;
    const reasons = document.createElement("p");
    reasons.textContent = `Why it surfaced: ${match.reasons.join("; ")}.`;
    const differences = document.createElement("ul");
    for (const text of match.concerns) {
      const item = document.createElement("li");
      item.textContent = text;
      differences.append(item);
    }
    const evidence = document.createElement("p");
    evidence.className = "muted";
    evidence.textContent = Object.entries(match.evidence || {}).flatMap(([feature, refs]) =>
      refs.map((ref) => `${feature}: ${ref.path}:${ref.line} (${ref.basis}, not runtime proof)`)).join("; ");
    const review = document.createElement("button");
    review.type = "button";
    review.className = "secondary";
    review.textContent = match.available ? "Review match" : "Reference files unavailable";
    review.disabled = !match.available;
    const preview = document.createElement("div");
    preview.hidden = true;
    review.addEventListener("click", () => action(async () => {
      if (!isCurrent()) throw new Error("The target idea changed. Review the current suggestions instead.");
      const source = await api(`/api/reuse-source?project=${encodeURIComponent(match.scenarioId)}`);
      if (!isCurrent()) return;
      if (source.manifestDigest !== match.manifestDigest) {
        throw new Error("Source metadata changed. Refresh the page or edit the idea to compare current starting points.");
      }
      const brief = document.createElement("article");
      brief.className = "markdown";
      renderMarkdown(brief, source.brief);
      const use = document.createElement("button");
      use.type = "button";
      use.textContent = "Use as starting point";
      use.addEventListener("click", () => action(async () => {
        if (!isCurrent()) throw new Error("The target brief changed. Compare the current catalog matches again.");
        const snapshot = { scenarioId: source.scenarioId, manifestDigest: source.manifestDigest,
          artifactsDigest: source.artifactsDigest };
        if (target) {
          await api("/api/reuse-selection", { ...target, reuseSource: snapshot });
          await refresh();
        } else {
          reuseSource = snapshot;
          acceptedMatchTitle = source.title;
          matchVersion++;
          host.replaceChildren();
          $("reuse-suggestions-status").textContent = `Starting from ${acceptedMatchTitle}. `
            + "Your project name, idea and selections are preserved. Both buttons refine before any copying or build.";
          $("create").textContent = "Refine adapted brief";
        }
      }));
      preview.replaceChildren(brief, use);
      preview.hidden = false;
    }));
    card.append(heading, label, summary, reasons, differences, evidence, review, preview);
    host.append(card);
  }
}
async function compareBriefMatches() {
  const item = scenarios.find((entry) => entry.projectSlug === selected);
  const target = { projectSlug: selected, fingerprint: item?.scoping?.fingerprint };
  const isCurrent = () => selected === target.projectSlug && scenarios.find((entry) =>
    entry.projectSlug === selected)?.scoping?.fingerprint === target.fingerprint;
  const result = await api("/api/reuse-recommendations", { ...target, fromBrief: true });
  if (!isCurrent()) return;
  $("brief-reuse-status").textContent = result.errors.length
    ? `Some catalog metadata could not be read: ${result.errors.map((entry) => entry.error).join("; ")}`
    : result.matches.length ? "Review a source before selecting. A selection requests a revised brief, not a build."
      : "No useful catalog match found. Continue with the original idea.";
  renderMatches($("brief-reuse-cards"), result.matches, isCurrent, target);
}
function chooseScenarioEntry(mode) {
  completedMatchInput = "";
  entryMode = mode;
  $("entry-new").setAttribute("aria-pressed", String(mode === "new"));
  $("entry-existing").setAttribute("aria-pressed", String(mode === "existing"));
  $("entry-existing").setAttribute("aria-expanded", String(mode === "existing"));
  $("reuse-panel").hidden = mode !== "existing";
  if (mode === "new") {
    reuseSource = null;
    acceptedMatchTitle = "";
    $("reuse-source").value = "";
    $("reuse-preview").hidden = true;
    $("reuse-clear").hidden = true;
    $("create").textContent = "Start building";
    $("reuse-status").textContent = "Source reuse cleared. The current intake is now a new idea; no files will be copied.";
  }
  queueMatches();
}
async function initialize() {
  const catalog = await api("/api/catalog");
  if (catalog.portalMode !== "visualizer") throw new Error("Restart the old portal to load visualization-only mode.");
  if (!Number.isInteger(catalog.backendEngineVersion) || catalog.backendEngineVersion < 20) {
    throw new Error("Restart the portal and refresh to enable starting from an existing scenario.");
  }
  reuseDiscoveryEnabled = catalog.backendEngineVersion >= 22;
  if (!reuseDiscoveryEnabled) {
    $("prompt-help").textContent += " Restart the portal runtime to enable automatic catalog suggestions.";
  }
  singleChoiceCards("industry", "industry", catalog.industries.map((name) => ({ id: name, name })), "");
  const patterns = catalog.agenticPatterns;
  if (!Array.isArray(patterns) || patterns.length !== 19 || !patterns.some((entry) => entry.id === "ai-decides")) {
    throw new Error("The pattern catalog is unavailable or incomplete. Restart the portal and refresh before building.");
  }
  const describePattern = (entry) => {
    $("pattern-help").textContent = entry.description;
  };
  singleChoiceCards("agentic-pattern", "agenticPattern", patterns.map((entry, index) => ({
    ...entry, name: index === 0 ? entry.name : `${String(index).padStart(2, "0")}. ${entry.name}`,
  })), "ai-decides", describePattern);
  describePattern(patterns.find((entry) => entry.id === "ai-decides"));
  for (const key of ["services", "businessUnits", "pillars", "domains"]) choices(catalog, key);
  $("prompt").addEventListener("input", () => queueMatches());
  $("prompt").addEventListener("blur", () => queueMatches(true));
  $("intake").addEventListener("change", () => queueMatches());
  $("reuse-dismiss").addEventListener("click", () => {
    if (busy) return;
    reuseSource = null;
    acceptedMatchTitle = "";
    $("create").textContent = "Start building";
    dismissedMatchInput = JSON.stringify(matchInput());
    matchVersion++;
    clearTimeout(matchTimer);
    $("reuse-suggestions").hidden = true;
  });
  $("brief-reuse-compare").addEventListener("click", () => action(compareBriefMatches));
  $("brief-reuse-clear").addEventListener("click", () => action(async () => {
    const item = scenarios.find((entry) => entry.projectSlug === selected);
    await api("/api/reuse-selection", { projectSlug: selected, fingerprint: item?.scoping?.fingerprint, reuseSource: null });
    await refresh();
  }));
  $("entry-new").addEventListener("click", () => { if (!busy) chooseScenarioEntry("new"); });
  $("entry-existing").addEventListener("click", () => { if (!busy) chooseScenarioEntry("existing"); });
  await loadReuseSources().catch((value) => {
    $("reuse-status").textContent = `Cannot load sources: ${value.message}. Reload the page to retry.`;
    error(value);
  });
  $("reuse-source").addEventListener("change", () => {
    reuseSource = null;
    $("reuse-preview").hidden = true;
    $("reuse-clear").hidden = true;
    $("create").textContent = "Start building";
    $("reuse-status").textContent = "Load this source before editing its brief.";
  });
  $("reuse-load").addEventListener("click", () => action(async () => {
    const id = $("reuse-source").value;
    if (!id) throw new Error("Choose an available source scenario.");
    const source = await api(`/api/reuse-source?project=${encodeURIComponent(id)}`);
    reuseSource = { scenarioId: source.scenarioId, manifestDigest: source.manifestDigest,
      artifactsDigest: source.artifactsDigest };
    $("slug").value = "";
    const editableBrief = source.brief.trim();
    const useRefinedBrief = editableBrief.length > 0 && editableBrief.length <= 6000;
    $("prompt").value = useRefinedBrief ? editableBrief : source.intake.prompt;
    for (const key of ["industry", "agenticPattern", "services", "businessUnits", "pillars", "domains"]) {
      const values = Array.isArray(source.intake[key]) ? source.intake[key] : [source.intake[key]];
      for (const input of document.querySelectorAll(`input[name="${key}"]`)) {
        input.checked = values.includes(input.value) || (key === "services" && input.value === "foundry");
      }
    }
    describePattern(patterns.find((entry) => entry.id === source.intake.agenticPattern));
    renderMarkdown($("reuse-brief"), source.brief);
    $("reuse-preview").hidden = false;
    $("reuse-preview").open = true;
    $("reuse-clear").hidden = false;
    $("create").textContent = "Refine adapted brief";
    $("reuse-status").textContent = `Modifying ${source.title}. Choose a NEW project name and edit the industry, `
      + "scope and prompt below. Both submit buttons review the adapted brief before any copying or build."
      + (useRefinedBrief ? "" : " The full source brief is reference-only; the editable prompt uses its saved intake.");
    $("slug").focus();
  }));
  $("reuse-clear").addEventListener("click", () => {
    if (!busy) chooseScenarioEntry("new");
  });
  $("system-consent").addEventListener("change", systemButtons);
  $("system-check").addEventListener("click", () => runSystemCheck());
  $("system-identity").addEventListener("click", () => runSystemCheck(true));
  $("intake").addEventListener("submit", (event) => {
    event.preventDefault();
    const scoping = event.submitter?.id === "refine" || reuseSource !== null;
    action(async () => {
      if (entryMode === "existing" && !reuseSource) {
        throw new Error("Choose a source scenario and select Modify brief from source before continuing.");
      }
      const value = { projectSlug: $("slug").value, industry: selectedChoice("industry"), prompt: $("prompt").value,
        agenticPattern: selectedChoice("agenticPattern"), intakeMode: scoping ? "scope" : "build" };
      if (!value.industry || !value.agenticPattern) throw new Error("Choose one industry and one workflow pattern.");
      for (const key of ["services", "businessUnits", "pillars", "domains"]) {
        value[key] = [...document.querySelectorAll(`input[name="${key}"]:checked`)].map((input) => input.value);
      }
      if (reuseSource) value.reuseSource = reuseSource;
      await api("/api/scenarios", value);
      navigate("build");
      await refresh();
      await select(value.projectSlug);
      await handoff(scoping ? "scoping" : "scenario");
    });
  });
  $("open-agent").addEventListener("click", () => action(openScenarioChat));
  $("conversation-input").addEventListener("input", () => {
    const scope = conversationScope();
    if (!scope) return;
    const previous = conversationDrafts.get(scope.key);
    const text = $("conversation-input").value;
    conversationDrafts.set(scope.key, previous?.text.trim() === text.trim() ? { ...previous, text } : { text });
    renderConversation();
  });
  $("conversation-form").addEventListener("submit", (event) => {
    event.preventDefault();
    void sendConversationMessage();
  });
  $("conversation-open").addEventListener("click", () => action(async () => {
    const scope = conversationScope();
    if (!scope) return;
    await reopenChat(scope.phase);
    await loadConversation();
  }));
  $("scoping-changes").addEventListener("input", () => {
    const item = scenarios.find((entry) => entry.projectSlug === selected);
    if (item) renderScopingResponse(item);
  });
  $("scoping-modify").addEventListener("click", () => {
    const item = scenarios.find((entry) => entry.projectSlug === selected);
    if (busy || !item?.scoping?.canRespond) return;
    const response = item.scoping.response;
    if (!$("scoping-changes").value && item.scoping.responseCurrent
        && response?.decision === "changes_requested" && response.continuation?.status !== "dispatched") {
      $("scoping-changes").value = response.changes;
    }
    $("scoping-editor").hidden = false;
    $("scoping-response-error").hidden = true;
    renderScopingResponse(item);
    $("scoping-changes").focus();
    $("scoping-changes").scrollIntoView({ block: "nearest" });
  });
  $("scoping-cancel").addEventListener("click", () => {
    if (busy) return;
    $("scoping-changes").value = "";
    $("scoping-editor").hidden = true;
    $("scoping-response-error").hidden = true;
    const item = scenarios.find((entry) => entry.projectSlug === selected);
    if (item) renderScopingResponse(item);
    $("scoping-modify").focus();
  });
  $("scoping-open-chat").addEventListener("click", () => action(async () => {
    const slug = selected;
    const value = await reopenChat("scenario");
    if (selected === slug) $("scoping-chat-status").textContent = `${value.message} `
      + "The brief controls handle continuation automatically; use this chat to review progress and decisions.";
  }, true));
  $("scoping-confirm").addEventListener("click", () => action(() => respondToScoping("confirmed"), true));
  $("scoping-request-changes").addEventListener("click", () => action(() => respondToScoping("changes_requested"), true));
  $("open-package-folder").addEventListener("click", () => action(async () => {
    if (!selected) throw new Error("Select a scenario.");
    const value = await api("/api/open-package-folder", { projectSlug: selected });
    $("package-folder-status").textContent = value.message;
  }));
  $("open-composition").addEventListener("click", () => action(() => handoff("composition")));
  $("refresh").addEventListener("click", () => refresh().catch(error));
  $("active-project").addEventListener("change", () => select($("active-project").value).catch(error));
  $("create").disabled = false;
  $("refine").disabled = false;
  await loadSystemPlan().catch(error);
  await refresh();
  setInterval(() => refresh().catch(error), 4000);
}
initializeNavigation();
initializeAppearance();
initialize().catch(error);
