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
  function plural(n, words) {
    return words[n % 100 >= 11 && n % 100 <= 14 ? 2 : n % 10 === 1 ? 0 : n % 10 >= 2 && n % 10 <= 4 ? 1 : 2];
  }
  // This is a presentation of server balances, never an independent access check.
  function paintSummary(me, {hours, empty}) {
    const value = document.getElementById("modernRemaining");
    const label = document.getElementById("modernRemainingLabel");
    const rate = document.getElementById("modernDeviceRate");
    if (!value || !label || !rate) return;
    const devices = me.devices || [];
    const phones = devices.filter(device => device.kind !== "router" && device.platform !== "router");
    let amount = "—", caption = "Добавьте устройство и подключайтесь";
    if (me.balance_enabled && devices.length && !phones.length) {
      caption = "Срок доступа — в карточке роутера";
    } else if (me.balance_enabled && me.billing_paused) {
      amount = "Ⅱ"; caption = "Списания приостановлены";
    } else if (empty) {
      amount = "0"; caption = "Пополните баланс для подключения";
    } else if (!me.balance_enabled && !me.has_access) {
      amount = "0"; caption = "Продлите доступ для подключения";
    } else if (phones.length || (!me.balance_enabled && me.has_access)) {
      if (hours <= 0) { amount = "0"; caption = "Доступ закончился"; }
      else if (hours < 1) { amount = "< 1"; caption = "часа доступа осталось"; }
      else if (hours < 24) { amount = String(Math.floor(hours)); caption = `${plural(Math.floor(hours), ["час", "часа", "часов"])} доступа`; }
      else { amount = String(Math.floor(hours / 24)); caption = `${plural(Math.floor(hours / 24), ["день", "дня", "дней"])} доступа`; }
    } else if (me.trial_available) {
      caption = "Ваш подарок ждёт ниже";
    }
    value.textContent = amount;
    label.textContent = caption;
    value.dataset.state = empty ? "empty" : "ready";
    const daily = Number(me.vpn_day_price_rub);
    rate.textContent = devices.length && !phones.length ? "Роутер оплачивается отдельно" : !phones.length ? "Без устройств списаний нет" : me.billing_paused ? "Списания приостановлены" : me.balance_enabled && Number.isFinite(daily) && daily > 0 ? `${(daily * phones.length).toLocaleString("ru-RU")} ₽ в сутки · ${phones.length} устр.` : "Выберите устройство для настройки";
  }
  window.WayAppearance = { apply, choose, paintSummary };
  apply();
  if (media.addEventListener) media.addEventListener("change", apply);
  document.addEventListener("DOMContentLoaded", () => {
    apply();
    const details = document.getElementById("modernReferralDetails");
    if (details) details.addEventListener("click", () => window.openReferrals());
    document.querySelectorAll("[data-design-choice]").forEach(button => button.addEventListener("click", () => choose("design", button.dataset.designChoice)));
    document.querySelectorAll("[data-mode-choice]").forEach(button => button.addEventListener("click", () => choose("theme", button.dataset.modeChoice)));
  });
})();
