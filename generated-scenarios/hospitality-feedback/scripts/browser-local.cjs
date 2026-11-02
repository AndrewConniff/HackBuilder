"use strict";
// Bounded local browser check; no Foundry response is mocked.
const { chromium } = require("../.tools/render/node_modules/playwright");
const fs = require("node:fs");
const path = require("node:path");
(async () => {
  const root = path.resolve(__dirname, "..");
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  const errors = [];
  page.on("pageerror", e => errors.push(e.message));
  try {
    await page.goto("http://127.0.0.1:5080", { waitUntil: "networkidle" });
    if (!(await page.title()).includes("Margie's Travel")) throw new Error("Wrong branding");
    await page.locator("#refresh").click();
    await page.waitForFunction(() => document.querySelector("#statuses").children.length >= 12);
    const rows = await page.locator("#statuses tr").allTextContents();
    if (!rows.every(row => row.includes("completed"))) throw new Error("Incomplete ingestion");
    await page.locator("#ask").click();
    await page.waitForFunction(() => document.querySelector("#chatStatus").textContent.includes("503"));
    const chatStatus = await page.locator("#chatStatus").textContent();
    if (!chatStatus.includes("Not successful")) throw new Error("Missing explicit dependency failure");
    if (errors.length) throw new Error(errors.join("\n"));
    fs.mkdirSync(path.join(root, "evidence"), { recursive: true });
    await page.screenshot({ path: path.join(root, "evidence/local-browser.png"), fullPage: true });
    const evidence = {
      status: "passed", scope: "local_browser_only", checkedAtUtc: new Date().toISOString(),
      url: "http://127.0.0.1:5080", localOnly: true,
      checks: { branding: true, ingestionStatus: true, missingFoundryReturns503: true, noPageErrors: true },
      liveAgentInvocation: false, liveModelInference: false, chatStatus
    };
    fs.writeFileSync(path.join(root, "evidence/browser-local.json"), JSON.stringify(evidence, null, 2) + "\n");
    console.log(JSON.stringify(evidence, null, 2));
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
