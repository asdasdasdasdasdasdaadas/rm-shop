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
  { id: "ios", title: "iPhone, iPad", hint: "IPHONE, IPAD", sub: "iOS 15+" },
  { id: "android", title: "Android", hint: "ANDROID", sub: "8.0+" },
  { id: "macos", title: "macOS", hint: "MACOS", sub: "12+" },
  { id: "windows", title: "Windows", hint: "WINDOWS", sub: "10/11" },
  { id: "androidtv", title: "Android TV", hint: "ANDROID TV", sub: "Смарт-ТВ" },
  { id: "appletv", title: "Apple TV", hint: "APPLE TV", sub: "tvOS" },
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

function platformSub(id) {
  const p = PLATFORMS.find((x) => x.id === id);
  return p && p.sub ? p.sub : "";
}

function nameChips(platform) {
  if (platform === "ios") return ["Мой iPhone", "Рабочий телефон", "Домашний iPad", "iPhone мамы"];
  if (platform === "android") return ["Мой Android", "Рабочий телефон", "Планшет"];
  if (platform === "macos") return ["MacBook", "iMac", "Рабочий Mac"];
  if (platform === "windows") return ["Ноутбук", "Рабочий ПК", "Домашний ПК"];
  if (platform === "androidtv") return ["Телевизор", "Android TV"];
  if (platform === "appletv") return ["Apple TV", "Гостиная"];
  return ["Моё устройство"];
}

function storeCaption(url) {
  if (!url) return "Скачать";
  if (url.indexOf("apple.com") >= 0) return "Открыть в App Store";
  if (url.indexOf("google.com") >= 0) return "Открыть в Google Play";
  return "Скачать";
}

function step2Hint(platform) {
  if (platform === "ios") {
    return "Для iPhone и iPad рекомендуем Incy — быстрее ставится и стабильнее держит соединение.";
  }
  if (platform === "android" || platform === "androidtv") {
    return "Для Android рекомендуем Happ — ставится из магазина и просто принимает ссылку.";
  }
  if (platform === "macos" || platform === "appletv") {
    return "Для Apple рекомендуем Incy, если доступен. Иначе Happ.";
  }
  return "Выберите клиент под вашу систему. Если уже установлен — сразу нажмите «Продолжить».";
}

function platIconSvg(id) {
  if (id === "ios") {
    return '<svg viewBox="0 0 24 24" fill="none"><rect x="6" y="2" width="12" height="20" rx="3" stroke="currentColor" stroke-width="1.8"/><circle cx="12" cy="18" r="1" fill="currentColor"/></svg>';
  }
  if (id === "android") {
    return '<svg viewBox="0 0 24 24" fill="none"><rect x="4" y="7" width="16" height="14" rx="3" stroke="currentColor" stroke-width="1.8"/><path d="M8 7V4M16 7V4M4 12h16" stroke="currentColor" stroke-width="1.8"/></svg>';
  }
  if (id === "macos") {
    return '<svg viewBox="0 0 24 24" fill="none"><rect x="3" y="4" width="18" height="12" rx="2" stroke="currentColor" stroke-width="1.8"/><path d="M8 20h8M12 16v4" stroke="currentColor" stroke-width="1.8"/></svg>';
  }
  if (id === "windows") {
    return '<svg viewBox="0 0 24 24" fill="none"><path d="M3 6l8-1v7H3V6zM12 5l9-1v8h-9V5zM3 13h8v7l-8-1v-6zM12 13h9v8l-9-1v-7z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg>';
  }
  if (id === "androidtv") {
    return '<svg viewBox="0 0 24 24" fill="none"><rect x="2" y="5" width="20" height="13" rx="2" stroke="currentColor" stroke-width="1.8"/><path d="M8 21h8" stroke="currentColor" stroke-width="1.8"/></svg>';
  }
  return '<svg viewBox="0 0 24 24" fill="none"><rect x="2" y="5" width="20" height="13" rx="2" stroke="currentColor" stroke-width="1.8"/><circle cx="12" cy="11.5" r="2" stroke="currentColor" stroke-width="1.6"/><path d="M8 21h8" stroke="currentColor" stroke-width="1.8"/></svg>';
}

function setWizProgress(step) {
  const bar = $("wizProgress");
  if (step >= 4) {
    bar.classList.add("hidden");
    return;
  }
  bar.classList.remove("hidden");
  [1, 2, 3].forEach((n) => {
    $("wizPf" + n).style.width = n <= step ? "100%" : "0%";
  });
}

function hideQr() {
  $("qrSheet").classList.add("hidden");
  $("qrScrim").classList.add("hidden");
  $("qrBox").innerHTML = "";
}

function showQr(url) {
  if (!url) return;
  const box = $("qrBox");
  box.innerHTML = "";
  if (typeof qrcode !== "function") {
    tg.showAlert("Не удалось построить QR-код");
    return;
  }
  const qr = qrcode(0, "M");
  qr.addData(url);
  qr.make();
  const n = qr.getModuleCount();
  const pad = 4;
  const dim = n + pad * 2;
  let d = "";
  for (let r = 0; r < n; r++) {
    for (let c = 0; c < n; c++) {
      if (qr.isDark(r, c)) d += "M" + (c + pad) + " " + (r + pad) + "h1v1h-1z";
    }
  }
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 " + dim + " " + dim);
  svg.setAttribute("class", "wiz-qr-svg");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "QR-код");
  const bg = document.createElementNS(ns, "rect");
  bg.setAttribute("width", String(dim));
  bg.setAttribute("height", String(dim));
  bg.setAttribute("fill", "#ffffff");
  const path = document.createElementNS(ns, "path");
  path.setAttribute("d", d);
  path.setAttribute("fill", "#0d1611");
  svg.appendChild(bg);
  svg.appendChild(path);
  box.appendChild(svg);
  $("qrSheet").classList.remove("hidden");
  $("qrScrim").classList.remove("hidden");
}

function applyTheme() {
  const bg = "#0d1611";
  try {
    tg.setHeaderColor(bg);
    tg.setBackgroundColor(bg);
    if (typeof tg.setBottomBarColor === "function") tg.setBottomBarColor(bg);
    if (tg.MainButton && tg.MainButton.hide) tg.MainButton.hide();
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
    $("balanceLine").innerHTML = `${me.balance_rub} ₽ <span>на счету</span>`;
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

const INTRO_KEY = "way_intro_v1";
let introTimer = 0;
let introShown = false;

function hideIntro() {
  if (introTimer) {
    clearTimeout(introTimer);
    introTimer = 0;
  }
  $("intro").classList.add("hidden");
}

function showBoot() {
  hideCoach();
  hideIntro();
  $("boot").classList.remove("hidden");
  $("fail").classList.add("hidden");
  $("maint").classList.add("hidden");
  $("app").classList.add("hidden");
}

function showFail(message) {
  hideCoach();
  hideIntro();
  $("boot").classList.add("hidden");
  $("app").classList.add("hidden");
  $("maint").classList.add("hidden");
  $("fail").classList.remove("hidden");
  $("failText").textContent = message;
}

function showMaint(notice) {
  hideCoach();
  hideIntro();
  $("boot").classList.add("hidden");
  $("fail").classList.add("hidden");
  $("app").classList.add("hidden");
  $("maint").classList.remove("hidden");
  if (notice) $("maintText").textContent = notice;
  try {
    tg.BackButton.hide();
  } catch (_e) {}
  setMain("");
}

function showApp() {
  hideIntro();
  $("boot").classList.add("hidden");
  $("fail").classList.add("hidden");
  $("maint").classList.add("hidden");
  $("app").classList.remove("hidden");
  replayAnim($("app"), "app-in");
  scheduleCoach();
}

function introSeen() {
  try {
    return sessionStorage.getItem(INTRO_KEY) === "1";
  } catch (_e) {
    return introShown;
  }
}

function markIntroSeen() {
  introShown = true;
  try {
    sessionStorage.setItem(INTRO_KEY, "1");
  } catch (_e) {}
}

function finishIntro() {
  if (introTimer) {
    clearTimeout(introTimer);
    introTimer = 0;
  }
  markIntroSeen();
  showApp();
}

function reducedMotion() {
  return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function shouldShowIntro() {
  return !introSeen();
}

function showIntro(me) {
  const user = me.user || {};
  const name = (user.name || "").trim() || "друг";
  const nick = (user.username || "").trim();
  $("introHello").textContent = "Привет";
  $("introName").textContent = name;
  const nickEl = $("introNick");
  nickEl.textContent = nick;
  nickEl.classList.toggle("hidden", !nick);
  const av = $("introAvatar");
  const fb = $("introFallback");
  if (user.photo) {
    av.src = user.photo;
    av.classList.remove("hidden");
    fb.classList.add("hidden");
  } else {
    av.removeAttribute("src");
    av.classList.add("hidden");
    fb.textContent = (name.charAt(0) || "?").toUpperCase();
    fb.classList.remove("hidden");
  }
  $("boot").classList.add("hidden");
  $("fail").classList.add("hidden");
  $("maint").classList.add("hidden");
  $("app").classList.add("hidden");
  $("intro").classList.remove("hidden");
  try {
    tg.HapticFeedback.impactOccurred("light");
  } catch (_e) {}
  introTimer = setTimeout(finishIntro, reducedMotion() ? 400 : 2400);
}

let mainFn = null;
if (tg.BackButton && tg.BackButton.onClick) {
  tg.BackButton.onClick(() => onBack());
}

function setMainBusy(busy) {
  const btn = $("appMainBtn");
  if (!btn) return;
  btn.disabled = Boolean(busy);
}

function setMain(text, fn) {
  mainFn = fn || null;
  const bar = $("appMainBar");
  const btn = $("appMainBtn");
  try {
    if (tg.MainButton && tg.MainButton.hide) tg.MainButton.hide();
  } catch (_e) {}
  if (!text) {
    bar.classList.add("hidden");
    document.body.classList.remove("has-main-btn");
    return;
  }
  btn.textContent = text;
  btn.disabled = false;
  bar.classList.remove("hidden");
  document.body.classList.add("has-main-btn");
}

$("appMainBtn").onclick = () => {
  if ($("appMainBtn").disabled) return;
  if (mainFn) mainFn();
};

function replayAnim(el, cls) {
  if (!el) return;
  el.classList.remove(cls);
  void el.offsetWidth;
  el.classList.add(cls);
}

function switchView(id, motion) {
  if (id !== "view-home") hideCoach();
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
let topupMode = "fast";
let topupCode = "";

const COACH_KEY = "way_home_coach_v2";
let coachIndex = 0;
let coachList = [];
let coachVisible = false;
let coachPlaceTimer = 0;
let coachStartTimers = [];

function coachDone() {
  try {
    return localStorage.getItem(COACH_KEY) === "1";
  } catch (_e) {
    return false;
  }
}

function markCoachDone() {
  try {
    localStorage.setItem(COACH_KEY, "1");
  } catch (_e) {}
}

function hideCoach() {
  coachVisible = false;
  if (coachPlaceTimer) {
    clearTimeout(coachPlaceTimer);
    coachPlaceTimer = 0;
  }
  const el = $("coach");
  if (el) el.classList.add("hidden");
}

function finishCoach() {
  markCoachDone();
  hideCoach();
}

function coachElReady(id) {
  const el = $(id);
  return Boolean(el && !el.classList.contains("hidden"));
}

function buildCoachSteps(me) {
  const steps = [];
  if (!me) return steps;
  if (me.balance_enabled) {
    const n = (me.devices || []).length;
    if (me.trial_available && coachElReady("trialHomeBtn")) {
      steps.push({
        id: "trialHomeBtn",
        title: "Можно начать бесплатно",
        text: "Пробные рубли сразу на баланс. Потом добавьте устройство — без него деньги не списываются.",
      });
    } else if ((me.balance_rub || 0) < 1 && coachElReady("topupBtn")) {
      steps.push({
        id: "topupBtn",
        title: "Сначала пополните баланс",
        text: "Сутки спишутся, когда появится первое устройство. Пока устройств нет — баланс не тратится.",
      });
    }
    if (n === 0 && $("ctaAdd") && !$("ctaAdd").classList.contains("hidden")) {
      steps.push({
        id: "ctaAdd",
        title: "Добавьте устройство",
        text: "Выберите телефон или компьютер, установите приложение — ссылка подставится сама. Займёт меньше минуты.",
        action: "wizard",
      });
    } else if (n === 0 && $("addDeviceEmpty") && !$("emptyDevices").classList.contains("hidden")) {
      steps.push({
        id: "addDeviceEmpty",
        title: "Добавьте устройство",
        text: "Выберите телефон или компьютер, установите приложение — ссылка подставится сама. Займёт меньше минуты.",
        action: "wizard",
      });
    }
  } else if (!me.has_access && coachElReady("topupBtn")) {
    steps.push({
      id: "topupBtn",
      title: "Оформите доступ",
      text: "Выберите срок подписки. После оплаты появится ссылка для приложения.",
      action: "topup",
    });
  }
  return steps;
}

function applyCoachCopy() {
  const step = coachList[coachIndex];
  if (!step) return;
  const total = coachList.length;
  $("coachKicker").textContent = `${coachIndex + 1} из ${total}`;
  $("coachTitle").textContent = step.title;
  $("coachText").textContent = step.text;
  const last = coachIndex === total - 1;
  const next = $("coachNext");
  if (step.action === "wizard") next.textContent = "Добавить устройство";
  else if (step.action === "topup") next.textContent = "Пополнить";
  else next.textContent = last ? "Понятно" : "Далее";
}

function pinCoachCard() {
  const card = $("coachCard");
  const hole = $("coachHole");
  hole.classList.add("is-off");
  card.style.top = "auto";
  card.style.bottom = `calc(28px + var(--tg-safe-area-inset-bottom, 0px))`;
}

function layoutCoach() {
  if (!coachVisible) return;
  const step = coachList[coachIndex];
  if (!step) {
    hideCoach();
    return;
  }
  applyCoachCopy();
  const target = $(step.id);
  const hole = $("coachHole");
  const card = $("coachCard");
  if (!target || target.classList.contains("hidden")) {
    pinCoachCard();
    return;
  }
  const r = target.getBoundingClientRect();
  if (r.width < 24 || r.height < 20 || r.bottom < 8 || r.top > window.innerHeight - 8) {
    pinCoachCard();
    return;
  }
  hole.classList.remove("is-off");
  const pad = 6;
  hole.style.top = `${Math.max(8, r.top - pad)}px`;
  hole.style.left = `${Math.max(8, r.left - pad)}px`;
  hole.style.width = `${r.width + pad * 2}px`;
  hole.style.height = `${r.height + pad * 2}px`;
  const radius = getComputedStyle(target).borderRadius;
  hole.style.borderRadius = radius && radius !== "0px" ? radius : "16px";

  const spaceBelow = window.innerHeight - r.bottom;
  if (spaceBelow > 200) {
    card.style.top = `${r.bottom + 14}px`;
    card.style.bottom = "auto";
  } else {
    card.style.bottom = `${Math.max(16, window.innerHeight - r.top + 14)}px`;
    card.style.top = "auto";
  }
}

function placeCoach() {
  const step = coachList[coachIndex];
  if (!step) {
    hideCoach();
    return;
  }
  applyCoachCopy();
  const target = $(step.id);
  if (target && !target.classList.contains("hidden")) {
    try {
      target.scrollIntoView({ block: "center", behavior: "smooth" });
    } catch (_e) {}
  }
  if (coachPlaceTimer) clearTimeout(coachPlaceTimer);
  const delay = reducedMotion() ? 0 : 200;
  coachPlaceTimer = setTimeout(() => {
    coachPlaceTimer = 0;
    layoutCoach();
  }, delay);
}

function coachCanRun() {
  if (screen !== "home") return false;
  if ($("app").classList.contains("hidden")) return false;
  if (!$("intro").classList.contains("hidden")) return false;
  if (!$("fail").classList.contains("hidden")) return false;
  if (!$("maint").classList.contains("hidden")) return false;
  return true;
}

function scheduleCoach() {
  coachStartTimers.forEach((id) => clearTimeout(id));
  coachStartTimers = [];
  [350, 800, 1400].forEach((ms) => {
    coachStartTimers.push(setTimeout(() => maybeStartCoach(false), ms));
  });
}

function maybeStartCoach(force) {
  if (!coachCanRun()) return;
  if (!force && coachDone()) return;
  if (coachVisible && !force) {
    layoutCoach();
    return;
  }
  coachList = buildCoachSteps(window.__me);
  if (!coachList.length) return;
  coachIndex = 0;
  coachVisible = true;
  $("coach").classList.remove("hidden");
  applyCoachCopy();
  pinCoachCard();
  placeCoach();
}

function coachAdvance() {
  haptic();
  const step = coachList[coachIndex];
  if (step && step.action === "wizard") {
    finishCoach();
    startWizard();
    return;
  }
  if (step && step.action === "topup") {
    finishCoach();
    openTopup();
    return;
  }
  if (coachIndex >= coachList.length - 1) {
    finishCoach();
    return;
  }
  coachIndex += 1;
  placeCoach();
}

function planRub(plan) {
  if (!plan) return 0;
  const top = Number(plan.topup_rub);
  if (top > 0) return top;
  return Math.round(Number(plan.rub) || 0);
}

function topupDayPrice(me) {
  const price = Math.max(1, Number(me.vpn_day_price_rub) || 1);
  const n = (me.devices || []).length;
  return price * (n > 0 ? n : 1);
}

function topupDaysFor(me, amount) {
  return Math.max(0, Math.floor(amount / topupDayPrice(me)));
}

function currentTopupPlan(me) {
  const plans = me.plans || [];
  return plans.find((p) => p.code === topupCode) || plans[0] || null;
}

function ensureTopupCode(me) {
  const plans = me.plans || [];
  if (plans.some((p) => p.code === topupCode)) return;
  const hit = plans.find((p) => planRub(p) === 100);
  topupCode = (hit || plans[0] || {}).code || "";
}

function setTopupRangeFill(range) {
  const min = Number(range.min);
  const max = Number(range.max);
  const val = Number(range.value);
  const pct = max === min ? 100 : ((val - min) / (max - min)) * 100;
  range.style.setProperty("--fill", `${pct}%`);
}

function applyTopupMode() {
  const custom = topupMode === "custom";
  $("tabFast").classList.toggle("on", !custom);
  $("tabCustom").classList.toggle("on", custom);
  $("fastPanel").classList.toggle("hidden", custom);
  $("customPanel").classList.toggle("hidden", !custom);
}

function updateTopupCta(me) {
  const plan = currentTopupPlan(me);
  if (!plan) {
    setMain("");
    return;
  }
  const amount = planRub(plan);
  const label = me.balance_enabled
    ? `Пополнить на ${amount} ₽`
    : `Оплатить · ${plan.title}`;
  setMain(label, async () => {
    haptic();
    setMainBusy(true);
    try {
      await payPlan(plan);
    } catch (e) {
      showErr(e);
    } finally {
      setMainBusy(false);
    }
  });
}
function onBack() {
  haptic();
  if (screen === "wizard") {
    if (!$("qrSheet").classList.contains("hidden")) {
      hideQr();
      return;
    }
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
  requestAnimationFrame(() => scheduleCoach());
}

function openTopup() {
  const me = window.__me;
  if (!me) return;
  screen = "topup";
  topupMode = "fast";
  switchView("view-topup", "push");
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
  if (!me) return;
  ensureTopupCode(me);
  const plans = me.plans || [];
  const canCustom = Boolean(me.balance_enabled && plans.length > 1);
  $("topupTabs").classList.toggle("hidden", !canCustom);
  if (!canCustom) topupMode = "fast";
  applyTopupMode();
  $("topupHint").textContent = me.balance_enabled
    ? "Выберите сумму — покажем, на сколько дней доступа её хватит."
    : "Выберите срок подписки.";
  const amounts = plans.map(planRub).filter((n) => n > 0);
  const maxAmt = amounts.length ? Math.max(...amounts) : 0;
  const hitAmt = amounts.includes(100) ? 100 : (amounts[1] || 0);
  const grid = $("topupGrid");
  grid.innerHTML = "";
  plans.forEach((plan) => {
    const amount = planRub(plan);
    const b = document.createElement("button");
    b.type = "button";
    b.className = "pay-card" + (plan.code === topupCode ? " on" : "");
    if (me.balance_enabled && amount === maxAmt && maxAmt > 0) {
      const badge = document.createElement("span");
      badge.className = "pay-badge best";
      badge.textContent = "Выгодно";
      b.appendChild(badge);
    } else if (me.balance_enabled && amount === hitAmt && hitAmt !== maxAmt) {
      const badge = document.createElement("span");
      badge.className = "pay-badge hot";
      badge.textContent = "Хит";
      b.appendChild(badge);
    }
    const amt = document.createElement("div");
    amt.className = "pay-amount";
    amt.textContent = me.balance_enabled
      ? `${amount} ₽`
      : plan.title;
    const days = document.createElement("div");
    days.className = "pay-days";
    days.textContent = me.balance_enabled
      ? `≈ ${daysLabel(topupDaysFor(me, amount))} доступа`
      : daysLabel(plan.days);
    const rateEl = document.createElement("div");
    rateEl.className = "pay-rate";
    if (me.balance_enabled) {
      rateEl.textContent = `${me.vpn_day_price_rub} ₽/день за устройство`;
    } else {
      rateEl.textContent = plan.rub ? `${plan.rub} ₽` : `${plan.stars} звёзд`;
    }
    b.appendChild(amt);
    b.appendChild(days);
    b.appendChild(rateEl);
    b.onclick = () => {
      haptic();
      topupCode = plan.code;
      renderTopup(me);
    };
    grid.appendChild(b);
  });
  if (canCustom) {
    const min = Number(me.topup_min) || amounts[0] || 50;
    const max = Number(me.topup_max) || amounts[amounts.length - 1] || min;
    const step = Math.max(1, Number(me.topup_step) || 50);
    const plan = currentTopupPlan(me);
    const val = planRub(plan) || min;
    const range = $("topupRange");
    range.min = String(min);
    range.max = String(max);
    range.step = String(step);
    range.value = String(val);
    setTopupRangeFill(range);
    $("customVal").textContent = String(val);
    $("customDays").textContent = `≈ ${daysLabel(topupDaysFor(me, val))} VPN`;
    $("topupRangeMin").textContent = `${min} ₽`;
    $("topupRangeMax").textContent = `${max} ₽`;
    const nDev = (me.devices || []).length;
    $("topupStrip").textContent = nDev
      ? `Списание ${me.vpn_day_price_rub} ₽ в день за устройство. Сейчас устройств: ${nDev}.`
      : "Пока нет устройств — баланс не списывается. Оценка дней — как для одного устройства.";
  }
  updateTopupCta(me);
}

function closeWizard() {
  hideQr();
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
  const lead = $("wizLead");
  body.innerHTML = "";
  $("wizHint").textContent = "";
  lead.textContent = "";
  const oldOk = $("wizOkFloat");
  if (oldOk) oldOk.remove();
  if (wiz.url) wiz.step = 4;
  $("wizStep").classList.toggle("hidden", wiz.step >= 4);
  replayAnim($("wizTitle"), "title-in");
  setWizProgress(wiz.step);

  if (wiz.step === 1) {
    $("wizStep").textContent = "Шаг 1 из 3";
    $("wizTitle").textContent = "На чём подключаемся?";
    lead.textContent = "Выберите устройство — настроим ссылку и подсказки именно под него.";
    const grid = document.createElement("div");
    grid.className = "plat-grid";
    PLATFORMS.forEach((p) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "plat-card" + (wiz.platform === p.id ? " on" : "");
      const check = document.createElement("span");
      check.className = "plat-check";
      const icon = document.createElement("div");
      icon.className = "plat-icon";
      icon.innerHTML = platIconSvg(p.id);
      const name = document.createElement("div");
      name.className = "plat-name";
      name.textContent = p.title;
      const sub = document.createElement("div");
      sub.className = "plat-sub";
      sub.textContent = p.sub || "";
      b.appendChild(check);
      b.appendChild(icon);
      b.appendChild(name);
      b.appendChild(sub);
      b.onclick = () => {
        haptic();
        wiz.platform = p.id;
        const first = clientsFor(p.id)[0];
        wiz.client = first ? first.id : "happ";
        wiz.title = "";
        renderWizard();
      };
      grid.appendChild(b);
    });
    body.appendChild(grid);
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
    $("wizTitle").textContent = "Установи приложение";
    lead.textContent = step2Hint(wiz.platform);
    const list = clientsFor(wiz.platform);
    list.forEach((c, i) => {
      const row = document.createElement("button");
      row.type = "button";
      row.className = "wiz-app" + (wiz.client === c.id ? " on" : "");
      const logo = document.createElement("div");
      logo.className = "wiz-app-logo" + (i === 0 ? "" : " muted");
      logo.textContent = c.mark;
      const info = document.createElement("div");
      info.className = "wiz-app-info";
      const t = document.createElement("div");
      t.className = "wiz-app-name";
      t.appendChild(document.createTextNode(c.name));
      if (i === 0) {
        const rec = document.createElement("span");
        rec.className = "rec-badge";
        rec.textContent = "Рекомендуем";
        t.appendChild(rec);
      }
      const s = document.createElement("div");
      s.className = "wiz-app-sub";
      s.textContent = "Для " + platformLabel(wiz.platform);
      info.appendChild(t);
      info.appendChild(s);
      const store = c.stores[wiz.platform];
      if (store) {
        const a = document.createElement("button");
        a.type = "button";
        a.className = "wiz-app-store";
        a.textContent = storeCaption(store);
        a.onclick = (e) => {
          e.stopPropagation();
          haptic();
          tg.openLink(store);
        };
        info.appendChild(a);
      }
      const mark = document.createElement("span");
      mark.className = "radio" + (wiz.client === c.id ? " on" : "");
      row.appendChild(logo);
      row.appendChild(info);
      row.appendChild(mark);
      row.onclick = () => {
        haptic();
        wiz.client = c.id;
        renderWizard();
      };
      body.appendChild(row);
    });
    $("wizHint").textContent =
      "Приложение можно сменить в любой момент. Уже установлено? Нажмите «Продолжить».";
    replayAnim(body, "wiz-swap");
    setMain("Продолжить с " + clientLabel(wiz.client), () => {
      haptic();
      wiz.step = 3;
      renderWizard();
    });
    return;
  }

  if (wiz.step === 3) {
    $("wizStep").textContent = "Шаг 3 из 3";
    $("wizTitle").textContent = "Как назовём устройство?";
    lead.textContent = "Пригодится, если подключите несколько гаджетов — так проще не запутаться.";
    const chips = nameChips(wiz.platform);
    if (!(wiz.title || "").trim()) wiz.title = chips[0] || defaultTitle();
    const box = document.createElement("div");
    box.className = "wiz-name-box";
    const lab = document.createElement("label");
    lab.setAttribute("for", "devName");
    lab.textContent = "Название устройства";
    const input = document.createElement("input");
    input.id = "devName";
    input.type = "text";
    input.placeholder = "например: мой iPhone";
    input.value = wiz.title;
    input.autocomplete = "off";
    box.appendChild(lab);
    box.appendChild(input);
    const chipWrap = document.createElement("div");
    chipWrap.className = "wiz-chips";
    const paintChips = () => {
      chipWrap.querySelectorAll(".wiz-chip").forEach((el) => {
        el.classList.toggle("on", el.textContent === (wiz.title || "").trim());
      });
    };
    chips.forEach((label) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "wiz-chip";
      chip.textContent = label;
      chip.onclick = () => {
        haptic();
        wiz.title = label;
        input.value = label;
        paintChips();
      };
      chipWrap.appendChild(chip);
    });
    input.oninput = () => {
      wiz.title = input.value;
      paintChips();
    };
    body.appendChild(box);
    body.appendChild(chipWrap);
    paintChips();
    replayAnim(body, "wiz-swap");
    setMain("Создать", async () => {
      haptic();
      const title = (wiz.title || "").trim() || defaultTitle();
      try {
        setMainBusy(true);
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
        wiz.step = 4;
        await load();
        renderWizard();
      } catch (e) {
        showErr(e);
      } finally {
        setMainBusy(false);
      }
    });
    return;
  }

  $("wizStep").textContent = "";
  $("wizTitle").textContent = "Готово, можно пользоваться";
  lead.textContent =
    "Ссылка привязана к «" +
    wiz.title +
    "». Откройте её в " +
    clientLabel(wiz.client) +
    " — VPN подключится.";
  const ok = document.createElement("div");
  ok.id = "wizOkFloat";
  ok.className = "wiz-ok";
  ok.innerHTML =
    '<svg viewBox="0 0 24 24" fill="none"><path d="M5 13l4 4L19 7" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  $("wizTitle").parentNode.insertBefore(ok, $("wizTitle"));
  const recap = document.createElement("div");
  recap.className = "wiz-recap";
  const recIcon = document.createElement("div");
  recIcon.className = "plat-icon";
  recIcon.innerHTML = platIconSvg(wiz.platform);
  const recTxt = document.createElement("span");
  const recB = document.createElement("b");
  recB.textContent = wiz.title || defaultTitle();
  recTxt.appendChild(recB);
  recTxt.appendChild(
    document.createTextNode(
      " · " + platformLabel(wiz.platform) + " · через " + clientLabel(wiz.client)
    )
  );
  recap.appendChild(recIcon);
  recap.appendChild(recTxt);

  const link = document.createElement("div");
  link.className = "wiz-link";
  const lbl = document.createElement("div");
  lbl.className = "wiz-link-lbl";
  lbl.textContent = "Ссылка для " + clientLabel(wiz.client);
  const row = document.createElement("div");
  row.className = "wiz-link-row";
  const urlEl = document.createElement("div");
  urlEl.className = "wiz-link-text";
  urlEl.textContent = wiz.url || "";
  const copy = document.createElement("button");
  copy.type = "button";
  copy.className = "wiz-copy";
  copy.textContent = "Копировать";
  copy.onclick = () => {
    haptic();
    navigator.clipboard.writeText(wiz.url || "").then(() => {
      copy.classList.add("on");
      copy.textContent = "Скопировано";
      setTimeout(() => {
        copy.classList.remove("on");
        copy.textContent = "Копировать";
      }, 1600);
    }).catch(() => tg.showAlert("Не удалось скопировать"));
  };
  row.appendChild(urlEl);
  row.appendChild(copy);
  link.appendChild(lbl);
  link.appendChild(row);

  const tiles = document.createElement("div");
  tiles.className = "wiz-tiles";
  const openTile = document.createElement("button");
  openTile.type = "button";
  openTile.className = "wiz-tile";
  openTile.innerHTML =
    '<svg viewBox="0 0 24 24" fill="none"><path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>';
  const openLab = document.createElement("div");
  openLab.className = "lab";
  openLab.textContent = "Открыть в " + clientLabel(wiz.client);
  openTile.appendChild(openLab);
  openTile.onclick = () => openClient(wiz.client, wiz.url);
  const qrTile = document.createElement("button");
  qrTile.type = "button";
  qrTile.className = "wiz-tile";
  qrTile.innerHTML =
    '<svg viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="7" height="7" stroke="currentColor" stroke-width="1.8"/><rect x="14" y="3" width="7" height="7" stroke="currentColor" stroke-width="1.8"/><rect x="3" y="14" width="7" height="7" stroke="currentColor" stroke-width="1.8"/><path d="M14 14h3v3h-3zM18 18h3v3h-3zM14 21h3M21 14v3" stroke="currentColor" stroke-width="1.8"/></svg>';
  const qrLab = document.createElement("div");
  qrLab.className = "lab";
  qrLab.textContent = "Показать QR";
  qrTile.appendChild(qrLab);
  qrTile.onclick = () => {
    haptic();
    showQr(wiz.url);
  };
  tiles.appendChild(openTile);
  tiles.appendChild(qrTile);

  body.appendChild(recap);
  body.appendChild(link);
  body.appendChild(tiles);
  $("wizHint").textContent =
    "Ссылку можно вставить вручную в Happ или Incy — она не сгорает.";
  replayAnim(body, "wiz-swap");
  setMain("Готово", () => {
    haptic();
    closeWizard();
    load().catch(() => {});
  });
}

function defaultTitle() {
  const chips = nameChips(wiz.platform);
  return chips[0] || ("Устройство " + platformLabel(wiz.platform));
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

function paintDevice(d) {
  const me = window.__me;
  if ($("devBrand") && me && me.brand_name) $("devBrand").textContent = me.brand_name;
  $("devTitle").textContent = d.title || "Устройство";
  $("devClient").textContent = clientLabel(d.client);
  $("devPlatform").textContent = platformLabel(d.platform);
  $("devUrl").textContent = d.subscription_url || "Ссылка появится после создания";
  $("devOpenLabel").textContent = "Открыть в " + clientLabel(d.client);
  const on = Boolean(d.active);
  $("devStatus").classList.toggle("off", !on);
  $("devStatusText").textContent = on ? "Активно" : "Неактивно";
}

function showDevice(d) {
  haptic();
  screen = "device";
  openDevice = d;
  switchView("view-device", "push");
  try {
    tg.BackButton.show();
  } catch (_e) {}
  paintDevice(d);
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
      paintDevice(fresh);
    }
  }
  if (screen === "topup") renderTopup(me);
  if (!$("intro").classList.contains("hidden")) return;
  if (shouldShowIntro()) showIntro(me);
  else showApp();
}

async function load() {
  const me = await api("/api/me");
  if (me.maintenance) {
    showMaint(me.notice);
    return;
  }
  if (me.blocked) {
    showMaint(me.notice || "Доступ ограничен.");
    return;
  }
  paint(me);
}

function closeMenu() {
  $("menu").classList.add("hidden");
  $("menuScrim").classList.add("hidden");
}

function toggleMenu(e) {
  if (e) e.stopPropagation();
  haptic();
  $("menu").classList.toggle("hidden");
  $("menuScrim").classList.toggle("hidden", $("menu").classList.contains("hidden"));
}

$("menuBtn").onclick = toggleMenu;
$("devMore").onclick = toggleMenu;
$("menuScrim").onclick = closeMenu;
$("menu").onclick = (e) => e.stopPropagation();

$("topupBtn").onclick = () => {
  haptic();
  openTopup();
};

$("tabFast").onclick = () => {
  haptic();
  topupMode = "fast";
  if (window.__me) renderTopup(window.__me);
};

$("tabCustom").onclick = () => {
  haptic();
  topupMode = "custom";
  if (window.__me) renderTopup(window.__me);
};

function snapTopupFromRange() {
  const me = window.__me;
  if (!me) return;
  const val = Number($("topupRange").value);
  const plan = (me.plans || []).find((p) => planRub(p) === val);
  if (plan) topupCode = plan.code;
  renderTopup(me);
}

$("topupRange").oninput = () => {
  const me = window.__me;
  if (!me) return;
  const range = $("topupRange");
  setTopupRangeFill(range);
  const val = Number(range.value);
  $("customVal").textContent = String(val);
  $("customDays").textContent = `≈ ${daysLabel(topupDaysFor(me, val))} VPN`;
};

$("topupRange").onchange = () => snapTopupFromRange();

$("topupMinus").onclick = () => {
  const range = $("topupRange");
  range.value = String(Math.max(Number(range.min), Number(range.value) - Number(range.step)));
  haptic();
  snapTopupFromRange();
};

$("topupPlus").onclick = () => {
  const range = $("topupRange");
  range.value = String(Math.min(Number(range.max), Number(range.value) + Number(range.step)));
  haptic();
  snapTopupFromRange();
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
$("coachSkip").onclick = (e) => {
  e.stopPropagation();
  haptic();
  finishCoach();
};
$("coachNext").onclick = (e) => {
  e.stopPropagation();
  coachAdvance();
};
$("coachCard").onclick = (e) => e.stopPropagation();
$("coachCatch").onclick = () => {
  haptic();
  finishCoach();
};
$("coachReplay").onclick = () => {
  haptic();
  try {
    localStorage.removeItem(COACH_KEY);
  } catch (_e) {}
  maybeStartCoach(true);
};
window.addEventListener("resize", () => {
  if (coachVisible) layoutCoach();
});

$("promoToggle").onclick = () => {
  const body = $("promoBody");
  body.classList.toggle("open");
  $("promoChev").style.transform = body.classList.contains("open") ? "rotate(180deg)" : "rotate(0deg)";
};

let toastTimer = 0;
function showToast(text) {
  const el = $("appToast");
  if (!el) return;
  $("appToastText").textContent = text;
  el.classList.add("show");
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 1600);
}

$("devBack").onclick = () => onBack();

$("devCopy").onclick = () => {
  const d = openDevice;
  if (!d || !d.subscription_url) return;
  haptic();
  navigator.clipboard.writeText(d.subscription_url).then(() => {
    $("devCopy").classList.add("copied");
    $("devCopyLabel").textContent = "Готово";
    showToast("Ссылка скопирована");
    setTimeout(() => {
      $("devCopy").classList.remove("copied");
      $("devCopyLabel").textContent = "Копировать";
    }, 1600);
  }).catch(() => tg.showAlert("Не удалось скопировать"));
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
      paintDevice(openDevice);
    }
    await load();
    showToast("Ссылка перевыпущена. Обновите подписку в клиенте.");
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

$("intro").onclick = () => finishIntro();

$("qrClose").onclick = () => hideQr();
$("qrScrim").onclick = () => hideQr();

$("retryBtn").onclick = () => {
  showBoot();
  load().catch((err) => showFail(err.message || "Не удалось загрузить данные"));
};

if (tg.onEvent) {
  tg.onEvent("invoiceClosed", (status) => {
    if (status === "paid") load().catch(() => {});
  });
  tg.onEvent("viewportChanged", () => {
    if (coachVisible) layoutCoach();
    else if (!coachDone()) scheduleCoach();
  });
}
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && window.__me) {
    load().catch(() => {});
  }
});

load().catch((err) => showFail(err.message || "Не удалось загрузить данные"));
