(() => {
  "use strict";

  const drawerContent = () => document.querySelector("#drawer-content");

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

  function currentIssueId(root) {
    const action = root.querySelector("[data-frontline-action][data-issue-id]");
    if (action?.dataset.issueId) return action.dataset.issueId;
    const trace = root.querySelector('a[href^="/trace/"]');
    if (!trace) return null;
    const value = trace.getAttribute("href") || "";
    const match = value.match(/^\/trace\/([A-Za-z0-9_-]{1,128})$/);
    return match ? match[1] : null;
  }

  function controlMarkup(issue, plans) {
    if (issue.state !== "ACTION_PENDING") return "";

    const matching = plans.filter((plan) => plan.state_observed === issue.state);
    const sanctioned = matching.find((plan) => plan.status === "SANCTIONED");
    if (sanctioned) {
      return `<div class="recovery-control recovery-sanctioned"><strong>Controlled recovery sanctioned</strong><span>${escapeText(sanctioned.recommended_action || "Fresh evidence authorized")}</span></div>`;
    }

    const proposed = matching.find((plan) => plan.status === "PROPOSED");
    if (proposed) {
      return `<div class="recovery-control"><span class="recovery-kicker">Controlled recovery</span><strong>${escapeText(proposed.recommended_action || "Recovery plan")}</strong><p>${escapeText(proposed.recommendation || "")}</p><button type="button" class="frontline-primary" data-recovery-action="sanction" data-issue-id="${escapeText(issue.id)}" data-plan-id="${escapeText(proposed.id)}">Sanction recovery plan</button><div class="frontline-error"></div></div>`;
    }

    return `<div class="recovery-control"><span class="recovery-kicker">Recovery option</span><p>Create a bounded advisory plan from current authoritative state. The planner cannot mutate work, record evidence, or close the issue.</p><button type="button" class="secondary-button" data-recovery-action="plan" data-issue-id="${escapeText(issue.id)}">Generate controlled recovery plan</button><div class="frontline-error"></div></div>`;
  }

  function escapeText(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  async function perform(button) {
    const issueId = button.dataset.issueId;
    const action = button.dataset.recoveryAction;
    const planId = button.dataset.planId;
    if (!issueId || !action) return;

    const original = button.textContent;
    button.disabled = true;
    button.textContent = action === "sanction" ? "Sanctioning…" : "Planning safely…";

    try {
      const path = action === "sanction"
        ? `/api/issues/${encodeURIComponent(issueId)}/recovery-plans/${encodeURIComponent(planId)}/sanction`
        : `/api/issues/${encodeURIComponent(issueId)}/recovery-plan`;
      await requestJson(path, { method: "POST" });
      if (typeof window.frontlineRefreshNow === "function") await window.frontlineRefreshNow();
      if (typeof window.openFrontlineIssue === "function") await window.openFrontlineIssue(issueId);
    } catch (error) {
      button.disabled = false;
      button.textContent = original;
      const node = button.parentElement?.querySelector(".frontline-error");
      if (node) node.textContent = error.message;
    }
  }

  async function enhanceDrawer() {
    const root = drawerContent();
    if (!root || !root.querySelector(".frontline-investigation")) return;
    if (root.querySelector("[data-recovery-controls-ready='1']")) return;

    const issueId = currentIssueId(root);
    if (!issueId) return;

    try {
      const payload = await requestJson(`/api/issues/${encodeURIComponent(issueId)}`);
      const issue = payload?.issue || {};
      const plans = Array.isArray(payload?.recovery_plans) ? payload.recovery_plans : [];
      const markup = controlMarkup(issue, plans);
      if (!markup) return;

      const host = document.createElement("div");
      host.dataset.recoveryControlsReady = "1";
      host.className = "recovery-controls-host";
      host.innerHTML = markup;

      const hero = root.querySelector(".investigation-hero");
      if (hero) hero.insertAdjacentElement("afterend", host);
      else root.appendChild(host);

      host.querySelectorAll("[data-recovery-action]").forEach((button) => {
        button.addEventListener("click", () => perform(button));
      });
    } catch (_error) {
      // The core issue drawer remains usable if recovery controls cannot load.
    }
  }

  const observer = new MutationObserver(() => enhanceDrawer());
  window.addEventListener("DOMContentLoaded", () => {
    observer.observe(document.body, { childList: true, subtree: true });
    enhanceDrawer();
  });
})();
