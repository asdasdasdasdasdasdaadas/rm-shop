/* Read before styles render so a saved light theme does not flash green. */
(function () {
  const root = document.documentElement;
  const key = "way_appearance_v1";
  let state = { design: "classic", theme: "system" };
  try {
    const saved = JSON.parse(localStorage.getItem(key) || "null");
    if (saved && ["classic", "modern"].includes(saved.design)) state.design = saved.design;
    if (saved && ["system", "light", "dark"].includes(saved.theme)) state.theme = saved.theme;
  } catch (_) {}
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  function apply() {
    const telegram = window.Telegram && window.Telegram.WebApp;
    const system = telegram && telegram.initData ? telegram.colorScheme : (media.matches ? "dark" : "light");
    root.dataset.design = state.design;
    root.dataset.colorScheme = state.theme === "system" ? (system === "dark" ? "dark" : "light") : state.theme;
    document.querySelectorAll("[data-design-choice]").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.designChoice === state.design)));
    document.querySelectorAll("[data-mode-choice]").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.modeChoice === state.theme)));
    const modern = document.getElementById("modernThemeSettings");
    const classic = document.getElementById("classicThemeSettings");
    if (modern) modern.hidden = state.design !== "modern";
    if (classic) classic.hidden = state.design !== "classic";
    window.dispatchEvent(new Event("appearancechange"));
  }
  function choose(field, value) {
    if (field === "design" && !["classic", "modern"].includes(value)) return;
    if (field === "theme" && !["system", "light", "dark"].includes(value)) return;
    if (!["design", "theme"].includes(field)) return;
    state[field] = value;
    try { localStorage.setItem(key, JSON.stringify(state)); } catch (_) {}
    apply();
  }
  window.WayAppearance = { apply, choose };
  apply();
  if (media.addEventListener) media.addEventListener("change", apply);
  document.addEventListener("DOMContentLoaded", () => {
    apply();
    document.querySelectorAll("[data-design-choice]").forEach(button => button.addEventListener("click", () => choose("design", button.dataset.designChoice)));
    document.querySelectorAll("[data-mode-choice]").forEach(button => button.addEventListener("click", () => choose("theme", button.dataset.modeChoice)));
  });
})();
