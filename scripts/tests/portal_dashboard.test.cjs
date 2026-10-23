// Exercise dashboard state and actions with the Node runtime and a minimal DOM.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

class Element {
  constructor(tag = "div") {
    this.tag = tag;
    this.value = "";
    this.checked = false;
    this.hidden = false;
    this.children = [];
    this.dataset = {};
    this.listeners = {};
    this.textContent = "";
  }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) {
    this.children = children;
    if (this.tag === "select") this.value = children[0]?.value || "";
  }
  add(child) { this.children.push(child); }
  addEventListener(name, listener) { this.listeners[name] = listener; }
  setAttribute(name, value) { this[name] = value; }
  focus() { this.focused = true; }
  scrollIntoView(options) { this.scrollOptions = options; }
}

test("Worker activity is collapsed by default and renders literal observed actions without reopening", async () => {
  const run = fixture();
  run.status = "running";
  run.activity = {
    processAlive: true,
    lastOutputAtUtc: new Date(Date.now() - 240000).toISOString(),
    recentActions: ["Read infrastructure", "<script>Run tests</script>"],
  };
  const { get, context } = await dashboard(run);
  const html = fs.readFileSync(path.join(__dirname, "..", "..", "portal", "index.html"), "utf8");
  assert.match(html, /<details id="worker-activity" class="worker-activity">/);
  assert.match(get("worker-activity-status").textContent, /Process running/);
  assert.match(get("worker-activity-status").textContent, /does not mean it is stuck/);
  assert.equal(get("worker-recent-actions").children[0].textContent, "<script>Run tests</script>");
  get("worker-activity").open = true;
  vm.runInContext("renderRun(currentRun)", context);
  assert.equal(get("worker-activity").open, true);
});

test("Azure readiness displays private proposal sources and requires discovery consent without authorizing", async () => {
  const run = fixture();
  run.project.deploymentContext = {
    scope: { account: "operator@example.test", environment: "finance-agent", region: "eastus2" },
    sources: { account: "Current Azure CLI", environment: "Scenario slug", region: "Architecture" },
    authentication: { azureCli: "Signed in", azd: "Signed in", compatibility: "Preflight still needed" },
    checkedAtUtc: "2026-10-23T15:00:00Z", conflicts: [],
  };
  const { get } = await dashboard(run);
  assert.equal(get("azure-resolve").disabled, true);
  assert.match(get("azure-context-fields").children.at(-1).textContent, /eastus2.*Architecture/);
  assert.equal(get("azure-environment").value, "finance-agent");
  get("azure-discovery-consent").checked = true;
  get("azure-discovery-consent").listeners.change();
  assert.equal(get("azure-resolve").disabled, false);
  assert.equal(run.project.authorizations.length, 0);
});

test("Backend readiness consolidates failures and retains collapsed state without claiming scenario success", async () => {
  const run = fixture();
  run.project.decisions = [];
  run.project.backendReadiness = {
    ready: false, checkedAtUtc: "2026-10-23T20:00:00Z",
    plan: { stages: { "local-validation": ["docker"] } },
    checks: [
      { id: "docker", name: "Docker", ok: false, detail: "Engine stopped", fix: "Start Docker Desktop." },
      { id: "azure-authentication", name: "Azure sign-in", ok: false, detail: "azd signed out" },
      { id: "chromium-runtime", name: "Chromium", ok: true, detail: "Actual browser launch passed" },
    ],
  };
  const { get, context, requests } = await dashboard(run);
  assert.match(get("backend-readiness-badge").textContent, /Needs attention/);
  assert.match(get("backend-readiness-status").textContent, /1\/3 passed/);
  assert.equal(get("backend-preflight-results").children.length, 3);
  assert.equal(get("backend-setup").disabled, false);
  get("backend-readiness").open = true;
  vm.runInContext("renderRun(currentRun)", context);
  assert.equal(get("backend-readiness").open, true);
  assert.equal(requests.some((item) => item.url === "/api/readiness/repair"), false);
  run.status = "running";
  run.project.writer = run.id;
  vm.runInContext(`renderRun(${JSON.stringify(run)})`, context);
  assert.equal(get("backend-setup").disabled, true);
  assert.equal(get("backend-retry").disabled, true);
});

test("Visible execution controls resume idle cancelled projects and never bypass pending decisions", async () => {
  const run = fixture();
  run.status = "cancelled";
  run.project.status = "cancelled";
  run.project.decisions = [];
  const { get, context } = await dashboard(run);
  assert.equal(get("play").disabled, false);
  assert.equal(get("pause").disabled, true);
  assert.equal(get("cancel-run").disabled, true);
  assert.match(get("execution-control-status").textContent, /Idle.*no worker is running/);
  run.project.status = "needs_attention";
  vm.runInContext(`renderRun(${JSON.stringify(run)})`, context);
  assert.equal(get("play").disabled, false);
  run.project.decisions = fixture().project.decisions;
  vm.runInContext(`renderRun(${JSON.stringify(run)})`, context);
  assert.equal(get("play").disabled, true);
  assert.match(get("execution-control-status").textContent, /Waiting for the decision/);
  run.status = "running";
  run.project.writer = run.id;
  vm.runInContext(`renderRun(${JSON.stringify(run)})`, context);
  assert.equal(get("pause").disabled, false);
  assert.equal(get("cancel-run").disabled, false);
});

test("Unreviewed technical questions stay internal; only classified business decisions reach the user", async () => {
  const run = fixture();
  run.project.decisions[0].kind = "business";
  const { get, context } = await dashboard(run);
  assert.equal(get("cancel-run").disabled, false);
  assert.equal(get("decision-panel").hidden, true);
  assert.equal(get("play").disabled, false);
  run.project.decisions[0].review = {
    disposition: "business", unresolvedNeed: "Advice scope is unresolved.",
    intakeEvidence: "Intake does not specify personalized advice.",
    choiceImpacts: { Education: "General information only", Advice: "Additional compliance controls" },
  };
  vm.runInContext(`renderRun(${JSON.stringify(run)})`, context);
  assert.equal(get("decision-panel").hidden, false);
  assert.equal(get("play").disabled, true);
  assert.match(get("decision-reason").textContent, /Additional compliance controls/);
  run.project.decisions[0].kind = "deployment";
  vm.runInContext(`renderRun(${JSON.stringify(run)})`, context);
  assert.equal(get("play").disabled, true);
  assert.equal(get("cancel-run").disabled, false);
});

function fixture() {
  const project = {
    revision: 5,
    status: "waiting_for_user",
    writer: null,
    localToolConsent: { scope: "scenario-local-execution", grantedAtUtc: "2026-10-22T19:00:00Z" },
    stages: { requirements: { status: "completed", summary: "Brokerage story recorded" } },
    authorizations: [],
    decisions: [{
      id: "design-1", status: "pending", kind: "design",
      question: "Confirm the design?", reason: "Review private backend and public chat",
      choices: ["Confirm", "Revise"], acceptChoice: "Confirm",
    }],
  };
  return {
    id: "run-2", kind: "scenario", status: "completed", startedAtUtc: "2026-10-22T19:00:00Z",
    request: { projectSlug: "finance-agent" }, project, review: { ready: false }, output: "raw CLI details",
  };
}

test("Local projects can resume in place with explicit consent rather than a new intake", async () => {
  const run = {
    id: "local-preview", kind: "local-preview", status: "discovered", discovered: true,
    request: { projectSlug: "legacy-reference" }, project: null, review: { ready: false },
    localInventory: ["01-requirements.md", "infra", "src"],
  };
  const { get, context, requests } = await dashboard(run);
  assert.equal(get("workspace-consent-label").hidden, false);
  assert.equal(get("workspace-consent").checked, false);
  assert.equal(get("play").disabled, true);
  assert.match(get("play").textContent, /Resume existing scenario/);
  assert.match(get("project-summary").textContent, /without starting over/);
  assert.equal(get("compose").disabled, true);
  get("workspace-consent").checked = true;
  vm.runInContext(`renderRun(${JSON.stringify(run)})`, context);
  assert.equal(get("play").disabled, false);
  assert.equal(get("continue").disabled, true);
  assert.equal(get("pause").disabled, true);
  const before = requests.filter((item) => item.method === "POST").length;
  assert.equal(before, 0);
  await get("play").listeners.click({ preventDefault() {} });
  const submitted = requests.find((item) => item.url === "/api/runs/local-preview/resume-local");
  assert.ok(submitted);
  assert.equal(JSON.parse(submitted.body).toolConsent, true);
  assert.equal(requests.some((item) => item.url === "/api/runs" && item.method === "POST"), false);
});

async function dashboard(run = fixture(), workflowVersion = 5, appearance = {}) {
  const elements = new Map();
  const created = [];
  const requests = [];
  const storage = new Map();
  if (appearance.savedTheme !== undefined) storage.set("abcbuilder-theme", appearance.savedTheme);
  const events = {};
  const domEvents = {};
  const warnings = [];
  let domReady = !appearance.loading;
  let launchedRun;
  const media = {
    matches: Boolean(appearance.systemDark),
    addEventListener(name, handler) { this.listener = handler; },
  };
  const storageFailure = () => { const error = new Error("Storage disabled"); error.name = "SecurityError"; throw error; };
  const scenarios = [{
    id: "finance-source", title: "Finance reference", industry: "Financial Services",
    metadataStatus: "curated", summary: "Reuse the private agent architecture.",
    services: ["foundry"], pillars: [], domains: [], available: true, manifestDigest: "a".repeat(64),
  }];
  const catalog = {
    industries: [{ id: "Financial Services", name: "Financial Services" }],
    businessUnits: [
      { id: "generic", name: "Generic" }, { id: "finance", name: "Finance" }, { id: "it", name: "IT" },
    ],
    services: [{ id: "foundry", name: "Foundry", required: true }],
    pillars: [], domains: [], cliAvailable: appearance.cliAvailable ?? true, workflowVersion, backendEngineVersion: 3,
    maxConcurrentWorkers: 4,
    systemControlsVersion: appearance.systemControlsVersion ?? 1,
    prerequisitesVersion: appearance.prerequisitesVersion ?? 1,
    prerequisiteInventory: [
      {id:"azure-cli", name:"Azure CLI", state:"not-checked", stages:["bicep"]},
      {id:"azd", name:"Azure Developer CLI", state:"not-checked", stages:["deployment"]},
      {id:"docker", name:"Docker CLI and running Linux engine", state:"not-checked", stages:["local-validation"]},
    ],
  };
  const get = (id) => {
    if (!elements.has(id)) elements.set(id, new Element(
      ["run-select", "decision-choice", "reuse-scenario", "system-build-mode", "system-preflight-scope"].includes(id)
        ? "select" : "div",
    ));
    return elements.get(id);
  };
  const query = (selector) => {
    const name = /name="([^"]+)"/.exec(selector)?.[1];
    const value = /value="([^"]+)"/.exec(selector)?.[1];
    return created.filter((item) => item.tag === "input" &&
      (!name || item.name === name) && (!value || item.value === value) &&
      (!selector.includes(":checked") || item.checked));
  };
  const context = vm.createContext({
    document: {
      documentElement: new Element("html"), readyState: appearance.loading ? "loading" : "complete",
      addEventListener: (name, handler) => { domEvents[name] = () => { domReady = true; handler(); }; },
      getElementById: (id) => domReady ? get(id) : null,
      querySelectorAll: query, querySelector: (selector) => query(selector)[0],
      createElement: (tag) => { const item = new Element(tag); created.push(item); return item; },
    },
    matchMedia: (query) => query.includes("prefers-color-scheme")
      ? media : { matches: Boolean(appearance.reducedMotion) },
    addEventListener: (name, handler) => { events[name] = handler; },
    localStorage: {
      getItem: (key) => appearance.storageBlocked ? storageFailure() : storage.get(key) ?? null,
      setItem: (key, value) => appearance.storageBlocked ? storageFailure() : storage.set(key, value),
    },
    console: { warn: (...args) => warnings.push(args) },
    location: { hash: "", pathname: "/", reload() { get("reloaded").textContent = "yes"; } },
    history: { replaceState() {} },
    sessionStorage: { getItem: () => "local-test", setItem() {} },
    URL, URLSearchParams, clearTimeout() {}, setTimeout() { return 1; },
    Option: function (text, value) { this.textContent = text; this.value = value; },
    fetch: async (url, options) => {
      requests.push({ url, ...options });
      if (url.startsWith("/api/prerequisites/plan?")) return { ok:true, json:async () => ({
        checks:catalog.prerequisiteInventory,
        stages: { requirements:[], architecture:[], diagrams:["graphviz"], bicep:["azure-cli"],
          application:["dotnet"], "local-validation":["docker"] },
      }) };
      if (url === "/api/prerequisites/check") {
        if (appearance.preflightGate) await appearance.preflightGate;
        return { ok:true, json:async () => ({
          checkedAtUtc:"2026-10-23T05:00:00Z",
          checks:[
            {id:"azure-cli", name:"Azure CLI", ok:true, installed:true, state:"ready", detail:"Version checked"},
            {id:"docker", name:"Docker CLI and running Linux engine", ok:false, installed:true,
              state:"engine-unavailable", detail:"Linux engine unavailable", fix:"Start Docker Desktop."},
          ],
          plan:{ stages:{bicep:["azure-cli"],"local-validation":["docker"]} },
        }) };
      }
      if (url === "/api/system") return { ok: true, json: async () => structuredClone(appearance.system || {
        status: "running", pid: 123, uptimeSeconds: 30, workspace: "C:\\workspace",
        stateDirectory: "C:\\workspace\\.abcbuilder-portal", pythonExecutable: "python.exe",
        port: 8765, startedAtUtc: "2026-10-23T00:00:00Z", workflowVersion: 5, workers: [],
        canStopServer: true, launcher: "C:\\workspace\\Start-ABCBuilder.cmd",
      }) };
      if (url === "/api/system/stop" || url === "/api/system/restart") return {
        ok: true, json: async () => ({ action: url.split("/").at(-1), restartToken: "replacement-test-token" }),
      };
      if (url === "/api/health") return {
        ok: true, json: async () => ({ status: "ok", workspace: "C:\\workspace" }),
      };
      if (url === "/api/projects") {
        if (appearance.projectsUnavailable)
          return { ok: false, status: 500, json: async () => ({ error: "Project state could not be read." }) };
        return { ok: true, json: async () => structuredClone(appearance.projects || []) };
      }
      if (url === "/api/runs" && options.method === "POST") {
        if (appearance.startGate) await appearance.startGate;
        if (appearance.conflict) return {
          ok: false, status: 409, json: async () => ({
            error: "This project already exists.", code: "project_exists", project: appearance.conflict,
          }),
        };
        launchedRun = { ...run, id: "run-new", status: "running", request: JSON.parse(options.body) };
        return { ok: true, json: async () => structuredClone(launchedRun) };
      }
      if (options.method === "POST" &&
          /^\/api\/runs\/[^/]+\/(continue|revise|compose|stop|retry-setup|revoke-consent|resume-local)$/.test(url)) {
        if (appearance.followupGate) await appearance.followupGate;
        if (url.endsWith("/revoke-consent")) {
          run.project.localToolConsent = null;
          run.project.revision++;
        }
        return { ok: true, json: async () => structuredClone(appearance.followupRun || run) };
      }
      if (options.method === "GET" && /^\/api\/runs\/[^/]+$/.test(url) && appearance.readRun) {
        const override = await appearance.readRun(url);
        if (override) return { ok: true, json: async () => structuredClone(override) };
      }
      const other = (appearance.additionalRuns || []).find((item) => url === `/api/runs/${item.id}`);
      const value = url === "/api/catalog" ? catalog
        : url === "/api/scenarios" ? { scenarios, errors: [] }
        : url === "/api/preview" ? { request: JSON.parse(options.body), prompt: "Prepared scenario preview" }
        : url === "/api/runs" ? [
          ...(launchedRun ? [launchedRun] : []),
          run,
          { ...run, id: "run-1", startedAtUtc: "2026-10-22T18:00:00Z" },
          ...(appearance.additionalRuns || []),
        ] : url.includes("/artifact?") ? {
          path: "packages/coach-guide/Finale.md", text: "<script>not executed</script>\nPrivate answer",
        } : other || (appearance.archivedRun && url.endsWith(appearance.archivedRun.id) ? appearance.archivedRun
        : launchedRun && url.endsWith(launchedRun.id) ? launchedRun : run);
      return { ok: true, json: async () => structuredClone(value) };
    },
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, "..", "..", "portal", "app.js"), "utf8"), context);
  await new Promise(setImmediate);
  get("system-build-mode").value = "auto";
  get("system-preflight-scope").value = "all";
  return { get, context, requests, run, query, storage, media, events, domEvents, warnings };
}

function readyBrief(view) {
  view.get("project").value = "energy-operations";
  view.query('input[name="industry"]')[0].checked = true;
  view.get("tool-consent").checked = true;
  vm.runInContext("summarize()", view.context);
}

test("System navigation is read-only and reports local server details without launching work", async () => {
  const view = await dashboard();
  await view.get("nav-system").listeners.click({ preventDefault() {} });
  assert.equal(view.get("system").hidden, false);
  assert.equal(view.get("workspace").hidden, true);
  assert.equal(view.get("scenario-form").hidden, true);
  assert.equal(view.get("page-stage").textContent, "System");
  assert.match(view.get("system-status").textContent, /PID 123/);
  assert.match(view.get("system-worker-status").textContent, /All workers are idle/);
  assert.equal(view.get("system-stop").disabled, true);
  assert.equal(view.get("system-restart").disabled, true);
  assert.equal(view.requests.some(item => item.method === "POST"), false);
});

test("System stop and restart remain blocked by workers despite a checked confirmation", async () => {
  const view = await dashboard(fixture(), 5, { system: {
    status: "running", pid: 123, workers: [{
      runId: "other-worker", projectSlug: "other-scenario", kind: "scenario", pid: 456, canStop: false,
    }], canStopServer: false,
  } });
  await view.get("nav-system").listeners.click({ preventDefault() {} });
  view.get("system-confirm").checked = true;
  view.get("system-confirm").listeners.change();
  assert.equal(view.get("system-stop").disabled, true);
  assert.equal(view.get("system-restart").disabled, true);
  assert.match(view.get("system-worker-status").textContent, /blocked/);
  await view.get("system-stop").listeners.click();
  assert.match(view.get("error").textContent, /all workers are idle/);
  assert.equal(view.requests.some(item => item.url === "/api/system/stop"), false);
});

test("System worker stop is confirmed and targets only that worker without changing scenario selection", async () => {
  const view = await dashboard(fixture(), 5, { system: {
    status: "running", pid: 123, workers: [{
      runId: "other-worker", projectSlug: "other-scenario", kind: "scenario", pid: 456, canStop: true,
    }], canStopServer: false,
  } });
  await view.get("nav-system").listeners.click({ preventDefault() {} });
  const row = view.get("system-workers").children[0];
  const checkbox = row.children[1].children[0];
  const button = row.children[2];
  assert.equal(button.disabled, true);
  checkbox.checked = true;
  checkbox.listeners.change();
  await button.listeners.click();
  assert.equal(view.requests.filter(item => item.method === "POST").length, 1);
  assert.equal(view.requests.find(item => item.method === "POST").url, "/api/runs/other-worker/stop");
  assert.equal(view.get("run-select").value, "run-2");
  assert.equal(view.get("page-stage").textContent, "System");
});

test("System shutdown is explicit and leaves launcher recovery visible without refreshing the stopped server", async () => {
  const view = await dashboard();
  await view.get("nav-system").listeners.click({ preventDefault() {} });
  view.get("system-confirm").checked = true;
  view.get("system-confirm").listeners.change();
  assert.equal(view.get("system-stop").disabled, false);
  await view.get("system-stop").listeners.click();
  assert.match(view.get("system-status").textContent, /Shutdown accepted/);
  assert.equal(view.get("system-stop").disabled, true);
  const before = view.requests.length;
  await vm.runInContext("refreshRuns()", view.context);
  assert.equal(view.requests.length, before);
  assert.equal(JSON.parse(view.requests.find(item => item.url === "/api/system/stop").body).confirmed, true);
});

test("System restart waits for authenticated health then reloads the fresh backend", async () => {
  const view = await dashboard();
  await view.get("nav-system").listeners.click({ preventDefault() {} });
  view.get("system-confirm").checked = true;
  await view.get("system-restart").listeners.click();
  assert.equal(view.get("reloaded").textContent, "yes");
  assert.equal(view.requests.filter(item => item.url === "/api/system/restart").length, 1);
  assert.equal(view.requests.filter(item => item.url === "/api/health").length, 1);
});

test("System page requires a compatible backend rather than presenting unsupported controls", async () => {
  const view = await dashboard(fixture(), 5, { systemControlsVersion: 0 });
  assert.match(view.get("error").textContent, /Restart the local portal/);
  assert.equal(view.requests.some(item => item.url === "/api/system"), false);
});

test("System checklist starts unchecked and requires authorization before command probes", async () => {
  const view = await dashboard();
  assert.equal(view.get("system-preflight-results").children.length, 3);
  const row = view.get("system-preflight-results").children[0];
  assert.equal(row.dataset.state, "not-checked");
  assert.match(row.children[1].textContent, /Not checked: Azure CLI/);
  assert.equal(view.get("system-preflight-check").disabled, true);
  await view.get("system-preflight-check").listeners.click();
  assert.match(view.get("error").textContent, /Authorize/);
  assert.equal(view.requests.some(item => item.url === "/api/prerequisites/check"), false);
});

test("System checklist distinguishes ready tools from an installed stopped Docker engine and shows its fix", async () => {
  const view = await dashboard();
  view.get("system-preflight-consent").checked = true;
  view.get("system-preflight-consent").listeners.change();
  await view.get("system-preflight-check").listeners.click();
  const rows = view.get("system-preflight-results").children;
  assert.equal(rows[0].dataset.state, "ready");
  assert.equal(rows[0].children[0].textContent, "\u2611");
  assert.match(rows[0].children[1].textContent, /Ready: Azure CLI/);
  assert.equal(rows[1].dataset.state, "engine-unavailable");
  assert.match(rows[1].children[2].textContent, /Executable discovered/);
  assert.match(rows[1].children[2].textContent, /Start Docker Desktop/);
  assert.match(view.get("system-preflight-status").textContent, /1 passed; 1 failed/);
  assert.equal(view.requests.filter(item => item.method === "POST").length, 1);
});

test("Intake audits do not block early scenario work when a future container tool fails", async () => {
  const view = await dashboard();
  readyBrief(view);
  assert.equal(view.get("launch").disabled, false);
  await view.get("intake-preflight-check").listeners.click();
  assert.match(view.get("intake-preflight-status").textContent, /Requirements\/design can proceed/);
  assert.equal(view.get("launch").disabled, false);
  assert.equal(view.requests.some(item => item.url === "/api/runs" && item.method === "POST"), false);
});

test("System scope changes clear green results instead of retaining old readiness", async () => {
  const view = await dashboard();
  view.get("system-preflight-consent").checked = true;
  await view.get("system-preflight-check").listeners.click();
  view.get("system-build-mode").value = "remote";
  await view.get("system-build-mode").listeners.change();
  assert.match(view.get("system-preflight-status").textContent, /Not checked/);
  assert.equal(view.get("system-preflight-results").children[0].dataset.state, "not-checked");
});

test("Late prerequisite results cannot replace a changed diagnostic scope", async () => {
  let release;
  const preflightGate = new Promise(resolve => { release = resolve; });
  const view = await dashboard(fixture(), 5, {preflightGate});
  view.get("system-preflight-consent").checked = true;
  const checking = view.get("system-preflight-check").listeners.click();
  view.get("system-build-mode").value = "remote";
  await view.get("system-build-mode").listeners.change();
  release();
  await checking;
  assert.match(view.get("system-preflight-status").textContent, /Scope changed during/);
  assert.equal(view.get("system-preflight-results").children[0].dataset.state, "not-checked");
});

function blockers(view) {
  return view.get("launch-blockers").children.map((item) => item.children[0]?.textContent || item.textContent);
}

test("intake explains every missing required value beside the disabled build button", async () => {
  const view = await dashboard();
  assert.equal(view.get("launch").disabled, true);
  assert.deepEqual(blockers(view), [
    "Enter a project name.", "Choose one industry.", "Check the local tool execution consent box below.",
  ]);
  assert.match(view.get("launch-status").textContent, /3 items/);
  assert.equal(view.get("project-error").hidden, true);
  view.get("launch-blockers").children[0].children[0].listeners.click();
  assert.equal(view.get("project").focused, true);
  assert.equal(view.get("project")["aria-invalid"], "true");
  assert.equal(view.get("project-error").hidden, false);
});

test("a valid brief enables build and keeps the summary in sync", async () => {
  const view = await dashboard();
  readyBrief(view);
  assert.equal(view.get("launch").disabled, false);
  assert.match(view.get("launch-status").textContent, /^Ready to build/);
  assert.equal(view.get("launch-blockers").children.length, 0);
  assert.equal(view.get("summary-project").textContent, "energy-operations");
  assert.equal(view.get("summary-industry").textContent, "Financial Services");
  assert.equal(view.get("summary-business-units").textContent, "Generic");
});

test("project format and length errors are inline and clear when corrected", async () => {
  const view = await dashboard();
  readyBrief(view);
  for (const value of ["Energy", "energy ops", "energy--ops", "../other", "x".repeat(41)]) {
    view.get("project").value = value;
    view.get("scenario-form").listeners.input({ target: { name: "project" } });
    assert.equal(view.get("launch").disabled, true, value);
    assert.equal(view.get("project-error").hidden, false, value);
    assert.equal(view.get("project")["aria-invalid"], "true", value);
  }
  view.get("project").value = "x".repeat(40);
  view.get("scenario-form").listeners.input({ target: { name: "project" } });
  assert.equal(view.get("launch").disabled, false);
  assert.equal(view.get("project-error").hidden, true);
  assert.equal(view.get("project")["aria-invalid"], "false");
});

test("prompt length and empty unit selections use the same limits as the backend", async () => {
  const view = await dashboard();
  readyBrief(view);
  view.get("prompt").value = "x".repeat(6001);
  view.get("scenario-form").listeners.input({ target: { name: "prompt" } });
  assert.equal(view.get("launch").disabled, true);
  assert.match(view.get("prompt-error").textContent, /6,000/);
  view.get("prompt").value = "x".repeat(6000);
  view.get("scenario-form").listeners.input({ target: { name: "prompt" } });
  assert.equal(view.get("launch").disabled, false);
  view.get("prompt").value = "";
  view.query('input[name="businessUnits"][value="generic"]')[0].checked = false;
  view.get("scenario-form").listeners.change({ target: { name: "businessUnits" } });
  assert.equal(view.get("launch").disabled, true);
  assert.equal(view.query('input[name="businessUnits"]')[0]["aria-invalid"], "true");
  view.query('input[name="businessUnits"][value="generic"]')[0].checked = true;
  vm.runInContext("summarize()", view.context);
  assert.equal(view.get("launch").disabled, false);
});

test("business unit, consent and existing-project blockers are specific", async () => {
  const view = await dashboard();
  readyBrief(view);
  view.query('input[name="businessUnits"][value="generic"]')[0].checked = false;
  vm.runInContext("summarize()", view.context);
  assert.match(blockers(view)[0], /Select at least one business unit/);
  view.query('input[name="businessUnits"][value="generic"]')[0].checked = true;
  view.get("tool-consent").checked = false;
  vm.runInContext("summarize()", view.context);
  const consentLink = view.get("launch-blockers").children[0].children[0];
  consentLink.listeners.click();
  assert.equal(view.get("tool-consent").focused, true);
  assert.equal(view.get("tool-consent").checked, false);
  view.get("tool-consent").checked = true;
  for (const slug of ["finance-agent", "finance-source"]) {
    view.get("project").value = slug;
    vm.runInContext("summarize()", view.context);
    assert.match(blockers(view)[0], /already exists/);
    assert.equal(view.get("launch").disabled, true);
  }
});

test("an unrelated running job does not block a new scenario; missing CLI is explained separately", async () => {
  const view = await dashboard(fixture(), 5, {
    cliAvailable: false,
    additionalRuns: [{ ...fixture(), id: "other-run", status: "running", request: { projectSlug: "other-project" } }],
  });
  readyBrief(view);
  assert.equal(view.get("launch").disabled, true);
  assert.ok(blockers(view).some((message) => /CLI was not detected/.test(message)));
  assert.ok(!blockers(view).some((message) => /busy|other-project/.test(message)));
  assert.match(view.get("worker-capacity").textContent, /1 of 4 workers active/);
});

test("four busy workers block new work but leave navigation and the selected job's stop action available", async () => {
  const additionalRuns = Array.from({ length: 4 }, (_, number) => ({
    ...fixture(), id: `busy-${number}`, status: "running",
    request: { projectSlug: `scenario-${number}` },
  }));
  const view = await dashboard(fixture(), 5, { additionalRuns });
  readyBrief(view);
  assert.equal(view.get("launch").disabled, true);
  assert.ok(blockers(view).some((message) => /All 4 workers are busy/.test(message)));
  assert.match(view.get("worker-capacity").textContent, /4 of 4 workers active/);
  assert.equal(view.get("worker-list").children.length, 4);
  assert.equal(view.get("continue").disabled, true);
  view.get("nav-build").listeners.click({ preventDefault() {} });
  view.get("run-select").value = "busy-2";
  await view.get("run-select").listeners.change({ preventDefault() {} });
  assert.equal(vm.runInContext("currentRun.id", view.context), "busy-2");
  assert.equal(view.get("stop").hidden, false);
  await view.get("stop").listeners.click({ preventDefault() {} });
  const posts = view.requests.filter((item) => item.method === "POST");
  assert.equal(posts.length, 1);
  assert.equal(posts[0].url, "/api/runs/busy-2/stop");
});

test("three other workers leave a slot for another scenario and preserve worker-link focus on refresh", async () => {
  const additionalRuns = Array.from({ length: 3 }, (_, number) => ({
    ...fixture(), id: `busy-${number}`, status: "running", request: { projectSlug: `scenario-${number}` },
  }));
  const view = await dashboard(fixture(), 5, { additionalRuns });
  readyBrief(view);
  assert.equal(view.get("launch").disabled, false);
  assert.equal(view.get("answer-decision").disabled, false);
  const link = view.get("worker-list").children[0].children[0];
  await vm.runInContext("refreshRuns()", view.context);
  assert.equal(view.get("worker-list").children[0].children[0], link);
});

test("scenario switching preserves independent drafts, decision choices, review confirmations and last stage", async () => {
  const first = fixture();
  first.review = { ready: true, fingerprint: "review-a", checks: {}, applicationUrl: "https://example.invalid/a" };
  const other = {
    ...structuredClone(first), id: "other-run", request: { projectSlug: "other-scenario" },
    review: { ...first.review, fingerprint: "review-b" },
  };
  const view = await dashboard(first, 5, { additionalRuns: [other] });
  view.get("prompt").value = "Keep the new scenario intake untouched";
  view.get("decision").value = "Instructions for A";
  view.get("decision-choice").value = "Confirm";
  view.get("approval").value = "Approval draft for A";
  view.get("tested").checked = true;
  view.get("nav-hack").listeners.click({ preventDefault() {} });
  view.get("run-select").value = other.id;
  await view.get("run-select").listeners.change({ preventDefault() {} });
  assert.equal(view.get("decision").value, "");
  assert.equal(view.get("decision-choice").value, "");
  assert.equal(view.get("approval").value, "");
  assert.equal(view.get("tested").checked, false);
  view.get("decision").value = "Instructions for B";
  view.get("nav-build").listeners.click({ preventDefault() {} });
  view.get("run-select").value = first.id;
  await view.get("run-select").listeners.change({ preventDefault() {} });
  assert.equal(view.get("decision").value, "Instructions for A");
  assert.equal(view.get("decision-choice").value, "Confirm");
  assert.equal(view.get("approval").value, "Approval draft for A");
  assert.equal(view.get("tested").checked, true);
  assert.equal(view.get("page-stage").textContent, "Compose the hack");
  first.review.fingerprint = "changed-review";
  await vm.runInContext("refreshRuns()", view.context);
  assert.equal(view.get("approval").value, "");
  assert.equal(view.get("tested").checked, false);
  view.get("run-select").value = other.id;
  await view.get("run-select").listeners.change({ preventDefault() {} });
  assert.equal(view.get("decision").value, "Instructions for B");
  assert.equal(view.get("page-stage").textContent, "Build & validate");
  assert.equal(view.get("prompt").value, "Keep the new scenario intake untouched");
  assert.equal(view.requests.filter((item) => item.method === "POST").length, 0);
});

test("a late status response for the old scenario never replaces a newly selected scenario", async () => {
  let release;
  let block = false;
  const delayed = new Promise((resolve) => { release = resolve; });
  const first = fixture();
  const other = { ...fixture(), id: "other-run", request: { projectSlug: "other-scenario" } };
  const view = await dashboard(first, 5, {
    additionalRuns: [other],
    readRun: async (url) => block && url === `/api/runs/${first.id}` ? delayed : undefined,
  });
  block = true;
  const refresh = vm.runInContext("refreshRuns()", view.context);
  await new Promise(setImmediate);
  view.get("run-select").value = other.id;
  await view.get("run-select").listeners.change({ preventDefault() {} });
  release(first);
  await refresh;
  assert.equal(vm.runInContext("currentRun.id", view.context), other.id);
  assert.equal(view.get("run-select").value, other.id);
});

test("a background launch completing after navigation does not hijack the selected scenario", async () => {
  let release;
  const startGate = new Promise((resolve) => { release = resolve; });
  const other = { ...fixture(), id: "other-run", request: { projectSlug: "other-scenario" } };
  const view = await dashboard(fixture(), 5, { startGate, additionalRuns: [other] });
  readyBrief(view);
  const launch = view.get("scenario-form").listeners.submit({ preventDefault() {} });
  await new Promise(setImmediate);
  view.get("nav-build").listeners.click({ preventDefault() {} });
  view.get("run-select").value = other.id;
  await view.get("run-select").listeners.change({ preventDefault() {} });
  view.get("decision").value = "Keep my current draft";
  release();
  await launch;
  assert.equal(vm.runInContext("currentRun.id", view.context), other.id);
  assert.equal(view.get("decision").value, "Keep my current draft");
  assert.equal(view.get("page-stage").textContent, "Build & validate");
  assert.match(view.get("worker-capacity").textContent, /1 of 4 workers active/);
});

test("actions pause while the newly selected scenario loads instead of targeting the previous scenario", async () => {
  let release;
  let block = false;
  const delayed = new Promise((resolve) => { release = resolve; });
  const other = { ...fixture(), id: "other-run", request: { projectSlug: "other-scenario" } };
  const view = await dashboard(fixture(), 5, {
    additionalRuns: [other],
    readRun: async (url) => block && url === `/api/runs/${other.id}` ? delayed : undefined,
  });
  block = true;
  view.get("run-select").value = other.id;
  const change = view.get("run-select").listeners.change({ preventDefault() {} });
  await new Promise(setImmediate);
  for (const id of ["continue", "revise", "answer-decision", "compose", "stop"])
    assert.equal(view.get(id).disabled, true);
  await view.get("answer-decision").listeners.click({ preventDefault() {} });
  assert.match(view.get("error").textContent, /finish loading/);
  assert.equal(view.requests.filter((item) => item.method === "POST").length, 0);
  release(other);
  await change;
  assert.equal(vm.runInContext("currentRun.id", view.context), other.id);
  assert.equal(view.get("answer-decision").disabled, false);
});

test("a followup completing for A preserves B's selection and draft and targets A's revision", async () => {
  let release;
  const followupGate = new Promise((resolve) => { release = resolve; });
  const first = fixture();
  const other = {
    ...fixture(), id: "other-run", request: { projectSlug: "other-scenario" },
    project: { ...fixture().project, revision: 99 },
  };
  const view = await dashboard(first, 5, { followupGate, additionalRuns: [other] });
  view.get("tool-consent").checked = true;
  view.get("decision-choice").value = "Confirm";
  view.get("decision").value = "Submit only to A";
  const submit = view.get("answer-decision").listeners.click({ preventDefault() {} });
  await new Promise(setImmediate);
  view.get("run-select").value = other.id;
  await view.get("run-select").listeners.change({ preventDefault() {} });
  view.get("decision").value = "Do not erase B's draft";
  release();
  await submit;
  const post = view.requests.find((item) => item.method === "POST");
  assert.equal(post.url, `/api/runs/${first.id}/continue`);
  assert.equal(JSON.parse(post.body).revision, 5);
  assert.equal(vm.runInContext("currentRun.id", view.context), other.id);
  assert.equal(view.get("decision").value, "Do not erase B's draft");
});

test("invalid submission and preview never send requests to start or prepare a scenario", async () => {
  const view = await dashboard();
  await view.get("scenario-form").listeners.submit({ preventDefault() {} });
  await view.get("preview").listeners.click({ preventDefault() {} });
  assert.equal(view.get("launch").disabled, true);
  assert.match(view.get("error").textContent, /Enter a project name/);
  assert.equal(view.requests.filter((request) => request.method === "POST").length, 0);
});

test("preview does not require execution consent, but launch does and prevents duplicate submissions", async () => {
  let release;
  const startGate = new Promise((resolve) => { release = resolve; });
  const view = await dashboard(fixture(), 5, { startGate });
  readyBrief(view);
  view.get("tool-consent").checked = false;
  await vm.runInContext("preview()", view.context);
  assert.equal(view.requests.filter((request) => request.url === "/api/preview").length, 1);
  await view.get("scenario-form").listeners.submit({ preventDefault() {} });
  assert.equal(view.requests.filter((request) => request.url === "/api/runs" && request.method === "POST").length, 0);
  view.get("tool-consent").checked = true;
  const first = view.get("scenario-form").listeners.submit({ preventDefault() {} });
  await new Promise(setImmediate);
  assert.equal(view.get("launch").disabled, true);
  assert.ok(blockers(view).some((message) => /Starting your scenario/.test(message)));
  await view.get("scenario-form").listeners.submit({ preventDefault() {} });
  release();
  await first;
  const starts = view.requests.filter((request) => request.url === "/api/runs" && request.method === "POST");
  assert.equal(starts.length, 1);
  assert.equal(JSON.parse(starts[0].body).toolConsent, true);
});

test("saved projects without files or runs are explained and are not overwritten", async () => {
  const projects = [{ projectSlug: "record-only", status: "needs_attention", runId: null }];
  const view = await dashboard(fixture(), 5, { projects });
  readyBrief(view);
  view.get("project").value = "record-only";
  vm.runInContext("summarize()", view.context);
  assert.equal(view.get("launch").disabled, true);
  assert.equal(view.get("project-conflict").hidden, false);
  assert.match(view.get("project-conflict-message").textContent, /without a portal run/);
  assert.equal(view.get("open-existing").hidden, true);
  await view.get("scenario-form").listeners.submit({ preventDefault() {} });
  assert.equal(view.requests.filter((item) => item.method === "POST").length, 0);
  assert.equal(projects.length, 1);
});

test("opening an existing project is navigation only and preserves the new intake", async () => {
  const view = await dashboard();
  view.get("project").value = "finance-agent";
  view.get("prompt").value = "Keep this separate business idea";
  vm.runInContext("summarize()", view.context);
  assert.equal(view.get("open-existing").hidden, false);
  await view.get("open-existing").listeners.click({ preventDefault() {} });
  assert.equal(view.get("page-stage").textContent, "Build & validate");
  assert.equal(view.get("run-select").value, "run-2");
  assert.equal(view.get("project").value, "finance-agent");
  assert.equal(view.get("prompt").value, "Keep this separate business idea");
  assert.equal(view.get("tool-consent").checked, false);
  assert.equal(view.requests.filter((item) => item.method === "POST").length, 0);
});

test("existing project navigation keeps an older project outside the recent-run window selected", async () => {
  const archivedRun = { ...fixture(), id: "archived-run", request: { projectSlug: "older-project" } };
  const view = await dashboard(fixture(), 5, {
    projects: [{ projectSlug: "older-project", status: "waiting_for_user", runId: archivedRun.id }],
    archivedRun,
  });
  view.get("project").value = "older-project";
  vm.runInContext("summarize()", view.context);
  await view.get("open-existing").listeners.click({ preventDefault() {} });
  await vm.runInContext("refreshRuns()", view.context);
  assert.equal(view.get("run-select").value, archivedRun.id);
  assert.equal(vm.runInContext("currentRun.request.projectSlug", view.context), "older-project");
  assert.equal(view.requests.filter((item) => item.method === "POST").length, 0);
});

test("suggested new names fit the slug limit, skip occupied names and change only the target name", async () => {
  const slug = "a".repeat(40);
  const view = await dashboard(fixture(), 5, {
    projects: [slug, `${"a".repeat(38)}-2`].map((projectSlug) => ({
      projectSlug, status: "completed", runId: null,
    })),
  });
  readyBrief(view);
  view.get("project").value = slug;
  view.get("prompt").value = "An energy scenario";
  view.get("reuse-scenario").value = "finance-source";
  const before = vm.runInContext("request()", view.context);
  vm.runInContext("summarize()", view.context);
  view.get("new-project-name").listeners.click();
  const after = vm.runInContext("request()", view.context);
  assert.equal(after.projectSlug, `${"a".repeat(38)}-3`);
  assert.equal(after.projectSlug.length, 40);
  assert.deepEqual({ ...after, projectSlug: before.projectSlug }, { ...before });
  assert.equal(view.get("project").focused, true);
  assert.equal(view.get("project-conflict").hidden, true);
  assert.equal(view.get("launch").disabled, false);
  assert.equal(view.requests.filter((item) => item.method === "POST").length, 0);
});

test("launch refreshes project names to catch projects created in another tab without starting work", async () => {
  const projects = [];
  const view = await dashboard(fixture(), 5, { projects });
  readyBrief(view);
  projects.push({ projectSlug: "energy-operations", status: "completed", runId: null });
  await view.get("scenario-form").listeners.submit({ preventDefault() {} });
  assert.equal(view.get("launch").disabled, true);
  assert.equal(view.get("project-conflict").hidden, false);
  assert.match(view.get("error").textContent, /already exists/);
  assert.equal(view.get("project").value, "energy-operations");
  assert.equal(view.requests.filter((item) => item.method === "POST").length, 0);
});

test("a concurrent server-side duplicate returns recovery actions without clearing or renaming the intake", async () => {
  const view = await dashboard(fixture(), 5, {
    conflict: { projectSlug: "energy-operations", status: "waiting_for_user", runId: "existing-run" },
  });
  readyBrief(view);
  view.get("prompt").value = "Preserve the customer's brief";
  await view.get("scenario-form").listeners.submit({ preventDefault() {} });
  assert.equal(view.get("launch").disabled, true);
  assert.equal(view.get("project-conflict").hidden, false);
  assert.equal(view.get("open-existing").hidden, false);
  assert.equal(view.get("project").value, "energy-operations");
  assert.equal(view.get("prompt").value, "Preserve the customer's brief");
  assert.match(view.get("error").textContent, /already exists/);
  assert.equal(view.requests.filter((item) => item.method === "POST").length, 1);
});

test("project-list read failures are reported and never launch a scenario", async () => {
  const appearance = {};
  const view = await dashboard(fixture(), 5, appearance);
  readyBrief(view);
  appearance.projectsUnavailable = true;
  await view.get("scenario-form").listeners.submit({ preventDefault() {} });
  assert.match(view.get("error").textContent, /Project state could not be read/);
  assert.equal(view.requests.filter((item) => item.method === "POST").length, 0);
});

test("theme follows system preference and is applied before DOM content initializes", async () => {
  const { get, context, requests, domEvents } = await dashboard(fixture(), 5, { systemDark: true, loading: true });
  assert.equal(vm.runInContext("document.documentElement.dataset.theme", context), "dark");
  assert.equal(requests.length, 0);
  domEvents.DOMContentLoaded();
  await new Promise(setImmediate);
  assert.equal(get("theme-toggle")["aria-checked"], "true");
  assert.ok(requests.some((item) => item.url === "/api/catalog"));
});

test("theme switch is independent of execution and saves an explicit preference", async () => {
  const { get, context, storage, requests } = await dashboard();
  assert.equal(vm.runInContext("document.documentElement.dataset.theme", context), "light");
  const initial = requests.length;
  get("theme-toggle").listeners.click();
  assert.equal(vm.runInContext("document.documentElement.dataset.theme", context), "dark");
  assert.equal(get("theme-toggle")["aria-checked"], "true");
  assert.equal(storage.get("abcbuilder-theme"), "dark");
  get("theme-toggle").listeners.click();
  assert.equal(get("theme-toggle")["aria-checked"], "false");
  assert.equal(storage.get("abcbuilder-theme"), "light");
  assert.equal(requests.length, initial);
});

test("saved theme overrides system preference and follows changes from another tab", async () => {
  const { get, context, storage, events, media } = await dashboard(fixture(), 5, {
    systemDark: true, savedTheme: "light",
  });
  assert.equal(get("theme-toggle")["aria-checked"], "false");
  media.listener({ matches: true });
  assert.equal(vm.runInContext("document.documentElement.dataset.theme", context), "light");
  storage.set("abcbuilder-theme", "dark");
  events.storage({ key: "abcbuilder-theme" });
  assert.equal(get("theme-toggle")["aria-checked"], "true");
  storage.delete("abcbuilder-theme");
  events.storage({ key: null });
  media.listener({ matches: false });
  assert.equal(vm.runInContext("document.documentElement.dataset.theme", context), "light");
});

test("blocked theme storage is reported without blocking portal controls or switching", async () => {
  const { get, context, warnings } = await dashboard(fixture(), 5, { storageBlocked: true });
  assert.equal(get("theme-notice").hidden, false);
  assert.match(get("theme-notice").textContent, /this tab only/);
  get("theme-toggle").listeners.click();
  assert.equal(vm.runInContext("document.documentElement.dataset.theme", context), "dark");
  assert.equal(get("error").textContent, "");
  assert.equal(warnings.length, 2);
  assert.equal(get("run-select").children.length, 2);
});

test("invalid stored themes use system preference and log the invalid setting", async () => {
  const { context, warnings } = await dashboard(fixture(), 5, { savedTheme: "invalid", systemDark: true });
  assert.equal(vm.runInContext("document.documentElement.dataset.theme", context), "dark");
  assert.equal(warnings.length, 1);
});

test("workspace scrolling respects reduced-motion preferences", async () => {
  for (const reducedMotion of [false, true]) {
    const { get, context } = await dashboard(fixture(), 5, { reducedMotion });
    vm.runInContext("scrollToWorkspace()", context);
    assert.equal(get("workspace").scrollOptions.behavior, reducedMotion ? "instant" : "smooth");
  }
});

test("company palette and theme text/control contrast meet WCAG AA thresholds", () => {
  const css = fs.readFileSync(path.join(__dirname, "..", "..", "portal", "styles.css"), "utf8");
  const declarations = (block) => Object.fromEntries(
    Array.from(block.matchAll(/(--[\w-]+):\s*([^;]+);/g), (match) => [match[1], match[2].trim()]),
  );
  const light = declarations(css.match(/:root\s*\{([^}]+)\}/)[1]);
  const dark = { ...light, ...declarations(css.match(/:root\[data-theme="dark"\]\s*\{([^}]+)\}/)[1]) };
  for (const [name, value] of Object.entries({
    purple: "#8661c5", "expanded-teal": "#389a91", blue: "#0078d4", magenta: "#c03bc4",
    teal: "#49c5b1", "light-purple": "#c5b4e3", black: "#000000", white: "#ffffff",
    "blue-black": "#091f2e", "warm-white": "#fff8f3",
  })) assert.equal(light[`--ilt-${name}`], value);
  const luminance = (hex) => hex.slice(1).match(/../g)
    .map((value) => parseInt(value, 16) / 255)
    .map((value) => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4)
    .reduce((sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index], 0);
  for (const [theme, tokens] of Object.entries({ light, dark })) {
    const resolve = (name) => {
      const value = tokens[name];
      assert.ok(value, `Missing ${name}`);
      const reference = /^var\((--[\w-]+)\)$/.exec(value);
      return reference ? resolve(reference[1]) : value;
    };
    const check = (foreground, background, threshold) => {
      const values = [luminance(resolve(foreground)), luminance(resolve(background))].sort((a, b) => a - b);
      const ratio = (values[1] + 0.05) / (values[0] + 0.05);
      assert.ok(ratio >= threshold, `${theme}: ${foreground} on ${background} = ${ratio.toFixed(2)}`);
    };
    for (const background of ["--bg", "--panel", "--surface", "--input"]) {
      for (const foreground of ["--text", "--muted", "--link", "--purple", "--status-alert"])
        check(foreground, background, 4.5);
    }
    for (const [foreground, background] of [
      ["--accent", "--accent-surface"], ["--accent", "--panel"],
      ["--primary-text", "--primary-bg"], ["--badge-text", "--badge-bg"],
      ["--danger-text", "--danger-bg"], ["--muted", "--code-bg"],
    ]) check(foreground, background, 4.5);
    check("--control-border", "--input", 3);
    check("--accent-border", "--accent-surface", 3);
    check("--text", "--accent-surface", 4.5);
    check("--focus", "--accent-surface", 3);
    check("--focus", "--bg", 3);
  }
});

test("business units are multi-select and Generic is exclusive", async () => {
  const { get, query, context } = await dashboard();
  const generic = query('input[name="businessUnits"][value="generic"]')[0];
  const finance = query('input[name="businessUnits"][value="finance"]')[0];
  const it = query('input[name="businessUnits"][value="it"]')[0];
  assert.equal(generic.checked, true);
  finance.checked = true;
  get("businessUnits").listeners.change({ target: finance });
  assert.equal(generic.checked, false);
  it.checked = true;
  get("businessUnits").listeners.change({ target: it });
  assert.equal(get("summary-business-units").textContent, "Finance, IT");
  assert.deepEqual(Array.from(vm.runInContext("request().businessUnits", context)), ["finance", "it"]);
  generic.checked = true;
  get("businessUnits").listeners.change({ target: generic });
  assert.equal(finance.checked, false);
  assert.equal(it.checked, false);
});

test("reuse catalog preserves target scope and submits source digest without starting work", async () => {
  const { get, query, context, requests } = await dashboard();
  get("reuse-scenario").value = "finance-source";
  get("reuse-scenario").listeners.change();
  const body = vm.runInContext("request()", context);
  assert.equal(body.reuseScenarioId, "finance-source");
  assert.equal(body.reuseManifestDigest, "a".repeat(64));
  assert.equal(body.industry, "");
  assert.equal(query('input[name="businessUnits"][value="generic"]')[0].checked, true);
  assert.equal(get("summary-source").textContent, "finance-source");
  assert.match(get("reuse-description").textContent, /app\/data and validation are new/);
  await get("refresh-catalog").listeners.click({ preventDefault() {} });
  assert.ok(requests.every((item) => item.method === "GET"));
});

test("dashboard groups attempts and displays workflow decisions instead of process success", async () => {
  const { get, requests } = await dashboard();
  assert.equal(get("run-select").children.length, 2);
  assert.equal(get("run-select").value, "run-2");
  assert.equal(get("run-status").textContent, "waiting for user");
  assert.equal(get("stage-list").children.length, 9);
  assert.equal(get("hack-stage-list").children.length, 5);
  assert.equal(get("stage-list").children[0].children[1].textContent, "completed");
  assert.equal(get("stage-list").children[6].children[1].textContent, "Not authorized");
  assert.equal(get("decision-panel").hidden, false);
  assert.equal(get("decision-question").textContent, "Confirm the design?");
  assert.equal(get("compose").disabled, true);
  assert.equal(get("run-output").textContent, "raw CLI details");
  await get("refresh-runs").listeners.click({ preventDefault() {} });
  assert.ok(requests.every((request) => request.method === "GET"));
});

test("decision submission includes ID, revision and selected answer but no implicit deployment permission", async () => {
  const { get, requests } = await dashboard();
  get("decision-choice").value = "Confirm";
  get("tool-consent").checked = true;
  await get("answer-decision").listeners.click({ preventDefault() {} });
  const posted = requests.find((request) => request.method === "POST");
  assert.equal(posted.url, "/api/runs/run-2/continue");
  const body = JSON.parse(posted.body);
  assert.equal(body.revision, 5);
  assert.equal(body.decisionId, "design-1");
  assert.equal(body.choice, "Confirm");
  assert.equal(body.message, "Confirm");
  assert.equal(body.deploymentAuthorized, undefined);
});

test("saved scenario consent survives refresh without checking or authorizing new intake", async () => {
  const { get, requests } = await dashboard();
  assert.equal(get("workspace-consent-label").hidden, true);
  assert.match(get("local-consent-status").textContent, /authorized for this scenario/);
  assert.equal(get("tool-consent").checked, false);
  assert.equal(get("workspace-consent").checked, false);
  get("decision-choice").value = "Confirm";
  await get("answer-decision").listeners.click({ preventDefault() {} });
  const posted = requests.find((request) => request.method === "POST");
  assert.equal(JSON.parse(posted.body).toolConsent, false);
  assert.equal(get("workspace-consent-label").hidden, true);
  assert.equal(get("tool-consent").checked, false);
});

test("legacy workspace consent is explicit and cannot leak across scenarios or into intake", async () => {
  const run = fixture();
  run.project.localToolConsent = null;
  const { get, context } = await dashboard(run);
  assert.equal(get("workspace-consent-label").hidden, false);
  assert.equal(get("answer-decision").disabled, true);
  get("workspace-consent").checked = true;
  get("workspace-consent").listeners.change();
  assert.equal(get("tool-consent").checked, false);
  assert.equal(get("answer-decision").disabled, false);
  context.otherConsentRun = structuredClone(run);
  context.otherConsentRun.id = "other-run";
  context.otherConsentRun.request.projectSlug = "other-scenario";
  vm.runInContext("selectRun(otherConsentRun.id, otherConsentRun.request.projectSlug); renderRun(otherConsentRun)", context);
  assert.equal(get("workspace-consent").checked, false);
  assert.equal(get("answer-decision").disabled, true);
  assert.equal(get("tool-consent").checked, false);
});

test("revocation does not start a worker and makes explicit authorization necessary again", async () => {
  const { get, requests } = await dashboard();
  assert.equal(get("revoke-consent").hidden, false);
  await get("revoke-consent").listeners.click({ preventDefault() {} });
  const posted = requests.filter((request) => request.method === "POST");
  assert.equal(posted.length, 1);
  assert.equal(posted[0].url, "/api/runs/run-2/revoke-consent");
  assert.equal(get("workspace-consent-label").hidden, false);
  assert.equal(get("revoke-consent").hidden, true);
  assert.equal(get("answer-decision").disabled, true);
});

test("setup required replaces approval choices and retry cannot itself clear the blocker", async () => {
  const run = fixture();
  run.project.decisions = [];
  run.project.status = "setup_required";
  run.project.setupBlocker = {
    id: "setup-1", stage: "diagrams", kind: "prerequisite",
    action: "Repair Graphviz PATH outside the worker.", verification: "Render a PNG in the actual worker.",
  };
  run.project.stages.diagrams = { status: "blocked", summary: "dot unavailable" };
  const { get, requests } = await dashboard(run);
  assert.equal(get("run-status").textContent, "Setup required");
  assert.equal(get("setup-panel").hidden, false);
  assert.match(get("setup-action").textContent, /Graphviz/);
  assert.equal(get("decision-panel").hidden, true);
  assert.equal(get("instructions-panel").hidden, true);
  assert.equal(get("continue").disabled, true);
  assert.equal(get("retry-setup").disabled, false);
  await get("retry-setup").listeners.click({ preventDefault() {} });
  const posted = requests.find((request) => request.method === "POST");
  assert.equal(posted.url, "/api/runs/run-2/retry-setup");
  const body = JSON.parse(posted.body);
  assert.equal(body.decisionId, undefined);
  assert.equal(body.passed, undefined);
  assert.equal(body.toolConsent, false);
  assert.equal(get("setup-panel").hidden, false);
});

test("pending decision survives refresh, but choice is cleared for a different decision", async () => {
  const { get, context, run } = await dashboard();
  get("decision-choice").value = "Confirm";
  await vm.runInContext("refreshRuns()", context);
  assert.equal(get("decision-choice").value, "Confirm");
  run.project.decisions[0].id = "design-2";
  await vm.runInContext("refreshRuns()", context);
  assert.equal(get("decision-choice").value, "");
});

test("no generic decision card appears on zero-exit or legacy runs", async () => {
  const run = fixture();
  run.project.status = "needs_attention";
  run.project.decisions = [];
  const { get, context } = await dashboard(run);
  assert.equal(get("decision-panel").hidden, true);
  assert.match(get("project-summary").textContent, /no success was inferred/);
  run.project = null;
  await vm.runInContext("refreshRuns()", context);
  assert.equal(get("decision-panel").hidden, true);
  assert.match(get("project-summary").textContent, /no stages are inferred/);
});

test("CLI output stays inside an initially collapsed diagnostic disclosure", () => {
  const html = fs.readFileSync(path.join(__dirname, "..", "..", "portal", "index.html"), "utf8");
  assert.match(html, /<details>\s*<summary>Technical details and execution log<\/summary>[\s\S]*?id="run-output"/);
});

test("stale backend is surfaced instead of silently using the old runner contract", async () => {
  const { get, requests } = await dashboard(fixture(), 2);
  assert.equal(get("launch").disabled, true);
  assert.match(get("error").textContent, /Restart the local portal server/);
  assert.equal(requests.length, 1);
});

test("historical review never presents a live endpoint or independently passed checks", async () => {
  const run = fixture();
  run.review = {
    ready: true, evidenceType: "historical-user-attestation",
    fingerprint: "reviewed", applicationUrl: null, checks: {},
  };
  const { get } = await dashboard(run);
  assert.equal(get("app-link").hidden, true);
  assert.match(get("review-reason").textContent, /not independently verified/);
  assert.match(get("check-list").children[0].textContent, /granular checks unavailable/);
  assert.match(get("tested-label").textContent, /historical deployment attestation/);
  assert.equal(get("compose").disabled, true);
});

test("validated external composition replaces intermediate state without starting a job", async () => {
  const run = fixture();
  run.composition = { status: "packages_validated" };
  run.review = {
    ready: true, evidenceType: "historical-user-attestation", approval: { decision: "approved" },
    fingerprint: "reviewed", applicationUrl: null, checks: {},
  };
  const { get, requests } = await dashboard(run);
  assert.match(get("run-status").textContent, /Packages validated/);
  assert.equal(get("stage-list").children[6].children[1].textContent, "user attested");
  assert.equal(get("stage-list").children[8].children[1].textContent, "completed");
  for (const stage of get("hack-stage-list").children)
    assert.equal(stage.children[1].textContent, "completed");
  assert.equal(get("review-evidence").hidden, true);
  assert.equal(get("decision-panel").hidden, true);
  assert.ok(requests.every((request) => request.method === "GET"));
});

test("workflow navigation separates shape, build and actual hack artifacts", async () => {
  const run = fixture();
  run.artifacts = [{ path: "packages/hack/Instructions/01-challenge.md", group: "Learner materials",
    private: false, download: false }];
  const { get } = await dashboard(run);
  assert.equal(get("scenario-form").hidden, false);
  assert.equal(get("workspace").hidden, true);
  get("nav-build").listeners.click({ preventDefault() {} });
  assert.equal(get("scenario-form").hidden, true);
  assert.equal(get("build-details").hidden, false);
  assert.equal(get("review").hidden, true);
  assert.match(get("nav-build").className, /active/);
  get("nav-hack").listeners.click({ preventDefault() {} });
  assert.equal(get("build-details").hidden, true);
  assert.equal(get("review").hidden, false);
  assert.equal(get("hack-artifacts").hidden, false);
  assert.match(get("artifact-list").children[0].children[2].children[0].textContent, /01-challenge.md/);
  get("workspace-consent").checked = true;
  get("workspace-consent").listeners.change();
  assert.equal(get("tool-consent").checked, false);
});

test("document preview is authenticated inert text and clearly labels private coach material", async () => {
  const run = fixture();
  run.artifacts = [{ path: "packages/coach-guide/Finale.md", group: "Private coach guide",
    private: true, download: false }];
  const { get, requests } = await dashboard(run);
  await get("artifact-list").children[1].children[2].children[0].listeners.click({ preventDefault() {} });
  assert.equal(get("artifact-preview").hidden, false);
  assert.match(get("artifact-title").textContent, /^PRIVATE/);
  assert.equal(get("artifact-content").children[0].tag, "p");
  assert.equal(get("artifact-content").children[0].children[0], "<script>not executed</script>");
  const request = requests.find((item) => item.url.includes("/artifact?"));
  assert.match(request.headers.Authorization, /^Bearer /);
  assert.equal(request.method, "GET");
});

test("Markdown renders headings, lists, tables and code without allowing executable HTML or links", async () => {
  const { context, get } = await dashboard();
  const source = "# Title\n\n- **One**\n- Two\n\n| A | B |\n| --- | --- |\n| X | Y |\n\n```js\n<script>alert(1)</script>\n```\n\n[bad](javascript:alert)\n[good](https://example.com)\n";
  context.markdownSource = source;
  vm.runInContext("renderMarkdown(document.getElementById('preview-test'), markdownSource)", context);
  const blocks = get("preview-test").children;
  assert.deepEqual(blocks.map((item) => item.tag), ["h1", "ul", "table", "pre", "p", "p"]);
  assert.equal(blocks[3].children[0].textContent, "<script>alert(1)</script>");
  assert.equal(blocks[4].children[1].tag, "span");
  assert.equal(blocks[5].children[1].tag, "a");
  assert.equal(blocks[5].children[1].rel, "noopener noreferrer");
});

test("deliverables use three audience groups and preserve private labels on release archives", async () => {
  const run = fixture();
  run.artifacts = [
    { path: "packages/hack/index.md", group: "Learner materials", private: false, download: false },
    { path: "packages/participant/README.md", group: "Participant starter", private: false, download: false },
    { path: "packages/coach-guide/Finale.md", group: "Private coach guide", private: true, download: false },
    { path: "packages/validation/release/coach.zip", group: "Release downloads", private: true, download: true },
    { path: "packages/validation/release/hack.zip", group: "Release downloads", private: false, download: true },
  ];
  const { get } = await dashboard(run);
  const groups = get("artifact-list").children;
  assert.deepEqual(groups.map((group) => group.dataset.group), ["learner", "coach", "release"]);
  assert.equal(groups[0].children[2].children.length, 2);
  assert.equal(groups[1].children[2].children.length, 1);
  assert.equal(groups[2].children[2].children.length, 2);
  assert.match(groups[2].children[2].children[0].textContent, /^PRIVATE/);
  assert.match(groups[0].children[0].children[1].textContent, /Learner materials \(2\)/);
});
