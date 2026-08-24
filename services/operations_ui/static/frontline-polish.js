(() => {
  "use strict";

  function decoratePastSections(root = document) {
    root.querySelectorAll(".past-section").forEach((section) => {
      const heading = section.querySelector(":scope > h3");
      if (!heading) return;
      const text = heading.textContent.trim().toLowerCase();
      section.classList.toggle("past-section-carried", text.startsWith("carried from earlier shifts"));
      section.classList.toggle("past-section-history", text.startsWith("recently completed"));
    });
  }

  function statusParts(text) {
    const value = String(text || "").trim();
    const known = [
      ["CLAIMED · UNVERIFIED", "Reported complete", "claimed"],
      ["WAITING", "Waiting", "waiting"],
      ["VERIFYING", "Checking evidence", "verifying"],
      ["VERIFIED", "Verified complete", "verified"],
      ["CLOSED", "Verified complete", "verified"],
      ["BLOCKED", "Blocked", "blocked"],
      ["FAILED", "Failed", "failed"],
    ];

    for (const [prefix, label, kind] of known) {
      if (!value.startsWith(prefix)) continue;
      const remainder = value.slice(prefix.length).replace(/^\s*·\s*/, "");
      return { label, kind, remainder };
    }

    const [label, ...rest] = value.split(" · ");
    return { label: label || "Status", kind: "other", remainder: rest.join(" · ") };
  }

  function decoratePastRows(root = document) {
    root.querySelectorAll(".past-row > span").forEach((container) => {
      if (container.dataset.decoratedStatus === "1") return;
      container.dataset.decoratedStatus = "1";

      const parts = statusParts(container.textContent);
      container.textContent = "";

      const status = document.createElement("span");
      status.className = `past-status past-status-${parts.kind}`;
      status.textContent = parts.label;
      container.appendChild(status);

      if (parts.remainder) {
        const age = document.createElement("span");
        age.className = "past-age";
        age.textContent = parts.remainder;
        container.appendChild(age);
      }
    });
  }

  function apply(root = document) {
    decoratePastSections(root);
    decoratePastRows(root);
  }

  window.addEventListener("DOMContentLoaded", () => {
    apply(document);
    const observer = new MutationObserver(() => apply(document));
    observer.observe(document.body, { childList: true, subtree: true });
  });
})();
