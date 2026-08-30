const tg = window.Telegram && window.Telegram.WebApp
  ? window.Telegram.WebApp
  : {
      ready() {},
      expand() {},
      initData: "",
      colorScheme: "light",
      showAlert: (m) => window.alert(m),
      showConfirm: (m, cb) => cb(window.confirm(m)),
      openLink: (u) => window.open(u, "_blank"),
      openTelegramLink: (u) => window.open(u, "_blank"),
      openInvoice() {},
      setHeaderColor() {},
      setBackgroundColor() {},
      onEvent() {},
      BackButton: { show() {}, hide() {}, onClick() {} },
      MainButton: {
        show() {},
        hide() {},
        setText() {},
        enable() {},
        disable() {},
        showProgress() {},
        hideProgress() {},
        onClick() {},
      },
      HapticFeedback: { impactOccurred() {}, notificationOccurred() {} },
    };

tg.ready();
tg.expand();

const $ = (id) => document.getElementById(id);

const PLATFORMS = [
  { id: "ios", title: "iPhone, iPad", hint: "IPHONE, IPAD" },
  { id: "android", title: "Android", hint: "ANDROID" },
  { id: "macos", title: "macOS", hint: "MACOS" },
  { id: "windows", title: "Windows", hint: "WINDOWS" },
  { id: "androidtv", title: "Android TV", hint: "ANDROID TV" },
  { id: "appletv", title: "Apple TV", hint: "APPLE TV" },
];

const CLIENTS = {
  incy: {
    id: "incy",
    name: "Incy",
    mark: "IN",
    stores: {
      ios: "https://apps.apple.com/search?term=Incy",
      macos: "https://apps.apple.com/search?term=Incy",
      appletv: "https://apps.apple.com/search?term=Incy",
    },
  },
  happ: {
    id: "happ",
    name: "Happ",
    mark: "H",
    stores: {
      ios: "https://apps.apple.com/app/id6504287215",
      macos: "https://apps.apple.com/app/id6504287215",
      appletv: "https://apps.apple.com/app/id6504287215",
      android: "https://play.google.com/store/apps/details?id=com.happproxy",
      androidtv: "https://play.google.com/store/apps/details?id=com.happproxy",
      windows: "https://github.com/Happ-proxy/happ-desktop/releases",
    },
  },
  v2rayng: {
    id: "v2rayng",
    name: "v2rayNG",
    mark: "v2",
    stores: {
      android: "https://play.google.com/store/apps/details?id=com.v2ray.ang",
      androidtv: "https://play.google.com/store/apps/details?id=com.v2ray.ang",
    },
  },
  v2rayn: {
    id: "v2rayn",
    name: "v2rayN",
    mark: "v2",
    stores: {
      windows: "https://github.com/2dust/v2rayN/releases",
    },
  },
};

function clientsFor(platform) {
  if (platform === "ios" || platform === "macos" || platform === "appletv") {
    return [CLIENTS.incy, CLIENTS.happ];
  }
  if (platform === "android" || platform === "androidtv") {
    return [CLIENTS.happ, CLIENTS.v2rayng];
  }
  return [CLIENTS.happ, CLIENTS.v2rayn];
}

function platformLabel(id) {
  const p = PLATFORMS.find((x) => x.id === id);
  return p ? p.title : id || "—";
}

function clientLabel(id) {
  return (CLIENTS[id] && CLIENTS[id].name) || id || "—";
}

function applyTheme() {
  try {
    tg.setHeaderColor("#0d1611");
    tg.setBackgroundColor("#0d1611");
  } catch (_e) {}
}

const GAUGE_C = 2 * Math.PI * 46;
const GAUGE_REF_DAYS = 30;
const FROGS = {
  neutral: "frogNeutral",
  happy: "frogHappy",
  worried: "frogWorried",
  sad: "frogSad",
};

function setFrog(expression) {
  Object.keys(FROGS).forEach((key) => {
    $(FROGS[key]).classList.toggle("hidden", key !== expression);
  });
}

function setGauge(pct, tone) {
  const el = $("gaugeValue");
  const p = Math.max(0, Math.min(1, Number(pct) || 0));
  el.style.strokeDashoffset = String(GAUGE_C - GAUGE_C * p);
  el.classList.remove("tone-empty", "tone-warn", "tone-ok");
  el.classList.add(tone === "warn" ? "tone-warn" : tone === "empty" ? "tone-empty" : "tone-ok");
}

function paintStatus(me) {
  const n = (me.devices || []).length;
  const left = me.balance_enabled ? me.days_left : me.days;
  const running = me.balance_enabled ? n > 0 : Boolean(me.has_access);
  if (me.balance_enabled) {
    $("balanceLine").innerHTML = `${me.balance_rub} <span>на счету</span>`;
  } else {
    $("balanceLine").innerHTML = `${daysLabel(me.days)} <span>подписки</span>`;
  }
  const pill = $("statusPill");
  const badge = $("daysBadge");
  if (!running) {
    setFrog("neutral");
    setGauge(0, "empty");
    badge.classList.add("hidden");
    pill.className = "status-pill";
    pill.innerHTML = '<span class="dot"></span> Тариф не запущен';
    $("statusNote").textContent = me.balance_enabled
      ? "Добавьте устройство — лягушка возьмётся за дело и покажет, на сколько дней хватит баланса."
      : "Оформите доступ — лягушка возьмётся за дело и покажет срок подписки.";
  } else if (left < 3) {
    setFrog("worried");
    setGauge(left / GAUGE_REF_DAYS, "warn");
    badge.classList.remove("hidden");
    badge.textContent = daysLabel(left);
    pill.className = "status-pill warn";
    pill.innerHTML = me.balance_enabled
      ? '<span class="dot"></span> Баланс заканчивается'
      : '<span class="dot"></span> Срок заканчивается';
    $("statusNote").textContent = me.balance_enabled
      ? `При текущем расходе осталось примерно ${daysLabel(left)}.`
      : `Осталось ${daysLabel(left)} подписки.`;
  } else {
    setFrog("happy");
    setGauge(left / GAUGE_REF_DAYS, "ok");
    badge.classList.remove("hidden");
    badge.textContent = daysLabel(left);
    pill.className = "status-pill on";
    pill.innerHTML = '<span class="dot"></span> Подключено';
    $("statusNote").textContent = me.balance_enabled
      ? `При текущем расходе баланса хватит примерно на ${daysLabel(left)}.`
      : `Подписка действует ещё ${daysLabel(left)}.`;
  }
  const add = $("ctaAdd");
  const topup = $("topupBtn");
  if (me.balance_enabled && n === 0) {
    add.classList.remove("hidden");
    add.className = "btn btn-primary";
    topup.className = "btn btn-ghost";
    topup.textContent = "Пополнить";
  } else {
    add.classList.add("hidden");
    topup.className = "btn btn-primary";
    topup.textContent = "Пополнить баланс";
  }
}

applyTheme();
if (tg.onEvent) tg.onEvent("themeChanged", applyTheme);

function haptic() {
  try {
    tg.HapticFeedback.impactOccurred("light");
  } catch (_e) {}
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    ...opts,
    headers: {
      "Content-Type": "application/json",
      "X-Init-Data": tg.initData || "",
      ...(opts.headers || {}),
    },
  });
  const data = await res.json().catch(() => ({ ok: false, error: "Ошибка ответа" }));
  if (!res.ok || data.ok === false) {
    throw new Error(data.error || "Ошибка запроса");
  }
  return data;
}

function daysWord(n) {
  const abs = Math.abs(n);
  const mod10 = abs % 10;
  const mod100 = abs % 100;
  if (mod10 === 1 && mod100 !== 11) return "день";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return "дня";
  return "дней";
}

function daysLabel(n) {
  return `${n} ${daysWord(n)}`;
}

function rublesWord(n) {
  const abs = Math.abs(n);
  const mod10 = abs % 10;
  const mod100 = abs % 100;
  if (mod10 === 1 && mod100 !== 11) return "рубль";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return "рубля";
  return "рублей";
}

function rublesLabel(n) {
  return `${n} ${rublesWord(n)}`;
}

function showErr(err) {
  try {
    tg.HapticFeedback.notificationOccurred("error");
  } catch (_e) {}
  tg.showAlert(err.message || String(err));
}

function showBoot() {
  $("boot").classList.remove("hidden");
  $("fail").classList.add("hidden");
  $("maint").classList.add("hidden");
  $("app").classList.add("hidden");
}

function showFail(message) {
  $("boot").classList.add("hidden");
  $("app").classList.add("hidden");
  $("maint").classList.add("hidden");
  $("fail").classList.remove("hidden");
  $("failText").textContent = message;
}

function showMaint(notice) {
  $("boot").classList.add("hidden");
  $("fail").classList.add("hidden");
  $("app").classList.add("hidden");
  $("maint").classList.remove("hidden");
  if (notice) $("maintText").textContent = notice;
  try {
    tg.MainButton.hide();
    tg.BackButton.hide();
  } catch (_e) {}
}

function showApp() {
  $("boot").classList.add("hidden");
  $("fail").classList.add("hidden");
  $("maint").classList.add("hidden");
  $("app").classList.remove("hidden");
  replayAnim($("app"), "app-in");
}

let mainFn = null;
if (tg.MainButton && tg.MainButton.onClick) {
  tg.MainButton.onClick(() => {
    if (mainFn) mainFn();
  });
}
if (tg.BackButton && tg.BackButton.onClick) {
  tg.BackButton.onClick(() => onBack());
}

function setMain(text, fn) {
  mainFn = fn;
  if (!tg.MainButton) return;
  if (!text) {
    tg.MainButton.hide();
    document.body.classList.remove("has-main-btn");
    return;
  }
  tg.MainButton.setText(text);
  try {
    tg.MainButton.setParams({ color: "#2fae6b", text_color: "#0d1611" });
  } catch (_e) {}
  tg.MainButton.show();
  tg.MainButton.enable();
  document.body.classList.add("has-main-btn");
}

function replayAnim(el, cls) {
  if (!el) return;
  el.classList.remove(cls);
  void el.offsetWidth;
  el.classList.add(cls);
}

function switchView(id, motion) {
  ["view-home", "view-topup", "view-wizard", "view-device"].forEach((vid) => {
    const el = $(vid);
    const on = vid === id;
    el.classList.toggle("hidden", !on);
    el.classList.remove("view-in-fade", "view-in-push", "view-in-pop");
    if (on) replayAnim(el, "view-in-" + (motion || "fade"));
  });
}

const wiz = {
  step: 1,
  platform: "ios",
  client: "incy",
  title: "",
  url: "",
};

let screen = "home";
let openDevice = null;
function onBack() {
  haptic();
  if (screen === "wizard") {
    if (wiz.step > 1 && !wiz.url) {
      wiz.step -= 1;
      renderWizard();
      return;
    }
    closeWizard();
    return;
  }
  if (screen === "device") {
    openHome();
    return;
  }
  if (screen === "topup") {
    openHome();
  }
}

function openHome() {
  const fromStack = screen === "wizard" || screen === "device" || screen === "topup";
  screen = "home";
  openDevice = null;
  switchView("view-home", fromStack ? "pop" : "fade");
  setMain("");
  try {
    tg.BackButton.hide();
  } catch (_e) {}
}

function openTopup() {
  const me = window.__me;
  if (!me) return;
  screen = "topup";
  switchView("view-topup", "push");
  setMain("");
  try {
    tg.BackButton.show();
  } catch (_e) {}
  renderTopup(me);
}

async function payPlan(plan) {
  const inv = await api("/api/invoice", {
    method: "POST",
    body: JSON.stringify({ plan: plan.code }),
  });
  if (inv.pay_url) {
    tg.openLink(inv.pay_url);
    return;
  }
  tg.openInvoice(inv.invoice_url, (status) => {
    if (status === "paid") load();
  });
}

function renderTopup(me) {
  const row = $("topupRow");
  row.innerHTML = "";
  me.plans.forEach((plan) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "cell nav";
    const price = plan.rub ? rublesLabel(Number(plan.rub) || plan.rub) : `${plan.stars} звёзд`;
    const main = document.createElement("div");
    main.className = "plan-main";
    const title = document.createElement("div");
    title.className = "plan-title";
    title.textContent = plan.title;
    const sub = document.createElement("div");
    sub.className = "plan-sub";
    sub.textContent = me.balance_enabled ? "на баланс" : daysLabel(plan.days);
    main.appendChild(title);
    main.appendChild(sub);
    const cost = document.createElement("span");
    cost.className = "plan-price";
    cost.textContent = price;
    b.appendChild(main);
    b.appendChild(cost);
    b.onclick = async () => {
      haptic();
      try {
        await payPlan(plan);
      } catch (e) {
        showErr(e);
      }
    };
    row.appendChild(b);
  });
}

function closeWizard() {
  wiz.step = 1;
  wiz.url = "";
  openHome();
}

function startWizard() {
  const me = window.__me;
  if (!me || !me.balance_enabled) return;
  haptic();
  wiz.step = 1;
  wiz.platform = "ios";
  wiz.client = "incy";
  wiz.title = "";
  wiz.url = "";
  screen = "wizard";
  switchView("view-wizard", "push");
  try {
    tg.BackButton.show();
  } catch (_e) {}
  renderWizard();
}

function renderWizard() {
  const body = $("wizBody");
  body.innerHTML = "";
  $("wizHint").textContent = "";
  replayAnim($("wizTitle"), "title-in");
  if (wiz.step === 1) {
    $("wizStep").textContent = "Шаг 1 из 3";
    $("wizTitle").textContent = "Выбор устройства";
    const group = document.createElement("section");
    group.className = "group";
    PLATFORMS.forEach((p) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "cell nav";
      b.style.justifyContent = "space-between";
      const main = document.createElement("div");
      main.className = "plan-main";
      const t = document.createElement("div");
      t.className = "plan-title";
      t.textContent = p.title;
      const s = document.createElement("div");
      s.className = "plan-sub";
      s.textContent = p.hint;
      main.appendChild(t);
      main.appendChild(s);
      const r = document.createElement("span");
      r.className = "radio" + (wiz.platform === p.id ? " on" : "");
      b.appendChild(main);
      b.appendChild(r);
      b.onclick = () => {
        haptic();
        wiz.platform = p.id;
        const first = clientsFor(p.id)[0];
        wiz.client = first ? first.id : "happ";
        renderWizard();
      };
      group.appendChild(b);
    });
    body.appendChild(group);
    replayAnim(body, "wiz-swap");
    setMain("Продолжить", () => {
      haptic();
      wiz.step = 2;
      renderWizard();
    });
    return;
  }
  if (wiz.step === 2) {
    $("wizStep").textContent = "Шаг 2 из 3";
    $("wizTitle").textContent = "Установите приложение";
    const list = clientsFor(wiz.platform);
    const group = document.createElement("section");
    group.className = "group";
    list.forEach((c) => {
      const row = document.createElement("div");
      row.className = "cell client-row";
      const icon = document.createElement("div");
      icon.className = "client-icon";
      icon.textContent = c.mark;
      const main = document.createElement("div");
      main.className = "plan-main";
      const t = document.createElement("div");
      t.className = "plan-title";
      t.textContent = c.name;
      const s = document.createElement("div");
      s.className = "plan-sub";
      s.textContent = "ДЛЯ " + platformLabel(wiz.platform).toUpperCase();
      main.appendChild(t);
      main.appendChild(s);
      const store = c.stores[wiz.platform];
      if (store) {
        const a = document.createElement("a");
        a.className = "store-link";
        a.href = store;
        a.textContent = store.indexOf("apple.com") >= 0 ? "App Store" : store.indexOf("google.com") >= 0 ? "Google Play" : "Скачать";
        a.onclick = (e) => {
          e.preventDefault();
          haptic();
          tg.openLink(store);
        };
        main.appendChild(a);
      }
      const mark = document.createElement("span");
      mark.className = (wiz.client === c.id ? "check on" : "check");
      row.appendChild(icon);
      row.appendChild(main);
      row.appendChild(mark);
      row.onclick = (e) => {
        if (e.target.closest("a")) return;
        haptic();
        wiz.client = c.id;
        renderWizard();
      };
      group.appendChild(row);
    });
    body.appendChild(group);
    replayAnim(body, "wiz-swap");
    $("wizHint").textContent =
      "Приложение можно сменить в любой момент. Если уже установлено, нажмите «Продолжить».";
    setMain("Продолжить с " + clientLabel(wiz.client), () => {
      haptic();
      wiz.step = 3;
      renderWizard();
    });
    return;
  }

  $("wizStep").textContent = "Шаг 3 из 3";
  $("wizTitle").textContent = wiz.url ? "Приятного пользования" : "Имя устройства";
  const group = document.createElement("section");
  group.className = "group";
  if (wiz.url) {
    const lab = document.createElement("div");
    lab.className = "cell static";
    lab.innerHTML = `<span class="cell-label">Ваша ссылка для ${clientLabel(wiz.client)}</span>`;
    const url = document.createElement("div");
    url.className = "cell url-box";
    url.textContent = wiz.url;
    const copy = document.createElement("button");
    copy.type = "button";
    copy.className = "cell action";
    copy.textContent = "Скопировать";
    copy.onclick = () => {
      haptic();
      navigator.clipboard.writeText(wiz.url);
      tg.showAlert("Ссылка скопирована");
    };
    const open = document.createElement("button");
    open.type = "button";
    open.className = "cell action";
    open.textContent = "Открыть в " + clientLabel(wiz.client);
    open.onclick = () => openClient(wiz.client, wiz.url);
    group.appendChild(lab);
    group.appendChild(url);
    group.appendChild(copy);
    group.appendChild(open);
  }
  const field = document.createElement("div");
  field.className = "cell field";
  const input = document.createElement("input");
  input.id = "devName";
  input.type = "text";
  input.placeholder = "например: мой iPhone";
  input.value = wiz.title;
  input.oninput = () => {
    wiz.title = input.value;
  };
  field.appendChild(input);
  if (!wiz.url) {
    const cap = document.createElement("div");
    cap.className = "cell static";
    cap.innerHTML = '<span class="cell-label">Назовите устройство</span>';
    group.appendChild(cap);
  } else {
    const cap = document.createElement("div");
    cap.className = "cell static";
    cap.innerHTML = '<span class="cell-label">Название</span>';
    group.appendChild(cap);
  }
  group.appendChild(field);
  body.appendChild(group);
  replayAnim(body, "wiz-swap");
  $("wizHint").textContent = "Ссылку можно вставить вручную в Happ или Incy.";
  if (wiz.url) {
    setMain("Готово", () => {
      haptic();
      closeWizard();
      load().catch(() => {});
    });
    return;
  }
  setMain("Создать", async () => {
    haptic();
    const title = (wiz.title || "").trim() || defaultTitle();
    try {
      tg.MainButton.showProgress();
      const created = await api("/api/devices", {
        method: "POST",
        body: JSON.stringify({
          title,
          platform: wiz.platform,
          client: wiz.client,
        }),
      });
      wiz.title = title;
      wiz.url = created.subscription_url || "";
      await load();
      renderWizard();
    } catch (e) {
      showErr(e);
    } finally {
      try {
        tg.MainButton.hideProgress();
      } catch (_e) {}
    }
  });
}

function defaultTitle() {
  return "Устройство " + platformLabel(wiz.platform);
}

function openClient(client, url) {
  haptic();
  if (!url) return;
  if (client === "happ") {
    window.location.href = "happ://add/" + encodeURIComponent(url);
    return;
  }
  tg.openLink(url);
}

function showDevice(d) {
  haptic();
  screen = "device";
  openDevice = d;
  switchView("view-device", "push");
  try {
    tg.BackButton.show();
  } catch (_e) {}
  $("devTitle").textContent = d.title || "Устройство";
  $("devClient").textContent = clientLabel(d.client);
  $("devPlatform").textContent = platformLabel(d.platform);
  $("devUrl").textContent = d.subscription_url || "Ссылка появится после создания";
  setMain("");
}

function renderConnect(me) {
  const wrap = $("connectWrap");
  const body = $("connectBody");
  if (me.balance_enabled) {
    wrap.classList.add("hidden");
    return;
  }
  wrap.classList.remove("hidden");
  body.innerHTML = "";
  if (!me.subscription_url) {
    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = "Ссылка появится после бесплатного периода или оплаты.";
    body.appendChild(p);
    return;
  }
  const copyRow = document.createElement("button");
  copyRow.type = "button";
  copyRow.className = "cell copy-cell";
  copyRow.textContent = me.subscription_url;
  const copyBtn = document.createElement("button");
  copyBtn.type = "button";
  copyBtn.className = "cell action";
  copyBtn.textContent = "Скопировать ссылку";
  const copy = () => {
    haptic();
    navigator.clipboard.writeText(me.subscription_url);
    tg.showAlert("Ссылка скопирована");
  };
  copyRow.onclick = copy;
  copyBtn.onclick = copy;
  const reissueBtn = document.createElement("button");
  reissueBtn.type = "button";
  reissueBtn.className = "cell action";
  reissueBtn.textContent = "Перевыпустить ссылку";
  reissueBtn.onclick = () => reissueSubscription();
  body.appendChild(copyRow);
  body.appendChild(copyBtn);
  body.appendChild(reissueBtn);
}

function renderDevices(me) {
  const block = $("devicesBlock");
  if (!me.balance_enabled) {
    block.classList.add("hidden");
    return;
  }
  block.classList.remove("hidden");
  const n = me.devices.length;
  $("deviceCount").textContent = "· " + n;
  $("addDevice").classList.toggle("hidden", n === 0);
  $("emptyDevices").classList.toggle("hidden", n > 0);
  const body = $("devicesBody");
  body.classList.toggle("hidden", n === 0);
  body.innerHTML = "";
  if (!n) return;
  me.devices.forEach((d) => {
    const el = document.createElement("button");
    el.type = "button";
    el.className = "device-row";
    el.innerHTML =
      '<div class="glyph sm" aria-hidden="true">' +
      '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><rect x="6" y="2" width="12" height="20" rx="2.5" stroke="#5fd68b" stroke-width="1.6"/><circle cx="12" cy="18" r="0.8" fill="#5fd68b"/></svg>' +
      "</div>";
    const meta = document.createElement("div");
    meta.className = "meta";
    const title = document.createElement("div");
    title.className = "n";
    title.textContent = d.title || "Устройство";
    const st = document.createElement("div");
    st.className = "s" + (d.active ? "" : " off");
    st.innerHTML = '<span class="dot"></span>' + (d.active ? "Подключено" : "Неактивно");
    meta.appendChild(title);
    meta.appendChild(st);
    el.appendChild(meta);
    el.onclick = () => showDevice(d);
    body.appendChild(el);
  });
}

function paint(me) {
  if (me.brand_name) document.title = me.brand_name;
  $("name").textContent = me.user.name;
  $("login").textContent = me.user.username || "без username";
  const avatar = $("avatar");
  if (me.user.photo) {
    avatar.src = me.user.photo;
  } else {
    avatar.removeAttribute("src");
  }
  paintStatus(me);
  if (me.balance_enabled) {
    const rub = me.referral_reward_rub || 50;
    $("inviteTitle").textContent = `Приведи друга — получи ${rub} ₽`;
    $("inviteNote").textContent = `Другу тоже начислят ${rub} ₽ на баланс`;
  } else {
    const refDays = me.referral_reward_days || 7;
    const friendDays = me.referral_invitee_days || 5;
    $("inviteTitle").textContent = `Приведи друга — ${daysLabel(refDays)}`;
    $("inviteNote").textContent =
      `Другу начислят +${daysLabel(friendDays)} к бесплатному периоду`;
  }
  $("invite").textContent = me.invite_url;
  $("offerLink").href = me.legal.offer;
  $("privacyLink").href = me.legal.privacy;
  $("supportLink").href = me.legal.support;
  if (me.promo_enabled) {
    $("promoCard").classList.remove("hidden");
  } else {
    $("promoCard").classList.add("hidden");
  }
  const trustBtn = $("trustBtn");
  const trustOpen = $("trustOpen");
  const t = me.trust;
  if (me.balance_enabled && t && t.open) {
    trustBtn.classList.add("hidden");
    trustOpen.classList.remove("hidden");
    const due = t.open.due_at ? new Date(t.open.due_at) : null;
    $("trustDue").textContent = due && !Number.isNaN(due.getTime())
      ? `списание ${due.toLocaleDateString("ru-RU")}`
      : rublesLabel(t.open.amount);
  } else if (me.balance_enabled && t && t.available) {
    trustOpen.classList.add("hidden");
    trustBtn.classList.remove("hidden");
    trustBtn.textContent = `Доверительный платёж · ${rublesLabel(t.amount)}`;
  } else {
    trustBtn.classList.add("hidden");
    trustOpen.classList.add("hidden");
  }
  const trialHome = $("trialHomeBtn");
  if (me.trial_available) {
    trialHome.classList.remove("hidden");
    trialHome.textContent = me.balance_enabled
      ? `Попробовать бесплатно · ${rublesLabel(me.trial_rub)}`
      : `Попробовать бесплатно · ${daysLabel(me.trial_days)}`;
  } else {
    trialHome.classList.add("hidden");
  }
  renderConnect(me);
  renderDevices(me);
  window.__me = me;
  if (screen === "device" && openDevice) {
    const fresh = me.devices.find((x) => x.id === openDevice.id);
    if (fresh) {
      openDevice = fresh;
      $("devTitle").textContent = fresh.title || "Устройство";
      $("devClient").textContent = clientLabel(fresh.client);
      $("devPlatform").textContent = platformLabel(fresh.platform);
      $("devUrl").textContent = fresh.subscription_url || "Ссылка появится после создания";
    }
  }
  showApp();
}

async function load() {
  const me = await api("/api/me");
  if (me.maintenance) {
    showMaint(me.notice);
    return;
  }
  paint(me);
}

function closeMenu() {
  $("menu").classList.add("hidden");
  $("menuScrim").classList.add("hidden");
}

$("menuBtn").onclick = (e) => {
  e.stopPropagation();
  haptic();
  $("menu").classList.toggle("hidden");
  $("menuScrim").classList.toggle("hidden", $("menu").classList.contains("hidden"));
};
$("menuScrim").onclick = closeMenu;
$("menu").onclick = (e) => e.stopPropagation();

$("topupBtn").onclick = () => {
  haptic();
  openTopup();
};

$("trialHomeBtn").onclick = async () => {
  haptic();
  try {
    await api("/api/trial", { method: "POST", body: "{}" });
    await load();
  } catch (e) {
    showErr(e);
  }
};

$("trustBtn").onclick = () => {
  const me = window.__me;
  const t = me && me.trust;
  if (!t || !t.available) return;
  haptic();
  const text =
    `Начислить ${rublesLabel(t.amount)} (${daysLabel(t.days)} по ${rublesLabel(t.daily_cost)} в сутки). ` +
    `Через ${daysLabel(t.days)} сумма спишется, даже если баланс уйдёт в минус.`;
  const go = async () => {
    try {
      await api("/api/trust", { method: "POST", body: "{}" });
      await load();
    } catch (e) {
      showErr(e);
    }
  };
  if (tg.showConfirm) {
    tg.showConfirm(text, (ok) => {
      if (ok) go();
    });
  } else if (window.confirm(text)) {
    go();
  }
};

$("shareBtn").onclick = () => {
  haptic();
  const url = window.__me && window.__me.invite_url;
  if (url) {
    const me = window.__me;
    let text;
    if (me && me.balance_enabled) {
      const rub = me.referral_reward_rub || 50;
      text = encodeURIComponent(
        `Подключайся. Нажми «Попробовать бесплатно» по ссылке — получишь ${rublesLabel(rub)} на баланс, и я тоже.`
      );
    } else {
      const days = (me && me.referral_reward_days) || 7;
      const extra = (me && me.referral_invitee_days) || 5;
      text = encodeURIComponent(
        `Подключайся. Нажми «Попробовать бесплатно» по ссылке — получишь +${daysLabel(extra)}, а я получу ${daysLabel(days)} VPN.`
      );
    }
    tg.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(url)}&text=${text}`);
  }
};

$("invite").onclick = () => {
  const url = window.__me && window.__me.invite_url;
  if (!url) return;
  haptic();
  navigator.clipboard.writeText(url);
  tg.showAlert("Ссылка скопирована");
};

$("promoBtn").onclick = async () => {
  haptic();
  try {
    await api("/api/promo", {
      method: "POST",
      body: JSON.stringify({ code: $("promo").value }),
    });
    $("promo").value = "";
    await load();
    tg.showAlert("Промокод применён");
  } catch (e) {
    showErr(e);
  }
};

$("ctaAdd").onclick = () => startWizard();
$("addDevice").onclick = () => startWizard();
$("addDeviceEmpty").onclick = () => startWizard();

$("promoToggle").onclick = () => {
  const body = $("promoBody");
  body.classList.toggle("open");
  $("promoChev").style.transform = body.classList.contains("open") ? "rotate(180deg)" : "rotate(0deg)";
};

$("devCopy").onclick = () => {
  const d = openDevice;
  if (!d || !d.subscription_url) return;
  haptic();
  navigator.clipboard.writeText(d.subscription_url);
  tg.showAlert("Ссылка скопирована");
};

$("devOpen").onclick = () => {
  const d = openDevice;
  if (!d || !d.subscription_url) return;
  openClient(d.client, d.subscription_url);
};

function askReissue() {
  return new Promise((resolve) => {
    const msg = "Старая ссылка перестанет работать. Перевыпустить?";
    if (typeof tg.showConfirm === "function") {
      tg.showConfirm(msg, (ok) => resolve(Boolean(ok)));
      return;
    }
    resolve(window.confirm(msg));
  });
}

async function reissueSubscription(deviceId) {
  haptic();
  if (!(await askReissue())) return;
  try {
    const path = deviceId
      ? `/api/devices/${deviceId}/reissue`
      : "/api/subscription/reissue";
    const data = await api(path, { method: "POST", body: "{}" });
    if (deviceId && openDevice && openDevice.id === deviceId) {
      openDevice.subscription_url = data.subscription_url || "";
      $("devUrl").textContent = openDevice.subscription_url || "Ссылка появится после создания";
    }
    await load();
    tg.showAlert("Ссылка перевыпущена. Обновите подписку в клиенте.");
  } catch (e) {
    showErr(e);
  }
}

$("devReissue").onclick = () => {
  const d = openDevice;
  if (!d) return;
  reissueSubscription(d.id);
};

$("vpnDown").onclick = async () => {
  haptic();
  try {
    await api("/api/vpn-report", { method: "POST", body: "{}" });
    tg.showAlert("Принято. Мы уже смотрим.");
  } catch (e) {
    showErr(e);
  }
};

$("supportBtn").onclick = () => {
  haptic();
  const url = (window.__me && window.__me.legal && window.__me.legal.support) || $("supportLink").href;
  if (url) tg.openTelegramLink(url);
};

$("retryBtn").onclick = () => {
  showBoot();
  load().catch((err) => showFail(err.message || "Не удалось загрузить данные"));
};

if (tg.onEvent) {
  tg.onEvent("invoiceClosed", (status) => {
    if (status === "paid") load().catch(() => {});
  });
}
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && window.__me) {
    load().catch(() => {});
  }
});

load().catch((err) => showFail(err.message || "Не удалось загрузить данные"));
