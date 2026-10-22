"use strict";

const $ = (id) => document.getElementById(id);
const bootstrap = new URLSearchParams(location.hash.slice(1)).get("token");
if (bootstrap) {
  sessionStorage.setItem("hackbuilder-token", bootstrap);
  history.replaceState(null, "", location.pathname);
}
let catalog;
let currentRun;
let timer;
let previewText = "";

function showStage(stage, updateHash = true) {
  const shape = stage === "shape";
  $("intake").hidden = !shape;
  $("scenario-form").hidden = !shape;
  if (!shape) $("preview-panel").hidden = true;
  $("workspace").hidden = shape;
  $("build-details").hidden = stage !== "build";
  $("review").hidden = stage !== "hack";
  const title = { shape: "Shape the scenario", build: "Build & validate", hack: "Compose the hack" }[stage];
  $("page-stage").textContent = title;
  $("workspace-title").textContent = title;
  for (const name of ["shape", "build", "hack"]) {
    $("nav-" + name).className = `nav-item${name === stage ? " active" : ""}`;
    $("nav-" + name).setAttribute("aria-current", name === stage ? "step" : "false");
  }
  if (updateHash) history.replaceState(null, "", { shape: "#intake", build: "#workspace", hack: "#review" }[stage]);
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
      headers: { Authorization: `Bearer ${sessionStorage.getItem("hackbuilder-token") || ""}` },
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
      Authorization: `Bearer ${sessionStorage.getItem("hackbuilder-token") || ""}`,
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const value = await response.json();
  if (!response.ok)
    throw new Error(value.error || `Request failed (${response.status}).`);
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

function summarize() {
  const data = request();
  $("summary-industry").textContent = data.industry || "Choose one industry";
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
  $("launch").disabled =
    !data.toolConsent ||
    !catalog.cliAvailable ||
    currentRun?.status === "running";
  $("compose").disabled =
    !$("tested").checked ||
    !$("approval").value.trim() ||
    !$("tool-consent").checked ||
    !currentRun?.review?.ready ||
    currentRun.status === "running" ||
    Boolean(currentRun.discovered);
}

function renderRun(run) {
  const previousDecisionId = pendingDecision()?.id;
  const changed =
    currentRun?.id !== run.id ||
    currentRun?.review?.fingerprint !== run.review?.fingerprint;
  currentRun = run;
  if (changed) {
    $("tested").checked = false;
    $("approval").value = "";
  }
  $("run-empty").hidden = true;
  $("run-details").hidden = false;
  $("run-name").textContent = `${run.request.projectSlug} / ${run.kind}`;
  const project = run.project;
  const historical = run.review?.evidenceType === "historical-user-attestation";
  const packaged = run.composition?.status === "packages_validated";
  const approved = run.review?.approval?.decision === "approved";
  if (changed) {
    $("artifact-preview").hidden = true;
    $("reference-content").hidden = true;
  }
  $("run-status").textContent = run.discovered && !packaged
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
    run.discovered
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
  $("run-output").textContent =
    run.output || run.error || "Starting the local Copilot CLI…";
  $("stop").hidden = run.status !== "running";
  const decision = pendingDecision();
  const canAct = !run.discovered && !project?.writer && run.status !== "running" && run.kind !== "composition";
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
  clearTimeout(timer);
  timer = setTimeout(() => refreshRuns().catch(showError), 3000);
}

async function loadRun(id) {
  renderRun(await api(`/api/runs/${id}`));
}

async function refreshRuns(selectId) {
  const runs = await api("/api/runs");
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
  const id = selectId || scenarios.find(
    (run) => run.request.projectSlug === currentRun?.request.projectSlug,
  )?.id || scenarios[0]?.id;
  if (id) {
    $("run-select").value = id;
    await loadRun(id);
  }
}

async function preview() {
  const value = await api("/api/preview", request());
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
  const body = {
    message: $("decision").value,
    toolConsent: $("tool-consent").checked,
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
  const run = await api(`/api/runs/${currentRun.id}/${kind}`, body);
  await refreshRuns(run.id);
  $("decision").value = "";
  showStage(kind === "compose" ? "hack" : "build");
  $("workspace").scrollIntoView({ behavior: "smooth" });
}

async function initialize() {
  catalog = await api("/api/catalog");
  if (catalog.workflowVersion !== 1)
    throw new Error("Restart the local portal server to load the workflow dashboard, then reload this page.");
  for (const item of catalog.industries)
    $("industries").append(choice(item, "industry", "radio"));
  for (const name of ["services", "pillars", "domains"]) {
    for (const item of catalog[name]) $(name).append(choice(item, name));
  }
  $("connection").textContent = catalog.cliAvailable
    ? "Local CLI detected"
    : "Install Copilot CLI";
  $("workspace-consent").checked = $("tool-consent").checked;
  $("workspace-consent").addEventListener("change", () => {
    $("tool-consent").checked = $("workspace-consent").checked;
    summarize();
  });
  $("tool-consent").addEventListener("change", () => {
    $("workspace-consent").checked = $("tool-consent").checked;
  });
  for (const [name, hash] of [["shape", "#intake"], ["build", "#workspace"], ["hack", "#review"]]) {
    $("nav-" + name).addEventListener("click", (event) => {
      event.preventDefault();
      showStage(name);
    });
  }
  showStage(location.hash === "#review" ? "hack" : location.hash === "#workspace" ? "build" : "shape", false);
  $("scenario-form").addEventListener("input", summarize);
  $("review").addEventListener("input", summarize);
  $("scenario-form").addEventListener(
    "submit",
    action(async () => {
      const run = await api("/api/runs", request());
      await refreshRuns(run.id);
      showStage("build");
      $("workspace").scrollIntoView({ behavior: "smooth" });
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
      if ($("run-select").value) await loadRun($("run-select").value);
    }),
  );
  for (const kind of ["continue", "revise", "compose", "stop"]) {
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
    for (const input of document.querySelectorAll('input[name="services"]'))
      input.checked = ["foundry", "cosmos-db", "managed-identity"].includes(
        input.value,
      );
    for (const input of document.querySelectorAll('input[name="pillars"]'))
      input.checked = ["security", "reliability"].includes(input.value);
    summarize();
  });
  summarize();
  await refreshRuns();
}

initialize().catch((error) => {
  $("connection").textContent = "Connection required";
  $("launch").disabled = true;
  showError(error);
});
