"use strict";

const vscode = require("vscode");
const fs = require("node:fs/promises");
const { existsSync } = require("node:fs");
const path = require("node:path");

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
  if (!folder) throw new Error("Open this scenario's ABC Builder repository in this editor window first.");
  await fs.access(path.join(folder.uri.fsPath, "scripts", "portal_visualizer.py"));
  return folder.uri.fsPath;
}

function statePath(root, slug) {
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug) || slug.length > 40) {
    throw new Error("Choose a valid ABC Builder scenario slug.");
  }
  const legacy = path.join(root, ".hackbuilder-portal");
  const current = path.join(root, ".abcbuilder-portal");
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

async function handleUri(uri) {
  const query = new URLSearchParams(uri.query);
  const root = await workspaceRoot(query.get("root"));
  const slug = query.get("project") || "";
  const phase = query.get("phase");
  if (!["scenario", "composition"].includes(phase)) throw new Error("Choose scenario or composition chat.");
  const directory = statePath(root, slug);
  if (uri.path === "/link") return linkChat(root, slug, phase);
  if (!["/open", "/ping"].includes(uri.path)) throw new Error("Unsupported ABC Builder chat action.");
  const request = query.get("request") || "";
  if (!/^[a-f0-9]{32}$/.test(request)) throw new Error("Invalid chat-open request.");
  const receipt = path.join(directory, "chat-open", `${request}.json`);
  if (uri.path === "/ping") return writeJson(receipt, { status: "ready", version: "0.1.0" });
  try {
    const data = await readSessions(directory);
    const resource = validateLink(data.sessions[phase]?.resource);
    const opened = await vscode.commands.executeCommand("vscode.open", vscode.Uri.parse(resource));
    if (opened === false) throw new Error("The editor could not reopen this chat. Relink an existing chat; no new one was created.");
    await writeJson(receipt, { status: "opened" });
  } catch (error) {
    await writeJson(receipt, { status: "failed", error: error.message });
    throw error;
  }
}

function activate(context) {
  const report = async (work) => {
    try { await work(); } catch (error) { await vscode.window.showErrorMessage(`ABC Builder chat: ${error.message}`); }
  };
  context.subscriptions.push(vscode.window.registerUriHandler({
    handleUri: (uri) => report(() => handleUri(uri)),
  }));
  context.subscriptions.push(vscode.commands.registerCommand("abcbuilder.linkChat", () => report(async () => {
    const root = await workspaceRoot();
    const slug = await vscode.window.showInputBox({ title: "ABC Builder scenario slug" });
    if (!slug) return;
    const phase = await vscode.window.showQuickPick(["scenario", "composition"], { title: "Conversation phase" });
    if (phase) await linkChat(root, slug, phase);
  })));
}

module.exports = { activate, validateLink, handleUri };
