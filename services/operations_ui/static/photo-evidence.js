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
        <small>Supporting visual evidence only · ${esc(record.model || "Gemini")}. Trusted source evidence and independent verification still control closure.</small>
      </div>`;
    }).join("");
  }

  function uploadMarkup(issueId) {
    return `<div class="visual-evidence-upload" data-photo-evidence-host="1">
      <div class="visual-evidence-head"><strong>Before / after photo proof</strong><span>Facilities</span></div>
      <p>Add a photo showing the problem before work and a photo after the repair. Gemini compares only what is visibly supported; it cannot close the issue.</p>
      <div class="visual-evidence-inputs">
        <label><span>Before</span><input type="file" accept="image/jpeg,image/png,image/webp" data-photo-kind="before"></label>
        <label><span>After</span><input type="file" accept="image/jpeg,image/png,image/webp" data-photo-kind="after"></label>
      </div>
      <button type="button" class="frontline-primary" data-photo-submit="1" data-issue-id="${esc(issueId)}">Submit before & after photo proof</button>
      <div class="frontline-error" data-photo-error="1"></div>
    </div>`;
  }

  async function submitPhotos(button) {
    const root = drawerContent();
    const host = button.closest("[data-photo-evidence-host]");
    const issueId = button.dataset.issueId;
    if (!root || !host || !issueId) return;
    const before = host.querySelector('[data-photo-kind="before"]')?.files?.[0];
    const after = host.querySelector('[data-photo-kind="after"]')?.files?.[0];
    const errorNode = host.querySelector("[data-photo-error]");
    if (!before || !after) {
      if (errorNode) errorNode.textContent = "Choose both a before photo and an after photo.";
      return;
    }
    const original = button.textContent;
    button.disabled = true;
    button.textContent = "Gemini is comparing the photos…";
    if (errorNode) errorNode.textContent = "";
    try {
      const form = new FormData();
      form.append("before", before, before.name || "before.jpg");
      form.append("after", after, after.name || "after.jpg");
      await requestJson(`/api/issues/${encodeURIComponent(issueId)}/photo-evidence`, {
        method: "POST",
        body: form,
      });
      if (typeof window.frontlineRefreshNow === "function") await window.frontlineRefreshNow();
      delete root.dataset.photoEvidenceIssue;
      if (typeof window.openFrontlineIssue === "function") await window.openFrontlineIssue(issueId);
    } catch (error) {
      button.disabled = false;
      button.textContent = original;
      if (errorNode) errorNode.textContent = error.message;
    }
  }

  async function enhanceDrawer() {
    const root = drawerContent();
    if (!root || !root.querySelector(".frontline-investigation")) return;
    const issueId = issueIdFromDrawer(root);
    if (!issueId) return;
    if (root.dataset.photoEvidenceIssue === issueId) return;

    // Synchronous guard prevents the MutationObserver from launching duplicate
    // async enhancement passes while the issue payload is loading.
    root.dataset.photoEvidenceIssue = issueId;

    try {
      const payload = await requestJson(`/api/issues/${encodeURIComponent(issueId)}`);
      const issue = payload?.issue || {};
      const records = Array.isArray(payload?.photo_evidence) ? payload.photo_evidence : [];
      const evidenceDetails = [...root.querySelectorAll("details")].find((node) =>
        node.querySelector("summary")?.textContent?.trim().toLowerCase().startsWith("evidence")
      );
      if (evidenceDetails && records.length) {
        const existing = evidenceDetails.querySelector("[data-photo-history]");
        if (!existing) {
          const history = document.createElement("div");
          history.dataset.photoHistory = "1";
          history.innerHTML = visualHistory(issueId, records);
          evidenceDetails.appendChild(history);
        }
      }

      if (issue.owner !== "Facilities" || issue.state !== "ACTION_PENDING") return;
      const existingComplete = root.querySelector('[data-frontline-action="complete"]');
      if (existingComplete) existingComplete.hidden = true;
      if (root.querySelector("[data-photo-evidence-host]")) return;
      const host = document.createElement("div");
      host.innerHTML = uploadMarkup(issueId);
      const node = host.firstElementChild;
      const hero = root.querySelector(".investigation-hero");
      if (node && hero) hero.insertAdjacentElement("afterend", node);
      node?.querySelector("[data-photo-submit]")?.addEventListener("click", (event) => submitPhotos(event.currentTarget));
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
