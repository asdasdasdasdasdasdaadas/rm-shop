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

function cssVar(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

function applyTheme() {
  const bg = cssVar("--bg-app", "#0d1611");
  try {
    tg.setHeaderColor(bg);
    tg.setBackgroundColor(bg);
    if (typeof tg.setBottomBarColor === "function") tg.setBottomBarColor(bg);
    if (tg.MainButton && tg.MainButton.hide) tg.MainButton.hide();
  } catch (_e) {}
}

const THEME_KEY = "way_theme_v1";
const APP_THEMES = ["green", "black", "pink", "purple", "orange", "yellow"];

function currentTheme() {
  const t = document.documentElement.getAttribute("data-theme") || "green";
  return APP_THEMES.indexOf(t) >= 0 ? t : "green";
}

function paintThemePicker() {
  const on = currentTheme();
  document.querySelectorAll(".theme-swatch").forEach((btn) => {
    btn.classList.toggle("is-on", btn.getAttribute("data-theme-id") === on);
  });
}

function setAppTheme(id) {
  const theme = APP_THEMES.indexOf(id) >= 0 ? id : "green";
  document.documentElement.setAttribute("data-theme", theme);
  try {
    localStorage.setItem(THEME_KEY, theme);
  } catch (_e) {}
  applyTheme();
  paintThemePicker();
}

function initAppTheme() {
  let t = "green";
  try {
    t = localStorage.getItem(THEME_KEY) || "green";
  } catch (_e) {}
  setAppTheme(t);
}

initAppTheme();

function isPcWebApp() {
  const plat = String(tg.platform || "").toLowerCase();
  if (["tdesktop", "macos", "web", "weba", "webk", "unigram"].includes(plat)) return true;
  if (window.matchMedia && window.matchMedia("(pointer: fine) and (min-width: 700px)").matches) return true;
  return window.innerWidth >= 840;
}

function syncPcLayout() {
  let cabinet = false;
  try {
    cabinet = !tg.initData;
  } catch (_e) {}
  document.documentElement.classList.toggle("is-pc", cabinet || isPcWebApp());
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
  syncPcLayout();
}

let fsTries = 0;
function requestMiniAppFullscreen() {
  if (isPcWebApp()) return;
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
window.addEventListener("resize", syncPcLayout);

let navScrollY = 0;
function syncNavScroll() {
  const y = window.scrollY || document.documentElement.scrollTop || 0;
  document.documentElement.classList.toggle("is-scrolled", y > 10);
  navScrollY = y;
}
window.addEventListener("scroll", syncNavScroll, { passive: true });

const LK_TOKEN_KEY = "way_lk_token";

function readLkCookie() {
  try {
    const parts = document.cookie.split(";");
    for (let i = 0; i < parts.length; i += 1) {
      const raw = parts[i].trim();
      const cut = raw.indexOf("=");
      if (cut < 0) continue;
      if (raw.slice(0, cut) !== LK_TOKEN_KEY) continue;
      return decodeURIComponent(raw.slice(cut + 1) || "");
    }
  } catch (_e) {}
  return "";
}

function writeLkCookie(token) {
  try {
    if (token) {
      document.cookie = LK_TOKEN_KEY + "=" + encodeURIComponent(token) + "; Max-Age=34560000; Path=/; SameSite=Lax";
    } else {
      document.cookie = LK_TOKEN_KEY + "=; Max-Age=0; Path=/";
    }
  } catch (_e) {}
}

function readLkToken() {
  const params = new URLSearchParams(window.location.search);
  const fromUrl = (params.get("t") || "").trim();
  if (fromUrl) {
    try {
      localStorage.setItem(LK_TOKEN_KEY, fromUrl);
    } catch (_e) {}
    writeLkCookie(fromUrl);
    params.delete("t");
    const qs = params.toString();
    const next = window.location.pathname + (qs ? `?${qs}` : "") + window.location.hash;
    try {
      history.replaceState({}, "", next);
    } catch (_e) {}
    return fromUrl;
  }
  try {
    const stored = localStorage.getItem(LK_TOKEN_KEY) || "";
    if (stored) {
      writeLkCookie(stored);
      return stored;
    }
  } catch (_e) {}
  const fromCookie = readLkCookie();
  if (fromCookie) {
    try {
      localStorage.setItem(LK_TOKEN_KEY, fromCookie);
    } catch (_e) {}
  }
  return fromCookie;
}

let lkToken = readLkToken();

function persistLkToken(token) {
  lkToken = String(token || "").trim();
  try {
    if (lkToken) localStorage.setItem(LK_TOKEN_KEY, lkToken);
    else localStorage.removeItem(LK_TOKEN_KEY);
  } catch (_e) {}
  writeLkCookie(lkToken);
}

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
  if (id === "router") return "Роутер";
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

const FUN_DEVICE_NAMES = [
  "Мармеладный мишка",
  "Хороший мальчик",
  "Акита ину",
  "Плюшевый кролик",
  "Лунный кот",
  "Сахарный песик",
  "Ленивый енот",
  "Космический хомяк",
  "Ванильный дракон",
  "Тихий барсук",
  "Рыжий корги",
  "Облачный кит",
  "Мятный динозавр",
  "Сонный пингвин",
  "Храбрый ёжик",
  "Сливочный пудель",
  "Ночной филин",
  "Ягодный лис",
  "Добрая капибара",
  "Морской котик",
  "Банановый гусь",
  "Шоколадный лабрадор",
  "Пушистая шиншилла",
  "Вежливый кактус",
  "Тёплый плед",
  "Чайный гриб",
  "Бумажный самолёт",
  "Стеклянная лягушка",
  "Клубничный ёж",
  "Синий корги",
  "Медовый шмель",
  "Тихий кактус",
  "Мокрый спаниель",
  "Розовый фламинго",
  "Снежный барс",
];

function diceIconSvg() {
  return (
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
    '<rect x="3.5" y="3.5" width="17" height="17" rx="4" stroke="currentColor" stroke-width="1.8"/>' +
    '<circle cx="8.2" cy="8.2" r="1.15" fill="currentColor"/>' +
    '<circle cx="15.8" cy="8.2" r="1.15" fill="currentColor"/>' +
    '<circle cx="12" cy="12" r="1.15" fill="currentColor"/>' +
    '<circle cx="8.2" cy="15.8" r="1.15" fill="currentColor"/>' +
    '<circle cx="15.8" cy="15.8" r="1.15" fill="currentColor"/>' +
    "</svg>"
  );
}

function pickFunDeviceName(current) {
  const now = String(current || "").trim();
  const pool = FUN_DEVICE_NAMES.filter((n) => n !== now);
  const list = pool.length ? pool : FUN_DEVICE_NAMES;
  return list[Math.floor(Math.random() * list.length)];
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
  if (id === "router") {
    return '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="3.5" y="11" width="17" height="8" rx="2.2" stroke="currentColor" stroke-width="1.8"/><path d="M7 11V8.2M12 11V6.5M17 11V8.2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><circle cx="8" cy="15" r="1.1" fill="currentColor"/><circle cx="12" cy="15" r="1.1" fill="currentColor"/><path d="M4.8 7.2a9.2 9.2 0 0 1 14.4 0" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>';
  }
  if (id === "ios") {
    return '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M16.7 12.7c0-2.1 1.7-3.1 1.8-3.2-1-1.4-2.5-1.6-3-1.6-1.3-.1-2.5.8-3.1.8-.7 0-1.7-.7-2.8-.7-1.4.1-2.8.8-3.5 2.1-1.5 2.6-.4 6.4 1.1 8.5.7 1 1.6 2.1 2.7 2.1 1.1 0 1.5-.7 2.8-.7s1.6.7 2.8.7c1.2 0 1.9-1 2.6-2 .8-1.2 1.1-2.3 1.1-2.4 0 0-2.2-.9-2.5-3.6zm-1.6-6.6c.6-.7 1-1.7.9-2.7-.9 0-2 .6-2.6 1.3-.6.6-1.1 1.6-.9 2.6 1 .1 2-.5 2.6-1.2z"/></svg>';
  }
  if (id === "android") {
    return '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M17.7 9.15l1.72-3a.7.7 0 10-1.22-.7l-1.76 3.05a10.4 10.4 0 00-8.88 0L5.8 5.45a.7.7 0 10-1.22.7l1.72 3A8.1 8.1 0 003.5 15.5h17a8.1 8.1 0 00-2.8-6.35zM8.2 13.4a1.15 1.15 0 110-2.3 1.15 1.15 0 010 2.3zm7.6 0a1.15 1.15 0 110-2.3 1.15 1.15 0 010 2.3z"/></svg>';
  }
  if (id === "macos") {
    return '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="3" y="4" width="18" height="12.5" rx="2.2" stroke="currentColor" stroke-width="1.8"/><path d="M8 20.5h8M12 16.5v4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path fill="currentColor" d="M13.9 8.7c0-1.1.9-1.6.9-1.7-.5-.7-1.3-.8-1.6-.8-.7-.1-1.3.4-1.6.4-.4 0-.9-.4-1.5-.4-.7 0-1.5.4-1.8 1.1-.8 1.3-.2 3.3.6 4.4.4.5.8 1.1 1.4 1.1.6 0 .8-.4 1.4-.4s.8.4 1.5.4c.6 0 1-.5 1.4-1.1.4-.6.6-1.2.6-1.2s-1.2-.4-1.3-1.8zm-.8-3.4c.3-.4.5-.9.5-1.4-.5 0-1 .3-1.3.7-.3.3-.6.8-.5 1.3.5.1 1-.2 1.3-.6z"/></svg>';
  }
  if (id === "windows") {
    return '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3.5 6.2l8.1-1.1v7.2H3.5V6.2zm9.1-1.3l8.4-1.2v8.6h-8.4V4.9zM3.5 13.6h8.1v7.3l-8.1-1.1v-6.2zm9.1.1h8.4v8.5l-8.4-1.2V13.7z"/></svg>';
  }
  if (id === "androidtv") {
    return '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="2.5" y="5" width="19" height="12.5" rx="2.2" stroke="currentColor" stroke-width="1.8"/><path d="M8 20.5h8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><circle cx="9.2" cy="11.2" r="1.1" fill="currentColor"/><circle cx="14.8" cy="11.2" r="1.1" fill="currentColor"/></svg>';
  }
  return '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="2.5" y="5" width="19" height="12.5" rx="2.2" stroke="currentColor" stroke-width="1.8"/><path d="M8 20.5h8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path fill="currentColor" d="M12.7 9.3c0-.8.6-1.2.6-1.2-.4-.5-1-.6-1.2-.6-.5 0-1 .3-1.2.3s-.7-.3-1.1-.3c-.6 0-1.1.3-1.4.8-.6 1-.2 2.5.4 3.3.3.4.6.8 1.1.8s.6-.3 1.1-.3.6.3 1.1.3c.5 0 .8-.4 1.1-.8.3-.5.4-.9.4-1zm-.6-2.5c.2-.3.4-.7.4-1.1-.4 0-.8.2-1 .5-.2.3-.4.6-.4 1 .4 0 .8-.2 1-.4z"/></svg>';
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
  const appBg = cssVar("--bg-app", "#0d1611");
  const accent = cssVar("--accent", "#5fd68b");
  bg.setAttribute("fill", dark ? appBg : "#ffffff");
  const path = document.createElementNS(ns, "path");
  path.setAttribute("d", d);
  path.setAttribute("fill", dark ? accent : appBg);
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
      ? "Добавьте устройство — без него VPN не стартует, деньги лежат. Сутки только за то, что сами добавите."
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
  if (me.balance_enabled && me.billing_paused && running) {
    setFrog("happy");
    setGauge(1, "ok");
    badge.classList.add("hidden");
    pill.className = "status-pill on";
    pill.innerHTML = '<span class="dot"></span> Подключено';
    $("statusNote").textContent = "Тарификация отключена. Сутки с баланса не списываются.";
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

function inviteMonthNeed(me) {
  const reward = Math.max(0, Number(me && me.referral_reward_rub) || 0);
  const day = Math.max(1, Number(me && me.vpn_day_price_rub) || 1);
  if (reward < 1) return 0;
  return Math.max(1, Math.ceil((day * 30) / reward));
}

function inviteMonthLeft(me) {
  const need = inviteMonthNeed(me);
  if (need < 1) return 0;
  const rewarded = Math.max(0, Number(me && me.referral_rewarded_count) || 0);
  const inCycle = rewarded % need;
  return inCycle === 0 ? need : (need - inCycle);
}

function inviteHomeProgress(me) {
  if (!me || !me.balance_enabled) return "";
  const left = inviteMonthLeft(me);
  if (left < 1) return "";
  return `Ещё ${left} ${friendsWord(left)} с оплатой — и месяц VPN`;
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
  hideDecoy();
  $("boot").classList.remove("hidden");
  $("fail").classList.add("hidden");
  $("maint").classList.add("hidden");
  $("app").classList.add("hidden");
}

function showFail(message, opts = {}) {
  hideCoach();
  hideIntro();
  hideDecoy();
  $("boot").classList.add("hidden");
  $("app").classList.add("hidden");
  $("maint").classList.add("hidden");
  $("fail").classList.remove("hidden");
  $("failText").textContent = message;
  const login = Boolean(opts.login);
  const form = $("loginForm");
  const retry = $("retryBtn");
  if (form) form.classList.toggle("hidden", !login);
  if (retry) retry.classList.toggle("hidden", login);
  if (login) {
    const input = $("loginUser");
    if (input) setTimeout(() => input.focus(), 50);
  }
}

function showLogin(message) {
  showFail(message || "Введите логин Telegram", { login: true });
}

function goToDecoy(query) {
  const q = String(query || "").trim();
  try {
    const params = new URLSearchParams(window.location.search);
    params.delete("t");
    if (q) params.set("q", q);
    else params.delete("q");
    const qs = params.toString();
    history.replaceState({}, "", window.location.pathname + (qs ? `?${qs}` : "") + window.location.hash);
  } catch (_e) {}
  showDecoy(q);
}

function fakeSearchHits(q) {
  const text = String(q || "").trim() || "запрос";
  const enc = encodeURIComponent(text);
  return [
    {
      host: "ru.wikipedia.org",
      title: text + " — Википедия",
      href: "https://ru.wikipedia.org/w/index.php?search=" + enc,
      snippet: "Краткая справка, связанные статьи и ссылки по запросу «" + text + "».",
    },
    {
      host: "www.google.com",
      title: "Результаты по запросу " + text,
      href: "https://www.google.com/search?q=" + enc,
      snippet: "Документы, новости и страницы, где встречается «" + text + "».",
    },
    {
      host: "yandex.ru",
      title: text + ": что это и где искать",
      href: "https://yandex.ru/search/?text=" + enc,
      snippet: "Подборка открытых источников, определения и похожие формулировки.",
    },
    {
      host: "translate.yandex.ru",
      title: "Перевод и значение: " + text,
      href: "https://translate.yandex.ru/?text=" + enc,
      snippet: "Возможные значения, употребление в текстах и близкие по смыслу слова.",
    },
  ];
}

function paintDecoyHits(q) {
  const box = $("decoyHits");
  const stats = $("decoyStats");
  if (!box) return;
  const hits = fakeSearchHits(q);
  const n = 800000 + (String(q).length * 17341) % 9000000;
  if (stats) stats.textContent = "Результатов: примерно " + n.toLocaleString("ru-RU") + " (0,31 сек.)";
  box.innerHTML = hits.map((item) => (
    "<article class=\"decoy-hit\">" +
      "<a href=\"" + item.href + "\" target=\"_blank\" rel=\"noopener noreferrer\">" +
        "<cite>" + item.host + "</cite>" +
        "<h3>" + item.title.replace(/</g, "") + "</h3>" +
      "</a>" +
      "<p>" + item.snippet.replace(/</g, "") + "</p>" +
    "</article>"
  )).join("");
}

function showDecoy(query) {
  hideCoach();
  hideIntro();
  document.documentElement.classList.add("is-decoy");
  document.title = query ? (query + " — Поиск") : "Поиск";
  $("boot").classList.add("hidden");
  $("fail").classList.add("hidden");
  $("maint").classList.add("hidden");
  $("app").classList.add("hidden");
  const q = String(query || "").trim();
  const home = $("decoyHome");
  const serp = $("decoySerp");
  const top = $("decoyQTop");
  const main = $("decoyQ");
  if (main && q) main.value = q;
  if (top && q) top.value = q;
  if (q) {
    if (home) home.classList.add("hidden");
    if (serp) serp.classList.remove("hidden");
    paintDecoyHits(q);
  } else {
    if (home) home.classList.remove("hidden");
    if (serp) serp.classList.add("hidden");
    if (main) setTimeout(() => main.focus(), 40);
  }
}

function hideDecoy() {
  document.documentElement.classList.remove("is-decoy");
}

function showMaint(notice) {
  hideCoach();
  hideIntro();
  hideDecoy();
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
  hideDecoy();
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
  maybeOpenFirstRun(window.__me);
  $("boot").classList.add("hidden");
  $("fail").classList.add("hidden");
  $("maint").classList.add("hidden");
  $("app").classList.remove("hidden");
  $("app").inert = true;
  el.classList.add("intro-go");
  introTimer = setTimeout(() => {
    $("app").inert = false;
    hideIntro();
    if (screen === "home") scheduleCoach();
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
  ["view-home", "view-topup", "view-wizard", "view-device", "view-router", "view-support", "view-faq", "view-article", "view-billing", "view-referrals", "view-offer", "view-settings"].forEach((vid) => {
    const el = $(vid);
    if (!el) return;
    const on = vid === id;
    el.classList.toggle("hidden", !on);
    el.classList.remove("view-in-fade", "view-in-push", "view-in-pop");
    if (on && !$("app").classList.contains("hidden")) {
      replayAnim(el, "view-in-" + (motion || "fade"));
    }
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
    screen === "router" ||
    screen === "topup" ||
    screen === "support" ||
    screen === "faq" ||
    screen === "billing" ||
    screen === "settings" ||
    screen === "article"
  ) {
    return;
  }
  if (screen === "offer") {
    paintOffer(me);
    return;
  }
  if (shouldShowOffer(me)) {
    openOffer({ instant: true });
    return;
  }
  if (me.balance_enabled) startWizard({ fromOffer: false, instant: true });
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
        text: "Пробные рубли сразу на баланс. Пока устройства нет — ничего не спишется. Так можно спокойно проверить, держит ли.",
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
        text: "Без устройства VPN не заработает и баланс не начнёт тратиться. Три коротких шага — и устройство будет готово.",
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
        text: "Телефон, компьютер или телевизор. Каждое — свои сутки, добавляйте только то, чем пользуетесь.",
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
        text: "Имя только для Вашего списка. Кнопка «Создать» спишет сутки с баланса и выдаст ссылку.",
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
        text: "Нажмите «Открыть» или вставьте ссылку вручную. После этого VPN заработает. Если что — напишите в поддержку.",
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
  return periodTopupRub(me, 30);
}

function periodTopupRub(me, days) {
  const n = Math.max(1, Number(me.vpn_day_price_rub) || 1) * days;
  const min = Number(me.topup_min) || 1;
  const max = Number(me.topup_max) || n;
  return Math.min(max, Math.max(min, Math.round(n)));
}

function periodTopupPlans(me) {
  if (!me.balance_enabled) {
    const order = { "1m": 1, "3m": 2, "6m": 3, "12m": 4 };
    return (me.plans || [])
      .filter((p) => order[p.code])
      .sort((a, b) => order[a.code] - order[b.code])
      .map((p) => Object.assign({}, p, {
        label: p.title,
        hit: p.code === "6m",
      }));
  }
  const day = Math.max(1, Number(me.vpn_day_price_rub) || 1);
  const min = Number(me.topup_min) || 1;
  const max = Number(me.topup_max) || 5000;
  const periods = [
    { days: 30, label: "1 мес" },
    { days: 180, label: "6 мес", hit: true },
    { days: 365, label: "12 мес" },
  ];
  const packs = [700, 2000, 5000];
  const out = [];
  const seen = {};
  const add = (n, extra) => {
    if (!Number.isFinite(n) || n < min || n > max || seen[n]) return;
    seen[n] = true;
    out.push(Object.assign({
      code: "b" + n,
      title: n + " рублей",
      topup_rub: n,
      rub: n,
    }, extra));
  };
  periods.forEach((s) => {
    add(day * s.days, { days: s.days, label: s.label, hit: Boolean(s.hit) });
  });
  packs.forEach((n) => {
    const days = Math.floor(n / day);
    add(n, { days, label: daysLabel(days), pack: true });
  });
  return out;
}

function monthTopupPlan(me) {
  const plans = periodTopupPlans(me);
  return plans[0] || {
    code: "b" + monthTopupRub(me),
    title: monthTopupRub(me) + " рублей",
    topup_rub: monthTopupRub(me),
    rub: monthTopupRub(me),
  };
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
  const plans = periodTopupPlans(me);
  return plans.find((p) => p.code === topupCode) || plans.find((p) => p.hit) || plans[0] || null;
}

function ensureTopupCode(me) {
  const plans = periodTopupPlans(me);
  if (plans.some((p) => p.code === topupCode)) return;
  const hit = plans.find((p) => p.hit);
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
  if (screen === "router") {
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
  if (screen === "article") {
    finishAnnouncement();
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
  if (screen === "settings") {
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
  const fromStack = screen === "wizard" || screen === "device" || screen === "router" || screen === "topup" || screen === "support" || screen === "faq" || screen === "article" || screen === "billing" || screen === "referrals" || screen === "offer" || screen === "settings";
  stopSupportPoll();
  stopRouterPayPoll();
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

function ticketDayLabel(d) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const day = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const diff = (today - day) / 86400000;
  if (diff === 0) return "Сегодня";
  if (diff === 1) return "Вчера";
  return d.toLocaleDateString("ru-RU", { day: "numeric", month: "long" });
}

function ticketTimeLabel(d) {
  return d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}

function paintSupportChrome(current) {
  const status = $("supportStatus");
  const badge = $("supportBadge");
  const note = $("supportComposeNote");
  const input = $("supportText");
  if (status) {
    status.textContent = current
      ? `Тикет #${current.id}`
      : "Напишите, что случилось. Можно прикрепить скриншот. Ответ придёт сюда и в чат бота.";
  }
  if (badge) {
    const key = current && current.status;
    badge.textContent = SUPPORT_STATUS[key] || "";
    badge.className = "support-badge" + (key ? " is-" + key : " hidden");
    if (!key) badge.classList.add("hidden");
  }
  if (note) {
    note.classList.toggle("hidden", !(current && current.status === "closed"));
  }
  if (input) input.placeholder = "Написать";
}

function resizeSupportText() {
  const el = $("supportText");
  if (!el) return;
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 140) + "px";
}

function paintSupportThread(current) {
  const box = $("supportThread");
  if (!box) return;
  box.innerHTML = "";
  paintSupportChrome(current);
  const messages = (current && current.messages) || [];
  if (!messages.length) {
    const empty = document.createElement("div");
    empty.className = "support-empty";
    empty.textContent = current
      ? (current.status === "closed"
        ? "Переписка пустая. Новое сообщение откроет следующий тикет."
        : "Пока пусто. Опишите проблему — откроем тикет.")
      : "Пока пусто. Опишите проблему — откроем тикет.";
    box.appendChild(empty);
    return;
  }
  let lastDay = "";
  messages.forEach((m) => {
    const when = m.created_at ? new Date(m.created_at) : null;
    const valid = when && !Number.isNaN(when.getTime());
    if (valid) {
      const day = ticketDayLabel(when);
      if (day !== lastDay) {
        lastDay = day;
        const sep = document.createElement("div");
        sep.className = "support-day";
        sep.textContent = day;
        box.appendChild(sep);
      }
    }
    const wrap = document.createElement("div");
    wrap.className = "support-bubble " + (m.author === "admin" ? "admin" : "user");
    if (m.author === "admin") {
      const meta = document.createElement("div");
      meta.className = "support-bubble-meta";
      meta.textContent = "Поддержка";
      wrap.appendChild(meta);
    }
    if (m.body) {
      const body = document.createElement("div");
      body.className = "support-bubble-body";
      body.textContent = m.body;
      wrap.appendChild(body);
    }
    paintTicketAttachments(wrap, m.attachments);
    if (valid) {
      const time = document.createElement("div");
      time.className = "support-bubble-time";
      time.textContent = ticketTimeLabel(when);
      wrap.appendChild(time);
    }
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
  items.forEach((item) => {
    const wrap = document.createElement("div");
    wrap.className = "faq-item";
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

function openSettings() {
  hideCoach();
  stopSupportPoll();
  screen = "settings";
  switchView("view-settings", "push");
  setMain("");
  paintThemePicker();
  try {
    tg.BackButton.show();
  } catch (_e) {}
  syncWebBack();
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
    if (me.balance_enabled && invited > rewarded) {
      note.textContent = earned > 0
        ? "Начислено за " + rewarded + " " + friendsWord(rewarded) + " с оплатой. Остальные ещё не оплатили."
        : "Деньги придут после первой оплаты друга. Пока бонус не начислен.";
    } else if (invited > 0 && rewarded === 0 && earned === 0) {
      note.textContent = me.balance_enabled
        ? "Друзья пришли, но ещё не оплатили — бонус после первой оплаты."
        : "Друзья пришли. Дни начислятся после их первой оплаты.";
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
      if (how) how.textContent = `Вам ${rub} ₽ за каждого, кто оплатил. Другу за переход бонус не начисляется.`
        + (Number(me.referral_invitee_reward_rub) > 0
          ? ` После первой оплаты другу ещё ${me.referral_invitee_reward_rub} ₽ на баланс.`
          : "");
      if (pay) pay.textContent = `Вывести можно от ${me.referral_payout_min || 2000} ₽ реферальных, которые ещё на балансе. Заявка уходит администратору.`;
      if (payWrap) payWrap.classList.remove("hidden");
    } else {
      if (when) when.textContent = "Начисление после первой оплаты друга по вашей ссылке. Пока друг только пришёл и не оплатил, денег не будет.";
      if (how) how.textContent = `Вам ${rub} ₽ на баланс за каждого, кто оплатил. Другу бонус за переход не начисляется.`
        + (Number(me.referral_invitee_reward_rub) > 0
          ? ` После первой оплаты другу ещё ${me.referral_invitee_reward_rub} ₽ на баланс.`
          : "");
      if (payWrap) payWrap.classList.add("hidden");
    }
  } else {
    const mine = daysLabel(me.referral_reward_days || 7);
    const friend = daysLabel(me.referral_invitee_days || 5);
    if (me.referral_payout_enabled) {
      if (when) when.textContent = "Дни придут после первой оплаты друга по вашей ссылке.";
      if (how) how.textContent = `Вам ${mine}. Другу при бесплатном периоде +${friend}.`;
    } else {
      if (when) when.textContent = "Дни придут после первой оплаты друга по вашей ссылке.";
      if (how) how.textContent = `Вам ${mine}. Другу при бесплатном периоде +${friend}.`;
    }
    if (payWrap) payWrap.classList.add("hidden");
  }
  paintRefFriends(me);
  paintPayout(me);
}

function paintRefFriends(me) {
  const list = $("refFriendsList");
  const empty = $("refFriendsEmpty");
  if (!list) return;
  const friends = Array.isArray(me && me.referrals) ? me.referrals : [];
  list.innerHTML = "";
  if (!friends.length) {
    list.classList.add("hidden");
    if (empty) empty.classList.remove("hidden");
    return;
  }
  if (empty) empty.classList.add("hidden");
  list.classList.remove("hidden");
  friends.forEach((friend) => {
    const row = document.createElement("div");
    row.className = "ref-friend";
    const meta = document.createElement("div");
    meta.className = "meta";
    const name = document.createElement("div");
    name.className = "n";
    const label = String((friend && friend.name) || "друг");
    const user = friend && friend.username ? "@" + friend.username : "";
    name.textContent = user ? label + " · " + user : label;
    const st = document.createElement("div");
    const paid = !!(friend && friend.paid);
    st.className = "s" + (paid ? " ok" : "");
    st.textContent = paid ? "есть оплата" : "ещё без оплаты";
    meta.appendChild(name);
    meta.appendChild(st);
    row.appendChild(meta);
    list.appendChild(row);
  });
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
    resizeSupportText();
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

function openOffer(opts) {
  const me = window.__me;
  if (!me) return;
  hideCoach();
  screen = "offer";
  switchView("view-offer", opts && opts.instant ? "fade" : "push");
  setMain("");
  paintOffer(me);
  replayAnim($("view-offer"), "offer-play");
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
  if (topupMode !== "custom") topupMode = "fast";
  ensureTopupCode(me);
  const plans = periodTopupPlans(me);
  const canCustom = Boolean(me.balance_enabled);
  $("topupTabs").classList.toggle("hidden", !canCustom);
  if (!canCustom) topupMode = "fast";
  applyTopupMode();
  const titleEl = document.querySelector("#view-topup .wiz-title");
  if (titleEl) titleEl.textContent = "Сколько зальём?";
  $("topupHint").textContent = me.balance_enabled
    ? `Сутки одного устройства — ${me.vpn_day_price_rub} ₽. Сверху срок, снизу круглые суммы. Чем больше устройств, тем быстрее уходит баланс.`
      + (me.referred && !me.has_paid_topup && Number(me.referral_invitee_reward_rub) > 0
        ? ` По ссылке друга после этого пополнения на баланс ещё ${me.referral_invitee_reward_rub} ₽.`
        : "")
    : "Выберите срок подписки. Сюда можно зайти даже если VPN потом отключится.";
  const grid = $("topupGrid");
  grid.innerHTML = "";
  plans.forEach((plan) => {
    const amount = planRub(plan);
    const b = document.createElement("button");
    b.type = "button";
    b.className = "pay-card" + (plan.code === topupCode ? " on" : "") + (plan.hit ? " hit" : "");
    if (plan.hit) {
      const badge = document.createElement("span");
      badge.className = "pay-badge hot";
      badge.textContent = "Хит";
      b.appendChild(badge);
    }
    const amt = document.createElement("div");
    amt.className = "pay-amount";
    amt.textContent = `${amount} ₽`;
    const days = document.createElement("div");
    days.className = "pay-days";
    days.textContent = plan.label || daysLabel(plan.days);
    b.appendChild(amt);
    b.appendChild(days);
    const rateEl = document.createElement("div");
    rateEl.className = "pay-rate";
    if (me.balance_enabled) {
      const day = Math.max(1, Number(me.vpn_day_price_rub) || 1);
      const one = Math.floor(amount / day);
      rateEl.textContent = plan.pack ? "на 1 устройство" : `≈ ${daysLabel(one)}`;
    } else {
      rateEl.textContent = plan.rub ? `${plan.rub} ₽` : `${plan.stars} звёзд`;
    }
    b.appendChild(rateEl);
    b.onclick = () => {
      haptic();
      topupCode = plan.code;
      renderTopup(me);
    };
    grid.appendChild(b);
  });
  if (canCustom) {
    const min = Number(me.topup_min) || 1;
    const max = Number(me.topup_max) || min;
    if (!topupCustomRub) {
      const hit = plans.find((p) => p.hit) || plans[0];
      topupCustomRub = Math.min(max, Math.max(min, planRub(hit) || min));
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
  const n = phoneDevices(me).length;
  if (cap > 0 && n >= cap) {
    tg.showAlert("Можно подключить не больше " + cap + " устройств");
    return;
  }
  if (!(opts && opts.instant)) haptic();
  hideCoach();
  wiz.step = 1;
  wiz.platform = isPcWebApp() ? "windows" : "ios";
  const first = clientsFor(wiz.platform)[0];
  wiz.client = first ? first.id : "";
  wiz.title = "";
  wiz.url = "";
  wiz.fromOffer = Boolean(opts && opts.fromOffer);
  screen = "wizard";
  switchView("view-wizard", opts && opts.instant ? "fade" : "push");
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
    lead.textContent = "Каждое устройство — свои сутки. Добавляйте только то, чем пользуетесь.";
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
    const row = document.createElement("div");
    row.className = "wiz-name-row";
    row.appendChild(input);
    const dice = document.createElement("button");
    dice.type = "button";
    dice.className = "wiz-dice";
    dice.setAttribute("aria-label", "Случайное название");
    dice.innerHTML = diceIconSvg();
    let diceBusy = false;
    dice.onclick = () => {
      if (diceBusy) return;
      haptic();
      diceBusy = true;
      const finish = (name) => {
        wiz.title = name;
        input.value = name;
        paintChips();
        diceBusy = false;
        dice.classList.remove("is-rolling");
      };
      if (reducedMotion()) {
        finish(pickFunDeviceName(input.value));
        return;
      }
      dice.classList.add("is-rolling");
      let n = 0;
      const tick = setInterval(() => {
        input.value = pickFunDeviceName(input.value);
        n += 1;
        if (n < 8) return;
        clearInterval(tick);
        finish(pickFunDeviceName(input.value));
      }, 55);
    };
    row.appendChild(dice);
    box.appendChild(row);
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
  const icon = document.querySelector("#view-device .dev-icon");
  if (icon) icon.innerHTML = platIconSvg(d.platform);
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
  if (isRouterDevice(d)) {
    openRouter();
    return;
  }
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

function isRouterDevice(d) {
  return Boolean(d && (d.kind === "router" || d.platform === "router"));
}

function phoneDevices(me) {
  return (me && me.devices ? me.devices : []).filter((d) => !isRouterDevice(d));
}

function routerDevice(me) {
  return (me && me.devices ? me.devices : []).find((d) => isRouterDevice(d)) || null;
}

function devicesKey(me) {
  return (me.devices || [])
    .map((d) => [d.id, d.title || "", d.active ? 1 : 0, d.client || "", d.platform || "", d.kind || ""].join(":"))
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
  const phoneN = phoneDevices(me).length;
  const cap = Number(me.max_devices) || 0;
  const atCap = cap > 0 && phoneN >= cap;
  $("deviceCount").textContent = cap > 0 ? "· " + n + " из " + cap : "· " + n;
  $("addDevice").classList.toggle("hidden", (phoneN === 0 && n === 0) || atCap);
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
      platIconSvg(d.platform) +
      "</div>";
    const meta = document.createElement("div");
    meta.className = "meta";
    const title = document.createElement("div");
    title.className = "n";
    title.textContent = d.title || "Устройство";
    const st = document.createElement("div");
    st.className = "s" + (d.active ? "" : " off");
    st.innerHTML = '<span class="dot"></span>' + (d.active ? "Подключено" : "Неактивно");
    if (isRouterDevice(d)) {
      st.innerHTML = '<span class="dot"></span>' + (d.active ? "Роутер · не с баланса" : "Роутер · неактивен");
    }
    meta.appendChild(title);
    meta.appendChild(st);
    el.appendChild(meta);
    const chev = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    chev.setAttribute("class", "chev");
    chev.setAttribute("viewBox", "0 0 24 24");
    chev.setAttribute("width", "18");
    chev.setAttribute("height", "18");
    chev.setAttribute("fill", "none");
    chev.setAttribute("aria-hidden", "true");
    const chevPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
    chevPath.setAttribute("d", "M9 6l6 6-6 6");
    chevPath.setAttribute("stroke", "currentColor");
    chevPath.setAttribute("stroke-width", "2");
    chevPath.setAttribute("stroke-linecap", "round");
    chevPath.setAttribute("stroke-linejoin", "round");
    chev.appendChild(chevPath);
    el.appendChild(chev);
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

function paintRefBanner(me) {
  const pill = $("inviteBannerPill");
  if (!pill) return;
  const rub = Math.max(0, Number(me && me.referral_reward_rub) || 0);
  const days = Math.max(0, Number(me && me.referral_reward_days) || 0);
  if (me && me.balance_enabled && rub > 0) {
    pill.innerHTML = "Получайте <span class=\"ref-banner-amt\">" + rub + " ₽</span> за каждого друга";
  } else if (days > 0) {
    pill.innerHTML = "Получайте <span class=\"ref-banner-amt\">" + daysLabel(days) + "</span> за каждого друга";
  } else {
    pill.textContent = "Отправьте ссылку — друг попадёт к нам же";
  }
}

function routerInfo(me) {
  return (me && me.router) || {};
}

function fmtRouterDate(iso) {
  if (!iso) return "";
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return "";
  return dt.toLocaleDateString("ru-RU");
}

function paintRouterCard(me) {
  const card = $("routerCard");
  if (!card) return;
  const r = routerInfo(me);
  const on = Boolean(me && me.balance_enabled && r.enabled);
  card.classList.toggle("hidden", !on);
  if (!on) return;
  const pill = $("routerCardNote");
  if (!pill) return;
  const days = r.days || 30;
  const rub = r.rub || 0;
  if (r.active && r.has_device) {
    const until = fmtRouterDate(r.expire_at);
    pill.innerHTML = until
      ? "До <span class=\"ref-banner-amt\">" + until + "</span>"
      : "Оплачен · в устройствах";
    return;
  }
  if (r.active) {
    pill.innerHTML = "Оплачен · <span class=\"ref-banner-amt\">создать</span>";
    return;
  }
  pill.innerHTML =
    "<span class=\"ref-banner-amt\">" + days + " дней</span> · " + rub + " ₽";
}

let routerPayPoll = 0;

function stopRouterPayPoll() {
  if (routerPayPoll) {
    clearInterval(routerPayPoll);
    routerPayPoll = 0;
  }
}

function armRouterPayPoll() {
  stopRouterPayPoll();
  let n = 0;
  routerPayPoll = setInterval(() => {
    n += 1;
    if (n > 40 || screen !== "router") {
      stopRouterPayPoll();
      return;
    }
    load()
      .then(() => {
        const r = window.__me && window.__me.router;
        if (r && r.active) stopRouterPayPoll();
      })
      .catch(() => {});
  }, 3000);
}

function openRouter() {
  const me = window.__me;
  const r = routerInfo(me);
  if (!me || !me.balance_enabled || !r.enabled) return;
  haptic();
  screen = "router";
  switchView("view-router", "push");
  try {
    tg.BackButton.show();
  } catch (_e) {}
  syncWebBack();
  setMain("");
  renderRouter(me);
}

function renderRouter(me) {
  const r = routerInfo(me);
  const status = $("routerStatus");
  const actions = $("routerActions");
  const lead = $("routerLead");
  if (!status || !actions) return;
  const days = r.days || 30;
  const rub = r.rub || 0;
  const until = fmtRouterDate(r.expire_at);
  const device = routerDevice(me);
  if (lead) {
    lead.textContent =
      "Слот на " +
      days +
      " дней. Не списывается с баланса телефонов и не занимает лимит устройств. Один роутер на аккаунт.";
  }
  status.innerHTML = "";
  const k = document.createElement("div");
  k.className = "k";
  const v = document.createElement("div");
  v.className = "v";
  const d = document.createElement("div");
  d.className = "d";
  if (r.active && device) {
    k.textContent = "Слот активен";
    v.textContent = until ? "До " + until : "Оплачен";
    d.textContent = "Устройство уже в списке. Ссылку вставьте в клиент роутера.";
  } else if (r.active) {
    k.textContent = "Слот оплачен";
    v.textContent = until ? "До " + until : "Можно создать устройство";
    d.textContent = "Создайте роутер — он появится в устройствах, даже если лимит телефонов заполнен.";
  } else {
    k.textContent = "Отдельная оплата";
    v.textContent = rub + " ₽ за " + days + " дней";
    d.textContent = "После оплаты создайте устройство и вставьте ссылку в Keenetic, OpenWrt или другой клиент.";
  }
  status.appendChild(k);
  status.appendChild(v);
  status.appendChild(d);
  actions.innerHTML = "";
  if (!r.active) {
    const pay = document.createElement("button");
    pay.type = "button";
    pay.className = "btn btn-primary";
    pay.textContent = "Оплатить " + rub + " ₽";
    pay.onclick = async () => {
      haptic();
      pay.disabled = true;
      try {
        await payPlan({ code: "router" });
        armRouterPayPoll();
        tg.showAlert("После оплаты вернитесь сюда — слот появится сам.");
      } catch (e) {
        showErr(e);
      } finally {
        pay.disabled = false;
      }
    };
    actions.appendChild(pay);
    return;
  }
  if (!device) {
    const create = document.createElement("button");
    create.type = "button";
    create.className = "btn btn-primary";
    create.textContent = "Создать устройство";
    create.onclick = async () => {
      haptic();
      create.disabled = true;
      try {
        await api("/api/devices", {
          method: "POST",
          body: JSON.stringify({ kind: "router", title: "Роутер", platform: "router" }),
        });
        await load();
      } catch (e) {
        showErr(e);
      } finally {
        create.disabled = false;
      }
    };
    actions.appendChild(create);
    return;
  }
  if (device.subscription_url) {
    const link = document.createElement("div");
    link.className = "router-link";
    link.textContent = device.subscription_url;
    actions.appendChild(link);
    const copy = document.createElement("button");
    copy.type = "button";
    copy.className = "btn btn-primary";
    copy.textContent = "Скопировать ссылку";
    copy.onclick = () => {
      haptic();
      navigator.clipboard.writeText(device.subscription_url);
      tg.showAlert("Ссылка скопирована");
    };
    actions.appendChild(copy);
  }
  const reissue = document.createElement("button");
  reissue.type = "button";
  reissue.className = "btn btn-ghost";
  reissue.textContent = "Перевыпустить ссылку";
  reissue.onclick = async () => {
    await reissueSubscription(device.id);
    if (screen === "router") renderRouter(window.__me);
  };
  actions.appendChild(reissue);
  const del = document.createElement("button");
  del.type = "button";
  del.className = "btn btn-ghost";
  del.textContent = "Удалить устройство";
  del.onclick = async () => {
    haptic();
    if (!(await askDeleteDevice())) return;
    try {
      await api(`/api/devices/${device.id}`, { method: "DELETE" });
      lastDevicesKey = "";
      await load();
      showToast("Устройство удалено");
    } catch (e) {
      showErr(e);
    }
  };
  actions.appendChild(del);
}

function paintInviteeBonus(me) {
  const el = $("inviteeBonus");
  if (!el) return;
  const n = Math.max(0, Number(me && me.referral_invitee_reward_rub) || 0);
  const show = !!(me && me.balance_enabled && me.referred && !me.has_paid_topup && n > 0);
  el.classList.toggle("hidden", !show);
  if (show) {
    el.textContent =
      "Вы пришли по ссылке друга. После первого пополнения на баланс ещё " + n + " ₽.";
  }
}

const ANNOUNCE_KEY = "way_announce_seen_v1";

function seenAnnouncementId() {
  try {
    return Number(localStorage.getItem(ANNOUNCE_KEY) || 0) || 0;
  } catch (_e) {
    return 0;
  }
}

function markAnnouncementSeen(id) {
  try {
    localStorage.setItem(ANNOUNCE_KEY, String(id || 0));
  } catch (_e) {}
}

function shortenLead(text, max) {
  const s = String(text || "").replace(/\s+/g, " ").trim();
  if (!s) return "";
  if (s.length <= max) return s;
  const cut = s.slice(0, max);
  const space = cut.lastIndexOf(" ");
  return ((space > 40 ? cut.slice(0, space) : cut).trim()) + "…";
}

function paintUpdateNotice(me) {
  const el = $("updateNotice");
  if (!el) return;
  const a = me && me.announcement;
  const id = a && Number(a.id);
  const items = (a && a.items) || [];
  const hasCopy = Boolean((a && a.lead) || (a && a.title) || items.length);
  const show = Boolean(id && hasCopy && id !== seenAnnouncementId());
  el.classList.toggle("hidden", !show);
  if (!show) return;
  const kicker = $("updateNoticeKicker");
  if (kicker) kicker.textContent = a.kicker || "Что нового";
  $("updateNoticeTitle").textContent = a.title || "Мы кое-что обновили";
  const lead = $("updateNoticeLead");
  if (lead) {
    const short = shortenLead(a.lead || "", 120);
    lead.textContent = short;
    lead.classList.toggle("hidden", !short);
  }
}

function paintArticle(a) {
  if (!a) return;
  const kicker = $("articleKicker");
  if (kicker) kicker.textContent = a.kicker || "Что нового";
  const title = $("articleTitle");
  if (title) title.textContent = a.title || "Мы кое-что обновили";
  const lead = $("articleLead");
  if (lead) {
    lead.textContent = a.lead || "";
    lead.classList.toggle("hidden", !a.lead);
  }
  const closing = $("articleClosing");
  if (closing) {
    closing.textContent = a.closing || "";
    closing.classList.toggle("hidden", !a.closing);
  }
  const list = $("articleItems");
  const items = a.items || [];
  if (list) {
    list.innerHTML = "";
    list.classList.toggle("hidden", !items.length);
    items.forEach((text) => {
      const li = document.createElement("li");
      li.textContent = text;
      list.appendChild(li);
    });
  }
  loadUpdateNoticeImage(a.image_url || "", $("articleImage"));
}

function openAnnouncement() {
  const a = window.__me && window.__me.announcement;
  if (!a || !a.id) return;
  hideCoach();
  stopSupportPoll();
  screen = "article";
  switchView("view-article", "push");
  setMain("");
  paintArticle(a);
  try {
    tg.BackButton.show();
  } catch (_e) {}
  syncWebBack();
}

function finishAnnouncement() {
  const id = window.__me && window.__me.announcement && window.__me.announcement.id;
  markAnnouncementSeen(id);
  openHome();
  if (window.__me) paintUpdateNotice(window.__me);
}

let updateNoticeBlob = "";

async function loadUpdateNoticeImage(url, img) {
  img = img || $("articleImage");
  if (!img) return;
  if (updateNoticeBlob) {
    URL.revokeObjectURL(updateNoticeBlob);
    updateNoticeBlob = "";
  }
  if (!url) {
    img.classList.add("hidden");
    img.removeAttribute("src");
    return;
  }
  try {
    const headers = { "X-Init-Data": tg.initData || "" };
    if (lkToken) headers["X-Lk-Token"] = lkToken;
    const res = await fetch(url, { headers });
    if (!res.ok) throw new Error("no image");
    const blob = await res.blob();
    updateNoticeBlob = URL.createObjectURL(blob);
    img.src = updateNoticeBlob;
    img.classList.remove("hidden");
  } catch (_e) {
    img.classList.add("hidden");
    img.removeAttribute("src");
  }
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
  paintInviteeBonus(me);
  paintRefBanner(me);
  paintRouterCard(me);
  paintUpdateNotice(me);
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
  if (screen === "router") renderRouter(me);
  if (firstRunBusy) return;
  if (!$("intro").classList.contains("hidden")) return;
  if (shouldShowIntro()) showIntro(me);
  else {
    maybeOpenFirstRun(me);
    showApp();
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
  if (!tg.initData && !lkToken) {
    showLogin("Введите логин Telegram");
    return;
  }
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
  topupMode = "fast";
  if (me) renderTopup(me);
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

if ($("updateNoticeClose")) {
  $("updateNoticeClose").onclick = (e) => {
    e.stopPropagation();
    haptic();
    const id = window.__me && window.__me.announcement && window.__me.announcement.id;
    markAnnouncementSeen(id);
    if (window.__me) paintUpdateNotice(window.__me);
  };
}
if ($("updateNotice")) {
  $("updateNotice").onclick = (e) => {
    if (e.target && e.target.closest && e.target.closest("#updateNoticeClose")) return;
    haptic();
    openAnnouncement();
  };
  $("updateNotice").onkeydown = (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    e.preventDefault();
    openAnnouncement();
  };
}
if ($("articleDone")) {
  $("articleDone").onclick = () => {
    haptic();
    finishAnnouncement();
  };
}

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
  $("refHomeCard").onkeydown = (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      haptic();
      openReferrals();
    }
  };
}
if ($("routerCard")) {
  $("routerCard").onclick = () => openRouter();
  $("routerCard").onkeydown = (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      openRouter();
    }
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
    tg.showAlert("Историю можно выложить только из приложения, не из браузера. Нужна свежая версия.");
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

function inviteShareText(me) {
  const fromApi = me && String(me.invite_share_text || "").trim();
  if (fromApi) return fromApi;
  return "VPN: сутки только за свои устройства. Подключайтесь по ссылке.";
}

function inviteCopyText(me) {
  const fromApi = me && String(me.invite_copy_text || "").trim();
  if (fromApi) return fromApi;
  const url = me && me.invite_url;
  const text = inviteShareText(me);
  return url ? text + "\n\n" + url : text;
}

function shareInvite() {
  const me = window.__me;
  const url = me && me.invite_url;
  if (!url) return;
  const text = encodeURIComponent(inviteShareText(me));
  tg.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(url)}&text=${text}`);
}

function copyInvite() {
  const me = window.__me;
  const block = inviteCopyText(me);
  if (!block) return;
  const done = () => {
    if (typeof showToast === "function") showToast("Текст скопирован");
    else tg.showAlert("Текст скопирован");
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(block).then(done).catch(() => tg.showAlert(block));
  } else {
    tg.showAlert(block);
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
if ($("menuSettings")) {
  $("menuSettings").onclick = () => {
    closeMenu();
    haptic();
    openSettings();
  };
}
if ($("themeList")) {
  $("themeList").onclick = (e) => {
    const btn = e.target.closest(".theme-swatch");
    if (!btn) return;
    haptic();
    setAppTheme(btn.getAttribute("data-theme-id"));
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
if ($("supportText")) {
  $("supportText").addEventListener("input", resizeSupportText);
  $("supportText").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && document.documentElement.classList.contains("is-pc")) {
      e.preventDefault();
      sendSupport();
    }
  });
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
  load().catch((err) => handleLoadFail(err));
};

let loginWaitSeq = 0;

function setLoginWaiting(on) {
  const form = $("loginForm");
  const input = $("loginUser");
  const btn = $("loginBtn");
  if (form) form.classList.toggle("is-waiting", Boolean(on));
  if (input) input.disabled = Boolean(on);
  if (btn) btn.disabled = Boolean(on);
}

async function waitCabinetConfirm(waitId, username) {
  const seq = ++loginWaitSeq;
  setLoginWaiting(true);
  $("failText").textContent = "Подтвердите вход в Telegram";
  const started = Date.now();
  while (seq === loginWaitSeq && Date.now() - started < 10 * 60 * 1000) {
    await new Promise((resolve) => setTimeout(resolve, 1400));
    if (seq !== loginWaitSeq) return;
    try {
      const res = await fetch("/api/cabinet-login/status?id=" + encodeURIComponent(waitId));
      const data = await res.json().catch(() => ({}));
      if (data && data.token) {
        persistLkToken(data.token);
        syncPcLayout();
        setLoginWaiting(false);
        showBoot();
        await load();
        return;
      }
      if (data && data.status === "declined") {
        setLoginWaiting(false);
        goToDecoy(username);
        return;
      }
      if (data && data.status === "expired") {
        setLoginWaiting(false);
        showLogin("Не дождались подтверждения. Попробуйте ещё раз.");
        return;
      }
    } catch (_e) {}
  }
  if (seq === loginWaitSeq) {
    setLoginWaiting(false);
    showLogin("Не дождались подтверждения. Попробуйте ещё раз.");
  }
}

if ($("loginForm")) {
  $("loginForm").onsubmit = async (e) => {
    e.preventDefault();
    const input = $("loginUser");
    const btn = $("loginBtn");
    const username = (input && input.value || "").trim();
    if (!username) {
      $("failText").textContent = "Введите логин Telegram";
      if (input) input.focus();
      return;
    }
    if (btn) btn.disabled = true;
    $("failText").textContent = "Входим...";
    try {
      const res = await fetch("/api/cabinet-login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username }),
      });
      const payload = await res.json().catch(() => ({ ok: true }));
      if (payload && payload.token) {
        persistLkToken(payload.token);
        syncPcLayout();
        showBoot();
        await load();
        return;
      }
      if (payload && payload.wait) {
        await waitCabinetConfirm(payload.wait, username);
        return;
      }
      goToDecoy(username);
    } catch (_e) {
      goToDecoy(username);
    } finally {
      if (btn && !$("loginForm").classList.contains("is-waiting")) btn.disabled = false;
    }
  };
}

if ($("loginUser") && $("loginForm")) {
  const loginInput = $("loginUser");
  const loginFormEl = $("loginForm");
  const syncLoginFrog = () => {
    const hasText = Boolean(loginInput.value);
    const focused = document.activeElement === loginInput;
    loginFormEl.classList.toggle("is-watching", focused);
    loginFormEl.classList.toggle("is-peeking", hasText && !reducedMotion());
  };
  loginInput.addEventListener("focus", syncLoginFrog);
  loginInput.addEventListener("blur", syncLoginFrog);
  loginInput.addEventListener("input", syncLoginFrog);
}

async function submitDecoySearch(raw) {
  const q = String(raw || "").trim();
  if (!q) {
    goToDecoy("");
    return;
  }
  await new Promise((resolve) => setTimeout(resolve, 220));
  goToDecoy(q);
}

function bindDecoyForm(form, input) {
  if (!form) return;
  form.onsubmit = (e) => {
    e.preventDefault();
    submitDecoySearch(input && input.value);
  };
}

bindDecoyForm($("decoyForm"), $("decoyQ"));
bindDecoyForm($("decoyFormTop"), $("decoyQTop"));
if ($("decoyHomeLink")) {
  $("decoyHomeLink").onclick = (e) => {
    e.preventDefault();
    goToDecoy("");
  };
}

function handleLoadFail(err) {
  const msg = (err && err.message) || "Не удалось загрузить данные";
  const expired = /недействительна|истекла/i.test(msg);
  if (!tg.initData && (expired || !lkToken)) {
    persistLkToken("");
    showLogin("Введите логин Telegram");
    return;
  }
  showFail(msg);
}

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

load().catch((err) => handleLoadFail(err));
