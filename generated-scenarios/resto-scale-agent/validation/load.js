// Authorized deployment-only reservation/read load; inspect locally without making requests.
import http from "k6/http";
import { check, fail } from "k6";
import execution from "k6/execution";
import { Rate, Trend } from "k6/metrics";

const profiles = {
  normal: { reads: 40, writes: 10, duration: "30m" },
  burst: { reads: 140, writes: 10, duration: "5m" },
  soak: { reads: 20, writes: 5, duration: "2h" }
};
const profile = profiles[__ENV.PROFILE || "normal"];
if (!profile) throw new Error("PROFILE must be normal, burst or soak.");
const readLatency = new Trend("read_latency", true);
const writeLatency = new Trend("write_latency", true);
const unexpected = new Rate("unexpected_responses");
const base = (__ENV.TARGET_URL || "").replace(/\/$/, "");
const runId = __ENV.RUN_ID;
const start = Date.parse(`${__ENV.SERVICE_DATE}T00:00:00Z`);

export const options = {
  scenarios: Object.fromEntries(["reads", "writes"].map(kind => [kind, {
    executor: "constant-arrival-rate", exec: kind, rate: profile[kind], timeUnit: "1s",
    duration: profile.duration, preAllocatedVUs: kind === "reads" ? 250 : 30,
    maxVUs: kind === "reads" ? 250 : 30
  }])),
  thresholds: {
    read_latency: ["p(95)<=500"],
    write_latency: ["p(95)<=800"],
    unexpected_responses: ["rate<0.01"],
    dropped_iterations: ["count==0"],
    checks: ["rate==1"]
  }
};

export function setup() {
  if (!base.startsWith("https://") || !/^[a-zA-Z0-9-]{8,40}$/.test(runId || "") || !Number.isFinite(start))
    fail("Require the authorized HTTPS TARGET_URL, unique RUN_ID and unused SERVICE_DATE.");
  const response = http.get(`${base}/api/session/csrf`);
  if (response.status !== 200) fail(`CSRF setup failed: HTTP ${response.status}`);
  return {
    csrf: response.json("token"),
    cookies: Object.entries(response.cookies).flatMap(([name, values]) =>
      values.map(value => `${name}=${value.value}`)).join("; ")
  };
}

export function reads() {
  const response = http.get(`${base}/api/menu`);
  readLatency.add(response.timings.duration);
  unexpected.add(response.status !== 200);
  check(response, { "read returns real catalog": result => result.status === 200 && result.json().length === 12 });
}

export function writes(data) {
  const index = execution.scenario.iterationInTest;
  const date = new Date(start + Math.floor(index / 1250) * 86400000).toISOString().slice(0, 10);
  const response = http.post(`${base}/api/reservations`, JSON.stringify({
    slot: `${date}:${Math.floor(index / 250) % 5 + 1}`,
    floor: Math.floor(index / 50) % 5 + 1, seats: 1, guestId: "guest-001", requestId: `${runId}-${index}`
  }), { headers: { "Content-Type": "application/json", "X-CSRF-TOKEN": data.csrf, Cookie: data.cookies } });
  writeLatency.add(response.timings.duration);
  unexpected.add(response.status !== 200);
  check(response, { "reservation has durable identity": result => result.status === 200 && Boolean(result.json("visitId")) });
}

export function handleSummary(data) {
  return { [__ENV.SUMMARY_PATH || "load-summary.json"]: JSON.stringify(data, null, 2) };
}
