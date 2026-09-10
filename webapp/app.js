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
      setBottomBarColor() {},
      requestFullscreen() {},
      disableVerticalSwipes() {},
      isFullscreen: false,
      viewportHeight: window.innerHeight,
      viewportStableHeight: window.innerHeight,
      safeAreaInset: { top: 0, bottom: 0, left: 0, right: 0 },
      contentSafeAreaInset: { top: 0, bottom: 0, left: 0, right: 0 },
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
if (typeof tg.disableVerticalSwipes === "function") {
  try {
    tg.disableVerticalSwipes();
  } catch (_e) {}
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

function applyViewport() {
  const root = document.documentElement;
  const h = Number(tg.viewportHeight) || window.innerHeight;
  const sh = Number(tg.viewportStableHeight) || h;
  const sa = tg.safeAreaInset || {};
  const ca = tg.contentSafeAreaInset || {};
  const fs = Boolean(tg.isFullscreen);
  const top = (Number(sa.top) || 0) + (Number(ca.top) || 0);
  const bottom = (Number(sa.bottom) || 0) + (Number(ca.bottom) || 0);
  const left = (Number(sa.left) || 0) + (Number(ca.left) || 0);
  const right = (Number(sa.right) || 0) + (Number(ca.right) || 0);
  root.classList.toggle("is-fullscreen", fs);
  root.style.setProperty("--app-vh", h + "px");
  root.style.setProperty("--app-svh", sh + "px");
  root.style.setProperty("--app-safe-top", (fs ? Math.max(top, 62) : top) + "px");
  root.style.setProperty("--app-safe-bottom", bottom + "px");
  root.style.setProperty("--app-safe-left", left + "px");
  root.style.setProperty("--app-safe-right", right + "px");
}

let fsTries = 0;
function requestMiniAppFullscreen() {
  if (tg.isFullscreen) return;
  if (typeof tg.requestFullscreen !== "function") return;
  if (fsTries > 6) return;
  fsTries += 1;
  try {
    tg.requestFullscreen();
  } catch (_e) {}
}

applyTheme();
applyViewport();
requestMiniAppFullscreen();

let navScrollY = 0;
function syncNavScroll() {
  const y = window.scrollY || document.documentElement.scrollTop || 0;
  document.documentElement.classList.toggle("is-scrolled", y > 10);
  navScrollY = y;
}
window.addEventListener("scroll", syncNavScroll, { passive: true });

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
    icon: "/icons/incy.png",
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
    icon: "/icons/happ.png",
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
    icon: "/icons/v2rayng.png",
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
    icon: "/icons/v2rayn.png",
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

function fillAppLogo(el, app, muted) {
  const icon = app && app.icon;
  el.className = "wiz-app-logo" + (muted ? " muted" : "") + (icon ? " has-img" : "");
  el.textContent = "";
  if (icon) {
    const img = document.createElement("img");
    img.alt = "";
    img.src = icon;
    img.onerror = () => {
      el.classList.remove("has-img");
      el.textContent = (app && app.mark) || "";
    };
    el.appendChild(img);
    return;
  }
  el.textContent = (app && app.mark) || "";
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
  const hours = remainHours(me);
  const days = hours / 24;
  const running = me.balance_enabled ? n > 0 : Boolean(me.has_access);
  if (me.balance_enabled) {
    $("balanceLine").innerHTML = `${me.balance_rub} ₽ <span>на счету</span>`;
  } else {
    $("balanceLine").innerHTML = `${remainLabel(me, { running })} <span>подписки</span>`;
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
  } else if (days < 3) {
    setFrog("worried");
    setGauge(days / GAUGE_REF_DAYS, "warn");
    badge.classList.remove("hidden");
    badge.textContent = remainLabel(me, { running });
    pill.className = "status-pill warn";
    pill.innerHTML = me.balance_enabled
      ? '<span class="dot"></span> Баланс заканчивается'
      : '<span class="dot"></span> Срок заканчивается';
    $("statusNote").textContent = me.balance_enabled
      ? `При текущем расходе осталось примерно ${remainLabel(me, { running })}.`
      : `Осталось ${remainLabel(me, { running })} подписки.`;
  } else {
    setFrog("happy");
    setGauge(days / GAUGE_REF_DAYS, "ok");
    badge.classList.remove("hidden");
    badge.textContent = remainLabel(me, { running });
    pill.className = "status-pill on";
    pill.innerHTML = '<span class="dot"></span> Подключено';
    $("statusNote").textContent = me.balance_enabled
      ? `При текущем расходе баланса хватит примерно на ${remainLabel(me, { running })}.`
      : `Подписка действует ещё ${remainLabel(me, { running })}.`;
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

function haptic(kind) {
  try {
    tg.HapticFeedback.impactOccurred(kind || "light");
  } catch (_e) {}
}

async function api(path, opts = {}) {
  const headers = {
    "X-Init-Data": tg.initData || "",
    ...(opts.headers || {}),
  };
  if (lkToken) headers["X-Lk-Token"] = lkToken;
  if (!(opts.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
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

let thanksArmed = false;
let thanksFlushing = false;

function armThanksOnClose() {
  thanksArmed = true;
}

function flushThanksOnClose() {
  if (!thanksArmed || thanksFlushing) return;
  thanksArmed = false;
  thanksFlushing = true;
  const headers = {
    "Content-Type": "application/json",
    "X-Init-Data": tg.initData || "",
  };
  if (lkToken) headers["X-Lk-Token"] = lkToken;
  try {
    fetch("/api/cabinet-leave", {
      method: "POST",
      headers,
      body: "{}",
      keepalive: true,
    });
  } catch (_e) {}
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

function hoursWord(n) {
  const abs = Math.abs(n);
  const mod10 = abs % 10;
  const mod100 = abs % 100;
  if (mod10 === 1 && mod100 !== 11) return "час";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return "часа";
  return "часов";
}

function hoursLabel(n) {
  return `${n} ${hoursWord(n)}`;
}

function remainHours(me) {
  const raw = Number(me && me.hours_left);
  if (Number.isFinite(raw) && raw >= 0) return raw;
  const days = me && me.balance_enabled ? me.days_left : me && me.days;
  return Math.max(0, Number(days) || 0) * 24;
}

function remainLabel(me, opts) {
  const running = Boolean(opts && opts.running);
  const hours = remainHours(me);
  if (hours < 1) return running ? "меньше часа" : daysLabel(0);
  if (hours < 24) return hoursLabel(hours);
  return daysLabel(Math.floor(hours / 24));
}

function friendsWord(n) {
  const abs = Math.abs(n);
  const mod10 = abs % 10;
  const mod100 = abs % 100;
  if (mod10 === 1 && mod100 !== 11) return "друг";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return "друга";
  return "друзей";
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

const INTRO_KEY = "way_intro_v4";
let introTimer = 0;
let introHapticTimer = 0;
let introHapticLoop = 0;
let introShown = false;

function clearIntroTimers() {
  if (introTimer) {
    clearTimeout(introTimer);
    introTimer = 0;
  }
  if (introHapticTimer) {
    clearTimeout(introHapticTimer);
    introHapticTimer = 0;
  }
  if (introHapticLoop) {
    clearInterval(introHapticLoop);
    introHapticLoop = 0;
  }
}

function hideIntro() {
  clearIntroTimers();
  const el = $("intro");
  el.classList.remove("intro-catch", "intro-go", "intro-in");
  el.classList.add("hidden");
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

function pulseIntroCatch() {
  const el = $("intro");
  if (!el || el.classList.contains("hidden") || el.classList.contains("intro-go")) return;
  haptic("medium");
  try {
    tg.HapticFeedback.notificationOccurred("success");
  } catch (_e) {}
  el.classList.add("intro-catch");
  setTimeout(() => el.classList.remove("intro-catch"), 280);
}

function finishIntro() {
  const el = $("intro");
  if (el.classList.contains("hidden") || el.classList.contains("intro-go")) return;
  clearIntroTimers();
  markIntroSeen();
  $("app").classList.remove("hidden");
  $("app").inert = true;
  el.classList.add("intro-go");
  introTimer = setTimeout(() => {
    $("app").inert = false;
    showApp();
    maybeOpenFirstRun(window.__me);
  }, reducedMotion() ? 0 : 800);
}

function reducedMotion() {
  return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function shouldShowIntro() {
  return !introSeen();
}

function showIntro(me) {
  const user = me.user || {};
  const username = String(user.username || "").trim().replace(/^@+/, "");
  const nick = $("introNick");
  nick.textContent = username ? `@${username}` : "";
  nick.classList.toggle("hidden", !username);
  const avatar = $("introAvatar");
  const fallback = $("introFallback");
  fallback.textContent = String(user.name || username || "?").charAt(0).toUpperCase();
  fallback.classList.remove("hidden");
  avatar.classList.add("hidden");
  avatar.onload = () => {
    avatar.classList.remove("hidden");
    fallback.classList.add("hidden");
  };
  avatar.onerror = () => {
    avatar.classList.add("hidden");
    fallback.classList.remove("hidden");
  };
  if (user.photo) avatar.src = user.photo;
  else avatar.removeAttribute("src");
  $("boot").classList.add("hidden");
  $("fail").classList.add("hidden");
  $("maint").classList.add("hidden");
  $("app").classList.add("hidden");
  const el = $("intro");
  el.classList.remove("hidden", "intro-catch", "intro-go", "intro-in");
  void el.offsetWidth;
  el.classList.add("intro-in");
  clearIntroTimers();
  introTimer = setTimeout(finishIntro, reducedMotion() ? 1600 : 4200);
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
  if (id !== "view-home" && id !== "view-wizard") hideCoach();
  ["view-home", "view-topup", "view-wizard", "view-device", "view-support", "view-faq", "view-billing", "view-referrals", "view-offer"].forEach((vid) => {
    const el = $(vid);
    const on = vid === id;
    el.classList.toggle("hidden", !on);
    el.classList.remove("view-in-fade", "view-in-push", "view-in-pop");
    if (on) replayAnim(el, "view-in-" + (motion || "fade"));
  });
  window.scrollTo(0, 0);
  document.documentElement.classList.remove("is-scrolled");
  navScrollY = 0;
}

const wiz = {
  step: 1,
  platform: "ios",
  client: "incy",
  title: "",
  url: "",
  fromOffer: false,
};

let screen = "home";
let firstRunBusy = false;
let loadSeq = 0;
let lastConnectUrl = null;
let openDevice = null;
let topupMode = "fast";
let faqFrom = "home";
let topupCode = "";
let topupCustomRub = 0;

const COACH_KEY = "way_home_coach_v2";
const WIZ_COACH_KEY = "way_wiz_coach_v1";
const ONBOARD_KEY = "way_onboard_v1";
const OFFER_SKIP_KEY = "way_offer_skip_v1";
let coachIndex = 0;
let coachList = [];
let coachVisible = false;
let coachPlaceTimer = 0;
let coachStartTimers = [];
let coachLayoutRaf = 0;
let coachViewportTimer = 0;
let coachHideTimer = 0;
let coachScrollY = 0;
let coachScrollLocked = false;

function coachDone() {
  try {
    return localStorage.getItem(ONBOARD_KEY) === "1" || localStorage.getItem(COACH_KEY) === "1";
  } catch (_e) {
    return false;
  }
}

function onboardDone() {
  try {
    return localStorage.getItem(ONBOARD_KEY) === "1";
  } catch (_e) {
    return false;
  }
}

function markOnboardDone() {
  try {
    localStorage.setItem(ONBOARD_KEY, "1");
    localStorage.setItem(COACH_KEY, "1");
    localStorage.setItem(OFFER_SKIP_KEY, "1");
  } catch (_e) {}
  try {
    localStorage.setItem(WIZ_COACH_KEY, JSON.stringify({ 1: 1, 2: 1, 3: 1, 4: 1, done: 1 }));
  } catch (_e) {}
}

function offerSkipped() {
  try {
    return localStorage.getItem(OFFER_SKIP_KEY) === "1";
  } catch (_e) {
    return false;
  }
}

function skipOffer() {
  try {
    localStorage.setItem(OFFER_SKIP_KEY, "1");
  } catch (_e) {}
}

function shouldShowOffer(me) {
  if (!me) return false;
  if ((me.devices || []).length) return false;
  if (me.trial_available) return true;
  const kind = me.trial_notice && me.trial_notice.kind;
  if (kind === "claim" || kind === "granted") return true;
  if (!me.balance_enabled || me.has_paid_topup) return false;
  return Number(me.balance_rub) > 0 || Number(me.days) > 0 || Number(me.trial_days) > 0;
}

function maybeOpenFirstRun(me) {
  if (!me || firstRunBusy) return;
  if ((me.devices || []).length) return;
  if (
    screen === "wizard" ||
    screen === "device" ||
    screen === "topup" ||
    screen === "support" ||
    screen === "faq" ||
    screen === "billing"
  ) {
    return;
  }
  if (screen === "offer") {
    paintOffer(me);
    return;
  }
  if (shouldShowOffer(me)) {
    openOffer();
    return;
  }
  if (me.balance_enabled) startWizard({ fromOffer: false });
}

function markCoachDone() {
  try {
    localStorage.setItem(COACH_KEY, "1");
  } catch (_e) {}
}

function clearCoachPulse() {
  document.querySelectorAll(".coach-pulse").forEach((el) => el.classList.remove("coach-pulse"));
}

function onCoachScrollGuard(e) {
  if (!coachScrollLocked) return;
  const t = e.target;
  if (t && t.closest && t.closest("#coachCard")) return;
  e.preventDefault();
}

function lockCoachScroll() {
  if (coachScrollLocked) return;
  coachScrollLocked = true;
  coachScrollY = window.scrollY || document.documentElement.scrollTop || 0;
  document.body.classList.add("coach-lock");
  document.body.style.top = `-${coachScrollY}px`;
  try {
    if (typeof tg.disableVerticalSwipes === "function") tg.disableVerticalSwipes();
  } catch (_e) {}
}

function unlockCoachScroll() {
  if (!coachScrollLocked) return;
  coachScrollLocked = false;
  document.body.classList.remove("coach-lock");
  document.body.style.top = "";
  window.scrollTo(0, coachScrollY);
  try {
    if (screen === "home" && typeof tg.enableVerticalSwipes === "function") tg.enableVerticalSwipes();
  } catch (_e) {}
}

function hideCoach() {
  coachVisible = false;
  if (coachPlaceTimer) {
    clearTimeout(coachPlaceTimer);
    coachPlaceTimer = 0;
  }
  if (coachLayoutRaf) {
    cancelAnimationFrame(coachLayoutRaf);
    coachLayoutRaf = 0;
  }
  if (coachViewportTimer) {
    clearTimeout(coachViewportTimer);
    coachViewportTimer = 0;
  }
  if (coachHideTimer) {
    clearTimeout(coachHideTimer);
    coachHideTimer = 0;
  }
  clearCoachPulse();
  const el = $("coach");
  if (!el || el.classList.contains("hidden")) {
    if (el) el.classList.remove("is-on", "is-out");
    unlockCoachScroll();
    return;
  }
  el.classList.add("is-out");
  if (reducedMotion()) {
    el.classList.add("hidden");
    el.classList.remove("is-on", "is-out");
    unlockCoachScroll();
    return;
  }
  coachHideTimer = setTimeout(() => {
    coachHideTimer = 0;
    el.classList.add("hidden");
    el.classList.remove("is-on", "is-out");
    unlockCoachScroll();
  }, 220);
}

function playCoachEnter() {
  const el = $("coach");
  const card = $("coachCard");
  if (!el || !card) return;
  el.classList.remove("is-out");
  if (reducedMotion()) {
    el.classList.add("is-on");
    return;
  }
  el.classList.remove("is-on");
  card.classList.remove("coach-step-in");
  void el.offsetWidth;
  el.classList.add("is-on");
}

function playCoachStepIn() {
  const card = $("coachCard");
  if (!card || reducedMotion()) return;
  card.classList.remove("coach-step-in");
  void card.offsetWidth;
  card.classList.add("coach-step-in");
}

function finishCoach(acknowledge) {
  const step = coachList[coachIndex];
  const wizTip = Boolean(step && step.wiz);
  if (wizTip) {
    markWizCoachStep(wiz.step);
    if (wiz.step >= 4) markOnboardDone();
  }
  hideCoach();
  if (wizTip) return;
  if (acknowledge || !hasRequiredCoach(window.__me)) markCoachDone();
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
    if (me.trial_available && coachElReady("trialHomeBtn") && offerSkipped()) {
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
  next.textContent = last ? "Понятно" : "Далее";
  $("coachSkip").classList.toggle("hidden", Boolean(step.required));
  $("coach").classList.toggle("is-required", Boolean(step.required));
  const catchEl = $("coachCatch");
  if (catchEl) catchEl.style.pointerEvents = step.required ? "none" : "auto";
}

function markWizCoachStep(step) {
  try {
    const seen = JSON.parse(localStorage.getItem(WIZ_COACH_KEY) || "{}");
    seen[String(step)] = 1;
    localStorage.setItem(WIZ_COACH_KEY, JSON.stringify(seen));
  } catch (_e) {}
}

function wizCoachSeen(step) {
  try {
    const seen = JSON.parse(localStorage.getItem(WIZ_COACH_KEY) || "{}");
    return Boolean(seen[String(step)]);
  } catch (_e) {
    return false;
  }
}

function buildWizCoachSteps() {
  if (screen !== "wizard" || onboardDone() || wizCoachSeen("done") || wizCoachSeen(wiz.step)) return [];
  if (wiz.step === 1 && $("wizPlatGrid")) {
    return [
      {
        id: "wizPlatGrid",
        wiz: true,
        required: true,
        title: "Выберите устройство",
        text: "Телефон, компьютер или телевизор. От выбора зависят приложение и подсказки.",
      },
    ];
  }
  if (wiz.step === 2) {
    const id = $("wizStoreBtn") ? "wizStoreBtn" : $("wizAppList") ? "wizAppList" : "";
    if (!id) return [];
    return [
      {
        id,
        wiz: true,
        required: true,
        title: "Поставьте приложение",
        text: "Скачайте клиент из магазина, если его ещё нет. Когда будет установлено, нажмите Продолжить внизу.",
      },
    ];
  }
  if (wiz.step === 3 && $("wizNameBox")) {
    return [
      {
        id: "wizNameBox",
        wiz: true,
        required: true,
        title: "Назовите и создайте",
        text: "Имя только для списка в кабинете. Кнопка «Создать» спишет сутки с баланса и выдаст ссылку.",
      },
    ];
  }
  if (wiz.step === 4 && $("wizOpenTile")) {
    return [
      {
        id: "wizOpenTile",
        wiz: true,
        required: true,
        title: "Откройте в приложении",
        text: "Нажмите «Открыть» или вставьте ссылку вручную. После этого VPN заработает.",
      },
    ];
  }
  return [];
}

let wizCoachTimer = 0;

function queueWizCoach() {
  if (wiz.fromOffer) return;
  if (wizCoachTimer) clearTimeout(wizCoachTimer);
  wizCoachTimer = setTimeout(() => {
    wizCoachTimer = 0;
    startWizCoach();
  }, reducedMotion() ? 40 : 380);
}

function startWizCoach() {
  if (screen !== "wizard") return;
  if ($("app").classList.contains("hidden")) return;
  const steps = buildWizCoachSteps();
  if (!steps.length) {
    if (coachVisible && coachList[coachIndex] && coachList[coachIndex].wiz) hideCoach();
    return;
  }
  if (coachVisible && coachList[coachIndex] && coachList[coachIndex].id === steps[0].id) {
    requestCoachLayout();
    return;
  }
  coachList = steps;
  coachIndex = 0;
  coachVisible = true;
  if (coachHideTimer) {
    clearTimeout(coachHideTimer);
    coachHideTimer = 0;
  }
  $("coach").classList.remove("hidden");
  applyCoachCopy();
  pinCoachCard();
  playCoachEnter();
  placeCoach();
}

function coachCardBottom() {
  const bar = $("appMainBar");
  const mainOn = bar && !bar.classList.contains("hidden");
  const pad = screen === "wizard" && mainOn ? 88 : 28;
  return `calc(${pad}px + var(--tg-safe-area-inset-bottom, 0px))`;
}

function pinCoachCard() {
  const card = $("coachCard");
  const hole = $("coachHole");
  hole.classList.add("is-off");
  card.style.top = "auto";
  card.style.bottom = coachCardBottom();
}

function coachTargetVisible(el) {
  const r = el.getBoundingClientRect();
  const top = 8;
  const bottom = window.innerHeight - 8;
  return r.width >= 24 && r.height >= 20 && r.top >= top && r.bottom <= bottom;
}

function requestCoachLayout() {
  if (!coachVisible) return;
  if (coachLayoutRaf) cancelAnimationFrame(coachLayoutRaf);
  coachLayoutRaf = requestAnimationFrame(() => {
    coachLayoutRaf = 0;
    layoutCoach();
  });
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
  card.style.top = "auto";
  card.style.bottom = coachCardBottom();
  if (!target || target.classList.contains("hidden")) {
    hole.classList.add("is-off");
    return;
  }
  const r = target.getBoundingClientRect();
  if (r.width < 24 || r.height < 20 || r.bottom < 8 || r.top > window.innerHeight - 8) {
    hole.classList.add("is-off");
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
  if (!target.classList.contains("coach-pulse")) {
    clearCoachPulse();
    target.classList.add("coach-pulse");
  }
}

function placeCoach() {
  const step = coachList[coachIndex];
  if (!step) {
    hideCoach();
    return;
  }
  applyCoachCopy();
  const card = $("coachCard");
  if (card) {
    card.style.top = "auto";
    card.style.bottom = coachCardBottom();
  }
  const target = $(step.id);
  if (target && !target.classList.contains("hidden") && !coachTargetVisible(target)) {
    try {
      target.scrollIntoView({ block: "nearest", behavior: "auto" });
    } catch (_e) {}
  }
  if (coachPlaceTimer) clearTimeout(coachPlaceTimer);
  coachPlaceTimer = setTimeout(() => {
    coachPlaceTimer = 0;
    layoutCoach();
  }, 0);
}

function coachCanRun() {
  if (screen !== "home" && screen !== "wizard") return false;
  if ($("app").classList.contains("hidden")) return false;
  if (!$("intro").classList.contains("hidden")) return false;
  if (!$("fail").classList.contains("hidden")) return false;
  if (!$("maint").classList.contains("hidden")) return false;
  return true;
}

function scheduleCoach() {
  coachStartTimers.forEach((id) => clearTimeout(id));
  coachStartTimers = [];
  const wait = reducedMotion() ? 0 : 520;
  coachStartTimers.push(setTimeout(() => maybeStartCoach(false), wait));
}

function maybeStartCoach(force) {
  if (screen === "wizard" || screen === "offer") return;
  if (!coachCanRun()) return;
  if (!force && coachDone()) return;
  if (coachVisible && !force) {
    requestCoachLayout();
    return;
  }
  coachList = buildCoachSteps(window.__me);
  if (!coachList.length) return;
  coachIndex = 0;
  coachVisible = true;
  if (coachHideTimer) {
    clearTimeout(coachHideTimer);
    coachHideTimer = 0;
  }
  lockCoachScroll();
  $("coach").classList.remove("hidden");
  applyCoachCopy();
  pinCoachCard();
  playCoachEnter();
  placeCoach();
}

function coachAdvance() {
  haptic();
  const step = coachList[coachIndex];
  if (step && (step.action === "wizard" || step.action === "topup")) {
    finishCoach(true);
    return;
  }
  if (coachIndex >= coachList.length - 1) {
    finishCoach(true);
    return;
  }
  coachIndex += 1;
  placeCoach();
  playCoachStepIn();
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

function monthTopupRub(me) {
  const n = Math.max(1, Number(me.vpn_day_price_rub) || 1) * 30;
  const min = Number(me.topup_min) || 1;
  const max = Number(me.topup_max) || n;
  return Math.min(max, Math.max(min, n));
}

function firstTopup(me) {
  return Boolean(me && me.balance_enabled && !me.has_paid_topup);
}

function monthTopupPlan(me) {
  const n = monthTopupRub(me);
  return {
    code: "b" + n,
    title: n + " рублей",
    topup_rub: n,
    rub: n,
  };
}

function currentTopupPlan(me) {
  if (topupMode === "first") return monthTopupPlan(me);
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
  if (topupMode === "first") {
    topupCode = monthTopupPlan(me).code;
    return;
  }
  const plans = me.plans || [];
  if (plans.some((p) => p.code === topupCode)) return;
  const month = monthTopupRub(me);
  const hit = plans.find((p) => planRub(p) === month) || plans.find((p) => planRub(p) === 100);
  topupCode = (hit || plans[0] || {}).code || "";
}

function applyTopupMode() {
  const first = topupMode === "first";
  const custom = topupMode === "custom";
  const firstEl = $("topupFirst");
  if (firstEl) firstEl.classList.toggle("hidden", !first);
  $("tabFast").classList.toggle("on", !custom);
  $("tabCustom").classList.toggle("on", custom);
  $("fastPanel").classList.toggle("hidden", custom || first);
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
  let label;
  if (topupMode === "first") {
    label = `Месяц за ${amount} ₽`;
  } else if (me.balance_enabled) {
    label = `Пополнить на ${amount} ₽`;
  } else {
    label = `Оплатить · ${plan.title}`;
  }
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
      markWizCoachStep(wiz.step);
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
    return;
  }
  if (screen === "support") {
    stopSupportPoll();
    openHome();
    return;
  }
  if (screen === "faq") {
    if (faqFrom === "support") openSupport();
    else openHome();
    return;
  }
  if (screen === "billing") {
    openHome();
    return;
  }
  if (screen === "referrals") {
    openHome();
    return;
  }
  if (screen === "offer") {
    const me = window.__me;
    if (me && me.balance_enabled && !(me.devices || []).length) {
      startWizard({ fromOffer: true });
      return;
    }
    openHome();
  }
}

function openHome() {
  const fromStack = screen === "wizard" || screen === "device" || screen === "topup" || screen === "support" || screen === "faq" || screen === "billing" || screen === "referrals" || screen === "offer";
  stopSupportPoll();
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
  topupMode = firstTopup(me) ? "first" : "fast";
  switchView("view-topup", "push");
  try {
    tg.BackButton.show();
  } catch (_e) {}
  syncWebBack();
  renderTopup(me);
}

const SUPPORT_STATUS = { open: "Ждём ответ", pending: "Есть ответ", closed: "Закрыт" };
const SUPPORT_MAX_FILES = 5;
let supportPoll = 0;
let supportPending = [];

function stopSupportPoll() {
  if (supportPoll) {
    clearInterval(supportPoll);
    supportPoll = 0;
  }
}

function isTicketImage(att) {
  return (att && att.kind === "photo") || String((att && att.mime) || "").startsWith("image/");
}

function paintTicketAttachments(wrap, atts) {
  if (!wrap || !atts || !atts.length) return;
  const box = document.createElement("div");
  box.className = "support-atts";
  atts.forEach((a) => {
    if (isTicketImage(a) && a.url) {
      const link = document.createElement("a");
      link.href = a.url;
      link.target = "_blank";
      link.rel = "noopener";
      const img = document.createElement("img");
      img.className = "support-att-img";
      img.alt = a.original_name || "Фото";
      img.src = a.url;
      link.appendChild(img);
      box.appendChild(link);
    } else {
      const link = document.createElement("a");
      link.className = "support-att-file";
      link.href = a.url || "#";
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = a.original_name || "Файл";
      box.appendChild(link);
    }
  });
  wrap.appendChild(box);
}

function paintSupportPending() {
  const box = $("supportAttachList");
  if (!box) return;
  box.innerHTML = "";
  supportPending.forEach((file, i) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "support-attach-chip";
    chip.textContent = file.name || "Файл";
    chip.onclick = () => {
      supportPending.splice(i, 1);
      paintSupportPending();
    };
    box.appendChild(chip);
  });
}

function addSupportFiles(list) {
  const incoming = Array.from(list || []);
  incoming.forEach((file) => {
    if (supportPending.length >= SUPPORT_MAX_FILES) return;
    supportPending.push(file);
  });
  paintSupportPending();
}

function paintSupportThread(current) {
  const box = $("supportThread");
  const status = $("supportStatus");
  if (!box) return;
  box.innerHTML = "";
  const messages = (current && current.messages) || [];
  if (status) {
    status.textContent = current
      ? `Тикет #${current.id} · ${SUPPORT_STATUS[current.status] || current.status}`
      : "Напишите, что случилось. Можно прикрепить скриншот. Ответ придёт сюда и в чат бота.";
  }
  if (!messages.length) {
    const empty = document.createElement("div");
    empty.className = "support-empty";
    empty.textContent = current && current.status === "closed"
      ? "Тикет закрыт. Новое сообщение откроет следующий."
      : "Пока пусто. Опишите проблему — откроем тикет.";
    box.appendChild(empty);
    return;
  }
  messages.forEach((m) => {
    const wrap = document.createElement("div");
    wrap.className = "support-bubble " + (m.author === "admin" ? "admin" : "user");
    const meta = document.createElement("div");
    meta.className = "support-bubble-meta";
    const when = m.created_at ? new Date(m.created_at) : null;
    const time = when && !Number.isNaN(when.getTime()) ? when.toLocaleString("ru-RU") : "";
    meta.textContent = (m.author === "admin" ? "Поддержка" : "Вы") + (time ? " · " + time : "");
    wrap.appendChild(meta);
    if (m.body) {
      const body = document.createElement("div");
      body.className = "support-bubble-body";
      body.textContent = m.body;
      wrap.appendChild(body);
    }
    paintTicketAttachments(wrap, m.attachments);
    box.appendChild(wrap);
  });
  box.scrollTop = box.scrollHeight;
}

async function loadSupport(silent) {
  try {
    const data = await api("/api/tickets");
    paintSupportThread(data.current);
  } catch (e) {
    if (!silent) showErr(e);
  }
}

function openSupport() {
  screen = "support";
  switchView("view-support", "push");
  setMain("");
  try {
    tg.BackButton.show();
  } catch (_e) {}
  syncWebBack();
  loadSupport();
  stopSupportPoll();
  supportPoll = setInterval(() => {
    if (screen === "support") loadSupport(true);
  }, 8000);
}

function paintFaq(me) {
  const box = $("faqList");
  if (!box) return;
  box.innerHTML = "";
  const items = (me && me.faq) || [];
  items.forEach((item, i) => {
    const wrap = document.createElement("div");
    wrap.className = "faq-item" + (i === 0 ? " on" : "");
    const btn = document.createElement("button");
    btn.type = "button";
    const title = document.createElement("span");
    title.textContent = item.q || "";
    const arrow = document.createElement("span");
    arrow.className = "arrow";
    arrow.textContent = "›";
    btn.appendChild(title);
    btn.appendChild(arrow);
    const ans = document.createElement("div");
    ans.className = "faq-a";
    ans.textContent = item.a || "";
    btn.onclick = () => {
      haptic();
      const open = wrap.classList.contains("on");
      box.querySelectorAll(".faq-item").forEach((el) => el.classList.remove("on"));
      if (!open) wrap.classList.add("on");
    };
    wrap.appendChild(btn);
    wrap.appendChild(ans);
    box.appendChild(wrap);
  });
}

function openFaq(from) {
  const me = window.__me;
  if (!me) return;
  faqFrom = from === "support" ? "support" : "home";
  stopSupportPoll();
  screen = "faq";
  switchView("view-faq", "push");
  setMain("");
  try {
    tg.BackButton.show();
  } catch (_e) {}
  syncWebBack();
  paintFaq(me);
}

const BILL_KIND = {
  charge: "Списание",
  pause: "Пауза тарификации",
  disable: "Отключение",
  revive: "Включение",
  trial: "Бесплатный период",
  admin_balance: "Баланс",
  admin_grant: "Начисление",
  trust: "Обещанный платёж",
  trust_collect: "Возврат обещанного",
  device_delete: "Удаление устройства",
  referral: "Бонус за друга",
  referral_payout: "Вывод рефералки",
  referral_revoke: "Возврат за друга",
  story: "Награда за историю",
};

function billKindLabel(kind) {
  return BILL_KIND[kind] || "Операция";
}

function billAmountText(n) {
  const v = Number(n);
  if (!Number.isFinite(v) || v === 0) return "";
  return (v > 0 ? "+" : "") + v + " ₽";
}

function billDayKey(dt) {
  const d = new Date(dt);
  if (Number.isNaN(d.getTime())) return "";
  return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
}

function billDayLabel(dt) {
  const d = new Date(dt);
  if (Number.isNaN(d.getTime())) return "";
  const start = (x) => Date.UTC(x.getFullYear(), x.getMonth(), x.getDate());
  const now = new Date();
  const diff = Math.round((start(now) - start(d)) / 86400000);
  if (diff === 0) return "Сегодня";
  if (diff === 1) return "Вчера";
  return d.toLocaleDateString("ru-RU", { day: "numeric", month: "long" });
}

function billTone(kind, amount) {
  const v = Number(amount);
  if (Number.isFinite(v) && v < 0) return "neg";
  if (Number.isFinite(v) && v > 0) return "pos";
  if (kind === "disable" || kind === "device_delete" || kind === "referral_payout") return "neg";
  if (kind === "revive" || kind === "trial" || kind === "trust" || kind === "referral" || kind === "story") return "pos";
  return "mute";
}

function billMarkSvg(tone) {
  if (tone === "pos") {
    return '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>';
  }
  if (tone === "neg") {
    return '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M5 12h14" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>';
  }
  return '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M8 7v10M16 7v10" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>';
}

function billOpsWord(n) {
  const abs = Math.abs(n);
  const mod10 = abs % 10;
  const mod100 = abs % 100;
  if (mod10 === 1 && mod100 !== 11) return "операция";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return "операции";
  return "операций";
}

function paintBilling(data) {
  const box = $("billingList");
  const summary = $("billingSummary");
  if (!box) return;
  box.innerHTML = "";
  const items = (data && data.items) || [];
  const charged = Number(data && data.charged_rub) || 0;
  if (summary) {
    summary.classList.remove("hidden");
    summary.innerHTML = "";
    const kicker = document.createElement("div");
    kicker.className = "bill-summary-kicker";
    kicker.textContent = "Списано за 7 дней";
    const value = document.createElement("div");
    value.className = "bill-summary-value";
    value.textContent = charged + " ₽";
    const note = document.createElement("div");
    note.className = "bill-summary-note";
    note.textContent = items.length
      ? items.length + " " + billOpsWord(items.length) + " по балансу и устройствам"
      : "Пока не было списаний и начислений";
    summary.appendChild(kicker);
    summary.appendChild(value);
    summary.appendChild(note);
  }
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "section bill-empty";
    empty.innerHTML = '<div class="t">Пусто</div><div class="d">Когда спишется сутки VPN или придёт пополнение, запись появится здесь.</div>';
    box.appendChild(empty);
    return;
  }
  const groups = [];
  items.forEach((e) => {
    const key = billDayKey(e.created_at) || "other";
    let group = groups[groups.length - 1];
    if (!group || group.key !== key) {
      group = { key, label: billDayLabel(e.created_at) || "Ранее", items: [] };
      groups.push(group);
    }
    group.items.push(e);
  });
  groups.forEach((group) => {
    const wrap = document.createElement("div");
    wrap.className = "section bill-group";
    const head = document.createElement("div");
    head.className = "section-head";
    const h = document.createElement("span");
    h.className = "h";
    h.textContent = group.label;
    head.appendChild(h);
    wrap.appendChild(head);
    group.items.forEach((e) => {
      const tone = billTone(e.kind, e.amount);
      const row = document.createElement("div");
      row.className = "bill-item";
      const mark = document.createElement("div");
      mark.className = "bill-mark " + tone;
      mark.innerHTML = billMarkSvg(tone);
      row.appendChild(mark);
      const main = document.createElement("div");
      main.className = "bill-item-main";
      const title = document.createElement("div");
      title.className = "bill-item-title";
      title.textContent = billKindLabel(e.kind);
      main.appendChild(title);
      const subBits = [e.device_title, e.note].filter(Boolean);
      if (e.balance_after != null) subBits.push("остаток " + e.balance_after + " ₽");
      if (subBits.length) {
        const sub = document.createElement("div");
        sub.className = "bill-item-sub";
        sub.textContent = subBits.join(" · ");
        main.appendChild(sub);
      }
      row.appendChild(main);
      const side = document.createElement("div");
      side.className = "bill-item-side";
      const amt = billAmountText(e.amount);
      if (amt) {
        const money = document.createElement("div");
        money.className = "bill-item-amt " + tone;
        money.textContent = amt;
        side.appendChild(money);
      }
      const when = e.created_at ? new Date(e.created_at) : null;
      if (when && !Number.isNaN(when.getTime())) {
        const time = document.createElement("div");
        time.className = "bill-item-time";
        time.textContent = when.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
        side.appendChild(time);
      }
      row.appendChild(side);
      wrap.appendChild(row);
    });
    box.appendChild(wrap);
  });
}

async function loadBilling() {
  const box = $("billingList");
  const summary = $("billingSummary");
  if (summary) summary.classList.add("hidden");
  if (box) {
    box.innerHTML = "";
    const wait = document.createElement("p");
    wait.className = "support-empty";
    wait.textContent = "Загружаю...";
    box.appendChild(wait);
  }
  try {
    paintBilling(await api("/api/billing"));
  } catch (e) {
    if (summary) summary.classList.add("hidden");
    if (box) {
      box.innerHTML = "";
      const err = document.createElement("p");
      err.className = "support-empty";
      err.textContent = e.message || "Не удалось загрузить историю";
      box.appendChild(err);
    } else {
      showErr(e);
    }
  }
}

function openBilling() {
  screen = "billing";
  switchView("view-billing", "push");
  setMain("");
  try {
    tg.BackButton.show();
  } catch (_e) {}
  syncWebBack();
  loadBilling();
}

function paintReferrals(me) {
  if (!me) return;
  const invited = Number(me.invited_count) || 0;
  const earned = Number(me.referral_earned) || 0;
  const rewarded = Number(me.referral_rewarded_count) || 0;
  const countEl = $("refCountValue");
  const countLabel = $("refCountLabel");
  const earnEl = $("refEarnValue");
  const earnLabel = $("refEarnLabel");
  if (countEl) countEl.textContent = String(invited);
  if (countLabel) countLabel.textContent = friendsWord(invited);
  if (me.balance_enabled) {
    if (earnEl) earnEl.textContent = earned + " ₽";
    if (earnLabel) earnLabel.textContent = "получено";
  } else {
    const days = rewarded * (Number(me.referral_reward_days) || 0);
    if (earnEl) earnEl.textContent = String(days);
    if (earnLabel) earnLabel.textContent = daysWord(days);
  }
  const note = $("refStatsNote");
  if (note) {
    if (me.balance_enabled && me.referral_payout_enabled && invited > rewarded) {
      note.textContent = earned > 0
        ? "Начислено за " + rewarded + " " + friendsWord(rewarded) + " с оплатой. Остальные ещё не оплатили."
        : "Деньги придут после первой оплаты друга. Пока бонус не начислен.";
    } else if (invited > 0 && rewarded === 0 && earned === 0) {
      note.textContent = me.balance_enabled
        ? "Друзья пришли, но бонус ещё не начислен."
        : "Друзья пришли, начисление дней ещё впереди.";
    } else {
      note.textContent = "";
    }
  }
  const when = $("refFaqWhen");
  const how = $("refFaqHow");
  const payWrap = $("refFaqPayoutWrap");
  const pay = $("refFaqPayout");
  if (me.balance_enabled) {
    const rub = me.referral_reward_rub || 50;
    if (me.referral_payout_enabled) {
      if (when) when.textContent = "Начисление после первой оплаты друга по вашей ссылке. Пока друг только пришёл и не оплатил, денег не будет.";
      if (how) how.textContent = `Вам ${rub} ₽ за каждого, кто оплатил. Другу бонус за переход не начисляется.`;
      if (pay) pay.textContent = `Вывести можно от ${me.referral_payout_min || 2000} ₽ реферальных, которые ещё на балансе. Заявка уходит администратору.`;
      if (payWrap) payWrap.classList.remove("hidden");
    } else {
      if (when) when.textContent = "Начисление, когда друг нажмёт «Попробовать бесплатно» по вашей ссылке.";
      if (how) how.textContent = `Вам и другу по ${rub} ₽ на баланс.`;
      if (payWrap) payWrap.classList.add("hidden");
    }
  } else {
    const mine = daysLabel(me.referral_reward_days || 7);
    const friend = daysLabel(me.referral_invitee_days || 5);
    if (me.referral_payout_enabled) {
      if (when) when.textContent = "Дни придут после первой оплаты друга по вашей ссылке.";
      if (how) how.textContent = `Вам ${mine}. Другу при бесплатном периоде +${friend}.`;
    } else {
      if (when) when.textContent = "Дни придут, когда друг нажмёт «Попробовать бесплатно» по вашей ссылке.";
      if (how) how.textContent = `Вам ${mine}, другу +${friend} к бесплатному периоду.`;
    }
    if (payWrap) payWrap.classList.add("hidden");
  }
  paintPayout(me);
}

function openReferrals() {
  const me = window.__me;
  if (!me) return;
  screen = "referrals";
  switchView("view-referrals", "push");
  setMain("");
  try {
    tg.BackButton.show();
  } catch (_e) {}
  syncWebBack();
  paintReferrals(me);
}

async function sendSupport() {
  const el = $("supportText");
  const text = (el && el.value || "").trim();
  if (!text && !supportPending.length) {
    tg.showAlert("Напишите сообщение или прикрепите файл");
    return;
  }
  const btn = $("supportSend");
  if (btn) btn.disabled = true;
  try {
    const fd = new FormData();
    fd.append("text", text);
    supportPending.forEach((file) => fd.append("files", file, file.name));
    const data = await api("/api/tickets", {
      method: "POST",
      body: fd,
    });
    if (el) el.value = "";
    supportPending = [];
    paintSupportPending();
    const input = $("supportFiles");
    if (input) input.value = "";
    paintSupportThread(data.current);
  } catch (e) {
    showErr(e);
  } finally {
    if (btn) btn.disabled = false;
  }
}

function monthPriceLabel(me) {
  if (me.balance_enabled) {
    const n = Math.max(1, Number(me.vpn_day_price_rub) || 1) * 30;
    return `${n} ₽ месяц`;
  }
  const plan = (me.plans || []).find((p) => p.code === "1m") || (me.plans || [])[0];
  if (!plan) return "—";
  const n = Number(plan.topup_rub || plan.rub);
  if (!Number.isFinite(n) || n <= 0) return "—";
  return `${Math.round(n)} ₽ месяц`;
}

function paintOffer(me) {
  if (!me) return;
  const days = Number((me.trial_notice && me.trial_notice.days) || me.trial_days) || 3;
  $("offerDays").textContent = String(days);
  $("offerPrice").textContent = monthPriceLabel(me);
  const gb = Number(me.traffic_limit_gb) || 0;
  $("offerTraffic").textContent = gb > 0 ? `${gb} ГБ` : "Безлимит";
  const note = $("offerNote");
  if (gb > 0) {
    note.textContent = `*В пробный период доступно ${gb} ГБ`;
    note.classList.remove("hidden");
  } else {
    note.textContent = "";
    note.classList.add("hidden");
  }
}

function openOffer() {
  const me = window.__me;
  if (!me) return;
  hideCoach();
  screen = "offer";
  switchView("view-offer", "push");
  setMain("");
  paintOffer(me);
  try {
    tg.BackButton.show();
  } catch (_e) {}
  syncWebBack();
}

async function startOfferTry() {
  const me = window.__me;
  if (!me) return;
  haptic();
  const btn = $("offerTry");
  if (btn) btn.disabled = true;
  firstRunBusy = true;
  try {
    if (me.trial_available) {
      await api("/api/trial", { method: "POST", body: "{}" });
      await load();
    }
    const next = window.__me || me;
    if (next.balance_enabled) {
      startWizard({ fromOffer: true });
      return;
    }
    markOnboardDone();
    openHome();
  } catch (e) {
    showErr(e);
  } finally {
    firstRunBusy = false;
    if (btn) btn.disabled = false;
  }
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
  const first = firstTopup(me) && topupMode !== "custom";
  if (first) topupMode = "first";
  ensureTopupCode(me);
  const plans = me.plans || [];
  const canCustom = Boolean(me.balance_enabled);
  $("topupTabs").classList.toggle("hidden", !canCustom || topupMode === "first");
  if (!canCustom && topupMode !== "first") topupMode = "fast";
  applyTopupMode();
  const titleEl = document.querySelector("#view-topup .wiz-title");
  if (titleEl) {
    titleEl.textContent = topupMode === "first" ? "Месяц, чтобы не думать" : "Сколько зальём?";
  }
  $("topupHint").textContent = me.balance_enabled
    ? topupMode === "first"
      ? `Один платёж на ~30 суток одного устройства. С каждого устройства списывается ${me.vpn_day_price_rub} ₽ в сутки.`
      : `С каждого устройства списывается ${me.vpn_day_price_rub} ₽ в сутки. Карточки показывают, на сколько дней хватит суммы при одном устройстве.`
    : "Выберите срок подписки.";
  if (topupMode === "first") {
    const amount = monthTopupRub(me);
    const btn = $("topupMonthBtn");
    if (btn) {
      btn.innerHTML = "";
      const amt = document.createElement("div");
      amt.className = "pay-amount";
      amt.textContent = `${amount} ₽`;
      const days = document.createElement("div");
      days.className = "pay-days";
      days.textContent = "месяц · одно устройство";
      btn.appendChild(amt);
      btn.appendChild(days);
    }
    updateTopupCta(me);
    return;
  }
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
      const month = monthTopupRub(me);
      const hit = firstTopup(me)
        ? month
        : (amounts.includes(100) ? 100 : (planRub(currentTopupPlan(me)) || min));
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
  const toOffer = wiz.fromOffer && !wiz.url && shouldShowOffer(window.__me);
  if (wiz.url) markOnboardDone();
  hideQr();
  wiz.step = 1;
  wiz.url = "";
  wiz.fromOffer = false;
  if (toOffer) {
    openOffer();
    return;
  }
  openHome();
}

function startWizard(opts) {
  const me = window.__me;
  if (!me || !me.balance_enabled) return;
  const cap = Number(me.max_devices) || 0;
  const n = (me.devices || []).length;
  if (cap > 0 && n >= cap) {
    tg.showAlert("Можно подключить не больше " + cap + " устройств");
    return;
  }
  haptic();
  hideCoach();
  wiz.step = 1;
  wiz.platform = "ios";
  const first = clientsFor("ios")[0];
  wiz.client = first ? first.id : "";
  wiz.title = "";
  wiz.url = "";
  wiz.fromOffer = Boolean(opts && opts.fromOffer);
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
    $("wizTitle").textContent = "Выбор устройства";
    lead.textContent = "";
    const list = document.createElement("div");
    list.id = "wizPlatGrid";
    list.className = "wiz-radio";
    PLATFORMS.forEach((p) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "wiz-radio-row" + (wiz.platform === p.id ? " on" : "");
      const name = document.createElement("span");
      name.textContent = p.hint || p.title;
      const mark = document.createElement("span");
      mark.className = "radio" + (wiz.platform === p.id ? " on" : "");
      b.appendChild(name);
      b.appendChild(mark);
      b.onclick = () => {
        haptic();
        wiz.platform = p.id;
        const first = clientsFor(p.id)[0];
        wiz.client = first ? first.id : "";
        wiz.title = "";
        renderWizard();
      };
      list.appendChild(b);
    });
    body.appendChild(list);
    replayAnim(body, "wiz-swap");
    setMain("Продолжить", () => {
      haptic();
      markWizCoachStep(1);
      wiz.step = 2;
      renderWizard();
    });
    queueWizCoach();
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
      queueWizCoach();
      return;
    }
    if (!list.some((c) => c.id === wiz.client)) wiz.client = list[0].id;
    const listWrap = document.createElement("div");
    listWrap.id = "wizAppList";
    list.forEach((c, i) => {
      const row = document.createElement("button");
      row.type = "button";
      row.className = "wiz-app" + (wiz.client === c.id ? " on" : "");
      const logo = document.createElement("div");
      fillAppLogo(logo, c, i !== 0);
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
      listWrap.appendChild(row);
    });
    body.appendChild(listWrap);
    const storeBtn = listWrap.querySelector(".wiz-app-store");
    if (storeBtn) storeBtn.id = "wizStoreBtn";
    $("wizHint").textContent =
      "Приложение можно сменить в любой момент. Уже установлено? Нажмите «Продолжить».";
    replayAnim(body, "wiz-swap");
    setMain("Продолжить с " + clientLabel(wiz.client), () => {
      haptic();
      markWizCoachStep(2);
      wiz.step = 3;
      renderWizard();
    });
    queueWizCoach();
    return;
  }

  if (wiz.step === 3) {
    $("wizStep").textContent = "Шаг 3 из 3";
    $("wizTitle").textContent = "Как назовём устройство?";
    lead.textContent = "Пригодится, если подключите несколько гаджетов — так проще не запутаться.";
    const chips = nameChips(wiz.platform);
    if (!(wiz.title || "").trim()) wiz.title = chips[0] || defaultTitle();
    const box = document.createElement("div");
    box.id = "wizNameBox";
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
        markWizCoachStep(3);
        wiz.title = title;
        wiz.url = created.subscription_url || "";
        wiz.step = 4;
        if (created.first_device) armThanksOnClose();
        await load();
        renderWizard();
      } catch (e) {
        showErr(e);
      } finally {
        setMainBusy(false);
      }
    });
    queueWizCoach();
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
  openTile.id = "wizOpenTile";
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
  queueWizCoach();
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
    $("storyNote").textContent = "Администратор подтвердит или отклонит награду.";
    let ticks = 0;
    const tick = () => {
      const cur = window.__me || me;
      if (!cur.story_pending || cur.story_rewarded) {
        stopStoryTimer();
        return;
      }
      const left = storyRemain(cur);
      timer.textContent = left > 0 ? fmtStoryRemain(left) : "ещё на проверке";
      timer.classList.remove("hidden");
      ticks += 1;
      if (ticks % 15 === 0) load();
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
    $("storyNote").textContent = "Откроется редактор истории Telegram. Награда один раз после подтверждения администратором.";
    $("storyBtn").textContent = "Выложить";
  }
}

function paintPayout(me) {
  const card = $("refPayoutCard");
  const form = $("refPayoutForm");
  const btn = $("refPayoutBtn");
  if (!card) return;
  if (!me.balance_enabled || !me.referral_payout_enabled) {
    card.classList.add("hidden");
    return;
  }
  card.classList.remove("hidden");
  const min = me.referral_payout_min || 2000;
  const avail = me.referral_available || 0;
  const pending = me.referral_pending || 0;
  const earned = me.referral_earned || 0;
  $("refPayoutTitle").textContent = "Вывод реферальных";
  if (pending > 0) {
    $("refPayoutNote").textContent = `Заявка на ${pending} ₽ на проверке. Пока ждите решения.`;
    form.classList.add("hidden");
    return;
  }
  $("refPayoutNote").textContent =
    `Накоплено ${earned} ₽, к выводу сейчас ${avail} ₽. Минимум ${min} ₽. ` +
    "Выводится только реферальное, которое ещё на балансе.";
  if (me.referral_payout_can) {
    form.classList.remove("hidden");
    if (btn) btn.textContent = `Вывести ${avail} ₽`;
  } else {
    form.classList.add("hidden");
  }
}

const TRIAL_NOTICE_KEY = "way_trial_notice_v1";

function trialNoticeDismissed(kind) {
  try {
    return localStorage.getItem(TRIAL_NOTICE_KEY) === String(kind || "");
  } catch (_e) {
    return false;
  }
}

function dismissTrialNotice(kind) {
  try {
    localStorage.setItem(TRIAL_NOTICE_KEY, String(kind || "1"));
  } catch (_e) {}
  const el = $("trialNotice");
  if (el) el.classList.add("hidden");
}

function paintTrialNotice(me) {
  const el = $("trialNotice");
  if (el) el.classList.add("hidden");
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
  paintTrialNotice(me);
  if (me.balance_enabled) {
    const invited = Number(me.invited_count) || 0;
    const earned = Number(me.referral_earned) || 0;
    $("inviteTitle").textContent = "Рефералы";
    $("inviteNote").textContent = invited + " " + friendsWord(invited) + " · " + earned + " ₽";
  } else {
    const invited = Number(me.invited_count) || 0;
    $("inviteTitle").textContent = "Рефералы";
    $("inviteNote").textContent = invited + " " + friendsWord(invited);
  }
  $("invite").textContent = me.invite_url;
  paintPayout(me);
  if (screen === "referrals") paintReferrals(me);
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
  const menuBilling = $("menuBilling");
  if (menuBilling) menuBilling.classList.toggle("hidden", !me.balance_enabled);
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
  const showTrust = Boolean(
    me.balance_enabled
    && t
    && t.enabled !== false
    && (t.open || t.available || ((Number(me.days_left) || 0) < 3 && me.has_paid_topup))
  );
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
  if (me.trial_available && offerSkipped()) {
    const trialHomeBtn = $("trialHomeBtn");
    trialHomeBtn.classList.remove("hidden");
    trialHomeBtn.textContent = me.balance_enabled
      ? `Попробовать бесплатно · ${rublesLabel(me.trial_rub)}`
      : `Попробовать бесплатно · ${daysLabel(me.trial_days)}`;
  } else {
    $("trialHomeBtn").classList.add("hidden");
  }
  renderConnect(me);
  renderDevices(me);
  window.__me = me;
  if (me.first_device_thanks_pending) armThanksOnClose();
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
  if (firstRunBusy) return;
  if (!$("intro").classList.contains("hidden")) return;
  const firstRun = !(me.devices || []).length;
  if (!firstRun && shouldShowIntro()) showIntro(me);
  else {
    showApp();
    maybeOpenFirstRun(me);
  }
  if (screen !== "offer" && screen !== "wizard") syncCoach(me);
}

function syncCoach(me) {
  if (screen !== "home") return;
  if ($("app").classList.contains("hidden")) return;
  if (coachDone()) {
    if (coachVisible && !(coachList[coachIndex] && coachList[coachIndex].wiz)) hideCoach();
    return;
  }
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
      const nextId = coachList[coachIndex] && coachList[coachIndex].id;
      if (nextId === oldId) {
        applyCoachCopy();
        return;
      }
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
  const me = window.__me;
  topupMode = firstTopup(me) ? "first" : "fast";
  if (me) renderTopup(me);
};

$("tabCustom").onclick = () => {
  haptic();
  topupMode = "custom";
  if (window.__me) renderTopup(window.__me);
  const inp = $("topupAmount");
  if (inp) setTimeout(() => inp.focus(), 50);
};

if ($("topupOtherBtn")) {
  $("topupOtherBtn").onclick = () => {
    haptic();
    topupMode = "custom";
    if (window.__me) renderTopup(window.__me);
    const inp = $("topupAmount");
    if (inp) setTimeout(() => inp.focus(), 50);
  };
}

if ($("topupMonthBtn")) {
  $("topupMonthBtn").onclick = () => {
    const me = window.__me;
    if (!me) return;
    haptic();
    const plan = monthTopupPlan(me);
    setMainBusy(true);
    payPlan(plan).catch(showErr).finally(() => setMainBusy(false));
  };
}

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

async function claimTrial() {
  haptic();
  try {
    await api("/api/trial", { method: "POST", body: "{}" });
    showToast("Тестовый баланс начислен");
    await load();
  } catch (e) {
    showErr(e);
  }
}

$("trialHomeBtn").onclick = () => claimTrial();

$("trialNoticeClose").onclick = (e) => {
  e.stopPropagation();
  haptic();
  const kind = window.__me && window.__me.trial_notice && window.__me.trial_notice.kind;
  dismissTrialNotice(kind);
  if (window.__me) paint(window.__me);
};

$("trialNoticeAct").onclick = () => {
  haptic();
  startWizard();
};

$("trustBtn").onclick = () => openTrust();
$("trustHelp").onclick = () => openTrust();
$("menuTrust").onclick = () => {
  closeMenu();
  openTrust();
};
if ($("supportLink")) {
  $("supportLink").onclick = () => {
    closeMenu();
    openSupport();
  };
}
if ($("menuBilling")) {
  $("menuBilling").onclick = () => {
    closeMenu();
    openBilling();
  };
}
if ($("menuReferrals")) {
  $("menuReferrals").onclick = () => {
    closeMenu();
    openReferrals();
  };
}
if ($("refHomeCard")) {
  $("refHomeCard").onclick = () => {
    haptic();
    openReferrals();
  };
}

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

function shareInvite() {
  const url = window.__me && window.__me.invite_url;
  if (!url) return;
  const me = window.__me;
  let text;
  if (me && me.balance_enabled) {
    const rub = me.referral_reward_rub || 50;
    text = encodeURIComponent(
      me.referral_payout_enabled
        ? `Подключайся по ссылке. После первой оплаты я получу ${rublesLabel(rub)} за приглашение.`
        : `Подключайся. Нажми «Попробовать бесплатно» по ссылке — получишь ${rublesLabel(rub)} на баланс, и я тоже.`
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

function copyInvite() {
  const url = window.__me && window.__me.invite_url;
  if (!url) return;
  const done = () => {
    if (typeof showToast === "function") showToast("Ссылка скопирована");
    else tg.showAlert("Ссылка скопирована");
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(url).then(done).catch(() => tg.showAlert("Ссылка: " + url));
  } else {
    tg.showAlert("Ссылка: " + url);
  }
}

$("shareBtn").onclick = (e) => {
  if (e) e.stopPropagation();
  haptic();
  shareInvite();
};

if ($("refCopyBtn")) {
  $("refCopyBtn").onclick = () => {
    haptic();
    copyInvite();
  };
}

$("invite").onclick = () => {
  haptic();
  copyInvite();
};

if ($("refPayoutBtn")) {
  $("refPayoutBtn").onclick = async () => {
    haptic();
    const details = ($("refPayoutDetails") && $("refPayoutDetails").value) || "";
    try {
      const r = await api("/api/referral-payout", {
        method: "POST",
        body: JSON.stringify({ details }),
      });
      if ($("refPayoutDetails")) $("refPayoutDetails").value = "";
      await load();
      tg.showAlert((r && r.message) ? r.message.replace(/<[^>]+>/g, "") : "Заявка отправлена");
    } catch (e) {
      showErr(e);
    }
  };
}

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
    localStorage.removeItem(WIZ_COACH_KEY);
    localStorage.removeItem(ONBOARD_KEY);
    localStorage.removeItem(OFFER_SKIP_KEY);
  } catch (_e) {}
  maybeStartCoach(true);
};
document.addEventListener("touchmove", onCoachScrollGuard, { passive: false });
document.addEventListener("wheel", onCoachScrollGuard, { passive: false });
window.addEventListener("resize", () => {
  if (!coachVisible) return;
  clearTimeout(coachViewportTimer);
  coachViewportTimer = setTimeout(() => {
    coachViewportTimer = 0;
    requestCoachLayout();
  }, 80);
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

$("supportBtn").onclick = () => {
  haptic();
  openSupport();
};
if ($("faqBtn")) {
  $("faqBtn").onclick = () => {
    haptic();
    openFaq("home");
  };
}
if ($("supportFaqBtn")) {
  $("supportFaqBtn").onclick = () => {
    haptic();
    openFaq("support");
  };
}
if ($("menuFaq")) {
  $("menuFaq").onclick = () => {
    closeMenu();
    haptic();
    openFaq("home");
  };
}
if ($("offerTry")) $("offerTry").onclick = () => startOfferTry();
if ($("supportSend")) $("supportSend").onclick = () => sendSupport();
if ($("supportAttach")) {
  $("supportAttach").onclick = () => {
    const input = $("supportFiles");
    if (input) input.click();
  };
}
if ($("supportFiles")) {
  $("supportFiles").onchange = (e) => {
    addSupportFiles(e.target.files);
    e.target.value = "";
  };
}

$("intro").onclick = finishIntro;
$("intro").onkeydown = (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    finishIntro();
  }
};

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
    applyViewport();
    requestMiniAppFullscreen();
    if (!coachVisible) return;
    clearTimeout(coachViewportTimer);
    coachViewportTimer = setTimeout(() => {
      coachViewportTimer = 0;
      requestCoachLayout();
    }, 80);
  });
  tg.onEvent("fullscreenChanged", () => {
    applyViewport();
    applyTheme();
  });
  tg.onEvent("safeAreaChanged", applyViewport);
  tg.onEvent("contentSafeAreaChanged", applyViewport);
  tg.onEvent("activated", () => {
    tg.expand();
    requestMiniAppFullscreen();
    applyViewport();
  });
}
let visTimer = 0;
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState !== "visible" || !window.__me) return;
  clearTimeout(visTimer);
  visTimer = setTimeout(() => load().catch(() => {}), 400);
});
window.addEventListener("pagehide", flushThanksOnClose);
window.addEventListener("beforeunload", flushThanksOnClose);

load().catch((err) => showFail(err.message || "Не удалось загрузить данные"));
