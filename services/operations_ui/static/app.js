let spokenReceipt = null;
let mediaRecorder = null;
let recordedChunks = [];

const drawer = document.querySelector("#drawer");
const backdrop = document.querySelector("#drawer-backdrop");

function closeDrawer() {
  drawer.classList.add("hidden");
  backdrop.classList.add("hidden");
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
    const payload = await response.json().catch(() => null);
    if (!response.ok) throw new Error(payload?.message || payload?.detail || `${response.status}`);
    status.textContent = payload.blocked ? `Blocked by security policy: ${payload.message}` : payload.message;
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
  textarea.value = "Synthetic night-shift handover for Tower 4: a standard wheelchair is missing from the Level 3 lift lobby. A Spanish interpreter is needed in Room 402. Home oxygen delivery to the synthetic discharge lounge is still pending. Room 418 needs EVS turnaround. The sink in Room 406 is leaking. Patient transport is waiting to move a guest from the discharge lounge to the north entrance.";
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
        const uncertainty = result.uncertain_segments?.length ? ` · review ${result.uncertain_segments.length} uncertain segment(s)` : "";
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