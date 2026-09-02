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

const LK_TOKEN_KEY = "way_lk_token";

function readLkToken() {
  const params = new URLSearchParams(window.location.search);
  const fromUrl = (params.get("t") || "").trim();
  if (fromUrl) {
    try {
      localStorage.setItem(LK_TOKEN_KEY, fromUrl);
    } catch (_e) {}
    params.delete("t");
    const qs = params.toString();
    const next = window.location.pathname + (qs ? `?${qs}` : "") + window.location.hash;
    try {
      history.replaceState({}, "", next);
    } catch (_e) {}
    return fromUrl;
  }
  try {
    return localStorage.getItem(LK_TOKEN_KEY) || "";
  } catch (_e) {
    return "";
  }
}

const lkToken = readLkToken();

const $ = (id) => document.getElementById(id);

const PLATFORMS = [
  { id: "ios", title: "iPhone, iPad", hint: "IPHONE, IPAD", sub: "iOS 15+" },
  { id: "android", title: "Android", hint: "ANDROID", sub: "8.0+" },
  { id: "macos", title: "macOS", hint: "MACOS", sub: "12+" },
  { id: "windows", title: "Windows", hint: "WINDOWS", sub: "10/11" },
  { id: "androidtv", title: "Android TV", hint: "ANDROID TV", sub: "Смарт-ТВ" },
  { id: "appletv", title: "Apple TV", hint: "APPLE TV", sub: "tvOS" },
];

const DEFAULT_VPN_APPS = [
  {
    id: "incy",
    name: "Incy",
    mark: "IN",
    deep_link: "incy://import/{url}",
    platforms: ["ios", "macos", "appletv"],
    stores: {
      ios: "https://apps.apple.com/search?term=Incy",
      macos: "https://apps.apple.com/search?term=Incy",
      appletv: "https://apps.apple.com/search?term=Incy",
    },
  },
  {
    id: "happ",
    name: "Happ",
    mark: "H",
    deep_link: "happ://add/{url}",
    platforms: ["ios", "macos", "appletv", "android", "androidtv", "windows"],
    stores: {
      ios: "https://apps.apple.com/app/id6504287215",
      macos: "https://apps.apple.com/app/id6504287215",
      appletv: "https://apps.apple.com/app/id6504287215",
      android: "https://play.google.com/store/apps/details?id=com.happproxy",
      androidtv: "https://play.google.com/store/apps/details?id=com.happproxy",
      windows: "https://github.com/Happ-proxy/happ-desktop/releases",
    },
  },
  {
    id: "v2rayng",
    name: "v2rayNG",
    mark: "v2",
    deep_link: "v2rayng://install-sub?url={enc}",
    platforms: ["android", "androidtv"],
    stores: {
      android: "https://play.google.com/store/apps/details?id=com.v2ray.ang",
      androidtv: "https://play.google.com/store/apps/details?id=com.v2ray.ang",
    },
  },
  {
    id: "v2rayn",
    name: "v2rayN",
    mark: "v2",
    deep_link: "",
    platforms: ["windows"],
    stores: { windows: "https://github.com/2dust/v2rayN/releases" },
  },
];

let vpnApps = DEFAULT_VPN_APPS.slice();

function applyVpnApps(list) {
  vpnApps = Array.isArray(list) && list.length ? list : DEFAULT_VPN_APPS.slice();
}

function clientsFor(platform) {
  return vpnApps.filter((c) => (c.platforms || []).indexOf(platform) >= 0);
}

function clientById(id) {
  return vpnApps.find((c) => c.id === id) || DEFAULT_VPN_APPS.find((c) => c.id === id) || null;
}

function platformLabel(id) {
  const p = PLATFORMS.find((x) => x.id === id);
  return p ? p.title : id || "—";
}

function clientLabel(id) {
  const c = clientById(id);
  return (c && c.name) || id || "—";
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

function makeQrSvg(url, className) {
  if (!url || typeof qrcode !== "function") return null;
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
  const dark = className === "dev-qr-svg";
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 " + dim + " " + dim);
  svg.setAttribute("class", className || "wiz-qr-svg");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "QR-код");
  const bg = document.createElementNS(ns, "rect");
  bg.setAttribute("width", String(dim));
  bg.setAttribute("height", String(dim));
  bg.setAttribute("fill", dark ? "#0d1611" : "#ffffff");
  const path = document.createElementNS(ns, "path");
  path.setAttribute("d", d);
  path.setAttribute("fill", dark ? "#5fd68b" : "#0d1611");
  svg.appendChild(bg);
  svg.appendChild(path);
  return svg;
}

function showQr(url) {
  if (!url) return;
  const box = $("qrBox");
  box.innerHTML = "";
  const svg = makeQrSvg(url, "wiz-qr-svg");
  if (!svg) {
    tg.showAlert("Не удалось построить QR-код");
    return;
  }
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
  const headers = {
    "Content-Type": "application/json",
    "X-Init-Data": tg.initData || "",
    ...(opts.headers || {}),
  };
  if (lkToken) headers["X-Lk-Token"] = lkToken;
  const res = await fetch(path, {
    ...opts,
    headers,
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
  const wasHidden = $("app").classList.contains("hidden");
  hideIntro();
  $("boot").classList.add("hidden");
  $("fail").classList.add("hidden");
  $("maint").classList.add("hidden");
  $("app").classList.remove("hidden");
  if (wasHidden) {
    if (!reducedMotion()) replayAnim($("app"), "app-in");
    scheduleCoach();
  }
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
let loadSeq = 0;
let lastConnectUrl = null;
let openDevice = null;
let topupMode = "fast";
let topupCode = "";
let topupCustomRub = 0;

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

function clearCoachPulse() {
  document.querySelectorAll(".coach-pulse").forEach((el) => el.classList.remove("coach-pulse"));
}

function hideCoach() {
  coachVisible = false;
  if (coachPlaceTimer) {
    clearTimeout(coachPlaceTimer);
    coachPlaceTimer = 0;
  }
  clearCoachPulse();
  const el = $("coach");
  if (el) el.classList.add("hidden");
}

function finishCoach() {
  hideCoach();
  if (!hasRequiredCoach(window.__me)) markCoachDone();
}

function hasRequiredCoach(me) {
  return buildCoachSteps(me).some((s) => s.required);
}

function coachElReady(id) {
  const el = $(id);
  return Boolean(el && !el.classList.contains("hidden"));
}

function deviceCoachTarget() {
  if (coachElReady("ctaAdd")) return "ctaAdd";
  if (coachElReady("addDeviceEmpty")) return "addDeviceEmpty";
  return "";
}

function buildCoachSteps(me) {
  const steps = [];
  if (!me) return steps;
  if (me.balance_enabled) {
    const n = (me.devices || []).length;
    if (me.trial_available && coachElReady("trialHomeBtn")) {
      steps.push({
        id: "trialHomeBtn",
        required: true,
        title: "Начните бесплатно",
        text: "Нажмите сюда — пробные рубли сразу на баланс. Без устройства деньги не списываются.",
      });
    } else if ((me.balance_rub || 0) < 1 && coachElReady("topupBtn")) {
      steps.push({
        id: "topupBtn",
        required: true,
        title: "Пополните баланс",
        text: "Без денег устройство не создать. Сутки спишутся только после подключения.",
        action: "topup",
      });
    }
    const addId = n === 0 ? deviceCoachTarget() : "";
    if (addId) {
      steps.push({
        id: addId,
        required: true,
        title: "Добавьте устройство",
        text: "Без устройства VPN не заработает и баланс не начнёт тратиться. Нажмите кнопку и пройдите три коротких шага.",
        action: "wizard",
      });
    }
  } else if (!me.has_access && coachElReady("topupBtn")) {
    steps.push({
      id: "topupBtn",
      required: true,
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
  $("coachSkip").classList.toggle("hidden", Boolean(step.required));
  $("coach").classList.toggle("is-required", Boolean(step.required));
  const catchEl = $("coachCatch");
  if (catchEl) catchEl.style.pointerEvents = step.required ? "none" : "auto";
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
  const pad = 8;
  hole.style.top = `${Math.max(8, r.top - pad)}px`;
  hole.style.left = `${Math.max(8, r.left - pad)}px`;
  hole.style.width = `${r.width + pad * 2}px`;
  hole.style.height = `${r.height + pad * 2}px`;
  const radius = getComputedStyle(target).borderRadius;
  hole.style.borderRadius = radius && radius !== "0px" ? radius : "16px";
  clearCoachPulse();
  target.classList.add("coach-pulse");

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
  const required = hasRequiredCoach(window.__me);
  if (!force && coachDone() && !required) return;
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
  if (topupMode === "custom") {
    const min = Number(me.topup_min) || 1;
    const max = Number(me.topup_max) || min;
    const n = Number(topupCustomRub);
    if (!Number.isFinite(n) || n < min || n > max) return null;
    return {
      code: "b" + n,
      title: n + " рублей",
      topup_rub: n,
      rub: n,
    };
  }
  const plans = me.plans || [];
  return plans.find((p) => p.code === topupCode) || plans[0] || null;
}

function ensureTopupCode(me) {
  const plans = me.plans || [];
  if (plans.some((p) => p.code === topupCode)) return;
  const hit = plans.find((p) => planRub(p) === 100);
  topupCode = (hit || plans[0] || {}).code || "";
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
    const min = Number(me.topup_min) || 1;
    setMain(topupMode === "custom" ? `Укажите сумму от ${min} ₽` : "");
    const btn = $("appMainBtn");
    if (btn && topupMode === "custom") btn.disabled = true;
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
function browserCabinet() {
  return Boolean(lkToken) && !tg.initData;
}

function syncWebBack() {
  const el = $("webBack");
  if (!el) return;
  el.classList.toggle("hidden", !(browserCabinet() && screen !== "home"));
}

function onBack() {
  haptic();
  if (screen === "wizard" || screen === "device") {
    if (!$("qrSheet").classList.contains("hidden")) {
      hideQr();
      return;
    }
  }
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
    if (typeof tg.enableVerticalSwipes === "function") tg.enableVerticalSwipes();
  } catch (_e) {}
  syncWebBack();
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
  syncWebBack();
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
  const canCustom = Boolean(me.balance_enabled);
  $("topupTabs").classList.toggle("hidden", !canCustom);
  if (!canCustom) topupMode = "fast";
  applyTopupMode();
  $("topupHint").textContent = me.balance_enabled
    ? `С каждого устройства списывается ${me.vpn_day_price_rub} ₽ в сутки. Карточки показывают, на сколько дней хватит суммы при одном устройстве.`
    : "Выберите срок подписки.";
  const amounts = plans.map(planRub).filter((n) => n > 0);
  const hitAmt = amounts.includes(100) ? 100 : (amounts[1] || 0);
  const grid = $("topupGrid");
  grid.innerHTML = "";
  plans.forEach((plan) => {
    const amount = planRub(plan);
    const b = document.createElement("button");
    b.type = "button";
    b.className = "pay-card" + (plan.code === topupCode ? " on" : "");
    if (me.balance_enabled && amount === hitAmt && hitAmt > 0) {
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
      ? `≈ ${daysLabel(topupDaysFor(me, amount))}`
      : daysLabel(plan.days);
    b.appendChild(amt);
    b.appendChild(days);
    if (!me.balance_enabled) {
      const rateEl = document.createElement("div");
      rateEl.className = "pay-rate";
      rateEl.textContent = plan.rub ? `${plan.rub} ₽` : `${plan.stars} звёзд`;
      b.appendChild(rateEl);
    }
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
    if (!topupCustomRub) {
      const hit = amounts.includes(100) ? 100 : (planRub(currentTopupPlan(me)) || min);
      topupCustomRub = Math.min(max, Math.max(min, hit));
    }
    const inp = $("topupAmount");
    if (document.activeElement !== inp) inp.value = String(topupCustomRub);
    paintCustomTopup(me);
    const nDev = (me.devices || []).length;
    $("topupStrip").textContent = nDev
      ? `Сейчас устройств: ${nDev}. Чем их больше, тем быстрее уходит баланс.`
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
  const cap = Number(me.max_devices) || 0;
  const n = (me.devices || []).length;
  if (cap > 0 && n >= cap) {
    tg.showAlert("Можно подключить не больше " + cap + " устройств");
    return;
  }
  haptic();
  wiz.step = 1;
  wiz.platform = "ios";
  const first = clientsFor("ios")[0];
  wiz.client = first ? first.id : "";
  wiz.title = "";
  wiz.url = "";
  screen = "wizard";
  switchView("view-wizard", "push");
  try {
    tg.BackButton.show();
  } catch (_e) {}
  syncWebBack();
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
        wiz.client = first ? first.id : "";
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
    if (!list.length) {
      const empty = document.createElement("p");
      empty.className = "muted";
      empty.textContent = "Для этой платформы нет приложений. Добавьте их в админке.";
      body.appendChild(empty);
      $("wizHint").textContent = "";
      replayAnim(body, "wiz-swap");
      setMain("");
      return;
    }
    if (!list.some((c) => c.id === wiz.client)) wiz.client = list[0].id;
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
      const store = (c.stores || {})[wiz.platform];
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

function clientDeepLink(client, url) {
  if (!url) return "";
  const c = clientById(client);
  const tpl = (c && c.deep_link) || "";
  if (!tpl) return "";
  return tpl.split("{enc}").join(encodeURIComponent(url)).split("{url}").join(url);
}

function openClient(client, url) {
  haptic();
  if (!url) return;
  const deep = clientDeepLink(client, url);
  if (!deep) {
    tg.openLink(url);
    return;
  }
  let bridge = "";
  try {
    bridge = new URL("open.html", window.location.href).href + "?to=" + encodeURIComponent(deep);
  } catch (_e) {}
  if (bridge) {
    tg.openLink(bridge);
    return;
  }
  window.location.href = deep;
}

function paintDevice(d) {
  $("devTitle").textContent = d.title || "Устройство";
  $("devClient").textContent = clientLabel(d.client);
  $("devPlatform").textContent = platformLabel(d.platform);
  $("devUrl").textContent = d.subscription_url || "Ссылка появится после создания";
  $("devOpenLabel").textContent = "Открыть в " + clientLabel(d.client);
  const on = Boolean(d.active);
  $("devStatus").classList.toggle("off", !on);
  $("devStatusText").textContent = on ? "Активно" : "Неактивно";
  const box = $("devQr");
  const btn = $("devQrBtn");
  box.innerHTML = "";
  const svg = d.subscription_url ? makeQrSvg(d.subscription_url, "dev-qr-svg") : null;
  btn.classList.toggle("hidden", !svg);
  if (svg) box.appendChild(svg);
}

function showDevice(d) {
  haptic();
  screen = "device";
  openDevice = d;
  switchView("view-device", "push");
  try {
    tg.BackButton.show();
    if (typeof tg.disableVerticalSwipes === "function") tg.disableVerticalSwipes();
  } catch (_e) {}
  syncWebBack();
  paintDevice(d);
  setMain("");
}

function renderConnect(me) {
  const wrap = $("connectWrap");
  const body = $("connectBody");
  if (me.balance_enabled) {
    wrap.classList.add("hidden");
    lastConnectUrl = null;
    return;
  }
  wrap.classList.remove("hidden");
  const url = me.subscription_url || "";
  if (url === lastConnectUrl && body.childElementCount) return;
  lastConnectUrl = url;
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

function devicesKey(me) {
  return (me.devices || [])
    .map((d) => [d.id, d.title || "", d.active ? 1 : 0, d.client || "", d.platform || ""].join(":"))
    .join("|") + "|" + String(me.max_devices || 0);
}

let lastDevicesKey = "";

function renderDevices(me) {
  const block = $("devicesBlock");
  if (!me.balance_enabled) {
    block.classList.add("hidden");
    lastDevicesKey = "";
    return;
  }
  block.classList.remove("hidden");
  const n = me.devices.length;
  const cap = Number(me.max_devices) || 0;
  const atCap = cap > 0 && n >= cap;
  $("deviceCount").textContent = cap > 0 ? "· " + n + " из " + cap : "· " + n;
  $("addDevice").classList.toggle("hidden", n === 0 || atCap);
  $("emptyDevices").classList.toggle("hidden", n > 0);
  const body = $("devicesBody");
  body.classList.toggle("hidden", n === 0);
  const key = devicesKey(me);
  if (key === lastDevicesKey) return;
  lastDevicesKey = key;
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

function fmtStoryRemain(sec) {
  sec = Math.max(0, Math.floor(sec));
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  if (h > 0) return h + " ч " + String(m).padStart(2, "0") + " мин";
  return String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
}

let storyTick = 0;

function stopStoryTimer() {
  clearInterval(storyTick);
  storyTick = 0;
}

function storyRemain(me) {
  if (me.story_check_until) {
    const until = new Date(me.story_check_until).getTime();
    if (!Number.isNaN(until)) return Math.max(0, Math.ceil((until - Date.now()) / 1000));
  }
  return Number(me.story_check_seconds) || 0;
}

function paintStoryCard(me, rub) {
  const card = $("storyCard");
  const timer = $("storyTimer");
  const pending = !!me.story_pending && !me.story_rewarded;
  card.classList.toggle("is-checking", pending);
  stopStoryTimer();
  if (pending) {
    $("storyTitle").textContent = "Проверка истории";
    $("storyNote").textContent = "Награда придёт, когда таймер дойдёт до нуля.";
    const tick = () => {
      const left = storyRemain(window.__me || me);
      timer.textContent = fmtStoryRemain(left);
      timer.classList.remove("hidden");
      if (left <= 0) {
        stopStoryTimer();
        load();
      }
    };
    tick();
    storyTick = setInterval(tick, 1000);
    return;
  }
  timer.classList.add("hidden");
  if (me.story_rewarded) {
    $("storyTitle").textContent = "Выложить историю";
    $("storyNote").textContent = "Награда уже начислена. Можно выложить ещё раз.";
    $("storyBtn").textContent = "Ещё раз";
  } else {
    $("storyTitle").textContent = `История — ${rub} ₽`;
    $("storyNote").textContent = "Откроется редактор истории Telegram. Награда один раз после проверки.";
    $("storyBtn").textContent = "Выложить";
  }
}

function paint(me) {
  applyVpnApps(me.vpn_apps);
  if (me.brand_name) document.title = me.brand_name;
  $("name").textContent = me.user.name;
  $("login").textContent = me.user.username || "без username";
  const avatar = $("avatar");
  const photo = me.user.photo || "";
  if (photo) {
    if (avatar.getAttribute("src") !== photo) avatar.src = photo;
  } else if (avatar.getAttribute("src")) {
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
  const storyCard = $("storyCard");
  if (me.story_reward_enabled) {
    const rub = me.story_reward_rub || 0;
    storyCard.classList.remove("hidden");
    paintStoryCard(me, rub);
  } else {
    storyCard.classList.add("hidden");
    stopStoryTimer();
  }
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
  const trustHelp = $("trustHelp");
  const menuTrust = $("menuTrust");
  const t = me.trust;
  const showTrust = Boolean(me.balance_enabled && t && t.enabled !== false);
  if (trustHelp) trustHelp.classList.toggle("hidden", !showTrust);
  if (menuTrust) menuTrust.classList.toggle("hidden", !showTrust);
  if (!showTrust) {
    trustBtn.classList.add("hidden");
    trustOpen.classList.add("hidden");
  } else if (t.open) {
    trustBtn.classList.add("hidden");
    trustOpen.classList.remove("hidden");
    const due = t.open.due_at ? new Date(t.open.due_at) : null;
    $("trustDue").textContent = due && !Number.isNaN(due.getTime())
      ? `вернуть ${rublesLabel(t.open.amount)} · ${due.toLocaleDateString("ru-RU")}`
      : `вернуть ${rublesLabel(t.open.amount)}`;
  } else {
    trustOpen.classList.add("hidden");
    trustBtn.classList.remove("hidden");
    trustBtn.textContent = t.available
      ? Number(t.fee) > 0
        ? `Обещанный платёж · ${daysLabel(t.days)} + ${rublesLabel(t.fee)}`
        : `Обещанный платёж · ${daysLabel(t.days)}`
      : `Обещанный платёж · ${daysLabel(t.days)}`;
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
      const same =
        fresh.subscription_url === openDevice.subscription_url &&
        fresh.title === openDevice.title &&
        fresh.active === openDevice.active &&
        fresh.client === openDevice.client &&
        fresh.platform === openDevice.platform;
      openDevice = fresh;
      if (!same) paintDevice(fresh);
    }
  }
  if (screen === "topup") renderTopup(me);
  if (!$("intro").classList.contains("hidden")) return;
  if (shouldShowIntro()) showIntro(me);
  else showApp();
  syncCoach(me);
}

function syncCoach(me) {
  if (screen !== "home") return;
  if ($("app").classList.contains("hidden")) return;
  if (hasRequiredCoach(me)) {
    if (coachVisible) {
      const oldId = coachList[coachIndex] && coachList[coachIndex].id;
      coachList = buildCoachSteps(me);
      if (!coachList.length) {
        hideCoach();
        return;
      }
      const idx = coachList.findIndex((s) => s.id === oldId);
      coachIndex = idx >= 0 ? idx : 0;
      placeCoach();
      return;
    }
    scheduleCoach();
    return;
  }
  if (coachVisible) finishCoach();
}

async function load() {
  const seq = ++loadSeq;
  const me = await api("/api/me");
  if (seq !== loadSeq) return;
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
  const inp = $("topupAmount");
  if (inp) setTimeout(() => inp.focus(), 50);
};

function paintCustomTopup(me) {
  const min = Number(me.topup_min) || 1;
  const max = Number(me.topup_max) || min;
  const raw = String(($("topupAmount") && $("topupAmount").value) || "").replace(/\D/g, "");
  const n = raw ? Number(raw) : null;
  const hint = $("topupCustomHint");
  if (n == null) {
    $("customDays").textContent = "Введите любую сумму";
    hint.textContent = `От ${min} до ${max} ₽`;
    hint.classList.remove("bad");
    return;
  }
  const ok = n >= min && n <= max;
  if (ok) topupCustomRub = n;
  $("customDays").textContent = `≈ ${daysLabel(topupDaysFor(me, n))}`;
  hint.textContent = ok ? `От ${min} до ${max} ₽` : `Можно от ${min} до ${max} ₽`;
  hint.classList.toggle("bad", !ok);
}

$("topupAmount").oninput = () => {
  const me = window.__me;
  if (!me) return;
  const inp = $("topupAmount");
  const next = String(inp.value || "").replace(/\D/g, "");
  if (inp.value !== next) inp.value = next;
  paintCustomTopup(me);
  updateTopupCta(me);
};

$("topupAmount").onkeydown = (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    $("topupAmount").blur();
    const btn = $("appMainBtn");
    if (btn && !btn.disabled) btn.click();
  }
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

$("trustBtn").onclick = () => openTrust();
$("trustHelp").onclick = () => openTrust();
$("menuTrust").onclick = () => {
  closeMenu();
  openTrust();
};

function openTrust() {
  const me = window.__me;
  const t = me && me.trust;
  if (!me || !me.balance_enabled || !t) return;
  haptic();
  if (t.open) {
    const due = t.open.due_at ? new Date(t.open.due_at) : null;
    const when = due && !Number.isNaN(due.getTime()) ? due.toLocaleDateString("ru-RU") : "";
    tg.showAlert(
      when
        ? `Обещанный платёж уже открыт. Вернуть ${rublesLabel(t.open.amount)} ${when}.`
        : `Обещанный платёж уже открыт. Вернуть ${rublesLabel(t.open.amount)}.`
    );
    return;
  }
  if (!t.available) {
    tg.showAlert(t.reason || "Сейчас обещанный платёж недоступен");
    return;
  }
  const credit = rublesLabel(t.amount);
  const fee = Number(t.fee) || 0;
  const repay = rublesLabel(t.repay || t.amount + fee);
  const text =
    `Начислим ${credit} — ${daysLabel(t.days)} одного устройства.` +
    (fee > 0 ? ` За услугу спишется ещё ${rublesLabel(fee)}.` : "") +
    ` Через ${daysLabel(t.days)} вернём ${repay}, даже если баланс уйдёт в минус.`;
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
}

$("storyBtn").onclick = async () => {
  haptic();
  const me = window.__me;
  if (!me || !me.story_reward_enabled) return;
  const media = me.story_media_url || `${window.location.origin}/story.png`;
  const caption = [me.story_share_text, me.story_bot_url].filter(Boolean).join("\n");
  const canShare = typeof tg.shareToStory === "function";
  if (!canShare || browserCabinet()) {
    tg.showAlert("Откройте кабинет в Telegram, чтобы выложить историю. Нужна свежая версия приложения.");
    return;
  }
  try {
    tg.shareToStory(media, {
      text: caption,
      widget_link: me.story_bot_url
        ? { url: me.story_bot_url, name: me.brand_name || "VPN" }
        : undefined,
    });
  } catch (_e) {
    tg.showAlert("Не удалось открыть историю. Обновите Telegram.");
    return;
  }
  if (me.story_rewarded || me.story_pending) return;
  try {
    await api("/api/story-share", { method: "POST", body: "{}" });
    await load();
  } catch (e) {
    showErr(e);
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
  const step = coachList[coachIndex];
  if (step && step.required) return;
  finishCoach();
};
$("coachNext").onclick = (e) => {
  e.stopPropagation();
  coachAdvance();
};
$("coachCard").onclick = (e) => e.stopPropagation();
$("coachCatch").onclick = () => {
  const step = coachList[coachIndex];
  if (step && step.required) return;
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

$("devQrBtn").onclick = () => {
  const d = openDevice;
  if (!d || !d.subscription_url) return;
  haptic();
  showQr(d.subscription_url);
};

function askDeleteDevice() {
  return new Promise((resolve) => {
    const msg = "Устройство будет удалено, VPN на нём перестанет работать. Продолжить?";
    if (typeof tg.showConfirm === "function") {
      tg.showConfirm(msg, (ok) => resolve(Boolean(ok)));
      return;
    }
    resolve(window.confirm(msg));
  });
}

async function deleteDevice() {
  const d = openDevice;
  if (!d) return;
  haptic();
  if (!(await askDeleteDevice())) return;
  try {
    await api(`/api/devices/${d.id}`, { method: "DELETE" });
    lastDevicesKey = "";
    openHome();
    await load();
    showToast("Устройство удалено");
  } catch (e) {
    showErr(e);
  }
}

$("devDelete").onclick = () => deleteDevice();

function vpnReportContext() {
  const me = window.__me || {};
  const plat = tg.platform || "";
  const conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  const tgUser = (tg.initDataUnsafe && tg.initDataUnsafe.user) || {};
  const devices = Array.isArray(me.devices) ? me.devices : [];
  return {
    source: "webapp",
    view: screen,
    wizard_step: screen === "wizard" ? wiz.step : null,
    platform: (openDevice && openDevice.platform) || wiz.platform || plat,
    client: (openDevice && openDevice.client) || wiz.client || "",
    device: openDevice
      ? {
          id: openDevice.id,
          title: openDevice.title,
          client: openDevice.client,
          platform: openDevice.platform,
          active: openDevice.active,
        }
      : null,
    me: {
      days: me.days,
      days_left: me.days_left,
      balance_rub: me.balance_rub,
      billing_active: me.billing_active,
      has_access: me.has_access,
      device_count: devices.length,
      devices: devices.map((d) => ({
        id: d.id,
        title: d.title,
        client: d.client,
        platform: d.platform,
        active: d.active,
      })),
    },
    telegram: {
      platform: plat,
      version: tg.version || "",
      colorScheme: tg.colorScheme || "",
      isExpanded: !!tg.isExpanded,
      viewportHeight: tg.viewportHeight || window.innerHeight,
      viewportStableHeight: tg.viewportStableHeight || window.innerHeight,
      language: tgUser.language_code || navigator.language || "",
      isPremium: !!tgUser.is_premium,
    },
    browser: {
      userAgent: navigator.userAgent || "",
      language: navigator.language || "",
      languages: navigator.languages || [],
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "",
      timezoneOffset: new Date().getTimezoneOffset(),
      online: navigator.onLine,
      connection: conn
        ? { type: conn.effectiveType || conn.type || "", downlink: conn.downlink, rtt: conn.rtt }
        : null,
      screen: { w: window.screen && screen.width, h: window.screen && screen.height, dpr: window.devicePixelRatio },
    },
    page: { href: location.href, hidden: document.hidden },
    now: new Date().toISOString(),
  };
}

$("vpnDown").onclick = async () => {
  haptic();
  try {
    await api("/api/vpn-report", {
      method: "POST",
      body: JSON.stringify({ context: vpnReportContext() }),
    });
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

$("webBack").onclick = () => onBack();

if (tg.onEvent) {
  tg.onEvent("invoiceClosed", (status) => {
    if (status === "paid") load().catch(() => {});
  });
  tg.onEvent("viewportChanged", () => {
    if (coachVisible) layoutCoach();
  });
}
let visTimer = 0;
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState !== "visible" || !window.__me) return;
  clearTimeout(visTimer);
  visTimer = setTimeout(() => load().catch(() => {}), 400);
});

load().catch((err) => showFail(err.message || "Не удалось загрузить данные"));
