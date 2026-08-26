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
    if (state === "WAITING" || state === "ACTION_PENDING" || state === "CLAIMED · UNVERIFIED") return 3;
    if (state === "VERIFYING") return 4;
    if (state === "VERIFIED" || state === "CLOSED") return 5;
    if (state === "BLOCKED" || state === "NEEDS DECISION" || state === "FAILED") return 2;
    return 0;
  };

  const stageForTransition = (text) => {
    const value = String(text || "").toUpperCase();
    const target = value.includes("→") ? value.split("→").pop().trim() : value;
    if (target.includes("ACTION_PENDING") || target === "WAITING") return 3;
    if (target.includes("VERIFYING")) return 4;
    if (target.includes("CLOSED") || target.includes("VERIFIED")) return 4;
    if (target.includes("ASSIGNED")) return 2;
    if (target.includes("TRIAGED")) return 1;
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

  function stageMarker(item, isCurrent) {
    const transition = item.querySelector("strong")?.textContent || "";
    const stageIndex = stageForTransition(transition);
    const marker = document.createElement("span");
    marker.className = `past-stage-marker stage-${stageIndex + 1}${isCurrent ? " is-current" : ""}`;
    marker.textContent = String(stageIndex + 1);
    marker.title = stages[stageIndex]?.label || "Lifecycle stage";
    return marker;
  }

  function enhanceTimeline(details, kind, openByDefault) {
    if (!details || details.dataset.lifecycleEnhanced === "1") return;
    const items = Array.from(details.querySelectorAll(":scope > .frontline-history-item"));
    if (!items.length) return;

    details.dataset.lifecycleEnhanced = "1";
    details.open = openByDefault;
    details.classList.add("past-activity-focus", `${kind}-focus`);

    items.forEach((item, index) => {
      const isCurrent = index === 0;
      item.classList.add("past-activity-item", `${kind}-item`);
      item.classList.toggle("is-current", isCurrent);
      item.prepend(stageMarker(item, isCurrent));
    });

    if (items.length > 1) {
      const earlier = document.createElement("details");
      earlier.className = "past-activity-earlier";
      earlier.innerHTML = `<summary>Earlier activity · ${items.length - 1}</summary>`;
      items.slice(1).forEach((item) => earlier.appendChild(item));
      details.appendChild(earlier);
    }
  }

  function enhanceDrawerTimelines() {
    const drawer = document.querySelector("#drawer-content");
    if (!drawer) return;
    const detailSections = Array.from(drawer.querySelectorAll(".frontline-investigation > details"));

    const findByLabels = (...labels) => {
      const normalized = new Set(labels.map((label) => String(label).trim().toLowerCase()));
      return detailSections.find((node) => {
        const text = node.querySelector(":scope > summary")?.textContent.trim().toLowerCase();
        return text && normalized.has(text);
      });
    };

    enhanceTimeline(findByLabels("past activity"), "past-activity", true);
    enhanceTimeline(
      findByLabels("state authority audit", "technical audit"),
      "technical-audit",
      false
    );
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
      enhanceDrawerTimelines();
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