// Verify the active portal's appearance, wording and scenario handoffs.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "..", "portal", "visualizer.js"), "utf8");
const markdownSource = fs.readFileSync(path.join(__dirname, "..", "..", "portal", "markdown.js"), "utf8");
const html = fs.readFileSync(path.join(__dirname, "..", "..", "portal", "visualizer.html"), "utf8");
const css = fs.readFileSync(path.join(__dirname, "..", "..", "portal", "visualizer.css"), "utf8");
const catalogPatterns = JSON.parse(
  fs.readFileSync(path.join(__dirname, "..", "..", "portal", "catalog.json"), "utf8"),
).agenticPatterns;
const industries = [...new Set(fs.readFileSync(
  path.join(__dirname, "..", "..", "microsoft_industry_verticals.csv"), "utf8",
).trim().split(/\r?\n/).slice(1).map((line) => line.split(",")[0]))];

class Element {
  constructor(tag = "div") {
    this.tag = tag;
    this.value = "";
    this.checked = false;
    this.hidden = true;
    this.dataset = {};
    this.listeners = {};
    this.children = [];
    this.textContent = "";
  }
  addEventListener(name, handler) { this.listeners[name] = handler; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  add(child) { this.append(child); }
  setAttribute(name, value) { this[name] = value; }
  focus() { this.focused = true; }
  scrollIntoView() { this.scrolled = true; }
}

async function portal({ saved = null, dark = false, storageError = null, items = [], files = [],
  patterns = catalogPatterns, backendVersion = 15, review = { available: false }, fileText = "",
  systemReady = true, systemFailure = false, identityFailure = false, hash = "" } = {}) {
  const elements = new Map();
  const get = (id) => {
    if (!elements.has(id)) {
      const element = new Element();
      if (id === "create") element.disabled = true;
      elements.set(id, element);
    }
    return elements.get(id);
  };
  const inputs = (name) => {
    const found = [];
    const visit = (element) => {
      if (element.tag === "input" && element.name === name) found.push(element);
      for (const child of element.children || []) visit(child);
    };
    for (const element of elements.values()) visit(element);
    return found;
  };
  const queryInputs = (selector) => {
    const match = selector.match(/^input\[name="([^"]+)"\](:checked)?$/);
    return match ? inputs(match[1]).filter((input) => !match[2] || input.checked) : [];
  };
  const storage = new Map(saved === null ? [] : [["abcbuilder-theme", saved]]);
  const listeners = {};
  const system = { matches: dark, addEventListener(name, handler) { this[name] = handler; } };
  const requests = [];
  const warnings = [];
  const location = { hash };
  let systemReport = null;
  let systemIdentity = null;
  const context = vm.createContext({
    document: {
      documentElement: new Element(), getElementById: get, createElement: (tag) => new Element(tag),
      createElementNS: (_, tag) => new Element(tag),
      querySelectorAll: queryInputs, querySelector: (selector) => queryInputs(selector)[0] || null,
      createTextNode: (value) => value,
    },
    matchMedia: () => system,
    addEventListener: (name, handler) => { listeners[name] = handler; },
    localStorage: {
      getItem(key) { if (storageError) throw storageError; return storage.get(key) ?? null; },
      setItem(key, value) { if (storageError) throw storageError; storage.set(key, value); },
      removeItem(key) { if (storageError) throw storageError; storage.delete(key); },
    },
    console: { warn: (...args) => warnings.push(args) },
    Option: function (name, value) { this.textContent = name; this.value = value; },
    URL,
    location,
    setInterval: () => {},
    fetch: async (url, options = {}) => {
      requests.push({ url, options });
      const data = options.body ? JSON.parse(options.body) : {};
      const services = ["foundry", "container-apps", "functions"];
      const profile = { services, buildMode: "local", localFunctions: true,
        loadTests: true, stages: { application: ["dotnet"] } };
      if (url === "/api/prerequisites/check") {
        if (systemFailure) return { ok: false, json: async () => ({ error: "Checker timed out." }) };
        systemReport = { ...profile, ready: systemReady, checkedAtUtc: "2026-10-24T22:00:00Z",
          checks: [{ id: "dotnet", name: ".NET SDK", ok: systemReady, detail: "SDK result", fix: systemReady ? "" : "Install SDK." }] };
      }
      if (url === "/api/system/identity") {
        if (identityFailure) return { ok: false, json: async () => ({ error: "CLI accounts differ." }) };
        systemIdentity = { status: "ready", checkedAtUtc: "now",
          identity: { scope: { account: "operator@example.test", tenantId: "tenant", subscriptionId: "sub" } } };
      }
      const body = url === "/api/catalog"
        ? { portalMode: "visualizer", industries, services: [
          { id: "foundry", name: "Foundry" }, { id: "container-apps", name: "Container Apps" },
        ], businessUnits: [], pillars: [], domains: [],
          agenticPatterns: patterns, backendEngineVersion: backendVersion }
        : url === "/api/prerequisites/plan" ? { plan: profile,
          checks: [{ id: "dotnet", name: ".NET SDK", state: "not-checked", stages: ["application"] }],
          report: systemReport && JSON.stringify(services) === JSON.stringify(systemReport.services) ? systemReport : null,
          identity: systemIdentity }
        : url === "/api/prerequisites/check" ? systemReport
        : url === "/api/system/identity" ? systemIdentity
        : url === "/api/handoff" ? { message: "Brief sent." }
        : url === "/api/chat-open" ? { message: "Existing scenario chat reopened automatically." }
        : url === "/api/open-package-folder" ? { message: "Opened package folder." }
        : url.startsWith("/api/review?") ? review
        : url === "/api/scenarios" ? items : files;
      return { ok: true, json: async () => body, text: async () => fileText };
    },
  });
  vm.runInContext(markdownSource, context);
  vm.runInContext(source, context);
  await new Promise(setImmediate);
  const change = (value) => { get("theme").value = value; get("theme").listeners.change(); };
  const theme = () => context.document.documentElement.dataset.theme;
  const choose = () => vm.runInContext('select("test-scenario")', context);
  const refresh = () => vm.runInContext("refresh()", context);
  const preview = (file) => vm.runInContext(`preview("test-scenario", ${JSON.stringify(file)})`, context);
  const render = (text) => {
    context.markdownText = text;
    vm.runInContext('renderMarkdown(document.getElementById("test-markdown"), markdownText)', context);
    return get("test-markdown");
  };
  const navigate = (view) => get(`nav-${view}`).listeners.click({ preventDefault() {} });
  const checkChoice = (name, value) => {
    const group = inputs(name);
    assert.ok(group.some((input) => input.value === value), `Missing ${name} choice: ${value}`);
    for (const input of group) input.checked = input.value === value;
    const input = group.find((entry) => entry.checked);
    if (input.listeners.change) input.listeners.change();
  };
  return { get, storage, listeners, system, requests, warnings, change, theme, choose, refresh, preview, render,
    navigate, location, checkChoice, inputs };
}

test("Four workflow views preserve the brief and selection without triggering execution", async () => {
  const ui = await portal({ items: [scenario("running")] });
  assert.equal(ui.get("view-create").hidden, false);
  assert.equal(ui.get("view-build").hidden, true);
  assert.equal(ui.get("project-switch").hidden, true);
  ui.get("prompt").value = "Customer story in progress";
  ui.navigate("build");
  await ui.choose();
  const requestCount = ui.requests.length;
  for (const view of ["hack", "system", "create", "build"]) {
    ui.navigate(view);
    for (const name of ["create", "build", "hack", "system"]) {
      assert.equal(ui.get(`view-${name}`).hidden, name !== view);
      assert.equal(ui.get(`nav-${name}`)["aria-current"], name === view ? "page" : "false");
    }
    assert.equal(ui.get("active-project").value, view === "hack" ? "" : "test-scenario");
    assert.equal(ui.get("project-switch").hidden, !["build", "hack"].includes(view));
    assert.equal(ui.get("prompt").value, "Customer story in progress");
    assert.equal(ui.location.hash, `#${view}`);
  }
  assert.equal(ui.requests.length, requestCount);
  assert.equal(ui.get("open-composition").hidden, true);
  assert.equal(ui.get("export-actions").hidden, true);
  assert.equal(ui.get("hack-detail").hidden, true);
  assert.equal(ui.get("hack-empty").hidden, false);
});

test("Hash navigation restores views and supports browser back/forward", async () => {
  const ui = await portal({ hash: "#system" });
  assert.equal(ui.get("view-system").hidden, false);
  ui.location.hash = "#hack";
  ui.listeners.hashchange();
  assert.equal(ui.get("view-hack").hidden, false);
  assert.equal(ui.get("hack-title-heading").focused, true);
  ui.location.hash = "#system";
  ui.listeners.hashchange();
  assert.equal(ui.get("view-system").hidden, false);
  ui.location.hash = "#not-a-view";
  ui.listeners.hashchange();
  assert.equal(ui.get("view-create").hidden, false);
});

test("Working scenario selector updates both workflow views and can clear selection", async () => {
  const ui = await portal({ items: [scenario("approved", { canCompose: true })] });
  ui.navigate("hack");
  ui.get("active-project").value = "test-scenario";
  await ui.get("active-project").listeners.change();
  assert.equal(ui.get("hack-detail").hidden, false);
  assert.equal(ui.get("hack-project-title").textContent, "Test scenario");
  assert.equal(ui.get("scenario").hidden, false);
  ui.get("active-project").value = "";
  await ui.get("active-project").listeners.change();
  assert.equal(ui.get("hack-detail").hidden, true);
  assert.equal(ui.get("hack-empty").hidden, false);
  assert.equal(ui.get("scenario").hidden, true);
});

test("Create hack offers ZIP exports and native package browsing instead of detailed file inventories", async () => {
  const item = scenario("completed", { canExport: true });
  item.packageFolder = "C:\\azd-projects\\test-scenario\\packages";
  const ui = await portal({ items: [item], fileText: "# Reference guide",
    files: [{ audience: "reference", path: "reference.md" },
      { audience: "learner", path: "learner.md" }, { audience: "coach", path: "coach.md" }] });
  await ui.choose();
  assert.equal(ui.get("files").children.length, 1);
  assert.equal(ui.get("files").children[0].children[1].textContent, "reference.md");
  assert.doesNotMatch(html, /id="hack-files"/);
  assert.equal(ui.get("package-folder-actions").hidden, false);
  assert.equal(ui.get("package-folder-path").textContent, item.packageFolder);
  ui.navigate("hack");
  assert.equal(ui.requests.some((entry) => entry.url === "/api/open-package-folder"), false);
  await ui.get("open-package-folder").listeners.click();
  const request = ui.requests.find((entry) => entry.url === "/api/open-package-folder");
  assert.deepEqual(JSON.parse(request.options.body), { projectSlug: "test-scenario" });
  assert.equal(ui.get("package-folder-status").textContent, "Opened package folder.");
  ui.navigate("system");
  assert.equal(ui.get("preview").hidden, true);
  ui.navigate("hack");
  assert.equal(ui.get("export-actions").hidden, false);
  ui.navigate("system");
  await ui.get("files").children[0].children[1].listeners.click();
  assert.equal(ui.get("preview").hidden, false);
  assert.equal(ui.get("preview-title").textContent, "reference.md");
  assert.equal(ui.get("preview").scrolled, true);
  ui.navigate("system");
  assert.equal(ui.get("preview").hidden, true);
});

test("Portal uses editor-neutral actions and explicit light/dark styling", () => {
  assert.match(html, /id="create" type="submit" disabled>Start building</);
  assert.match(html, /id="open-agent" type="button" hidden>Open scenario chat</);
  assert.match(html, /Create hack materials/);
  assert.doesNotMatch(html, /VS\s*Code/i);
  for (const value of ["system", "light", "dark"]) assert.match(html, new RegExp(`value="${value}"`));
  assert.match(css, /:root\[data-theme="dark"\]/);
  assert.match(css, /:root:not\(\[data-theme="light"\]\)/);
  assert.match(css, /\[hidden\]\s*\{\s*display:\s*none\s*!important;/);
});

test("Milestone checklist visibly preserves completion, pending work, timestamps and limitations", async () => {
  const item = scenario("approved", { canCompose: true });
  item.stages = [
    { id: "bicep", label: "Bicep infrastructure", status: "completed", summary: "Build passed",
      updatedAtUtc: "2026-10-25T00:00:00Z" },
    { id: "live-validation", label: "Live runtime validation", status: "completed",
      summary: "Functional pass; load target unmet" },
    { id: "review", label: "Scenario suitability approval", status: "completed", summary: "User approved" },
    { id: "hack-content", label: "Hack challenges", status: "not_reported", summary: "No completion report recorded." },
  ];
  const ui = await portal({ items: [item] });
  await ui.choose();
  assert.equal(ui.get("scenario-status").textContent, "Scenario approved");
  assert.equal(ui.get("stage-count").textContent, "3 of 3 milestones completed");
  const cards = ui.get("stage-history").children;
  assert.equal(cards.length, 3);
  assert.equal(cards[0].children[0].className, "milestone-icon");
  assert.equal(cards[0].children[0]["aria-hidden"], "true");
  assert.equal(cards[0].children[1].textContent, "Bicep infrastructure");
  assert.equal(cards[0].children[2].textContent, "Completed");
  assert.match(cards[0].children[4].textContent, /Reported:/);
  assert.equal(cards[1].children[3].textContent, "Functional pass; load target unmet");
  const hackRows = ui.get("hack-stage-history").children;
  assert.equal(hackRows.length, 1);
  assert.equal(hackRows[0].children[1].textContent, "Hack challenges");
  assert.equal(hackRows[0].children[2].textContent, "Not started / unreported");
  assert.equal(hackRows[0].dataset.status, "not_reported");
  assert.equal(ui.get("hack-stage-count").textContent, "0 of 1 milestones completed");
  ui.navigate("hack");
  assert.equal(ui.get("view-hack").hidden, false);
  await ui.refresh();
  assert.equal(ui.get("stage-history").children.length, 3);
  assert.equal(ui.get("hack-stage-history").children.length, 1);
  const section = html.slice(html.indexOf('aria-labelledby="stage-history-title"'), html.indexOf('id="next-action"'));
  assert.match(section, /id="stage-history"/);
  assert.doesNotMatch(section, /<details| hidden/);
});

test("All hack milestones and counts belong to Create hack, not the reference list", async () => {
  const item = scenario("approved", { canCompose: true });
  item.stages = ["requirements", "review", "hack-content", "hack-starter", "hack-coach", "hack-validation"]
    .map((id, index) => ({ id, label: id, status: index < 3 ? "completed" : "running", summary: id }));
  item.progress.steps = { requirements: { status: "completed", summary: "Story done" },
    "hack-content": { status: "completed", summary: "Challenges done" } };
  const ui = await portal({ items: [item] });
  await ui.choose();
  assert.equal(ui.get("stage-history").children.length, 2);
  assert.equal(ui.get("hack-stage-history").children.length, 4);
  assert.equal(ui.get("stage-count").textContent, "2 of 2 milestones completed");
  assert.equal(ui.get("hack-stage-count").textContent, "1 of 4 milestones completed");
  assert.equal(ui.get("steps").children.length, 1);
  for (const row of ui.get("stage-history").children) assert.doesNotMatch(row.children[1].textContent, /^hack-/);
  for (const row of ui.get("hack-stage-history").children) assert.match(row.children[1].textContent, /^hack-/);
  assert.ok(html.indexOf('id="hack-stage-history"') > html.indexOf('id="view-hack"'));
});

test("Milestone status icons retain text labels and respect reduced motion", async () => {
  const item = scenario("running");
  item.stages = ["running", "not_reported", "blocked", "failed", "waiting_for_user", "available"].map((status) => ({
    id: status, label: status, status, summary: "Recorded stage detail",
  }));
  const ui = await portal({ items: [item] });
  await ui.choose();
  const rows = ui.get("stage-history").children;
  assert.equal(rows[0].children[2].textContent, "Running");
  assert.equal(rows[1].children[0].textContent, "");
  assert.equal(rows[2].children[0].textContent, "!");
  assert.equal(rows[3].children[2].textContent, "Failed");
  assert.equal(rows[4].children[0].textContent, "?");
  assert.equal(rows[5].children[2].textContent, "Artifacts available");
  for (const row of rows) assert.equal(row.children[0]["aria-hidden"], "true");
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
  assert.match(css, /data-status="completed"\] \.milestone-icon\s*\{[^}]*background:\s*#217346/);
  assert.match(css, /\.stage-history\s*\{[^}]*list-style:\s*none/);
  assert.doesNotMatch(css, /\.stage-history\s*\{[^}]*grid-template-columns/);
});

test("System follows OS changes until an explicit choice and can be restored", async () => {
  const ui = await portal({ dark: true });
  assert.equal(ui.theme(), "dark");
  assert.equal(ui.get("theme").value, "system");
  ui.system.matches = false;
  ui.system.change();
  assert.equal(ui.theme(), "light");
  ui.change("dark");
  assert.equal(ui.theme(), "dark");
  assert.equal(ui.storage.get("abcbuilder-theme"), "dark");
  ui.system.change();
  assert.equal(ui.theme(), "dark");
  ui.change("system");
  assert.equal(ui.storage.has("abcbuilder-theme"), false);
  assert.equal(ui.theme(), "light");
});

test("Light and dark choices survive reloads and synchronize between tabs", async () => {
  for (const saved of ["light", "dark"]) {
    const ui = await portal({ saved, dark: saved === "light" });
    assert.equal(ui.theme(), saved);
    assert.equal(ui.get("theme").value, saved);
    ui.storage.set("abcbuilder-theme", saved === "dark" ? "light" : "dark");
    ui.listeners.storage({ key: "unrelated" });
    assert.equal(ui.theme(), saved);
    ui.listeners.storage({ key: "abcbuilder-theme" });
    assert.notEqual(ui.theme(), saved);
    ui.storage.clear();
    ui.listeners.storage({ key: null });
    assert.equal(ui.get("theme").value, "system");
  }
});

test("Invalid saved appearance is reported and falls back to the system", async () => {
  const ui = await portal({ saved: "invalid", dark: true });
  assert.equal(ui.theme(), "dark");
  assert.equal(ui.get("theme").value, "system");
  assert.equal(ui.warnings.length, 1);
});

test("Blocked or full browser storage leaves appearance usable and displays a notice", async () => {
  for (const name of ["SecurityError", "QuotaExceededError"]) {
    const ui = await portal({ storageError: { name } });
    ui.change("dark");
    assert.equal(ui.theme(), "dark");
    assert.equal(ui.get("theme-notice").hidden, false);
    assert.match(ui.get("theme-notice").textContent, /this tab only/);
    assert.equal(ui.get("error").hidden, true);
  }
});

test("Start building still saves the brief and explicitly hands off the scenario", async () => {
  const ui = await portal();
  ui.get("slug").value = "test-scenario";
  ui.checkChoice("industry", "Manufacturing & Mobility");
  ui.get("prompt").value = "Build a scenario.";
  ui.get("intake").listeners.submit({ preventDefault() {} });
  await new Promise(setImmediate);
  const saved = ui.requests.find((item) => item.url === "/api/scenarios" && item.options.method === "POST");
  assert.equal(JSON.parse(saved.options.body).projectSlug, "test-scenario");
  assert.equal(JSON.parse(saved.options.body).agenticPattern, "ai-decides");
  const handoff = ui.requests.find((item) => item.url === "/api/handoff");
  assert.deepEqual(JSON.parse(handoff.options.body), { projectSlug: "test-scenario", phase: "scenario" });
  assert.equal(ui.get("handoff-status").textContent, "Brief sent.");
  assert.equal(ui.get("create").disabled, false);
  assert.equal(ui.get("error").hidden, true);
});

test("Create form shows 18 numbered patterns plus Let AI decide outside advanced selections", async () => {
  const ui = await portal();
  const selector = ui.get("agentic-pattern");
  assert.equal(selector.children.length, 19);
  assert.equal(ui.inputs("agenticPattern").filter((input) => input.checked).length, 1);
  assert.equal(ui.inputs("agenticPattern")[0].checked, true);
  assert.equal(selector.children[0].children[1].textContent, "Let AI decide");
  assert.match(selector.children[1].children[1].textContent, /^01\. Single-Agent Tool Loop$/);
  assert.match(selector.children[18].children[1].textContent, /^18\. Adaptive Hybrid/);
  assert.ok(ui.inputs("agenticPattern").every((input) => input.type === "radio" && input.required));
  assert.match(ui.get("pattern-help").textContent, /customer scenario/);
  assert.ok(html.indexOf('id="agentic-pattern"') < html.indexOf("<details>"));
});

test("Every explicit pattern updates its explanation and is included unchanged in the submitted brief", async () => {
  for (const pattern of catalogPatterns.slice(1)) {
    const ui = await portal();
    ui.checkChoice("agenticPattern", pattern.id);
    assert.equal(ui.get("pattern-help").textContent, pattern.description);
    ui.get("slug").value = "test-scenario";
    ui.checkChoice("industry", "Manufacturing & Mobility");
    ui.get("prompt").value = "A fictional manufacturer's supply quality workflow.";
    ui.get("intake").listeners.submit({ preventDefault() {} });
    await new Promise(setImmediate);
    const saved = ui.requests.find((item) => item.url === "/api/scenarios" && item.options.method === "POST");
    assert.equal(JSON.parse(saved.options.body).agenticPattern, pattern.id);
    assert.equal(ui.get("view-build").hidden, false);
    assert.equal(ui.location.hash, "#build");
    assert.equal(ui.get("error").hidden, true);
    ui.checkChoice("agenticPattern", "ai-decides");
    assert.equal(ui.get("pattern-help").textContent, catalogPatterns[0].description);
  }
});

test("Every catalog industry has an icon and a required single-choice control, not a dropdown", async () => {
  const ui = await portal();
  assert.equal(ui.get("industry").children.length, industries.length);
  assert.ok(ui.inputs("industry").every((input) => input.type === "radio" && input.required && !input.checked));
  const iconPaths = new Set();
  for (const card of ui.get("industry").children) {
    const [input, icon, label] = card.children;
    assert.equal(label.textContent, input.value);
    assert.equal(icon.tag, "svg");
    assert.equal(icon["aria-hidden"], "true");
    assert.ok(icon.children[0].d);
    iconPaths.add(icon.children[0].d);
  }
  assert.equal(iconPaths.size, industries.length);
  for (const industry of industries) {
    ui.checkChoice("industry", industry);
    assert.equal(ui.inputs("industry").filter((input) => input.checked).length, 1);
    ui.get("slug").value = "test-scenario";
    ui.get("prompt").value = "A scenario.";
    ui.get("intake").listeners.submit({ preventDefault() {} });
    await new Promise(setImmediate);
    const saved = ui.requests.filter((item) => item.url === "/api/scenarios" && item.options.method === "POST").at(-1);
    assert.equal(JSON.parse(saved.options.body).industry, industry);
  }
  assert.doesNotMatch(html, /<select[^>]*id="(?:industry|agentic-pattern)"/);
  assert.match(css, /\.selection-card:has\(input:focus-visible\)/);
});

test("Missing industry selection reports an error without creating or handing off a scenario", async () => {
  const ui = await portal();
  ui.get("intake").listeners.submit({ preventDefault() {} });
  await new Promise(setImmediate);
  assert.match(ui.get("error").textContent, /Choose one industry/);
  assert.equal(ui.requests.some((item) => item.url === "/api/handoff"), false);
  assert.equal(ui.requests.some((item) => item.url === "/api/scenarios" && item.options.method === "POST"), false);
});

test("Missing or incomplete pattern catalog displays an explicit error rather than silently dropping choices", async () => {
  for (const patterns of [null, [], catalogPatterns.slice(0, 18)]) {
    const ui = await portal({ patterns });
    assert.equal(ui.get("error").hidden, false);
    assert.match(ui.get("error").textContent, /pattern catalog is unavailable or incomplete/);
    assert.equal(ui.get("create").disabled, true);
    assert.equal(ui.requests.some((item) => item.options.method === "POST"), false);
  }
});

test("An old server cannot silently discard the selected pattern", async () => {
  const ui = await portal({ backendVersion: 9 });
  assert.equal(ui.get("create").disabled, true);
  assert.equal(ui.get("error").hidden, false);
  assert.match(ui.get("error").textContent, /Restart the portal/);
});

test("System checklist starts unchecked and executes diagnostics only after explicit permission", async () => {
  const ui = await portal();
  assert.equal(ui.get("system-status").textContent, "Not checked");
  assert.equal(ui.get("system-checks").children.length, 1);
  assert.match(ui.get("system-checks").children[0].children[0].textContent, /Not checked/);
  assert.equal(ui.requests.some((item) => item.url === "/api/prerequisites/check"), false);
  await ui.get("system-check").listeners.click();
  assert.equal(ui.requests.some((item) => item.url === "/api/prerequisites/check"), false);
  ui.get("system-consent").checked = true;
  ui.get("system-consent").listeners.change();
  await ui.get("system-check").listeners.click();
  assert.equal(ui.get("system-status").textContent, "Sign-in not checked");
  assert.equal(ui.get("system-nav-status").textContent, "Sign-in not checked");
  const check = ui.requests.find((item) => item.url === "/api/prerequisites/check");
  assert.deepEqual(JSON.parse(check.options.body), { toolConsent: true });
  assert.match(ui.get("system-summary").textContent, /1\/1 checks passed/);
  await ui.get("system-identity").listeners.click();
  assert.equal(ui.get("system-status").textContent, "Ready");
  assert.equal(ui.get("system-nav-status").textContent, "Ready");
});

test("System is workspace-wide and selecting scenarios never changes or reruns its profile", async () => {
  const ui = await portal({ hash: "#system", items: [scenario("running")] });
  assert.equal(ui.get("project-switch").hidden, true);
  for (const id of ["system-scope", "system-build-mode", "system-local-functions"]) {
    assert.doesNotMatch(html, new RegExp(`id="${id}"`));
    assert.doesNotMatch(source, new RegExp(`\\$\\("${id}"\\)`));
  }
  const plans = () => ui.requests.filter((item) => item.url === "/api/prerequisites/plan");
  assert.deepEqual(JSON.parse(plans()[0].options.body), {});
  const before = plans().length;
  ui.navigate("build");
  await ui.choose();
  ui.navigate("system");
  assert.equal(plans().length, before);
  assert.equal(ui.get("project-switch").hidden, true);
});

test("System prerequisite failures show remedies, and command failures never look ready", async () => {
  for (const systemFailure of [false, true]) {
    const ui = await portal({ systemReady: false, systemFailure });
    ui.get("system-consent").checked = true;
    await ui.get("system-check").listeners.click();
    assert.equal(ui.get("system-status").textContent, systemFailure ? "Check failed" : "Needs attention");
    if (!systemFailure) {
      assert.match(ui.get("system-checks").children[0].children[2].textContent, /Install SDK/);
    } else assert.match(ui.get("system-summary").textContent, /timed out/);
  }
});

test("System sign-in check displays CLI-derived IDs without creating a deployment approval", async () => {
  const ui = await portal();
  ui.get("system-consent").checked = true;
  await ui.get("system-identity").listeners.click();
  assert.match(ui.get("system-identity-status").textContent, /tenant tenant; subscription sub/);
  assert.match(ui.get("system-identity-status").textContent, /No IDs need to be typed/);
  assert.equal(ui.get("system-status").textContent, "Not checked");
  assert.equal(ui.requests.some((item) => item.url === "/api/handoff"), false);
});

test("Successful sign-in cannot hide a failing toolchain", async () => {
  const ui = await portal({ systemReady: false });
  ui.get("system-consent").checked = true;
  await ui.get("system-check").listeners.click();
  await ui.get("system-identity").listeners.click();
  assert.equal(ui.get("system-status").textContent, "Needs attention");
  assert.equal(ui.get("system-nav-status").textContent, "Needs attention");
});

test("Failed Azure authentication prevents Ready even when all tools passed", async () => {
  const ui = await portal({ identityFailure: true });
  ui.get("system-consent").checked = true;
  await ui.get("system-check").listeners.click();
  await ui.get("system-identity").listeners.click();
  assert.equal(ui.get("system-status").textContent, "Needs attention");
  assert.match(ui.get("system-identity-status").textContent, /CLI accounts differ/);
});

test("Waiting review uses the one scenario chat action without submitting a new approval or a review prompt", async () => {
  const item = scenario("waiting_for_user");
  item.chatLinks = { scenario: true };
  const review = { available: true, path: "local-evidence/review/deployment-review.md",
    fingerprint: "review-fingerprint", text: "# Review\n\n**Read-only** preparation.\n\n- Choose the next step." };
  const ui = await portal({ items: [item], review });
  await ui.choose();
  assert.equal(ui.get("deployment-review").hidden, false);
  assert.equal(ui.get("review-path").textContent, review.path);
  assert.equal(ui.get("review-content").children[0].tag, "h1");
  assert.equal(ui.get("open-agent").hidden, false);
  ui.get("open-agent").listeners.click();
  await new Promise(setImmediate);
  const request = ui.requests.find((entry) => entry.url === "/api/chat-open");
  assert.deepEqual(JSON.parse(request.options.body), {
    projectSlug: "test-scenario", phase: "scenario",
  });
  assert.equal(ui.get("scenario-chat-link-status").textContent, "Existing scenario chat reopened automatically.");
  assert.match(ui.get("next-action").textContent, /Matching prior consent is reused/);
  item.progress.status = "running";
  await ui.refresh();
  assert.equal(ui.get("deployment-review").hidden, true);
  assert.equal(ui.get("open-agent").hidden, false);
});

test("Listed Markdown gets a formatted preview while HTML remains inert text", async () => {
  const ui = await portal({ items: [scenario("running")], fileText: "# Document\n<script>not executed</script>" });
  await ui.choose();
  await ui.preview("README.md");
  assert.equal(ui.get("preview-markdown").hidden, false);
  assert.equal(ui.get("preview-markdown").children[0].tag, "h1");
  assert.equal(ui.get("preview-text").hidden, true);
  await ui.preview("document.html");
  assert.equal(ui.get("preview-markdown").hidden, true);
  assert.equal(ui.get("preview-text").hidden, false);
  assert.match(ui.get("preview-text").textContent, /<script>/);
});

test("Shared Markdown renderer supports tables, escaped pipes, code and safe links without executing HTML", async () => {
  const ui = await portal();
  const target = ui.render("# Title\n\n| Host | Runtime |\n| --- | --- |\n| App | DOTNETCORE\\|10.0 |\n\n"
    + "```powershell\naz deployment sub what-if\n```\n\n- **First**\n- Second\n\n"
    + "<script>alert(1)</script>\n[unsafe](javascript:alert)\n[safe](https://example.com)\n[local](../secret.json)");
  const tags = [];
  const visit = (node) => {
    if (typeof node === "string") return;
    tags.push(node.tag);
    for (const child of node.children) visit(child);
  };
  visit(target);
  assert.ok(tags.includes("table"));
  assert.ok(tags.includes("pre"));
  assert.ok(tags.includes("ul"));
  assert.equal(tags.filter((tag) => tag === "a").length, 1);
  assert.equal(tags.includes("script"), false);
  const table = target.children.find((node) => node.tag === "table");
  const cells = table.children[1].children[0].children;
  assert.equal(cells.length, 2);
  assert.equal(cells[1].children[0], "DOTNETCORE|10.0");
  assert.doesNotMatch(markdownSource, /innerHTML|insertAdjacentHTML|document\.write/);
});

function scenario(status, actions = {}) {
  const approved = Boolean(actions.canCompose || actions.canExport);
  return { projectSlug: "test-scenario", title: "Test scenario", progress: { status, summary: "Latest report" },
    approval: { approved },
    stages: approved ? ["requirements", "architecture", "diagrams", "bicep", "application",
      "local-validation", "deployment", "live-validation", "review"]
      .map((id) => ({ id, label: id, status: "completed", summary: "Completed" })) : [],
    actions: { canContinue: false, canCompose: false, canExport: false, ...actions } };
}

test("Create hack lists only approved references with every prerequisite completed", async () => {
  const eligible = scenario("approved", { canCompose: true });
  const items = [eligible];
  const add = (item, slug) => { item.projectSlug = slug; items.push(item); };
  for (const id of eligible.stages.map((stage) => stage.id)) {
    for (const status of ["running", "blocked", "failed", "waiting_for_user", "available", "not_reported", "missing"]) {
      const item = scenario("approved", { canCompose: true });
      if (status === "missing") item.stages = item.stages.filter((stage) => stage.id !== id);
      else item.stages.find((stage) => stage.id === id).status = status;
      add(item, `${id}-${status}`);
    }
  }
  const unapproved = scenario("completed", { canExport: true });
  unapproved.approval.approved = false;
  add(unapproved, "stale-approval");
  const noApproval = scenario("approved", { canCompose: true });
  delete noApproval.approval;
  add(noApproval, "missing-approval");
  for (const status of ["saved", "unknown", "blocked", "running"]) add(scenario(status), status);
  const composing = scenario("running", {});
  composing.approval = eligible.approval;
  composing.stages = [...eligible.stages,
    { id: "hack-content", status: "running", summary: "Authoring challenges" }];
  add(composing, "composing");
  add(scenario("completed", { canExport: true }), "exportable");
  const ui = await portal({ items, hash: "#hack" });
  const slugs = () => ui.get("active-project").children.map((option) => option.value);
  assert.deepEqual(slugs(), ["", "test-scenario", "composing", "exportable"]);
  ui.navigate("build");
  assert.equal(slugs().length, items.length - 3 + 1);
  assert.equal(slugs().includes("test-scenario"), false);
  assert.equal(slugs().includes("composing"), false);
  assert.equal(slugs().includes("exportable"), false);
  ui.navigate("system");
  assert.equal(slugs().length, items.length + 1);
  assert.equal(ui.requests.some((entry) => ["/api/handoff", "/api/chat-link", "/api/scenarios"]
    .includes(entry.url) && entry.options.method === "POST"), false);
});

test("Validated hacks move to Create hack even when legacy granular reference reports are missing", async () => {
  const item = scenario("completed", { canExport: true });
  item.progress.stage = "hack-validation";
  item.composition = { status: "packages_validated" };
  item.stages = [{ id: "requirements", status: "available" }, { id: "review", status: "completed" },
    { id: "hack-validation", status: "completed" }];
  const ui = await portal({ items: [item], hash: "#build" });
  assert.equal(ui.get("active-project").children.length, 1);
  assert.equal(ui.get("board").children.length, 0);
  assert.equal(ui.get("hack-board").children.length, 1);
  assert.equal(ui.get("hack-board").children[0].children[0].textContent, "Ready to export (1)");
  ui.navigate("hack");
  assert.equal(ui.get("active-project").children[1].value, "test-scenario");
  await ui.get("hack-board").children[0].children[1].listeners.click();
  assert.equal(ui.get("hack-detail").hidden, false);
  ui.navigate("build");
  assert.equal(ui.get("active-project").value, "");
  assert.equal(ui.get("scenario").hidden, true);
  assert.equal(ui.get("open-agent").hidden, true);
  ui.navigate("hack");
  assert.equal(ui.get("active-project").value, "test-scenario");
  assert.equal(ui.get("hack-detail").hidden, false);
  for (const status of ["running", "failed", "blocked", "waiting_for_user"]) {
    item.stages[0].status = status;
    await ui.refresh();
    assert.equal(ui.get("active-project").children.length, 1);
    assert.equal(ui.get("hack-board").children.length, 0);
    assert.equal(ui.get("board").children.length, 1);
  }
  item.stages[0].status = "available";
  item.approval.approved = false;
  await ui.refresh();
  assert.equal(ui.get("hack-board").children.length, 0);
  item.approval.approved = true;
  item.composition.status = "stale";
  await ui.refresh();
  assert.equal(ui.get("hack-board").children.length, 0);
});

test("Create hack hides an ineligible selection and restores it in Build & validate", async () => {
  const item = scenario("blocked");
  const ui = await portal({ items: [item] });
  ui.navigate("build");
  await ui.choose();
  ui.navigate("hack");
  assert.equal(ui.get("active-project").value, "");
  assert.equal(ui.get("hack-detail").hidden, true);
  assert.equal(ui.get("hack-empty").hidden, false);
  assert.equal(ui.get("open-agent").hidden, true);
  assert.equal(ui.get("scenario-chat-link-status").hidden, true);
  ui.navigate("build");
  assert.equal(ui.get("active-project").value, "test-scenario");
  assert.equal(ui.get("scenario").hidden, false);
  assert.equal(ui.get("open-agent").hidden, false);
});

test("Polling adds completed references and removes newly blocked or stale approvals from Create hack", async () => {
  const item = scenario("blocked");
  const ui = await portal({ items: [item], hash: "#hack" });
  await ui.choose();
  assert.equal(ui.get("active-project").children.length, 1);
  Object.assign(item, scenario("approved", { canCompose: true }));
  await ui.refresh();
  assert.equal(ui.get("active-project").value, "test-scenario");
  assert.equal(ui.get("hack-detail").hidden, false);
  assert.equal(ui.get("open-agent").hidden, false);
  assert.equal(ui.get("board").children.length, 0);
  assert.equal(ui.get("hack-board").children.length, 1);
  item.stages.find((stage) => stage.id === "live-validation").status = "blocked";
  await ui.refresh();
  assert.equal(ui.get("active-project").children.length, 1);
  assert.equal(ui.get("active-project").value, "");
  assert.equal(ui.get("hack-detail").hidden, true);
  assert.equal(ui.get("open-agent").hidden, true);
  assert.equal(ui.get("board").children.length, 1);
  assert.equal(ui.get("hack-board").children.length, 0);
  item.stages.find((stage) => stage.id === "live-validation").status = "completed";
  item.approval.approved = false;
  await ui.refresh();
  assert.equal(ui.get("active-project").children.length, 1);
  assert.equal(ui.get("hack-detail").hidden, true);
});

test("Build and handoff states hide phase actions, exports and empty material groups", async () => {
  for (const status of ["running", "in_progress", "handed_off"]) {
    const ui = await portal({ items: [scenario(status)], files: [{ audience: "reference", path: "README.md" }] });
    await ui.choose();
    for (const id of ["open-composition", "scenario-actions",
      "learner-zip", "coach-zip", "export-actions", "export-help"]) {
      assert.equal(ui.get(id).hidden, true, `${status}: ${id}`);
    }
    assert.equal(ui.get("open-agent").hidden, false);
    assert.equal(ui.get("open-agent").textContent, "Open scenario chat");
    assert.equal(ui.get("scenario-status").textContent, status === "handed_off" ? "Starting" : "Building");
    assert.equal(ui.get("files").children.length, 1);
    assert.match(ui.get("next-action").textContent, /No action is needed|Check the agent chat/);
  }
});

test("Unstarted brief offers the single Start scenario chat action", async () => {
  const ui = await portal({ items: [scenario("saved", { canContinue: true })] });
  await ui.choose();
  assert.equal(ui.get("scenario-status").textContent, "Ready to start");
  assert.equal(ui.get("open-agent").hidden, false);
  assert.equal(ui.get("open-agent").textContent, "Start scenario chat");
  assert.equal(ui.get("open-composition").hidden, true);
  assert.match(ui.get("next-action").textContent, /building has not started/);
});

test("Approval unlocks composition, not exports or a second scenario build", async () => {
  const ui = await portal({ items: [scenario("waiting_for_user", { canCompose: true })] });
  await ui.choose();
  assert.equal(ui.get("open-agent").hidden, false);
  assert.equal(ui.get("open-composition").hidden, false);
  assert.equal(ui.get("export-actions").hidden, true);
  assert.match(ui.get("next-action").textContent, /Scenario approved/);
});

test("Open scenario chat automatically resolves an unlinked conversation without a Copy Link prompt", async () => {
  const item = scenario("blocked", { canContinue: true });
  item.chatLinks = { scenario: false };
  const ui = await portal({ items: [item] });
  await ui.choose();
  assert.match(ui.get("scenario-chat-link-status").textContent, /Automatically finds and reopens/);
  await ui.get("open-agent").listeners.click();
  const request = ui.requests.find((entry) => entry.url === "/api/chat-open");
  assert.deepEqual(JSON.parse(request.options.body), { projectSlug: "test-scenario", phase: "scenario" });
  assert.equal(ui.requests.some((entry) => entry.url === "/api/handoff"), false);
  assert.match(ui.get("scenario-chat-link-status").textContent, /reopened automatically/);
});

test("Single chat navigation follows the selected scenario across views and exposes no replacement action", async () => {
  const item = scenario("approved", { canCompose: true });
  item.chatLinks = { scenario: true };
  const ui = await portal({ items: [item] });
  await ui.choose();
  ui.navigate("hack");
  await ui.get("open-agent").listeners.click();
  const request = ui.requests.find((entry) => entry.url === "/api/chat-open");
  assert.equal("newChat" in JSON.parse(request.options.body), false);
  assert.deepEqual(JSON.parse(request.options.body), { projectSlug: "test-scenario", phase: "scenario" });
  assert.doesNotMatch(html, /id="(?:link-|replace-|continue-review)/);
  assert.equal((html.match(/id="open-agent"/g) || []).length, 1);
  assert.ok(html.indexOf('id="open-agent"') < html.indexOf('id="view-system"'));
});

test("Draft files do not unlock exports; current validation does, and a new build hides them again", async () => {
  const item = scenario("in_progress");
  const ui = await portal({ items: [item], files: [{ audience: "learner", path: "packages/hack/README.md" }] });
  await ui.choose();
  assert.equal(ui.get("learner-zip").hidden, true);
  item.progress.status = "completed";
  item.actions.canExport = true;
  await ui.refresh();
  assert.equal(ui.get("scenario-status").textContent, "Ready to export");
  assert.equal(ui.get("learner-zip").hidden, false);
  assert.equal(ui.get("coach-zip").hidden, true);
  assert.equal(ui.get("export-actions").hidden, false);
  item.progress.status = "running";
  item.actions.canExport = false;
  await ui.refresh();
  assert.equal(ui.get("export-actions").hidden, true);
  assert.equal(ui.get("learner-zip").hidden, true);
});
