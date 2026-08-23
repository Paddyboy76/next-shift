(() => {
  "use strict";

  const STORAGE_KEY = "next-shift-theme";
  const root = document.documentElement;

  function storedTheme() {
    try {
      const value = window.localStorage.getItem(STORAGE_KEY);
      return value === "light" || value === "dark" ? value : null;
    } catch (_error) {
      return null;
    }
  }

  function applyTheme(theme) {
    const resolved = theme === "light" ? "light" : "dark";
    root.dataset.theme = resolved;

    const button = document.querySelector("#theme-toggle");
    if (button) {
      const next = resolved === "dark" ? "light" : "dark";
      button.textContent = next === "light" ? "Light mode" : "Dark mode";
      button.setAttribute("aria-label", `Switch to ${next} mode`);
      button.setAttribute("aria-pressed", resolved === "light" ? "true" : "false");
    }
  }

  function saveTheme(theme) {
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
    } catch (_error) {
      // The UI still switches even if storage is unavailable.
    }
  }

  applyTheme(storedTheme() || "dark");

  window.addEventListener("DOMContentLoaded", () => {
    const strip = document.querySelector(".security-strip");
    if (!strip || document.querySelector("#theme-toggle")) return;

    const button = document.createElement("button");
    button.id = "theme-toggle";
    button.type = "button";
    strip.appendChild(button);

    applyTheme(root.dataset.theme || "dark");

    button.addEventListener("click", () => {
      const next = root.dataset.theme === "light" ? "dark" : "light";
      applyTheme(next);
      saveTheme(next);
    });
  });
})();
