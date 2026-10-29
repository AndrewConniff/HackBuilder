const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

async function fixture(t, { opened, link, submitError, activeChat = true, delayedChat = false,
  nativeOpener = true } = {}) {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "abc-chat-"));
  t.after(() => fs.rm(root, { recursive: true, force: true }));
  await fs.mkdir(path.join(root, "scripts"));
  await fs.writeFile(path.join(root, "scripts", "portal_visualizer.py"), "");
  const calls = [];
  const tabListeners = new Set();
  class TabInputChat {}
  const vscode = {
    workspace: { isTrusted: true, workspaceFolders: [{ uri: { fsPath: root } }] },
    Uri: { parse: (value) => value },
    commands: {
      executeCommand: async (...args) => {
        calls.push(args);
        assert.notEqual(args[0], "vscode.open", "Session links must use the native opener, not text-editor options");
        if (args[0] === "_workbench.open") {
          assert.equal(args[2], undefined);
          assert.equal(args[3], undefined);
          assert.equal(args[4].sideBySide, true);
          assert.equal(args[4].editorOptions.preserveFocus, false);
        }
        if (args[0] === "_workbench.open" && delayedChat) {
          setTimeout(() => {
            vscode.window.tabGroups.activeTabGroup.activeTab = { input: new TabInputChat() };
            for (const listener of tabListeners) listener();
          }, 10);
        }
        if (args[0] === "workbench.action.chat.submit" && submitError) throw submitError;
        return opened;
      },
      getCommands: async (filterInternal = false) => [
        "workbench.action.chat.submit", ...(!filterInternal && nativeOpener ? ["_workbench.open"] : []),
      ],
      registerCommand: () => ({ dispose() {} }),
    },
    window: {
      tabGroups: {
        activeTabGroup: { activeTab: { input: activeChat ? new TabInputChat() : {} } },
        onDidChangeTabs: (handler) => {
          tabListeners.add(handler);
          return { dispose: () => tabListeners.delete(handler) };
        },
        onDidChangeTabGroups: (handler) => {
          tabListeners.add(handler);
          return { dispose: () => tabListeners.delete(handler) };
        },
      },
      showInputBox: async () => link,
      showInformationMessage: async () => {},
      showWarningMessage: async () => "Replace link",
      registerUriHandler: () => ({ dispose() {} }),
    },
    TabInputChat,
    ViewColumn: { Beside: -2 },
  };
  const context = vm.createContext({
    require: (name) => name === "vscode" ? vscode : require(name), module: { exports: {} },
    URL, URLSearchParams, setTimeout, clearTimeout,
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
  assert.equal(calls[0][0], "_workbench.open");
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
  assert.equal(receipt.version, "0.2.3");
});

async function briefFixture(t, options = {}) {
  const value = await fixture(t, { link: "agent-host-session://copilot/existing", ...options });
  await value.bridge.handleUri(value.uri("link"));
  const text = "## Refined brief\n\nA synthetic grocery journey.\n";
  await fs.writeFile(path.join(value.directory, "scoping.md"), text);
  const response = {
    schemaVersion: 1, projectSlug: "test-scenario", decision: "confirmed", changes: "",
    fingerprint: require("node:crypto").createHash("sha256").update(text).digest("hex"),
    continuation: { requestId: "a".repeat(32), status: "pending" },
  };
  await fs.writeFile(path.join(value.directory, "scoping-response.json"), JSON.stringify(response));
  return { ...value, response, text };
}

test("Brief fingerprints match Python text reads across BOM and line endings", async (t) => {
  for (const newline of ["\n", "\r\n", "\r"]) {
    for (const bom of ["", "\uFEFF"]) {
      await t.test(`${JSON.stringify(newline)} with BOM=${Boolean(bom)}`, async (t) => {
        const { bridge, calls, directory, uri, text } = await briefFixture(t);
        await fs.writeFile(path.join(directory, "scoping.md"), bom + text.replace(/\n/g, newline));
        await bridge.handleUri(uri("continue"));
        assert.deepEqual(calls.map((entry) => entry[0]), ["_workbench.open", "workbench.action.chat.submit"]);
      });
    }
  }
});

test("Confirmation reuses the saved native conversation and dispatches a fixed normal-workflow continuation once", async (t) => {
  const { bridge, calls, directory, uri } = await briefFixture(t);
  await bridge.handleUri(uri("continue"));
  assert.deepEqual(calls.map((entry) => entry[0]), ["_workbench.open", "workbench.action.chat.submit"]);
  assert.equal(calls[0][1], "agent-host-session://copilot/existing");
  assert.equal(calls[0][4].sideBySide, true);
  assert.equal(calls[0][4].editorOptions.preserveFocus, false);
  const text = calls[1][1].inputValue;
  assert.match(text, /normal Start building workflow/);
  assert.match(text, /same|existing conversation/);
  assert.match(text, /grants no new Azure\/Entra/);
  assert.match(text, /architecture\/deployment review boundary/);
  assert.doesNotMatch(text, /mode:|autoApprove|disable.*permission/);
  await bridge.handleUri(uri("continue"));
  assert.equal(calls.length, 2);
  const receipt = JSON.parse(await fs.readFile(path.join(directory, "chat-open", `${"a".repeat(32)}.json`)));
  assert.equal(receipt.status, "dispatched");
});

test("Continuation waits for the exact reopened chat to become an editor before sending", async (t) => {
  const { bridge, calls, uri } = await briefFixture(t, { activeChat: false, delayedChat: true });
  await bridge.handleUri(uri("continue"));
  assert.deepEqual(calls.map((entry) => entry[0]), ["_workbench.open", "workbench.action.chat.submit"]);
  assert.equal(calls[0][4].sideBySide, true);
});

test("A missing native opener fails explicitly without submitting or acknowledging a reopen", async (t) => {
  const { bridge, calls, directory, uri } = await briefFixture(t, { nativeOpener: false });
  for (const action of ["open", "continue"]) {
    await assert.rejects(bridge.handleUri(uri(action)), /does not support native session-link/);
    const receipt = JSON.parse(await fs.readFile(path.join(directory, "chat-open", `${"a".repeat(32)}.json`)));
    assert.equal(receipt.status, "failed");
  }
  assert.equal(calls.length, 0);
});

test("Changes dispatch only a scoping revision; raw comments are read from the saved response, not executed", async (t) => {
  const { bridge, calls, directory, uri, response } = await briefFixture(t);
  response.decision = "changes_requested";
  response.changes = "Add delivery slots.";
  await fs.writeFile(path.join(directory, "scoping-response.json"), JSON.stringify(response));
  await bridge.handleUri(uri("continue"));
  const text = calls[1][1].inputValue;
  assert.match(text, /SCOPING ONLY/);
  assert.match(text, /fresh brief review/);
  assert.doesNotMatch(text, /normal Start building workflow/);
});

test("Stale fingerprints, mismatched request IDs and non-scenario continuations cannot submit", async (t) => {
  const { bridge, calls, directory, uri } = await briefFixture(t);
  await assert.rejects(bridge.handleUri(uri("continue", { request: "b".repeat(32) })), /response changed/);
  await assert.rejects(bridge.handleUri(uri("continue", { phase: "composition" })), /only.*scenario/);
  await fs.appendFile(path.join(directory, "scoping.md"), "Changed");
  await assert.rejects(bridge.handleUri(uri("continue")), /reviewed brief changed/);
  assert.equal(calls.length, 0);
});

test("Missing chat focus fails before submission and uncertain sends cannot be replayed", async (t) => {
  const unfocused = await briefFixture(t, { activeChat: false });
  await assert.rejects(unfocused.bridge.handleUri(unfocused.uri("continue")), /active chat editor/);
  assert.equal(unfocused.calls.filter((entry) => entry[0] === "workbench.action.chat.submit").length, 0);
  const uncertain = await briefFixture(t, { submitError: new Error("Editor disconnected during dispatch") });
  await assert.rejects(uncertain.bridge.handleUri(uncertain.uri("continue")), /disconnected/);
  await assert.rejects(uncertain.bridge.handleUri(uncertain.uri("continue")), /may already be queued/);
  assert.equal(uncertain.calls.filter((entry) => entry[0] === "workbench.action.chat.submit").length, 1);
});
