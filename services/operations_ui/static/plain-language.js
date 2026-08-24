(() => {
  "use strict";

  const exactText = new Map([
    ["State Authority audit", "Technical audit"],
    ["Full audit trace", "Full audit trail"],
    ["Open full lifecycle trace", "Open full audit trail"],
    ["Next governed action", "Next step"],
    ["Generate controlled recovery plan", "Create recovery plan"],
    ["Run independent verifier", "Check evidence and verify"],
    ["Record trusted evidence", "Record completion evidence"],
    ["Record fresh trusted evidence", "Record fresh completion evidence"],
    ["Governed intake is running", "Preparing operational work"],
  ]);

  function translateExactLabels(root = document) {
    root.querySelectorAll("summary, button, a, strong, h2, h3").forEach((element) => {
      const current = element.textContent.trim();
      const replacement = exactText.get(current);
      if (replacement) element.textContent = replacement;
    });
  }

  function simplifyProgress(root = document) {
    const progress = root.querySelector(".frontline-progress-steps");
    if (!progress || progress.dataset.plainLanguage === "1") return;

    progress.dataset.plainLanguage = "1";
    progress.innerHTML = `
      Checking handover → identifying work → checking completeness → creating work → dispatching teams
      <details class="frontline-technical-process">
        <summary>Technical processing</summary>
        <span>Agent Gateway + Model Armor → Agent Runtime → Coverage Critic → State Authority</span>
      </details>`;
  }

  function apply(root = document) {
    translateExactLabels(root);
    simplifyProgress(root);
  }

  window.addEventListener("DOMContentLoaded", () => {
    apply(document);

    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (node.nodeType !== Node.ELEMENT_NODE) continue;
          apply(node);
        }
      }

      apply(document);
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  });
})();
