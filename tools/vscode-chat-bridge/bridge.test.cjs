const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

async function fixture(t, { opened, link } = {}) {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "abc-chat-"));
  t.after(() => fs.rm(root, { recursive: true, force: true }));
  await fs.mkdir(path.join(root, "scripts"));
  await fs.writeFile(path.join(root, "scripts", "portal_visualizer.py"), "");
  const calls = [];
  const vscode = {
    workspace: { isTrusted: true, workspaceFolders: [{ uri: { fsPath: root } }] },
    Uri: { parse: (value) => value },
    commands: {
      executeCommand: async (...args) => { calls.push(args); return opened; },
      registerCommand: () => ({ dispose() {} }),
    },
    window: {
      showInputBox: async () => link,
      showInformationMessage: async () => {},
      showWarningMessage: async () => "Replace link",
      registerUriHandler: () => ({ dispose() {} }),
    },
  };
  const context = vm.createContext({
    require: (name) => name === "vscode" ? vscode : require(name), module: { exports: {} }, URL, URLSearchParams,
  });
  vm.runInContext(await fs.readFile(path.join(__dirname, "extension.js"), "utf8"), context);
  const bridge = context.module.exports;
  const directory = path.join(root, ".abcbuilder-portal", "scenarios", "test-scenario");
  const uri = (action, overrides = {}) => ({
    path: `/${action}`,
    query: new URLSearchParams({
      root, project: "test-scenario", phase: "scenario", request: "a".repeat(32), ...overrides,
    }).toString(),
  });
  return { root, bridge, calls, vscode, directory, uri };
}

test("Only native chat session links are accepted", async (t) => {
  const { bridge } = await fixture(t);
  assert.equal(bridge.validateLink("agent-host-session://copilot/one?chat=main"), "agent-host-session://copilot/one?chat=main");
  for (const value of ["https://example.test", "command:delete", "vscode://other/run", "", undefined,
    "agent-host-session://copilot/one\nagent-host-session://copilot/two"]) {
    assert.throws(() => bridge.validateLink(value));
  }
});

test("Linking persists only the selected phase and reopening uses the saved chat, without a prompt", async (t) => {
  const link = "agent-host-session://copilot/existing?chat=main";
  const { bridge, calls, directory, uri } = await fixture(t, { link });
  await bridge.handleUri(uri("link"));
  const saved = JSON.parse(await fs.readFile(path.join(directory, "chat-sessions.json")));
  assert.equal(saved.sessions.scenario.resource, link);
  assert.equal(saved.sessions.composition, undefined);
  await bridge.handleUri(uri("open"));
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], "vscode.open");
  assert.equal(calls[0][1], link);
  const receipt = JSON.parse(await fs.readFile(path.join(directory, "chat-open", `${"a".repeat(32)}.json`)));
  assert.equal(receipt.status, "opened");
});

test("Missing links, native open failures, workspace mismatches and untrusted workspaces fail explicitly", async (t) => {
  const { bridge, calls, directory, uri, vscode } = await fixture(t, {
    link: "agent-host-session://copilot/existing", opened: false,
  });
  await assert.rejects(bridge.handleUri(uri("open")), /Paste one session link/);
  assert.equal(calls.length, 0);
  await bridge.handleUri(uri("link"));
  await assert.rejects(bridge.handleUri(uri("open")), /could not reopen/);
  const receipt = JSON.parse(await fs.readFile(path.join(directory, "chat-open", `${"a".repeat(32)}.json`)));
  assert.equal(receipt.status, "failed");
  await assert.rejects(bridge.handleUri(uri("open", { project: "../other" })), /valid.*slug/);
  await assert.rejects(bridge.handleUri(uri("open", { root: path.join(directory, "other") })), /repository/);
  vscode.workspace.isTrusted = false;
  await assert.rejects(bridge.handleUri(uri("open")), /Trust this workspace/);
});

test("Native activation probe acknowledges readiness without reading or opening a conversation", async (t) => {
  const { bridge, calls, directory, uri } = await fixture(t);
  await bridge.handleUri(uri("ping"));
  assert.equal(calls.length, 0);
  const receipt = JSON.parse(await fs.readFile(path.join(directory, "chat-open", `${"a".repeat(32)}.json`)));
  assert.equal(receipt.status, "ready");
  assert.equal(receipt.version, "0.1.0");
});
