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

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString();
}

async function json(url, options = {}) {
  const response = await fetch(url, options);

  if (!response.ok) {
    throw new Error(`${response.status} ${url}`);
  }

  return response.json();
}

async function loadSummary() {
  const summary = await json("/api/summary");

  document.querySelector("#metric-open").textContent =
    summary.open;
  document.querySelector("#metric-verifying").textContent =
    summary.verifying;
  document.querySelector("#metric-closed").textContent =
    summary.closed;
  document.querySelector("#metric-review").textContent =
    summary.human_review;
}

function issueCard(issue) {
  return `
    <article
      class="issue-card"
      data-issue="${escapeHtml(issue.id)}"
    >
      <span class="owner">
        ${escapeHtml(issue.owner)}
      </span>
      <h3>
        ${escapeHtml(issue.title || issue.id)}
      </h3>
      <div class="next-action">
        ${escapeHtml(nextActions[issue.state] || "Review state")}
      </div>
      <div class="card-time">
        ${escapeHtml(shortTime(issue.updated_at))}
      </div>
    </article>
  `;
}

async function loadBoard() {
  const payload = await json("/api/issues");
  const issues = payload.issues || [];

  board.innerHTML = states
    .map((state) => {
      const matching = issues.filter(
        (issue) => issue.state === state
      );

      return `
        <section class="lane">
          <div class="lane-title">
            <span>${state.replaceAll("_", " ")}</span>
            <span>${matching.length}</span>
          </div>
          ${
            matching.length
              ? matching.map(issueCard).join("")
              : '<div class="empty">No work</div>'
          }
        </section>
      `;
    })
    .join("");

  document
    .querySelectorAll(".issue-card")
    .forEach((card) => {
      card.addEventListener("click", () => {
        openIssue(card.dataset.issue);
      });
    });

  document.querySelector("#last-refresh").textContent =
    `Updated ${new Date().toLocaleTimeString()}`;
}

async function loadShifts() {
  const payload = await json("/api/shifts");
  const snapshots = payload.snapshots || [];

  document.querySelector("#shift-list").innerHTML =
    snapshots.length
      ? snapshots
          .map(
            (snapshot) => `
              <div class="shift-item">
                <strong>
                  ${escapeHtml(snapshot.outgoing_shift)}
                  →
                  ${escapeHtml(snapshot.incoming_shift)}
                </strong>
                <span>
                  ${escapeHtml(snapshot.unresolved_count)} unresolved
                </span>
                <span>
                  ${escapeHtml(shortTime(snapshot.created_at))}
                </span>
              </div>
            `
          )
          .join("")
      : '<div class="empty">No shift snapshots yet</div>';
}

async function openIssue(issueId) {
  const payload = await json(`/api/issues/${issueId}`);
  const issue = payload.issue;
  const evidence = payload.evidence || [];
  const transitions = payload.transitions || [];

  drawerContent.innerHTML = `
    <span class="eyebrow">${escapeHtml(issue.owner)}</span>
    <h2>${escapeHtml(issue.title || issue.id)}</h2>

    <div class="detail-section">
      <h3>Current state</h3>
      <div class="timeline-item">
        <strong>${escapeHtml(issue.state)}</strong><br>
        ${escapeHtml(nextActions[issue.state] || "")}
      </div>
    </div>

    <div class="detail-section">
      <h3>Operational history</h3>
      ${
        (issue.history || []).length
          ? issue.history
              .slice()
              .reverse()
              .map(
                (event) => `
                  <div class="timeline-item">
                    <strong>
                      ${escapeHtml(event.from || "START")}
                      →
                      ${escapeHtml(event.to)}
                    </strong><br>
                    ${escapeHtml(event.reason || "")}<br>
                    <small>
                      ${escapeHtml(event.actor || "")}
                      ·
                      ${escapeHtml(shortTime(event.at))}
                    </small>
                  </div>
                `
              )
              .join("")
          : '<div class="empty">No history</div>'
      }
    </div>

    <div class="detail-section">
      <h3>Trusted evidence</h3>
      ${
        evidence.length
          ? evidence
              .map(
                (item) => `
                  <div class="timeline-item">
                    <strong>
                      ${escapeHtml(item.evidence_type)}
                    </strong><br>
                    Source:
                    ${escapeHtml(item.source)}<br>
                    Subject:
                    ${escapeHtml(item.subject)}
                  </div>
                `
              )
              .join("")
          : '<div class="empty">No evidence recorded yet</div>'
      }
    </div>

    <div class="detail-section">
      <h3>State Authority events</h3>
      ${
        transitions.length
          ? transitions
              .map(
                (item) => `
                  <div class="timeline-item">
                    <strong>
                      ${escapeHtml(item.from_state)}
                      →
                      ${escapeHtml(item.to_state)}
                    </strong><br>
                    ${escapeHtml(item.principal)}<br>
                    ${escapeHtml(shortTime(item.committed_at))}
                  </div>
                `
              )
              .join("")
          : '<div class="empty">No transition events</div>'
      }
    </div>
  `;

  drawer.classList.remove("hidden");
  backdrop.classList.remove("hidden");
}

function closeDrawer() {
  drawer.classList.add("hidden");
  backdrop.classList.add("hidden");
}

document
  .querySelector("#drawer-close")
  .addEventListener("click", closeDrawer);

backdrop.addEventListener("click", closeDrawer);

document
  .querySelector("#submit-handover")
  .addEventListener("click", async () => {
    const button =
      document.querySelector("#submit-handover");
    const textarea =
      document.querySelector("#handover");
    const status =
      document.querySelector("#intake-status");

    const message = textarea.value.trim();

    if (!message) return;

    button.disabled = true;
    status.textContent = "Processing governed intake…";

    try {
      const response = await json(
        "/api/intake",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ message }),
        }
      );

      status.textContent = response.blocked
        ? `Blocked by security policy: ${response.message}`
        : response.message;

      if (!response.blocked) {
        textarea.value = "";

        setTimeout(refresh, 2000);
        setTimeout(refresh, 6000);
      }
    } catch (error) {
      status.textContent =
        `Intake failed: ${error.message}`;
    } finally {
      button.disabled = false;
    }
  });

async function refresh() {
  try {
    await Promise.all([
      loadSummary(),
      loadBoard(),
      loadShifts(),
    ]);
  } catch (error) {
    document.querySelector("#last-refresh").textContent =
      `Refresh failed: ${error.message}`;
  }
}

refresh();

setInterval(refresh, 5000);
