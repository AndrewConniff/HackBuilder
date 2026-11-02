const form = document.getElementById("chat");
const button = document.getElementById("send");
const result = document.getElementById("result");
const answer = document.getElementById("answer");
const evidence = document.getElementById("evidence");
form.addEventListener("submit", async (event) => {
    event.preventDefault();
    button.disabled = true;
    result.setAttribute("aria-busy", "true");
    answer.textContent = "Consulting the brokerage education agent...";
    evidence.textContent = "";
    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: document.getElementById("message").value }),
            signal: AbortSignal.timeout(65000)
        });
        if (!response.ok) {
            answer.textContent = `Request failed (${response.status}). No answer was produced. Please retry later.`;
            return;
        }
        const reply = await response.json();
        answer.textContent = reply.answer;
        evidence.textContent =
            `Sources: ${reply.sources.join(", ") || "none cited"} | Correlation: ${reply.correlationId} ` +
            `| Agent response: ${reply.agentResponseId} | SHA-256: ${reply.digest}`;
    } catch (error) {
        answer.textContent = error.name === "TimeoutError"
            ? "The request timed out. No answer was produced."
            : "The connection failed. No answer was produced.";
    } finally {
        button.disabled = false;
        result.setAttribute("aria-busy", "false");
    }
});
