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
  scrollIntoView() {}
}

function fixture() {
  const project = {
    revision: 5,
    status: "waiting_for_user",
    writer: null,
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

async function dashboard(run = fixture(), workflowVersion = 1) {
  const elements = new Map();
  const requests = [];
  const catalog = {
    industries: [{ id: "Financial Services", name: "Financial Services" }],
    services: [{ id: "foundry", name: "Foundry", required: true }],
    pillars: [], domains: [], cliAvailable: true, workflowVersion,
  };
  const get = (id) => {
    if (!elements.has(id)) elements.set(id, new Element(
      ["run-select", "decision-choice"].includes(id) ? "select" : "div",
    ));
    return elements.get(id);
  };
  const context = vm.createContext({
    document: { getElementById: get, querySelectorAll: () => [], createElement: (tag) => new Element(tag) },
    location: { hash: "", pathname: "/" }, history: { replaceState() {} },
    sessionStorage: { getItem: () => "local-test", setItem() {} },
    URL, URLSearchParams, clearTimeout() {}, setTimeout() { return 1; },
    Option: function (text, value) { this.textContent = text; this.value = value; },
    fetch: async (url, options) => {
      requests.push({ url, ...options });
      const value = url === "/api/catalog" ? catalog
        : url === "/api/runs" ? [
          run,
          { ...run, id: "run-1", startedAtUtc: "2026-10-22T18:00:00Z" },
        ] : url.includes("/artifact?") ? {
          path: "packages/coach-guide/Finale.md", text: "<script>not executed</script>\nPrivate answer",
        } : run;
      return { ok: true, json: async () => structuredClone(value) };
    },
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, "..", "..", "portal", "app.js"), "utf8"), context);
  await new Promise(setImmediate);
  return { get, context, requests, run };
}

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
  const { get, requests } = await dashboard(fixture(), 0);
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
  assert.equal(get("tool-consent").checked, true);
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
