const terminalStates = new Set(["CLOSED", "FAILED"]);
const interventionStates = new Set(["HUMAN_REVIEW", "BLOCKED", "FAILED"]);
const canonicalOwners = [
  "Facilities",
  "AssetLogistics",
  "LanguageAccess",
  "DischargeDME",
  "EVSThroughput",
  "PatientTransport",
];

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
const attentionSection = document.querySelector("#attention-section");
const attentionWork = document.querySelector("#attention-work");
const ownerFilters = document.querySelector("#owner-filters");
const drawer = document.querySelector("#drawer");
const backdrop = document.querySelector("#drawer-backdrop");
const drawerContent = document.querySelector("#drawer-content");
const refreshAlert = document.querySelector("#refresh-alert");

let drawerOrigin = null;
let currentOwner = "ALL";
let cachedIssues = [];

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
  const date = new Date(issue.updated_at || issue.created_at || "");
  return Number.isNaN(date.getTime()) ? 0 : date.getTime();
}

function stateTime(issue) {
  const date = new Date(issue.last_transition_at || issue.updated_at || issue.created_at || "");
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

function issueLocation(issue) {
  const input = issue.workflow_input || {};
  if (input.origin && input.destination) return `${input.origin} → ${input.destination}`;
  return input.room || input.service_location || input.destination || input.origin ||
    issue.facilities_location || issue.evs_room || issue.interpreter_service_location ||
    issue.dme_delivery_destination || issue.transport_origin || "—";
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

function statePill(state) {
  const normalized = String(state || "UNKNOWN");
  return `<span class="state-pill state-${escapeAttr(normalized.toLowerCase())}">${escapeHtml(normalized.replaceAll("_", " "))}</span>`;
}

function claimChip(issue) {
  if (String(issue.human_reach_status || "") !== "COMPLETION_CLAIMED") return "";
  return '<span class="claim-chip">CLAIMED · UNVERIFIED</span>';
}

function workRow(issue, inactive = false) {
  const state = String(issue.state || "UNKNOWN");
  const absoluteTime = shortTime(issue.last_transition_at || issue.updated_at || issue.created_at);
  return `<article class="work-row${inactive ? " work-row-inactive" : ""}" data-issue="${escapeAttr(issue.id)}" role="button" tabindex="0" aria-label="Open ${escapeAttr(issue.title || issue.id)}">
    <div class="work-owner">${escapeHtml(issue.owner || "Unknown")}</div>
    <div class="work-main">
      <div class="work-title-line"><strong>${escapeHtml(issue.title || issue.id)}</strong>${claimChip(issue)}</div>
      <span class="work-location">${escapeHtml(issueLocation(issue))}</span>
    </div>
    <div class="work-state">${statePill(state)}</div>
    <div class="work-age" title="${escapeAttr(absoluteTime)}">${escapeHtml(timeInState(issue))}</div>
    <div class="work-next">${escapeHtml(nextActions[state] || "Review state")}</div>
  </article>`;
}

function attentionCard(issue) {
  const state = String(issue.state || "UNKNOWN");
  return `<article class="attention-card" data-issue="${escapeAttr(issue.id)}" role="button" tabindex="0">
    <div class="attention-card-top"><span class="owner">${escapeHtml(issue.owner)}</span>${statePill(state)}</div>
    <strong>${escapeHtml(issue.title || issue.id)}</strong>
    ${claimChip(issue)}
    <span>${escapeHtml(issueLocation(issue))} · ${escapeHtml(timeInState(issue))}</span>
  </article>`;
}

function bindIssueTargets() {
  document.querySelectorAll("[data-issue]").forEach((element) => {
    const activate = () => openIssue(element.dataset.issue, element);
    element.addEventListener("click", activate);
    element.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        activate();
      }
    });
  });
}

function renderOwnerFilters(activeIssues) {
  const counts = Object.fromEntries(canonicalOwners.map((owner) => [owner, 0]));
  activeIssues.forEach((issue) => {
    if (counts[issue.owner] !== undefined) counts[issue.owner] += 1;
  });
  const buttons = [
    `<button class="owner-filter${currentOwner === "ALL" ? " active" : ""}" data-owner-filter="ALL">All <span>${activeIssues.length}</span></button>`,
    ...canonicalOwners.map((owner) => `<button class="owner-filter${currentOwner === owner ? " active" : ""}" data-owner-filter="${escapeAttr(owner)}">${escapeHtml(owner)} <span>${counts[owner]}</span></button>`),
  ];
  ownerFilters.innerHTML = buttons.join("");
  ownerFilters.querySelectorAll("[data-owner-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      currentOwner = button.dataset.ownerFilter;
      renderBoard(cachedIssues);
    });
  });
}

function renderBoard(issues) {
  cachedIssues = issues;
  const newest = issues.slice().sort((a, b) => issueTime(b) - issueTime(a));
  const active = newest.filter((issue) => !terminalStates.has(String(issue.state))).sort(compareAttention);
  const inactive = newest.filter((issue) => terminalStates.has(String(issue.state)));

  renderOwnerFilters(active);

  const intervention = active.filter((issue) =>
    interventionStates.has(String(issue.state)) || String(issue.human_reach_status || "") === "COMPLETION_CLAIMED"
  );
  attentionSection.classList.toggle("hidden", intervention.length === 0);
  attentionWork.innerHTML = intervention.map(attentionCard).join("");

  const visible = currentOwner === "ALL" ? active : active.filter((issue) => issue.owner === currentOwner);
  board.innerHTML = visible.length
    ? `<div class="worklist-head"><span>Owner</span><span>Work</span><span>State</span><span>Waiting</span><span>Next governed action</span></div>${visible.map((issue) => workRow(issue)).join("")}`
    : '<div class="empty queue-empty">No open work for this owner.</div>';

  inactiveCount.textContent = `${inactive.length} item${inactive.length === 1 ? "" : "s"}`;
  inactiveBoard.innerHTML = inactive.length ? inactive.map((issue) => workRow(issue, true)).join("") : '<div class="empty">No closed or failed work yet.</div>';

  bindIssueTargets();
  document.querySelector("#last-refresh").textContent = `Updated ${new Date().toLocaleTimeString()}`;
}

async function loadBoard() {
  const payload = await json("/api/issues");
  renderBoard(Array.isArray(payload.issues) ? payload.issues : []);
}

async function loadShifts() {
  const payload = await json("/api/shifts");
  const snapshots = payload.snapshots || [];
  document.querySelector("#shift-list").innerHTML = snapshots.length
    ? snapshots.map((snapshot) => `<div class="shift-item"><strong>${escapeHtml(snapshot.outgoing_shift)} → ${escapeHtml(snapshot.incoming_shift)}</strong><span>${escapeHtml(snapshot.unresolved_count)} unresolved</span><span>${escapeHtml(shortTime(snapshot.created_at))}</span></div>`).join("")
    : '<div class="empty">No shift snapshots yet</div>';
}

function actionControls(issue) {
  if (issue.state === "ACTION_PENDING") {
    return `<div class="detail-section primary-action"><span class="eyebrow">Next governed action</span><h3>Record trusted evidence</h3><div class="timeline-item">Synthetic acceptance control. Evidence is recorded through the dedicated trusted-evidence identity; it cannot close the issue.</div><button class="primary-action-button" data-issue-action="complete" data-issue-id="${escapeAttr(issue.id)}">Record synthetic trusted evidence</button><div class="action-error hidden" role="alert"></div></div>`;
  }
  if (issue.state === "VERIFYING") {
    return `<div class="detail-section primary-action"><span class="eyebrow">Next governed action</span><h3>Independent verification</h3><div class="timeline-item">The verifier independently reads trusted evidence and requests closure through State Authority.</div><button class="primary-action-button" data-issue-action="verify" data-issue-id="${escapeAttr(issue.id)}">Run independent verifier</button><div class="action-error hidden" role="alert"></div></div>`;
  }
  return "";
}

function humanReachSection(delivery) {
  if (!delivery) return '<div class="detail-section"><h3>Human Reach</h3><div class="empty">No frontline delivery recorded for this issue.</div></div>';
  const status = String(delivery.delivery_status || "PENDING");
  const responses = Array.isArray(delivery.response_history) ? delivery.response_history.slice().reverse() : [];
  const completionWarning = status === "COMPLETION_CLAIMED"
    ? '<div class="claim-callout"><strong>Claimed · unverified</strong><br>A frontline worker says the task is complete. Trusted evidence and independent verification are still required.</div>'
    : "";
  return `<div class="detail-section"><h3>Human Reach</h3><div class="timeline-item"><strong>${escapeHtml(humanReachLabels[status] || status)}</strong><br>Destination: ${escapeHtml(delivery.destination_display_name || "Resolving…")}<br>WHO: ${escapeHtml(delivery.who || "—")}<br>WHAT: ${escapeHtml(delivery.what || "—")}<br>WHERE: ${escapeHtml(delivery.where || "—")}<br>Work order: ${escapeHtml(delivery.work_order || "—")}</div>${completionWarning}${responses.length ? responses.map((item) => `<div class="timeline-item"><strong>${escapeHtml(String(item.to_status || item.action || "Response").replaceAll("_", " "))}</strong><br>${escapeHtml(item.actor_display_name || item.actor_user || "Frontline worker")}<br><small>${escapeHtml(shortTime(item.at))}</small></div>`).join("") : '<div class="empty">No frontline response yet</div>'}</div>`;
}

async function runIssueAction(issueId, action, button) {
  const original = button.textContent;
  const errorBox = button.parentElement.querySelector(".action-error");
  if (errorBox) { errorBox.textContent = ""; errorBox.classList.add("hidden"); }
  button.disabled = true;
  button.textContent = action === "complete" ? "Recording trusted evidence…" : "Running verifier…";
  try {
    await json(`/api/issues/${issueId}/${action === "complete" ? "complete" : "verify"}`, { method: "POST" });
    await refresh();
    await openIssue(issueId);
  } catch (error) {
    button.disabled = false;
    button.textContent = original;
    if (errorBox) { errorBox.textContent = error.message; errorBox.classList.remove("hidden"); }
  }
}

async function openIssue(issueId, origin = null) {
  const payload = await json(`/api/issues/${issueId}`);
  const issue = payload.issue;
  const evidence = payload.evidence || [];
  const transitions = payload.transitions || [];
  const humanReach = payload.human_reach || null;
  if (origin instanceof HTMLElement) drawerOrigin = origin;

  drawerContent.innerHTML = `<div class="drawer-header"><span class="eyebrow">${escapeHtml(issue.owner)}</span><h2>${escapeHtml(issue.title || issue.id)}</h2></div>
    <div class="detail-section current-state-section"><h3>Current state</h3><div class="timeline-item current-state-card"><div class="detail-state-row">${statePill(issue.state)}<span title="${escapeAttr(shortTime(issue.last_transition_at || issue.updated_at || issue.created_at))}">In state ${escapeHtml(timeInState(issue))}</span></div><div class="detail-next-action">${escapeHtml(nextActions[issue.state] || "")}</div></div></div>
    ${actionControls(issue)}
    ${humanReachSection(humanReach)}
    <div class="detail-section"><h3>Trusted evidence</h3>${evidence.length ? evidence.map((item) => `<div class="timeline-item"><strong>${escapeHtml(item.evidence_type)}</strong><br>Source: ${escapeHtml(item.source)}<br>Subject: ${escapeHtml(item.subject)}<br>${item.verified_by ? `Verified by: ${escapeHtml(item.verified_by)}` : "Awaiting independent verification"}</div>`).join("") : '<div class="empty">No evidence recorded yet</div>'}</div>
    <div class="detail-section"><h3>Operational history</h3>${(issue.history || []).length ? issue.history.slice().reverse().map((event) => `<div class="timeline-item"><strong>${escapeHtml(event.from || "START")} → ${escapeHtml(event.to)}</strong><br>${escapeHtml(event.reason || "")}<br><small>${escapeHtml(event.actor || "")} · ${escapeHtml(shortTime(event.at))}</small></div>`).join("") : '<div class="empty">No history</div>'}</div>
    <div class="detail-section"><h3>State Authority events</h3>${transitions.length ? transitions.map((item) => `<div class="timeline-item"><strong>${escapeHtml(item.from_state)} → ${escapeHtml(item.to_state)}</strong><br>${escapeHtml(item.principal)}<br>${escapeHtml(shortTime(item.committed_at))}</div>`).join("") : '<div class="empty">No transition events</div>'}</div>`;

  const actionButton = drawerContent.querySelector("[data-issue-action]");
  if (actionButton) actionButton.addEventListener("click", () => runIssueAction(actionButton.dataset.issueId, actionButton.dataset.issueAction, actionButton));
  drawer.scrollTop = 0;
  drawer.classList.remove("hidden");
  backdrop.classList.remove("hidden");
  document.querySelector("#drawer-close").focus();
}

function closeDrawer() {
  drawer.classList.add("hidden");
  backdrop.classList.add("hidden");
  if (drawerOrigin?.isConnected) drawerOrigin.focus();
  drawerOrigin = null;
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
    const response = await json("/api/intake", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message }) });
    status.textContent = response.blocked ? `Blocked by security policy: ${response.message}` : response.message;
    if (!response.blocked) { textarea.value = ""; setTimeout(refresh, 2000); setTimeout(refresh, 6000); }
  } catch (error) {
    status.textContent = `Intake failed: ${error.message}`;
  } finally {
    button.disabled = false;
  }
});

async function refresh() {
  try {
    await Promise.all([loadSummary(), loadBoard(), loadShifts()]);
    refreshAlert.classList.add("hidden");
    refreshAlert.textContent = "";
    document.body.classList.remove("data-stale");
  } catch (error) {
    document.querySelector("#last-refresh").textContent = "Refresh failed";
    refreshAlert.textContent = `Live data refresh failed: ${error.message}`;
    refreshAlert.classList.remove("hidden");
    document.body.classList.add("data-stale");
  }
}

refresh();
setInterval(refresh, 5000);
