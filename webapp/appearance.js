/* Read before styles render so a saved light theme does not flash green. */
(function () {
  const root = document.documentElement;
  function apply() {
    root.dataset.design = "modern";
    root.dataset.colorScheme = "dark";
    root.dataset.theme = "black";
    window.dispatchEvent(new Event("appearancechange"));
  }
  // Compatibility with already open clients; legacy preferences cannot restore the old UI.
  function choose() { apply(); }
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
    let amount = "Начнём?", caption = "Добавьте устройство — настройка займёт пару минут";
    if (me.balance_enabled && devices.length && !phones.length) {
      amount = "Роутер"; caption = "Срок доступа — в карточке роутера";
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
    const changed = value.textContent !== amount;
    value.textContent = amount;
    if (changed && window.WayMotion) window.WayMotion.value(value);
    label.textContent = caption;
    value.dataset.state = empty ? "empty" : "ready";
    const daily = Number(me.vpn_day_price_rub);
    rate.textContent = devices.length && !phones.length ? "Роутер оплачивается отдельно" : !phones.length ? "Без устройств списаний нет" : me.billing_paused ? "Списания приостановлены" : me.balance_enabled && Number.isFinite(daily) && daily > 0 ? `${(daily * phones.length).toLocaleString("ru-RU")} ₽ в сутки · ${phones.length} устр.` : "Выберите устройство для настройки";
  }
  function assign() {}
  window.WayAppearance = { apply, choose, paintSummary, assign };
  apply();
  document.addEventListener("DOMContentLoaded", () => {
    apply();
    const details = document.getElementById("modernReferralDetails");
    if (details) details.addEventListener("click", () => window.openReferrals());
  });
})();
