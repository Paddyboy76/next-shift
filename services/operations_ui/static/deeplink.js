(() => {
  "use strict";

  const TERMINAL = new Set(["CLOSED", "FAILED"]);
  const INTERVENTION = new Set(["BLOCKED", "HUMAN_REVIEW"]);
  const SHIFT_HOURS = [7, 19];
  const MAX_RECENT_HISTORY = 30;

  const esc = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");

  const parseTime = (value) => {
    const date = value ? new Date(value) : null;
    return date && !Number.isNaN(date.getTime()) ? date : null;
  };

  const issueStamp = (issue) => parseTime(
    issue.last_transition_at || issue.updated_at || issue.created_at
  );

  const shortClock = (value) => {
    const date = parseTime(value);
    if (!date) return "—";
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const shortDate = (value) => {
    const date = parseTime(value);
    if (!date) return "—";
    return date.toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const age = (value) => {
    const date = parseTime(value);
    if (!date) return "—";
    const ms = Math.max(0, Date.now() - date.getTime());
    const mins = Math.floor(ms / 60000);
    if (mins < 1) return "now";
    if (mins < 60) return `${mins}m`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h`;
    return `${Math.floor(hours / 24)}d`;
  };

  const humanize = (value) => String(value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());

  const locationOf = (issue) => {
    const input = issue.workflow_input || {};
    if (input.origin && input.destination) return `${input.origin} → ${input.destination}`;
    return input.room || input.service_location || input.destination || input.origin ||
      issue.facilities_location || issue.evs_room || issue.interpreter_service_location ||
      issue.dme_delivery_destination || issue.transport_origin || "—";
  };

  const latestHistory = (issue) => {
    const history = Array.isArray(issue.history) ? issue.history : [];
    return history.length ? history[history.length - 1] : null;
  };

  const latestText = (issue) => {
    const event = latestHistory(issue);
    if (event?.reason) return humanize(event.reason);
    const state = String(issue.state || "UNKNOWN");
    const fallback = {
      RECEIVED: "Work received",
      TRIAGED: "Specialist triage complete",
      ASSIGNED: "Operational owner assigned",
      ACTION_PENDING: "Operational action accepted",
      VERIFYING: "Evidence submitted for verification",
      BLOCKED: "Work is blocked",
      HUMAN_REVIEW: "Human review requested",
      CLOSED: "Work independently verified",
      FAILED: "Workflow failed",
    };
    return fallback[state] || humanize(state);
  };

  const waitingFor = (issue) => {
    if (String(issue.human_reach_status || "") === "COMPLETION_CLAIMED") {
      return "Trusted evidence — completion is only a claim";
    }
    if (issue.verification_status === "REJECTED") {
      return "Controlled recovery / fresh evidence";
    }
    const state = String(issue.state || "UNKNOWN");
    return {
      RECEIVED: "Specialist triage",
      TRIAGED: "Specialist assignment",
      ASSIGNED: "Operational action",
      ACTION_PENDING: "Trusted completion evidence",
      VERIFYING: "Independent verification",
      BLOCKED: "Blocking dependency to be resolved",
      HUMAN_REVIEW: "Authorized human decision",
      CLOSED: "Nothing — verified complete",
      FAILED: "Failure review",
    }[state] || "Next governed action";
  };

  const stateLabel = (issue) => {
    if (String(issue.human_reach_status || "") === "COMPLETION_CLAIMED") {
      return "CLAIMED · UNVERIFIED";
    }
    const state = String(issue.state || "UNKNOWN");
    return {
      RECEIVED: "RECEIVED",
      TRIAGED: "TRIAGED",
      ASSIGNED: "ASSIGNED",
      ACTION_PENDING: "WAITING",
      VERIFYING: "VERIFYING",
      BLOCKED: "BLOCKED",
      HUMAN_REVIEW: "NEEDS DECISION",
      CLOSED: "VERIFIED",
      FAILED: "FAILED",
    }[state] || state.replaceAll("_", " ");
  };

  const isIntervention = (issue) => (
    INTERVENTION.has(String(issue.state || "")) ||
    String(issue.human_reach_status || "") === "COMPLETION_CLAIMED" ||
    issue.verification_status === "REJECTED"
  );

  async function requestJson(url, options = {}) {
    const response = await fetch(url, options);
    const raw = await response.text();
    let body = null;
    try { body = raw ? JSON.parse(raw) : null; } catch (_error) { body = null; }
    if (!response.ok) {
      throw new Error(body?.message || body?.detail || body?.error || raw || `${response.status}`);
    }
    return body;
  }

  function fallbackShiftStart() {
    const now = new Date();
    const start = new Date(now);
    start.setMinutes(0, 0, 0);
    const hour = now.getHours();
    if (hour >= SHIFT_HOURS[1]) {
      start.setHours(SHIFT_HOURS[1]);
    } else if (hour >= SHIFT_HOURS[0]) {
      start.setHours(SHIFT_HOURS[0]);
    } else {
      start.setDate(start.getDate() - 1);
      start.setHours(SHIFT_HOURS[1]);
    }
    return start;
  }

  function currentShift(snapshots) {
    const fallback = fallbackShiftStart();
    const newest = Array.isArray(snapshots) && snapshots.length ? snapshots[0] : null;
    const snapshotTime = parseTime(newest?.created_at);
    if (snapshotTime && Date.now() - snapshotTime.getTime() <= 14 * 60 * 60 * 1000) {
      return {
        start: snapshotTime,
        label: newest.incoming_shift || "Current shift",
        source: "shift handover",
      };
    }
    return { start: fallback, label: "Current shift", source: "active operational window" };
  }

  function injectStyles() {
    if (document.querySelector("#frontline-now-styles")) return;
    const style = document.createElement("style");
    style.id = "frontline-now-styles";
    style.textContent = `
      .workspace, .platform-grid, .metric-panel { display: none !important; }
      .hero-grid { grid-template-columns: minmax(0, 1fr) !important; margin-bottom: 16px !important; }
      .demo-intro { padding-top: 16px !important; padding-bottom: 16px !important; }
      .demo-intro p { max-width: 920px; }
      .frontline-shell { margin-top: 8px; display: grid; gap: 14px; }
      .frontline-topbar { display:flex; align-items:center; justify-content:space-between; gap:16px; padding:14px 16px; border:1px solid #d9e2e8; border-radius:12px; background:#fff; }
      .frontline-topbar h2 { margin:2px 0 0; font-size:22px; }
      .frontline-topbar .frontline-meta { color:#647884; font-size:12px; }
      .frontline-actions { display:flex; gap:8px; align-items:center; }
      .frontline-button { border:1px solid #cbd8df; background:#f7fafb; color:#173440; padding:8px 12px; border-radius:9px; font-weight:700; cursor:pointer; }
      .frontline-button:hover { background:#eef5f7; }
      .frontline-section { background:#fff; border:1px solid #d9e2e8; border-radius:12px; padding:14px; }
      .frontline-section-head { display:flex; justify-content:space-between; align-items:flex-end; gap:12px; margin-bottom:10px; }
      .frontline-section-head h3 { margin:2px 0 0; font-size:16px; }
      .frontline-count { color:#647884; font-size:12px; font-weight:700; }
      .frontline-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:9px; }
      .frontline-card { border:1px solid #d9e2e8; border-radius:10px; padding:11px 12px; background:#fbfdfe; cursor:pointer; min-width:0; }
      .frontline-card:hover { border-color:#8ebfc2; background:#f5fbfb; }
      .frontline-card.attention { border-color:#e4b7ae; background:#fff9f7; }
      .frontline-card-top { display:flex; justify-content:space-between; gap:8px; align-items:center; }
      .frontline-owner { color:#53707c; font-size:10px; font-weight:800; text-transform:uppercase; letter-spacing:.08em; }
      .frontline-state { font-size:10px; font-weight:900; padding:3px 7px; border-radius:999px; background:#e7f3f2; color:#17665f; white-space:nowrap; }
      .frontline-card.attention .frontline-state { background:#fee9e5; color:#9d382c; }
      .frontline-title { margin:7px 0 1px; font-size:14px; font-weight:800; color:#173440; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .frontline-location { color:#70848e; font-size:11px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .frontline-line { margin-top:7px; font-size:11px; line-height:1.35; color:#405b67; }
      .frontline-line strong { color:#183945; }
      .frontline-wait { display:flex; justify-content:space-between; gap:8px; align-items:flex-end; }
      .frontline-age { font-weight:900; color:#183945; white-space:nowrap; }
      .frontline-empty { color:#6e818b; padding:10px 2px; font-size:13px; }
      .frontline-carried { width:100%; text-align:left; border:1px dashed #c9d6dc; background:#f8fafb; border-radius:10px; padding:10px 12px; color:#536d78; cursor:pointer; font-weight:700; }
      .frontline-carried:hover { background:#f1f6f8; }
      .frontline-investigation .investigation-hero { border:1px solid #d9e2e8; background:#f8fbfc; border-radius:10px; padding:12px; margin-bottom:12px; }
      .frontline-investigation .investigation-grid { display:grid; grid-template-columns:1fr 1fr; gap:9px; margin:10px 0; }
      .frontline-investigation .investigation-fact { border:1px solid #e1e8ec; border-radius:9px; padding:10px; background:#fff; }
      .frontline-investigation .investigation-fact span { display:block; color:#6c818b; font-size:9px; text-transform:uppercase; letter-spacing:.08em; font-weight:900; }
      .frontline-investigation .investigation-fact strong { display:block; margin-top:4px; font-size:13px; line-height:1.35; color:#173440; }
      .frontline-investigation details { margin-top:10px; border-top:1px solid #e0e7eb; padding-top:10px; }
      .frontline-investigation summary { cursor:pointer; font-weight:800; color:#315461; }
      .frontline-history-item { margin-top:8px; padding:9px 10px; border-radius:8px; background:#f7fafb; font-size:11px; line-height:1.4; color:#415d68; }
      .frontline-primary { margin-top:12px; width:100%; border:0; background:#16877f; color:#fff; padding:11px 12px; border-radius:9px; font-weight:900; cursor:pointer; }
      .frontline-primary:disabled { opacity:.55; cursor:wait; }
      .frontline-error { margin-top:8px; color:#a23f34; font-size:11px; }
      .past-section { margin-top:14px; }
      .past-section h3 { margin:0 0 8px; }
      .past-row { display:flex; justify-content:space-between; gap:12px; border-bottom:1px solid #edf1f3; padding:9px 0; font-size:11px; }
      .past-row:last-child { border-bottom:0; }
      .past-row button { border:0; background:none; color:#126f69; font-weight:800; cursor:pointer; text-align:left; }
      .advisor-card { margin-top:8px; padding:10px; border:1px solid #dfe7eb; border-radius:9px; background:#f9fbfc; }
      .advisor-card strong { display:block; color:#173440; }
      .advisor-card span { display:block; margin-top:4px; color:#5c737d; font-size:11px; line-height:1.4; }
      .frontline-intake-progress { display:none; margin-top:9px; padding:10px; border:1px solid #d4e2e5; border-radius:9px; background:#f7fbfb; }
      .frontline-intake-progress.active { display:block; }
      .frontline-progress-track { height:5px; border-radius:999px; overflow:hidden; background:#dfeaec; margin:7px 0; }
      .frontline-progress-bar { height:100%; width:35%; border-radius:999px; background:#178b82; animation:frontline-progress 1.2s ease-in-out infinite alternate; }
      .frontline-progress-steps { color:#607983; font-size:10px; line-height:1.4; }
      @keyframes frontline-progress { from { transform:translateX(-20%); } to { transform:translateX(210%); } }
      @media (max-width:1100px) { .frontline-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } }
      @media (max-width:720px) { .frontline-grid, .frontline-investigation .investigation-grid { grid-template-columns:1fr; } .frontline-topbar { align-items:flex-start; flex-direction:column; } }
    `;
    document.head.appendChild(style);
  }

  let cache = { issues: [], shifts: [], shift: null };

  function shell() {
    let node = document.querySelector("#frontline-shell");
    if (node) return node;
    const hero = document.querySelector(".hero-grid");
    node = document.createElement("section");
    node.id = "frontline-shell";
    node.className = "frontline-shell";
    node.innerHTML = `
      <div class="frontline-topbar">
        <div>
          <span class="eyebrow">Live operations · now</span>
          <h2>What is happening this shift?</h2>
          <div id="frontline-shift-meta" class="frontline-meta">Loading current shift…</div>
        </div>
        <div class="frontline-actions">
          <button id="frontline-refresh" class="frontline-button" type="button">Refresh now</button>
          <button id="frontline-past" class="frontline-button" type="button">Past</button>
        </div>
      </div>
      <section id="frontline-attention" class="frontline-section">
        <div class="frontline-section-head"><div><span class="eyebrow">Needs input now</span><h3>Intervention</h3></div><span id="frontline-attention-count" class="frontline-count"></span></div>
        <div id="frontline-attention-grid" class="frontline-grid"></div>
      </section>
      <section class="frontline-section">
        <div class="frontline-section-head"><div><span class="eyebrow">Current shift</span><h3>Ongoing work</h3></div><span id="frontline-live-count" class="frontline-count"></span></div>
        <div id="frontline-live-grid" class="frontline-grid"></div>
        <button id="frontline-carried" class="frontline-carried" type="button"></button>
      </section>`;
    if (hero?.parentNode) hero.insertAdjacentElement("afterend", node);
    else document.querySelector("main")?.appendChild(node);
    node.querySelector("#frontline-refresh")?.addEventListener("click", loadNow);
    node.querySelector("#frontline-past")?.addEventListener("click", openPast);
    node.querySelector("#frontline-carried")?.addEventListener("click", openPast);
    return node;
  }

  function card(issue, shiftStart, attention = false) {
    const stamp = issueStamp(issue);
    const carried = stamp && stamp < shiftStart;
    return `<article class="frontline-card${attention ? " attention" : ""}" data-frontline-issue="${esc(issue.id)}" tabindex="0" role="button">
      <div class="frontline-card-top"><span class="frontline-owner">${esc(issue.owner || "Unknown")}${carried ? " · carried" : ""}</span><span class="frontline-state">${esc(stateLabel(issue))}</span></div>
      <div class="frontline-title">${esc(issue.title || issue.id)}</div>
      <div class="frontline-location">${esc(locationOf(issue))}</div>
      <div class="frontline-line"><strong>Latest:</strong> ${esc(latestText(issue))}</div>
      <div class="frontline-line frontline-wait"><span><strong>Waiting for:</strong> ${esc(waitingFor(issue))}</span><span class="frontline-age">${esc(age(issue.last_transition_at || issue.updated_at || issue.created_at))}</span></div>
    </article>`;
  }

  function bindCards(root = document) {
    root.querySelectorAll("[data-frontline-issue]").forEach((node) => {
      const activate = () => openFrontlineIssue(node.dataset.frontlineIssue);
      node.addEventListener("click", activate);
      node.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          activate();
        }
      });
    });
  }

  function renderNow() {
    shell();
    const shift = cache.shift;
    if (!shift) return;
    const active = cache.issues.filter((issue) => !TERMINAL.has(String(issue.state || "")));
    const attention = active.filter(isIntervention).sort((a, b) => (issueStamp(b)?.getTime() || 0) - (issueStamp(a)?.getTime() || 0));
    const attentionIds = new Set(attention.map((issue) => issue.id));
    const current = active
      .filter((issue) => !attentionIds.has(issue.id))
      .filter((issue) => {
        const stamp = issueStamp(issue);
        return stamp && stamp >= shift.start;
      })
      .sort((a, b) => (issueStamp(b)?.getTime() || 0) - (issueStamp(a)?.getTime() || 0));
    const carried = active.filter((issue) => !attentionIds.has(issue.id) && !current.some((item) => item.id === issue.id));

    const meta = document.querySelector("#frontline-shift-meta");
    if (meta) meta.textContent = `${shift.label} · since ${shortClock(shift.start.toISOString())} · ${current.length + attention.length} relevant now`;

    const attentionSection = document.querySelector("#frontline-attention");
    const attentionGrid = document.querySelector("#frontline-attention-grid");
    const attentionCount = document.querySelector("#frontline-attention-count");
    if (attentionSection) attentionSection.style.display = attention.length ? "block" : "none";
    if (attentionCount) attentionCount.textContent = `${attention.length} item${attention.length === 1 ? "" : "s"}`;
    if (attentionGrid) attentionGrid.innerHTML = attention.length
      ? attention.map((issue) => card(issue, shift.start, true)).join("")
      : '<div class="frontline-empty">Nothing needs intervention right now.</div>';

    const liveGrid = document.querySelector("#frontline-live-grid");
    const liveCount = document.querySelector("#frontline-live-count");
    if (liveCount) liveCount.textContent = `${current.length} item${current.length === 1 ? "" : "s"}`;
    if (liveGrid) liveGrid.innerHTML = current.length
      ? current.map((issue) => card(issue, shift.start)).join("")
      : '<div class="frontline-empty">No active work has changed during this shift.</div>';

    const carriedButton = document.querySelector("#frontline-carried");
    if (carriedButton) {
      carriedButton.textContent = carried.length
        ? `Carried from earlier shifts · ${carried.length} — available in Past`
        : "No carried-forward work from earlier shifts";
      carriedButton.disabled = carried.length === 0;
    }
    bindCards(document.querySelector("#frontline-shell") || document);
  }

  async function loadNow() {
    try {
      const [issuePayload, shiftPayload] = await Promise.all([
        requestJson("/api/issues"),
        requestJson("/api/shifts"),
      ]);
      cache.issues = Array.isArray(issuePayload?.issues) ? issuePayload.issues : [];
      cache.shifts = Array.isArray(shiftPayload?.snapshots) ? shiftPayload.snapshots : [];
      cache.shift = currentShift(cache.shifts);
      renderNow();
    } catch (error) {
      const live = document.querySelector("#frontline-live-grid");
      if (live) live.innerHTML = `<div class="frontline-error">Unable to refresh live work: ${esc(error.message)}</div>`;
    }
  }

  function openDrawer(content) {
    const drawer = document.querySelector("#drawer");
    const backdrop = document.querySelector("#drawer-backdrop");
    const body = document.querySelector("#drawer-content");
    if (!drawer || !backdrop || !body) return;
    body.innerHTML = content;
    drawer.scrollTop = 0;
    drawer.classList.remove("hidden");
    backdrop.classList.remove("hidden");
    document.querySelector("#drawer-close")?.focus();
  }

  function actionButton(issue, plans) {
    const sanctioned = plans.some((plan) => plan.status === "SANCTIONED" && plan.state_observed === issue.state);
    if (issue.state === "ACTION_PENDING" && issue.verification_status === "REJECTED" && !sanctioned) {
      return `<button class="frontline-primary" data-frontline-action="recovery-plan" data-issue-id="${esc(issue.id)}">Generate controlled recovery plan</button>`;
    }
    if (issue.state === "ACTION_PENDING") {
      return `<button class="frontline-primary" data-frontline-action="complete" data-issue-id="${esc(issue.id)}">${sanctioned ? "Record fresh trusted evidence" : "Record trusted evidence"}</button>`;
    }
    if (issue.state === "VERIFYING") {
      return `<button class="frontline-primary" data-frontline-action="verify" data-issue-id="${esc(issue.id)}">Run independent verifier</button>`;
    }
    return "";
  }

  async function performAction(button) {
    const issueId = button.dataset.issueId;
    const action = button.dataset.frontlineAction;
    const original = button.textContent;
    button.disabled = true;
    button.textContent = action === "verify" ? "Verifying…" : action === "recovery-plan" ? "Planning safely…" : "Recording evidence…";
    try {
      const path = action === "complete"
        ? `/api/issues/${issueId}/complete`
        : action === "verify"
          ? `/api/issues/${issueId}/verify`
          : `/api/issues/${issueId}/recovery-plan`;
      await requestJson(path, { method: "POST" });
      await loadNow();
      await openFrontlineIssue(issueId);
    } catch (error) {
      button.disabled = false;
      button.textContent = original;
      const errorNode = button.parentElement?.querySelector(".frontline-error") || document.createElement("div");
      errorNode.className = "frontline-error";
      errorNode.textContent = error.message;
      if (!errorNode.parentElement) button.insertAdjacentElement("afterend", errorNode);
    }
  }

  function historyItems(issue) {
    const history = Array.isArray(issue.history) ? issue.history.slice().reverse() : [];
    return history.length
      ? history.map((event) => `<div class="frontline-history-item"><strong>${esc(event.from || "START")} → ${esc(event.to || "")}</strong><br>${esc(humanize(event.reason || "State changed"))}<br><small>${esc(event.actor || "")} · ${esc(shortDate(event.at))}</small></div>`).join("")
      : '<div class="frontline-empty">No earlier activity.</div>';
  }

  async function openFrontlineIssue(issueId) {
    try {
      const payload = await requestJson(`/api/issues/${issueId}`);
      const issue = payload.issue || {};
      const evidence = Array.isArray(payload.evidence) ? payload.evidence : [];
      const transitions = Array.isArray(payload.transitions) ? payload.transitions : [];
      const plans = Array.isArray(payload.recovery_plans) ? payload.recovery_plans : [];
      const human = payload.human_reach || null;
      const latest = latestHistory(issue);
      const humanStatus = human?.delivery_status ? humanize(human.delivery_status) : "—";
      const content = `<div class="frontline-investigation">
        <div class="drawer-header"><span class="eyebrow">Investigate now · ${esc(issue.owner || "Unknown")}</span><h2>${esc(issue.title || issue.id)}</h2><div class="subtle-note">${esc(locationOf(issue))}</div></div>
        <div class="investigation-hero">
          <div class="frontline-card-top"><span class="frontline-state">${esc(stateLabel(issue))}</span><strong>${esc(age(issue.last_transition_at || issue.updated_at || issue.created_at))}</strong></div>
          <div class="investigation-grid">
            <div class="investigation-fact"><span>What is happening now?</span><strong>${esc(latestText(issue))}</strong></div>
            <div class="investigation-fact"><span>What are we waiting for?</span><strong>${esc(waitingFor(issue))}</strong></div>
            <div class="investigation-fact"><span>Who owns it?</span><strong>${esc(issue.owner || "Unknown")}</strong></div>
            <div class="investigation-fact"><span>Latest update</span><strong>${esc(latest ? `${shortClock(latest.at)} · ${latestText(issue)}` : shortDate(issue.updated_at || issue.created_at))}</strong></div>
          </div>
          ${human ? `<div class="investigation-fact"><span>Frontline reach</span><strong>${esc(humanStatus)}${human.destination_display_name ? ` · ${esc(human.destination_display_name)}` : ""}</strong></div>` : ""}
          ${actionButton(issue, plans)}
          <div class="frontline-error"></div>
        </div>
        <details><summary>Past activity</summary>${historyItems(issue)}</details>
        <details><summary>Evidence & verification</summary>${evidence.length ? evidence.map((item) => `<div class="frontline-history-item"><strong>${esc(item.evidence_type || "Evidence")}</strong><br>Source: ${esc(item.source || "—")}<br>${item.verified_by ? `Verified by ${esc(item.verified_by)}` : "Awaiting independent verification"}</div>`).join("") : '<div class="frontline-empty">No trusted evidence recorded.</div>'}</details>
        <details><summary>State Authority audit</summary>${transitions.length ? transitions.map((item) => `<div class="frontline-history-item"><strong>${esc(item.from_state || "")} → ${esc(item.to_state || "")}</strong><br>${esc(item.principal || "")}<br><small>${esc(shortDate(item.committed_at))}</small></div>`).join("") : '<div class="frontline-empty">No State Authority events.</div>'}</details>
        ${plans.length ? `<details><summary>Recovery history</summary>${plans.map((plan) => `<div class="frontline-history-item"><strong>${esc(plan.recommended_action || "Recovery plan")}</strong> · ${esc(plan.status || "")}<br>${esc(plan.recommendation || "")}<br><small>${esc(plan.authority_boundary || "")}</small></div>`).join("")}</details>` : ""}
        <details><summary>Full audit trace</summary><div class="frontline-history-item">Open the immutable governed lifecycle trace when detailed investigation is required.<br><a href="/trace/${encodeURIComponent(issue.id)}">Open full lifecycle trace</a></div></details>
      </div>`;
      openDrawer(content);
      document.querySelectorAll("[data-frontline-action]").forEach((button) => button.addEventListener("click", () => performAction(button)));
    } catch (error) {
      openDrawer(`<div class="frontline-investigation"><div class="drawer-header"><h2>Unable to open issue</h2></div><div class="frontline-error">${esc(error.message)}</div></div>`);
    }
  }

  async function openPast() {
    try {
      if (!cache.shift) await loadNow();
      const shiftStart = cache.shift?.start || fallbackShiftStart();
      const active = cache.issues.filter((issue) => !TERMINAL.has(String(issue.state || "")));
      const carried = active.filter((issue) => {
        const stamp = issueStamp(issue);
        return !stamp || stamp < shiftStart;
      });
      const completed = cache.issues
        .filter((issue) => TERMINAL.has(String(issue.state || "")))
        .slice(0, MAX_RECENT_HISTORY);
      const [intelligence] = await Promise.all([
        requestJson("/api/intelligence").catch(() => null),
      ]);
      const recommendations = Array.isArray(intelligence?.recommendations) ? intelligence.recommendations : [];
      const content = `<div class="frontline-investigation">
        <div class="drawer-header"><span class="eyebrow">Past · available when needed</span><h2>History & carried work</h2><div class="subtle-note">Live Operations stays focused on the current shift. Nothing is deleted.</div></div>
        <section class="past-section"><h3>Carried from earlier shifts · ${carried.length}</h3>${carried.length ? carried.map((issue) => `<div class="past-row"><button data-frontline-issue="${esc(issue.id)}">${esc(issue.owner)} · ${esc(issue.title || issue.id)}</button><span>${esc(stateLabel(issue))} · ${esc(age(issue.last_transition_at || issue.updated_at || issue.created_at))}</span></div>`).join("") : '<div class="frontline-empty">No carried-forward work.</div>'}</section>
        <section class="past-section"><h3>Recently completed / failed</h3>${completed.length ? completed.map((issue) => `<div class="past-row"><button data-frontline-issue="${esc(issue.id)}">${esc(issue.owner)} · ${esc(issue.title || issue.id)}</button><span>${esc(stateLabel(issue))} · ${esc(shortDate(issue.updated_at || issue.created_at))}</span></div>`).join("") : '<div class="frontline-empty">No recent history.</div>'}</section>
        <details class="past-section"><summary>Shift snapshots · ${cache.shifts.length}</summary>${cache.shifts.length ? cache.shifts.slice(0, 10).map((snapshot) => `<div class="frontline-history-item"><strong>${esc(snapshot.outgoing_shift || "Shift")} → ${esc(snapshot.incoming_shift || "Shift")}</strong><br>${esc(snapshot.unresolved_count || 0)} unresolved · ${esc(shortDate(snapshot.created_at))}</div>`).join("") : '<div class="frontline-empty">No shift snapshots.</div>'}</details>
        <details class="past-section"><summary>Management insight · Operational Improvement Advisor</summary>${recommendations.length ? recommendations.map((item) => `<div class="advisor-card"><strong>${esc(item.pattern || "Pattern")}</strong><span>${esc(item.recommended_change || "")}</span><span>Why: ${esc(item.why_it_matters || "")}</span><span>Confidence: ${esc(item.confidence || "—")} · Scope: ${esc(item.affected_scope || "—")}</span></div>`).join("") : '<div class="frontline-empty">No advisory recommendations available.</div>'}</details>
      </div>`;
      openDrawer(content);
      bindCards(document.querySelector("#drawer-content") || document);
    } catch (error) {
      openDrawer(`<div class="frontline-investigation"><div class="drawer-header"><h2>Past unavailable</h2></div><div class="frontline-error">${esc(error.message)}</div></div>`);
    }
  }

  function enhanceIntakeProgress() {
    const submit = document.querySelector("#submit-handover");
    const status = document.querySelector("#intake-status");
    if (!submit || !status || document.querySelector("#frontline-intake-progress")) return;
    const progress = document.createElement("div");
    progress.id = "frontline-intake-progress";
    progress.className = "frontline-intake-progress";
    progress.innerHTML = `<strong>Governed intake is running</strong><div class="frontline-progress-track"><div class="frontline-progress-bar"></div></div><div class="frontline-progress-steps">Agent Gateway + Model Armor → Agent Runtime interpretation → Coverage Critic → State Authority persistence & dispatch<br><em>Only the returned server result is treated as completed; this indicator does not fake intermediate success.</em></div>`;
    status.insertAdjacentElement("afterend", progress);
    submit.addEventListener("click", () => {
      const text = document.querySelector("#handover")?.value.trim();
      if (text) progress.classList.add("active");
    }, true);
    const observer = new MutationObserver(() => {
      if (status.textContent && status.textContent !== "Processing governed intake…") {
        progress.classList.remove("active");
        setTimeout(loadNow, 500);
      }
    });
    observer.observe(status, { childList: true, subtree: true, characterData: true });
  }

  function handleDeepLink() {
    const issueId = new URLSearchParams(window.location.search).get("issue");
    if (!issueId) return;
    if (!/^[A-Za-z0-9_-]{1,128}$/.test(issueId)) {
      console.warn("Ignoring invalid issue deep link");
      return;
    }
    openFrontlineIssue(issueId);
  }

  window.addEventListener("load", async () => {
    injectStyles();
    shell();
    enhanceIntakeProgress();
    window.openFrontlineIssue = openFrontlineIssue;
    await loadNow();
    handleDeepLink();
    window.setInterval(loadNow, 7000);
  });
})();
