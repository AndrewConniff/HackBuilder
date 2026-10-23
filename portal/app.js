"use strict";

const $ = (id) => document.getElementById(id);
const themeKey = "abcbuilder-theme";
const systemTheme = matchMedia("(prefers-color-scheme: dark)");
let themeStorageUnavailable = false;
let themePreference = readThemePreference();

function themeStorageError(error) {
  if (!["SecurityError", "QuotaExceededError"].includes(error.name)) throw error;
  console.warn("Appearance preference could not be stored by this browser.", error);
  themeStorageUnavailable = true;
}

function readThemePreference() {
  try {
    const value = localStorage.getItem(themeKey);
    if (value === null || value === "light" || value === "dark") return value;
    console.warn("Ignoring an invalid saved appearance preference; using the system theme.");
    return null;
  } catch (error) {
    themeStorageError(error);
    return null;
  }
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const toggle = $("theme-toggle");
  if (toggle) toggle.setAttribute("aria-checked", String(theme === "dark"));
}

applyTheme(themePreference || (systemTheme.matches ? "dark" : "light"));
systemTheme.addEventListener("change", (event) => {
  if (themePreference === null) applyTheme(event.matches ? "dark" : "light");
});
addEventListener("storage", (event) => {
  if (event.key !== themeKey && event.key !== null) return;
  themePreference = readThemePreference();
  applyTheme(themePreference || (systemTheme.matches ? "dark" : "light"));
});

function initializeThemeSwitch() {
  applyTheme(document.documentElement.dataset.theme);
  const notice = $("theme-notice");
  const showStorageNotice = () => {
    notice.hidden = !themeStorageUnavailable;
    notice.textContent = themeStorageUnavailable
      ? "Appearance applies to this tab only because browser storage is unavailable."
      : "";
  };
  showStorageNotice();
  $("theme-toggle").addEventListener("click", () => {
    themePreference = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    applyTheme(themePreference);
    try {
      localStorage.setItem(themeKey, themePreference);
      themeStorageUnavailable = false;
    } catch (error) {
      themeStorageError(error);
    }
    showStorageNotice();
  });
}

const bootstrap = new URLSearchParams(location.hash.slice(1)).get("token");
if (bootstrap) {
  sessionStorage.setItem("abcbuilder-token", bootstrap);
  history.replaceState(null, "", location.pathname);
}
let catalog;
let currentRun;
let timer;
let previewText = "";
let reusableScenarios = [];
let knownRuns = [];
let knownProjects = [];
let launching = false;
let intakeReady = false;
let readinessSignature = "";
const touchedIntake = new Set();
const scenarioDrafts = new Map();
const scenarioStages = new Map();
let selectedRunId = null;
let selectedProjectSlug = null;
let selectionRevision = 0;
let detailRevision = 0;
let listRevision = 0;
let navigationRevision = 0;
let workerSignature = "";
let currentStage = "shape";
let systemTimer;
let systemStatus;
let systemWorkerSignature = "";
let serverTransition = null;
let prerequisiteSignature = "";
let prerequisiteRevision = 0;
let prerequisiteBusy = false;
let systemPrerequisiteRevision = 0;

function portalToken() {
  return sessionStorage.getItem("abcbuilder-token") || sessionStorage.getItem("hackbuilder-token") || "";
}

function scrollToWorkspace() {
  $("workspace").scrollIntoView({
    behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth",
  });
}

function showStage(stage, updateHash = true) {
  currentStage = stage;
  const shape = stage === "shape";
  const system = stage === "system";
  $("system").hidden = !system;
  $("intake").hidden = !shape;
  $("scenario-form").hidden = !shape;
  if (!shape) $("preview-panel").hidden = true;
  $("workspace").hidden = shape || system;
  $("build-details").hidden = stage !== "build";
  $("review").hidden = stage !== "hack";
  const project = selectedProjectSlug || currentRun?.request.projectSlug;
  if (["build", "hack"].includes(stage) && project) scenarioStages.set(project, stage);
  const title = {
    shape: "Shape the scenario", build: "Build & validate", hack: "Compose the hack", system: "System",
  }[stage];
  $("page-stage").textContent = title;
  $("workspace-title").textContent = title;
  for (const name of ["shape", "build", "hack", "system"]) {
    $("nav-" + name).className = `nav-item${name === stage ? " active" : ""}`;
    $("nav-" + name).setAttribute("aria-current", name === stage ? "step" : "false");
  }
  if (updateHash) history.replaceState(null, "", {
    shape: "#intake", build: "#workspace", hack: "#review", system: "#system",
  }[stage]);
  clearTimeout(systemTimer);
}

function systemControls() {
  const allowed = systemStatus?.canStopServer && $("system-confirm").checked && !serverTransition && !prerequisiteBusy;
  $("system-stop").disabled = !allowed;
  $("system-restart").disabled = !allowed;
  $("system-confirm").disabled = Boolean(serverTransition);
  $("system-refresh").disabled = Boolean(serverTransition);
  prerequisiteControls();
}

function prerequisiteControls() {
  $("intake-preflight-check").disabled = prerequisiteBusy || !$("tool-consent").checked || Boolean(serverTransition);
  $("system-preflight-check").disabled =
    prerequisiteBusy || !$("system-preflight-consent").checked || Boolean(serverTransition);
}

function renderPrerequisiteChecks(scope, checks, profile) {
  $(scope + "-preflight-results").replaceChildren(...checks.map((check) => {
    const stages = check.stages || Object.entries(profile.stages)
      .filter(([, tools]) => tools.includes(check.id)).map(([stage]) => stage);
    const item = document.createElement("li");
    item.className = "preflight-result";
    item.dataset.state = check.state || (check.ok ? "ready" : "failed-check");
    const indicator = document.createElement("span");
    indicator.className = "preflight-indicator";
    indicator.textContent = check.ok ? "\u2611" : "\u2610";
    indicator.setAttribute("aria-hidden", "true");
    const label = document.createElement("strong");
    label.textContent = `${check.state === "not-checked" ? "Not checked" : check.ok ? "Ready" : "Needs attention"}: ` +
      check.name;
    const details = document.createElement("p");
    details.textContent = (stages.length ? `Required for ${stages.join(", ")}.` : "General toolchain check.") +
      (check.installed === true ? " Executable discovered." : check.installed === false ? " Executable not found." : "") +
      (check.detail ? `\n${check.detail}` : "") + (check.fix ? `\nFix: ${check.fix}` : "");
    item.append(indicator, label, details);
    return item;
  }));
}

async function prerequisitePlan() {
  const services = selected("services");
  const signature = JSON.stringify(services);
  if (signature === prerequisiteSignature) return;
  prerequisiteSignature = signature;
  const revision = ++prerequisiteRevision;
  $("intake-preflight-status").textContent = "Service scope changed. Run a new prerequisite check.";
  $("intake-preflight-results").replaceChildren();
  $("intake-preflight-plan-status").textContent = "Resolving the selected service profile.";
  $("intake-preflight-plan").replaceChildren();
  try {
    const profile = await api(`/api/prerequisites/plan?services=${encodeURIComponent(services.join(","))}`);
    if (revision !== prerequisiteRevision) return;
    $("intake-preflight-plan-status").textContent =
      "No tool gate for requirements/design. Build approach is provisional until architecture is confirmed.";
    $("intake-preflight-plan").replaceChildren(...Object.entries(profile.stages)
      .filter(([, tools]) => tools.length).map(([stage, tools]) => {
        const item = document.createElement("li");
        item.textContent = `${stage}: ${tools.join(", ")}`;
        return item;
      }));
  } catch (error) {
    if (revision !== prerequisiteRevision) return;
    prerequisiteSignature = "";
    $("intake-preflight-plan-status").textContent = `Could not resolve prerequisites: ${error.message}`;
    throw error;
  }
}

async function prerequisiteCheck(scope) {
  if (prerequisiteBusy) throw new Error("Wait for the current prerequisite audit.");
  const consent = scope === "intake" ? $("tool-consent").checked : $("system-preflight-consent").checked;
  if (!consent) throw new Error("Authorize the local read-only commands before running prerequisite checks.");
  const selectedScope = $("system-preflight-scope").value;
  if (scope === "system" && selectedScope === "selected" && (!currentRun || currentRun.discovered))
    throw new Error("Select a saved scenario with service scope in Build & validate, or check all catalog services.");
  const body = scope === "intake" ? { services: selected("services") }
    : selectedScope === "selected" ? { runId: currentRun.id }
    : { services: catalog.services.map((item) => item.id) };
  body.buildMode = scope === "intake" ? "auto" : $("system-build-mode").value;
  body.localFunctions = scope === "system" && $("system-local-functions").checked;
  body.toolConsent = true;
  const signature = prerequisiteSignature;
  const systemRevision = systemPrerequisiteRevision;
  const selectedProject = currentRun?.request.projectSlug;
  prerequisiteBusy = true;
  systemControls();
  const status = $(scope + "-preflight-status");
  status.textContent = "Checking all planned dependencies and a temporary PNG. No installation or cloud operations.";
  $(scope + "-preflight-results").replaceChildren();
  try {
    const report = await api("/api/prerequisites/check", body);
    if ((scope === "intake" && signature !== prerequisiteSignature) ||
        (scope === "system" && (systemRevision !== systemPrerequisiteRevision ||
          (selectedScope === "selected" && selectedProject !== currentRun?.request.projectSlug)))) {
      status.textContent = "Scope changed during the audit. Run a new check; old results were not applied.";
      return;
    }
    const failures = report.checks.filter((item) => !item.ok);
    status.textContent = `${report.checks.length - failures.length} passed; ${failures.length} failed. ` +
      `Checked ${report.checkedAtUtc}. Requirements/design can proceed. ` +
      "Recheck after setup changes and in the actual worker before an affected build stage.";
    renderPrerequisiteChecks(scope, report.checks, report.plan);
  } catch (error) {
    status.textContent = `Audit failed; no readiness is claimed. ${error.message}`;
    throw error;
  } finally {
    prerequisiteBusy = false;
    systemControls();
  }
}

async function resetSystemPrerequisites() {
  const revision = ++systemPrerequisiteRevision;
  $("system-preflight-status").textContent = "Scope changed. Not checked; no readiness is assumed.";
  $("system-preflight-results").replaceChildren();
  const query = new URLSearchParams({
    buildMode: $("system-build-mode").value,
    localFunctions: String($("system-local-functions").checked),
  });
  if ($("system-preflight-scope").value === "selected") {
    if (!currentRun || currentRun.discovered) return;
    query.set("runId", currentRun.id);
  } else {
    query.set("services", catalog.services.map((item) => item.id).join(","));
  }
  const profile = await api(`/api/prerequisites/plan?${query}`);
  if (revision === systemPrerequisiteRevision)
    renderPrerequisiteChecks("system", profile.checks, profile);
}

async function refreshSystem() {
  if (serverTransition) return;
  systemStatus = await api("/api/system");
  if (serverTransition) return;
  $("system-status").textContent =
    `Server ${systemStatus.status} · PID ${systemStatus.pid} · uptime ${systemStatus.uptimeSeconds}s`;
  const details = [
    ["Workspace", systemStatus.workspace], ["State directory", systemStatus.stateDirectory],
    ["Python", systemStatus.pythonExecutable], ["Port", systemStatus.port],
    ["Started (UTC)", systemStatus.startedAtUtc], ["Workflow version", systemStatus.workflowVersion],
  ];
  $("system-details").replaceChildren(...details.flatMap(([label, value]) => {
    const term = document.createElement("dt");
    term.textContent = label;
    const description = document.createElement("dd");
    description.textContent = String(value);
    return [term, description];
  }));
  $("system-launcher").textContent = `Local launcher: ${systemStatus.launcher}`;
  $("system-worker-status").textContent = systemStatus.preflightRunning
    ? "A prerequisite audit is running. Server stop/restart is paused until it finishes."
    : systemStatus.workers.length
    ? `${systemStatus.workers.length} active worker/writer entries. Server stop/restart is blocked.`
    : "All workers are idle. Server stop/restart is available after confirmation.";
  const signature = JSON.stringify(systemStatus.workers);
  if (signature !== systemWorkerSignature) {
    systemWorkerSignature = signature;
    $("system-workers").replaceChildren(...systemStatus.workers.map((worker) => {
      const item = document.createElement("li");
      const title = document.createElement("p");
      title.textContent = `${worker.projectSlug} · ${worker.kind} · PID ${worker.pid ?? "not started"}`;
      item.append(title);
      if (!worker.canStop) {
        const warning = document.createElement("p");
        warning.textContent = "Not stoppable by this server. Inspect the original process and saved writer locally.";
        item.append(warning);
        return item;
      }
      const confirmation = document.createElement("label");
      confirmation.className = "consent";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      const label = document.createElement("span");
      label.textContent = `Confirm stopping only ${worker.projectSlug}.`;
      confirmation.append(checkbox, label);
      const stop = document.createElement("button");
      stop.type = "button";
      stop.className = "secondary";
      stop.textContent = `Stop worker: ${worker.projectSlug}`;
      stop.disabled = true;
      checkbox.addEventListener("change", () => { stop.disabled = !checkbox.checked; });
      stop.addEventListener("click", action(async () => {
        if (!checkbox.checked) throw new Error("Confirm the specific worker before stopping it.");
        stop.disabled = true;
        try {
          await api(`/api/runs/${worker.runId}/stop`, {});
        } finally {
          systemWorkerSignature = "";
          await refreshSystem();
        }
      }));
      item.append(confirmation, stop);
      return item;
    }));
  }
  systemControls();
  clearTimeout(systemTimer);
  if (currentStage === "system")
    systemTimer = setTimeout(() => refreshSystem().catch(showError), 3000);
}

async function serverAction(kind) {
  if (!systemStatus?.canStopServer || !$("system-confirm").checked || serverTransition || prerequisiteBusy)
    throw new Error("Wait until all workers are idle and confirm the server action.");
  serverTransition = kind;
  systemControls();
  clearTimeout(timer);
  clearTimeout(systemTimer);
  let result;
  try {
    result = await api(`/api/system/${kind}`, { confirmed: true });
  } catch (error) {
    serverTransition = null;
    systemControls();
    await refreshSystem();
    throw error;
  }
  $("system-status").textContent = kind === "stop"
    ? "Shutdown accepted. Use the local launcher below to start the portal again."
    : "Restarting server. Waiting for the fresh backend to become ready…";
  $("connection").textContent = kind === "stop" ? "Server stopping" : "Restarting";
  if (kind === "stop") return;
  sessionStorage.setItem("abcbuilder-token", result.restartToken);
  let failure = "Server has not answered yet.";
  for (let attempt = 0; attempt < 40; attempt++) {
    try {
      const health = await api("/api/health");
      if (health.workspace !== systemStatus.workspace)
        throw new Error("The restarted port belongs to another workspace. Use the local launcher.");
      location.reload();
      return;
    } catch (error) {
      if (!(error instanceof TypeError) && error.status !== 403 && error.status !== 503) throw error;
      failure = error.message;
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`Restart did not become ready. Use the local launcher to recover. Last check: ${failure}`);
}

function markdownInline(parent, value) {
  const pattern = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\([^)]+\))/g;
  let offset = 0;
  for (const match of value.matchAll(pattern)) {
    parent.append(value.slice(offset, match.index));
    const token = match[0];
    let element;
    if (token.startsWith("[")) {
      const link = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(token);
      element = document.createElement("span");
      element.textContent = link[1];
      try {
        const url = new URL(link[2]);
        if (["https:", "http:"].includes(url.protocol)) {
          element = document.createElement("a");
          element.href = url.href;
          element.target = "_blank";
          element.rel = "noopener noreferrer";
          element.textContent = link[1];
        }
      } catch {
        // Relative artifact links need authenticated routing; keep their labels inert.
        element.title = link[2];
      }
    } else {
      const width = token.startsWith("**") ? 2 : 1;
      element = document.createElement(token.startsWith("`") ? "code" : width === 2 ? "strong" : "em");
      element.textContent = token.slice(width, -width);
    }
    parent.append(element);
    offset = match.index + token.length;
  }
  parent.append(value.slice(offset));
}

function renderMarkdown(target, source) {
  const lines = source.replace(/\r\n?/g, "\n").split("\n");
  const blocks = [];
  let index = 0;
  if (lines[0] === "---") {
    const end = lines.indexOf("---", 1);
    if (end > 0) index = end + 1;
  }
  const cells = (line) => line.trim().replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim());
  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) { index++; continue; }
    const fence = /^\s*(`{3,}|~{3,})(.*)$/.exec(line);
    if (fence) {
      const code = [];
      index++;
      while (index < lines.length && !lines[index].trim().startsWith(fence[1])) code.push(lines[index++]);
      index++;
      const pre = document.createElement("pre");
      const content = document.createElement("code");
      content.textContent = code.join("\n");
      pre.append(content);
      blocks.push(pre);
      continue;
    }
    if (/^\s*\|?[\s:|-]+\|[\s:|-]*$/.test(lines[index + 1] || "") && line.includes("|")) {
      const table = document.createElement("table");
      const row = (text, header) => {
        const tr = document.createElement("tr");
        for (const value of cells(text)) {
          const cell = document.createElement(header ? "th" : "td");
          markdownInline(cell, value);
          tr.append(cell);
        }
        return tr;
      };
      const head = document.createElement("thead");
      head.append(row(line, true));
      table.append(head);
      const body = document.createElement("tbody");
      index += 2;
      while (index < lines.length && lines[index].includes("|") && lines[index].trim())
        body.append(row(lines[index++], false));
      table.append(body);
      blocks.push(table);
      continue;
    }
    const heading = /^(#{1,6})\s+(.+)$/.exec(line);
    if (heading) {
      const element = document.createElement(`h${heading[1].length}`);
      markdownInline(element, heading[2]);
      blocks.push(element);
      index++;
      continue;
    }
    if (/^\s*([-*_])(?:\s*\1){2,}\s*$/.test(line)) {
      blocks.push(document.createElement("hr")); index++; continue;
    }
    const list = /^\s*(?:([-+*])|(\d+)[.)])\s+/.exec(line);
    if (list) {
      const element = document.createElement(list[2] ? "ol" : "ul");
      if (list[2]) element.start = Number(list[2]);
      const pattern = list[2] ? /^\s*\d+[.)]\s+/ : /^\s*[-+*]\s+/;
      while (index < lines.length && pattern.test(lines[index])) {
        const item = document.createElement("li");
        markdownInline(item, lines[index++].replace(pattern, ""));
        element.append(item);
      }
      blocks.push(element);
      continue;
    }
    const quote = /^>\s?(.*)$/.exec(line);
    const element = document.createElement(quote ? "blockquote" : "p");
    markdownInline(element, quote ? quote[1] : line);
    blocks.push(element);
    index++;
  }
  target.replaceChildren(...blocks);
}

async function openArtifact(entry) {
  if (!currentRun) return;
  const url = `/api/runs/${currentRun.id}/artifact?path=${encodeURIComponent(entry.path)}`;
  if (entry.download) {
    const response = await fetch(url, {
      headers: { Authorization: `Bearer ${portalToken()}` },
    });
    if (!response.ok) throw new Error((await response.json()).error || "Download failed.");
    const link = document.createElement("a");
    const objectUrl = URL.createObjectURL(await response.blob());
    link.href = objectUrl;
    link.download = entry.path.split("/").at(-1);
    link.click();
    URL.revokeObjectURL(objectUrl);
    return;
  }
  const value = await api(url);
  if (entry.group === "Reference scenario documents") {
    renderMarkdown($("reference-content"), value.text);
    $("reference-content").hidden = false;
    return;
  }
  $("artifact-title").textContent = `${entry.private ? "PRIVATE · " : ""}${value.path}`;
  renderMarkdown($("artifact-content"), value.text);
  $("artifact-preview").hidden = false;
}
const stageLabels = {
  requirements: "Requirements",
  architecture: "Architecture validation",
  diagrams: "Architecture diagrams",
  bicep: "Bicep creation",
  application: "Application implementation",
  "local-validation": "Local validation",
  deployment: "Deployment",
  "live-validation": "Live scenario validation",
  review: "Scenario suitability review",
  "hack-plan": "Hack package planning",
  "hack-content": "Challenges and learner guide",
  "hack-starter": "Participant starter",
  "hack-coach": "Private coach package",
  "hack-validation": "Hack package validation",
};

function pendingDecision() {
  return currentRun?.project?.decisions.find((item) => item.status === "pending");
}

function showError(error) {
  $("error").textContent = error.message || String(error);
  $("error").hidden = false;
}

async function api(path, body) {
  const response = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      Authorization: `Bearer ${portalToken()}`,
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const value = await response.json();
  if (!response.ok)
    throw Object.assign(new Error(value.error || `Request failed (${response.status}).`), {
      code: value.code, project: value.project, status: response.status,
    });
  return value;
}

function selected(name) {
  return Array.from(
    document.querySelectorAll(`input[name="${name}"]:checked`),
    (input) => input.value,
  );
}

function request() {
  return {
    prompt: $("prompt").value,
    projectSlug: $("project").value,
    industry: selected("industry")[0] || "",
    businessUnits: selected("businessUnits"),
    ...($("reuse-scenario").value ? {
      reuseScenarioId: $("reuse-scenario").value,
      reuseManifestDigest: reusableScenarios.find((item) => item.id === $("reuse-scenario").value)?.manifestDigest,
    } : {}),
    services: selected("services"),
    pillars: selected("pillars"),
    domains: selected("domains"),
    toolConsent: $("tool-consent").checked,
  };
}

function choice(item, name, type = "checkbox") {
  const label = document.createElement("label");
  label.className = "choice";
  const input = document.createElement("input");
  input.type = type;
  input.name = name;
  input.value = item.id;
  if (item.required) {
    input.checked = true;
    input.disabled = true;
  }
  if (type === "radio") input.required = true;
  if (name === "industry" || name === "businessUnits")
    input.setAttribute("aria-describedby", `${name}-help ${name}-error`);
  const text = document.createElement("span");
  const title = document.createElement("strong");
  title.textContent = item.name;
  text.append(title);
  if (item.description && name === "services") {
    const description = document.createElement("small");
    description.textContent = item.description;
    text.append(description);
  }
  label.append(input, text);
  return label;
}

function existingProject(slug) {
  const project = knownProjects.find((item) => item.projectSlug === slug);
  const run = knownRuns.find((item) => item.request.projectSlug === slug);
  const source = reusableScenarios.find((item) => item.id === slug);
  return project || run || source ? {
    projectSlug: slug,
    runId: project?.runId || run?.id,
    status: project?.status || run?.status || "local files only",
    discovered: !project && (!run || run.discovered),
  } : null;
}

function nextProjectName(slug) {
  let number = 2;
  let candidate;
  do {
    const suffix = `-${number++}`;
    candidate = slug.slice(0, 40 - suffix.length).replace(/-+$/, "") + suffix;
  } while (existingProject(candidate));
  return candidate;
}

function renderProjectConflict(slug) {
  const project = existingProject(slug);
  $("project-conflict").hidden = !project;
  if (!project) return;
  $("project-conflict-message").textContent =
    `“${slug}” already exists (${project.status.replaceAll("_", " ")}). ` +
    (project.discovered
      ? "Its local files can be previewed, but cannot be continued as a portal job. "
      : project.runId
      ? "Open it in Build & validate to review progress, continue, or request a revision. "
      : "A saved project record exists without a portal run to open; the saved state has been preserved. ") +
    "To build a separate scenario, use a new name. Reuse a scenario selects a source architecture, not a project to continue.";
  $("open-existing").hidden = !project.runId;
  $("open-existing").textContent = project.discovered ? "Preview existing files" : "Open existing project";
  $("new-project-name").textContent = `Use new name: ${nextProjectName(slug)}`;
}

async function refreshProjects() {
  knownProjects = await api("/api/projects");
  summarize();
}

function activeRuns() {
  return knownRuns.filter((run) => run.status === "running");
}

function hasWorkerCapacity() {
  return activeRuns().length < catalog.maxConcurrentWorkers;
}

function selectRun(id, slug) {
  selectedRunId = id;
  selectedProjectSlug = slug || knownRuns.find((run) => run.id === id)?.request.projectSlug ||
    knownProjects.find((project) => project.runId === id)?.projectSlug || null;
  selectionRevision++;
  if (currentRun?.id !== id) {
    for (const name of ["continue", "revise", "answer-decision", "compose", "stop",
      "retry-setup", "revoke-consent"]) $(name).disabled = true;
    $("project-summary").textContent = "Loading the selected scenario. Actions are paused until its status arrives.";
  }
}

function renderWorkerCapacity() {
  const running = activeRuns();
  const message =
    `${running.length} of ${catalog.maxConcurrentWorkers} workers active. ` +
    (hasWorkerCapacity() ? "Other scenarios can run independently. " : "All workers are busy; new work must wait. ") +
    "Switching scenarios never stops a job. Stop job affects only the selected run.";
  if ($("worker-capacity").textContent !== message) $("worker-capacity").textContent = message;
  const signature = JSON.stringify(running.map((run) => [run.id, run.kind, run.request.projectSlug]));
  if (signature === workerSignature) return;
  workerSignature = signature;
  $("worker-list").replaceChildren(...running.map((run) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "validation-link";
    button.textContent = `${run.request.projectSlug} · ${run.kind} running`;
    button.addEventListener("click", action(async () => {
      const navigation = ++navigationRevision;
      await refreshRuns(run.id, run.request.projectSlug);
      if (navigation === navigationRevision && selectedProjectSlug === run.request.projectSlug)
        showStage(scenarioStages.get(run.request.projectSlug) || "build");
    }));
    item.append(button);
    return item;
  }));
}

function intakeIssues(data, execution = true) {
  const issues = [];
  const add = (field, message) => issues.push({ field, message });
  if (!data.projectSlug) {
    add("project", "Enter a project name.");
  } else if (data.projectSlug.length > 40) {
    add("project", "Keep the project name to 40 characters or fewer.");
  } else if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(data.projectSlug)) {
    add("project", "Use lowercase letters, numbers and single hyphens in the project name; no spaces.");
  } else if (existingProject(data.projectSlug)) {
    add("project", "That project already exists. Choose a new name or continue it in Build & validate.");
  }
  if (!catalog.industries.some((item) => item.id === data.industry))
    add("industry", "Choose one industry.");
  if (!data.businessUnits.length) {
    add("businessUnits", "Select at least one business unit, or choose Generic.");
  } else if (data.businessUnits.includes("generic") && data.businessUnits.length > 1) {
    add("businessUnits", "Choose Generic on its own, or select specific business units.");
  }
  if (data.prompt.length > 6000) add("prompt", "Keep the scenario prompt to 6,000 characters or fewer.");
  if (!data.prompt.trim() && !data.services.length)
    add("prompt", "Describe a business problem or select at least one Azure service.");
  if (data.reuseScenarioId && !reusableScenarios.some(
    (item) => item.id === data.reuseScenarioId && item.available,
  )) add("reuse-scenario", "The selected architecture source is unavailable. Refresh the catalog and select it again.");
  if (execution) {
    if (!data.toolConsent) add("consent", "Check the local tool execution consent box below.");
    if (!catalog.cliAvailable)
      add("cli", "Copilot CLI was not detected. Install it, run copilot login, then restart the portal.");
    if (!hasWorkerCapacity())
      add("capacity", `All ${catalog.maxConcurrentWorkers} workers are busy. You can still switch scenarios and review progress.`);
    if (launching) add("starting", "Starting your scenario. Please wait.");
    if (!intakeReady) add("loading", "Wait for the scenario catalog and job status to finish loading.");
  }
  return issues;
}

function focusIntakeIssue(issue) {
  if (issue.field === "capacity") {
    showStage("build");
    $("run-select").focus();
    return;
  }
  touchedIntake.add(issue.field);
  summarize();
  const target = issue.field === "consent" ? $("tool-consent")
    : ["industry", "businessUnits"].includes(issue.field)
    ? document.querySelector(`input[name="${issue.field}"]`) : $(issue.field);
  target.focus();
  target.scrollIntoView({
    block: "center",
    behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth",
  });
}

function renderIntakeValidation(data) {
  const issues = intakeIssues(data);
  const status = issues.length
    ? `${issues.length} ${issues.length === 1 ? "item" : "items"} to resolve before building.`
    : "Ready to build. Your scenario brief is complete.";
  if ($("launch-status").textContent !== status) $("launch-status").textContent = status;
  $("launch-status").dataset.ready = String(issues.length === 0);
  const signature = JSON.stringify(issues);
  if (signature !== readinessSignature) {
    readinessSignature = signature;
    $("launch-blockers").replaceChildren(...issues.map((issue) => {
      const item = document.createElement("li");
      if (["project", "industry", "businessUnits", "prompt", "reuse-scenario", "consent", "capacity"]
        .includes(issue.field)) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "validation-link";
        button.textContent = issue.message;
        button.addEventListener("click", () => focusIntakeIssue(issue));
        item.append(button);
      } else {
        item.textContent = issue.message;
      }
      return item;
    }));
  }
  for (const field of ["project", "industry", "businessUnits", "prompt", "consent"]) {
    const error = issues.find((issue) => issue.field === field);
    const show = Boolean(error && touchedIntake.has(field));
    $(`${field}-error`).textContent = show ? error.message : "";
    $(`${field}-error`).hidden = !show;
    const controls = ["industry", "businessUnits"].includes(field)
      ? [$(`${field}-field`), ...document.querySelectorAll(`input[name="${field}"]`)]
      : [$(field === "consent" ? "tool-consent" : field)];
    for (const control of controls) control.setAttribute("aria-invalid", String(show));
  }
  $("launch").disabled = issues.length > 0;
  $("launch").title = issues.map((issue) => issue.message).join("\n");
  return issues;
}

function validatedIntake(execution = false) {
  const data = request();
  const issues = intakeIssues(data, execution);
  for (const issue of issues) touchedIntake.add(issue.field);
  renderIntakeValidation(data);
  if (issues.length) {
    const focusable = issues.find((issue) =>
      ["project", "industry", "businessUnits", "prompt", "reuse-scenario", "consent", "capacity"].includes(issue.field),
    );
    if (focusable) focusIntakeIssue(focusable);
    throw new Error(`Review your scenario brief: ${issues[0].message}`);
  }
  return data;
}

function summarize() {
  prerequisiteControls();
  prerequisitePlan().catch(showError);
  const data = request();
  renderProjectConflict(data.projectSlug);
  $("summary-project").textContent = data.projectSlug || "Enter a project name";
  $("summary-industry").textContent = data.industry || "Choose one industry";
  $("summary-business-units").textContent = catalog.businessUnits
    .filter((item) => data.businessUnits.includes(item.id)).map((item) => item.name).join(", ") || "Select a unit";
  $("summary-source").textContent = data.reuseScenarioId || "New scenario";
  $("summary-services").textContent = catalog.services
    .filter((item) => data.services.includes(item.id))
    .map((item) => item.name)
    .join(", ");
  const domainPillars = catalog.domains
    .filter((item) => data.domains.includes(item.id))
    .map((item) => item.pillar);
  $("summary-priorities").textContent =
    catalog.pillars
      .filter(
        (item) =>
          data.pillars.includes(item.id) || domainPillars.includes(item.id),
      )
      .map((item) => item.name)
      .join(", ") || "No preference yet";
  renderIntakeValidation(data);
  renderWorkerCapacity();
  $("compose").disabled =
    !$("tested").checked ||
    !$("approval").value.trim() ||
    !localExecutionAllowed() ||
    Boolean(currentRun?.project?.setupBlocker) ||
    !currentRun?.review?.ready ||
    selectedRunId !== currentRun?.id ||
    Boolean(currentRun?.project?.writer) ||
    !hasWorkerCapacity() ||
    currentRun.status === "running" ||
    Boolean(currentRun.discovered);
}

function localExecutionAllowed() {
  return currentRun?.project?.localToolConsent?.scope === "scenario-local-execution" ||
    $("workspace-consent").checked;
}

function renderWorkerActivity(run) {
  const activity = run.activity;
  const running = run.status === "running";
  const lastOutput = Date.parse(activity?.lastOutputAtUtc || "");
  const start = Date.parse(run.startedAtUtc || "");
  const end = running ? Date.now() : Date.parse(run.finishedAtUtc || "");
  const seconds = Number.isFinite(lastOutput) ? Math.max(0, Math.floor((Date.now() - lastOutput) / 1000)) : null;
  const age = seconds === null ? "No output received yet" :
    `Last output ${seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m`} ago`;
  const elapsed = Number.isFinite(start) && Number.isFinite(end) ?
    ` · Attempt elapsed ${Math.max(0, Math.floor((end - start) / 60000))}m` : "";
  const process = running ? (activity?.processAlive ? "Process running" : "Process status not confirmed") :
    `Attempt ${run.status}`;
  $("worker-activity").hidden = Boolean(run.discovered);
  $("worker-activity-badge").textContent = `· ${running && seconds !== null && seconds >= 180 ? "Quiet" : process}`;
  $("worker-activity-status").textContent = `${process} · ${age}${elapsed}` +
    (running && seconds !== null && seconds >= 180 ? ". No recent output; this alone does not mean it is stuck." : "");
  const actions = activity?.recentActions || [];
  $("worker-latest-action").textContent = actions.length ?
    `Latest observed action: ${actions.at(-1)}` : "No tool-action headings received yet.";
  $("worker-recent-actions").replaceChildren(...actions.slice().reverse().map(label => {
    const item = document.createElement("li");
    item.textContent = label;
    return item;
  }));
}

function renderRun(run) {
  const switched = currentRun?.request.projectSlug !== run.request.projectSlug;
  if (switched && currentRun) {
    scenarioDrafts.set(currentRun.request.projectSlug, {
      decision: $("decision").value, choice: $("decision-choice").value, decisionId: pendingDecision()?.id,
      approval: $("approval").value, tested: $("tested").checked,
      fingerprint: currentRun.review?.fingerprint, runId: currentRun.id,
    });
  }
  const draft = switched ? scenarioDrafts.get(run.request.projectSlug) : null;
  const previousDecisionId = switched ? draft?.decisionId : pendingDecision()?.id;
  if (switched) {
    $("decision").value = draft?.decision || "";
    $("decision-choice").value = draft?.choice || "";
  }
  const changed =
    currentRun?.id !== run.id ||
    currentRun?.review?.fingerprint !== run.review?.fingerprint;
  currentRun = run;
  if (switched && $("system-preflight-scope").value === "selected") resetSystemPrerequisites().catch(showError);
  if (switched) $("workspace-consent").checked = false;
  if (changed) {
    const sameReview = draft?.runId === run.id && draft?.fingerprint === run.review?.fingerprint;
    $("tested").checked = Boolean(sameReview && draft.tested);
    $("approval").value = sameReview ? draft.approval : "";
  }
  $("run-empty").hidden = true;
  $("run-details").hidden = false;
  $("run-name").textContent = `${run.request.projectSlug} / ${run.kind}`;
  const project = run.project;
  const authorized = project?.localToolConsent?.scope === "scenario-local-execution";
  const setup = project?.setupBlocker;
  $("workspace-consent-label").hidden = authorized || !project || Boolean(run.discovered);
  $("workspace-consent").disabled = Boolean(project?.writer);
  $("local-consent-status").textContent = authorized
    ? "Local execution is authorized for this scenario across steps and resumptions. Azure and publishing are excluded."
    : project && !run.discovered
      ? "Authorize local execution once for this scenario. Older projects require one explicit confirmation."
      : "Select a saved scenario to view its local execution authorization.";
  $("revoke-consent").hidden = !authorized;
  $("revoke-consent").disabled = Boolean(project?.writer) || run.status === "running";
  $("setup-panel").hidden = !setup;
  if (setup) {
    $("setup-action").textContent = setup.action;
    $("setup-verification").textContent = `Required worker check: ${setup.verification}`;
  }
  const historical = run.review?.evidenceType === "historical-user-attestation";
  const packaged = run.composition?.status === "packages_validated";
  const approved = run.review?.approval?.decision === "approved";
  if (changed) {
    $("artifact-preview").hidden = true;
    $("reference-content").hidden = true;
  }
  $("run-status").textContent = setup ? "Setup required" : run.discovered && !packaged
    ? "Local project · read-only preview"
    : packaged
    ? "Packages validated · event not deployed"
    : run.review?.ready && approved
    ? "Scenario approved"
    : run.review?.ready
    ? "Review ready"
    : (project?.status || "Legacy execution").replaceAll("_", " ");
  $("execution-status").textContent = `Execution: ${run.status}${run.error ? ` · ${run.error}` : ""}`;
  $("project-summary").textContent =
    setup
      ? "A technical prerequisite or host permission is unresolved. Verify setup rather than approving again."
    : run.discovered
      ? `Discovered on disk. Read-only preview; missing workflow details are not inferred. Available: ${(run.localInventory || []).join(", ") || "No recognized artifacts yet"}.`
      : packaged
      ? "Challenges, learner guide, participant starter and private coach package are validated. Event not deployed."
      : run.composition?.status === "stale"
      ? `Package evidence needs attention: ${run.composition.reason}`
      : run.orphaned
      ? "The owning server stopped. Inspect its worker locally, then use Stop job to recover after it exits; the writer lease is retained."
      : run.review?.ready
      ? historical
        ? "Historical deployment is user-attested; resources were deleted. No independent runtime results are claimed."
        : "Live validation is current. Test the scenario before suitability approval."
      : project?.status === "local_ready"
        ? "Local validation complete. Azure deployment is not yet proven; review the next authorization step below."
        : project?.status === "needs_attention"
          ? "The worker finished without a complete stage result. Inspect diagnostics or resume; no success was inferred."
          : project
            ? "Follow scenario progress here. Refresh reads status only; decisions and approvals remain separate."
            : "This older run has no structured progress. Resume to reconcile existing artifacts; no stages are inferred.";
  const stageItems = Object.entries(stageLabels).map(([key, label]) => {
      let stage = project?.stages[key];
      if (key.startsWith("hack-") && packaged) {
        stage = { status: "completed", summary: "Validated package receipt matches the approved reference and package contents." };
      } else if (key.startsWith("hack-") && run.composition?.status === "stale") {
        stage = { status: "failed", summary: "Package validation receipt is stale; revalidation required." };
      } else if (key === "review" && approved) {
        stage = { status: "completed", summary: "Explicit suitability approval recorded against this reference." };
      } else if (key === "local-validation" && run.localValidation?.status === "recorded_passed") {
        stage = { status: "recorded_passed", summary: run.localValidation.summary };
      } else if (approved && ["requirements", "architecture", "diagrams", "bicep", "application"].includes(key)
          && (!stage || stage.status === "pending")) {
        stage = { status: "reviewed", summary: "Included in the approved reference snapshot; original stage telemetry is unavailable." };
      } else if (historical && ["deployment", "live-validation"].includes(key)) {
        stage = { status: "user_attested", summary: "Historical deployment reported successful by the user; environment deleted, granular logs unavailable." };
      }
      const item = document.createElement("li");
      item.dataset.status = stage?.status || "pending";
      const name = document.createElement("strong");
      name.textContent = label;
      const status = document.createElement("span");
      status.textContent = run.review?.ready && !approved && key === "review"
        ? "Ready for your review"
        : stage?.status === "blocked" ? "Setup required"
        : (stage?.status || "pending") === "pending" && key === "deployment" &&
            !project?.authorizations.some((entry) => entry.kind === "deployment")
          ? "Not authorized"
          : (stage?.status || "pending").replaceAll("_", " ");
      item.append(name, status);
      if (stage?.summary) {
        const summary = document.createElement("p");
        summary.textContent = stage.summary;
        item.append(summary);
      }
      return item;
    });
  $("stage-list").replaceChildren(...stageItems.slice(0, 9));
  $("hack-stage-list").replaceChildren(...stageItems.slice(9));
  $("hack-summary").textContent = packaged
    ? "Packages validated. Explore the learner challenges, minimum starter and private coach materials below. Event not deployed."
    : approved ? "Scenario approved. Composition creates learner content, starter and private coach packages."
      : "Confirm scenario suitability below to unlock hack composition.";
  const packageArtifacts = (run.artifacts || []).filter((entry) => entry.group !== "Reference scenario documents");
  $("reference-list").replaceChildren(...(run.artifacts || [])
    .filter((entry) => entry.group === "Reference scenario documents").map((entry) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary artifact-button";
      button.textContent = entry.path;
      button.addEventListener("click", action(() => openArtifact(entry)));
      return button;
    }));
  $("hack-artifacts").hidden = !packageArtifacts.length;
  const artifactGroups = [
    { id: "learner", title: "Learner materials", icon: "\uD83D\uDCDA",
      description: "Challenges, resources and the participant starter.",
      includes: (entry) => !entry.download && !entry.private },
    { id: "coach", title: "Private coach material", icon: "\uD83D\uDD12",
      description: "Solutions, Finale and deployment guidance. Coach access only.",
      includes: (entry) => !entry.download && entry.private },
    { id: "release", title: "Release downloads", icon: "\uD83D\uDCE6",
      description: "Packaged ZIPs. Only learner and participant archives are public.",
      includes: (entry) => entry.download },
  ];
  $("artifact-list").replaceChildren(...artifactGroups.map((group) => {
    const entries = packageArtifacts.filter(group.includes);
    const section = document.createElement("section");
    section.className = `artifact-group artifact-group-${group.id}`;
    section.dataset.group = group.id;
    const heading = document.createElement("h4");
    const icon = document.createElement("span");
    icon.className = "artifact-group-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = group.icon;
    const title = document.createElement("span");
    title.textContent = `${group.title} (${entries.length})`;
    heading.append(icon, title);
    const description = document.createElement("p");
    description.className = "subtle";
    description.textContent = group.description;
    const list = document.createElement("div");
    list.className = "artifact-group-items";
    for (const entry of entries) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `secondary artifact-button${entry.private ? " artifact-private" : ""}`;
      button.textContent = `${entry.private ? "PRIVATE · " : ""}${entry.group} · ${entry.path.split("/").at(-1)}${entry.download ? " · Download" : " · Read"}`;
      button.addEventListener("click", action(() => openArtifact(entry)));
      list.append(button);
    }
    if (!entries.length) {
      const empty = document.createElement("p");
      empty.className = "subtle";
      empty.textContent = "Available after package creation.";
      list.append(empty);
    }
    section.append(heading, description, list);
    return section;
  }));
  renderWorkerActivity(run);
  $("run-output").textContent =
    run.output || run.error || "Starting the local Copilot CLI…";
  $("stop").hidden = run.status !== "running";
  $("stop").disabled = false;
  const decision = pendingDecision();
  const idle = !run.discovered && !project?.writer && run.status !== "running" && hasWorkerCapacity() &&
    localExecutionAllowed();
  const canAct = idle && run.kind !== "composition" && !setup;
  $("retry-setup").disabled = !idle || Boolean(decision);
  $("instructions-panel").hidden = Boolean(setup);
  $("decision-panel").hidden = !decision || packaged;
  $("decision-actions").hidden = !decision || packaged;
  $("answer-decision").disabled = !canAct;
  $("continue").disabled = !canAct || Boolean(decision);
  $("revise").disabled = !canAct;
  if (decision) {
    const selectedChoice = $("decision-choice").value;
    $("decision-question").textContent = decision.question;
    $("decision-reason").textContent = decision.reason;
    $("decision-choice").replaceChildren(
      new Option("Select a response", ""),
      ...decision.choices.map((value) => new Option(value, value)),
    );
    if (decision.id === previousDecisionId && decision.choices.includes(selectedChoice))
      $("decision-choice").value = selectedChoice;
    $("decision-scope").hidden = !decision.scope;
    $("decision-scope").textContent = decision.scope ? JSON.stringify(decision.scope, null, 2) : "";
  }
  $("review-status").textContent = approved ? "APPROVED" : run.review?.ready
    ? "REVIEW READY"
    : "LOCKED";
  $("review-reason").textContent = run.review?.ready
    ? historical
      ? "The reviewed reference has an explicit historical user attestation. The endpoint and test logs are unavailable; this is not independently verified live acceptance."
      : "Live acceptance evidence and the reference fingerprint are current. Open the app and test it yourself."
    : run.review?.reason ||
      "Acceptance evidence will be checked after the job finishes.";
  $("review-evidence").hidden = !run.review?.ready || approved;
  if (run.review?.ready) {
    $("app-link").hidden = historical;
    $("app-link").href = historical ? "" : run.review.applicationUrl;
    $("tested-label").textContent = historical
      ? "I confirm my historical deployment attestation and approve this reference as suitable for the hack."
      : "I tested the live scenario and confirm it is workable and usable for this hack.";
    $("check-list").replaceChildren(
      ...(historical ? ["User-attested historical deployment; granular checks unavailable"]
        : Object.keys(run.review.checks)).map((name) => {
        const item = document.createElement("li");
        item.textContent = historical ? name : `✓ ${name}`;
        return item;
      }),
    );
  }
  summarize();
  if (switched && !$("workspace").hidden && scenarioStages.has(run.request.projectSlug))
    showStage(scenarioStages.get(run.request.projectSlug));
  clearTimeout(timer);
  timer = setTimeout(() => refreshRuns().catch(showError), 3000);
}

async function loadRun(id) {
  const selection = selectionRevision;
  const detail = ++detailRevision;
  let run;
  try {
    run = await api(`/api/runs/${id}`);
  } catch (error) {
    if (selection !== selectionRevision || detail !== detailRevision || selectedRunId !== id) {
      console.warn("Ignoring a failed status request for a scenario no longer selected.", id, error);
      return;
    }
    throw error;
  }
  if (selection === selectionRevision && detail === detailRevision && selectedRunId === id)
    renderRun(run);
}

async function refreshRuns(selectId, selectSlug) {
  if (serverTransition) return;
  if (selectId) selectRun(selectId, selectSlug);
  const revision = ++listRevision;
  const runs = await api("/api/runs");
  if (revision !== listRevision) return;
  const selection = selectionRevision;
  if (selectedRunId && !runs.some((run) => run.request.projectSlug === selectedProjectSlug)) {
    const missing = await api(`/api/runs/${selectedRunId}`);
    if (revision !== listRevision || selection !== selectionRevision) return;
    runs.unshift(missing);
  }
  knownRuns = runs;
  const seen = new Set();
  const scenarios = runs.filter((run) => {
    const slug = run.request.projectSlug;
    if (seen.has(slug)) return false;
    seen.add(slug);
    return true;
  });
  $("run-select").replaceChildren(new Option("Select a scenario", ""));
  for (const run of scenarios) {
    $("run-select").add(
      new Option(
        `${run.request.projectSlug}${run.discovered ? " · local project" : ""}`,
        run.id,
      ),
    );
  }
  const selected = scenarios.find((run) => run.request.projectSlug === selectedProjectSlug) || scenarios[0];
  const id = selected?.id;
  if (id) {
    selectedRunId = id;
    selectedProjectSlug = selected.request.projectSlug;
    $("run-select").value = id;
    await loadRun(id);
  } else {
    summarize();
  }
}

async function preview() {
  const value = await api("/api/preview", validatedIntake());
  previewText = value.prompt;
  $("preview-output").textContent = value.prompt;
  $("preview-panel").hidden = false;
  return value;
}

function action(handler) {
  return async (event) => {
    event?.preventDefault();
    $("error").hidden = true;
    try {
      await handler(event);
    } catch (error) {
      showError(error);
    }
  };
}

async function followup(kind) {
  if (!currentRun) throw new Error("Select a scenario run first.");
  if (selectedRunId !== currentRun.id)
    throw new Error("Wait for the selected scenario to finish loading before acting on it.");
  const origin = currentRun;
  const navigation = navigationRevision;
  const sentText = $("decision").value;
  const body = {
    message: $("decision").value,
    toolConsent: $("workspace-consent").checked,
    revision: currentRun.project?.revision,
  };
  const decision = pendingDecision();
  if (kind === "continue" && decision) {
    const choice = $("decision-choice").value;
    if (!choice) throw new Error("Select a decision response.");
    Object.assign(body, {
      decisionId: decision.id,
      choice,
      message: body.message.trim() || choice,
    });
  } else if (kind === "continue" && !body.message.trim()) {
    body.message = "Resume the next incomplete step using persisted decisions and evidence.";
  }
  if (kind === "compose") {
    Object.assign(body, {
      message: $("approval").value,
      functionalityTested: $("tested").checked,
      fingerprint: currentRun.review?.fingerprint,
    });
  }
  let run;
  try {
    run = await api(`/api/runs/${origin.id}/${kind}`, body);
  } catch (error) {
    error.message = `${origin.request.projectSlug}: ${error.message}`;
    throw error;
  }
  const consumesInstruction = ["continue", "revise", "compose"].includes(kind);
  const draft = scenarioDrafts.get(origin.request.projectSlug);
  if (consumesInstruction && draft?.decision === sentText) draft.decision = "";
  await refreshRuns(
    navigation === navigationRevision ? run.id : undefined, origin.request.projectSlug,
  );
  if (navigation === navigationRevision && currentRun?.request.projectSlug === origin.request.projectSlug) {
    if (consumesInstruction && $("decision").value === sentText) $("decision").value = "";
    if (!["stop", "revoke-consent"].includes(kind)) showStage(kind === "compose" ? "hack" : "build");
    scrollToWorkspace();
  }
}

async function initialize() {
  catalog = await api("/api/catalog");
  if (catalog.workflowVersion !== 5 || catalog.maxConcurrentWorkers !== 4 ||
      catalog.systemControlsVersion !== 1 || catalog.prerequisitesVersion !== 1)
    throw new Error("Restart the local portal server to load the workflow dashboard, then reload this page.");
  for (const item of catalog.industries)
    $("industries").append(choice(item, "industry", "radio"));
  for (const name of ["businessUnits", "services", "pillars", "domains"]) {
    for (const item of catalog[name]) $(name).append(choice(item, name));
  }
  document.querySelector('input[name="businessUnits"][value="generic"]').checked = true;
  $("businessUnits").addEventListener("change", (event) => {
    const changed = event.target;
    if (changed.name !== "businessUnits" || !changed.checked) return;
    for (const input of document.querySelectorAll('input[name="businessUnits"]')) {
      if (changed.value === "generic" ? input !== changed : input.value === "generic") input.checked = false;
    }
    summarize();
  });
  $("refresh-catalog").addEventListener("click", action(refreshCatalog));
  $("open-existing").addEventListener("click", action(async () => {
    const project = existingProject($("project").value);
    if (!project?.runId) throw new Error("No portal run is available for this project. Choose a new name.");
    const navigation = ++navigationRevision;
    await refreshRuns(project.runId, project.projectSlug);
    if (navigation === navigationRevision && selectedProjectSlug === project.projectSlug) {
      showStage("build");
      scrollToWorkspace();
    }
  }));
  $("new-project-name").addEventListener("click", () => {
    $("project").value = nextProjectName($("project").value);
    $("error").hidden = true;
    touchedIntake.add("project");
    summarize();
    $("project").focus();
  });
  $("reuse-scenario").addEventListener("change", () => {
    const source = reusableScenarios.find((item) => item.id === $("reuse-scenario").value);
    if (source) {
      for (const name of ["services", "pillars", "domains"]) {
        for (const input of document.querySelectorAll(`input[name="${name}"]`))
          input.checked = input.disabled || source[name].includes(input.value);
      }
    }
    describeSource();
    summarize();
  });
  $("connection").textContent = catalog.cliAvailable
    ? "Local CLI detected"
    : "Install Copilot CLI";
  $("workspace-consent").addEventListener("change", () => {
    if (currentRun) renderRun(currentRun);
    else summarize();
  });
  $("system-refresh").addEventListener("click", action(refreshSystem));
  $("system-preflight-consent").addEventListener("change", prerequisiteControls);
  renderPrerequisiteChecks("system", catalog.prerequisiteInventory, { stages: {} });
  for (const id of ["system-preflight-scope", "system-build-mode", "system-local-functions"])
    $(id).addEventListener("change", action(resetSystemPrerequisites));
  for (const scope of ["intake", "system"])
    $(scope + "-preflight-check").addEventListener("click", action(() => prerequisiteCheck(scope)));
  $("system-confirm").addEventListener("change", systemControls);
  for (const kind of ["stop", "restart"])
    $("system-" + kind).addEventListener("click", action(() => serverAction(kind)));
  for (const name of ["shape", "build", "hack", "system"]) {
    $("nav-" + name).addEventListener("click", action(async (event) => {
      event.preventDefault();
      navigationRevision++;
      $("error").hidden = true;
      showStage(name);
      if (name === "system") await refreshSystem();
    }));
  }
  showStage(location.hash === "#system" ? "system"
    : location.hash === "#review" ? "hack" : location.hash === "#workspace" ? "build" : "shape", false);
  if (currentStage === "system") await refreshSystem();
  const updateIntake = (event) => {
    const field = event.target.id === "tool-consent" ? "consent" : event.target.name;
    if (field) touchedIntake.add(field);
    summarize();
  };
  $("scenario-form").addEventListener("input", updateIntake);
  $("scenario-form").addEventListener("change", updateIntake);
  $("review").addEventListener("input", summarize);
  $("scenario-form").addEventListener(
    "submit",
    action(async () => {
      const data = validatedIntake(true);
      const navigation = navigationRevision;
      launching = true;
      summarize();
      try {
        await refreshProjects();
        if (existingProject(data.projectSlug)) {
          touchedIntake.add("project");
          throw new Error(`“${data.projectSlug}” already exists. Open the existing project or use a new name below.`);
        }
        const run = await api("/api/runs", data);
        await refreshRuns(
          navigation === navigationRevision ? run.id : undefined, data.projectSlug,
        );
        if (navigation === navigationRevision) {
          showStage("build");
          scrollToWorkspace();
        }
      } catch (error) {
        if (error.code === "project_exists" && error.project?.projectSlug === data.projectSlug) {
          knownProjects = knownProjects.filter((item) => item.projectSlug !== data.projectSlug);
          knownProjects.push(error.project);
          touchedIntake.add("project");
        }
        throw error;
      } finally {
        launching = false;
        summarize();
      }
    }),
  );
  $("preview").addEventListener("click", action(preview));
  $("copy").addEventListener(
    "click",
    action(async () => {
      await navigator.clipboard.writeText(previewText);
      $("copy").textContent = "Copied";
    }),
  );
  $("download").addEventListener(
    "click",
    action(async () => {
      const value = await preview();
      const blob = new Blob([JSON.stringify(value.request, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${value.request.projectSlug}-request.json`;
      link.click();
      URL.revokeObjectURL(url);
    }),
  );
  $("refresh-runs").addEventListener(
    "click",
    action(() => refreshRuns()),
  );
  $("answer-decision").addEventListener("click", action(() => followup("continue")));
  $("run-select").addEventListener(
    "change",
    action(async () => {
      if ($("run-select").value) {
        navigationRevision++;
        selectRun($("run-select").value);
        await loadRun(selectedRunId);
      }
    }),
  );
  for (const kind of ["continue", "revise", "compose", "stop", "retry-setup", "revoke-consent"]) {
    $(kind).addEventListener(
      "click",
      action(() => followup(kind)),
    );
  }
  $("example").addEventListener("click", () => {
    $("prompt").value =
      "Build a finance risk-assistance scenario. A Foundry agent should explain synthetic portfolio exposure using Cosmos DB data, with managed identity, traceable answers and explicit errors.";
    $("project").value = "finance-risk-agent";
    for (const input of document.querySelectorAll('input[name="industry"]'))
      input.checked = input.value === "Financial Services";
    for (const input of document.querySelectorAll('input[name="businessUnits"]'))
      input.checked = input.value === "finance";
    for (const input of document.querySelectorAll('input[name="services"]'))
      input.checked = ["foundry", "cosmos-db", "managed-identity"].includes(
        input.value,
      );
    for (const input of document.querySelectorAll('input[name="pillars"]'))
      input.checked = ["security", "reliability"].includes(input.value);
    summarize();
  });
  summarize();
  await refreshCatalog();
  await refreshProjects();
  await refreshRuns();
  intakeReady = true;
  summarize();
}

function describeSource() {
  const source = reusableScenarios.find((item) => item.id === $("reuse-scenario").value);
  $("reuse-description").textContent = source
    ? `${source.title} · ${source.industry || "Industry not recorded"} · ${source.metadataStatus}. ${source.summary} ` +
      "Choose your target industry and business units below. Architecture is guidance; app/data and validation are new."
    : "Reuse creates a new reference. Deployment state, approvals and credentials are never inherited.";
}

async function refreshCatalog() {
  const previous = $("reuse-scenario").value;
  const value = await api("/api/scenarios");
  reusableScenarios = value.scenarios;
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = "Start a new scenario";
  $("reuse-scenario").replaceChildren(empty, ...reusableScenarios.map((item) => {
    const option = document.createElement("option");
    option.value = item.id;
    option.disabled = !item.available;
    option.textContent = `${item.title} (${item.id})${item.available ? "" : " · local files/manifest required"}`;
    return option;
  }));
  if (reusableScenarios.some((item) => item.id === previous && item.available)) $("reuse-scenario").value = previous;
  $("catalog-errors").textContent = value.errors.map((item) => `${item.id}: ${item.error}`).join("; ");
  describeSource();
  summarize();
}

function startPortal() {
  initializeThemeSwitch();
  initialize().catch((error) => {
    $("connection").textContent = "Connection required";
    $("launch").disabled = true;
    $("launch-status").textContent = `Cannot build: ${error.message}`;
    $("launch-status").dataset.ready = "false";
    showError(error);
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", startPortal, { once: true });
} else {
  startPortal();
}
