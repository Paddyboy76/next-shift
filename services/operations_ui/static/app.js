let spokenReceipt = null;
let mediaRecorder = null;
let recordedChunks = [];

const drawer = document.querySelector("#drawer");
const backdrop = document.querySelector("#drawer-backdrop");

const publicDemoHandover = "Synthetic night-shift handover for Tower 4: a standard wheelchair is missing from the Level 3 lift lobby. A Spanish interpreter is needed in Room 402. Home oxygen delivery to the synthetic discharge lounge is still pending. Room 418 needs EVS turnaround. The sink in Room 406 is leaking. Patient transport is waiting to move a guest from the discharge lounge to the north entrance.";

// Shared acceptance copy for the governed issue actions rendered by the
// frontline shell. Keeping these labels here preserves the public UI contract
// while deeplink.js remains the sole live-work renderer/poller.
const governedActionLabels = Object.freeze({
  recordEvidence: "Record synthetic trusted evidence",
  verify: "Run independent verifier",
});
window.nextShiftGovernedActionLabels = governedActionLabels;

function closeDrawer() {
  drawer.classList.add("hidden");
  backdrop.classList.add("hidden");
}

function intakeItemLabel(item, fallback) {
  if (!item || typeof item !== "object") return fallback;
  const title = typeof item.title === "string" && item.title.trim()
    ? item.title.trim()
    : fallback;
  const owner = typeof item.owner === "string" && item.owner.trim()
    ? ` (${item.owner.trim()})`
    : "";
  return `${title}${owner}`;
}

function intakeOutcomeText(payload) {
  if (payload?.blocked) return `Blocked by security policy: ${payload.message}`;

  const created = Array.isArray(payload?.issues) ? payload.issues : [];
  const held = Array.isArray(payload?.held_proposals) ? payload.held_proposals : [];

  if (!created.length && !held.length) return payload?.message || "Intake completed.";

  const outcomes = [
    ...created.map((item) => `${intakeItemLabel(item, "Operational issue")} — created`),
    ...held.map((item) => `${intakeItemLabel(item, "Operational issue")} — held for review`),
  ];

  const reviewSummary = typeof payload?.coverage_review?.summary === "string"
    ? payload.coverage_review.summary.trim()
    : "";

  return `${outcomes.join(" · ")}${reviewSummary ? `\n\nCoverage review: ${reviewSummary}` : ""}`;
}

document.querySelector("#drawer-close").addEventListener("click", closeDrawer);
backdrop.addEventListener("click", closeDrawer);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !drawer.classList.contains("hidden")) closeDrawer();
});

document.querySelector("#submit-handover").addEventListener("click", async () => {
  const button = document.querySelector("#submit-handover");
  const textarea = document.querySelector("#handover");
  const status = document.querySelector("#intake-status");
  const message = textarea.value.trim();
  if (!message) return;
  button.disabled = true;
  status.textContent = "Processing governed intake…";
  try {
    const response = await fetch("/api/intake", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, spoken_receipt: spokenReceipt }),
    });
    const raw = await response.text();
    let payload = null;
    if (raw) {
      try {
        payload = JSON.parse(raw);
      } catch (_error) {
        payload = null;
      }
    }
    if (!response.ok) {
      throw new Error(payload?.message || payload?.detail || payload?.error || raw.trim() || `${response.status}`);
    }
    if (payload === null) {
      throw new Error("Invalid JSON response from governed intake");
    }
    status.textContent = intakeOutcomeText(payload);
    if (!payload.blocked) {
      textarea.value = "";
      spokenReceipt = null;
      document.querySelector("#spoken-status").textContent = "Optional · Gemini transcription · review required";
      setTimeout(() => window.frontlineRefreshNow?.(), 2000);
      setTimeout(() => window.frontlineRefreshNow?.(), 6000);
    }
  } catch (error) {
    status.textContent = `Intake failed: ${error.message}`;
  } finally {
    button.disabled = false;
  }
});

document.querySelector("#load-demo-handover").addEventListener("click", () => {
  const textarea = document.querySelector("#handover");
  textarea.value = publicDemoHandover;
  spokenReceipt = null;
  document.querySelector("#spoken-status").textContent = "Prepared synthetic text · review before sending";
  document.querySelector("#intake-status").textContent = "Six operational teams represented · submission still uses the governed live path";
  textarea.focus();
});

document.querySelector("#handover").addEventListener("input", () => {
  if (spokenReceipt) {
    spokenReceipt = null;
    document.querySelector("#spoken-status").textContent = "Transcript edited · now using stable text fallback";
  }
});

document.querySelector("#record-handover").addEventListener("click", async () => {
  const button = document.querySelector("#record-handover");
  const status = document.querySelector("#spoken-status");
  if (mediaRecorder?.state === "recording") {
    mediaRecorder.stop();
    button.disabled = true;
    status.textContent = "Sending audio to Gemini…";
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
    status.textContent = "Recording unavailable in this browser · text intake remains available";
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recordedChunks = [];
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.addEventListener("dataavailable", (event) => { if (event.data.size) recordedChunks.push(event.data); });
    mediaRecorder.addEventListener("stop", async () => {
      stream.getTracks().forEach((track) => track.stop());
      try {
        const blob = new Blob(recordedChunks, { type: mediaRecorder.mimeType || "audio/webm" });
        const form = new FormData();
        form.append("audio", blob, "spoken-handover.webm");
        const response = await fetch("/api/spoken-handover/transcribe", { method: "POST", body: form });
        const result = await response.json().catch(() => null);
        if (!response.ok) throw new Error(result?.message || `${response.status}`);
        document.querySelector("#handover").value = result.transcript;
        spokenReceipt = result.receipt;
        const uncertainSegments = Array.isArray(result.uncertain_segments)
          ? result.uncertain_segments.filter((item) => typeof item === "string" && item.trim()).slice(0, 3)
          : [];
        const uncertainty = uncertainSegments.length
          ? ` · check: ${uncertainSegments.map((item) => `“${item.trim()}”`).join("; ")}`
          : "";
        status.textContent = `Gemini transcript ready · review before sending${uncertainty} · audit ${result.receipt.audit_reference}`;
      } catch (error) {
        spokenReceipt = null;
        status.textContent = `Transcription failed: ${error.message} · text intake remains available`;
      } finally {
        button.disabled = false;
        button.textContent = "Record spoken handover";
      }
    });
    mediaRecorder.start();
    button.textContent = "Stop and transcribe";
    status.textContent = "Recording synthetic non-clinical handover…";
  } catch (error) {
    status.textContent = `Microphone unavailable: ${error.message} · text intake remains available`;
  }
});
