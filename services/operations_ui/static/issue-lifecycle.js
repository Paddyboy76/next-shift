(() => {
  "use strict";

  const stages = [
    { key: "interpret", label: "Interpret" },
    { key: "route", label: "Route" },
    { key: "execute", label: "Execute" },
    { key: "prove", label: "Prove" },
    { key: "verify", label: "Verify" },
  ];

  const stageForState = (label) => {
    const state = String(label || "").trim().toUpperCase();
    if (state === "RECEIVED") return 0;
    if (state === "TRIAGED") return 1;
    if (state === "ASSIGNED") return 2;
    if (state === "WAITING" || state === "CLAIMED · UNVERIFIED") return 3;
    if (state === "VERIFYING") return 4;
    if (state === "VERIFIED") return 5;
    if (state === "BLOCKED" || state === "NEEDS DECISION" || state === "FAILED") return 2;
    return 0;
  };

  const statusCopy = (label, index) => {
    const state = String(label || "").trim().toUpperCase();
    if (state === "VERIFIED") return "Verified closed";
    if (state === "VERIFYING") return "Independent verification";
    if (state === "WAITING" || state === "CLAIMED · UNVERIFIED") return "Trusted evidence required";
    if (state === "ASSIGNED") return "Operational work in progress";
    if (state === "TRIAGED") return "Routing to specialist";
    if (state === "RECEIVED") return "Interpreting handover";
    if (state === "BLOCKED") return "Execution blocked";
    if (state === "NEEDS DECISION") return "Human decision required";
    if (state === "FAILED") return "Workflow requires review";
    return stages[Math.min(index, stages.length - 1)]?.label || "Lifecycle";
  };

  function renderLifecycle() {
    const drawer = document.querySelector("#drawer-content");
    if (!drawer) return;

    drawer.querySelectorAll(".issue-lifecycle").forEach((node) => node.remove());

    const investigation = drawer.querySelector(".frontline-investigation");
    const header = investigation?.querySelector(":scope > .drawer-header");
    const hero = investigation?.querySelector(":scope > .investigation-hero");
    const stateNode = hero?.querySelector(".frontline-state");
    if (!investigation || !header || !hero || !stateNode) return;

    const activeIndex = stageForState(stateNode.textContent);
    const completeAll = activeIndex >= stages.length;
    const currentIndex = completeAll ? stages.length - 1 : activeIndex;

    const items = stages.map((stage, index) => {
      const isComplete = completeAll || index < currentIndex;
      const isActive = !completeAll && index === currentIndex;
      const classes = [
        "issue-lifecycle-stage",
        `issue-lifecycle-${stage.key}`,
        isComplete ? "is-complete" : "",
        isActive ? "is-active" : "",
      ].filter(Boolean).join(" ");
      return `<li class="${classes}"><strong>${index + 1}</strong><span>${stage.label}</span></li>`;
    }).join("");

    const lifecycle = document.createElement("section");
    lifecycle.className = `issue-lifecycle${completeAll ? " is-finished" : ""}`;
    lifecycle.setAttribute("aria-label", "Issue lifecycle progress");
    lifecycle.innerHTML = `
      <div class="issue-lifecycle-heading">
        <span>Operational lifecycle</span>
        <strong>${statusCopy(stateNode.textContent, currentIndex)}</strong>
      </div>
      <ol>${items}</ol>`;

    header.insertAdjacentElement("afterend", lifecycle);
  }

  window.addEventListener("load", () => {
    const drawer = document.querySelector("#drawer-content");
    if (!drawer) return;
    const observer = new MutationObserver(renderLifecycle);
    observer.observe(drawer, { childList: true, subtree: true });
    renderLifecycle();
  });
})();