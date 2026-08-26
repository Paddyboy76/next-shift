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

  const stageClasses = (stage, index, currentIndex, completeAll, prefix) => {
    const isComplete = completeAll ? index < stages.length - 1 : index < currentIndex;
    const isActive = completeAll ? index === stages.length - 1 : index === currentIndex;
    return [
      `${prefix}-stage`,
      `${prefix}-${stage.key}`,
      isComplete ? "is-complete" : "",
      isActive ? "is-active" : "",
    ].filter(Boolean).join(" ");
  };

  function setCurrentStageClass(stateNode, stageKey, completeAll) {
    if (!stateNode) return;
    stages.forEach((stage) => stateNode.classList.remove(`lifecycle-current-${stage.key}`));
    stateNode.classList.toggle("lifecycle-finished", completeAll);
    stateNode.classList.add(`lifecycle-current-${stageKey}`);
  }

  function renderDrawerLifecycle() {
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
    const currentStage = stages[currentIndex];
    setCurrentStageClass(stateNode, currentStage.key, completeAll);

    const items = stages.map((stage, index) => (
      `<li class="${stageClasses(stage, index, currentIndex, completeAll, "issue-lifecycle")}"><strong>${index + 1}</strong><span>${stage.label}</span></li>`
    )).join("");

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

  function renderCardLifecycle(card) {
    const stateNode = card.querySelector(".frontline-state");
    if (!stateNode) return;

    const stateLabel = stateNode.textContent.trim();
    const activeIndex = stageForState(stateLabel);
    const completeAll = activeIndex >= stages.length;
    const currentIndex = completeAll ? stages.length - 1 : activeIndex;
    const currentStage = stages[currentIndex];
    const signature = `${stateLabel}|${currentIndex}|${completeAll}`;
    setCurrentStageClass(stateNode, currentStage.key, completeAll);
    card.dataset.lifecycleStage = currentStage.key;

    let lifecycle = card.querySelector(":scope > .card-lifecycle");
    if (lifecycle?.dataset.signature === signature) return;

    const items = stages.map((stage, index) => (
      `<span class="${stageClasses(stage, index, currentIndex, completeAll, "card-lifecycle")}" title="${stage.label}"><strong>${index + 1}</strong><em>${stage.label}</em></span>`
    )).join("");

    if (!lifecycle) {
      lifecycle = document.createElement("div");
      lifecycle.className = "card-lifecycle";
      lifecycle.setAttribute("aria-label", "Issue lifecycle progress");
      const cardTop = card.querySelector(".frontline-card-top");
      if (cardTop) cardTop.insertAdjacentElement("afterend", lifecycle);
      else card.prepend(lifecycle);
    }

    lifecycle.dataset.signature = signature;
    lifecycle.classList.toggle("is-finished", completeAll);
    lifecycle.innerHTML = items;
  }

  function renderCardLifecycles() {
    document.querySelectorAll(".frontline-card").forEach(renderCardLifecycle);
  }

  let queued = false;
  function scheduleRender() {
    if (queued) return;
    queued = true;
    window.requestAnimationFrame(() => {
      queued = false;
      renderDrawerLifecycle();
      renderCardLifecycles();
    });
  }

  window.addEventListener("load", () => {
    const drawer = document.querySelector("#drawer-content");
    if (drawer) {
      const drawerObserver = new MutationObserver(scheduleRender);
      drawerObserver.observe(drawer, { childList: true, subtree: true });
    }

    const mainObserver = new MutationObserver(scheduleRender);
    mainObserver.observe(document.body, { childList: true, subtree: true });
    scheduleRender();
  });
})();