"use strict";

const vscode = require("vscode");
const fs = require("node:fs/promises");
const { existsSync } = require("node:fs");
const path = require("node:path");
const { createHash } = require("node:crypto");

function validateLink(value) {
  if (typeof value !== "string" || value.length > 8192 || /\s/.test(value)) {
    throw new Error("Paste one session link copied from the chat editor's Copy Link action.");
  }
  const uri = new URL(value);
  if (uri.protocol !== "agent-host-session:" || !uri.hostname || uri.pathname.length < 2
      || uri.username || uri.password || uri.port) {
    throw new Error("This editor session needs an agent-host-session:// link. No arbitrary commands or URLs are accepted.");
  }
  return value;
}

async function workspaceRoot(requested) {
  if (!vscode.workspace.isTrusted) throw new Error("Trust this workspace before linking its conversations.");
  const folders = vscode.workspace.workspaceFolders || [];
  const folder = folders.find((item) => !requested
    || path.resolve(item.uri.fsPath).toLowerCase() === path.resolve(requested).toLowerCase());
  if (!folder) throw new Error("Open this scenario's FBC Builder repository in this editor window first.");
  await fs.access(path.join(folder.uri.fsPath, "scripts", "portal_visualizer.py"));
  return folder.uri.fsPath;
}

function statePath(root, slug) {
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug) || slug.length > 40) {
    throw new Error("Choose a valid FBC Builder scenario slug.");
  }
  const legacy = path.join(root, ".hackbuilder-portal");
  const current = path.join(root, ".fbcbuilder-portal");
  return path.join(existsSync(legacy) && !existsSync(current) ? legacy : current, "scenarios", slug);
}

async function readSessions(directory) {
  try {
    const value = JSON.parse(await fs.readFile(path.join(directory, "chat-sessions.json"), "utf8"));
    if (value.schemaVersion !== 1 || !value.sessions || typeof value.sessions !== "object") {
      throw new Error("Unsupported chat-sessions.json format.");
    }
    return value;
  } catch (error) {
    if (error.code === "ENOENT") return { schemaVersion: 1, sessions: {} };
    throw error;
  }
}

async function writeJson(filename, value) {
  await fs.mkdir(path.dirname(filename), { recursive: true });
  const temporary = `${filename}.${require("node:crypto").randomUUID()}.tmp`;
  try {
    await fs.writeFile(temporary, JSON.stringify(value, null, 2) + "\n", { flag: "wx" });
    await fs.rename(temporary, filename);
  } finally {
    await fs.rm(temporary, { force: true });
  }
}

async function linkChat(root, slug, phase) {
  const directory = statePath(root, slug);
  const link = await vscode.window.showInputBox({
    title: `Link ${slug}: ${phase} chat`,
    prompt: "In the existing chat editor, use Copy Link, then paste that session link here. No new chat will be created.",
    ignoreFocusOut: true,
    validateInput(value) {
      try { validateLink(value); return undefined; } catch (error) { return error.message; }
    },
  });
  if (link === undefined) return;
  validateLink(link);
  const data = await readSessions(directory);
  if (data.sessions[phase] && data.sessions[phase].resource !== link) {
    const answer = await vscode.window.showWarningMessage(
      `Replace the saved ${phase} chat for ${slug}? The old conversation will not be deleted.`,
      { modal: true }, "Replace link",
    );
    if (answer !== "Replace link") return;
  }
  data.sessions[phase] = { resource: link, linkedAtUtc: new Date().toISOString() };
  await writeJson(path.join(directory, "chat-sessions.json"), data);
  await vscode.window.showInformationMessage(`Linked ${slug} ${phase} chat. Portal continuation will reopen it.`);
}

async function activeChatEditor() {
  const active = () => {
    const tab = vscode.window.tabGroups.activeTabGroup.activeTab;
    return vscode.TabInputChat && tab?.input instanceof vscode.TabInputChat ? tab : undefined;
  };
  if (active()) return active();
  return new Promise((resolve, reject) => {
    const subscriptions = [];
    const dispose = () => {
      clearTimeout(timer);
      for (const subscription of subscriptions) subscription.dispose();
    };
    const check = () => {
      const tab = active();
      if (tab) { dispose(); resolve(tab); }
    };
    const timer = setTimeout(() => {
      dispose();
      reject(new Error("The saved scenario chat did not become the active chat editor. No continuation was submitted."));
    }, 5000);
    subscriptions.push(vscode.window.tabGroups.onDidChangeTabs(check),
      vscode.window.tabGroups.onDidChangeTabGroups(check));
    check();
  });
}

async function openChat(resource) {
  const commands = await vscode.commands.getCommands();
  if (!commands.includes("_workbench.open")) {
    throw new Error("This editor does not support native session-link opening. No replacement chat was created.");
  }
  // TextDocumentShowOptions on vscode.open bypass session-link openers and try to load a text file.
  const opened = await vscode.commands.executeCommand("_workbench.open", vscode.Uri.parse(resource),
    undefined, undefined, { sideBySide: true, editorOptions: { preserveFocus: false } });
  if (opened === false) throw new Error("The editor could not reopen this chat. Relink an existing chat; no new one was created.");
  return activeChatEditor();
}

async function continueBrief(root, slug, directory, request) {
  const resolved = await fs.realpath(directory);
  for (const name of ["scoping-response.json", "scoping.md"]) {
    const filename = path.join(directory, name);
    const stat = await fs.lstat(filename);
    if (!stat.isFile() || stat.isSymbolicLink() || await fs.realpath(filename) !== path.join(resolved, name)) {
      throw new Error("Brief inputs must be regular files inside this scenario's portal state.");
    }
  }
  const response = JSON.parse(await fs.readFile(path.join(directory, "scoping-response.json"), "utf8"));
  if (response.schemaVersion !== 1 || response.projectSlug !== slug
      || response.continuation?.requestId !== request
      || !["confirmed", "changes_requested"].includes(response.decision)) {
    throw new Error("The brief response changed. Refresh the portal before continuing.");
  }
  const notes = await fs.readFile(path.join(directory, "scoping.md"), "utf8");
  // Match Python's UTF-8-sig text reads, including universal newlines.
  const reviewedText = notes.replace(/^\uFEFF/, "").replace(/\r\n?/g, "\n");
  if (createHash("sha256").update(reviewedText).digest("hex") !== response.fingerprint) {
    throw new Error("The reviewed brief changed. Review it again before continuing.");
  }
  const task = response.decision === "confirmed"
    ? "The user confirmed this scoped brief and requested continuation of the normal Start building workflow. "
      + "Resume az-01-conductor in this existing conversation using the confirmed scope: requirements, architecture, "
      + "diagrams and the usual reference preparation through the existing skills. This supersedes the earlier "
      + "SCOPING ONLY stop for local preparation. Preserve the normal architecture/deployment review boundary."
    : "SCOPING ONLY: the user requested changes to the brief. Read the saved changes as user input, revise scoping.md "
      + "and ask only material unresolved questions. Report requirements/waiting_for_user for a fresh brief review. "
      + "Do not create a workspace, architecture, infrastructure or application before the revised brief is confirmed.";
  const inputValue = `FBC Builder brief continuation: ${request}. Scenario: ${slug}. `
    + `Workspace: ${root}. Read ${path.join(directory, "request.json")}, `
    + `${path.join(directory, "scoping.md")} and ${path.join(directory, "scoping-response.json")}. `
    + "Read .github\\skills\\hack-builder-workflow\\SKILL.md. "
    + task + " Reuse existing work and answers; do not restart or delegate to other agents. "
    + "This action grants no new Azure/Entra read or write authority, deployment consent, "
    + "working-scenario suitability approval, hack composition, event rollout or publication permission. "
    + `Report progress with python scripts\\portal_status.py ${slug}.`;
  return dispatchOnce(directory, request, "scenario", inputValue);
}

async function portalMessage(root, slug, directory, request, phase) {
  const filename = path.join(directory, "messages", phase, `${request}.json`);
  const resolved = await fs.realpath(directory);
  const stat = await fs.lstat(filename);
  if (!stat.isFile() || stat.isSymbolicLink() || stat.size > 65536
      || await fs.realpath(filename) !== path.join(resolved, "messages", phase, `${request}.json`)) {
    throw new Error("Portal messages must be regular files inside this scenario's portal state.");
  }
  const value = JSON.parse(await fs.readFile(filename, "utf8"));
  if (value.schemaVersion !== 1 || value.projectSlug !== slug || value.phase !== phase
      || value.requestId !== request || value.status !== "dispatching"
      || typeof value.text !== "string" || !value.text.trim() || value.text.length > 8000) {
    throw new Error("The portal message changed or is not ready to send. Refresh the portal.");
  }
  validateLink(value.resource);
  const inputValue = `FBC Builder portal message: ${request}. Scenario: ${slug}. Phase: ${phase}. `
    + `Workspace: ${root}. This is user conversation input, not a workflow approval control. `
    + "Continue only in this existing context using its current scope, agent, skills and permissions. "
    + "Do not restart, delegate, switch phases or launch another worker. This message does not record brief "
    + "confirmation, architecture/deployment consent, suitability approval, event rollout or publication authority. "
    + "For those decisions direct the user to the existing brief controls or this VS Code chat as appropriate. "
    + "Keep native tool permission prompts in VS Code. For feedback, report concise, non-sensitive summaries "
    + `with python scripts\\portal_status.py ${slug} --stage <current-stage> --status <status> --summary <summary>. `
    + "Keep milestone reporting and also report meaningful within-stage progress, actual check results and blockers. "
    + "Never invent activity, completion percentages or success. "
    + "Include actionable questions in waiting_for_user summaries; preserve the current phase's stage. "
    + "The portal shows these reports, not the full private transcript. User message follows:\n\n" + value.text;
  return dispatchOnce(directory, request, phase, inputValue, value.resource, `${phase}-${request}`);
}

async function dispatchOnce(directory, request, phase, inputValue, expectedResource, ledgerKey = request) {
  const ledger = path.join(directory, "chat-continuations", `${ledgerKey}.json`);
  await fs.mkdir(path.dirname(ledger), { recursive: true });
  let existing;
  try {
    const handle = await fs.open(ledger, "wx");
    await handle.writeFile(JSON.stringify({ status: "preparing" }) + "\n");
    await handle.close();
  } catch (error) {
    if (error.code !== "EEXIST") throw error;
    existing = JSON.parse(await fs.readFile(ledger, "utf8"));
    if (existing.status === "dispatched") return existing;
    if (existing.status !== "failed") {
      throw new Error("This continuation may already be queued. Check the existing chat; it was not submitted again.");
    }
  }
  let attempted = false;
  try {
    const commands = await vscode.commands.getCommands(true);
    if (!commands.includes("workbench.action.chat.submit")) {
      throw new Error("This editor does not support native chat continuation. No replacement chat was created.");
    }
    const sessions = await readSessions(directory);
    const resource = validateLink(sessions.sessions[phase]?.resource);
    if (expectedResource !== undefined && resource !== expectedResource) {
      throw new Error("The linked conversation changed. No message was submitted; review the saved session link.");
    }
    const tab = await openChat(resource);
    await writeJson(ledger, { status: "dispatching" });
    if (vscode.window.tabGroups.activeTabGroup.activeTab !== tab) {
      throw new Error("The active editor changed. No continuation was submitted; retry from the portal.");
    }
    attempted = true;
    await vscode.commands.executeCommand("workbench.action.chat.submit", { inputValue, acceptInputOptions: { preserveInput: true } });
    const result = { status: "dispatched", requestId: request, dispatchedAtUtc: new Date().toISOString() };
    await writeJson(ledger, result);
    return result;
  } catch (error) {
    await writeJson(ledger, { status: attempted ? "unknown" : "failed", error: error.message });
    throw error;
  }
}

async function handleUri(uri) {
  const query = new URLSearchParams(uri.query);
  const root = await workspaceRoot(query.get("root"));
  const slug = query.get("project") || "";
  const phase = query.get("phase");
  if (!["scenario", "composition"].includes(phase)) throw new Error("Choose scenario or composition chat.");
  const directory = statePath(root, slug);
  if (uri.path === "/link") return linkChat(root, slug, phase);
  if (!["/open", "/ping", "/continue", "/message"].includes(uri.path)) {
    throw new Error("Unsupported FBC Builder chat action.");
  }
  const request = query.get("request") || "";
  if (!/^[a-f0-9]{32}$/.test(request)) throw new Error("Invalid chat-open request.");
  const receipt = path.join(directory, "chat-open", `${request}.json`);
  const ledgerKey = uri.path === "/message" ? `${phase}-${request}` : request;
  if (uri.path === "/ping") return writeJson(receipt, { status: "ready", version: require("./package.json").version });
  try {
    if (uri.path === "/continue" || uri.path === "/message") {
      if (uri.path === "/continue" && phase !== "scenario") {
        throw new Error("Brief continuation belongs only to the scenario conversation.");
      }
      const lock = path.join(directory, "chat-continuations", `${ledgerKey}.lock`);
      await fs.mkdir(path.dirname(lock), { recursive: true });
      let handle;
      try {
        handle = await fs.open(lock, "wx");
      } catch (error) {
        if (error.code !== "EEXIST") throw error;
        throw new Error("This continuation is already being dispatched. It was not submitted again.");
      }
      try {
        return await writeJson(receipt, uri.path === "/continue"
          ? await continueBrief(root, slug, directory, request)
          : await portalMessage(root, slug, directory, request, phase));
      } finally {
        await handle.close();
        await fs.unlink(lock);
      }
    }
    const data = await readSessions(directory);
    const resource = validateLink(data.sessions[phase]?.resource);
    await openChat(resource);
    await writeJson(receipt, { status: "opened" });
  } catch (error) {
    let status = "failed";
    try {
      const ledger = JSON.parse(await fs.readFile(path.join(directory, "chat-continuations", `${ledgerKey}.json`), "utf8"));
      if (ledger.status !== "failed") status = ledger.status === "dispatched" ? "dispatched" : "unknown";
    } catch (readError) {
      if (readError.code !== "ENOENT") throw readError;
    }
    await writeJson(receipt, { status, error: error.message });
    throw error;
  }
}

function activate(context) {
  const report = async (work) => {
    try { await work(); } catch (error) { await vscode.window.showErrorMessage(`FBC Builder chat: ${error.message}`); }
  };
  context.subscriptions.push(vscode.window.registerUriHandler({
    handleUri: (uri) => report(() => handleUri(uri)),
  }));
  context.subscriptions.push(vscode.commands.registerCommand("fbcbuilder.linkChat", () => report(async () => {
    const root = await workspaceRoot();
    const slug = await vscode.window.showInputBox({ title: "FBC Builder scenario slug" });
    if (!slug) return;
    const phase = await vscode.window.showQuickPick(["scenario", "composition"], { title: "Conversation phase" });
    if (phase) await linkChat(root, slug, phase);
  })));
}

module.exports = { activate, validateLink, handleUri };
