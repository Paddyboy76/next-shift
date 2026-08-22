const activeStates = [
  "HUMAN_REVIEW",
  "BLOCKED",
  "ACTION_PENDING",
  "VERIFYING",
  "ASSIGNED",
  "TRIAGED",
  "RECEIVED",
];

const terminalStates = new Set(["CLOSED", "FAILED"]);

const attentionRank = {
  HUMAN_REVIEW: 0,
  BLOCKED: 1,
  FAILED: 2,
  ACTION_PENDING: 3,
  VERIFYING: 4,
  ASSIGNED: 5,
  TRIAGED: 6,
  RECEIVED: 7,
  CLOSED: 8,
};

const nextActions = {
  RECEIVED: "Await specialist triage",
  TRIAGED: "Await specialist assignment",
  ASSIGNED: "Begin operational action",
  ACTION_PENDING: "Await trusted evidence",
  VERIFYING: "Independent verification in progress",
  BLOCKED: "Resolve blocking dependency",
  HUMAN_REVIEW: "Authorized human decision required",
  CLOSED: "Verified complete — no action required",
  FAILED: "Review workflow failure",
};

const humanReachLabels = {
  PENDING: "Queued for frontline delivery",
  DELIVERED: "Delivered — awaiting frontline acknowledgement",
  ACKNOWLEDGED: "Acknowledged by frontline worker",
  BLOCKED: "Frontline worker reported blocked",
  COMPLETION_CLAIMED: "Human completion claimed — evidence still required",
  CANCELLED: "Frontline delivery no longer actionable",
};

const board = document.querySelector("#board");
const inactiveBoard = document.querySelector("#inactive-board");
const inactiveCount = document.querySelector("#inactive-count");
const latestWork = document.querySelector("#latest-work");
const drawer = document.querySelector("#drawer");
const backdrop = document.querySelector("#drawer-backdrop");
const drawerContent = document.querySelector("#drawer-content");
const refreshAlert = document.querySelector("#refresh-alert");
let drawerOrigin = null;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function escapeAttr(value) {
  return escapeHtml(value)
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function shortTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}

function issueTime(issue) {
  const raw = issue.updated_at || issue.created_at || "";
  const date = new Date(raw);
  return Number.isNaN(date.getTime()) ? 0 : date.getTime();
}

function stateTime(issue) {
  const raw = issue.last_transition_at || issue.updated_at || issue.created_at || "";
  const date = new Date(raw);
  return Number.isNaN(date.getTime()) ? 0 : date.getTime();
}

function formatDuration(milliseconds) {
  if (!Number.isFinite(milliseconds) || milliseconds < 0) return "—";
  const minutes = Math.floor(milliseconds / 60000);
  if (minutes < 1) return "<1m";
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  if (hours < 24) return remainder ? `${hours}h ${String(remainder).padStart(2, "0")}m` : `${hours}h`;
  const days = Math.floor(hours / 24);
  const dayHours = hours % 24;
  return dayHours ? `${days}d ${dayHours}h` : `${days}d`;
}

function timeInState(issue) {
  const timestamp = stateTime(issue);
  return timestamp ? formatDuration(Date.now() - timestamp) : "—";
}

function compareAttention(a, b) {
  const aState = String(a.state || "UNKNOWN");
  const bState = String(b.state || "UNKNOWN");
  const rankDifference = (attentionRank[aState] ?? 99) - (attentionRank[bState] ?? 99);
  return rankDifference || issueTime(b) - issueTime(a);
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

function claimMarker(issue) {
  if (String(issue.human_reach_status || "") !== "COMPLETION_CLAIMED") return "";
  return `<div class="claim-marker" aria-label="Human completion claimed but not independently verified">
    <span>CLAIMED</span>
    <strong>UNVERIFIED</strong>
  </div>`;
}

function issueCard(issue, options = {}) {
  const compact = options.compact === true;
  const inactive = options.inactive === true;
  const state = String(issue.state || "UNKNOWN");
  const absoluteTime = shortTime(issue.last_transition_at || issue.updated_at || issue.created_at);
  const classes = [
    "issue-card",
    compact ? "issue-card-compact" : "",
    inactive ? "issue-card-inactive" : "",
    issue.human_reach_status === "COMPLETION_CLAIMED" ? "issue-card-claimed" : "",
  ].filter(Boolean).join(" ");

  return `<article
    class="${classes}"
    data-issue="${escapeAttr(issue.id)}"
    role="button"
    tabindex="0"
    aria-label="Open ${escapeAttr(issue.title || issue.id)}"
  >
    <div class="issue-card-topline">
      <span class="owner">${escapeHtml(issue.owner)}</span>
      <span class="state-pill state-${escapeAttr(state.toLowerCase())}">${escapeHtml(state.replaceAll("_", " "))}</span>
    </div>
    ${claimMarker(issue)}
    <h3>${escapeHtml(issue.title || issue.id)}</h3>
    <div class="next-action">${escapeHtml(nextActions[state] || "Review state")}</div>
    <div class="card-time" title="${escapeAttr(absoluteTime)}">In state ${escapeHtml(timeInState(issue))}</div>
  </article>`;
}

function bindIssueCards() {
  document.querySelectorAll(".issue-card").forEach((card) => {
    const activate = () => openIssue(card.dataset.issue, card);
    card.addEventListener("click", activate);
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        activate();
      }
    });
  });
}

async function loadBoard() {
  const payload = await json("/api/issues");
  const issues = Array.isArray(payload.issues) ? payload.issues : [];
  const newest = issues.slice().sort((a, b) => issueTime(b) - issueTime(a));
  const active = newest
    .filter((issue) => !terminalStates.has(String(issue.state)))
    .sort(compareAttention);
  const inactive = newest.filter((issue) => terminalStates.has(String(issue.state)));

  latestWork.innerHTML = active.length
    ? active.slice(0, 8).map((issue) => issueCard(issue, { compact: true })).join("")
    : '<div class="empty focus-empty">No active operational work.</div>';

  const populatedLanes = activeStates
    .map((state) => ({
      state,
      matching: newest.filter((issue) => issue.state === state),
    }))
    .filter(({ matching }) => matching.length > 0);

  board.innerHTML = populatedLanes.length
    ? populatedLanes.map(({ state, matching }) => `<section class="lane lane-${state.toLowerCase()}">
      <div class="lane-title">
        <span>${state.replaceAll("_", " ")}</span>
        <span class="lane-count">${matching.length}</span>
      </div>
      <div class="lane-cards">
        ${matching.map((issue) => issueCard(issue)).join("")}
      </div>
    </section>`).join("")
    : '<div class="empty focus-empty">No open workflow lanes.</div>';

  inactiveCount.textContent = `${inactive.length} item${inactive.length === 1 ? "" : "s"}`;
  inactiveBoard.innerHTML = inactive.length
    ? inactive.map((issue) => issueCard(issue, { inactive: true })).join("")
    : '<div class="empty">No closed or failed work yet.</div>';

  bindIssueCards();
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
    return `<div class="detail-section primary-action">
      <span class="eyebrow">Next governed action</span>
      <h3>Record trusted evidence</h3>
      <div class="timeline-item">Synthetic acceptance control. Evidence is recorded through the dedicated trusted-evidence identity; it cannot close the issue.</div>
      <button class="primary-action-button" data-issue-action="complete" data-issue-id="${escapeAttr(issue.id)}">Record synthetic trusted evidence</button>
      <div class="action-error hidden" role="alert"></div>
    </div>`;
  }
  if (issue.state === "VERIFYING") {
    return `<div class="detail-section primary-action">
      <span class="eyebrow">Next governed action</span>
      <h3>Independent verification</h3>
      <div class="timeline-item">The verifier independently reads the trusted evidence and requests closure through State Authority.</div>
      <button class="primary-action-button" data-issue-action="verify" data-issue-id="${escapeAttr(issue.id)}">Run independent verifier</button>
      <div class="action-error hidden" role="alert"></div>
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
    ? `<div class="claim-callout"><strong>Claimed · unverified</strong><br>A frontline worker says the task is complete. That claim is not operational truth; trusted evidence and independent verification are still required.</div>`
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
  const errorBox = button.parentElement.querySelector(".action-error");
  if (errorBox) {
    errorBox.textContent = "";
    errorBox.classList.add("hidden");
  }
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
    if (errorBox) {
      errorBox.textContent = error.message;
      errorBox.classList.remove("hidden");
    }
  }
}

async function openIssue(issueId, origin = null) {
  const payload = await json(`/api/issues/${issueId}`);
  const issue = payload.issue;
  const evidence = payload.evidence || [];
  const transitions = payload.transitions || [];
  const humanReach = payload.human_reach || null;

  if (origin instanceof HTMLElement) drawerOrigin = origin;

  drawerContent.innerHTML = `
    <div class="drawer-header">
      <span class="eyebrow">${escapeHtml(issue.owner)}</span>
      <h2>${escapeHtml(issue.title || issue.id)}</h2>
    </div>
    <div class="detail-section current-state-section">
      <h3>Current state</h3>
      <div class="timeline-item current-state-card">
        <div class="detail-state-row">
          <span class="state-pill state-${escapeAttr(String(issue.state || "unknown").toLowerCase())}">${escapeHtml(String(issue.state || "UNKNOWN").replaceAll("_", " "))}</span>
          <span title="${escapeAttr(shortTime(issue.last_transition_at || issue.updated_at || issue.created_at))}">In state ${escapeHtml(timeInState(issue))}</span>
        </div>
        <div class="detail-next-action">${escapeHtml(nextActions[issue.state] || "")}</div>
      </div>
    </div>
    ${actionControls(issue)}
    ${humanReachSection(humanReach)}
    <div class="detail-section"><h3>Trusted evidence</h3>
      ${evidence.length ? evidence.map((item) => `<div class="timeline-item"><strong>${escapeHtml(item.evidence_type)}</strong><br>Source: ${escapeHtml(item.source)}<br>Subject: ${escapeHtml(item.subject)}<br>${item.verified_by ? `Verified by: ${escapeHtml(item.verified_by)}` : "Awaiting independent verification"}</div>`).join("") : '<div class="empty">No evidence recorded yet</div>'}
    </div>
    <div class="detail-section"><h3>Operational history</h3>
      ${(issue.history || []).length ? issue.history.slice().reverse().map((event) => `<div class="timeline-item"><strong>${escapeHtml(event.from || "START")} → ${escapeHtml(event.to)}</strong><br>${escapeHtml(event.reason || "")}<br><small>${escapeHtml(event.actor || "")} · ${escapeHtml(shortTime(event.at))}</small></div>`).join("") : '<div class="empty">No history</div>'}
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
  drawer.scrollTop = 0;
  drawer.classList.remove("hidden");
  backdrop.classList.remove("hidden");
  document.querySelector("#drawer-close").focus();
}

function closeDrawer() {
  drawer.classList.add("hidden");
  backdrop.classList.add("hidden");
  if (drawerOrigin && document.contains(drawerOrigin)) drawerOrigin.focus();
}

function trapDrawerFocus(event) {
  if (event.key !== "Tab" || drawer.classList.contains("hidden")) return;
  const focusable = Array.from(drawer.querySelectorAll('button, [href], [tabindex]:not([tabindex="-1"])'))
    .filter((element) => !element.disabled && element.offsetParent !== null);
  if (!focusable.length) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

document.querySelector("#drawer-close").addEventListener("click", closeDrawer);
backdrop.addEventListener("click", closeDrawer);
drawer.addEventListener("keydown", trapDrawerFocus);
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
    refreshAlert.textContent = "";
    refreshAlert.classList.add("hidden");
    document.body.classList.remove("data-stale");
  } catch (error) {
    const message = `Live data refresh failed: ${error.message}. Display may be stale.`;
    document.querySelector("#last-refresh").textContent = "Refresh failed";
    refreshAlert.textContent = message;
    refreshAlert.classList.remove("hidden");
    document.body.classList.add("data-stale");
  }
}

refresh();
setInterval(refresh, 5000);
