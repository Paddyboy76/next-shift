(() => {
  "use strict";

  const drawerContent = () => document.querySelector("#drawer-content");

  const esc = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");

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

  function issueIdFromDrawer(root) {
    const action = root.querySelector("[data-frontline-action][data-issue-id]");
    if (action?.dataset.issueId) return action.dataset.issueId;
    const trace = root.querySelector('a[href^="/trace/"]');
    const href = trace?.getAttribute("href") || "";
    const match = href.match(/^\/trace\/([A-Za-z0-9_-]{1,128})$/);
    return match ? match[1] : null;
  }

  function visualHistory(issueId, records) {
    if (!records.length) return "";
    return records.map((record) => {
      const inspection = record.inspection || {};
      const id = encodeURIComponent(record.id || "");
      return `<div class="visual-evidence-record">
        <div class="visual-evidence-head"><strong>Gemini visual comparison</strong><span>${inspection.completion_supported === true ? "Supports repair" : "Needs review"}</span></div>
        <div class="visual-evidence-images">
          <figure><img src="/api/issues/${encodeURIComponent(issueId)}/photo-evidence/${id}/before" alt="Before repair photo"><figcaption>Before</figcaption></figure>
          <figure><img src="/api/issues/${encodeURIComponent(issueId)}/photo-evidence/${id}/after" alt="After repair photo"><figcaption>After</figcaption></figure>
        </div>
        <p>${esc(inspection.summary || "Visual inspection recorded.")}</p>
        <small>Captured through Google Chat Human Reach · supporting visual evidence only · ${esc(record.model || "Gemini")}. Trusted source evidence and independent verification still control closure.</small>
      </div>`;
    }).join("");
  }

  async function enhanceDrawer() {
    const root = drawerContent();
    if (!root || !root.querySelector(".frontline-investigation")) return;
    const issueId = issueIdFromDrawer(root);
    if (!issueId) return;
    if (root.dataset.photoEvidenceIssue === issueId) return;

    // Synchronous guard prevents duplicate async enhancement passes.
    root.dataset.photoEvidenceIssue = issueId;

    try {
      const payload = await requestJson(`/api/issues/${encodeURIComponent(issueId)}`);
      const records = Array.isArray(payload?.photo_evidence) ? payload.photo_evidence : [];
      if (!records.length) return;

      const evidenceDetails = [...root.querySelectorAll("details")].find((node) =>
        node.querySelector("summary")?.textContent?.trim().toLowerCase().startsWith("evidence")
      );
      if (!evidenceDetails || evidenceDetails.querySelector("[data-photo-history]")) return;

      const history = document.createElement("div");
      history.dataset.photoHistory = "1";
      history.innerHTML = visualHistory(issueId, records);
      evidenceDetails.appendChild(history);
    } catch (_error) {
      // Core drawer remains usable if visual evidence is unavailable.
    }
  }

  window.addEventListener("DOMContentLoaded", () => {
    const root = drawerContent();
    if (!root) return;
    const observer = new MutationObserver(() => enhanceDrawer());
    observer.observe(root, { childList: true, subtree: true });
    enhanceDrawer();
  });
})();
