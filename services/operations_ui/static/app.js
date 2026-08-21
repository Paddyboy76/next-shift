const states = [
  "RECEIVED",
  "TRIAGED",
  "ASSIGNED",
  "ACTION_PENDING",
  "VERIFYING",
  "BLOCKED",
  "HUMAN_REVIEW",
  "CLOSED",
  "FAILED",
];

const nextActions = {
  RECEIVED: "Await specialist triage",
  TRIAGED: "Await specialist assignment",
  ASSIGNED: "Begin operational action",
  ACTION_PENDING: "Await trusted evidence",
  VERIFYING: "Await independent verification",
  BLOCKED: "Resolve blocking dependency",
  HUMAN_REVIEW: "Await authorized human decision",
  CLOSED: "Verified complete",
  FAILED: "Review failure",
};

const humanReachLabels = {
  PENDING: "Queued for frontline delivery",
  DELIVERED: "Delivered — awaiting frontline acknowledgement",
  ACKNOWLEDGED: "Acknowledged by frontline worker",
  BLOCKED: "Frontline worker reported blocked",
  COMPLETION_CLAIMED: "Human completion claimed — evidence still required",
};

const board = document.querySelector("#board");
const drawer = document.querySelector("#drawer");
const backdrop = document.querySelector("#drawer-backdrop");
const drawerContent = document.querySelector("#drawer-content");

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function shortTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}

async function json(url, options = {}) {
  const response = await fetch(url, options);
  const raw = await response.text();
  let payload = null;
  if (raw) {
    try { payload = JSON.parse(raw); } catch (_error) { payload = null; }
  }
  if (!response.ok) {
    const detail = payload?.message || payload?.detail || payload?.error || raw.trim() || url;
    throw new Error(`${response.status}: ${detail}`);
  }
  if (payload === null) throw new Error(`Invalid JSON response from ${url}`);
  return payload;
}

async function loadSummary() {
  const summary = await json("/api/summary");
  document.querySelector("#metric-open").textContent = summary.open;
  document.querySelector("#metric-verifying").textContent = summary.verifying;
  document.querySelector("#metric-closed").textContent = summary.closed;
  document.querySelector("#metric-review").textContent = summary.human_review;
}

function issueCard(issue) {
  return `<article class="issue-card" data-issue="${escapeHtml(issue.id)}">
    <span class="owner">${escapeHtml(issue.owner)}</span>
    <h3>${escapeHtml(issue.title || issue.id)}</h3>
    <div class="next-action">${escapeHtml(nextActions[issue.state] || "Review state")}</div>
    <div class="card-time">${escapeHtml(shortTime(issue.updated_at))}</div>
  </article>`;
}

async function loadBoard() {
  const payload = await json("/api/issues");
  const issues = payload.issues || [];
  board.innerHTML = states.map((state) => {
    const matching = issues.filter((issue) => issue.state === state);
    return `<section class="lane">
      <div class="lane-title"><span>${state.replaceAll("_", " ")}</span><span>${matching.length}</span></div>
      ${matching.length ? matching.map(issueCard).join("") : '<div class="empty">No work</div>'}
    </section>`;
  }).join("");
  document.querySelectorAll(".issue-card").forEach((card) => {
    card.addEventListener("click", () => openIssue(card.dataset.issue));
  });
  document.querySelector("#last-refresh").textContent = `Updated ${new Date().toLocaleTimeString()}`;
}

async function loadShifts() {
  const payload = await json("/api/shifts");
  const snapshots = payload.snapshots || [];
  document.querySelector("#shift-list").innerHTML = snapshots.length
    ? snapshots.map((snapshot) => `<div class="shift-item">
        <strong>${escapeHtml(snapshot.outgoing_shift)} → ${escapeHtml(snapshot.incoming_shift)}</strong>
        <span>${escapeHtml(snapshot.unresolved_count)} unresolved</span>
        <span>${escapeHtml(shortTime(snapshot.created_at))}</span>
      </div>`).join("")
    : '<div class="empty">No shift snapshots yet</div>';
}

function actionControls(issue) {
  if (issue.state === "ACTION_PENDING") {
    return `<div class="detail-section">
      <h3>Trusted completion</h3>
      <div class="timeline-item">Synthetic acceptance control. Evidence is recorded through the dedicated trusted-evidence identity; it cannot close the issue.</div>
      <button data-issue-action="complete" data-issue-id="${escapeHtml(issue.id)}">Record synthetic trusted evidence</button>
    </div>`;
  }
  if (issue.state === "VERIFYING") {
    return `<div class="detail-section">
      <h3>Independent verification</h3>
      <div class="timeline-item">The verifier independently reads the trusted evidence and requests closure through State Authority.</div>
      <button data-issue-action="verify" data-issue-id="${escapeHtml(issue.id)}">Run independent verifier</button>
    </div>`;
  }
  return "";
}

function humanReachSection(delivery) {
  if (!delivery) {
    return `<div class="detail-section">
      <h3>Human Reach</h3>
      <div class="empty">No frontline delivery recorded for this issue.</div>
    </div>`;
  }

  const status = String(delivery.delivery_status || "PENDING");
  const responses = Array.isArray(delivery.response_history)
    ? delivery.response_history.slice().reverse()
    : [];

  const completionWarning = status === "COMPLETION_CLAIMED"
    ? `<div class="timeline-item"><strong>Not verified complete</strong><br>A human completion claim is recorded, but trusted evidence and independent verification are still required before this issue can close.</div>`
    : "";

  return `<div class="detail-section">
    <h3>Human Reach</h3>
    <div class="timeline-item">
      <strong>${escapeHtml(humanReachLabels[status] || status)}</strong><br>
      Destination: ${escapeHtml(delivery.destination_display_name || "Resolving…")}<br>
      WHO: ${escapeHtml(delivery.who || "—")}<br>
      WHAT: ${escapeHtml(delivery.what || "—")}<br>
      WHERE: ${escapeHtml(delivery.where || "—")}<br>
      Work order: ${escapeHtml(delivery.work_order || "—")}
    </div>
    ${completionWarning}
    ${responses.length ? responses.map((item) => `<div class="timeline-item">
      <strong>${escapeHtml(String(item.to_status || item.action || "Response").replaceAll("_", " "))}</strong><br>
      ${escapeHtml(item.actor_display_name || item.actor_user || "Frontline worker")}<br>
      <small>${escapeHtml(shortTime(item.at))}</small>
    </div>`).join("") : '<div class="empty">No frontline response yet</div>'}
  </div>`;
}

async function runIssueAction(issueId, action, button) {
  const original = button.textContent;
  button.disabled = true;
  button.textContent = action === "complete" ? "Recording trusted evidence…" : "Running verifier…";
  try {
    const suffix = action === "complete" ? "complete" : "verify";
    await json(`/api/issues/${issueId}/${suffix}`, { method: "POST" });
    await refresh();
    await openIssue(issueId);
  } catch (error) {
    button.disabled = false;
    button.textContent = original;
    window.alert(error.message);
  }
}

async function openIssue(issueId) {
  const payload = await json(`/api/issues/${issueId}`);
  const issue = payload.issue;
  const evidence = payload.evidence || [];
  const transitions = payload.transitions || [];
  const humanReach = payload.human_reach || null;

  drawerContent.innerHTML = `
    <span class="eyebrow">${escapeHtml(issue.owner)}</span>
    <h2>${escapeHtml(issue.title || issue.id)}</h2>
    <div class="detail-section"><h3>Current state</h3><div class="timeline-item"><strong>${escapeHtml(issue.state)}</strong><br>${escapeHtml(nextActions[issue.state] || "")}</div></div>
    ${humanReachSection(humanReach)}
    ${actionControls(issue)}
    <div class="detail-section"><h3>Operational history</h3>
      ${(issue.history || []).length ? issue.history.slice().reverse().map((event) => `<div class="timeline-item"><strong>${escapeHtml(event.from || "START")} → ${escapeHtml(event.to)}</strong><br>${escapeHtml(event.reason || "")}<br><small>${escapeHtml(event.actor || "")} · ${escapeHtml(shortTime(event.at))}</small></div>`).join("") : '<div class="empty">No history</div>'}
    </div>
    <div class="detail-section"><h3>Trusted evidence</h3>
      ${evidence.length ? evidence.map((item) => `<div class="timeline-item"><strong>${escapeHtml(item.evidence_type)}</strong><br>Source: ${escapeHtml(item.source)}<br>Subject: ${escapeHtml(item.subject)}<br>${item.verified_by ? `Verified by: ${escapeHtml(item.verified_by)}` : "Awaiting independent verification"}</div>`).join("") : '<div class="empty">No evidence recorded yet</div>'}
    </div>
    <div class="detail-section"><h3>State Authority events</h3>
      ${transitions.length ? transitions.map((item) => `<div class="timeline-item"><strong>${escapeHtml(item.from_state)} → ${escapeHtml(item.to_state)}</strong><br>${escapeHtml(item.principal)}<br>${escapeHtml(shortTime(item.committed_at))}</div>`).join("") : '<div class="empty">No transition events</div>'}
    </div>`;

  const actionButton = drawerContent.querySelector("[data-issue-action]");
  if (actionButton) {
    actionButton.addEventListener("click", () => runIssueAction(
      actionButton.dataset.issueId,
      actionButton.dataset.issueAction,
      actionButton,
    ));
  }
  drawer.classList.remove("hidden");
  backdrop.classList.remove("hidden");
}

function closeDrawer() {
  drawer.classList.add("hidden");
  backdrop.classList.add("hidden");
}

document.querySelector("#drawer-close").addEventListener("click", closeDrawer);
backdrop.addEventListener("click", closeDrawer);

document.querySelector("#submit-handover").addEventListener("click", async () => {
  const button = document.querySelector("#submit-handover");
  const textarea = document.querySelector("#handover");
  const status = document.querySelector("#intake-status");
  const message = textarea.value.trim();
  if (!message) return;
  button.disabled = true;
  status.textContent = "Processing governed intake…";
  try {
    const response = await json("/api/intake", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    status.textContent = response.blocked ? `Blocked by security policy: ${response.message}` : response.message;
    if (!response.blocked) {
      textarea.value = "";
      setTimeout(refresh, 2000);
      setTimeout(refresh, 6000);
    }
  } catch (error) {
    status.textContent = `Intake failed: ${error.message}`;
  } finally {
    button.disabled = false;
  }
});

async function refresh() {
  try {
    await Promise.all([loadSummary(), loadBoard(), loadShifts()]);
  } catch (error) {
    document.querySelector("#last-refresh").textContent = `Refresh failed: ${error.message}`;
  }
}

refresh();
setInterval(refresh, 5000);
