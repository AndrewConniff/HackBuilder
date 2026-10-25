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
let systemBusy = false;
let systemReport = null;
let systemIdentity = null;
let projectSignature = "";
let viewVersion = 0;
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
  const key = "abcbuilder-theme";
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
  const response = await fetch(url, body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || `Request failed (${response.status}).`);
  return value;
}
function error(value) { $("error").textContent = value.message; $("error").hidden = false; }
function group(item) {
  return { running: "Building", in_progress: "Building", handed_off: "Starting",
    waiting_for_user: "Waiting for you", blocked: "Needs attention", failed: "Needs attention",
    completed: "Ready to export", approved: "Scenario approved", saved: "Ready to start" }[item.progress.status]
    || "Status unavailable";
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
  const statuses = { completed: "Completed", running: "Running", waiting_for_user: "Awaiting approval",
    blocked: "Blocked", failed: "Failed", handed_off: "Handed off", available: "Artifacts available",
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
  renderMilestones(stages.filter((stage) => !stage.id.startsWith("hack-")), "stage-history", "stage-count");
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
  $("open-agent").disabled = busy;
  $("open-composition").disabled = busy;
  const slug = selected, version = selectionVersion;
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
}
async function openScenarioChat() {
  const item = scenarios.find((entry) => entry.projectSlug === selected);
  if (!item) throw new Error("Select a scenario.");
  if (item.progress.status === "saved" && !item.chatLinks?.scenario) await handoff("scenario");
  else await reopenChat("scenario");
}
async function action(work) {
  if (busy) return;
  busy = true;
  $("error").hidden = true;
  for (const id of ["create", "open-agent", "open-composition"]) $(id).disabled = true;
  try { await work(); } catch (value) { error(value); }
  finally {
    busy = false;
    for (const id of ["create", "open-agent", "open-composition"]) $(id).disabled = false;
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
async function initialize() {
  const catalog = await api("/api/catalog");
  if (catalog.portalMode !== "visualizer") throw new Error("Restart the old portal to load visualization-only mode.");
  if (!Number.isInteger(catalog.backendEngineVersion) || catalog.backendEngineVersion < 15) {
    throw new Error("Restart the portal and refresh to enable workspace-wide System checks.");
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
  $("system-consent").addEventListener("change", systemButtons);
  $("system-check").addEventListener("click", () => runSystemCheck());
  $("system-identity").addEventListener("click", () => runSystemCheck(true));
  $("intake").addEventListener("submit", (event) => {
    event.preventDefault();
    action(async () => {
      const value = { projectSlug: $("slug").value, industry: selectedChoice("industry"), prompt: $("prompt").value,
        agenticPattern: selectedChoice("agenticPattern") };
      if (!value.industry || !value.agenticPattern) throw new Error("Choose one industry and one workflow pattern.");
      for (const key of ["services", "businessUnits", "pillars", "domains"]) {
        value[key] = [...document.querySelectorAll(`input[name="${key}"]:checked`)].map((input) => input.value);
      }
      await api("/api/scenarios", value);
      navigate("build");
      await refresh();
      await select(value.projectSlug);
      await handoff("scenario");
    });
  });
  $("open-agent").addEventListener("click", () => action(openScenarioChat));
  $("open-package-folder").addEventListener("click", () => action(async () => {
    if (!selected) throw new Error("Select a scenario.");
    const value = await api("/api/open-package-folder", { projectSlug: selected });
    $("package-folder-status").textContent = value.message;
  }));
  $("open-composition").addEventListener("click", () => action(() => handoff("composition")));
  $("refresh").addEventListener("click", () => refresh().catch(error));
  $("active-project").addEventListener("change", () => select($("active-project").value).catch(error));
  $("create").disabled = false;
  await loadSystemPlan().catch(error);
  await refresh();
  setInterval(() => refresh().catch(error), 4000);
}
initializeNavigation();
initializeAppearance();
initialize().catch(error);
