(() => {
  "use strict";

  const TEAM_LABELS = new Map([
    ["Facilities", "Facilities"],
    ["AssetLogistics", "Assets & Logistics"],
    ["LanguageAccess", "Language Access"],
    ["DischargeDME", "Discharge Equipment"],
    ["EVSThroughput", "Environmental Services"],
    ["PatientTransport", "Patient Transport"],
  ]);

  let activeTeam = "ALL";

  function setText(element, value) {
    if (element && element.textContent !== value) element.textContent = value;
  }

  function teamKeyFromText(value) {
    const text = String(value || "").trim();
    for (const [key, label] of TEAM_LABELS.entries()) {
      if (
        text === key ||
        text.startsWith(`${key} ·`) ||
        text === label ||
        text.startsWith(`${label} ·`)
      ) {
        return key;
      }
    }
    return null;
  }

  function decorateOwnerLabels(root = document) {
    root.querySelectorAll(".frontline-owner").forEach((element) => {
      const original = element.textContent.trim();
      const ownerKey = element.dataset.ownerKey || teamKeyFromText(original);
      if (!ownerKey) return;

      element.dataset.ownerKey = ownerKey;
      const carried = original.includes("· carried");
      const desired = `${TEAM_LABELS.get(ownerKey)}${carried ? " · carried" : ""}`;
      setText(element, desired);
    });

    root.querySelectorAll(".past-row button").forEach((button) => {
      const parts = button.textContent.split(" · ");
      const ownerKey = teamKeyFromText(parts[0]);
      if (!ownerKey) return;
      parts[0] = TEAM_LABELS.get(ownerKey);
      setText(button, parts.join(" · "));
    });
  }

  function decorateInvestigationOwner(root = document) {
    root.querySelectorAll(".frontline-investigation .drawer-header .eyebrow").forEach((element) => {
      const text = element.textContent.trim();
      if (!text.toLowerCase().startsWith("investigate now")) return;
      const ownerText = text.split("·").slice(1).join("·").trim();
      const ownerKey = teamKeyFromText(ownerText);
      if (ownerKey) setText(element, `Investigate now · ${TEAM_LABELS.get(ownerKey)}`);
    });

    root.querySelectorAll(".frontline-investigation .investigation-fact").forEach((fact) => {
      const label = fact.querySelector(":scope > span");
      const value = fact.querySelector(":scope > strong");
      if (!label || !value) return;

      const labelText = label.textContent.trim().toLowerCase();
      if (labelText === "who owns it?") setText(label, "Handled by");

      if (label.textContent.trim().toLowerCase() === "handled by") {
        const ownerKey = teamKeyFromText(value.textContent);
        if (ownerKey) setText(value, TEAM_LABELS.get(ownerKey));
      }
    });
  }

  function collectTeamCounts(shell) {
    const counts = Object.fromEntries([...TEAM_LABELS.keys()].map((key) => [key, 0]));
    const seen = new Set();

    shell.querySelectorAll(".frontline-card[data-frontline-issue]").forEach((card) => {
      const issueId = card.dataset.frontlineIssue;
      if (!issueId || seen.has(issueId)) return;
      seen.add(issueId);

      const owner = card.querySelector(".frontline-owner");
      const ownerKey = owner?.dataset.ownerKey || teamKeyFromText(owner?.textContent);
      if (ownerKey && counts[ownerKey] !== undefined) counts[ownerKey] += 1;
    });

    return { counts, total: seen.size };
  }

  function teamButton(ownerKey, label, count, active, disabled = false) {
    return `<button type="button" class="frontline-team-chip${active ? " active" : ""}${disabled ? " empty" : ""}" data-team-owner="${ownerKey}" aria-pressed="${active ? "true" : "false"}"${disabled ? " disabled" : ""}>
      <span>${label}</span><strong>${count}</strong>
    </button>`;
  }

  function renderTeamButtons(strip, shell) {
    const buttons = strip.querySelector(".frontline-team-buttons");
    if (!buttons) return;

    const { counts, total } = collectTeamCounts(shell);
    if (activeTeam !== "ALL" && !counts[activeTeam]) activeTeam = "ALL";

    const signature = JSON.stringify({ activeTeam, total, counts });
    if (buttons.dataset.signature === signature) return;
    buttons.dataset.signature = signature;

    const items = [
      teamButton("ALL", "All current work", total, activeTeam === "ALL"),
      ...[...TEAM_LABELS.entries()].map(([key, label]) =>
        teamButton(key, label, counts[key], activeTeam === key, counts[key] === 0)
      ),
    ];
    buttons.innerHTML = items.join("");
  }

  function syncFilteredSection(gridSelector, countSelector) {
    const grid = document.querySelector(gridSelector);
    if (!grid) return;

    const cards = [...grid.querySelectorAll(".frontline-card[data-frontline-issue]")];
    const visible = cards.filter((card) => !card.hidden).length;
    const count = document.querySelector(countSelector);
    setText(count, `${visible} item${visible === 1 ? "" : "s"}`);

    const section = grid.closest(".frontline-section");
    section?.classList.toggle("team-filter-no-visible", activeTeam !== "ALL" && visible === 0);
  }

  function applyTeamFilter(shell) {
    shell.querySelectorAll(".frontline-card[data-frontline-issue]").forEach((card) => {
      const owner = card.querySelector(".frontline-owner");
      const ownerKey = owner?.dataset.ownerKey || teamKeyFromText(owner?.textContent);
      card.hidden = activeTeam !== "ALL" && ownerKey !== activeTeam;
    });

    syncFilteredSection("#frontline-attention-grid", "#frontline-attention-count");
    syncFilteredSection("#frontline-live-grid", "#frontline-live-count");
  }

  function ensureTeamStrip(root = document) {
    const shell = root.querySelector("#frontline-shell") || document.querySelector("#frontline-shell");
    const topbar = shell?.querySelector(".frontline-topbar");
    if (!shell || !topbar) return;

    let strip = shell.querySelector("#frontline-team-strip");
    if (!strip) {
      strip = document.createElement("section");
      strip.id = "frontline-team-strip";
      strip.className = "frontline-team-strip";
      strip.setAttribute("aria-label", "Operational teams handling current shift work");
      strip.innerHTML = `
        <div class="frontline-team-strip-head">
          <div><span class="eyebrow">Operational teams</span><strong>Who is handling this shift</strong></div>
          <span>Tap a team to focus current work</span>
        </div>
        <div class="frontline-team-buttons"></div>`;
      topbar.insertAdjacentElement("afterend", strip);

      strip.addEventListener("click", (event) => {
        const button = event.target.closest("[data-team-owner]");
        if (!button || button.disabled) return;
        activeTeam = button.dataset.teamOwner || "ALL";
        apply(document);
      });
    }

    renderTeamButtons(strip, shell);
    applyTeamFilter(shell);
  }

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
    decorateOwnerLabels(root);
    decorateInvestigationOwner(root);
    decoratePastSections(root);
    decoratePastRows(root);
    ensureTeamStrip(root);
  }

  window.addEventListener("DOMContentLoaded", () => {
    apply(document);
    const observer = new MutationObserver(() => apply(document));
    observer.observe(document.body, { childList: true, subtree: true });
  });
})();
