/* Лягушка VPN — кабинет (Telegram Mini App и веб-кабинет).
 * Every screen is a function that returns markup: a bright widget card, then dark cards.
 * Screens live in a stack; Telegram's Back button pops it. Data comes from /api/me. */
(function () {
  "use strict";

  // ---------- Telegram ----------
  const noop = () => {};
  const tg = (window.Telegram && window.Telegram.WebApp) || {
    initData: "", ready: noop, expand: noop, close: noop, onEvent: noop, openInvoice: noop,
    showAlert: (m, cb) => { window.alert(m); if (cb) cb(); },
    showConfirm: (m, cb) => cb(window.confirm(m)),
    openLink: (u) => window.open(u, "_blank", "noopener"),
    openTelegramLink: (u) => window.open(u, "_blank", "noopener"),
    BackButton: { show: noop, hide: noop, onClick: noop },
    HapticFeedback: { impactOccurred: noop, notificationOccurred: noop, selectionChanged: noop },
  };
  const BG = "#111215";
  const call = (fn) => { try { return fn(); } catch (_e) { return undefined; } };
  call(() => tg.ready());
  call(() => tg.expand());
  call(() => tg.disableVerticalSwipes && tg.disableVerticalSwipes());
  call(() => { tg.setHeaderColor(BG); tg.setBackgroundColor(BG); tg.setBottomBarColor && tg.setBottomBarColor(BG); });
  call(() => tg.MainButton && tg.MainButton.hide());

  const haptic = (k) => call(() => tg.HapticFeedback.impactOccurred(k || "light"));
  const notify = (k) => call(() => tg.HapticFeedback.notificationOccurred(k));
  const isPc = () => ["tdesktop", "macos", "web", "weba", "webk", "unigram"].includes(String(tg.platform || "").toLowerCase()) || innerWidth >= 840;

  function applyViewport() {
    const r = document.documentElement.style;
    const sa = tg.safeAreaInset || {}, ca = tg.contentSafeAreaInset || {};
    const fs = Boolean(tg.isFullscreen);
    const top = (+sa.top || 0) + (+ca.top || 0);
    r.setProperty("--st", `max(env(safe-area-inset-top, 0px), ${fs ? Math.max(top, 62) : top}px)`);
    r.setProperty("--sb", `max(env(safe-area-inset-bottom, 0px), ${(+sa.bottom || 0) + (+ca.bottom || 0)}px)`);
    r.setProperty("--sl", `${(+sa.left || 0) + (+ca.left || 0)}px`);
    r.setProperty("--sr", `${(+sa.right || 0) + (+ca.right || 0)}px`);
  }
  let fsTries = 0;
  function fullscreen() {
    if (isPc() || tg.isFullscreen || typeof tg.requestFullscreen !== "function") return;
    if (typeof tg.isVersionAtLeast === "function" && !tg.isVersionAtLeast("8.0")) return;
    if (fsTries++ > 6) return;
    call(() => tg.requestFullscreen());
  }
  applyViewport();
  fullscreen();
  addEventListener("resize", applyViewport);

  // ---------- web cabinet token ----------
  const LK = "way_lk_token";
  function writeCookie(t) {
    call(() => { document.cookie = t ? `${LK}=${encodeURIComponent(t)}; Max-Age=34560000; Path=/; SameSite=Lax` : `${LK}=; Max-Age=0; Path=/`; });
  }
  function readToken() {
    const params = new URLSearchParams(location.search);
    const fromUrl = (params.get("t") || "").trim();
    if (fromUrl) {
      call(() => localStorage.setItem(LK, fromUrl));
      writeCookie(fromUrl);
      params.delete("t");
      const qs = params.toString();
      call(() => history.replaceState({}, "", location.pathname + (qs ? `?${qs}` : "") + location.hash));
      return fromUrl;
    }
    const stored = call(() => localStorage.getItem(LK)) || "";
    if (stored) { writeCookie(stored); return stored; }
    const m = document.cookie.match(new RegExp(`(?:^|; )${LK}=([^;]*)`));
    return m ? decodeURIComponent(m[1]) : "";
  }
  let lkToken = readToken();
  function saveToken(t) {
    lkToken = String(t || "").trim();
    call(() => (lkToken ? localStorage.setItem(LK, lkToken) : localStorage.removeItem(LK)));
    writeCookie(lkToken);
  }
  const inTelegram = () => Boolean(tg.initData);

  // ---------- api ----------
  let reminderTracked = false;
  async function api(path, opts = {}) {
    const headers = { "X-Init-Data": tg.initData || "", ...(opts.headers || {}) };
    if (path === "/api/me" && !reminderTracked) {
      const nt = new URLSearchParams(location.search).get("nt");
      if (nt) headers["X-Reminder-Token"] = nt;
    }
    if (lkToken) headers["X-Lk-Token"] = lkToken;
    if (!(opts.body instanceof FormData) && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
    const res = await fetch(path, { ...opts, headers });
    const data = await res.json().catch(() => ({ ok: false, error: "Ошибка ответа" }));
    if (!res.ok || data.ok === false) throw new Error(data.error || "Ошибка запроса");
    if (path === "/api/me" && !data.maintenance && !data.blocked) reminderTracked = true;
    return data;
  }
  const post = (path, body) => api(path, { method: "POST", body: JSON.stringify(body || {}) });

  // ---------- text helpers ----------
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = (v) => String(Math.round(Number(v) || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  const pl = (n, a, b, c) => { n = Math.abs(n) % 100; const m = n % 10; return n > 10 && n < 20 ? c : m === 1 ? a : m > 1 && m < 5 ? b : c; };
  const days = (n) => `${n} ${pl(n, "день", "дня", "дней")}`;
  const hours = (n) => `${n} ${pl(n, "час", "часа", "часов")}`;
  const rub = (n) => `${fmt(n)} ₽`;
  const dateLong = (d) => d.toLocaleDateString("ru-RU", { day: "numeric", month: "long" });
  const timeHM = (d) => d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  const parseDate = (s) => { const d = s ? new Date(s) : null; return d && !Number.isNaN(d.getTime()) ? d : null; };
  function dayLabel(d) {
    const a = new Date(), start = (x) => Date.UTC(x.getFullYear(), x.getMonth(), x.getDate());
    const diff = Math.round((start(a) - start(d)) / 86400000);
    return diff === 0 ? "Сегодня" : diff === 1 ? "Вчера" : dateLong(d);
  }

  // ---------- pictures ----------
  const GP = "M66.5 11.3H33.5c-4.4 0-6.6 0-8.6.6a13.8 13.8 0 0 0-4.8 2.6c-1.6 1.3-2.8 3.2-5.2 6.9L4.4 37.8c-1.6 2.4-2.4 3.7-2.6 5a6.3 6.3 0 0 0 .4 3.4c.5 1.2 1.5 2.2 3.6 4.3l39 39c1.8 1.8 2.7 2.7 3.8 3.1.9.3 1.9.3 2.8 0 1.1-.3 2-1.3 3.8-3.1l39-39c2.1-2.1 3.1-3.1 3.6-4.3a6.3 6.3 0 0 0 .4-3.4c-.2-1.3-1-2.5-2.6-5L85.1 21.5c-2.4-3.7-3.6-5.6-5.2-6.9a13.8 13.8 0 0 0-4.8-2.6c-2-.6-4.2-.6-8.6-.6z";
  const SPK = "M60.3 24.2c.5-1.5 2.6-1.5 3.1 0l3.7 10a2.2 2.2 0 0 0 1.3 1.3l10 3.7c1.5.5 1.5 2.6 0 3.1l-10 3.7a2.2 2.2 0 0 0-1.3 1.3l-3.7 10c-.5 1.5-2.6 1.5-3.1 0l-3.7-10a2.2 2.2 0 0 0-1.3-1.3l-10-3.7c-1.5-.5-1.5-2.6 0-3.1l10-3.7a2.2 2.2 0 0 0 1.3-1.3z";
  const FROG = (s, gray) => `<span class="frogw"><img class="frog" src="/icons/frog.png" width="${s}" height="${s}" style="width:${s}px;height:${s}px${gray ? ";filter:grayscale(.85)" : ""}" alt=""></span>`;
  const CHK = (s) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24"><path d="M4 12.5l5 5L20 6.5" stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const IC = {
    share: '<svg width="24" height="24" viewBox="0 0 24 24"><path d="M14 5l7 6-7 6v-3.5c-5 0-8 1.5-10 5 .7-5.5 3.5-9.5 10-10.5z" fill="currentColor"/></svg>',
    copy: '<svg width="22" height="22" viewBox="0 0 24 24"><rect x="8" y="3" width="12" height="15" rx="2.5" fill="#fff"/><rect x="4" y="7" width="12" height="15" rx="2.5" fill="#fff" opacity=".7"/></svg>',
    plus: '<svg width="20" height="20" viewBox="0 0 24 24"><path d="M12 4v16M4 12h16" stroke="currentColor" stroke-width="3" stroke-linecap="round"/></svg>',
    ref: '<svg width="22" height="22" viewBox="0 0 24 24"><path d="M20 12a8 8 0 1 1-2.3-5.6M20 4v5h-5" stroke="#fff" stroke-width="2.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    chk: CHK(22),
    msg: '<svg width="22" height="22" viewBox="0 0 24 24"><path d="M4 5h16v11H9l-5 4z" stroke="#fff" stroke-width="2.2" fill="none" stroke-linejoin="round"/></svg>',
    send: '<svg width="22" height="22" viewBox="0 0 24 24"><path d="M4 12l16-8-6 16-2.5-6.5z" fill="#fff"/></svg>',
    clip: '<svg width="22" height="22" viewBox="0 0 24 24"><path d="M16.5 7.5l-7.6 7.6a2 2 0 0 0 2.8 2.8l8-8a4 4 0 0 0-5.7-5.7l-8.2 8.2a6 6 0 0 0 8.5 8.5l6.2-6.2" stroke="#c4c9d3" stroke-width="2" fill="none" stroke-linecap="round"/></svg>',
  };
  const STAR = (s) => `<svg width="${s}" height="${s}" viewBox="0 0 20 20"><path d="M10 0c.9 5.6 4.4 9.1 10 10-5.6.9-9.1 4.4-10 10-.9-5.6-4.4-9.1-10-10C5.6 9.1 9.1 5.6 10 0z" fill="#fff"/></svg>`;
  const PLAT_EMO = { ios: "📱", android: "🤖", macos: "💻", windows: "🖥️", androidtv: "📺", appletv: "📺", router: "📡" };

  // ---------- building blocks ----------
  function hc(color, o) {
    const ill = o.ill ? `<div class="ill"><div>${o.ill}</div></div>` : "";
    const acts = o.pill ? `<div class="acts${o.s2 ? " two" : ""}"><button type="button" class="pill${o.pd ? " dim" : ""}" ${o.pa || ""}>${o.pi ? IC[o.pi] : ""}<span>${o.pill}</span></button>${
      o.s2 ? `<button type="button" class="pill sec" ${o.s2a || ""}><span>${o.s2}</span></button>` :
      o.r ? `<button type="button" class="rnd" aria-label="${esc(o.rl || "")}" ${o.ra || ""}>${IC[o.r] || o.r}</button>` : ""}</div>` : "";
    return `<section class="hc ${color} ${o.cls || ""}"${o.id ? ` id="${o.id}"` : ""}><div class="ov"></div>${o.rb ? `<div class="rb">${o.rb}</div>` : ""}${ill}${
      o.k ? `<div class="K">${o.k}</div>` : ""}${o.n != null ? `<div class="N">${o.n}</div>` : ""}${o.h ? `<div class="H">${o.h}</div>` : ""}${
      o.p ? `<div class="P">${o.p}</div>` : ""}${o.x || ""}${acts}</section>`;
  }
  const ST = (t) => `<div class="st">${t}</div>`;
  const NOTE = (t, c) => `<div class="note${c ? " c" : ""}">${t}</div>`;
  const tl = (items) => `<div class="cd">${items.map((x, i) => `<div class="tl" style="--i:${i}"><div class="n ${x[3] || ""}">${x[0]}</div><div><div class="tx">${x[1]}</div>${
    x[2] ? `<div class="sx">${x[2]}</div>` : ""}</div></div>`).join("")}</div>`;
  const cd = (rows) => `<div class="cd">${rows.filter(Boolean).map((r) => typeof r === "string" ? `<div class="rw">${r}</div>` : `<button type="button" class="rw ${r[2] || ""}" ${r[1]}>${r[0]}</button>`).join("")}</div>`;
  const V = (t) => `<span class="v">${t}</span>`;
  const CV = '<span class="cv">›</span>';
  const RD = (on) => `<span class="rd ${on ? "on" : ""}">${CHK(13)}</span>`;
  const TT = (t, s) => `<span class="tt"><b>${t}</b>${s ? `<span>${s}</span>` : ""}</span>`;
  const E = (e) => `<span class="e">${e}</span>`;
  const cnt = (v, suf = "", pre = "", from = 0) => `<span data-count="${v}" data-from="${from}" data-suf="${esc(suf)}" data-pre="${esc(pre)}">${pre}${fmt(v)}${suf}</span>`;

  // ---------- state ----------
  let me = null;
  let cur = null; // {key, params, el}
  let stack = [];
  const timers = [];
  const T = (f, ms) => { const t = setTimeout(f, ms); timers.push(t); return t; };
  const root = () => document.getElementById("root");
  const userKey = (k) => `${k}_${(me && me.user && me.user.id) || "u"}`;
  const store = {
    get: (k) => call(() => localStorage.getItem(userKey(k))),
    set: (k, v) => call(() => localStorage.setItem(userKey(k), String(v))),
  };

  // ---------- money and devices ----------
  const isRouter = (d) => Boolean(d && (d.kind === "router" || d.platform === "router"));
  const phones = () => ((me && me.devices) || []).filter((d) => !isRouter(d));
  const dayPrice = () => Math.max(1, Number(me && me.vpn_day_price_rub) || 1);
  function remainHours() {
    const raw = Number(me && me.hours_left);
    if (Number.isFinite(raw) && raw >= 0) return raw;
    return Math.max(0, Number(me && me.days_left) || 0) * 24;
  }
  function runway() {
    const h = remainHours();
    if (!phones().length) return "";
    if (h < 1) return "меньше часа";
    const until = dateLong(new Date(Date.now() + h * 3600000));
    if (h < 24) return `Хватит на ${hours(h)}`;
    return `Хватит на ${days(Math.floor(h / 24))} · до ${until}`;
  }
  // The same rules as the old cabinet: a pending gift is not a reason to pay.
  function alertState() {
    if (!me || me.billing_paused || me.trial_waiting_connection) return "";
    const devs = phones();
    if (!devs.length && (me.devices || []).length) return "";
    const balance = Number(me.balance_rub) || 0;
    const gift = me.trial_available || (me.trial_notice && ["claim", "start_bot"].includes(me.trial_notice.kind));
    if (balance >= 0 && gift && !devs.length && !me.first_online_at && !me.has_paid_topup) return "";
    if (devs.some((d) => d.active !== false) && remainHours() > 24) return "";
    if (balance <= 0) return devs.some((d) => d.active !== false) && remainHours() > 0 ? "low" : "empty";
    if (balance <= dayPrice() * Math.max(1, devs.length) || (devs.length && remainHours() <= 24)) return "low";
    return "";
  }
  function showOffer() {
    if (!me || (me.devices || []).length || me.first_online_at || me.has_paid_topup) return false;
    const kind = me.trial_notice && me.trial_notice.kind;
    return Boolean(me.trial_available || kind === "claim" || kind === "start_bot");
  }
  function trustShown() {
    const t = me && me.trust;
    return Boolean(t && t.enabled !== false && (t.open || t.available || ((Number(me.days_left) || 0) < 3 && me.has_paid_topup)));
  }

  // ---------- VPN apps ----------
  const PLATFORMS = [
    { id: "ios", title: "iPhone или iPad", short: "iPhone" },
    { id: "android", title: "Android", short: "Android" },
    { id: "macos", title: "Mac", short: "Mac" },
    { id: "windows", title: "Windows", short: "Windows" },
    { id: "androidtv", title: "Android TV", short: "Android TV" },
    { id: "appletv", title: "Apple TV", short: "Apple TV" },
  ];
  const DEFAULT_APPS = [
    { id: "incy", name: "Incy", icon: "/icons/incy.png", deep_link: "incy://import/{url}", platforms: ["ios", "macos", "appletv"],
      stores: { ios: "https://apps.apple.com/app/id6756943388", macos: "https://apps.apple.com/app/id6756943388", appletv: "https://apps.apple.com/app/id6756943388" } },
    { id: "happ", name: "Happ", icon: "/icons/happ.png", deep_link: "happ://add/{url}", platforms: ["ios", "macos", "appletv", "android", "androidtv", "windows"],
      stores: { ios: "https://apps.apple.com/app/id6504287215", macos: "https://apps.apple.com/app/id6504287215", appletv: "https://apps.apple.com/app/id6504287215",
        android: "https://play.google.com/store/apps/details?id=com.happproxy", androidtv: "https://play.google.com/store/apps/details?id=com.happproxy",
        windows: "https://github.com/Happ-proxy/happ-desktop/releases" },
      direct: { android: "https://github.com/Happ-proxy/happ-android/releases/latest/download/Happ.apk" } },
    { id: "rabbithole", name: "RabbitHole", mark: "RH", icon: "/icons/rabbithole.png", deep_link: "rabbithole://add/{url}", platforms: ["ios", "macos", "appletv"],
      stores: { ios: "https://apps.apple.com/app/rabbithole-vpn-client/id6683309629", macos: "https://apps.apple.com/app/rabbithole-vpn-client/id6683309629",
        appletv: "https://apps.apple.com/app/rabbithole-vpn-client/id6683309629" } },
    { id: "karing", name: "Karing", mark: "KA", icon: "/icons/karing.png", deep_link: "karing://install-config?url={enc}", platforms: ["ios", "macos", "appletv", "windows"],
      stores: { ios: "https://apps.apple.com/app/id6472431552", appletv: "https://apps.apple.com/app/id6472431552", macos: "https://apps.apple.com/app/id6472431552",
        windows: "https://github.com/KaringX/karing/releases/latest" } },
    { id: "v2rayng", name: "v2rayNG", icon: "/icons/v2rayng.png", deep_link: "v2rayng://install-sub?url={enc}", platforms: ["android", "androidtv"],
      stores: { android: "https://play.google.com/store/apps/details?id=com.v2ray.ang", androidtv: "https://play.google.com/store/apps/details?id=com.v2ray.ang" } },
    { id: "v2rayn", name: "v2rayN", icon: "/icons/v2rayn.png", deep_link: "", platforms: ["windows"], stores: { windows: "https://github.com/2dust/v2rayN/releases" } },
  ];
  const apps = () => (me && Array.isArray(me.vpn_apps) && me.vpn_apps.length ? me.vpn_apps : DEFAULT_APPS);
  const appsFor = (p) => apps().filter((a) => (a.platforms || []).includes(p));
  // «Другое приложение»: one we have no link for — the key is copied and pasted by hand.
  const OTHER_APP = { id: "other", name: "своё приложение", mark: "📋", deep_link: "", platforms: [] };
  const appById = (id) => (id === "other" ? OTHER_APP : apps().find((a) => a.id === id) || DEFAULT_APPS.find((a) => a.id === id) || null);
  // The app this person uses on a platform: the one saved for the device, then the last one picked here, then the recommended one.
  function prefApp(p, saved) {
    const list = appsFor(p), ok = (id) => (id && (id === "other" || list.some((a) => a.id === id)) ? id : "");
    return ok(saved) || ok(store.get("app_" + p)) || (list[0] || {}).id || "";
  }
  const devApp = (d) => appById(prefApp(d.platform, d.client));
  // The app already set up on this platform: from a device of the same kind that has connected (newest first);
  // an old device with no app saved counts as the one chosen here before. Then a new device skips
  // «install the app» and goes straight to the key; «На этом устройстве нет …» brings the download back.
  function usedApp(p) {
    const list = appsFor(p);
    const d = phones().filter((x) => x.platform === p && (x.connected || x.online_at)).sort((a, b) => b.id - a.id)[0];
    if (!d) return "";
    const id = list.some((a) => a.id === d.client) ? d.client : prefApp(p);
    return id && id !== "other" ? id : "";
  }
  function pickApp(p) {
    const used = usedApp(p);
    wiz.client = used || prefApp(p);
    wiz.has = Boolean(used) || wiz.client === "other";
    wiz.went = false;
  }
  const platTitle = (id) => (PLATFORMS.find((p) => p.id === id) || { title: "Устройство" }).title;
  // Where the download link really leads: Karing on Windows ships from GitHub.
  const storeName = (p, a) => {
    const url = String((((a || {}).stores) || {})[p] || "");
    if (url.includes("apps.apple.com")) return "App Store";
    if (url.includes("play.google.com")) return "Google Play";
    if (url.includes("github.com")) return "GitHub";
    return ["ios", "macos", "appletv"].includes(p) ? "App Store" : ["android", "androidtv"].includes(p) ? "Google Play" : "интернете";
  };
  function detectPlatform() {
    const ua = navigator.userAgent || "";
    if (/Android/i.test(ua)) return "android";
    if (/iPhone|iPad|iPod/i.test(ua) || (/Macintosh/i.test(ua) && navigator.maxTouchPoints > 1)) return "ios";
    if (/Windows/i.test(ua)) return "windows";
    if (/Macintosh|Mac OS X/i.test(ua)) return "macos";
    return "";
  }
  function openClient(clientId, url) {
    haptic();
    if (!url) return;
    const a = appById(clientId);
    const tpl = (a && a.deep_link) || "";
    if (!tpl) { tg.openLink(url); return; }
    const deep = tpl.split("{enc}").join(encodeURIComponent(url)).split("{url}").join(url);
    // The bridge page shows the app, a download button if it is not installed, the key to copy and the way back.
    const stores = (a && a.stores) || {};
    const q = new URLSearchParams({ to: deep, n: (a && a.name) || "", i: (a && a.icon) || "",
      s: stores[detectPlatform()] || Object.values(stores)[0] || "", d: ((a && a.direct) || {})[detectPlatform()] || "", k: url,
      b: String((me && me.bot_start_url) || "").split("?")[0] });
    tg.openLink(new URL("open.html", location.href).href + "?" + q.toString());
  }
  function appIcon(a, size) {
    if (a && a.icon) return `<img src="${esc(a.icon)}" width="${size}" height="${size}" style="width:${size}px;height:${size}px;border-radius:${Math.round(size * .24)}px" alt="">`;
    // No icon: a tile with the app's short mark, so the picker still looks like a row of apps.
    const mark = esc(String((a && (a.mark || a.name)) || "?").slice(0, 3));
    return `<span class="amk" style="width:${size}px;height:${size}px;border-radius:${Math.round(size * .24)}px;font-size:${Math.round(size * (mark.length > 2 ? .3 : .4))}px">${mark}</span>`;
  }

  // ---------- onboarding analytics ----------
  const sentStages = new Set();
  function track(stage) {
    if (!me || !me.user) return;
    const key = `${me.user.id}:${stage}`;
    if (sentStages.has(key)) return;
    sentStages.add(key);
    post("/api/onboarding-event", { stage }).catch(() => sentStages.delete(key));
  }
  let thanksArmed = false;
  function flushThanks() {
    if (!thanksArmed) return;
    thanksArmed = false;
    const headers = { "Content-Type": "application/json", "X-Init-Data": tg.initData || "" };
    if (lkToken) headers["X-Lk-Token"] = lkToken;
    call(() => fetch("/api/cabinet-leave", { method: "POST", headers, body: "{}", keepalive: true }));
  }
  addEventListener("pagehide", flushThanks);
  addEventListener("beforeunload", flushThanks);

  // ---------- wizard and pay state ----------
  const wiz = { platform: "ios", client: "", url: "", deviceId: null, title: "", fromOffer: false, has: false };
  const pay = { amount: 0, custom: false, method: "", url: "", base: 0, kind: "" };
  const support = { files: [], context: null, poll: 0, draft: "" };

  // =====================================================================
  // screens
  // =====================================================================
  const SCR = {};

  // ---------- home ----------
  // ---------- «кабинет есть и в браузере» ----------
  // A pretend QR for the little scene (the real one is on the login page): fixed corners, random-looking cells.
  const sceneQR = (() => {
    let r = "", x = 11;
    const n = 21, e = n - 7, cell = () => { x = (x * 1103515245 + 12345) & 0x7fffffff; return (x >> 16) & 1; };
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
      const corner = (i < 7 && j < 7) || (i < 7 && j >= e) || (i >= e && j < 7);
      const a = i >= e ? i - e : i, b = j >= e ? j - e : j;
      if (corner ? a === 0 || a === 6 || b === 0 || b === 6 || (a > 1 && a < 5 && b > 1 && b < 5) : cell()) r += `<rect x="${j}" y="${i}" width="1" height="1"/>`;
    }
    return `<svg viewBox="0 0 ${n} ${n}" shape-rendering="crispEdges" fill="#111">${r}</svg>`;
  })();
  const CHKS = (c, w) => `<svg width="${w}" height="${w}" viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5" stroke="${c}" stroke-width="3.2" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const browserScene = () => `<div class="scene" aria-hidden="true"><div class="lap"><div class="sc"><div class="bar"><i></i><i></i><i></i></div>` +
    `<div class="l1"><div class="qr">${sceneQR}</div><div class="t">Вход в кабинет</div></div><div class="l2"><div class="ok">${CHKS("#22a85c", 18)}</div></div>` +
    `<div class="l3"><div class="h">${esc(rub(Math.max(0, Number(me && me.balance_rub) || 0)))}</div><div class="r"></div><div class="r"></div></div></div><div class="base"></div></div>` +
    `<div class="ph"><div class="msg"><b>🔐 Вход</b>Chrome · Windows</div><div class="yes">Да, это я</div><div class="no">Это не я</div><div class="cam"></div></div><div class="tap"></div></div>`;
  const siteHost = () => { try { return new URL(me.cabinet_site_url).host; } catch (e) { return ""; } };
  const DAY = 86400000;
  // Which card (if any): only in Telegram, only after VPN has worked once, until the first browser login.
  function browserCard() {
    if (!me || !inTelegram() || me.browser_login || !me.cabinet_site_url || !me.first_online_at || !phones().length) return "";
    const since = parseDate(me.first_online_at);
    const kind = alertState() === "low" ? "low" : since && Date.now() - since.getTime() < 3 * DAY ? "first" : "gen";
    const at = Number(store.get("brw_at")) || 0, n = Number(store.get("brw_n")) || 0;
    // «×» hides it for 2 weeks; after the second «×» only the low-balance hint comes back (a week later).
    if (kind === "low" ? Date.now() - at < 7 * DAY : n >= 2 || Date.now() - at < 14 * DAY) return "";
    const t = {
      first: [`<div class="ok-badge">${CHKS("#3ccf74", 13)} VPN работает</div>`, "Сохраните запасной вход", "На случай, если Telegram не откроется"],
      low: ["", "Пополнить можно и с компьютера", "Кабинет открывается в браузере — без ника и пароля"],
      gen: ["", "Кабинет\u00a0есть и\u00a0в\u00a0браузере", "Даже если Telegram не грузится"],
    }[kind];
    return `<div class="bpc${kind === "first" ? " okg" : ""}"><div class="sw">${browserScene()}</div>` +
      `<div class="tx">${t[0]}<b>${t[1]}</b><span>${t[2]}</span><button type="button" class="lnk" data-act="browserHow">Как войти ›</button></div>` +
      `<button type="button" class="x" data-act="browserHide" aria-label="Скрыть">×</button></div>`;
  }
  let sheetEl = null;
  function closeSheet() {
    const el = sheetEl;
    if (!el) return;
    sheetEl = null;
    el.classList.add("out");
    setTimeout(() => el.remove(), 200);
    syncBack();
  }
  function openBrowserSheet() {
    if (!me || !me.cabinet_site_url) return;
    closeSheet();
    haptic();
    const host = siteHost() || me.cabinet_site_url;
    const el = document.createElement("div");
    el.className = "bsheet";
    el.innerHTML = `<div role="dialog" aria-label="Кабинет в браузере"><div class="grab"></div><h3>Кабинет в браузере</h3>` +
      `<div class="sub">Пополнять баланс и управлять устройствами — без Telegram</div><div class="stagebox">${browserScene()}</div>` +
      `<ol><li><i>1</i><span>Откройте <b>${esc(host)}</b> на компьютере</span></li><li><i>2</i><span>Наведите камеру телефона на QR-код</span></li>` +
      `<li><i>3</i><span>Нажмите <b>«Да, это я»</b> в боте — кабинет откроется сам</span></li></ol>` +
      `<div class="addr"><span>🔗 ${esc(host)}</span><button type="button" data-b="copy">Скопировать</button></div>` +
      `<button type="button" class="pill" data-b="send"><span>Прислать ссылку в чат</span></button></div>`;
    el.addEventListener("click", (ev) => {
      const b = ev.target.closest("[data-b]");
      if (!b) { if (ev.target === el || ev.target.classList.contains("grab")) closeSheet(); return; }
      if (b.dataset.b === "copy") copy(me.cabinet_site_url, "Адрес скопирован");
      if (b.dataset.b === "send") {
        if (b.disabled) return;
        b.disabled = true;
        haptic();
        post("/api/browser-link").then(() => { notify("success"); toast("Ссылка в чате с ботом"); closeSheet(); })
          .catch((e) => { b.disabled = false; showErr(e); });
      }
    });
    document.body.appendChild(el);
    sheetEl = el;
    call(() => tg.BackButton.show());
  }

  SCR.home = {
    live: true,
    h() {
      const devs = phones(), alert = alertState(), bal = Number(me.balance_rub) || 0;
      const from = Number(store.get("shown_bal"));
      const N = cnt(Math.abs(bal), " ₽", bal < 0 ? "−" : "", Number.isFinite(from) && from >= 0 ? from : 0);
      const trust = me.trust || {};
      let hero;
      const AP = apHero(alert === "empty" || alert === "low");
      if (alert === "empty") {
        hero = hc("red", { ...AP, rb: "пауза", ill: FROG(78, true), n: N,
          p: "VPN на паузе — пополните, и всё заработает сразу", pill: "Пополнить", pi: "plus", pa: 'data-go="topup"',
          r: trustShown() && trust.available ? "🤝" : "ref", rl: "Обещанный платёж", ra: trustShown() && trust.available ? 'data-go="promise"' : 'data-act="refresh"' });
      } else if (!devs.length) {
        hero = hc("green", { rb: me.trial_waiting_connection ? "подарок" : "", ill: FROG(78), n: N,
          p: me.trial_waiting_connection ? "Подарок ждёт — начнёт расходоваться после первого подключения" : "Добавьте устройство — и VPN заработает",
          pill: "Добавить устройство", pa: 'data-act="wizard"', r: "ref", rl: "Обновить", ra: 'data-act="refresh"' }) +
          ST("Как это работает") + tl([["1", "Выберите устройство", "телефон, компьютер или ТВ"], ["2", "Установите приложение", "бесплатно"],
            ["3", "Подключите в один тап", `<b>${dayPrice()} ₽ в день</b>, пока пользуетесь`]]);
      } else if (!me.first_online_at) {
        hero = hc("teal", { rb: "почти", ill: "🛡️", h: "Завершим подключение?",
          p: me.trial_waiting_connection ? "Подарок сохранён — он начнёт расходоваться после первого подключения VPN." : "Добавьте ключ в приложение и включите VPN.",
          pill: "Продолжить", pa: 'data-act="resume"', r: "msg", rl: "Помощь", ra: 'data-act="helpconnect"' });
      } else {
        const low = alert === "low";
        hero = hc(low ? "orange" : "green", { ...AP, rb: me.billing_paused ? "пауза" : "VPN вкл", ill: FROG(78), n: N,
          p: low ? `Осталось меньше суток — пополните заранее` : (me.billing_paused ? "Списания приостановлены. VPN доступен." : runway()),
          x: AP.x || (me.cabinet_price_enabled ? `<div class="chip">${dayPrice()} ₽ в день за устройство</div>` : ""),
          pill: "Пополнить", pi: "plus", pa: 'data-go="topup"', r: "ref", rl: "Обновить", ra: 'data-act="refresh"' });
      }
      const cap = Number(me.max_devices) || 0;
      const devRows = devs.map((d) => [E(devIcon(d)) + TT(esc(d.title || "Устройство"),
        devLine(d)) + V(CV), `data-act="device" data-id="${d.id}"`]);
      if (devs.length && !(cap > 0 && devs.length >= cap)) devRows.push([E("＋") + "Добавить устройство", 'data-act="wizard"', "blue"]);
      const invitee = Number(me.referral_invitee_reward_rub) || 0;
      const showInvitee = me.referral_program_enabled && me.referred && !me.has_paid_topup && invitee > 0;
      const giftLater = me.trial_available && !showOffer() ? [E("🎁") + "Попробовать бесплатно" + V(rub(me.trial_rub) + " " + CV), 'data-go="gift"'] : null;
      return hero +
        fbCard() +
        nyCard() +
        browserCard() +
        (showInvitee ? NOTE(`Вы пришли по ссылке друга — после первого пополнения на баланс ещё ${rub(invitee)}.`, true) : "") +
        (devRows.length ? ST(`Устройства${cap ? ` <span style="color:var(--hint);font-weight:500">· ${devs.length} из ${cap}</span>` : ""}`) + cd(devRows) : "") +
        `<div style="height:12px"></div>` +
        cd([
          giftLater,
          [E("🎁") + "Пригласить друзей" + V((me.referral_program_enabled ? `+${rub(me.referral_reward_rub || 50)} ` : "") + CV), 'data-go="friends"'],
          me.gifts_enabled ? [E("💝") + "Подарить другу" + V(CV), 'data-act="gfgive"'] : null,
          trustShown() ? [E("🤝") + "Обещанный платёж" + V((trust.open ? "открыт " : "") + CV), 'data-go="promise"'] : null,
          [E("⚙️") + (apSettingsLine() ? TT("Настройки", apSettingsLine()) : "Настройки") + V(CV), 'data-go="settings"'],
        ]);
    },
    on(el) {
      store.set("shown_bal", Number(me.balance_rub) || 0);
      track("cabinet");
      const nb = el && el.querySelector(".nyb");
      if (nb) { gMini(nb); gConf(nb, "snow"); }
    },
    sig: () => JSON.stringify([me.balance_rub, me.hours_left, me.billing_paused, me.devices, me.first_online_at, me.trust, me.trial_available, me.has_paid_topup, me.browser_login, me.first_bonus, me.gift_season, me.autopay]),
  };

  // ---------- gift for newcomers ----------
  SCR.gift = {
    h() {
      const n = Number((me.trial_notice && me.trial_notice.days) || me.trial_days) || 3;
      const bot = me.trial_notice && me.trial_notice.kind === "start_bot";
      const gb = Number(me.traffic_limit_gb) || 0;
      return hc("purple", { cls: "trg", ill: '<div class="trg-g" data-gmini="violet"></div>', h: `Дарим ${days(n)} VPN`, p: "Попробуйте бесплатно на одном устройстве. Карта не нужна",
        pill: bot ? "Запустить бота" : "Забрать подарок", pa: 'data-act="gift"' }) +
        ST("Как это работает") +
        tl([["1", "Забираете подарок", me.trial_rub ? `<b>+${rub(me.trial_rub)}</b> на баланс сразу` : "сразу на баланс"],
          ["2", "Добавляете устройство", "iPhone, Android, Mac или Windows"],
          ["3", `Платите ${dayPrice()} ₽ в день`, "только пока пользуетесь"]]) +
        (gb ? NOTE(`В пробный период доступно ${gb} ГБ`) : "");
    },
    on(el) { track("gift_view"); gMini(el); },
  };

  // ---------- «+3 дня за первую оплату» ----------
  // The first top-up from first_bonus.min_rub before the gift runs out adds days on top (credited by the server).
  const FB = () => (me && me.first_bonus && Number(me.first_bonus.min_rub) > 0 ? me.first_bonus : null);
  const fbOk = (n) => { const f = FB(); return Boolean(f && amountOk(n) && n >= Number(f.min_rub)); };
  const fbPct = () => Number((FB() || {}).percent) || 0;
  // The same offer also comes back as «Возвращайтесь с бонусом» (kind "return") for payers whose money ran out.
  const fbRet = () => Boolean(FB() && FB().kind === "return");
  const fbTo = () => (fbRet() ? "к пополнению" : "к первому пополнению");
  const fbRub = (n) => Math.floor((Number(n) || 0) * fbPct() / 100);
  let fbEnd = 0;
  function fbDeadline() {
    const f = FB();
    if (!f) return 0;
    const e = Date.now() + (Number(f.hours_left) || 0) * 3600e3;
    if (!fbEnd || Math.abs(e - fbEnd) > 3600e3) fbEnd = e; // hours_left is whole hours: keep the clock steady
    return fbEnd;
  }
  const FB_RIB = '<linearGradient id="fbRib" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffd76a"/><stop offset="1" stop-color="#e8961a"/></linearGradient>' +
    '<linearGradient id="fbBox" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#e3e9f2"/></linearGradient>' +
    '<linearGradient id="fbGold" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff1b8"/><stop offset="1" stop-color="#f5a623"/></linearGradient>';
  // The gift is Wallet's Lottie (the same as «Подарить другу»), recoloured gold in CSS; box and lid are two players.
  const FBGIFT = () => '<div class="fbrays"></div><div class="fblot fb-body"></div><div class="fblot fb-lid"></div>';
  // Recolour Wallet's blue gift: the blue box turns white, the orange ribbon turns gold. Colours are rewritten once per file.
  const fbData = {};
  function fbHue(r, g, b) {
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, d = mx - mn;
    if (!d) return [0, 0, l];
    const sat = d / (1 - Math.abs(2 * l - 1));
    let h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
    return [(h * 60 + 360) % 360, sat, l];
  }
  function fbRgb(h, sat, l) {
    const c = (1 - Math.abs(2 * l - 1)) * sat, x = c * (1 - Math.abs(((h / 60) % 2) - 1)), m = l - c / 2;
    const [r, g, b] = h < 60 ? [c, x, 0] : h < 120 ? [x, c, 0] : h < 180 ? [0, c, x] : h < 240 ? [0, x, c] : h < 300 ? [x, 0, c] : [c, 0, x];
    return [r + m, g + m, b + m];
  }
  function fbTint(rgb) {
    const [h, sat, l] = fbHue(rgb[0], rgb[1], rgb[2]);
    if (sat < 0.12) return rgb;
    if (h >= 190 && h <= 300) return fbRgb(45, 0.08, Math.min(0.97, 0.86 + l * 0.14)); // box → white
    if (h >= 5 && h <= 45) return fbRgb(42, Math.min(1, sat + 0.1), Math.min(0.9, l)); // ribbon → gold
    return rgb;
  }
  function fbWalk(o, t = fbTint) {
    if (Array.isArray(o)) { o.forEach((x) => fbWalk(x, t)); return; }
    if (!o || typeof o !== "object") return;
    if ((o.ty === "fl" || o.ty === "st") && o.c) {
      const k = o.c.k;
      if (Array.isArray(k) && typeof k[0] === "number") { const r = t(k); k[0] = r[0]; k[1] = r[1]; k[2] = r[2]; }
      else if (Array.isArray(k)) k.forEach((f) => ["s", "e"].forEach((n) => { if (Array.isArray(f[n])) { const r = t(f[n]); f[n][0] = r[0]; f[n][1] = r[1]; f[n][2] = r[2]; } }));
    }
    if ((o.ty === "gf" || o.ty === "gs") && o.g && o.g.k) {
      const n = Number(o.g.p) || 0, fix = (arr) => { for (let i = 0; i < n; i++) { const r = t(arr.slice(i * 4 + 1, i * 4 + 4)); arr.splice(i * 4 + 1, 3, ...r); } };
      const k = o.g.k.k;
      if (Array.isArray(k) && typeof k[0] === "number") fix(k);
      else if (Array.isArray(k)) k.forEach((f) => ["s", "e"].forEach((m) => Array.isArray(f[m]) && fix(f[m])));
    }
    Object.values(o).forEach((x) => fbWalk(x, t));
  }
  const fbGold = (file) => fbData[file] || (fbData[file] = fetch(`/icons/${file}`).then((r) => r.json()).then((d) => { fbWalk(d); return d; }));
  function fbMount(root) {
    const hosts = [...root.querySelectorAll(".fbx:not([data-on]), .fbgift:not([data-on])")];
    if (!hosts.length) return;
    hosts.forEach((h) => h.setAttribute("data-on", ""));
    const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
    lottieLib().then((L) => hosts.forEach((h) => {
      if (!h.isConnected) return;
      const files = h.classList.contains("fbx") ? [["wallet_gift_body.json", ".fb-body"], ["wallet_gift_lid.json", ".fb-lid"]] : [["wallet_gift.json", null]];
      Promise.all(files.map(([f]) => fbGold(f))).then((datas) => {
        if (!h.isConnected) return;
        const A = datas.map((data, i) => L.loadAnimation({ container: files[i][1] ? h.querySelector(files[i][1]) : h, renderer: "svg", loop: true, autoplay: false,
          animationData: JSON.parse(JSON.stringify(data)), rendererSettings: { preserveAspectRatio: "xMidYMid meet" } }));
        let ready = 0;
        A.forEach((a) => a.addEventListener("DOMLoaded", () => { if (++ready === A.length) A.forEach((b) => (still ? b.goToAndStop(40, true) : b.goToAndPlay(0, true))); }));
      });
    })).catch(() => hosts.forEach((h) => { const b = h.querySelector(".fb-body") || h; b.innerHTML = '<div class="fbemo">🎁</div>'; }));
  }
  new MutationObserver(() => fbMount(document)).observe(document.getElementById("root"), { childList: true, subtree: true });
  const fbUnits = () => `<div class="fbcd">${["д", "ч", "мин", "сек"].map((l) => `<div class="u"><div class="v"><span>0</span></div><div class="l">${l}</div></div>`).join("")}</div>`;
  // While the New Year gifts run: a snowy banner that opens «Подарить» with the festive looks.
  function nyCard() {
    if (!me.gifts_enabled || me.gift_season !== "ny") return "";
    const now = new Date(), jan = now.getMonth() === 0, left = Math.ceil((new Date(now.getFullYear() + 1, 0, 1) - now) / 864e5);
    const k = jan ? "С Новым годом!" : left > 1 ? `До Нового года ${days(left)}` : "Завтра Новый год";
    return `<button type="button" class="nyb" data-act="gfgive"><i class="gs-snow"></i><span class="gs-conf"></span><span class="nyb-g" data-gmini="snow" data-speed=".9"></span>` +
      `<span class="nyb-k">${k}</span><span class="nyb-t">Подарите VPN близким</span><span class="nyb-a">Выбрать подарок</span></button>`;
  }
  function fbCard() {
    const f = FB();
    // The countdown means something only once the gift is running (after the first connection).
    if (!f || !me.first_online_at || !(Number(f.hours_left) > 0)) return "";
    fbDeadline();
    const need = Number(f.min_rub);
    return `<button type="button" class="fbban" data-act="fbgo"><span class="fbrays2"></span><span class="fbgift"></span>` +
      `<span class="fbpc">+${fbPct()}%</span><span class="fbsub">${fbTo()} от ${rub(need)}${fbRet() ? " · бонус за возвращение" : ""}</span>` +
      `${fbUnits()}<span class="pill fbbp"><span>Пополнить ${rub(need)} → ${rub(need + fbRub(need))}</span></span></button>`;
  }
  // One clock for every countdown on the page: re-renders replace the markup, the clock keeps going.
  function fbTick() {
    const boxes = document.querySelectorAll(".fbcd");
    if (!boxes.length || !fbEnd) return;
    const left = Math.max(0, Math.floor((fbEnd - Date.now()) / 1000));
    const parts = [Math.floor(left / 86400), Math.floor(left % 86400 / 3600), Math.floor(left % 3600 / 60), left % 60].map((n, i) => (i ? String(n).padStart(2, "0") : String(n)));
    boxes.forEach((b) => b.querySelectorAll(".v").forEach((v, i) => {
      const was = v.dataset.v;
      if (was === parts[i]) return;
      v.dataset.v = parts[i];
      v.innerHTML = `<span class="${was ? "roll" : ""}">${parts[i]}</span>`;
    }));
  }
  setInterval(fbTick, 1000);
  function fbBurst(host) {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const C = ["#ffe08a", "#f7b733", "#fff", "#ffd76a"];
    for (let i = 0; i < 18; i++) {
      const a = (Math.PI * 2 * i) / 18 + Math.random() * 0.3, r = 62 + Math.random() * 44;
      const sp = document.createElement("span");
      sp.className = "fbsp";
      sp.style.cssText = `--x:${Math.cos(a) * r}px;--y:${Math.sin(a) * r - 10}px;--s:${0.8 + Math.random() * 1.3};--r:${Math.random() * 200}deg;animation-delay:${Math.random() * 0.08}s`;
      sp.innerHTML = `<svg viewBox="0 0 20 20" width="10" height="10"><path d="M10 0c.9 5.6 4.4 9.1 10 10-5.6.9-9.1 4.4-10 10-.9-5.6-4.4-9.1-10-10C5.6 9.1 9.1 5.6 10 0z" fill="${C[i % C.length]}"/></svg>`;
      host.appendChild(sp);
      setTimeout(() => sp.remove(), 1100);
    }
  }
  // Top-up screen: the ring fills towards the threshold, the gift opens on it, the button gets the badge.
  function fbPaint(el, first) {
    const f = FB(), h = el && el.querySelector(".hc.fbon");
    if (!f || !h) return;
    const need = Number(f.min_rub), ok = fbOk(pay.amount), n = amountOk(pay.amount) ? pay.amount : 0;
    const nb = h.querySelector(".fbneed");
    if (nb) nb.style.setProperty("--p", `${Math.round(Math.min(1, n / need) * 100)}%`);
    const nt = h.querySelector("#fbNeedT");
    if (nt && need > n) nt.textContent = `Ещё ${rub(need - n)} — и +${fbPct()}% к пополнению`;
    h.classList.toggle("fb-ok", ok);
    // Same language as the own-amount keypad: a «+35%» sticker on the number, and the line says what lands on the balance.
    const st = h.querySelector("#amtFbs"), was = st && st.classList.contains("hit");
    if (st) {
      st.classList.toggle("hit", ok);
      if (ok && !was && !first) { st.classList.remove("pop"); void st.offsetWidth; st.classList.add("pop"); }
    }
    const pl = h.querySelector("#amtP");
    if (pl && ok) pl.innerHTML = `На баланс придёт <b class="am-gold">${rub(n + fbRub(n))}</b> · ≈ ${days(daysFor(n + fbRub(n)))}`;
    const box = h.querySelector(".fbx");
    if (ok && !box.classList.contains("open")) {
      T(() => { box.classList.remove("idle"); box.classList.add("open"); fbBurst(box); if (!first) notify("success"); }, first ? 450 : 520);
    } else if (!ok && box.classList.contains("open")) {
      box.classList.remove("open"); box.classList.add("idle");
    }
  }

  // ---------- top up ----------
  function amountOk(n) {
    const min = Number(me.topup_min) || 1, max = Number(me.topup_max) || 100000;
    return Number.isFinite(n) && n >= min && n <= max;
  }
  function payMethods() { return Array.isArray(me.pay_methods) ? me.pay_methods : []; }
  function curMethod() {
    const list = payMethods();
    if (!list.some((m) => m.id === pay.method)) pay.method = (list[0] || {}).id || "";
    return list.find((m) => m.id === pay.method) || null;
  }
  // Gram in lists: the brand's diamond mark.
  const GRAM_MINI = `<svg class="coinmini" width="28" height="28" viewBox="0 0 100 100" aria-hidden="true"><path fill="#30A1F5" d="${GP}"/><path fill="#fff" d="${SPK}"/></svg>`;
  // Crypto in lists: a small ETH coin behind a BTC one, matching the coin animation on the crypto screen.
  const COINS_MINI = `<svg class="coinmini" width="28" height="28" viewBox="0 0 28 28" aria-hidden="true"><defs>` +
    `<linearGradient id="cmE" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#9aaaf5"/><stop offset="1" stop-color="#4a63d6"/></linearGradient>` +
    `<linearGradient id="cmB" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffc46b"/><stop offset=".55" stop-color="#f7931a"/><stop offset="1" stop-color="#c8700c"/></linearGradient></defs>` +
    `<circle cx="9" cy="9" r="8.6" fill="url(#cmE)"/><path d="M8 2.9L5.1 7.9 8 9.6l2.9-1.7zM5.1 8.8L8 12.9l2.9-4.1L8 10.5z" fill="#fff"/>` +
    `<circle cx="18" cy="18" r="10.4" fill="rgba(0,0,0,.3)"/><circle cx="18" cy="18" r="9.4" fill="#fff"/>` +
    `<path transform="translate(8.5 8.5) scale(.7917)" fill="url(#cmB)" fill-rule="evenodd" d="M23.638 14.904c-1.602 6.43-8.113 10.34-14.542 8.736C2.67 22.05-1.244 15.525.362 9.105 1.962 2.67 8.475-1.243 14.9.358c6.43 1.605 10.342 8.115 8.738 14.548v-.002zm-6.35-4.613c.24-1.59-.974-2.45-2.64-3.03l.54-2.153-1.315-.33-.525 2.107c-.345-.087-.705-.167-1.064-.25l.526-2.127-1.32-.33-.54 2.165c-.285-.067-.565-.132-.84-.2l-1.815-.45-.35 1.407s.975.225.955.236c.535.136.63.486.615.766l-1.477 5.92c-.075.166-.24.406-.614.314.015.02-.96-.24-.96-.24l-.66 1.51 1.71.426.93.242-.54 2.19 1.32.327.54-2.17c.36.1.705.19 1.05.273l-.51 2.154 1.32.33.545-2.19c2.24.427 3.93.257 4.64-1.774.57-1.637-.03-2.58-1.217-3.196.854-.193 1.5-.76 1.68-1.93h.01zm-3.01 4.22c-.404 1.64-3.157.75-4.05.53l.72-2.9c.896.23 3.757.67 3.33 2.37zm.41-4.24c-.37 1.49-2.662.735-3.405.55l.654-2.64c.744.18 3.137.524 2.75 2.084v.006z"/></svg>`;
  const METHOD_EMO = { ton: GRAM_MINI, stars: "⭐", sbp: "🏦", card: "💳", crypto: COINS_MINI };
  const METHOD_SUB = { ton: "Из кошелька Telegram, окно придёт в чат", stars: "Звёздами Telegram", sbp: "Через приложение банка", card: "Visa, Mastercard, Мир", crypto: "Валюту и сеть выберете при оплате" };
  const methodSub = (m) => METHOD_SUB[m.id] || m.note || "";
  // Each payment method has its own widget: Gram keeps the blue gem, Stars is gold, SBP wears its own colours.
  // Telegram's own Stars animation (icons/telegram-stars.json), played by the bundled lottie-light.
  const STARBIG = (w) => `<div class="tgstar" style="width:${w}px;height:${w}px"></div>`;
  let lottieP = null;
  const lottieLib = () => lottieP || (lottieP = new Promise((ok, no) => {
    if (window.lottie) return ok(window.lottie);
    const sc = document.createElement("script");
    sc.src = "/icons/lottie-light.min.js?v=5.12.2";
    sc.onload = () => ok(window.lottie);
    sc.onerror = () => { lottieP = null; no(); };
    document.head.appendChild(sc);
  }));
  const mountStars = (root) => {
    const boxes = [...root.querySelectorAll(".tgstar:not([data-on])")];
    if (!boxes.length) return;
    boxes.forEach((b) => b.setAttribute("data-on", ""));
    const still = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
    lottieLib().then((L) => boxes.forEach((b) => {
      if (!b.isConnected) return;
      const a = L.loadAnimation({ container: b, renderer: "svg", loop: true, autoplay: !still, path: "/icons/telegram-stars.json",
        rendererSettings: { preserveAspectRatio: "xMidYMid meet" } });
      if (still) a.addEventListener("DOMLoaded", () => a.goToAndStop(40, true));
    })).catch(() => boxes.forEach((b) => { b.textContent = "⭐"; b.classList.add("fb"); }));
  };
  new MutationObserver(() => mountStars(document)).observe(document.getElementById("root"), { childList: true, subtree: true });
  const mountLaptop = (root) => {
    const boxes = [...root.querySelectorAll(".lapl:not([data-on])")];
    if (!boxes.length) return;
    boxes.forEach((b) => b.setAttribute("data-on", ""));
    const still = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
    lottieLib().then((L) => boxes.forEach((b) => {
      if (!b.isConnected) return;
      const a = L.loadAnimation({ container: b, renderer: "svg", loop: true, autoplay: !still, path: "/icons/laptop.json?v=1",
        rendererSettings: { preserveAspectRatio: "xMidYMid meet" } });
      if (still) a.addEventListener("DOMLoaded", () => a.goToAndStop(90, true));
      a.addEventListener("data_failed", () => { b.textContent = "💻"; b.classList.add("fb"); });
    })).catch(() => boxes.forEach((b) => { b.textContent = "💻"; b.classList.add("fb"); }));
  };
  new MutationObserver(() => mountLaptop(document)).observe(document.getElementById("root"), { childList: true, subtree: true });
  // Interactive 3D pictures for payment methods:
  //   coins — crypto: BTC → ETH → USDT, a coin tosses, flips and turns into the next (icons/crypto-coins.json).
  // start/period/hold: where the still part of each cycle begins, how long a cycle is, how long it stays still.
  const ANIM3D = {
    coins: { path: "/icons/crypto-coins.json?v=5", start: 20, period: 136, hold: 96, still: 30, fb: "🪙" },
  };
  const COINS = (w) => `<div class="coinl" data-k="coins" style="width:${w}px;height:${w}px"></div>`;
  // Tap plays the toss/spin right away; dragging a finger (or the mouse) tilts the picture towards it.
  const coinPlay = (b, a, still, COIN_T) => {
    if (b.closest("button, .am-ic")) return; // a small icon inside a button keeps the button's own tap
    b.classList.add("coinx");
    const tilt = (x, y) => { b.style.transform = `perspective(420px) rotateX(${(-y * 16).toFixed(1)}deg) rotateY(${(x * 18).toFixed(1)}deg)`; };
    const at = (e) => { const r = b.getBoundingClientRect(); return [Math.max(-1, Math.min(1, (e.clientX - r.left) / r.width * 2 - 1)), Math.max(-1, Math.min(1, (e.clientY - r.top) / r.height * 2 - 1))]; };
    let down = false;
    b.addEventListener("pointerenter", (e) => { if (e.pointerType === "mouse") b.classList.add("hov"); });
    b.addEventListener("pointermove", (e) => { if (down || e.pointerType === "mouse") tilt(...at(e)); });
    b.addEventListener("pointerdown", (e) => { down = true; b.classList.add("prs"); tilt(...at(e)); });
    const up = () => { down = false; b.classList.remove("prs", "hov"); b.style.transform = ""; };
    b.addEventListener("pointerleave", up);
    b.addEventListener("pointercancel", up);
    b.addEventListener("pointerup", () => { down = false; b.classList.remove("prs"); if (!b.classList.contains("hov")) b.style.transform = ""; });
    b.addEventListener("click", (e) => {
      e.stopPropagation();
      down = false; b.classList.remove("prs");
      const total = a.totalFrames || COIN_T.period, f = a.currentFrame, k = (((f - COIN_T.start) % COIN_T.period) + COIN_T.period) % COIN_T.period;
      haptic("medium");
      if (still) { a.goToAndStop((f + COIN_T.period) % total || COIN_T.still, true); return; }
      if (k >= COIN_T.hold) return; // already in the air
      a.setSpeed(1.6);
      a.goToAndPlay((f - k + COIN_T.hold) % total, true);
      setTimeout(() => a.setSpeed(1), 450);
    });
  };
  const mountCoins = (root) => {
    const boxes = [...root.querySelectorAll(".coinl:not([data-on])")];
    if (!boxes.length) return;
    boxes.forEach((b) => b.setAttribute("data-on", ""));
    const still = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
    const kind = (b) => ANIM3D[b.dataset.k] || ANIM3D.coins;
    lottieLib().then((L) => boxes.forEach((b) => {
      if (!b.isConnected) return;
      const k = kind(b);
      const a = L.loadAnimation({ container: b, renderer: "svg", loop: true, autoplay: !still, path: k.path,
        rendererSettings: { preserveAspectRatio: "xMidYMid meet" } });
      if (still) a.addEventListener("DOMLoaded", () => a.goToAndStop(k.still, true));
      a.addEventListener("data_failed", () => { b.textContent = k.fb; b.classList.add("fb"); });
      coinPlay(b, a, still, k);
    })).catch(() => boxes.forEach((b) => { b.textContent = kind(b).fb; b.classList.add("fb"); }));
  };
  new MutationObserver(() => mountCoins(document)).observe(document.getElementById("root"), { childList: true, subtree: true });

  // Gram: a cut diamond (icons/gram-gem.json) over its glow and rays (icons/gram-fx.json). It pops in once (frames
  // 0..GEM.ent), then turns for ever. The cut repeats every 360°/8 and the light stays put, so frames ent..ent+loop are
  // one facet step: any angle maps onto them. A finger turns it a little, letting go springs it back; a tap nudges it and it hops.
  const GEM = { ent: 72, loop: 84, step: 45, idle: 45 / 1.4, pull: 24, gem: "/icons/gram-gem.json?v=6", fx: "/icons/gram-fx.json?v=3" };
  // The brand's star sits where it is in the Gram mark (upper right of the crown) and stays: it only twinkles.
  const GEML = (w) => `<div class="geml" style="width:${w}px;height:${w}px"><div class="gfx"></div><div class="ggem">` +
    `<svg class="gspk" viewBox="43.8 23.1 36 36" aria-hidden="true"><path fill="#fff" d="${SPK}"/></svg></div></div>`;
  const gemPlay = (b, a, still) => {
    const box = b.querySelector(".ggem");
    // base: the idle turn; off: how far a finger has turned it away from there — a little, with growing resistance
    // (at most GEM.pull°). While held the idle turn waits; on release `off` springs back to 0 and the idle turn eases
    // back in, so the stone settles where it was and carries on turning without a seam.
    let base = 0, off = 0, vel = 0, speed = still ? 0 : 1, drag = null, run = false, last = 0;
    const show = () => {
      const ph = base + off;
      a.goToAndStop(GEM.ent + ((((ph % GEM.step) + GEM.step) % GEM.step) / GEM.step) * GEM.loop, true);
    };
    const tick = (now) => {
      if (!b.isConnected) { run = false; return; }
      const dt = Math.min(.05, (now - (last || now)) / 1000);
      last = now;
      if (!drag) {
        vel += (-off * 160 - vel * 18) * dt;   // a spring, just under critical damping: one soft settle
        off += vel * dt;
        if (Math.abs(off) < .05 && Math.abs(vel) < .5) { off = 0; vel = 0; }
        speed += ((still ? 0 : 1) - speed) * (1 - Math.exp(-dt * 5));
        base += GEM.idle * speed * dt;
      }
      show();
      if (run) requestAnimationFrame(tick);
    };
    const go = () => { if (!run) { run = true; last = 0; requestAnimationFrame(tick); } };
    if (!still) a.addEventListener("complete", go, { once: true });
    if (b.closest("button, .am-ic")) return;
    b.classList.add("gemx");
    b.addEventListener("pointerdown", (e) => {
      drag = { x: e.clientX, y: e.clientY, t: performance.now(), off, moved: 0 };
      vel = 0; speed = 0;
      try { b.setPointerCapture(e.pointerId); } catch (_) { /* old webviews */ }
      box.classList.add("held");
      go();
    });
    b.addEventListener("pointermove", (e) => {
      if (!drag) return;
      const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      off = GEM.pull * Math.tanh((drag.off / GEM.pull) + dx * .6 / GEM.pull);
      drag.moved = Math.max(drag.moved, Math.hypot(dx, dy));
      b.style.setProperty("--gtx", `${(8 * Math.tanh(dy * -.02)).toFixed(1)}deg`);
    });
    const up = () => {
      if (!drag) return;
      const tap = drag.moved < 6 && performance.now() - drag.t < 350;
      drag = null;
      if (!still) speed = Math.max(speed, .45);   // it picks the idle turn up again while it settles
      box.classList.remove("held");
      b.style.removeProperty("--gtx");
      if (tap) {
        vel = 240;                       // a small nudge that springs home
        haptic("medium");
        box.classList.remove("hop"); void box.offsetWidth; box.classList.add("hop");
      }
    };
    b.addEventListener("pointerup", up);
    b.addEventListener("pointercancel", up);
  };
  const mountGems = (root) => {
    const boxes = [...root.querySelectorAll(".geml:not([data-on])")];
    if (!boxes.length) return;
    boxes.forEach((b) => b.setAttribute("data-on", ""));
    const still = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
    const fail = (b) => { b.textContent = "💎"; b.classList.add("fb"); };
    lottieLib().then((L) => boxes.forEach((b) => {
      if (!b.isConnected) return;
      const opt = { renderer: "svg", rendererSettings: { preserveAspectRatio: "xMidYMid meet" } };
      const fx = L.loadAnimation({ ...opt, container: b.querySelector(".gfx"), loop: true, autoplay: !still, path: GEM.fx });
      const a = L.loadAnimation({ ...opt, container: b.querySelector(".ggem"), loop: false, autoplay: false, path: GEM.gem });
      a.addEventListener("DOMLoaded", () => {
        if (still) { a.goToAndStop(GEM.ent, true); fx.goToAndStop(0, true); } else a.playSegments([0, GEM.ent], true);
      });
      a.addEventListener("data_failed", () => fail(b));
      gemPlay(b, a, still);
    })).catch(() => boxes.forEach(fail));
  };
  new MutationObserver(() => mountGems(document)).observe(document.getElementById("root"), { childList: true, subtree: true });
  const SBPBIG = (w) => `<div style="width:${w}px;height:${w}px;border-radius:${Math.round(w * .28)}px;background:#fff;display:flex;align-items:center;justify-content:center;box-shadow:0 10px 24px rgba(0,0,0,.25)"><img src="/icons/sbp.svg" width="${Math.round(w * .5)}" height="${Math.round(w * .58)}" alt=""></div>`;
  const CARDBIG = (w) => `<svg width="${w}" height="${Math.round(w * .72)}" viewBox="0 0 100 72"><rect x="2" y="2" width="96" height="68" rx="12" fill="#fff"/><rect x="2" y="16" width="96" height="12" fill="#2b3a66"/>` +
    `<rect x="12" y="40" width="22" height="16" rx="3" fill="#f2c14e"/><rect x="44" y="46" width="40" height="5" rx="2.5" fill="#c9cfdc"/></svg>`;
  const LOOK = {
    ton: { c: "blue", ill: (w) => GEML(w + 64) },
    stars: { c: "stars", ill: (w) => STARBIG(w + 28) },
    sbp: { c: "sbp", ill: (w) => SBPBIG(w + 4) },
    card: { c: "cardpay", ill: (w) => CARDBIG(w + 14) },
    crypto: { c: "slate", ill: (w) => COINS(w + 44) },
  };
  // Every method's picture sits in a slot of the same height, so the payment cards don't jump when the method changes.
  const look = (m) => {
    const L = LOOK[(m && m.id) || ""] || LOOK.ton;
    return { ...L, ill: (w) => `<div class="payill" style="height:${w + 24}px">${L.ill(w)}</div>` };
  };
  const WAIT_TEXT = {
    stars: ["Открыли счёт в Telegram", "<b>обычно мгновенно</b>"],
    sbp: ["Открыли оплату через СБП", "<b>подтвердите в приложении банка</b>"],
    card: ["Открыли защищённую страницу оплаты", "<b>обычно до минуты</b>"],
  };
  const daysFor = (amount) => Math.floor(amount / (dayPrice() * Math.max(1, phones().length)));
  const amountLine = () => (amountOk(pay.amount) ? `≈ ${days(daysFor(pay.amount))} VPN` : `Укажите сумму от ${rub(me.topup_min || 1)}`);
  SCR.topup = {
    h() {
      // The first payment starts small: «от 50 ₽» in the bot should not open on 500 ₽.
      const firstPay = !me.has_paid_topup, fb = FB(), start = fb ? Number(fb.min_rub) : firstPay ? 100 : 500;
      if (!amountOk(pay.amount)) pay.amount = amountOk(start) ? start : Number(me.topup_min) || 100;
      const chips = [...new Set(fb ? [Number(me.topup_min) || 50, 100, Number(fb.min_rub), 500] : firstPay ? [Number(me.topup_min) || 50, 100, 300, 500] : [100, 300, 500, 1000])]
        .filter(amountOk).sort((a, b) => a - b);
      const m = curMethod();
      const inChips = chips.includes(pay.amount) && !pay.custom;
      const L = look(m);
      const fbx = fb ? `<div class="fbx idle"><div class="fbhalo"></div>${FBGIFT()}</div>` : "";
      const need = fb ? `<button type="button" class="fbneed" data-act="fbneed"><i>+</i><span id="fbNeedT"></span></button>` : "";
      return hc(L.c, { cls: fb ? "fbon" : "", ill: fb ? fbx : L.ill(72), n: fb ? `<span class="fbnw"><span id="amtN">${rub(pay.amount)}</span><i class="am-fbs" id="amtFbs">+${fbPct()}%</i></span>` : `<span id="amtN">${rub(pay.amount)}</span>`,
        p: `<span id="amtP">${amountLine()}</span>`,
        x: need + `<div class="chp">${chips.map((v) => `<button type="button" data-act="amt" data-v="${v}" class="${inChips && v === pay.amount ? "on" : ""}${fb && v >= Number(fb.min_rub) ? " g" : ""}">${fmt(v)}</button>`).join("")}` +
          `<button type="button" data-act="amtc" class="${inChips ? "" : "on"}">${inChips ? "Своя" : fmt(pay.amount) + " ✎"}</button></div>`,
        pill: m ? `Оплатить ${rub(pay.amount)}` : "Оплата недоступна", pd: !m || !amountOk(pay.amount), pa: 'data-act="pay" id="payB"' }) +
        (m ? ST("Способ оплаты") + cd([[E(METHOD_EMO[m.id] || "💳") + TT(esc(m.title), esc(methodSub(m))) + (payMethods().length > 1 ? V("Изменить " + CV) : ""),
          payMethods().length > 1 ? 'data-go="method"' : ""]]) : NOTE("Оплата временно недоступна. Попробуйте позже или напишите в поддержку.", true)) +
        (fb ? NOTE(fbRet() ? `🎁 Бонус за возвращение: +${fbPct()}% к пополнению от ${rub(fb.min_rub)} до ${esc(fb.until || "конца акции")}`
          : `🎁 +${fbPct()}% к первому пополнению от ${rub(fb.min_rub)} — пока не закончился подарок`, true) : "") +
        NOTE(`Баланс ${rub(me.balance_rub)} · разовая оплата${me.autopay ? "" : ", без\u00a0автоплатежей"}`, true);
    },
    on(el) { fbPaint(el, true); },
  };
  function paintAmount(el, old) {
    const n = el.querySelector("#amtN");
    if (n && Number.isFinite(old) && amountOk(pay.amount)) countTo(n, old, pay.amount, " ₽");
    else if (n) n.textContent = amountOk(pay.amount) ? rub(pay.amount) : "— ₽";
    el.querySelector("#amtP").textContent = amountLine();
    const b = el.querySelector("#payB");
    const ok = amountOk(pay.amount) && curMethod();
    b.classList.toggle("dim", !ok);
    b.querySelector("span").textContent = curMethod() ? `Оплатить ${amountOk(pay.amount) ? rub(pay.amount) : ""}`.trim() : "Оплата недоступна";
    fbPaint(el);
  }

  // ---------- own amount: big number, own keypad, live hints ----------
  const GRAM = (w) => `<svg width="${w}" height="${w}" viewBox="0 0 100 100"><path fill="#30A1F5" d="${GP}"/><path fill="#fff" d="${SPK}"/></svg>`;
  const AM_ICON = { ton: () => GRAM(42), stars: () => STARBIG(52), sbp: () => `<img src="/icons/sbp.svg" width="30" height="35" alt="">`, card: () => CARDBIG(40), crypto: () => COINS(52) };
  const AM_TONE = { ton: "", stars: "gold", sbp: "green", card: "green", crypto: "" };
  const amt = { v: "", d: "", mode: "rub", rolling: false, gift: false, cnt: 1 };
  // The same screen types a gift for a friend («Своя» in «Подарить»): its own limits, one device's day price, no payment method.
  const amOk = (n) => (amt.gift ? gOk(n) && n * amt.cnt <= gLim()[1] : amountOk(n));
  const amMin = () => (amt.gift ? gLim()[0] : Number(me.topup_min) || 1);
  const amMax = () => (amt.gift ? gLim()[1] : Number(me.topup_max) || 100000);
  const amN = () => Number(amt.v) || 0;
  const amBig = () => (amt.mode === "rub" ? fmt(amN()) : fmt(Number(amt.d) || 0));
  // In days mode the keypad types days; the ruble amount follows as days × price of a day for all devices.
  const amPerDay = () => (amt.gift ? dayPrice() : dayPrice() * Math.max(1, phones().length));
  const amDays = () => (amt.mode === "rub" ? (amt.gift ? gDays(amN()) : daysFor(amN())) : Number(amt.d) || 0);
  const amRow = (m) => cd([[E(METHOD_EMO[m.id] || "💳") + TT(esc(m.title), `Баланс ${rub(me.balance_rub)}`) + (payMethods().length > 1 ? V("Изменить " + CV) : ""),
    payMethods().length > 1 ? 'data-go="method"' : ""]]);
  // The empty keypad already says where the range starts, instead of «Минимум …» after a wrong number.
  const amHint0 = () => {
    const lo = Number(me.topup_min) || 0;
    return amt.mode === "rub" ? (lo > 1 ? `Наберите сумму от ${rub(lo)}` : "Наберите сумму") : "Наберите количество дней";
  };
  SCR.amount = {
    h() {
      const m = curMethod();
      const id = (m && m.id) || "ton";
      const gift = amt.gift;
      return `<div class="am ${gift ? "" : AM_TONE[id] || ""}" id="am">` +
        (gift ? NOTE(`Подарок другу · нажмите на подарок, чтобы раздать несколько`, true) : m ? amRow(m) : NOTE("Оплата временно недоступна. Попробуйте позже или напишите в поддержку.", true)) +
        `<div class="am-stage zero" id="amStage"><svg width="0" height="0" style="position:absolute"><filter id="amGoo"><feGaussianBlur stdDeviation="3.5"/><feColorMatrix values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 22 -9"/></filter></svg><div class="am-glow"></div>` +
          `<div class="am-w" id="amW">${gift
            ? `<button type="button" class="am-ico am-gico in" id="amIco" data-act="amtico" aria-label="Ещё один подарок"><span class="am-ic"><span class="am-gift"></span></span><b class="am-cnt${amt.cnt > 1 ? " on" : ""}">×${amt.cnt}</b></button>`
            : `<button type="button" class="am-ico in" id="amIco" data-act="amtico" aria-label="Сменить способ оплаты"><span class="am-ic">${(AM_ICON[id] || AM_ICON.ton)()}</span></button>`}` +
          `<div class="am-num" id="amNum"><span>0</span></div><div class="am-caret"></div><div class="am-unit" id="amUnit">₽</div>` +
          (!gift && FB() ? `<div class="am-fbs" id="amFbs">+${fbPct()}%</div>` : "") + `</div>` +
          `<button type="button" class="am-sub" id="amSub" data-act="amtsw"><span id="amSubT"></span><span class="sw">⇅</span></button>` +
          `<div class="am-hint">${esc(amHint0())}</div></div>` +
        `<div class="am-bottom"><div class="am-quick">${[100, 500, 1000].map((q) => `<button type="button" data-act="amtq" data-v="${q}">+${fmt(q)}</button>`).join("")}</div>` +
          `<button type="button" class="am-pay off" id="amPay" data-act="amtpay"><span>Введите сумму</span></button>` +
          `<div class="am-padw"><div><div class="am-pad">${["1", "2", "3", "4", "5", "6", "7", "8", "9", "c", "0", "b"].map((k) =>
            `<button type="button" data-act="amtk" data-v="${k}"${k === "c" || k === "b" ? ' class="fn"' : ""} aria-label="${k === "b" ? "Стереть" : k === "c" ? "Очистить" : k}">${k === "b" ? "⌫" : k === "c" ? "C" : k}</button>`).join("")}</div></div></div></div>` +
        `</div>`;
    },
    on(el) {
      amt.rolling = false;
      if (amt.gift) { mountAmGift(el); amGiftHold(el); }
      amSetNum(el, amBig(), null);
      amSide(el);
      // The keypad slides up, like tapping the amount in Telegram.
      timers.push(setTimeout(() => {
        if (!cur || cur.el !== el) return;
        el.querySelector("#am").classList.add("open");
      }, 380));
    },
  };
  // Typing motion, taken frame by frame from the reference: a new digit grows out of the caret in gray and turns white,
  // a lone "0" melts into a blob and re-forms as the digit, and the whole row glides to its new centre (FLIP).
  function amSetNum(el, s, prev) {
    const num = el.querySelector("#amNum"), w = el.querySelector("#amW");
    const keep = [el.querySelector("#amIco"), el.querySelector(".am-caret"), el.querySelector("#amUnit")];
    const old = [...num.children].filter((c) => !c.classList.contains("out"));
    const k = w.getBoundingClientRect().width / (w.offsetWidth || 1) || 1;
    const x0 = new Map();
    keep.concat(old).forEach((n) => n && x0.set(n, n.getBoundingClientRect().left));
    const span = (c, cls) => { const e = document.createElement("span"); e.textContent = c; if (cls) e.className = cls; return e; };
    let moved = [];
    if (prev == null) num.replaceChildren(...[...s].map((c) => span(c)));
    else if (s.length === prev.length + 1 && s.startsWith(prev) && prev !== "0") {
      num.querySelectorAll(".out").forEach((o) => o.remove());
      num.appendChild(span(s.slice(-1), "add"));
      moved = old;
    } else if (s.length === prev.length - 1 && prev.startsWith(s) && s !== "0") {
      num.querySelectorAll(".out").forEach((o) => o.remove());
      const last = old[old.length - 1], nb = num.getBoundingClientRect();
      const lx = (last.getBoundingClientRect().left - nb.left) / k;
      last.className = "out"; last.style.left = lx + "px";
      moved = old;
      setTimeout(() => last.remove(), 200);
    } else if (prev === "0" && s.length === 1) {
      const o = old[0]; o.className = "melt";
      num.classList.add("goo");
      num.appendChild(span(s, "form"));
      setTimeout(() => { o.remove(); num.classList.remove("goo"); }, 85);
    } else num.replaceChildren(...[...s].map((c) => span(c, "form")));
    num.className = "am-num" + (num.classList.contains("goo") ? " goo" : "") + (s.length >= 7 ? " l6" : s.length >= 6 ? " l5" : "");
    if (prev == null) return;
    const car = keep[1];
    if (car) { car.style.animation = "none"; void car.offsetWidth; car.style.animation = ""; }
    const anim = [];
    keep.concat(moved).forEach((n) => {
      if (!n || !x0.has(n)) return;
      const dx = (x0.get(n) - n.getBoundingClientRect().left) / k;
      if (Math.abs(dx) < 0.5) return;
      n.style.transition = "none"; n.style.translate = dx + "px 0"; anim.push(n);
    });
    if (!anim.length) return;
    void num.offsetWidth;
    anim.forEach((n) => { n.style.transition = "translate .24s cubic-bezier(.25,.85,.3,1)"; n.style.translate = "0 0"; });
  }
  function amSide(el) {
    const n = amN(), ok = amOk(n), min = amMin(), max = amMax();
    el.querySelector("#amStage").classList.toggle("zero", !n);
    const sub = el.querySelector("#amSub");
    sub.classList.toggle("bad", Boolean(n) && !ok);
    const many = amt.gift && amt.cnt > 1;
    el.querySelector("#amSubT").textContent = !n ? "" : n < min ? `Минимум ${rub(min)}` : n > max ? `Максимум ${rub(max)}`
      : many && n * amt.cnt > max ? `Всего не больше ${rub(max)}`
      : many ? `${rub(n)} × ${amt.cnt} = ${rub(n * amt.cnt)}`
      : amt.mode === "rub" ? `≈ ${days(amDays())} VPN` : rub(n);
    const u = el.querySelector("#amUnit");
    u.textContent = amt.mode === "rub" ? "₽" : pl(amDays(), "день", "дня", "дней");
    u.classList.toggle("days", amt.mode !== "rub");
    el.querySelector(".am-hint").textContent = many ? `${amt.cnt} ${pl(amt.cnt, "подарок", "подарка", "подарков")} по ${amt.mode === "rub" ? rub(n) : days(amDays())} · удерживайте, чтобы сбросить`
      : amt.gift ? (amt.mode === "rub" ? "Сколько подарить?" : "Сколько дней подарить?")
      : amHint0();
    // «+35% к первому пополнению»: a sticker on the number lights up from the threshold,
    // and the line under it says what lands on the balance (or how much is missing).
    const fbEl = el.querySelector("#amFbs"), f = FB(), hit = Boolean(fbEl && f && !amt.gift && fbOk(n));
    if (fbEl && f && amt.mode === "rub" && n && !many) {
      const need = Number(f.min_rub), st = el.querySelector("#amSubT");
      if (hit) st.innerHTML = `На баланс придёт <b class="am-gold">${rub(n + fbRub(n))}</b> · ≈ ${days(daysFor(n + fbRub(n)))}`;
      else if (n < need && n >= min) st.innerHTML = `≈ ${days(amDays())} VPN · ещё ${rub(need - n)} до <b class="am-gold">+${fbPct()}%</b>`;
    }
    if (fbEl) {
      const was = fbEl.classList.contains("hit");
      fbEl.classList.toggle("hit", hit);
      if (!hit) fbEl.classList.remove("pop");
      if (hit && !was) { fbEl.classList.remove("pop"); void fbEl.offsetWidth; fbEl.classList.add("pop"); fbBurst(fbEl); notify("success"); }
    }
    const p = el.querySelector("#amPay");
    const can = amt.gift || curMethod();
    p.classList.toggle("off", !ok || !can);
    p.querySelector("span").textContent = !can ? "Оплата недоступна" : !ok ? "Введите сумму"
      : many ? `Подарить ${amt.cnt} × ${rub(n)}` : `${amt.gift ? "Подарить" : "Оплатить"} ${rub(n)}`;
  }
  function amtShake() {
    const w = cur.el.querySelector("#amW");
    w.classList.remove("shake"); void w.offsetWidth; w.classList.add("shake");
    notify("error");
  }
  function amtPress(k) {
    if (!cur || cur.key !== "amount" || amt.rolling) return;
    const el = cur.el, prev = amBig();
    const ed = amt.mode === "rub" ? amt.v : amt.d, lim = amt.mode === "rub" ? 6 : 5;
    const set = (x) => { if (amt.mode === "rub") amt.v = x; else { amt.d = x; amt.v = x ? String(Number(x) * amPerDay()) : ""; } };
    if (k === "b") { if (!ed) return amtShake(); set(ed.slice(0, -1)); }
    else if (k === "c") { if (!ed) return; set(""); }
    else { const nx = (ed === "0" ? "" : ed) + k; if (nx.length > lim || nx === "0") return amtShake(); set(nx); }
    haptic();
    el.querySelector("#am").classList.add("open");
    amSetNum(el, amBig(), prev);
    amSide(el);
    if (amN() > amMax()) amtShake();
  }
  function amRoll() {
    const el = cur.el, num = el.querySelector("#amNum"), target = amBig(), t0 = performance.now();
    amt.rolling = true;
    num.className = "am-num" + (target.length >= 7 ? " l6" : target.length >= 6 ? " l5" : "");
    amSide(el);
    (function f(t) {
      if (!cur || cur.el !== el) { amt.rolling = false; return; }
      const k = Math.min(1, (t - t0) / 520);
      if (k < 1) {
        num.innerHTML = [...target].map((c, i) => (/\d/.test(c) && k < 0.55 + i * 0.1
          ? `<span class="roll" style="--dy:${Math.round(Math.random() * 16 - 8)}px">${Math.floor(Math.random() * 10)}</span>` : `<span>${c}</span>`)).join("");
        requestAnimationFrame(f);
      } else { num.innerHTML = [...target].map((c) => `<span>${c}</span>`).join(""); amt.rolling = false; }
    })(t0);
  }
  function amtQuick(b) {
    if (amt.rolling) return;
    haptic();
    amt.v = String(Math.min(amMax(), amN() + Number(b.dataset.v)));
    amt.mode = "rub";
    cur.el.querySelector("#am").classList.add("open");
    amRoll();
  }
  function amSwap(b) {
    if (!amN() || amt.rolling) return;
    haptic("medium");
    amt.mode = amt.mode === "rub" ? "days" : "rub";
    if (amt.mode === "days") { const d = amt.gift ? gDays(amN()) : daysFor(amN()); amt.d = d ? String(d) : ""; if (amt.gift) amt.v = d ? String(d * amPerDay()) : ""; }
    amRoll();
  }
  // Tapping the method icon flips to the next payment method: the old icon spins away, the new one springs in,
  // the accent colour flows over and the method row above changes with it.
  function amCycle() {
    const list = payMethods(), m = curMethod();
    if (list.length < 2 || !m) return amBoom();
    const el = cur.el, next = list[(list.findIndex((x) => x.id === m.id) + 1) % list.length];
    pay.method = next.id;
    haptic("medium");
    const ico = el.querySelector("#amIco"), am = el.querySelector("#am");
    ico.classList.remove("in", "boom");
    ico.querySelectorAll(".am-ic.go").forEach((o) => o.remove());
    const old = ico.querySelector(".am-ic");
    if (old) { old.classList.remove("come"); old.classList.add("go"); setTimeout(() => old.remove(), 320); }
    const nw = document.createElement("span");
    nw.className = "am-ic come";
    nw.innerHTML = (AM_ICON[next.id] || AM_ICON.ton)();
    ico.appendChild(nw);
    Object.values(AM_TONE).forEach((t) => t && am.classList.remove(t));
    if (AM_TONE[next.id]) am.classList.add(AM_TONE[next.id]);
    const row = am.querySelector(".cd");
    if (row) {
      const t = document.createElement("div"); t.innerHTML = amRow(next);
      const fresh = t.firstElementChild; fresh.classList.add("am-rsw");
      row.replaceWith(fresh);
    }
    amSide(el);
  }
  function amBoom() {
    const i = cur.el.querySelector("#amIco");
    i.classList.remove("boom", "in"); void i.offsetWidth; i.classList.add("boom");
    haptic("medium");
  }
  // A computer keyboard types into the amount too.
  document.addEventListener("keydown", (e) => {
    if (!cur || cur.key !== "amount" || e.metaKey || e.ctrlKey || e.altKey) return;
    if (/^\d$/.test(e.key)) { e.preventDefault(); amtPress(e.key); }
    else if (e.key === "Backspace") { e.preventDefault(); amtPress("b"); }
    else if (e.key === "Enter") { e.preventDefault(); ACT.amtpay(cur.el.querySelector("#amPay")); }
  });

  SCR.method = {
    h() {
      const L = look(curMethod());
      return hc(L.c, { ill: L.ill(64), h: "Чем оплатить?", p: pay.amount > 0 ? `${rub(pay.amount)} на баланс · ${me.autopay ? "разовая оплата" : "без автоплатежей"}` : me.autopay ? "Разовая оплата" : "Разовая оплата, без автоплатежей" }) +
        ST("Способы") + cd(payMethods().map((m) => [E(METHOD_EMO[m.id] || "💳") + TT(esc(m.title), esc(methodSub(m))) + V(RD(m.id === pay.method)), `data-act="meth" data-v="${esc(m.id)}"`])) +
        `<div class="bot"><button type="button" class="bbtn" data-act="back">Готово</button></div>`;
    },
    bot: true,
  };

  // ---------- waiting for the money ----------
  SCR.wait = {
    h() {
      if (pay.kind === "autopay") {
        return hc("sbp", { cls: "shim", rb: "ждём", ill: SBPBIG(60), n: rub(pay.amount), p: "Ждём оплату · обычно до минуты",
          pill: "Ждём оплату…", pd: true, r: "ref", rl: "Проверить", ra: 'data-act="refresh"' }) +
          ST("Как это работает") +
          tl([[CHK(22), "Счёт создан", `${rub(pay.amount)} · СБП`, "ok"],
            ["2", "Подтверждение в банке", "<b>подтвердите в приложении банка</b>", "run"],
            ["🔁", "Включим автопополнение", "сразу после оплаты"]]) +
          (pay.url ? `<button type="button" class="lnk" data-act="reopen">Открыть оплату ещё раз</button>` : "") +
          NOTE("Если оплата не пройдёт, ничего не включится.", true);
      }
      const m = curMethod() || { title: "" };
      const L = look(m), wt = WAIT_TEXT[m.id] || [pay.kind === "stars" ? "Открыли счёт в Telegram" : "Открыли страницу оплаты", "<b>обычно до минуты</b>"];
      return hc(L.c, { cls: "shim", rb: "ждём", ill: L.ill(56), n: rub(pay.amount), p: `${esc(m.title)} · ≈ ${days(daysFor(pay.amount))} VPN`,
        pill: "Ждём оплату…", pd: true, r: "ref", rl: "Проверить", ra: 'data-act="refresh"' }) +
        ST("Как это работает") +
        tl([[CHK(22), wt[0], timeHM(new Date()), "ok"],
          ["2", "Ждём подтверждение", wt[1], "run"],
          ["3", "Зачислим на баланс", "и пришлём сообщение в чат"]]) +
        (pay.url ? `<button type="button" class="lnk" data-act="reopen">Открыть оплату ещё раз</button>` : "") +
        NOTE("Можно закрыть кабинет — деньги всё равно придут, а бот пришлёт сообщение.", true);
    },
    on(el) {
      const tick = () => {
        if (!cur || cur.key !== "wait" || cur.el !== el) return;
        load(true).then(() => { if (cur && cur.el === el) checkPaid(el); }).catch(() => {});
        T(tick, 4000);
      };
      T(tick, 3000);
    },
  };
  function checkPaid(el) {
    if (Number(me.balance_rub) > pay.base) paid(el, Number(me.balance_rub) - pay.base);
  }
  function paid(el, delta) {
    const h = el.querySelector(".hc");
    if (!h || h.classList.contains("dn")) return;
    h.classList.remove("shim");
    h.classList.add("dn", "go");
    h.querySelector(".rb").textContent = "зачислено";
    const g = h.querySelector(".gst");
    if (g) g.style.fill = "#27a865";
    const N = h.querySelector(".N");
    N.innerHTML = "<span></span>";
    const bonus = pay.fbOn && delta > pay.amount ? delta - pay.amount : 0;
    countTo(N.firstChild, 0, bonus ? pay.amount : delta, " ₽", "+");
    if (bonus) {
      h.querySelector(".P").insertAdjacentHTML("afterend", `<div class="fbdone"><span>🎁 ${pay.fbRet ? "Бонус за возвращение" : "Бонус за первую оплату"}</span><b>+${rub(bonus)}</b></div>`);
      T(() => { const d = h.querySelector(".fbdone"); if (d) { d.classList.add("in"); fbBurst(d); } }, 900);
      pay.fbOn = false;
    }
    h.querySelector(".P").textContent = pay.kind === "autopay" && runway() ? runway() : "Баланс: " + rub(me.balance_rub);
    const p = h.querySelector(".pill");
    p.classList.remove("dim");
    p.querySelector("span").textContent = "Отлично";
    p.setAttribute("data-act", "home");
    const ns = el.querySelectorAll(".tl .n");
    if (ns[1]) { ns[1].className = "n ok"; ns[1].innerHTML = CHK(22); const sx = ns[1].parentNode.querySelector(".sx"); if (sx) sx.textContent = "оплата прошла"; }
    T(() => { if (ns[2]) { ns[2].className = "n ok"; ns[2].innerHTML = CHK(22); } }, 400);
    const st = el.querySelector(".st");
    if (st) st.textContent = "Готово";
    el.querySelectorAll(".lnk").forEach((x) => x.remove());
    store.set("shown_bal", Number(me.balance_rub) || 0);
    store.set("seen_bal", Number(me.balance_rub) || 0);
    notify("success");
    boom();
    toast(`+${rub(delta)} на балансе 🎉`);
    if (pay.kind === "autopay") { apPaid(el); pay.kind = ""; return; }
    T(() => { if (!apQuiet(el)) paidInvite(el); }, 1100);
  }
  // Right after a payment people are happy with the service: offer to bring a friend. Shown on the first payment,
  // then at most once a month, only while the referral program pays out.
  function paidInvite(el) {
    if (!me.referral_program_enabled || !cur || cur.el !== el || el.querySelector(".pinv")) return;
    const last = Number(store.get("pinv_at")) || 0;
    if (last && Date.now() - last < 30 * 864e5) return;
    store.set("pinv_at", Date.now());
    const r = rub(Number(me.referral_reward_rub) || 50);
    const box = document.createElement("div");
    box.innerHTML = `<button type="button" class="fbban pinv" data-act="share"><span class="fbrays2"></span><span class="fbgift"></span>` +
      `<span class="pinv-k">Поделитесь с другом</span><span class="fbpc">+${r}</span><span class="fbsub">вам и другу: ему сразу, вам — когда он подключит VPN</span>` +
      `<span class="pill fbbp">${IC.share}<span>Пригласить друга</span></span></button>`;
    const note = el.querySelector(".note");
    const b = box.firstChild;
    if (note) note.replaceWith(b); else el.appendChild(b);
    T(() => b.scrollIntoView({ behavior: reduced() ? "auto" : "smooth", block: "nearest" }), 250);
    track("paid_invite_view");
  }

  // ---------- connect a device ----------
  SCR.wiz1 = {
    h() {
      return hc("teal", { ill: "📱", h: "Где включить VPN?", p: "Каждое устройство оплачивается отдельно", x: '<div class="dots"><i class="on"></i><i></i><i></i></div>' }) +
        ST("Устройство") + cd(PLATFORMS.map((p) => [E(PLAT_EMO[p.id]) + p.title + V(esc((appsFor(p.id)[0] || {}).name || "") + " " + CV), `data-act="plat" data-v="${p.id}"`]));
    },
    on() { track("wizard_1"); },
  };
  SCR.wizhave = {
    h() {
      const list = appsFor(wiz.platform);
      return hc("teal", { cls: "compact", h: "Какое у вас?", p: "Добавим ключ прямо в него" }) +
        `<div class="agrid">${list.map((a, i) => `<button type="button" data-act="haveapp" data-v="${esc(a.id)}" style="--i:${i}">${appIcon(a, 54)}<b>${esc(a.name)}</b></button>`).join("")}` +
        `<button type="button" data-act="haveapp" data-v="other" style="--i:${list.length}"><span class="aio">📋</span><b>Другое</b></button></div>` +
        NOTE("Нет в списке — выберите «Другое»: скопируем ключ, а вы вставите его в своё приложение.");
    },
  };
  SCR.wiz2 = {
    h() {
      const list = appsFor(wiz.platform);
      if (wiz.has && (wiz.client === "other" || list.some((a) => a.id === wiz.client))) {
        const own = appById(wiz.client), other = wiz.client === "other";
        // The app is a guess from another device (or the user's own pick): ask, and make «install» just as easy.
        return hc("teal", { ill: other ? "📋" : appIcon(own, 92), h: other ? "Своё приложение" : `${esc(own.name)} уже есть?`,
          p: other ? "Создадим ключ — вы вставите его в своё приложение" : `Если ${esc(own.name)} стоит на этом устройстве, сразу добавим в него ключ`,
          x: '<div class="dots"><i class="on"></i><i class="on"></i><i></i></div>',
          pill: other ? "Создать ключ" : "Да, создать ключ", pa: 'data-act="create" id="wizOk"' }) +
          (other ? "" : cd([[E("⬇️") + TT(`Нет, установить ${esc(own.name)}`, "бесплатно, займёт полминуты") + V(CV), 'data-act="hasnot"']])) +
          ST("Как это работает") +
          tl([["1", "Нажмите «Создать ключ»", "отдельный ключ для этого устройства"],
            ["2", other ? "Скопируйте ключ и вставьте в приложение" : `Подтвердите добавление в ${esc(own.name)}`, other ? "обычно «+» → «Импорт из буфера»" : "кнопка откроет приложение"],
            ["3", "Включите VPN", `${dayPrice()} ₽ в день, пока пользуетесь`]]) +
          cd([[E("🔄") + "Выбрать другое приложение" + V(CV), 'data-act="hasyes"'],
          ]);
      }
      if (!list.some((a) => a.id === wiz.client)) wiz.client = prefApp(wiz.platform);
      const a = appById(wiz.client);
      if (!a) {
        return hc("teal", { ill: PLAT_EMO[wiz.platform] || "📱", h: "Пока нет инструкции", p: `Для ${esc(platTitle(wiz.platform))} напишите в поддержку — поможем`,
          pill: "Написать в поддержку", pa: 'data-act="support"' });
      }
      const dl = (a.stores || {})[wiz.platform];
      if (dl && me && me.install_ab === "new") {
        // A/B test (app/install_test.py), group B. Two steps on one card: install, then add the key. «Добавить» works from the start (the app may already be
        // there); after «Скачать» step 1 is ticked and step 2 lights up, so coming back from the store shows what to press.
        const went = Boolean(wiz.went), sn = storeName(wiz.platform, a);
        const steps = `<div class="wsteps"><div class="wst ${went ? "ok" : "cur"}"><span class="wn">${went ? CHK(14) : "1"}</span>
          <span class="wt"><b>Установите ${esc(a.name)}</b><span>${went ? `Открыли ${esc(sn)}` : "бесплатно, полминуты"}</span></span>
          <button type="button" class="wsb${went ? " ghost" : ""}" data-act="store">${went ? "Ещё раз" : "Скачать"}</button></div>
          <div class="wst${went ? " cur" : ""}"><span class="wn">2</span><span class="wt"><b>Добавьте ключ в ${esc(a.name)}</b>
          <span>${went ? "Установили? Жмите кнопку ниже" : "Если уже стоит — жмите сразу"}</span></span></div></div>`;
        return hc("teal", { cls: "wiz2s" + (went ? " went" : ""), ill: appIcon(a, 64), h: "Подключим за 2 шага", p: `${esc(a.name)} — бесплатно в ${esc(sn)}`, x: steps,
          pill: `Добавить в ${esc(a.name)}`, pa: 'data-act="addkey" id="wizOk"' }) +
          apkRow(a) + guideRow(a) + appMore(list, a) +
          cd([[E(PLAT_EMO[wiz.platform] || "📱") + esc(platTitle(wiz.platform)) + V("Другое устройство " + CV), 'data-act="replat"']]);
      }
      return hc("teal", { ill: appIcon(a, 92), h: `Установите ${esc(a.name)}`, p: `Бесплатно в ${storeName(wiz.platform, a)}. Уже стоит — жмите ✓`,
        x: '<div class="dots"><i class="on"></i><i class="on"></i><i></i></div>',
        pill: dl ? "Скачать" : "Готово, установлено", pa: dl ? 'data-act="store"' : 'data-act="create"', r: "chk", rl: "Приложение установлено", ra: 'data-act="create" id="wizOk"' }) +
        apkRow(a) + guideRow(a) + appMore(list, a) +
        ST("Как это работает") +
        tl([["1", `Установите ${esc(a.name)}`, "займёт полминуты"], ["2", "Вернитесь сюда и нажмите ✓", "создадим ключ для этого устройства"],
          ["3", "Подключите в один тап", `${dayPrice()} ₽ в день, пока пользуетесь`]]) +
        cd([[E(PLAT_EMO[wiz.platform] || "📱") + esc(platTitle(wiz.platform)) + V("Другое устройство " + CV), 'data-act="replat"']]);
    },
    on() {
      track("wizard_2");
      // «Можно выбрать другое приложение» shows once per user, under the apps row.
      if (cur && cur.el.querySelector(".atip")) store.set("alt_tip", 1);
    },
  };
  // «Скачать APK напрямую»: the app's file straight from its site, for Android without Google Play
  // or where the store does not open. Only when the app has a direct link for this platform.
  function apkRow(a) {
    const url = a && (a.direct || {})[wiz.platform];
    return url ? `<button type="button" class="gde apk" data-act="apk"><span class="gi">${APK_IC}</span>
      <span class="al"><b>Скачать APK напрямую</b><span>Если Google Play нет или не работает</span></span>${CV}</button>` : "";
  }
  const APK_IC = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/></svg>';
  // «Как установить»: the app's guide (article or video) from the admin settings; nothing when it is not set.
  function guideRow(a) {
    return a && a.guide ? `<button type="button" class="gde" data-act="guide" data-v="${esc(a.id)}"><span class="gi">${GUIDE_IC}</span>
      <span class="al"><b>Инструкция по установке</b><span>Пошагово, как поставить ${esc(a.name)}</span></span>${CV}</button>` : "";
  }
  const GUIDE_IC = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5z"/><path d="M4 20.5A2.5 2.5 0 0 0 6.5 23H20v-5"/></svg>';
  // The recommended app stays in the card; the rest fold into «Другие приложения · N» and open as a list.
  function appMore(list, a) {
    if (list.length < 2) return "";
    const others = list.filter((x) => x.id !== a.id);
    const rows = list.map((x, i) => `<button type="button" class="ar" data-act="client" data-v="${esc(x.id)}" style="--i:${i}">${appIcon(x, 42)}<span class="at"><b>${esc(x.name)}</b>
      <span>${i ? "" : "★ рекомендуем · "}${x.deep_link ? "ключ добавится сам" : "ключ вставляется вручную"}</span></span><span class="ak">${x.id === a.id ? CHK(18) : ""}</span></button>`).join("");
    const names = others.slice(0, 3).map((x) => esc(x.name)).join(", ") + (others.length > 3 ? ` и ещё ${others.length - 3}` : "");
    const tip = store.get("alt_tip") ? "" : '<div class="atip">💡 Можно выбрать другое приложение<button type="button" class="x" data-act="tipx" aria-label="Закрыть">✕</button></div>';
    return `<div class="altw"><div class="alt"><button type="button" class="ah" data-act="appmore" aria-expanded="false"><span class="ava">${others.slice(0, 3).map((x) => appIcon(x, 30)).join("")}</span>
      <span class="al"><b>Другие приложения</b><span>${names}</span></span>${CV}</button><div class="als"><div>${rows}</div></div></div>${tip}</div>`;
  }
  SCR.wiz3 = {
    h() {
      const a = appById(wiz.client) || { name: "приложение" };
      const short = wiz.url ? wiz.url.replace(/^https?:\/\//, "").slice(0, 28) + "…" : "";
      if (wiz.client === "other") {
        return hc("green", { rb: "ключ", ill: "🛡️", h: "Добавьте ключ в приложение", p: "Скопируйте и вставьте его в своё приложение для VPN",
          x: `<div class="mono">${esc(short)}</div><div class="dots"><i class="on"></i><i class="on"></i><i class="on"></i></div>`,
          pill: "Скопировать ключ", pa: 'data-act="copykey"' }) +
          ST("Дальше") +
          tl([["1", "Скопируйте ключ", "кнопка выше"], ["2", "Вставьте в приложение", "обычно «+» → «Импорт из буфера» или «Добавить подписку»"],
            ["3", "Включите VPN", `<b>${dayPrice()} ₽ в день</b>, пока устройство добавлено`]]) +
          `<div style="height:12px"></div>` +
          cd([[E("🆘") + "Не получилось — помогите" + V(CV), 'data-act="helpconnect"'], [E("🏠") + "В кабинет" + V(CV), 'data-act="home"']]);
      }
      return hc("green", { rb: "ключ", ill: "🛡️", h: "Подключите VPN", p: `Ключ добавится в ${esc(a.name)} сам`,
        x: `<div class="mono">${esc(short)}</div><div class="dots"><i class="on"></i><i class="on"></i><i class="on"></i></div>`,
        pill: `Добавить в ${esc(a.name)}`, pa: 'data-act="connect"', r: "copy", rl: "Скопировать ключ", ra: 'data-act="copykey"' }) +
        ST("Дальше") +
        tl([["1", `Подтвердите добавление в ${esc(a.name)}`, "кнопка выше откроет приложение"],
          ["2", "Включите VPN в приложении", "разрешите VPN-подключение, если спросит"],
          ["3", "Готово — VPN работает", `<b>${dayPrice()} ₽ в день</b>, пока устройство добавлено`]]) +
        `<div style="height:12px"></div>` +
        cd([a.guide && [E("📖") + `Как подключить в ${esc(a.name)}` + V(CV), `data-act="guide" data-v="${esc(a.id)}"`],
          [E("🆘") + "Не получилось — помогите" + V(CV), 'data-act="helpconnect"'], [E("🏠") + "В кабинет" + V(CV), 'data-act="home"']]);
    },
    on() { track("wizard_4"); },
  };

  // ---------- device ----------
  // «Подключено» only after traffic went through the key: a key nobody used yet is not a working VPN.
  const devLine = (d) => !d.active ? '<span class="dot off"></span>Неактивно'
    : d.connected === false ? '<span class="dot wait"></span>Ещё не подключали'
    : `<span class="dot"></span>Подключено · ${dayPrice()} ₽ в день`;
  // ---------- device names ----------
  // The customer's own name and icon for a device, so «Телефон мамы» is not just another «Мой iPhone».
  const ICONS = ["📱", "💻", "🖥️", "📺", "🎮", "💼", "🏠", "⭐", "🧒", "👵"];
  const NAME_TIPS = ["Мой телефон", "Телефон мамы", "Рабочий", "Планшет сына", "Телевизор"];
  const NAME_MAX = 32;
  const devIcon = (d) => (d && d.icon) || PLAT_EMO[(d && d.platform) || ""] || "📱";
  // The device card's big picture: computers get the animated laptop (icons/laptop.json, LottieFiles «Laptop» by TheSub).
  const devBig = (d) => (!(d && d.icon) && ["macos", "windows"].includes((d && d.platform) || "") ? '<div class="lapl"></div>' : devIcon(d));
  function seenLine(d) {
    const on = parseDate(d.online_at);
    if (!d.active) return "неактивно";
    if (!on) return "ещё не подключали";
    if (Date.now() - on.getTime() < 15 * 60000) return '<b class="ok">● онлайн</b>';
    return `был ${dayLabel(on).toLowerCase()} в ${timeHM(on)}`;
  }
  // One sheet for one device (icon + name) or for a group with the same name (a field each).
  function nameSheet(devs) {
    if (document.querySelector(".nsw")) return;
    const multi = devs.length > 1;
    const icon = { v: devIcon(devs[0]), was: devIcon(devs[0]) };
    const field = (d) => `<label class="nfld"><span class="nem">${multi ? devIcon(d) : icon.v}</span>` +
      `<input maxlength="${NAME_MAX}" autocomplete="off" enterkeyhint="${multi ? "next" : "done"}" data-id="${d.id}" value="${esc(d.title || "")}">` +
      `<button type="button" class="nx" aria-label="Стереть">✕</button></label>`;
    const body = multi
      ? devs.map((d) => { const c = parseDate(d.created_at); return `<div class="npair"><div class="nh"><span>${c ? "Добавлен " + dateLong(c) : "Устройство"}</span><span>${seenLine(d)}</span></div>${field(d)}</div>`; }).join("")
      : field(devs[0]) + `<div class="nlim"><span>Видно только вам</span><span class="nc"></span></div>` +
        `<div class="nemo">${ICONS.map((e) => `<button type="button" class="${e === icon.v ? "on" : ""}" data-e="${e}">${e}</button>`).join("")}</div>`;
    const w = document.createElement("div");
    w.className = "nsw";
    w.innerHTML = `<div class="nsh" role="dialog" aria-label="Название устройства"><div class="grab"></div>` +
      `<h3>${multi ? "Подпишите устройства" : "Название устройства"}</h3>` +
      `<div class="nsub">${multi ? "Так проще понять, какое удалить и за что списание" : "Чтобы не путать устройства между собой"}</div>${body}` +
      `<div class="nchips">${NAME_TIPS.map((t) => `<button type="button">${t}</button>`).join("")}</div>` +
      `<button type="button" class="bbtn nsave dim">Сохранить</button><button type="button" class="ncancel">Отмена</button></div>`;
    document.body.appendChild(w);
    const inputs = [...w.querySelectorAll("input")], save = w.querySelector(".nsave"), cnt = w.querySelector(".nc");
    let active = inputs[0], busy = false;
    const changed = () => inputs.some((i) => i.value.trim() !== String((deviceById(i.dataset.id) || {}).title || "").trim()) || icon.v !== icon.was;
    const sync = () => {
      const ok = inputs.every((i) => i.value.trim()) && changed();
      save.classList.toggle("dim", !ok);
      if (cnt) cnt.textContent = `${active.value.length}/${NAME_MAX}`;
    };
    const close = () => { w.classList.add("out"); setTimeout(() => w.remove(), 320); };
    inputs.forEach((i, k) => {
      i.addEventListener("focus", () => { active = i; sync(); });
      i.addEventListener("input", sync);
      i.addEventListener("keydown", (e) => {
        if (e.key !== "Enter") return;
        e.preventDefault();
        if (inputs[k + 1]) inputs[k + 1].focus(); else if (!save.classList.contains("dim")) save.click(); else i.blur();
      });
    });
    w.querySelectorAll(".nx").forEach((x, k) => { x.onclick = () => { inputs[k].value = ""; inputs[k].focus(); sync(); }; });
    w.querySelectorAll(".nchips button").forEach((b) => {
      b.onclick = () => {
        haptic();
        active.value = b.textContent;
        w.querySelectorAll(".nchips button").forEach((x) => x.classList.toggle("on", x === b));
        active.parentElement.classList.remove("npop"); void active.offsetWidth; active.parentElement.classList.add("npop");
        const next = inputs[inputs.indexOf(active) + 1];
        if (next) active = next;
        sync();
      };
    });
    w.querySelectorAll(".nemo button").forEach((b) => {
      b.onclick = () => {
        haptic();
        icon.v = b.dataset.e;
        w.querySelectorAll(".nemo button").forEach((x) => x.classList.toggle("on", x === b));
        const em = w.querySelector(".nem"); em.textContent = icon.v; em.classList.remove("npop"); void em.offsetWidth; em.classList.add("npop");
        sync();
      };
    });
    w.querySelector(".ncancel").onclick = close;
    w.addEventListener("click", (e) => { if (e.target === w) close(); });
    save.onclick = async () => {
      if (busy || save.classList.contains("dim")) return;
      busy = true;
      save.classList.add("dim");
      const before = devs.map((d) => ({ id: d.id, title: d.title, icon: d.icon || "" }));
      try {
        for (const i of inputs) {
          const d = deviceById(i.dataset.id);
          const title = i.value.trim();
          const iconSet = !multi && icon.v !== icon.was;
          if (d && (title !== String(d.title || "").trim() || iconSet)) {
            await api(`/api/devices/${d.id}`, { method: "PATCH", body: JSON.stringify(iconSet ? { title, icon: icon.v } : { title }) });
          }
        }
        notify("success");
        close();
        await load(true).catch(() => {});
        renamedFlash(devs.map((d) => d.id));
        toastAct(multi ? "Теперь не перепутаете" : "Название сохранено", "Отменить", async () => {
          for (const b of before) await api(`/api/devices/${b.id}`, { method: "PATCH", body: JSON.stringify({ title: b.title || "Устройство", icon: b.icon }) }).catch(() => {});
          await load(true).catch(() => {});
        });
      } catch (e) {
        busy = false;
        save.classList.remove("dim");
        showErr(e);
      }
    };
    sync();
    if (!multi) { inputs[0].focus({ preventScroll: true }); inputs[0].select(); } // in the tap itself, so iOS opens the keyboard
  }
  // «I already have another app»: the device remembers it, and «Открыть» adds the key there instead of the recommended one.
  function appSheet(d) {
    if (document.querySelector(".nsw")) return;
    const list = appsFor(d.platform), was = (devApp(d) || {}).id;
    const w = document.createElement("div");
    w.className = "nsw";
    w.innerHTML = `<div class="nsh" role="dialog" aria-label="Приложение для VPN"><div class="grab"></div><h3>Каким приложением пользуетесь?</h3>` +
      `<div class="nsub">Кнопка «Открыть» будет добавлять ключ в него</div><div class="napps">` +
      list.concat([OTHER_APP]).map((a, i) => `<button type="button" class="${a.id === was ? "on" : ""}" data-v="${esc(a.id)}" style="--i:${i}">${appIcon(a, 40)}<span class="at"><b>${a.id === "other" ? "Другое приложение" : esc(a.name)}</b>` +
        `<span>${a.id === "other" ? "скопируем ключ — вставите вручную" : !i ? "★ рекомендуем" : a.deep_link ? "ключ добавится сам" : "ключ вставляется вручную"}</span></span><i>${a.id === was ? "✓" : ""}</i></button>`).join("") +
      `</div><button type="button" class="ncancel">Отмена</button></div>`;
    document.body.appendChild(w);
    const close = () => { w.classList.add("out"); setTimeout(() => w.remove(), 320); };
    w.querySelector(".ncancel").onclick = close;
    w.addEventListener("click", (e) => { if (e.target === w) close(); });
    w.querySelectorAll(".napps button").forEach((b) => {
      b.onclick = async () => {
        const id = b.dataset.v, a = appById(id);
        if (id === was) { close(); return; }
        notify("success");
        store.set("app_" + d.platform, id);
        const old = d.client;
        d.client = id;
        close();
        rerender();
        toast(id === "other" ? "Ключ будем копировать — вставьте его в своё приложение" : `Теперь ключ откроется в ${(a && a.name) || "приложении"}`);
        try {
          await api(`/api/devices/${d.id}`, { method: "PATCH", body: JSON.stringify({ client: id }) });
        } catch (e) {
          d.client = old;
          rerender();
          showErr(e);
        }
      };
    });
  }
  function renamedFlash(ids) {
    if (!cur) return;
    if (cur.key === "device") { const h = cur.el.querySelector(".hc .H"), i = cur.el.querySelector(".hc .ill"); [h, i].forEach((x) => x && x.classList.add("npop")); }
    ids.forEach((id) => { const r = cur.el.querySelector(`[data-act="device"][data-id="${id}"]`); if (r) r.classList.add("nflash"); });
  }
  const deviceById = (id) => ((me && me.devices) || []).find((d) => String(d.id) === String(id));
  SCR.device = {
    live: true,
    h(p) {
      const d = deviceById(p.id);
      if (!d) return hc("slate", { ill: "📱", h: "Устройство удалено", pill: "На главную", pa: 'data-act="home"' });
      const a = devApp(d) || appById("happ");
      const fresh = d.active && d.connected === false;
      return hc("teal", { rb: !d.active ? "пауза" : fresh ? "ждёт" : "онлайн", ill: devBig(d), h: esc(d.title || "Устройство"),
        p: !d.active ? "Неактивно — пополните баланс" : fresh ? `Ключ готов — добавьте его в ${esc((a && a.name) || "приложение")} и включите VPN`
          : `Активно · ${dayPrice()} ₽ в день`,
        ...(a && a.id === "other" ? { pill: "Скопировать ключ", pa: 'data-act="devcopy"' }
          : { pill: `Открыть в ${esc((a && a.name) || "приложении")}`, pa: `data-act="devopen"`, r: "copy", rl: "Скопировать ключ", ra: 'data-act="devcopy"' }) }) +
        ST("Устройство") +
        cd([[E("✏️") + TT("Название", esc(d.title || "Устройство")) + V(CV), 'data-act="rename"'],
          a ? [`<span class="e">${appIcon(a, 26)}</span>` + TT("Приложение", a.id === "other" ? "Своё — ключ вставляется вручную" : esc(a.name)) + V("сменить " + CV), 'data-act="devapp"'] : null,
          d.subscription_url ? [E("🔑") + TT("Ключ подписки", `<span class="keyv">${esc(d.subscription_url.replace(/^https?:\/\//, ""))}</span>`) + V("Скопировать"), 'data-act="devcopy"']
            : `${E("🔑")}${TT("Ключ подписки", "появится, когда устройство будет готово")}`,
          fresh ? null : [E("💡") + TT("Перестал работать VPN?", "Выпустим новый ключ, старый отключится") + V(CV), 'data-act="reissue"'],
          [E("🆘") + "Помощь с подключением" + V(CV), 'data-act="helpdevice"']]) +
        `<div style="height:12px"></div>` +
        cd([[E("🗑️") + "Удалить устройство", 'data-act="delete"', "red"]]) +
        NOTE(me.balance_enabled ? "Если устройство больше не нужно, удалите его — списания за него прекратятся." : "");
    },
    sig: (p) => JSON.stringify(deviceById(p.id) || null),
  };

  // ---------- friends ----------
  SCR.friends = {
    live: true,
    h(p) {
      const seg = me.gifts_enabled ? `<div class="seg">${[["invite", "Пригласить"], ["give", "Подарить"]].map(([v, t]) =>
        `<button type="button" data-act="gftab" data-v="${v}" class="${(p.tab || "invite") === v ? "on" : ""}">${t}</button>`).join("")}</div>` : "";
      return seg + `<div class="tabc">${me.gifts_enabled && p.tab === "give" ? giveTab() : this.invite()}</div>`;
    },
    on(el, p) {
      if (p.tab === "give") gGive(el); else gInvite(el);
      // Load the gifts up front, so «Подарить» opens complete and does not redraw a moment later.
      if (me.gifts_enabled && !gs.data) loadGifts();
    },
    invite() {
      const nf = me.friend_nft || {};
      nfThumbs = [];
      if (nf.enabled && Array.isArray(nf.steps) && nf.steps.length) return nfInvite(nf);
      return this.classic();
    },
    classic() {
      const on = Boolean(me.referral_program_enabled);
      const reward = Number(me.referral_reward_rub) || 50;
      const terms = me.referral_terms && typeof me.referral_terms === "object" ? me.referral_terms : {};
      const friends = Array.isArray(me.referrals) ? me.referrals : [];
      const invited = Number(me.invited_count) || 0, earned = Number(me.referral_earned) || 0;
      // The same purple stage as «Подарить», with a red-and-gold gift so the two tabs do not look alike.
      const hero = `<section class="hc gs inv ref"><div class="ov"></div>${gBack("violet")}<div class="inv-g" data-gmini="festive"></div>` +
        (on ? `<div class="K">Пригласите друзей</div><div class="N inv-n">+${rub(reward)}</div><div class="P">вам и другу за каждого приглашённого</div>`
          : `<div class="H">Пригласите друзей</div><div class="P">Пользоваться вместе приятнее. Сейчас новые награды не начисляются</div>`) +
        `<div class="acts"><button type="button" class="pill" data-act="share">${IC.share}<span>Поделиться</span></button>` +
        `<button type="button" class="rnd" aria-label="Скопировать" data-act="copyinvite">${IC.copy}</button></div></section>`;
      const how = on ? ST("Как это работает") + tl([["1", "Друг открывает бота по ссылке", esc(terms.friend || "и получает подарок")],
        ["2", "Начинает пользоваться VPN", esc(terms.when || "")], ["🎁", `Вам ${rub(reward)} на баланс`, earned ? `<b>+${rub(earned)}</b> уже получено` : esc(terms.how || "")]]) : "";
      const stats = ST("Ваши друзья") + cd([E("👥") + "Приглашено" + V(String(invited)), E("💰") + "Получено" + V(rub(earned))]);
      const list = friends.length ? cd(friends.map((f) => E(f.paid ? "✅" : "⏳") + TT(esc(f.name || "друг") + (f.username ? ` · @${esc(f.username)}` : ""), f.paid ? "есть оплата" : "ещё без оплаты"))) : "";
      return hero + how + stats + list + (terms.note ? NOTE(esc(terms.note)) : "");
    },
    sig: (p) => JSON.stringify([me.invited_count, me.referral_earned, me.referrals, me.referral_program_enabled, me.gifts_enabled, me.friend_nft, p && p.tab === "give" ? me.balance_rub : 0]),
  };

  // ---------- NFT gifts for friends ----------
  // Real Telegram collectibles for friends who paid VPN themselves and use it. The gift floats on its own
  // Telegram backdrop (the Lottie «Gift» layer, its pattern behind), the showcase rotates on a timer.
  const NF = "https://nft.fragment.com/gift/";
  const nfImg = (g) => NF + encodeURIComponent(g.slug) + ".webp";
  // A black backdrop is pure black, not Telegram's greyish Onyx Black.
  const NF_BLACK = ["#2a2a2d", "#0e0e10", "#000000"];
  const nfBlack = (g) => (Array.isArray(g.a) ? g.a : []).some((x) => x && x[0] === "Фон" && /black/i.test(String(x[1])));
  const nfBg = (g) => (nfBlack(g) ? NF_BLACK : Array.isArray(g.bg) && g.bg.length === 3 ? g.bg : NF_BLACK).map((c) => /^#[0-9a-f]{6}$/i.test(c) ? c : "#000000");
  const nfGrad = (g) => { const b = nfBg(g); return `radial-gradient(110% 70% at 50% 30%, ${b[0]} 0%, ${b[1]} 55%, ${b[2]} 100%)`; };
  const nfPl = (n, a, b, c) => { const m = n % 10, h = n % 100; return m === 1 && h !== 11 ? a : m >= 2 && m <= 4 && (h < 12 || h > 14) ? b : c; };
  const nfFr = (n) => `${n} ${nfPl(n, "друг", "друга", "друзей")}`;
  const nfDays = (n) => `${n} ${nfPl(n, "день", "дня", "дней")}`;
  const nfNo = (g) => esc(String(g.no || ""));
  // A small picture of a gift. Fragment's pictures carry the grey Onyx backdrop, so a black gift is drawn
  // on pure black from its own animation (first frame), with the picture as the fallback.
  let nfThumbs = [];
  const nfThumb = (g, cls, extra = "") => {
    if (!nfBlack(g)) return `<span class="${cls}"><img src="${nfImg(g)}" alt="">${extra}</span>`;
    nfThumbs.push(g);
    return `<span class="${cls} nf-tb" style="background:${nfGrad(g)}"><span class="nf-tl" data-nft="${nfThumbs.length - 1}"></span>${extra}</span>`;
  };
  let nfLottie = null;
  const nfCache = {};
  function nfLoadLottie() {
    if (window.lottie) return Promise.resolve(window.lottie);
    if (!nfLottie) nfLottie = new Promise((ok, no) => {
      const sc = document.createElement("script");
      sc.src = "https://cdnjs.cloudflare.com/ajax/libs/bodymovin/5.12.2/lottie.min.js";
      sc.onload = () => (window.lottie ? ok(window.lottie) : no(new Error("lottie")));
      sc.onerror = () => { nfLottie = null; no(new Error("lottie")); };
      document.head.appendChild(sc);
    });
    return nfLottie;
  }
  // only = "Gift" keeps just the gift so it floats on the cabinet card; "Pattern,Color Icon" is its pattern; nothing — the whole Telegram card.
  function nfPlay(box, g, only, frozen) {
    if (!box || !g) return;
    const still = () => { if (box.isConnected && (!only || only === "Gift")) box.innerHTML = `<img src="${nfImg(g)}" alt="">`; };
    if (!only) still();
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) { still(); return; }
    const data = nfCache[g.slug] = nfCache[g.slug] || fetch(NF + encodeURIComponent(g.slug) + ".lottie.json").then((r) => { if (!r.ok) throw new Error("gift"); return r.json(); });
    Promise.all([nfLoadLottie(), data]).then(([L, d0]) => {
      if (!box.isConnected) return;
      const d = JSON.parse(JSON.stringify(d0));
      if (only) d.layers = (d.layers || []).filter((l) => only.split(",").includes(l.nm));
      box.innerHTML = "";
      const a = L.loadAnimation({ container: box, renderer: "svg", loop: true, autoplay: !frozen, animationData: d, rendererSettings: { preserveAspectRatio: "xMidYMid slice" } });
      if (frozen) a.addEventListener("DOMLoaded", () => a.goToAndStop(0, true));
    }).catch(() => { nfCache[g.slug] = null; still(); });
  }
  // Warm everything the gift tab needs as soon as the cabinet loads: the player, every step's animation
  // and picture. Opening «Пригласить» then plays at once instead of waiting on Fragment.
  const nfPics = {};
  function nfPreload(nf) {
    if (!nf || !nf.enabled || !Array.isArray(nf.steps) || !nf.steps.length) return;
    const go = () => {
      nfLoadLottie().catch(() => {});
      nf.steps.forEach((s) => {
        const g = s && s.gift;
        if (!g || !g.slug) return;
        if (!nfPics[g.slug]) { const im = new Image(); im.decoding = "async"; im.src = nfImg(g); nfPics[g.slug] = im; }
        if (!nfCache[g.slug]) nfCache[g.slug] = fetch(NF + encodeURIComponent(g.slug) + ".lottie.json").then((r) => { if (!r.ok) throw new Error("gift"); return r.json(); });
        nfCache[g.slug].catch(() => { nfCache[g.slug] = null; });
      });
    };
    (window.requestIdleCallback || ((f) => setTimeout(f, 300)))(go, { timeout: 1200 });
  }
  const nfLeft = (nf) => Math.max(0, (Date.parse(nf.next_at) || 0) - Date.now());
  function nfFmt(ms, short) {
    const d = Math.floor(ms / 864e5), h = Math.floor(ms % 864e5 / 36e5), m = Math.floor(ms % 36e5 / 6e4), sec = Math.floor(ms % 6e4 / 1e3), z = (x) => String(x).padStart(2, "0");
    if (short) return d ? `${d} д ${h} ч` : `${z(h)}:${z(m)}:${z(sec)}`;
    return `${d ? `${d}<i>д</i>` : ""}${z(h)}<i>:</i>${z(m)}<i>:</i>${z(sec)}`;
  }
  // The step being collected now: the first one not earned yet (−1 when all are earned).
  const nfCur = (nf) => nf.steps.findIndex((s) => s.state === "none");
  const nfFresh = (nf) => { const seen = store.get("nf_period"); return seen != null && seen !== "" && seen !== String(nf.period); };
  function nfInvite(nf) {
    return nfHero(nf) + nfPath(nf) + nfFriends(nf) + nfRules(nf);
  }
  function nfHero(nf) {
    const n = Number(nf.counted) || 0, ci = nfCur(nf), all = ci < 0, last = nf.steps.length - 1;
    const st = nf.steps[all ? last : ci], g = st.gift, bg = nfBg(g);
    const prev = !all && ci > 0 ? nf.steps[ci - 1].need : 0, size = all ? 1 : Math.max(1, st.need - prev), done = all ? 1 : Math.max(0, Math.min(size, n - prev));
    const conf = Array.from({ length: 14 }, (_, i) => `<i style="left:${(i * 37) % 100}%;background:${i % 3 ? "rgba(255,255,255,.7)" : bg[0]};animation-duration:${4 + (i % 5)}s;animation-delay:-${i * .7}s;--dx:${(i % 2 ? 1 : -1) * (8 + i % 4 * 6)}px"></i>`).join("");
    const reward = Number(me.referral_reward_rub) || 50, chk = Number(nf.checking) || 0, soon = Number(nf.checking_left) || 0;
    const attrs = (Array.isArray(g.a) ? g.a : []).map((x) => `<span><i>${esc(x[1])}</i>${esc(x[2])}</span>`).join("");
    return `<section class="hc nf${nfBlack(g) ? " blk" : ""}" style="background:${nfGrad(g)}"><div class="nf-pat" data-nfg="${all ? last : ci}" data-only="Pattern,Color Icon"></div>` +
      `<div class="gs-conf">${conf}</div>` +
      `<div class="nf-top">${me.referral_program_enabled ? `<span class="b">+${rub(reward)} за каждого друга</span>` : "<span></span>"}` +
      `<span class="nf-tmh">${all ? "Все собраны 🏆" : `🔄 <b>${nfFmt(nfLeft(nf), 1)}</b>`}</span></div>${nfFresh(nf) && !all ? '<span class="nf-new">Новый подарок!</span>' : ""}` +
      `<div class="nf-gift" data-act="nfsheet" data-i="${all ? last : ci}"><div class="gs-rays" style="--ray:rgba(255,255,255,.12)"></div><div class="nf-glow"></div><div class="nf-lt" data-nfg="${all ? last : ci}" data-only="Gift"><img src="${nfImg(g)}" alt=""></div></div>` +
      `<div class="K" style="margin-top:2px">${all ? "Вы собрали все подарки" : ci === last ? "Главный подарок" : "Следующий NFT-подарок"}</div><div class="nf-n">${esc(g.name)}</div>` +
      `<div class="nf-rar">${attrs}</div>` +
      (all ? `<div class="nf-lbl" style="justify-content:center"><span>Спасибо, что зовёте друзей 💚</span></div>`
        : `<div class="nf-lbl"><span><b>${done}</b> из ${size} засчитано</span><span>ещё ${nfFr(Math.max(0, st.need - n))}</span></div>`) +
      `<div class="nf-bar">${Array.from({ length: Math.min(size, 40) }, (_, i) => `<i class="${i < done ? "on" : ""}${!all && i === done ? " nx" : ""}"></i>`).join("")}</div>` +
      (chk ? `<div class="nf-wait"><i></i>${nfFr(chk)} на проверке · ${soon ? nfDays(soon) : "сегодня"}</div>` : "") +
      `<div class="acts"><button type="button" class="pill" data-act="share">${IC.share}<span>Поделиться</span></button>` +
      `<button type="button" class="rnd" aria-label="Скопировать" data-act="copyinvite">${IC.copy}</button></div></section>`;
  }
  function nfPath(nf) {
    const n = Number(nf.counted) || 0, ci = nfCur(nf), last = nf.steps.length - 1, ms = nfLeft(nf), span = (Number(nf.period_days) || 3) * 864e5;
    const rows = nf.steps.map((s, i) => {
      const g = s.gift, bg = nfBg(g);
      const c = s.state === "got" ? "got" : s.state === "wait" ? "wait" : i === ci ? "cur" : "lock";
      const pct = c === "cur" ? Math.min(100, n / s.need * 100) : 0;
      const end = c === "got" ? `<span class="nf-bdg ok">получен</span>` : c === "wait" ? `<span class="nf-bdg w">в пути</span>`
        : c === "cur" ? `<span class="nf-lft">ещё <b>${Math.max(0, s.need - n)}</b></span>` : `<span class="nf-lk">🔒</span>`;
      const sub = c === "cur" ? `<span class="nf-pb"><i style="width:${pct}%;background:linear-gradient(90deg, ${bg[0]}, ${bg[1]})"></i></span><span>${n} из ${nfFr(s.need)}</span>`
        : c === "got" ? `<span>#${nfNo(g)} · у вас в Telegram</span>` : c === "wait" ? `<span>#${nfNo(g)} · придёт за сутки</span>` : `<span>за ${nfFr(s.need)}</span>`;
      return `<button type="button" class="nf-rg ${c}${i === last ? " top" : ""}${ci < 0 || i < ci ? " past" : ""}" data-act="nfsheet" data-i="${i}" style="--c1:${bg[0]};--c2:${bg[1]}">` +
        nfThumb(g, "nf-th", c === "got" ? "<em>✓</em>" : "") +
        `<span class="nf-md">${i === last ? '<small class="nf-crown">Главный подарок</small>' : ""}<b>${esc(g.name)}</b><span class="nf-sb">${sub}</span></span><span class="nf-en">${end}</span></button>`;
    }).join("");
    return ST("Подарки за друзей") +
      `<div class="nf-rot${ms < 864e5 ? " soon" : ""}" style="--p:${(100 - ms / span * 100).toFixed(2)}"><div class="nf-ring"><span>🔄</span></div>` +
      `<span class="nf-rt"><span>Новые подарки через</span><span class="nf-tmr">${nfFmt(ms)}</span></span><div class="nf-nx"><i>?</i><i>?</i></div></div>` +
      `<div class="nf-lad${nfFresh(nf) ? " flip" : ""}">${rows}</div>`;
  }
  const NF_COL = ["#e2724f", "#4f9be2", "#9b62d8", "#3cb878", "#e2a23c", "#d8557d", "#3cb0b8"];
  function nfFriends(nf) {
    const list = Array.isArray(nf.friends) ? nf.friends : [], days = Number(nf.check_days) || 7;
    if (!list.length) return ST("Ваши друзья") + cd([E("👋") + TT("Пока никого", "Отправьте ссылку — друг получит подарок на баланс")]);
    const bad = list.filter((x) => x.st === "bad").length, chk = list.filter((x) => x.st === "check").length;
    const rows = list.slice(0, 30).map((x, k) => {
      const name = esc(x.name || "Друг");
      const sub = x.st === "ok" ? "оплатил(а) и пользуется VPN"
        : x.st === "check" ? `проверка · ${Number(x.day) || 0} из ${nfDays(days)} <span class="nf-mb"><i style="width:${Math.min(100, (Number(x.day) || 0) / days * 100)}%"></i></span>`
        : x.st === "bad" ? `не засчитан · ${esc(x.reason || "не прошёл проверку")}`
        : x.st === "old" ? "пришёл до начала акции" : `ещё не оплатил VPN · нужно от ${rub(Number(nf.min_rub) || 100)}`;
      const tag = x.st === "ok" ? ["ok", "есть"] : x.st === "check" ? ["w", "ждём"] : x.st === "bad" ? ["no", "нет"] : ["", "—"];
      return `<div class="rw ${x.st}"><span class="nf-av" style="background:${x.st === "bad" || x.st === "old" ? "#3a3d45" : NF_COL[k % NF_COL.length]}">${esc(Array.from(x.name || "Д")[0] || "Д")}</span>` +
        `<span class="tt"><b>${name}</b><span>${sub}</span></span>${V(`<span class="nf-bdg ${tag[0]}">${tag[1]}</span>`)}</div>`;
    }).join("");
    return ST(`Ваши друзья · ${Number(nf.counted) || 0} засчитано`) + `<div class="cd nf-fw">${rows}</div>` +
      (chk || bad ? NOTE(`${chk ? `${nfFr(chk)} на проверке. ` : ""}${bad ? `${bad} ${nfPl(bad, "аккаунт не засчитан", "аккаунта не засчитаны", "аккаунтов не засчитано")} — это не новые живые пользователи.` : ""}`) : "");
  }
  function nfRules(nf) {
    const days = Number(nf.check_days) || 7, on = Number(nf.online_days) || 0;
    const items = [["Новый человек", "раньше не заходил в бота и пришёл по вашей ссылке"], [`Сам оплатил VPN от ${rub(Number(nf.min_rub) || 100)}`, "своей картой или СБП — не бонусами и не подарком"]];
    if (on) items.push(["Пользуется VPN", `подключался хотя бы ${nfDays(on)} из первых ${days}`]);
    items.push([`${days === 7 ? "Неделя" : nfDays(days)} без возврата`, `засчитываем через ${nfDays(days)} после оплаты`], ["Это не вы", "другая карта, другой телефон и устройство"]);
    return ST("Кто засчитывается") + `<div class="cd nf-chk">${items.map((x, i) => `<div class="tl" style="--i:${i}"><div class="n">✓</div><div><div class="tx">${x[0]}</div><div class="sx">${x[1]}</div></div></div>`).join("")}</div>` +
      NOTE("Подарки выдаём вручную и перед отправкой смотрим каждого друга. За накрутку путь обнуляется.");
  }
  // After a render: animations, the timer, and the reveal for a gift that was just earned.
  let nfTick = 0;
  function nfMount(el) {
    clearInterval(nfTick);
    const thumbs = nfThumbs;
    el.querySelectorAll("[data-nft]").forEach((b) => nfPlay(b, thumbs[Number(b.dataset.nft)], "Gift", true));
    const nf = me && me.friend_nft;
    if (!nf || !nf.enabled || !Array.isArray(nf.steps) || !el.querySelector(".hc.nf")) return;
    el.querySelectorAll("[data-nfg]").forEach((b) => nfPlay(b, (nf.steps[Number(b.dataset.nfg)] || {}).gift, b.dataset.only));
    const span = (Number(nf.period_days) || 3) * 864e5;
    let asked = false;
    nfTick = setInterval(() => {
      if (!el.isConnected) { clearInterval(nfTick); return; }
      const ms = nfLeft(nf);
      el.querySelectorAll(".nf-tmr").forEach((e) => { e.innerHTML = nfFmt(ms); });
      el.querySelectorAll(".nf-tmh b").forEach((e) => { e.textContent = nfFmt(ms, 1); });
      el.querySelectorAll(".nf-rot").forEach((e) => { e.style.setProperty("--p", (100 - ms / span * 100).toFixed(2)); e.classList.toggle("soon", ms < 864e5); });
      if (ms <= 0 && !asked) { asked = true; setTimeout(() => load(true).catch(() => {}), 1500); }
    }, 1000);
    const seenP = store.get("nf_period");
    setTimeout(() => store.set("nf_period", nf.period), 1500);
    if (seenP == null || seenP === "") store.set("nf_period", nf.period);
    const seen = new Set(String(store.get("nf_seen") || "").split(",").filter(Boolean));
    const fresh = (nf.rewards || []).filter((r) => r.status === "wait" && !seen.has(String(r.id)));
    if (fresh.length) {
      fresh.forEach((r) => seen.add(String(r.id)));
      store.set("nf_seen", [...seen].slice(-40).join(","));
      const r = fresh[fresh.length - 1];
      setTimeout(() => { if (el.isConnected) nfReveal(r); }, 450);
    }
  }
  function nfBurst(colors) {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const b = document.createElement("div");
    b.className = "nf-fx";
    b.innerHTML = Array.from({ length: 70 }, (_, i) => `<i style="background:${colors[i % colors.length]};--x:${(Math.random() - .5) * 460}px;--y:${(Math.random() - .25) * 700}px;--r:${Math.random() * 900}deg;animation-delay:${Math.random() * .12}s"></i>`).join("");
    document.body.appendChild(b);
    setTimeout(() => b.remove(), 1900);
  }
  function nfReveal(r) {
    const g = r.gift || {}, bg = nfBg(g);
    const rv = document.createElement("div");
    rv.className = "nf-rv";
    rv.style.setProperty("--rc", bg[0] + "30");
    rv.innerHTML = `<div class="nf-rays"></div><div class="nf-card"><div class="in"><div class="fc"><div class="nf-lt"></div></div><div class="bk">?</div></div></div>` +
      `<div class="t1">Новый NFT-подарок</div><div class="t2">${esc(g.name)} ваш!</div>` +
      `<div class="t3">${nfFr(Number(r.need) || 0)} оплатили VPN и пользуются им. Отправим #${nfNo(g)} в ваш профиль Telegram в течение суток.</div>` +
      `<div class="acts"><button type="button" class="pill"><span>Ура!</span></button></div>`;
    document.body.appendChild(rv);
    nfPlay(rv.querySelector(".nf-lt"), g);
    requestAnimationFrame(() => requestAnimationFrame(() => rv.classList.add("on")));
    setTimeout(() => { nfBurst([bg[0], "#fff", "#f1c94c", "#3ccf74", bg[1]]); notify("success"); }, 1050);
    const close = () => { rv.classList.remove("on"); setTimeout(() => rv.remove(), 400); };
    rv.querySelector(".pill").onclick = () => { haptic(); close(); };
  }
  function nfSheet(g, title, what) {
    if (!g) return;
    closeSheet();
    haptic();
    const el = document.createElement("div");
    el.className = "bsheet nfs";
    el.innerHTML = `<div role="dialog" aria-label="${esc(g.name)}"><div class="grab"></div><section class="hc nf${nfBlack(g) ? " blk" : ""}" style="background:${nfGrad(g)}">` +
      `<div class="gs-rays" style="--ray:rgba(255,255,255,.12);top:calc(50% - 15px)"></div><div class="nf-lt"></div><div class="nf-ttl">${esc(g.name)}<small>${title}</small></div></section>` +
      cd((Array.isArray(g.a) ? g.a : []).map((x) => `<span class="tt"><span style="margin:0">${esc(x[0])}</span><b>${esc(x[1])}</b></span><span class="nf-rr">${esc(x[2])}</span>`)) +
      NOTE(what) + "</div>";
    el.addEventListener("click", (ev) => { if (ev.target === el || ev.target.classList.contains("grab")) closeSheet(); });
    document.body.appendChild(el);
    sheetEl = el;
    call(() => tg.BackButton.show());
    nfPlay(el.querySelector(".nf-lt"), g, "Gift");
  }
  function nfStepSheet(i) {
    const nf = me.friend_nft || {}, s = (nf.steps || [])[i];
    if (!s) return;
    const n = Number(nf.counted) || 0, g = s.gift;
    if (s.state === "got" && s.nft_link && /^https:\/\/t\.me\//.test(s.nft_link)) { haptic(); call(() => tg.openTelegramLink(s.nft_link)); return; }
    const what = s.state === "got" ? "Подарок у вас в профиле Telegram. Его можно оставить, подарить или продать."
      : s.state === "wait" ? "Вы его заработали — отправим в течение суток, придёт сообщение от бота."
      : `Нужно ${nfFr(s.need)}, которые сами оплатили VPN и пользуются им. Осталось ${nfFr(Math.max(0, s.need - n))}.`;
    nfSheet(g, s.state === "none" ? `Коллекционный подарок Telegram · за ${nfFr(s.need)}` : `#${nfNo(g)} · ${s.state === "got" ? "ваш" : "в пути"}`, what);
  }

  // ---------- history ----------
  const BILL = { charge: "VPN", pause: "Пауза тарификации", disable: "Отключение", revive: "Включение", trial: "Подарок", admin_balance: "Баланс",
    admin_grant: "Начисление", trust: "Обещанный платёж", trust_collect: "Возврат обещанного", device_delete: "Удаление устройства", referral: "Бонус за друга",
    referral_payout: "Реферальная награда", referral_revoke: "Возврат за друга", story: "Награда за историю", topup: "Пополнение", router: "Роутер", promo: "Промокод",
    first_bonus: "Бонус за первую оплату", return_bonus: "Бонус за возвращение", gift_sent: "Подарок другу", gift_received: "Подарок от друга", gift_return: "Подарок вернулся" };
  SCR.history = {
    h(p) {
      const data = p.data;
      if (!data) {
        return hc("slate", { cls: "shim", ill: "🧾", h: "История", p: "Загружаю…" }) + `<div class="cd" style="height:150px"></div>`;
      }
      if (data.error) return hc("slate", { ill: "🧾", h: "История", p: esc(data.error), pill: "Повторить", pa: 'data-act="rehistory"' });
      const all = data.items || [];
      const charged = Math.abs(Number(data.charged_rub) || 0);
      const now = new Date(), byDay = [];
      const weekFrom = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 6);
      for (let i = 6; i >= 0; i--) {
        const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - i);
        byDay.push({ key: d.toDateString(), sum: 0 });
      }
      const devs = {};
      all.forEach((e) => {
        const d = parseDate(e.created_at), v = Number(e.amount);
        if (!d || !(v < 0) || d < weekFrom) return;
        const slot = byDay.find((x) => x.key === d.toDateString());
        if (slot) slot.sum += -v;
        if (e.kind === "charge") {
          const k = e.device_title || "Устройство";
          const x = devs[k] || (devs[k] = { sum: 0, n: 0, first: d });
          x.sum += -v; x.n += 1; if (d < x.first) x.first = d;
        }
      });
      const max = Math.max(1, ...byDay.map((x) => x.sum));
      if (!all.length) {
        return hc("slate", { ill: "🧾", h: "Пока пусто", p: "Здесь появятся пополнения, списания за VPN и бонусы", pill: "Пополнить баланс", pi: "plus", pa: 'data-go="topup"' });
      }
      // Seven days of spending, each bar signed with its weekday; today is the bright one.
      const WD = ["вс", "пн", "вт", "ср", "чт", "пт", "сб"];
      const bars = `<div class="bars">${byDay.map((x, i) => `<i class="${i === 6 ? "on" : ""}" style="height:${Math.max(6, Math.round((x.sum / max) * 100))}%;animation-delay:${0.2 + i * 0.06}s"></i>`).join("")}</div>` +
        `<div class="bars-l">${byDay.map((x, i) => `<span class="${i === 6 ? "on" : ""}">${i === 6 ? "сегодня" : WD[new Date(x.key).getDay()]}</span>`).join("")}</div>`;
      // The headline answers «на сколько хватит», the line below — how fast it goes.
      const bal = Math.max(0, Number(me && me.balance_rub) || 0), left = Math.max(0, Number(me && me.days_left) || 0);
      const perDay = Math.round(byDay.slice(-3).reduce((a, x) => a + x.sum, 0) / 3);
      const spend = `списано ${rub(charged)} за 7 дней${perDay ? ` · ${rub(perDay)} в день` : ""}`;
      const hero = me && me.balance_rub != null && charged
        ? hc("slate", { k: `Баланс ${esc(rub(bal))} · хватит на`, n: `${left} ${pl(left, "день", "дня", "дней")}`, p: spend, x: bars })
        : hc("slate", { n: charged ? cnt(charged, " ₽", "−") : "0 ₽", p: `списано за 7 дней`, x: bars });
      // Where the money goes: one row per device over the week.
      const dl = Object.entries(devs).sort((a, b) => b[1].sum - a[1].sum);
      const top = Math.max(1, ...dl.map(([, x]) => x.sum));
      const where = dl.length ? ST("Куда уходят деньги") + cd(dl.map(([name, x]) => {
        const day = Math.round(x.sum / Math.max(1, x.n));
        const since = x.first > new Date(weekFrom.getTime() + 864e5) ? ` · с ${dayLabel(x.first).toLowerCase()}` : "";
        return `<span class="tt"><b>${esc(name)}</b><span>${rub(day)} в день · ${rub(x.sum)} за неделю${esc(since)}</span><span class="hm"><i style="width:${Math.max(6, Math.round(x.sum / top * 100))}%"></i></span></span>`;
      })) : "";
      // Filter chips, then the feed: one day's VPN charges fold into one line.
      const F = p.filter || "all";
      const KIND = (k) => k === "charge" || k === "trust_collect" || k === "device_delete" ? "out" : k === "topup" || k === "router" ? "in" : "bonus";
      const chips = `<div class="hf">${[["all", "Все"], ["out", "Списания"], ["in", "Пополнения"], ["bonus", "Бонусы"]].map(([v, t]) =>
        `<button type="button" class="${F === v ? "on" : ""}" data-act="hfilter" data-v="${v}">${t}</button>`).join("")}</div>`;
      const items = all.filter((e) => F === "all" || (KIND(e.kind) === F && (F !== "bonus" || Number(e.amount) > 0)));
      const groups = [];
      items.forEach((e) => {
        const d = parseDate(e.created_at);
        const label = d ? dayLabel(d) : "Ранее";
        let g = groups[groups.length - 1];
        if (!g || g.label !== label) { g = { label, rows: [], vpn: null }; groups.push(g); }
        const v = Number(e.amount);
        if (e.kind === "charge" && v < 0) {
          if (!g.vpn) { g.vpn = { sum: 0, devs: new Set(), at: d, i: g.rows.length }; g.rows.push(null); }
          g.vpn.sum += -v; g.vpn.devs.add(e.device_title || "");
          return;
        }
        const sub = [e.device_title, e.note, d ? timeHM(d) : ""].filter(Boolean).map(esc).join(" · ");
        const amt = Number.isFinite(v) && v ? `<span class="${v > 0 ? "pos" : "neg"}">${v > 0 ? "+" : "−"}${rub(Math.abs(v))}</span>` : "";
        g.rows.push(TT(esc(BILL[e.kind] || "Операция"), sub) + V(amt));
      });
      groups.forEach((g) => {
        if (!g.vpn) return;
        const n = g.vpn.devs.size;
        g.rows[g.vpn.i] = TT("VPN за день", [n > 1 ? `${n} ${pl(n, "устройство", "устройства", "устройств")}` : esc([...g.vpn.devs][0] || ""), g.vpn.at ? timeHM(g.vpn.at) : ""].filter(Boolean).join(" · ")) +
          V(`<span class="neg">−${rub(g.vpn.sum)}</span>`);
      });
      const feed = groups.length ? groups.map((g) => ST(g.label) + cd(g.rows)).join("") : NOTE("За последний месяц таких операций нет");
      // This month in three numbers.
      const MONTHS = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"];
      const tot = { in: 0, bonus: 0, out: 0 };
      all.forEach((e) => {
        const d = parseDate(e.created_at), v = Number(e.amount);
        if (!d || !v || d.getMonth() !== now.getMonth() || d.getFullYear() !== now.getFullYear()) return;
        const k = KIND(e.kind);
        if (k === "in" && v > 0) tot.in += v;
        else if (k === "out" && v < 0) { if (e.kind === "charge") tot.out += -v; }
        else if (v > 0) tot.bonus += v;
      });
      const month = tot.in || tot.bonus || tot.out ? ST(MONTHS[now.getMonth()]) + cd([
        tot.in ? TT("Пополнено") + V(`<span class="pos">+${rub(tot.in)}</span>`) : "",
        tot.bonus ? TT("Бонусы и награды") + V(`<span class="pos">+${rub(tot.bonus)}</span>`) : "",
        tot.out ? TT("Списано за VPN") + V(`−${rub(tot.out)}`) : "",
      ]) : "";
      return hero + where + chips + feed + month;
    },
    on(el, p) { if (!p.data) loadHistory(); },
  };
  async function loadHistory() {
    let data;
    try { data = await api("/api/billing"); } catch (e) { data = { error: e.message || "Не удалось загрузить историю" }; }
    if (cur && cur.key === "history") { cur.params.data = data; rerender(false); }
  }

  // ---------- support ----------
  SCR.support = {
    h(p) {
      const t = p.ticket;
      const status = t ? ({ open: "ждём ответ", pending: "есть ответ", closed: "закрыт" }[t.status] || "") : "онлайн";
      const reply = Number(p.reply) || 0;
      const eta = reply ? `<div class="sp-eta"><i></i>Обычно отвечаем за ${reply < 60 ? `${reply} мин` : `${Math.round(reply / 60)} ${pl(Math.round(reply / 60), "час", "часа", "часов")}`}</div>` : "";
      const hero = hc("green", { cls: "compact", rb: status, ill: FROG(64), h: "Поддержка", p: (t ? `Обращение №${t.id} · ответ придёт сюда и\u00a0в\u00a0чат с\u00a0ботом` : "Ответ придёт сюда и\u00a0в\u00a0чат с\u00a0ботом") + eta });
      let chat = "";
      const msgs = (t && t.messages) || [];
      if (!p.loaded) chat = `<div class="empty"><span class="typing"><span></span><span></span><span></span></span></div>`;
      else if (!msgs.length) {
        chat = `<div class="empty">${support.context ? "Опишите, что не получилось. Устройство, приложение и этап настройки приложим сами." :
          t && t.status === "closed" ? "Нужна помощь? Выберите тему или напишите — откроем новое обращение." : "Что случилось? Выберите тему или опишите своими словами"}</div>` +
          (support.context ? "" : `<div class="sp-topics">${SP_TOPICS.map(([e, label], i) => `<button type="button" data-act="sptopic" data-v="${i}">${e} ${label}</button>`).join("")}</div>`);
      } else {
        let last = "";
        msgs.forEach((m) => {
          const d = parseDate(m.created_at);
          if (d && dayLabel(d) !== last) { last = dayLabel(d); chat += `<div class="day">${last}</div>`; }
          const op = m.author === "admin";
          const atts = (m.attachments || []).map((a) => ((a.kind === "photo" || String(a.mime || "").startsWith("image/")) && a.url
            ? `<button type="button" class="sp-img" data-act="spzoom" data-v="${esc(a.url)}"><img src="${esc(a.url)}" alt="${esc(a.original_name || "Фото")}"></button>`
            : `<a class="file" href="${esc(a.url || "#")}" target="_blank" rel="noopener">${esc(a.original_name || "Файл")}</a>`)).join("");
          const tick = op ? "" : `<b class="sp-tk${spSeen(t, d) ? " seen" : ""}" data-at="${d ? d.getTime() : 0}">${spSeen(t, d) ? "✓✓" : "✓"}</b>`;
          chat += `<div class="bub ${op ? "op" : "me"}">${op ? '<span class="who">Поддержка</span>' : ""}${esc(m.body || "")}${atts}${d ? `<i>${timeHM(d)}${tick}</i>` : ""}</div>`;
        });
        chat += `<div class="bub op sp-typing" id="sptyping"${t && t.typing ? "" : " hidden"}><span class="typing"><span></span><span></span><span></span></span>Поддержка печатает</div>`;
      }
      let actions = "";
      if (t && t.status !== "closed" && msgs.length) actions = `<button type="button" class="lnk" data-act="tclose">Вопрос решён</button>`;
      if (t && t.status === "closed") {
        actions = t.support_rating ? NOTE(`Спасибо! Ваша оценка: ${t.support_rating} из 5`, true)
          : NOTE("Как вам помощь?", true) + `<div class="rate">${[1, 2, 3, 4, 5].map((r) => `<button type="button" data-act="trate" data-v="${r}">${r} ★</button>`).join("")}</div>`;
      }
      // Pictures waiting to be sent show as thumbnails; other files by name.
      const files = support.files.map((f, i) => String(f.type || "").startsWith("image/")
        ? `<button type="button" class="sp-th" data-act="unfile" data-v="${i}" aria-label="Убрать ${esc(f.name)}"><img src="${spThumb(f)}" alt=""><b>✕</b></button>`
        : `<button type="button" data-act="unfile" data-v="${i}">📎 ${esc(f.name)} ✕</button>`).join("");
      return hero + `<div class="chat" id="chat">${chat}</div>` + actions +
        `<div style="height:8px"></div>` + cd([[E("💡") + "Частые вопросы" + V(CV), 'data-go="faq"']]) +
        `<div class="bot"><div class="files">${files}</div><div class="compose">` +
        `<button type="button" class="rnd" aria-label="Прикрепить файл" data-act="attach">${IC.clip}</button>` +
        `<textarea id="msg" rows="1" placeholder="${support.context ? "Что не получилось?" : "Написать"}">${esc(support.draft)}</textarea>` +
        `<button type="button" class="rnd send" aria-label="Отправить" data-act="send">${IC.send}</button></div>` +
        `<input type="file" id="files" multiple hidden accept="image/*,.pdf,.txt,.log,.zip"></div>`;
    },
    bot: true,
    on(el, p) {
      const ta = el.querySelector("#msg");
      const fit = () => { ta.style.height = "auto"; ta.style.height = Math.min(ta.scrollHeight, 140) + "px"; };
      ta.addEventListener("input", () => { support.draft = ta.value; fit(); });
      ta.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey && isPc()) { e.preventDefault(); ACT.send(); } });
      fit();
      el.querySelector("#files").addEventListener("change", (e) => {
        Array.from(e.target.files || []).forEach((f) => { if (support.files.length < 5) support.files.push(f); });
        e.target.value = "";
        rerender(false);
      });
      if (!p.loaded) loadTickets();
      scrollChat();
      clearInterval(support.poll);
      // Faster while a dialog is open, so «печатает» and the answer show up quickly.
      support.poll = setInterval(() => { if (cur && cur.key === "support") loadTickets(true); else clearInterval(support.poll); }, p.ticket && p.ticket.status !== "closed" ? 4000 : 8000);
    },
  };
  function scrollChat() { requestAnimationFrame(() => window.scrollTo(0, document.body.scrollHeight)); }
  const SP_TOPICS = [
    ["🔌", "Не подключается", "VPN не подключается. "],
    ["🐢", "Медленно работает", "VPN работает медленно. "],
    ["💳", "Не пришли деньги", "Пополнил баланс, но деньги не пришли. "],
    ["📱", "Новое устройство", "Хочу подключить ещё одно устройство. "],
    ["❓", "Другое", ""],
  ];
  // «✓✓» once support has opened the dialog after the message was sent.
  const spSeen = (t, d) => { const seen = parseDate(t && t.admin_seen_at); return !!(seen && d && seen >= d); };
  const spThumbs = new WeakMap();
  const spThumb = (f) => { if (!spThumbs.has(f)) spThumbs.set(f, URL.createObjectURL(f)); return spThumbs.get(f); };
  // Typing and read marks change often: patch them in place so the composer keeps focus and caret.
  function spPatch(t) {
    if (!cur || !cur.el) return;
    const ty = cur.el.querySelector("#sptyping");
    if (ty) { const was = ty.hidden; ty.hidden = !(t && t.typing); if (was && !ty.hidden) scrollChat(); }
    cur.el.querySelectorAll(".sp-tk").forEach((b) => {
      const ok = spSeen(t, new Date(Number(b.dataset.at)));
      b.classList.toggle("seen", ok);
      b.textContent = ok ? "✓✓" : "✓";
    });
  }
  const spKey = (t) => JSON.stringify(t ? { ...t, typing: 0, admin_seen_at: 0 } : null);
  async function loadTickets(silent) {
    try {
      const data = await api("/api/tickets");
      if (!cur || cur.key !== "support") return;
      const before = spKey(cur.params.ticket);
      cur.params.ticket = data.current || null;
      cur.params.reply = data.reply_minutes || 0;
      const changed = !cur.params.loaded || before !== spKey(cur.params.ticket);
      cur.params.loaded = true;
      if (changed) { rerender(false); scrollChat(); } else spPatch(cur.params.ticket);
    } catch (e) {
      if (!silent) showErr(e);
      if (cur && cur.key === "support" && !cur.params.loaded) { cur.params.loaded = true; rerender(false); }
    }
  }

  // ---------- faq ----------
  SCR.faq = {
    h() {
      const items = (me.faq || []).filter((x) => x && x.q);
      return hc("orange", { ill: "💡", h: "Частые вопросы", p: "Подключение, оплата и деньги", pill: "Написать в поддержку", pi: "msg", pa: 'data-act="support"' }) +
        (items.length ? ST("Популярное") + `<div class="cd">${items.map((q, i) => `<button type="button" class="rw q${i ? "" : " open"}" data-act="acc"><span class="qh"><b>${esc(q.q)}</b>${V(CV)}</span><span class="ans">${esc(q.a || "")}</span></button>`).join("")}</div>`
          : NOTE("Вопросов пока нет — напишите нам, ответим.", true));
    },
  };

  // ---------- settings ----------
  SCR.settings = {
    live: true,
    h() {
      const u = me.user || {};
      const photo = u.photo ? `<span class="frogw"><img class="frog" src="${esc(u.photo)}" width="80" height="80" style="width:80px;height:80px" alt="" onerror="this.src='/icons/frog.png'"></span>` : FROG(80);
      const quiet = Boolean(me.quiet_notifications);
      const who = [u.username ? "@" + esc(u.username) : "", u.id ? `ID ${esc(u.id)}` : ""].filter(Boolean).join(" · ");
      return hc("slate", { ill: photo, h: esc(u.name || "Профиль"), p: who, pill: "Поддержка", pi: "msg", pa: 'data-act="support"', r: "copy", rl: "Скопировать ID", ra: 'data-act="copyid"' }) +
        (me.notification_settings_available ? ST("Уведомления") + cd([["Режим тишины" + `<span class="tg ${quiet ? "" : "off"}"></span>`, 'data-act="quiet"']]) +
          NOTE("Без приглашений, акций и напоминаний. Сообщения о деньгах, доступе и ответы поддержки останутся.") : "") +
        ST("Ещё") +
        cd([[E("🧾") + "История операций" + V(CV), 'data-go="history"'],
          me.autopay ? [E("🔁") + "Автопополнение" + V((apOn() ? "включено " : me.autopay.status === "pending" ? "ждёт оплаты " : "выключено ") + CV), 'data-go="autopay"'] : null,
          me.promo_enabled ? [E("🎟️") + "Промокод" + V(CV), 'data-go="promo"'] : null,
          [E("💡") + "Частые вопросы" + V(CV), 'data-go="faq"'],
          me.cabinet_site_url && inTelegram() ? [E("💻") + "Кабинет в браузере" + V(esc(siteHost()) + " " + CV), 'data-act="browserHow"'] : null,
          me.legal && me.legal.offer ? [E("📄") + "Пользовательское соглашение" + V(CV), `data-act="link" data-v="${esc(me.legal.offer)}"`] : null,
          me.legal && me.legal.privacy ? [E("🔒") + "Политика конфиденциальности" + V(CV), `data-act="link" data-v="${esc(me.legal.privacy)}"`] : null]);
    },
    sig: () => JSON.stringify([me.user, me.quiet_notifications, me.notification_settings_available, me.promo_enabled, me.cabinet_site_url, me.autopay]),
  };

  // ---------- promo ----------
  SCR.promo = {
    h(p) {
      return hc("gold", { ill: "🎟️", h: "Промокод", p: p.result ? esc(p.result) : "Введите код — бонус придёт на баланс",
        x: `<div class="inp${p.ok ? " ok" : ""}" id="pin"><input id="promoInput" autocapitalize="characters" autocomplete="off" placeholder="Код" maxlength="40" value="${esc(p.code || "")}"><span class="sfx">${p.ok ? "✓ применён" : ""}</span></div>`,
        pill: p.ok ? "Готово" : "Применить", pa: p.ok ? 'data-act="back"' : 'data-act="promo"' }) +
        NOTE(`Баланс ${rub(me.balance_rub)}`, true);
    },
    on(el) {
      const i = el.querySelector("#promoInput");
      i.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); ACT.promo(); } });
    },
  };

  // ---------- автопополнение (app/autopay.py, docs/autopay/autopay-final.html) ----------
  // CISPay subscriptions: SBP only, CISPay charges on its own schedule. No pause, no «skip once», no amount change.
  const apOn = () => Boolean(me.autopay && me.autopay.status === "active");
  const apNext = () => parseDate((me.autopay || {}).next_charge_at);
  const apLead = () => days((me.autopay || {}).lead_days || 2);
  const apOpt = (n) => ((me.autopay || {}).options || []).find((o) => o.amount === n && o.ok);
  // Under the balance on the home card (screens 2, 8, 15): the date of the next top-up, «не сработало» or the offer.
  function apHero(alert) {
    const a = me.autopay;
    if (!a) return {};
    const chip = (t) => `<button type="button" class="chip apchip" data-go="autopay">${t} ›</button>`;
    if (a.status === "active") return { x: chip(`🔁 ${apNext() ? dateLong(apNext()) + " пополним" : "Пополним"} ${rub(a.amount)}`) };
    if (a.status === "pending") return { x: chip("🔁 Автопополнение ждёт оплаты") };
    if (!alert) return {};
    if (a.failed) return { x: `<div class="chip apchip warn">⚠️ Автопополнение не сработало</div>`, s2: "Включить снова", s2a: 'data-go="autopay"' };
    if (a.offer) return { s2: "🔁&nbsp;Автопополнение", s2a: 'data-go="autopay"' };
    return {};
  }
  const apSettingsLine = () => !me.autopay ? "" : apOn() ? "Автопополнение включено" : me.autopay.status === "pending" ? "Автопополнение ждёт оплаты" : "";
  function apHistory(a) {
    if (!(a.charges || []).length) return "";
    return ST("История") + cd(a.charges.map((c) => {
      const d = parseDate(c.at);
      return `${E(c.ok ? "✓" : "⏳")}${TT((d ? dateLong(d) : "") + (c.auto ? " · авто" : ""), "")}${V("+" + rub(c.amount))}`;
    }));
  }
  SCR.autopay = {
    live: true,
    h(p) {
      const a = me.autopay;
      if (!a) return hc("slate", { ill: "🔁", h: "Автопополнение", p: "Пока недоступно" });
      // Screen 16: on.
      if (a.status === "active" && !p.pick) {
        const d = apNext();
        return hc("green", { rb: "включено", ill: "🔁", n: rub(a.amount), p: `${d ? "около " + dateLong(d) + " · " : ""}через СБП` }) +
          `<div style="height:12px"></div>` + cd([[E("⚡") + TT("Автопополнение", `когда останется ${apLead()}`) + `<span class="tg"></span>`, 'data-act="apOff"']]) +
          ST("Настройки") +
          cd([`${E("💰")}${TT("Сумма", "другая сумма — выключите и включите заново")}${V(rub(a.amount))}`,
            `${E("⚡")}${TT("Способ оплаты", "привязка СБП в вашем банке")}${V("СБП")}`]) +
          apHistory(a);
      }
      // Screen 5 when they come back before paying.
      if (a.status === "pending" && a.pay_url && !p.pick) {
        return hc("sbp", { cls: "shim", rb: "ждём", ill: SBPBIG(60), n: rub(a.amount), p: "Ждём оплату · обычно до минуты",
          pill: "Оплатить через СБП", pa: 'data-act="apPay"', r: "ref", rl: "Проверить", ra: 'data-act="refresh"' }) +
          ST("Как это работает") +
          tl([[CHK(22), "Счёт создан", `${rub(a.amount)} · СБП`, "ok"], ["2", "Подтверждение в банке", "<b>подтвердите в приложении банка</b>", "run"],
            ["3", "Включим автопополнение", "сразу после оплаты"]]) +
          NOTE("Если оплата не пройдёт, ничего не включится.", true) +
          `<button type="button" class="lalt" data-act="apPick">Выбрать другую сумму</button>`;
      }
      // Screen 18: was on, now off.
      if (a.was_on && !p.pick) {
        return hc("slate", { rb: "выключено", ill: "🔁", n: rub(a.amount || 0),
          p: a.failed && a.ended_reason ? `Не сработало: ${esc(a.ended_reason)}` : "автопополнение выключено" }) +
          `<div style="height:12px"></div>` + cd([[E("⚡") + TT("Выключено", "пополняйте вручную, когда нужно") + `<span class="tg off"></span>`, 'data-act="apPick"']]) +
          apHistory(a);
      }
      // Screen 4: turning on — the payment that tops up is the one that switches it on.
      const pick = Number(p.amount) || a.default || 300;
      const opt = (a.options || []).find((o) => o.amount === pick) || {};
      return hc("green", { k: "🔁&nbsp;Пополнить и включить", n: `<span>${rub(pick)}</span>`, p: `≈ ${days(opt.days || 0)} VPN за раз`,
        x: `<div class="chp">${(a.options || []).map((o) => `<button type="button" data-act="apAmt" data-v="${o.amount}" class="${o.amount === pick ? "on" : ""}"${o.ok ? "" : ' disabled style="opacity:.4"'}>${fmt(o.amount)}</button>`).join("")}</div>`,
        pill: `Оплатить ${rub(pick)} и включить`, pa: 'data-act="apStart"', s2: "Оплатить один раз", s2a: 'data-act="apOnce"' }) +
        ST("Что будет дальше") +
        tl([[CHK(22), `Сегодня — оплата ${rub(pick)}`, "через СБП, она запомнится", "ok"],
          ["🔔", "За день напомним", "можно изменить или отключить"],
          ["🔁", `Пополним на ${rub(pick)}`, `когда останется ${apLead()}`]]) +
        ST("Способ оплаты") +
        cd([`${E("⚡")}${TT("СБП", "для автопополнения нужна СБП")}${V(RD(true))}`,
          `<span style="opacity:.55;display:contents">${E("💳")}${TT("Карта, Stars и TON", "только разовая оплата")}</span>`]) +
        NOTE("Автопополнение работает через СБП. Отключить — в любой момент в боте или в кабинете" +
          (me.legal && me.legal.offer ? ` · <button type="button" class="ulink" data-act="link" data-v="${esc(me.legal.offer)}">Условия</button>` : ""), true);
    },
    sig: () => JSON.stringify(me.autopay || null),
  };
  // Screen 3: a quiet card under the payment success, for people who top up before the warnings come.
  function apQuiet(el) {
    const a = me.autopay;
    if (!a || !a.offer || pay.kind === "autopay" || (curMethod() || {}).id !== "sbp" || !cur || cur.el !== el || el.querySelector(".apq")) return false;
    const n = apOpt(pay.amount) ? pay.amount : a.default;
    const box = document.createElement("div");
    box.className = "cd apq";
    box.innerHTML = `<div class="apq-h">🔁 Пополнять так же автоматически?</div>` +
      `<div class="apq-p">Когда останется ${apLead()}, пополним на ${rub(n)} через СБП. За день напомним в боте.</div>` +
      `<div class="apq-b"><button type="button" class="bbtn" data-go="autopay" data-amount="${n}">Включить</button><button type="button" class="bbtn sec" data-act="apQuietNo">Не сейчас</button></div>` +
      `<div class="apq-f">Отключить — в любой момент${me.legal && me.legal.offer ? ` · <button type="button" class="ulink" data-act="link" data-v="${esc(me.legal.offer)}">Условия</button>` : ""}</div>`;
    const note = el.querySelector(".note");
    if (note) note.replaceWith(box); else el.appendChild(box);
    T(() => box.scrollIntoView({ behavior: reduced() ? "auto" : "smooth", block: "nearest" }), 250);
    return true;
  }
  // Screen 6: the money came and autopay is on.
  function apPaid(el) {
    const a = me.autopay || {}, d = apNext();
    const h = el.querySelector(".hc");
    if (h) h.querySelector(".P").insertAdjacentHTML("afterend", `<div class="chip apchip">🔁 Автопополнение включено</div>`);
    const box = document.createElement("div");
    box.innerHTML = ST("Следующее пополнение") +
      tl([["🔔", d ? `${dateLong(new Date(d.getTime() - 864e5))} напомним в боте` : "За день напомним в боте", "можно изменить или отключить"],
        ["🔁", d ? `${dateLong(d)} — ${rub(a.amount || pay.amount)}` : `Пополним на ${rub(a.amount || pay.amount)}`, d ? "через СБП" : `когда останется ${apLead()}`]]) +
      cd([[E("⚙️") + "Изменить или отключить" + V(CV), 'data-go="autopay"']]);
    const note = el.querySelector(".note");
    if (note) note.replaceWith(box); else el.appendChild(box);
  }

  // ---------- promised payment ----------
  SCR.promise = {
    live: true,
    h() {
      const t = me.trust || {};
      const fee = Number(t.fee) || 0;
      if (t.open) {
        const due = parseDate(t.open.due_at);
        return hc("orange", { rb: "включён", ill: "🤝", h: "Обещанный платёж", p: `Вернуть ${rub(t.open.amount)}${due ? ` до ${dateLong(due)}` : ""}`,
          pill: "Пополнить", pi: "plus", pa: 'data-go="topup"' }) +
          ST("Как это работает") + tl([[CHK(22), "Включили", "<b>VPN работает</b>", "ok"], ["2", "Пополните до срока", "долг спишется сам"], ["3", "Готово", "можно снова взять, когда понадобится"]]);
      }
      return hc("orange", { ill: "🤝", h: "Обещанный платёж", p: t.available ? `VPN поработает ${days(t.days)} — оплатите позже` : esc(t.reason || "Сейчас обещанный платёж недоступен"),
        pill: "Включить", pd: !t.available, pa: 'data-act="trust"' }) +
        ST("Как это работает") +
        tl([["1", "Включаете", `<b>+${rub(t.amount || 0)}</b> на баланс сразу`],
          ["2", `${days(t.days || 0)} в долг`, fee ? `за услугу ещё ${rub(fee)}` : "без комиссии"],
          ["3", `Через ${days(t.days || 0)} спишем ${rub(t.repay || (t.amount || 0) + fee)}`, "даже если баланс уйдёт в минус"]]);
    },
    sig: () => JSON.stringify(me.trust || null),
  };

  // ---------- service screens ----------
  SCR.boot = { h: () => `<div class="boot">${hc("", { cls: "shim", ill: "" })}<div style="height:22px"></div><div class="cd"></div></div>`, bare: true };
  SCR.fail = { h: (p) => hc("red", { ill: "⚠️", h: "Не удалось загрузить", p: esc(p.msg || "Проверьте интернет и попробуйте ещё раз"), pill: "Повторить", pa: 'data-act="retry"' }), bare: true };
  SCR.maint = { h: (p) => hc("slate", { ill: p.blocked ? "🔒" : "🛠️", h: p.blocked ? "Доступ ограничен" : "Технические работы", p: esc(p.notice || "Скоро вернёмся") }), bare: true };
  // Browser login. Main way: «Войти через Telegram» (on a computer also a QR code) opens the bot with a ready
  // request, the person taps «Да, это я» and this page logs in by itself. By nickname is the fallback.
  const TGI = '<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><path d="M21.5 4.3 2.9 11.5c-1.3.5-1.3 1.2-.2 1.6l4.8 1.5 1.8 5.6c.2.6.4.8.9.8.4 0 .6-.2.9-.5l2.3-2.2 4.7 3.5c.9.5 1.5.2 1.7-.8l3.1-14.6c.3-1.3-.5-1.9-1.4-1.5zM8.3 14.2l9.6-6c.5-.3.9-.1.5.2l-7.9 7.2-.3 3.4-1.9-4.8z" fill="#fff"/></svg>';
  SCR.login = {
    bare: true,
    h(p) {
      if (p.nick) {
        return hc("blue", { cls: p.waiting ? "shim" : "", ill: FROG(78), h: "Вход по нику", p: esc(p.msg || "Введите ваш логин Telegram"),
          x: `<div class="inp"><input id="loginUser" autocomplete="username" autocapitalize="off" placeholder="@username"${p.waiting ? " disabled" : ""}></div>`,
          pill: p.waiting ? "Ждём подтверждения…" : "Войти", pd: p.waiting, pa: 'data-act="login"' }) +
          NOTE("Пришлём запрос на вход в чат с ботом — подтвердите его там.", true) +
          `<button type="button" class="lalt" data-act="loginTg">Войти через Telegram без ника</button>`;
      }
      const pc = isPc();
      // On a phone tg:// opens the app and this tab stays put, so after «Да, это я» the person comes back to it.
      // A computer opens t.me in a new tab (Telegram Desktop or the web version), the QR always carries t.me.
      const btn = p.link ? (pc ? `<a class="tgbtn" href="${esc(p.link)}" target="_blank" rel="noopener" data-act="loginOpen">`
        : `<a class="tgbtn" href="${esc(tgApp(p.link))}" data-act="loginOpen">`) + `${TGI}<span>Войти через Telegram</span></a>` : "";
      const qr = pc && p.link ? `<div class="lqr" aria-label="QR-код для входа"></div>` : "";
      const msg = p.msg || (p.failed ? "Не получилось подготовить вход. Обновите страницу или войдите по нику."
        : pc ? "Наведите камеру телефона на код и нажмите «Да, это я» в Telegram" : "Нажмите кнопку и подтвердите вход в Telegram");
      return hc("blue", { cls: p.link || p.failed ? "" : "shim", ill: qr ? "" : FROG(78), h: "Вход в кабинет", p: esc(msg),
        x: qr + btn + (p.opened ? `<div class="lwait"><span class="lspin"></span>Ждём «Да, это я» в Telegram…</div>` : "") }) +
        `<button type="button" class="lalt" data-act="loginNick">Войти по нику</button>`;
    },
    on(el, p) {
      if (p.nick) {
        const i = el.querySelector("#loginUser");
        if (!i.disabled) setTimeout(() => i.focus(), 60);
        i.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); ACT.login(); } });
        return;
      }
      if (!p.link && !p.failed) { tgLogin(); return; }
      const box = el.querySelector(".lqr");
      if (box) qrLib().then(() => {
        const q = qrcode(0, "M"); q.addData(p.link); q.make();
        box.innerHTML = q.createSvgTag({ cellSize: 4, margin: 0, scalable: true });
      }).catch(() => box.remove());
    },
  };
  function tgApp(link) {
    const m = String(link).match(/^https:\/\/t\.me\/([A-Za-z0-9_]+)\?start=([A-Za-z0-9_-]+)$/);
    return m ? `tg://resolve?domain=${m[1]}&start=${m[2]}` : link;
  }
  let qrLoad = null;
  function qrLib() {
    if (typeof qrcode === "function") return Promise.resolve();
    qrLoad = qrLoad || new Promise((ok, fail) => {
      const sc = document.createElement("script"); sc.src = "/qrcode.min.js"; sc.onload = ok; sc.onerror = () => { qrLoad = null; fail(); };
      document.head.appendChild(sc);
    });
    return qrLoad;
  }

  // =====================================================================
  // engine
  // =====================================================================
  function sparkle(el) {
    el.querySelectorAll(".hc").forEach((h, k) => {
      if (!h.className.match(/blue|green|indigo|purple|teal|orange|red|slate|gold/)) return;
      const W = Math.max(260, h.clientWidth || 360);
      for (let i = 0; i < 12; i++) {
        const x = (i * 71 + k * 37 + (cur ? cur.key.length : 3) * 13) % (W - 30) + 10, y = (i * 53 + k * 29) % 170 + 12, s = [6, 10, 14, 8][i % 4];
        if (Math.abs(x - W / 2) < 70 && y > 40) continue;
        const d = document.createElement("div");
        d.className = "sp";
        d.style.cssText = `left:${x}px;top:${y}px;opacity:${[0.5, 0.8, 0.35, 0.6][i % 4]};animation-delay:${(i * 0.37) % 2.6}s;animation-duration:${2.2 + (i % 3) * 0.6}s`;
        d.innerHTML = i % 3 ? STAR(s) : '<div style="width:3px;height:3px;border-radius:9px;background:#fff"></div>';
        h.appendChild(d);
      }
    });
  }
  function counts(el) {
    el.querySelectorAll("[data-count]").forEach((e) => countTo(e, Number(e.dataset.from) || 0, Number(e.dataset.count), e.dataset.suf, e.dataset.pre));
  }
  function countTo(e, from, to, suf = "", pre = "") {
    if (from === to) { e.textContent = pre + fmt(to) + suf; return; }
    const t0 = performance.now();
    (function f() {
      const k = Math.min(1, (performance.now() - t0) / 900), x = from + (to - from) * (1 - (1 - k) ** 3);
      e.textContent = pre + fmt(x) + suf;
      if (k < 1) requestAnimationFrame(f);
    })();
  }
  function build(key, params) {
    const s = SCR[key];
    const el = document.createElement("div");
    el.className = "scr" + (s.bot ? " has-bot" : "");
    el.dataset.k = key;
    el.innerHTML = s.h(params);
    return el;
  }
  function stopScreen() {
    timers.splice(0).forEach(clearTimeout);
    clearInterval(support.poll);
  }
  function go(key, params = {}, dir = "f") {
    if (!SCR[key]) return;
    if (sheetEl) { sheetEl.remove(); sheetEl = null; }
    stopScreen();
    if (dir === "f" && cur && !SCR[cur.key].bare) stack.push({ key: cur.key, params: cur.params });
    if (dir === "x") stack = [];
    const r = root();
    const el = build(key, params);
    const old = cur && cur.el;
    if (old && dir !== "x") {
      const y = scrollY;
      old.classList.add("ghost", dir === "b" ? "leaveB" : "leave");
      old.style.top = `${-y}px`;
      setTimeout(() => old.remove(), 440);
      el.classList.add(dir === "b" ? "enterB" : "enter");
    } else {
      if (old) old.remove();
      el.classList.add("fade");
    }
    r.appendChild(el);
    window.scrollTo(0, 0);
    cur = { key, params, el, sig: SCR[key].sig && me ? SCR[key].sig(params) : "" };
    sparkle(el);
    counts(el);
    if (SCR[key].on) SCR[key].on(el, params);
    syncBack();
  }
  function back() {
    haptic();
    if (sheetEl) { closeSheet(); return; }
    const prev = stack.pop();
    if (!prev) { if (cur && cur.key !== "home") go("home", {}, "b"); return; }
    if (prev.key === "wait") { back(); return; }
    go(prev.key, prev.params, "b");
  }
  function home() { stack = []; go("home", {}, cur && cur.key !== "home" ? "b" : "x"); stack = []; syncBack(); }
  // Repaint the current screen in place after fresh data, without replaying the entrance.
  function rerender(still = true) {
    if (!cur) return;
    const s = SCR[cur.key];
    const el = build(cur.key, cur.params);
    if (still) el.classList.add("still");
    cur.el.replaceWith(el);
    cur.el = el;
    sparkle(el);
    if (!still) counts(el);
    if (s.on && cur.key !== "home") s.on(el, cur.params);
  }
  function syncBack() {
    const show = Boolean(sheetEl || (cur && cur.key !== "home" && !SCR[cur.key].bare));
    call(() => (show ? tg.BackButton.show() : tg.BackButton.hide()));
    const wb = document.getElementById("webBack");
    if (wb) wb.hidden = !(show && !inTelegram());
    document.documentElement.classList.toggle("is-web", !inTelegram() && Boolean(lkToken));
  }

  // ---------- toast and confetti ----------
  let toastTimer = 0;
  function toast(m) {
    const e = document.getElementById("toast");
    e.textContent = m;
    e.classList.remove("act");
    e.classList.add("on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => e.classList.remove("on"), 2200);
  }
  // A toast with one button («Отменить»): stays a little longer and takes taps.
  function toastAct(m, label, fn) {
    const e = document.getElementById("toast");
    e.innerHTML = `${esc(m)}<button type="button" class="ta">${esc(label)}</button>`;
    e.classList.add("on", "act");
    e.querySelector(".ta").onclick = () => { e.classList.remove("on", "act"); clearTimeout(toastTimer); haptic(); fn(); };
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => e.classList.remove("on", "act"), 4500);
  }
  function boom() {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const c = document.createElement("canvas");
    c.className = "cf";
    const r = window.devicePixelRatio || 1, W = innerWidth, H = innerHeight;
    c.width = W * r; c.height = H * r;
    const x = c.getContext("2d");
    x.scale(r, r);
    document.body.appendChild(c);
    const P = [];
    for (let i = 0; i < 90; i++) P.push({ x: W / 2, y: H * 0.3, vx: Math.random() * 10 - 5, vy: -Math.random() * 9 - 3, c: ["#5ad48f", "#fff", "#30a1f5", "#ffd84d", "#ff8fb1"][i % 5], r: Math.random() * 6, s: Math.random() * 0.3 - 0.15 });
    let t = 0;
    (function f() {
      x.clearRect(0, 0, W, H);
      for (const p of P) { p.x += p.vx; p.y += p.vy; p.vy += 0.25; p.vx *= 0.99; p.r += p.s; x.save(); x.translate(p.x, p.y); x.rotate(p.r); x.fillStyle = p.c; x.fillRect(-3, -4, 6, 8); x.restore(); }
      if (++t < 130) requestAnimationFrame(f); else c.remove();
    })();
  }
  function showErr(e) { notify("error"); call(() => tg.showAlert((e && e.message) || String(e))); }
  const confirmAsk = (text) => new Promise((resolve) => { if (typeof tg.showConfirm === "function") tg.showConfirm(text, (ok) => resolve(Boolean(ok))); else resolve(window.confirm(text)); });
  function copy(text, done) {
    if (!text) return;
    haptic();
    const ok = () => toast(done || "Скопировано");
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(ok).catch(() => call(() => tg.showAlert(text)));
    else call(() => tg.showAlert(text));
  }

  // ---------- flows ----------
  function startWizard(fromOffer) {
    const cap = Number(me.max_devices) || 0;
    if (cap > 0 && phones().length >= cap) { call(() => tg.showAlert(`Можно подключить не больше ${cap} устройств`)); return; }
    haptic();
    Object.assign(wiz, { url: "", deviceId: null, title: "", fromOffer: Boolean(fromOffer) });
    const p = detectPlatform();
    if (p) { wiz.platform = p; pickApp(p); go("wiz2"); }
    else go("wiz1");
  }
  function resume() {
    const devs = phones();
    const d = devs.slice().sort((a, b) => b.id - a.id)[0];
    if (!d || !d.subscription_url) { startWizard(); return; }
    Object.assign(wiz, { platform: d.platform || detectPlatform() || "ios", url: d.subscription_url, deviceId: d.id, title: d.title });
    wiz.client = prefApp(wiz.platform, d.client) || "happ";
    go("wiz3");
  }
  let creating = false;
  async function createDevice(btn, opt = {}) {
    if (creating) return;
    creating = true;
    if (btn) btn.classList.add("dim");
    try {
      const names = { ios: "Мой iPhone", android: "Мой Android", macos: "MacBook", windows: "Ноутбук", androidtv: "Телевизор", appletv: "Apple TV" };
      // A second «Мой iPhone» becomes «Мой iPhone 2», so the list tells them apart.
      const base = names[wiz.platform] || "Моё устройство", taken = new Set((me.devices || []).map((d) => String(d.title || "").trim()));
      let title = base;
      for (let n = 2; taken.has(title); n++) title = `${base} ${n}`;
      const made = await post("/api/devices", { title, platform: wiz.platform, client: wiz.client });
      if (wiz.client) store.set("app_" + wiz.platform, wiz.client);
      Object.assign(wiz, { title, url: made.subscription_url || "", deviceId: made.device_id });
      if (made.first_device) thanksArmed = true;
      store.set("onboard", 1);
      await load(true).catch(() => {});
      notify("success");
      if (opt.open) openClient(wiz.client, wiz.url);
      stack = [];
      go("wiz3", {}, "f");
      stack = [{ key: "home", params: {} }];
      syncBack();
    } catch (e) {
      showErr(e);
    } finally {
      creating = false;
      if (btn) btn.classList.remove("dim");
    }
  }
  async function startPay(btn) {
    const m = curMethod();
    if (!m || !amountOk(pay.amount)) return;
    haptic();
    btn.classList.add("dim");
    try {
      pay.fbOn = fbOk(pay.amount);
      pay.fbRet = fbRet();
      const inv = await post("/api/invoice", { plan: "b" + pay.amount, method: m.id });
      pay.base = Number(me.balance_rub) || 0;
      if (inv.pay_url) {
        pay.url = inv.pay_url; pay.kind = "link";
        tg.openLink(inv.pay_url);
        go("wait");
        return;
      }
      if (inv.chat) {
        // Gram (TON) is paid in the chat with the bot: the card for this amount is already there.
        notify("success");
        toast("Окно оплаты уже в чате с ботом");
        setTimeout(() => call(() => tg.close()), 700);
        return;
      }
      if (!inv.invoice_url) throw new Error("Не удалось получить счёт Telegram Stars");
      pay.url = ""; pay.kind = "stars";
      if (!inTelegram()) { location.assign(inv.invoice_url); return; }
      go("wait");
      tg.openInvoice(inv.invoice_url, (status) => {
        if (status === "paid") load(true).then(() => cur && cur.key === "wait" && checkPaid(cur.el)).catch(() => {});
        else if (status === "failed") { showErr(new Error("Оплата не прошла. Попробуйте ещё раз.")); back(); }
        else if (status === "cancelled" && cur && cur.key === "wait") back();
      });
    } catch (e) {
      showErr(e);
    } finally {
      btn.classList.remove("dim");
    }
  }
  function openSupport(context) {
    support.context = context || null;
    if (context && context.prefill && !support.draft) support.draft = context.prefill;
    go("support");
  }
  function connectContext(d) {
    const dev = d || phones()[0];
    const a = appById(wiz.client) || appById((appsFor((dev && dev.platform) || wiz.platform)[0] || {}).id);
    return { device_id: (dev && dev.id) || wiz.deviceId, client: (a && a.name) || "", stage: "subscription" };
  }
  async function shareInvite(copyOnly) {
    if (!me.invite_url) return;
    haptic();
    post("/api/invitation-card-event", { action: copyOnly ? "copy" : "share" }).catch(() => {});
    const text = String(me.invite_share_text || "").trim() || "Попробуй VPN для телефона и компьютера.";
    if (copyOnly) { copy(String(me.invite_copy_text || "").trim() || `${text}\n\n${me.invite_url}`, "Ссылка скопирована"); return; }
    tg.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(me.invite_url)}&text=${encodeURIComponent(text)}`);
  }

  // ---------- actions ----------
  const ACT = {
    apAmt(b) {
      if (b.disabled) return;
      haptic("soft");
      cur.params.amount = Number(b.dataset.v);
      rerender(true);
    },
    apPick() { haptic("soft"); go("autopay", { pick: true }); },
    apPay() { const a = me.autopay || {}; if (a.pay_url) { haptic(); tg.openLink(a.pay_url); } },
    async apStart(b) {
      const a = me.autopay || {};
      const amount = Number(cur.params.amount) || a.default;
      if (!amount || b.classList.contains("dim")) return;
      haptic();
      b.classList.add("dim");
      try {
        const r = await post("/api/autopay", { amount });
        pay.amount = amount; pay.kind = "autopay"; pay.url = r.pay_url || ""; pay.base = Number(me.balance_rub) || 0; pay.fbOn = false;
        if (r.pay_url) tg.openLink(r.pay_url);
        go("wait");
        load(true).catch(() => {});
      } catch (e) { showErr(e); b.classList.remove("dim"); }
    },
    // «Оплатить один раз»: the same amount as a plain top-up, and no offer for 30 days.
    apOnce() {
      const amount = Number(cur.params.amount) || (me.autopay || {}).default;
      haptic();
      post("/api/autopay/later").catch(() => {});
      if (me.autopay) me.autopay.offer = false;
      if (amountOk(amount)) { pay.amount = amount; pay.custom = false; }
      go("topup");
    },
    // Screen 19: switching off also removes the SBP binding at CISPay, so it is the one place that asks.
    async apOff(b) {
      if (!(await confirmAsk("Отключить автопополнение? Привязку СБП удалим, больше ничего не спишем. Баланс и VPN останутся как есть. Чтобы включить снова, понадобится новая оплата через СБП."))) return;
      b.classList.add("dim");
      try {
        await post("/api/autopay/off");
        await load(true);
        notify("success");
        toast("Автопополнение выключено");
        rerender(true);
      } catch (e) { showErr(e); b.classList.remove("dim"); }
    },
    apQuietNo(b) {
      haptic("soft");
      post("/api/autopay/later").catch(() => {});
      if (me.autopay) me.autopay.offer = false;
      const c = b.closest(".apq");
      if (c) { c.style.transition = "opacity .25s"; c.style.opacity = "0"; setTimeout(() => c.remove(), 250); }
    },
    browserHow: () => openBrowserSheet(),
    browserHide(b) {
      haptic();
      store.set("brw_at", Date.now());
      store.set("brw_n", (Number(store.get("brw_n")) || 0) + 1);
      const c = b.closest(".bpc");
      if (c) { c.style.transition = "opacity .25s"; c.style.opacity = "0"; setTimeout(() => c.remove(), 250); }
      toast("Спрятали — напомним позже");
    },
    back,
    home,
    refresh(b) {
      b.classList.remove("spin"); void b.offsetWidth; b.classList.add("spin");
      haptic();
      load(true).then(() => { if (cur && cur.key === "wait") checkPaid(cur.el); else toast(`Обновлено в ${timeHM(new Date())}`); }).catch(showErr);
    },
    wizard: () => startWizard(),
    resume,
    hfilter(b) { haptic(); cur.params.filter = b.dataset.v; rerender(false); },
    support: () => openSupport(),
    sptopic(b) {
      haptic();
      const tp = SP_TOPICS[Number(b.dataset.v)];
      if (!tp) return;
      support.draft = tp[2];
      const ta = cur.el.querySelector("#msg");
      if (ta) { ta.value = tp[2]; ta.dispatchEvent(new Event("input")); ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length); }
    },
    // A picture from the chat, big, without leaving the cabinet.
    spzoom(b) {
      haptic();
      const z = document.createElement("button");
      z.type = "button";
      z.className = "sp-zoom";
      z.setAttribute("aria-label", "Закрыть");
      z.innerHTML = `<img src="${esc(b.dataset.v)}" alt="">`;
      z.onclick = () => z.remove();
      document.body.appendChild(z);
    },
    helpconnect: () => openSupport(connectContext()),
    helpdevice: () => openSupport(connectContext(deviceById(cur.params.id))),
    device: (b) => { haptic(); go("device", { id: b.dataset.id }); },
    link: (b) => tg.openLink(b.dataset.v),
    async gift(b) {
      if (me.trial_notice && me.trial_notice.kind === "start_bot") { tg.openTelegramLink(me.bot_start_url); return; }
      haptic();
      b.classList.add("dim");
      try {
        if (me.trial_available) {
          const res = await post("/api/trial");
          me.trial_available = false;
          if (res.balance_rub != null) me.balance_rub = res.balance_rub;
          await load(true).catch(() => {});
          boom();
          notify("success");
          toast(me.trial_rub ? `+${rub(me.trial_rub)} — подарок на балансе 🎁` : "Подарок на балансе 🎁");
        }
        const d = phones()[0];
        setTimeout(() => { stack = []; if (d) go("device", { id: d.id }, "f"); else startWizard(true); stack = [{ key: "home", params: {} }]; syncBack(); }, 700);
      } catch (e) { showErr(e); b.classList.remove("dim"); }
    },
    fbgo() {
      haptic();
      const f = FB();
      if (f && amountOk(Number(f.min_rub))) { pay.amount = Number(f.min_rub); pay.custom = false; }
      go("topup");
    },
    fbneed() {
      const f = FB(), b = f && cur.el.querySelector(`.chp [data-v="${Number(f.min_rub)}"]`);
      if (b) ACT.amt(b);
    },
    amt(b) {
      haptic();
      const old = pay.amount;
      pay.amount = Number(b.dataset.v);
      pay.custom = false;
      cur.el.querySelectorAll(".chp button").forEach((c) => c.classList.toggle("on", c === b));
      const amtI = cur.el.querySelector("#amtI");
      if (amtI) amtI.hidden = true;
      paintAmount(cur.el, old);
    },
    amtc() { haptic(); amt.gift = false; amt.cnt = 1; amt.v = pay.custom && amountOk(pay.amount) ? String(pay.amount) : ""; amt.mode = "rub"; amt.d = ""; go("amount"); },
    amtk(b) { amtPress(b.dataset.v); },
    amtq(b) { amtQuick(b); },

    amtsw(b) { amSwap(b); },
    amtico() { if (amt.gift) amGiftAdd(); else amCycle(); },
    amtpay(b) {
      const n = Number(amt.v) || 0;
      if (amt.gift) {
        if (!gOk(n)) return amtShake();
        haptic();
        gs.amount = n; gs.custom = true; gs.count = amt.cnt;
        back();
        return;
      }
      if (!amountOk(n)) return amtShake();
      pay.amount = n; pay.custom = true;
      startPay(b);
    },
    pay: (b) => startPay(b),
    meth(b) {
      haptic();
      const same = (curMethod() || {}).id === b.dataset.v;
      pay.method = b.dataset.v;
      cur.el.querySelectorAll(".rd").forEach((r) => r.classList.toggle("on", r.closest("[data-v]").dataset.v === pay.method));
      // The widget on top changes to the chosen method's look (the same method keeps its picture, it doesn't pop in again).
      if (same) return;
      const h = cur.el.querySelector(".hc"), L = look(curMethod());
      Object.values(LOOK).forEach((x) => h.classList.remove(x.c));
      h.classList.add(L.c);
      const ill = h.querySelector(".ill");
      const fresh = ill.cloneNode(false);
      fresh.innerHTML = `<div>${L.ill(64)}</div>`;
      ill.replaceWith(fresh);
    },
    reopen: () => pay.url && tg.openLink(pay.url),
    plat(b) { haptic(); wiz.platform = b.dataset.v; pickApp(wiz.platform); go("wiz2"); },
    // «X уже стоит» was a guess from another device: show the download screen for this one.
    hasnot() { haptic(); wiz.has = false; rerender(false); },
    hasyes() { haptic(); go("wizhave"); },
    haveapp(b) {
      notify("success");
      wiz.client = b.dataset.v;
      wiz.has = true;
      store.set("app_" + wiz.platform, wiz.client);
      go("wiz2");
    },
    replat: () => go("wiz1"),
    guide(b) {
      const a = appById(b.dataset.v);
      if (!a || !a.guide) return;
      haptic();
      tg.openLink ? tg.openLink(a.guide) : window.open(a.guide, "_blank", "noopener");
    },
    tipx(b) { const t = b.closest(".atip"); if (t) t.remove(); },
    appmore(b) {
      haptic();
      const tip = cur && cur.el.querySelector(".atip");
      if (tip) tip.remove();
      const alt = b.closest(".alt"), on = alt.classList.toggle("on");
      b.setAttribute("aria-expanded", String(on));
    },
    client(b) {
      haptic();
      wiz.client = b.dataset.v;
      wiz.went = false;
      const el = cur.el, alt = el.querySelector(".alt");
      if (alt) alt.classList.remove("on");
      // Swap the card in place: the icon pops in, texts fade, the list folds back with the new app checked.
      T(() => {
        if (!cur || cur.el !== el) return;
        const tmp = document.createElement("div");
        tmp.innerHTML = SCR.wiz2.h();
        const swap = (o, n, still) => { if (o && n) { if (still) n.classList.add("still"); o.replaceWith(n); } };
        swap(el.querySelector(".hc .ill"), tmp.querySelector(".hc .ill"));
        ["H", "P"].forEach((c) => { const n = tmp.querySelector(`.hc .${c}`); if (n) n.classList.add("fx"); swap(el.querySelector(`.hc .${c}`), n); });
        swap(el.querySelector(".hc .acts"), tmp.querySelector(".hc .acts"));
        swap(el.querySelector(".hc .wsteps"), tmp.querySelector(".hc .wsteps"), true);
        [".gde.apk", ".gde:not(.apk)"].forEach((sel) => {
          const g = el.querySelector(sel), ng = tmp.querySelector(sel);
          if (ng) ng.classList.add("still");
          if (g && ng) swap(g, ng); else if (g) g.remove(); else if (ng) { const w = el.querySelector(sel === ".gde.apk" ? ".gde:not(.apk), .altw" : ".altw"); if (w) w.before(ng); }
        });
        swap(el.querySelector(".alt"), tmp.querySelector(".alt"), true);
        const tl = el.querySelector(".tl"), ntl = tmp.querySelector(".tl");
        swap(tl && tl.parentNode, ntl && ntl.parentNode, true);
      }, alt ? 280 : 0);
    },
    apk() {
      const a = appById(wiz.client);
      const url = a && (a.direct || {})[wiz.platform];
      if (url) { haptic(); tg.openLink(url); }
    },
    store() {
      const a = appById(wiz.client);
      const url = a && (a.stores || {})[wiz.platform];
      if (url && !wiz.went) { wiz.went = true; T(() => rerender(), 400); }
      if (url) { haptic(); tg.openLink(url); }
    },
    create: () => createDevice(cur.el.querySelector("#wizOk")),
    addkey: () => createDevice(cur.el.querySelector("#wizOk"), { open: true }),
    connect: () => openClient(wiz.client, wiz.url),
    copykey: () => copy(wiz.url, "Ключ скопирован"),
    devopen() {
      const d = deviceById(cur.params.id);
      if (d) openClient((devApp(d) || {}).id, d.subscription_url);
    },
    devapp() { const d = deviceById(cur.params.id); if (d) { haptic(); appSheet(d); } },
    devcopy() { const d = deviceById(cur.params.id); if (d) copy(d.subscription_url, "Ключ скопирован"); },
    rename() { const d = deviceById(cur.params.id); if (d) { haptic(); nameSheet([d]); } },
    async reissue() {
      const d = deviceById(cur.params.id);
      if (!d || !(await confirmAsk("Старый ключ перестанет работать. Выпустить новый?"))) return;
      try {
        await post(`/api/devices/${d.id}/reissue`);
        await load(true);
        notify("success");
        toast("🔑 Новый ключ готов — добавьте его в приложение");
      } catch (e) { showErr(e); }
    },
    async delete() {
      const d = deviceById(cur.params.id);
      if (!d || !(await confirmAsk("Устройство будет удалено, VPN на нём перестанет работать. Продолжить?"))) return;
      try {
        await api(`/api/devices/${d.id}`, { method: "DELETE" });
        store.set("onboard", 1);
        await load(true).catch(() => {});
        toast("Устройство удалено");
        home();
      } catch (e) { showErr(e); }
    },
    share: () => shareInvite(false),
    nfsheet: (b) => nfStepSheet(Number(b.dataset.i)),
    copyinvite: () => shareInvite(true),
    copyid: () => copy(String((me.user || {}).id || ""), "ID скопирован"),
    async quiet(b) {
      const quiet = !me.quiet_notifications;
      if (quiet && !(await confirmAsk("Включить режим тишины? Приглашения, акции и напоминания больше не придут. Предупреждения о балансе, оплата и поддержка останутся."))) return;
      b.querySelector(".tg").classList.toggle("off", !quiet);
      try {
        const res = await post("/api/notification-settings", { quiet, confirmed: quiet });
        me.quiet_notifications = Boolean(res.quiet_notifications);
        toast(me.quiet_notifications ? "Режим тишины включён" : "Все уведомления включены");
      } catch (e) { showErr(e); }
      rerender();
    },
    async promo() {
      const i = cur.el.querySelector("#promoInput");
      const code = (i.value || "").trim();
      if (!code) { i.focus(); return; }
      haptic();
      const b = cur.el.querySelector(".pill");
      b.classList.add("dim");
      cur.params.code = code;
      try {
        const res = await post("/api/promo", { code });
        cur.params.ok = true;
        cur.params.result = res.credited_rub != null ? `Начислено ${rub(res.credited_rub)}. Баланс: ${rub(res.balance_rub)}` : `Промокод применён. Добавлено дней: ${res.days}`;
        await load(true).catch(() => {});
        rerender(true);
        boom();
        notify("success");
        toast("Промокод применён 🎟️");
      } catch (e) {
        cur.params.result = e.message || "Промокод не применён. Проверьте код";
        rerender(true);
        notify("error");
      }
    },
    async trust(b) {
      const t = me.trust || {};
      if (!t.available) return;
      const fee = Number(t.fee) || 0;
      const text = `Начислим ${rub(t.amount)} — ${days(t.days)} одного устройства.` + (fee > 0 ? ` За услугу спишется ещё ${rub(fee)}.` : "") +
        ` Через ${days(t.days)} спишем ${rub(t.repay || t.amount + fee)} с баланса, даже если он станет отрицательным.`;
      if (!(await confirmAsk(text))) return;
      b.classList.add("dim");
      try {
        await post("/api/trust");
        await load(true);
        const h = cur.el.querySelector(".hc");
        h.classList.add("dn", "go");
        boom();
        notify("success");
        toast("VPN снова работает ✓");
        setTimeout(() => rerender(), 900);
      } catch (e) { showErr(e); b.classList.remove("dim"); }
    },
    acc(b) {
      haptic("soft");
      const open = b.classList.contains("open");
      cur.el.querySelectorAll(".q").forEach((q) => q.classList.remove("open"));
      if (!open) b.classList.add("open");
    },
    attach: () => cur.el.querySelector("#files").click(),
    unfile(b) { support.files.splice(Number(b.dataset.v), 1); rerender(false); },
    async send() {
      const ta = cur.el.querySelector("#msg");
      const text = (ta.value || "").trim();
      if (!text && !support.files.length) { ta.focus(); return; }
      haptic();
      const btn = cur.el.querySelector(".send");
      btn.disabled = true;
      const fd = new FormData();
      fd.append("text", text);
      if (support.context && support.context.device_id) fd.append("connection_context", JSON.stringify(support.context));
      support.files.forEach((f) => fd.append("files", f, f.name));
      // Show the message right away; the server copy replaces it.
      const chat = cur.el.querySelector("#chat");
      if (text) {
        chat.querySelector(".empty") && chat.querySelector(".empty").remove();
        chat.insertAdjacentHTML("beforeend", `<div class="bub me">${esc(text)}<i>${timeHM(new Date())}</i></div>`);
        scrollChat();
      }
      try {
        const data = await api("/api/tickets", { method: "POST", body: fd });
        support.draft = ""; support.files = []; support.context = null;
        if (cur && cur.key === "support") { cur.params.ticket = data.current || null; cur.params.loaded = true; rerender(true); scrollChat(); }
      } catch (e) { showErr(e); btn.disabled = false; }
    },
    async tclose() {
      const t = cur.params.ticket;
      if (!t || !(await confirmAsk("Закрыть обращение? Если понадобится помощь, можно написать снова."))) return;
      try { await post(`/api/tickets/${t.id}/action`, { action: "close" }); await loadTickets(); } catch (e) { showErr(e); }
    },
    async trate(b) {
      const t = cur.params.ticket;
      if (!t) return;
      try { await post(`/api/tickets/${t.id}/action`, { action: "rate", rating: Number(b.dataset.v) }); notify("success"); await loadTickets(); } catch (e) { showErr(e); }
    },
    rehistory() { cur.params.data = null; rerender(false); loadHistory(); },
    retry() { go("boot", {}, "x"); load().catch(failed); },
    async login() {
      const i = cur.el.querySelector("#loginUser");
      const username = (i.value || "").trim();
      if (!username) { i.focus(); return; }
      const seq = ++loginSeq;
      go("login", { nick: true, waiting: true, msg: "Входим…" }, "x");
      try {
        const res = await fetch("/api/cabinet-login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username }) });
        const data = await res.json().catch(() => ({}));
        if (seq !== loginSeq) return;
        if (data && data.token) { saveToken(data.token); go("boot", {}, "x"); await load(); return; }
        if (data && data.wait) {
          go("login", { nick: true, waiting: true, msg: "Подтвердите вход в Telegram — мы прислали запрос в чат с ботом" }, "x");
          const st = await pollLogin(seq, data.wait);
          if (st === "declined") decoy(username);
          else if (st === "expired") go("login", { nick: true, msg: "Время подтверждения истекло. Попробуйте ещё раз." }, "x");
          return;
        }
        decoy(username);
      } catch (_e) { if (seq === loginSeq) decoy(username); }
    },
    loginNick() { loginSeq++; go("login", { nick: true }, "x"); },
    loginTg() { tgLogin(); },
    loginOpen() {
      // the link opens Telegram in a new tab/app; this page keeps waiting and logs in by itself
      if (cur && cur.params && !cur.params.opened) { cur.params.opened = true; setTimeout(() => cur && cur.key === "login" && rerender(), 400); }
      return true;
    },
  };

  // =====================================================================
  // «Подарить другу»: the giver's tab in «Пригласить друзей», the friend's gift screen
  // =====================================================================
  // The gift is Wallet's own animation (icons/wallet_gift*.json, see icons/PAYMENT-ASSETS.md), split into box and lid
  // so the lid can fly off. Particles, the beam and coins are ours.
  const gs = { amount: 0, custom: false, count: 1, data: null, busy: false, style: "violet", touched: false, greeting: "", greeted: false };
  // The giver picks how the gift looks: the card in the cabinet, the card in Telegram and the friend's screen share it.
  // box/rib recolour Wallet's blue box and orange ribbon: [hue, saturation or null to keep it, lightness from the original].
  const GSTY = {
    violet: { name: "Фиолетовый", ray: "rgba(255,226,140,.18)", conf: ["#ffd76a", "#fff", "#c9b2ff"], box: [45, 0.08, (l) => Math.min(0.97, 0.86 + l * 0.14)], rib: [42, null] },
    festive: { name: "Праздничный", ray: "rgba(255,226,140,.16)", conf: ["#ffd76a", "#ff5a5a", "#fff"], box: [356, 0.72, (l) => Math.min(0.62, 0.3 + l * 0.45)], rib: [44, null] },
    gold: { name: "Золотой", ray: "rgba(255,215,106,.14)", conf: ["#ffd76a", "#f7b733", "#fff3c4"], box: [43, 0.85, (l) => Math.min(0.72, 0.38 + l * 0.42)], rib: [230, 0.12, (l) => Math.max(0.1, l * 0.35)] },
    sunset: { name: "Закатный", ray: "rgba(255,255,255,.2)", conf: ["#fff", "#7ff0c8", "#ffe08a"], box: [160, 0.55, (l) => Math.min(0.82, 0.5 + l * 0.35)], rib: [40, 0.06, (l) => Math.min(0.98, 0.8 + l * 0.2)] },
    // New Year: snow (and a garland, or golden sparks) instead of confetti; offered first while the season runs.
    snow: { name: "Снежный", ny: 1, fx: "snow", ray: "rgba(190,220,255,.14)", conf: ["#fff", "#fff", "#dbe9ff"], box: [205, 0.6, (l) => Math.min(0.86, 0.6 + l * 0.3)], rib: [210, 0.1, (l) => Math.min(0.98, 0.84 + l * 0.16)] },
    tree: { name: "Ёлка", ny: 1, fx: "snow", gar: 1, ray: "rgba(255,226,140,.12)", conf: ["#fff", "#fff", "#e8fff0"], box: [45, 0.08, (l) => Math.min(0.97, 0.86 + l * 0.14)], rib: [356, 0.78, (l) => Math.min(0.6, 0.34 + l * 0.4)] },
    tangerine: { name: "Мандарины", ny: 1, fx: "spark", ray: "rgba(255,190,110,.16)", conf: ["#fff", "#fff", "#ffd76a"], box: [27, 0.95, (l) => Math.min(0.64, 0.42 + l * 0.32)], rib: [128, 0.55, (l) => Math.min(0.5, 0.24 + l * 0.34)] },
  };
  const nySeason = () => me.gift_season === "ny";
  const isNy = (k) => !!(GSTY[k] && GSTY[k].ny);
  // In the season the New Year looks come first; out of it only the usual four are offered.
  const gStyKeys = () => { const all = Object.keys(GSTY), ny = all.filter(isNy), reg = all.filter((k) => !isNy(k)); return nySeason() ? [...ny, ...reg] : reg; };
  const GREETS = ["С Новым годом! 🎄", "Пусть в новом году всё открывается с первого раза 🎄", "Без блокировок в новом году", "Чтобы YouTube не тормозил 🎉"];
  // A sagging wire with blinking bulbs along the top edge («Ёлка»).
  function gGarland(w, h) {
    const C = ["#ff5a5a", "#ffd76a", "#5fd38d", "#5fa8ff"], sag = 3, step = w / sag, pts = [];
    let d = "M0 2";
    for (let i = 0; i < sag; i++) {
      const x0 = i * step;
      d += ` Q${x0 + step / 2} ${h * 0.75} ${x0 + step} 2`;
      for (let j = 1; j < 6; j++) { const t = j / 6; pts.push([x0 + step * t, 2 + 2 * t * (1 - t) * (h * 0.75 - 2)]); }
    }
    return `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><path d="${d}" stroke="rgba(0,0,0,.45)" stroke-width="1.4" fill="none"/>${pts.map(([x, y], i) =>
      `<circle cx="${x.toFixed(1)}" cy="${(y + 4).toFixed(1)}" r="3.6" fill="${C[i % 4]}" style="filter:drop-shadow(0 0 4px ${C[i % 4]});animation-delay:-${(i * 0.37 % 1.6).toFixed(2)}s"/>`).join("")}</svg>`;
  }
  const gSty = (k) => (GSTY[k] ? k : "violet");
  const gTint = (p) => (c) => {
    const [h, sat, l] = fbHue(c[0], c[1], c[2]);
    if (sat < 0.12) return c;
    if (h >= 190 && h <= 300) return fbRgb(p.box[0], p.box[1], p.box[2](l));
    if (h >= 5 && h <= 45) return p.rib[1] == null ? fbRgb(p.rib[0], Math.min(1, sat + 0.1), Math.min(0.9, l)) : fbRgb(p.rib[0], p.rib[1], p.rib[2](l));
    return c;
  };
  const gRaw = {}, gCol = {};
  // Lottie writes into the data it plays, so every player gets its own copy.
  const gData = (file, k) => (gCol[k + file] = gCol[k + file] || (gRaw[file] = gRaw[file] || fetch(`/icons/${file}`).then((r) => r.json()))
    .then((d) => { const c = JSON.parse(JSON.stringify(d)); fbWalk(c, gTint(GSTY[k])); return c; })).then((d) => JSON.parse(JSON.stringify(d)));
  // Themed background layers (crossfade), slow rays and falling confetti behind the hero.
  const gBack = (k) => `<div class="gs-bgs">${Object.keys(GSTY).map((s) => `<i class="gs-${s}${s === k ? " on" : ""}" data-k="${s}"></i>`).join("")}</div>` +
    `<div class="gs-rays" style="--ray:${GSTY[k].ray}"></div><div class="gs-conf"></div><div class="gs-gar"></div>`;
  function gConf(h, k) {
    const g = h && h.querySelector(".gs-gar");
    if (g) g.innerHTML = GSTY[k].gar ? gGarland(g.clientWidth || 375, g.clientHeight || 46) : "";
    const c = h && h.querySelector(".gs-conf");
    if (!c || reduced()) return;
    const P = GSTY[k], C = P.conf;
    if (P.fx) {
      // Snowflakes drift side to side; «Мандарины» mixes in golden sparks.
      c.innerHTML = Array.from({ length: 26 }, (_, i) => {
        const spark = P.fx === "spark" && i % 3 === 0, sz = spark ? 3 : (2 + Math.random() * 3.5).toFixed(1);
        return `<i class="${spark ? "sp" : "sn"}" style="left:${(Math.random() * 100).toFixed(1)}%;width:${sz}px;height:${sz}px;opacity:${(0.4 + Math.random() * 0.55).toFixed(2)};` +
          `--dx:${(4 + Math.random() * 16).toFixed(0)}px;animation-duration:${(7 + Math.random() * 6).toFixed(1)}s;animation-delay:-${(Math.random() * 10).toFixed(1)}s"></i>`;
      }).join("");
      return;
    }
    c.innerHTML = Array.from({ length: 18 }, (_, i) => `<i style="left:${(Math.random() * 100).toFixed(1)}%;background:${C[i % 3]};opacity:${(0.45 + Math.random() * 0.5).toFixed(2)};` +
      `--dx:${(Math.random() * 30 - 15).toFixed(0)}px;animation-duration:${(4 + Math.random() * 5).toFixed(1)}s;animation-delay:-${(Math.random() * 8).toFixed(1)}s"></i>`).join("");
  }
  const gName = () => esc((tg.initDataUnsafe && tg.initDataUnsafe.user && tg.initDataUnsafe.user.first_name) || "Ваш друг");
  const gTotal = () => gs.amount * (gs.count || 1);
  const gLim = () => [Math.max(1, Number(me.gift_min) || 60), Math.max(1, Number(me.gift_max) || 20000)];
  const gOk = (n) => { const [lo, hi] = gLim(); return Number.isFinite(n) && n >= lo && n <= hi; };
  const gDays = (n) => Math.floor((Number(n) || 0) / dayPrice());
  const gPresets = () => (nySeason() && (gs.count || 1) === 1 ? [300, 500, 1000] : [30, 90, 360].map((d) => d * dayPrice())).filter(gOk);
  const gDaysLine = (n) => `≈ ${days(gDays(n))} VPN`;
  const HEART = '<svg width="22" height="22" viewBox="0 0 24 24"><path d="M12 20s-7.5-4.6-7.5-10.2A4.3 4.3 0 0 1 12 7.3a4.3 4.3 0 0 1 7.5 2.5C19.5 15.4 12 20 12 20z" fill="#fff"/></svg>';
  const GIFT_IC = '<svg width="22" height="22" viewBox="0 0 24 24" fill="#c4c9d3"><path d="M4 11h7v10H6a2 2 0 0 1-2-2zm9 0h7v8a2 2 0 0 1-2 2h-5zM3 7h8v3H3zm10 0h8v3h-8z"/><path d="M12 7C9 2 5 4 7 7m5 0c3-5 7-3 5 0" stroke="#c4c9d3" stroke-width="1.6" fill="none"/></svg>';
  const GSTAR = (s, c) => `<svg width="${s}" height="${s}" viewBox="0 0 20 20"><path d="M10 0c.9 5.6 4.4 9.1 10 10-5.6.9-9.1 4.4-10 10-.9-5.6-4.4-9.1-10-10C5.6 9.1 9.1 5.6 10 0z" fill="${c || "#fff"}"/></svg>`;
  const gScene = () => `<div class="gf-ill" data-act="gfbox"><div class="gf-box"><div class="gf-rays"></div><div class="gf-glow"></div><div class="gf-lot gf-body"></div><div class="gf-beam"><i class="wide"></i>${
    [[10, 210, -22, 1.9, 0], [6, 190, -13, 1.5, .4], [14, 220, -5, 2.2, .9], [8, 215, 3, 1.7, .2], [12, 205, 11, 2, .7], [6, 185, 19, 1.6, 1.1], [9, 200, 26, 2.3, .5]]
      .map(([w, h, r, d, dl]) => `<i class="sh" style="--w:${w}px;--h:${h}px;--r:${r}deg;--d:${d}s;--dl:${dl}s"></i>`).join("")
  }<i class="core"></i><i class="pool"></i></div><div class="gf-lot gf-lid"></div><div class="gf-flash"></div></div></div>`;
  const reduced = () => window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  // Box and lid are two players started on the same frame, so they move as one gift until the lid flies off.
  function mountGift(el, k) {
    const ill = el && el.querySelector(".gf-ill:not([data-on])");
    if (!ill) return;
    ill.setAttribute("data-on", "");
    k = gSty(k);
    Promise.all([lottieLib(), gData("wallet_gift_body.json", k), gData("wallet_gift_lid.json", k)]).then(([L, body, lid]) => {
      if (!ill.isConnected) return;
      const mk = (c, d) => { const box = ill.querySelector(c); box.innerHTML = ""; return L.loadAnimation({ container: box, renderer: "svg", loop: true, autoplay: false, animationData: d,
        rendererSettings: { preserveAspectRatio: "xMidYMid meet" } }); };
      (ill._players || []).forEach((a) => a.destroy());
      const A = [mk(".gf-body", body), mk(".gf-lid", lid)];
      let ready = 0;
      A.forEach((a) => a.addEventListener("DOMLoaded", () => { if (++ready === 2) { A.forEach((b) => (reduced() ? b.goToAndStop(40, true) : b.goToAndPlay(0, true))); ill.classList.remove("swap"); } }));
      ill._players = A;
    }).catch(() => { ill.querySelector(".gf-body").innerHTML = '<div style="font-size:96px;line-height:159px">🎁</div>'; });
  }
  // A small looping gift in the style's colours (tiles, the Telegram card preview, the keypad).
  function gMini(root) {
    root.querySelectorAll("[data-gmini]:not([data-on])").forEach((box) => {
      box.setAttribute("data-on", "");
      Promise.all([lottieLib(), gData("wallet_gift.json", gSty(box.dataset.gmini))]).then(([L, d]) => {
        if (!box.isConnected) return;
        box.innerHTML = "";
        const a = L.loadAnimation({ container: box, renderer: "svg", loop: !reduced(), autoplay: !reduced(), animationData: d });
        if (box.dataset.speed) a.setSpeed(Number(box.dataset.speed));
      }).catch(() => { box.textContent = "🎁"; });
    });
  }
  // Tapping the gift next to the amount adds one more gift (a giveaway for a group); holding it resets to one.
  function amGiftAdd() {
    if (!cur || cur.key !== "amount") return;
    const el = cur.el, ico = el.querySelector("#amIco"), badge = el.querySelector(".am-cnt");
    if (amt.cnt >= 100) { amBoom(); notify("error"); return; }
    amt.cnt++;
    haptic("medium");
    badge.textContent = `×${amt.cnt}`;
    badge.classList.add("on");
    badge.classList.remove("pop"); void badge.offsetWidth; badge.classList.add("pop");
    const ic = ico.querySelector(".am-ic");
    ic.classList.remove("hop"); void ic.offsetWidth; ic.classList.add("hop");
    const plus = document.createElement("i");
    plus.className = "am-plus"; plus.textContent = "+1";
    ico.appendChild(plus);
    setTimeout(() => plus.remove(), 700);
    amSide(el);
    if (amN() && !amOk(amN())) amtShake();
  }
  function amGiftHold(el) {
    const ico = el.querySelector("#amIco");
    let t = 0, held = false;
    const stop = () => clearTimeout(t);
    ico.addEventListener("pointerdown", () => {
      held = false;
      t = setTimeout(() => {
        if (amt.cnt === 1) return;
        held = true;
        amt.cnt = 1;
        notify("warning");
        const b = el.querySelector(".am-cnt"); b.textContent = "×1"; b.classList.remove("on");
        amSide(el);
      }, 550);
    });
    ["pointerup", "pointerleave", "pointercancel"].forEach((e) => ico.addEventListener(e, stop));
    // The click that ends a long press must not add a gift right back.
    ico.addEventListener("click", (e) => { if (held) { held = false; e.stopImmediatePropagation(); } }, true);
  }
  function mountAmGift(el) {
    const box = el && el.querySelector(".am-gift:not([data-gmini])");
    if (!box) return;
    box.dataset.gmini = gs.style;
    gMini(el);
  }

  // ---------- the giver ----------
  function giveTab() {
    if (nySeason() && !gs.touched) gs.style = "snow";
    if (nySeason() && !gs.greeted) gs.greeting = GREETS[0];
    const presets = gPresets(), [lo] = gLim();
    if (!gOk(gs.amount)) { gs.amount = presets[nySeason() ? Math.min(1, presets.length - 1) : 0] || lo; gs.custom = false; }
    const own = gs.custom && (gs.count > 1 || !presets.includes(gs.amount));
    const many = gs.count > 1;
    const chips = presets.map((v) => `<button type="button" data-act="gfamt" data-v="${v}" class="${!own && v === gs.amount ? "on" : ""}">${rub(v)}</button>`).join("") +
      `<button type="button" data-act="gfown" class="${own ? "on" : ""}">${own ? gOwnLabel() : "Своя"}</button>`;
    const hero = `<section class="hc gf gs"><div class="ov"></div>${gBack(gs.style)}${gScene()}<div class="K">${gKicker()}</div><div class="N gf-amt">${gAmtText()}</div>` +
      `<div class="P gf-days">${gSubText()}</div><div class="chp">${chips}</div>` +
      `<div class="acts"><button type="button" class="pill" data-act="gfsend">${IC.share}<span>${many ? "Подарить в группу" : "Подарить"}</span></button>` +
      `<button type="button" class="rnd" aria-label="Скопировать ссылку" data-act="gfcopy">${IC.copy}</button></div></section>`;
    const how = ST("Как это работает") + tl(many
      ? [["1", "Выберите сумму и количество", `Спишем с баланса — <b>${rub(gTotal())}</b>`], ["2", "Отправьте ссылку в группу", "Одна карточка на всех"],
        [GIFT_IC, "Каждый забирает по одному", "Кто первый — того и подарок"]]
      : [["1", "Выберите сумму", `Спишем с баланса — <b>${rub(gs.amount)}</b>`], ["2", "Отправьте подарок другу", "Карточка с кнопкой придёт от вас"],
        [GIFT_IC, "Друг открывает подарок", "Деньги сразу на его балансе"]]);
    const d = gs.data;
    const sent = d && Array.isArray(d.sent) ? d.sent : [];
    const ST_TXT = { active: "ждёт друга", claimed: "открыт", returned: "вернулся к вам" };
    const list = sent.length ? ST("Ваши подарки") + cd(sent.map((g) => {
      const when = parseDate(g.claimed_at || g.created_at);
      const n = Number(g.count) || 1, got = Number(g.claimed_count) || 0;
      const state = n > 1 ? (g.status === "claimed" ? "все разобрали" : g.status === "returned" ? `забрали ${got} из ${n}, остаток вернулся` : `забрали ${got} из ${n}`)
        : g.status === "claimed" && g.friend_name ? esc(g.friend_name) : ST_TXT[g.status] || "";
      const sub = [state, when ? dayLabel(when) : ""].filter(Boolean).join(" · ");
      return [E(g.status === "claimed" ? "✅" : g.status === "returned" ? "↩️" : "🎁") + TT(n > 1 ? `${rub(g.amount_rub)} × ${n}` : rub(g.amount_rub), sub) + (g.status === "active" ? V(CV) : ""),
        g.status === "active" ? `data-act="gfitem" data-code="${esc(g.code)}"` : ""];
    }).map((r) => (r[1] ? r : r[0]))) : "";
    const can = d ? Number(d.giftable_rub) || 0 : null;
    const note = me.gift_admin ? NOTE(me.gift_granted ? "Вам открыт безлимит подарков: дарите любую сумму кому угодно, с баланса ничего не спишется" : "Вы администратор: дарите любую сумму кому угодно, с баланса ничего не спишется", true)
      : can == null ? "" : NOTE(can >= gTotal() ? `Баланс ${rub(me.balance_rub)} · подарить можно до ${rub(can)}`
      : can > 0 ? `Подарить можно до ${rub(can)} — это деньги, которые вы внесли сами` : "Подарить можно только свои деньги — сначала пополните баланс", true);
    return hero + gStyBlock() + `<div class="gf-rest">${note + how + list}</div>`;
  }
  // «Оформление»: four tiles with live gifts, then the card the friend (or the chat) will get in Telegram.
  const gTile = (k) => `<button type="button" data-act="gfsty" data-k="${k}" class="${k === gs.style ? "on" : ""}"><i class="gs-${k}"></i><div class="mg" data-gmini="${k}" data-speed=".85"></div>` +
    `${isNy(k) ? '<span class="fl">❄</span>' : ""}<span class="ck">✓</span>${GSTY[k].name}</button>`;
  const gGreetRow = () => cd([[E("✍️") + TT(gs.greeting ? `«${esc(gs.greeting)}»` : "Добавить поздравление", gs.greeting ? "увидит друг в карточке" : "необязательно, до 200 символов") + V(CV),
    'data-act="gfgreet"']]).replace('class="cd"', 'class="cd grr"');
  const gStyBlock = () => {
    const keys = gStyKeys(), ny = keys.filter(isNy), reg = keys.filter((k) => !isNy(k));
    return `<div class="gf-sty">${ST(`Оформление <span class="gs-tag">${GSTY[gs.style].name}</span>`)}` +
      (ny.length ? `<div class="gs-tiles ny">${ny.map(gTile).join("")}</div>` : "") + `<div class="gs-tiles${ny.length ? " reg" : ""}">${reg.map(gTile).join("")}</div>` +
      ST("Поздравление") + `<div class="gs-grt">${gGreetRow()}</div>` +
      `${ST(`Так увидит ${gs.count > 1 ? "чат" : "друг"}`)}<div class="gs-pv">${gCard(gs.style, gs.count)}</div></div>`;
  };
  function gCard(k, n) {
    const many = n > 1, ny = isNy(k) ? " к Новому году" : "", wish = gs.greeting ? `<br><i>«${esc(gs.greeting)}»</i>` : "";
    const txt = many ? `<b>${gName()} раздаёт ${n} ${pl(n, "подарок", "подарка", "подарков")} по ${rub(gs.amount)} на VPN${ny}</b> — это ≈ ${days(gDays(gs.amount))} каждому. Кто первый — того и подарок!${wish}`
      : `<b>${gName()} дарит вам ${rub(gs.amount)} на VPN${ny}</b> — это ≈ ${days(gDays(gs.amount))}.${wish || " Откройте подарок, пока он не остыл!"}`;
    return `<div class="gs-post"><div class="gs-art"><i class="gs-${k}"></i><div class="gs-rays" style="--ray:${GSTY[k].ray}"></div><div class="gs-conf"></div><div class="gs-gar"></div>` +
      `<div class="lg"><img src="/icons/frog.png" alt="">Лягушка VPN</div>` +
      (many ? `<div class="gl" data-gmini="${k}" data-speed=".8"></div><div class="gr" data-gmini="${k}" data-speed=".8"></div>` : "") +
      `<div class="g1" data-gmini="${k}"></div>` +
      `<div class="tt">${isNy(k) ? (many ? "Подарки к Новому году" : "С Новым годом!") : many ? "Подарки для всех в чате" : "Вам подарок на VPN"}</div>` +
      `<div class="sb">${many ? "Кто первый — того и подарок" : isNy(k) ? "Вам подарок на VPN — нажмите, чтобы открыть" : "Нажмите, чтобы забрать — деньги сразу на баланс"}</div></div>` +
      `<div class="tx">🎁 ${txt}</div></div><div class="gs-kb">${many ? "🎁 Забрать подарок" : "🎁 Открыть подарок"}</div>`;
  }
  function gInvite(el) { gMini(el); gConf(el.querySelector(".hc.inv"), "festive"); nfMount(el); }
  function gGive(el) { mountGift(el, gs.style); gConf(el.querySelector(".hc.gf"), gs.style); gConf(el.querySelector(".gs-art"), gs.style); gMini(el); }
  // Switching the style: the background crossfades, the gift pops out and back in the new colours.
  function gPick(k) {
    if (!cur || k === gs.style || !GSTY[k]) return;
    haptic("light");
    gs.style = k; gs.touched = true;
    const el = cur.el, h = el.querySelector(".hc.gf");
    el.querySelectorAll(".gs-tiles button").forEach((b) => b.classList.toggle("on", b.dataset.k === k));
    const tag = el.querySelector(".gs-tag");
    if (tag) tag.textContent = GSTY[k].name;
    h.querySelectorAll(".gs-bgs i").forEach((i) => i.classList.toggle("on", i.dataset.k === k));
    h.querySelector(".gs-rays").style.setProperty("--ray", GSTY[k].ray);
    gConf(h, k);
    const ill = h.querySelector(".gf-ill");
    ill.classList.add("swap");
    setTimeout(() => { ill.removeAttribute("data-on"); mountGift(h, k); }, 200);
    const pv = el.querySelector(".gs-pv");
    if (pv) { pv.innerHTML = gCard(k, gs.count); gMini(pv); gConf(pv.querySelector(".gs-art"), k); }
    const kk = h.querySelector(".K");
    if (kk) kk.textContent = gKicker();
  }
  const gKicker = () => (gs.count > 1 ? "Подарки в группу" : isNy(gs.style) ? "Подарок к Новому году" : "Подарок другу");
  const gAmtText = () => (gs.count > 1 ? `${rub(gs.amount)} × ${gs.count}` : rub(gs.amount));
  const gSubText = () => (gs.count > 1 ? `${rub(gTotal())} всего · каждому ≈ ${days(gDays(gs.amount))}` : gDaysLine(gs.amount));
  const gOwnLabel = () => (gs.count > 1 ? `×${gs.count} ✎` : rub(gs.amount) + " ✎");
  function gPaint(el, old) {
    const n = el.querySelector(".gf-amt");
    if (n && gs.count === 1 && Number.isFinite(old) && old !== gs.amount) countTo(n, old, gs.amount, " ₽"); else if (n) n.textContent = gAmtText();
    const p = el.querySelector(".gf-days");
    if (p) p.textContent = gSubText();
    const k = el.querySelector(".hc.gf .K");
    if (k) k.textContent = gKicker();
    const pill = el.querySelector('.hc.gf [data-act="gfsend"] span');
    if (pill) pill.textContent = gs.count > 1 ? "Подарить в группу" : "Подарить";
    const tx = el.querySelector(".gs-pv .tx");
    if (tx) { const t = document.createElement("div"); t.innerHTML = gCard(gs.style, gs.count); tx.innerHTML = t.querySelector(".tx").innerHTML; }
  }
  async function loadGifts() {
    try { gs.data = await api("/api/gifts"); } catch (_e) { gs.data = null; }
    // Only the note and the list below the widget change: the gift keeps playing.
    const rest = cur && cur.key === "friends" && cur.params.tab === "give" && cur.el.querySelector(".gf-rest");
    if (!rest) return;
    const t = document.createElement("div");
    t.innerHTML = giveTab();
    const fresh = t.querySelector(".gf-rest");
    if (fresh && fresh.innerHTML !== rest.innerHTML) { fresh.classList.add("still"); rest.replaceWith(fresh); }
  }
  async function shareGift(res, copyOnly) {
    const text = res.share_text || "Подарок на VPN";
    if (copyOnly) { copy(`${text}\n\n${res.url}`, "Ссылка на подарок скопирована"); return; }
    if (res.prepared_id && typeof tg.shareMessage === "function" && (typeof tg.isVersionAtLeast !== "function" || tg.isVersionAtLeast("8.0"))) {
      call(() => tg.shareMessage(res.prepared_id, () => {}));
      return;
    }
    tg.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(res.url)}&text=${encodeURIComponent(text)}`);
  }
  async function sendGift(copyOnly) {
    if (gs.busy) return;
    const per = gs.amount, cnt = gs.count || 1, n = per * cnt, what = cnt > 1 ? `${cnt} ${pl(cnt, "подарок", "подарка", "подарков")} по ${rub(per)}` : rub(per);
    if (!gOk(per)) return;
    haptic();
    if (!gs.data) await loadGifts();
    const can = gs.data ? Number(gs.data.giftable_rub) || 0 : 0;
    if (n > can) {
      const need = n - can, min = Number(me.topup_min) || 1;
      if (await confirmAsk(can > 0 ? `Подарить можно до ${rub(can)}. Пополнить баланс на ${rub(Math.max(min, need))}?` : `Подарить можно только свои деньги. Пополнить баланс на ${rub(Math.max(min, need))}?`)) {
        pay.amount = Math.max(min, need); pay.custom = true; go("topup");
      }
      return;
    }
    const left = (Number(me.balance_rub) || 0) - n, perDay = dayPrice() * Math.max(1, phones().length);
    const warn = !me.gift_admin && phones().length && left < perDay ? `\n\nНа балансе останется ${rub(left)} — VPN может встать на паузу.` : "";
    const later = cnt > 1 ? "Каждый в группе заберёт по одному. Что не заберут, можно вернуть." : "Друг получит ссылку. Пока он её не откроет, подарок можно вернуть.";
    const ask = me.gift_admin ? `Подарить ${what}?\n\n${me.gift_granted ? "Подарок за счёт сервиса" : "Подарок от администратора"} — с вашего баланса ничего не спишется. ${later}`
      : `Подарить ${what}${cnt > 1 ? ` — ${rub(n)}` : ""} с баланса?\n\n${later}${warn}`;
    if (!(await confirmAsk(ask))) return;
    gs.busy = true;
    try {
      const res = await post("/api/gifts", { amount: per, count: cnt, style: gs.style, greeting: gs.greeting });
      me.balance_rub = res.balance_rub;
      notify("success");
      shareGift(res, copyOnly);
      loadGifts();
      load(true).catch(() => {});
    } catch (e) { showErr(e); }
    gs.busy = false;
  }
  async function giftItem(code) {
    const g = ((gs.data && gs.data.sent) || []).find((x) => x.code === code);
    if (!g) return;
    haptic();
    const pick = (id) => {
      if (id === "send") post(`/api/gifts/${encodeURIComponent(code)}/share`).then((r) => shareGift(r)).catch(showErr);
      else if (id === "copy") post(`/api/gifts/${encodeURIComponent(code)}/share`).then((r) => shareGift(r, true)).catch(showErr);
      else if (id === "back") returnGift(g);
    };
    if (typeof tg.showPopup === "function" && inTelegram()) {
      const n = Number(g.count) || 1, left = n - (Number(g.claimed_count) || 0);
      call(() => tg.showPopup({ title: n > 1 ? `${rub(g.amount_rub)} × ${n}` : `Подарок ${rub(g.amount_rub)}`,
        message: n > 1 ? `Осталось ${left} из ${n}.` : "Друг ещё не открыл его.",
        buttons: [{ id: "send", type: "default", text: "Отправить ещё раз" },
          { id: "back", type: "destructive", text: me.gift_admin ? "Отменить подарок" : n > 1 ? "Вернуть оставшиеся" : "Вернуть на баланс" }, { id: "x", type: "cancel" }] }, pick));
    } else if (await confirmAsk(`Подарок ${rub(g.amount_rub)} ещё не открыли. ${me.gift_admin ? "Отменить его" : "Вернуть его на баланс"}?`)) returnGift(g, true);
    else pick("copy");
  }
  async function returnGift(g, asked) {
    const n = Number(g.count) || 1, left = n - (Number(g.claimed_count) || 0), sum = rub(g.amount_rub * left);
    const q = me.gift_admin ? (n > 1 ? `Отменить оставшиеся ${left} из ${n}?` : `Отменить подарок ${rub(g.amount_rub)}?`)
      : n > 1 ? `Вернуть оставшиеся ${left} × ${rub(g.amount_rub)} = ${sum} на баланс?` : `Вернуть ${sum} на баланс?`;
    if (!asked && !(await confirmAsk(`${q} Ссылка перестанет работать.`))) return;
    try {
      const r = await post(`/api/gifts/${encodeURIComponent(g.code)}/return`);
      me.balance_rub = r.balance_rub;
      notify("success");
      toast(r.amount_rub ? `${rub(r.amount_rub)} снова на балансе` : "Подарок отменён");
      loadGifts();
      load(true).catch(() => {});
    } catch (e) { showErr(e); }
  }

  // ---------- the friend ----------
  // The giver's wishes: one line up to 200 characters, links and @mentions dropped (the server cleans them too).
  const gClean = (t) => String(t || "").replace(/(?:https?:\/\/|www\.)\S+|\b[\w-]+(?:\.[\w-]+)*\.(?:ru|рф|com|net|org|me|io|su|xyz|info|top|app|link|ly|gg|cc|tk|online|site|shop|pro)(?![\w-])\S*|@\w+/gi, "").replace(/[<>]/g, "").replace(/\s+/g, " ").trim().slice(0, 200);
  SCR.greet = {
    h() {
      const v = gs.greeting;
      return hc(isNy(gs.style) ? "blue" : "purple", { ill: "✍️", h: "Поздравление", p: "Друг увидит его в карточке и когда откроет подарок" }) +
        `<div class="grt"><textarea id="grt" rows="3" maxlength="200" placeholder="Например: с днём рождения!">${esc(v)}</textarea><div class="grt-n"><span>${v.length}</span> / 200</div></div>` +
        `<div class="grt-chips">${(nySeason() || isNy(gs.style) ? GREETS : ["С днём рождения! 🎉", "Пользуйся на здоровье", "Спасибо, что ты есть ❤️"]).map((t) =>
          `<button type="button" data-act="grchip" data-v="${esc(t)}" class="${t === v ? "on" : ""}">${esc(t)}</button>`).join("")}</div>` +
        NOTE("Ссылки и @упоминания убираем — так подарок не примут за спам.", true) +
        `<div class="bot"><button type="button" class="bbtn" data-act="grdone">Готово</button></div>`;
    },
    bot: true,
    on(el) {
      const ta = el.querySelector("#grt"), n = el.querySelector(".grt-n span");
      ta.addEventListener("input", () => {
        n.textContent = ta.value.length;
        el.querySelectorAll(".grt-chips button").forEach((b) => b.classList.toggle("on", b.dataset.v === ta.value));
      });
    },
  };
  SCR.present = {
    h(p) {
      const g = p.gift;
      if (!g) {
        return p.error ? hc("indigo", { ill: "🎁", h: "Подарок", p: esc(p.error), pill: "На главную", pa: 'data-act="gfhome"' })
          : hc("indigo", { cls: "shim", ill: "🎁", h: "Подарок", p: "Открываю…" }) + `<div class="cd" style="height:150px"></div>`;
      }
      const name = esc(g.from_name || "друга");
      const n = Number(g.count) || 1, many = n > 1;
      const wish = g.greeting && !g.mine ? `<div class="gf-qt"><p>«${esc(g.greeting)}»</p><small><i>${esc((g.from_name || "Д").slice(0, 1).toUpperCase())}</i>${name}</small></div>` : "";
      const leftBar = (k) => `<div class="gf-left"><div class="gf-bar"><i style="width:${Math.round((k / n) * 100)}%"></i></div><span>Осталось <b data-left>${k}</b> из ${n}</span></div>`;
      let txt, acts, bar = "";
      if (g.mine) {
        txt = many ? `<div class="H">Это ваши подарки</div><div class="P">${rub(g.amount_rub)} × ${n} — отправьте ссылку в группу</div>`
          : `<div class="H">Это ваш подарок</div><div class="P">${rub(g.amount_rub)} ждут друга — отправьте ему ссылку</div>`;
        if (many && g.status === "active") bar = leftBar(Number(g.left) || 0);
        acts = `<button type="button" class="pill" data-act="gfresend">${IC.share}<span>Отправить другу</span></button>`;
      } else if (g.claimed_by_me || p.opened) {
        txt = `<div class="N gf-amt">${rub(g.amount_rub)}</div><div class="P gf-days">${gDaysLine(g.amount_rub)} · уже на балансе</div>`;
        acts = `<button type="button" class="pill" data-act="gfvpn"><span>${phones().length ? "Открыть VPN" : "Подключить VPN"}</span></button>` +
          (g.thanked ? "" : `<button type="button" class="rnd" aria-label="Сказать спасибо" data-act="gfthanks">${HEART}</button>`);
      } else if (g.status === "active") {
        txt = `<div class="K">${name} ${many ? "раздаёт подарки" : "дарит вам"}</div><div class="H">${isNy(g.style) ? "Подарок к Новому году" : "Подарок на VPN"}</div>`;
        acts = `<button type="button" class="pill" data-act="gfopen"><span>${many ? "Забрать подарок" : "Открыть подарок"}</span></button>`;
        if (many) bar = leftBar(Number(g.left) || 0);
      } else {
        txt = g.status === "claimed" ? (many ? `<div class="H">Подарки разобрали</div><div class="P">Все ${n} ${pl(n, "подарок", "подарка", "подарков")} уже забрали — вы не успели</div>`
          : `<div class="H">Подарок уже открыли</div><div class="P">Каждый подарок открывается один раз</div>`)
          : `<div class="H">Подарок отменён</div><div class="P">Подарок вернулся к тому, кто его отправил</div>`;
        acts = `<button type="button" class="pill" data-act="gfhome"><span>На главную</span></button>`;
      }
      const hero = `<section class="hc gf gs${g.claimed_by_me || p.opened ? " opened" : ""}"><div class="ov"></div>${gBack(gSty(g.style))}${gScene()}<div class="gf-txt">${txt}</div>${g.status === "active" || g.claimed_by_me || p.opened ? wish : ""}${bar}<div class="acts">${acts}</div></section>`;
      if (g.mine || (g.status !== "active" && !g.claimed_by_me)) return hero;
      return hero + ST("Как это работает") + tl([["1", many ? "Заберите подарок" : "Откройте подарок", "Он ничего вам не стоит — подарок уже оплачен"],
        ["2", "Подключите VPN в один тап", "Кабинет подскажет, что установить"],
        [GIFT_IC, `Пользуйтесь ${days(gDays(g.amount_rub))}`, `<b>${rub(g.amount_rub)}</b> лягут на ваш баланс`]]);
    },
    on(el, p) {
      const k = gSty(p.gift && p.gift.style);
      mountGift(el, k);
      gConf(el.querySelector(".hc.gf"), k);
      if (!p.gift && !p.error) loadPresent(p.code);
      if (p.gift && (p.gift.claimed_by_me || p.opened)) gOpenedStill(el);
    },
  };
  async function loadPresent(code) {
    let gift = null, error = "";
    const c = encodeURIComponent(code || "");
    try { gift = await api(`/api/gifts/${c}`); } catch (e) { error = e.message || "Подарок не найден"; }
    if (cur && cur.key === "present" && cur.params.code === code) { cur.params.gift = gift; cur.params.error = error; rerender(false); }
  }
  // An already opened gift: the lid is gone and the light keeps shining, without the show.
  function gOpenedStill(el) {
    const h = el.querySelector(".hc.gf");
    if (!h) return;
    const q = (c) => h.querySelector(c);
    q(".gf-lid").style.opacity = 0;
    q(".gf-beam").style.opacity = 1; q(".gf-beam").classList.add("breathe");
    q(".gf-rays").style.opacity = .5; q(".gf-glow").style.opacity = .75;
    if (!reduced()) gMotes(q(".gf-beam"));
  }

  // ---------- the opening ----------
  const gSleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const EZ = { out: "cubic-bezier(.16,1,.3,1)" };
  function gPart(h, html, cls) { const e = document.createElement(cls === "i" ? "i" : "span"); e.className = "gf-p"; e.innerHTML = html || ""; h.appendChild(e); return e; }
  function gBurst(h, x0, y0) {
    for (let i = 0; i < 18; i++) {
      const s = 8 + Math.random() * 12, el = gPart(h, GSTAR(s, ["#fff", "#cbd7ff", "#ffd08a", "#9fb4ff"][i % 4]));
      const a = -Math.PI / 2 + (Math.random() - .5) * 2.8, d = 60 + Math.random() * 90, x1 = x0 + Math.cos(a) * d, y1 = y0 + Math.sin(a) * d * .8;
      el.animate([{ transform: `translate(${x0}px,${y0}px) scale(.2)`, opacity: 1 }, { transform: `translate(${x1}px,${y1}px) scale(1) rotate(90deg)`, opacity: 1, offset: .6 },
        { transform: `translate(${x1}px,${y1 + 30}px) scale(.4) rotate(140deg)`, opacity: 0 }], { duration: 1100 + Math.random() * 500, easing: "cubic-bezier(.2,.7,.3,1)", fill: "forwards" }).onfinish = () => el.remove();
    }
  }
  function gConfetti(h, x0, y0) {
    const cols = ["#ffb067", "#ffd9a8", "#ffffff", "#8fa4ff", "#e2733a"];
    for (let i = 0; i < 26; i++) {
      const el = gPart(h, "", "i"), w = 5 + Math.random() * 4;
      el.style.cssText = `width:${w}px;height:${w * 1.8}px;border-radius:2px;background:${cols[i % cols.length]}`;
      const a = -Math.PI / 2 + (Math.random() - .5) * 2.2, v = 120 + Math.random() * 120, x1 = x0 + Math.cos(a) * v * .9, y1 = y0 + Math.sin(a) * v;
      el.animate([{ transform: `translate(${x0}px,${y0}px) rotate(0)`, opacity: 1 }, { transform: `translate(${x1}px,${y1}px) rotate(${(Math.random() - .5) * 500}deg)`, opacity: 1, offset: .45 },
        { transform: `translate(${x1 + (Math.random() - .5) * 60}px,${y1 + 260}px) rotate(${(Math.random() - .5) * 1100}deg)`, opacity: 0 }],
        { duration: 1500 + Math.random() * 700, easing: "cubic-bezier(.2,.6,.4,1)", fill: "forwards" }).onfinish = () => el.remove();
    }
  }
  function gMotes(beam) {
    const tick = () => {
      if (!beam.isConnected) return;
      const m = document.createElement("i"); m.className = "mote"; beam.appendChild(m);
      const x0 = (Math.random() - .5) * 40, x1 = x0 * 2.6 + (Math.random() - .5) * 30, s = .5 + Math.random() * .9;
      m.animate([{ transform: `translate(${x0}px,0) scale(${s})`, opacity: 0 }, { opacity: 1, offset: .2 }, { opacity: .8, offset: .7 },
        { transform: `translate(${x1}px,-${150 + Math.random() * 60}px) scale(${s * .6})`, opacity: 0 }], { duration: 1600 + Math.random() * 1400, easing: "cubic-bezier(.3,.5,.5,1)" }).onfinish = () => m.remove();
      setTimeout(tick, 90 + Math.random() * 120);
    };
    tick();
  }
  function gWave(h, x, y, delay = 0, size = 9) {
    const w = document.createElement("i"); w.className = "gf-wave"; h.appendChild(w);
    w.animate([{ transform: `translate(${x}px,${y}px) scale(.2)`, opacity: 1 }, { transform: `translate(${x}px,${y}px) scale(${size})`, opacity: 0 }],
      { duration: 750, delay, easing: "cubic-bezier(.1,.7,.3,1)", fill: "both" }).onfinish = () => w.remove();
  }
  function gSpark(h, x, y, n = 5, big = 12) {
    for (let i = 0; i < n; i++) {
      const sz = 6 + Math.random() * big, el = gPart(h, GSTAR(sz, i % 2 ? "#fff" : "#ffe08a"));
      const a = Math.random() * Math.PI * 2, d = 14 + Math.random() * 26;
      el.animate([{ transform: `translate(${x - sz / 2}px,${y - sz / 2}px) scale(.2) rotate(0)`, opacity: 1 },
        { transform: `translate(${x - sz / 2 + Math.cos(a) * d}px,${y - sz / 2 + Math.sin(a) * d}px) scale(1) rotate(90deg)`, opacity: 0 }],
        { duration: 420 + Math.random() * 200, easing: "cubic-bezier(.2,.7,.3,1)", fill: "forwards" }).onfinish = () => el.remove();
    }
  }
  function gShake(el) {
    el.animate([0, 1, 2, 3, 4, 5, 6].map((i) => ({ transform: i === 6 ? "none" : `translate(${(Math.random() - .5) * 10 * (1 - i / 6)}px,${(Math.random() - .5) * 8 * (1 - i / 6)}px)` })),
      { duration: 340, easing: "linear" });
  }
  const COIN = `<svg viewBox="0 0 40 40" width="100%" height="100%"><defs><radialGradient id="gfcg" cx="35%" cy="30%" r="75%"><stop offset="0" stop-color="#fff3b8"/><stop offset=".45" stop-color="#ffc94a"/><stop offset="1" stop-color="#d98a12"/></radialGradient></defs>` +
    `<circle cx="20" cy="20" r="18.5" fill="url(#gfcg)" stroke="#a8620e" stroke-width="2"/><circle cx="20" cy="20" r="13.5" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="1.4"/>` +
    `<text x="20" y="26.5" text-anchor="middle" font-size="17" font-weight="800" fill="#b06a10" font-family="-apple-system,system-ui">₽</text><path d="M9 14c2-4 6-6 10-6" stroke="#fff" stroke-width="2.4" stroke-linecap="round" opacity=".8"/></svg>`;
  // Coins shoot out of the box, flip in the air and land in the amount, which counts up on every hit.
  function gCoins(h, ox, oy, getT, total, n = 12) {
    const hr = h.getBoundingClientRect();
    let got = 0;
    for (let i = 0; i < n; i++) {
      const el = document.createElement("span"); el.className = "gf-coin"; el.innerHTML = `<b>${COIN}</b>`; h.appendChild(el);
      const sz = 26 + Math.random() * 12; el.style.width = el.style.height = sz + "px"; el.firstChild.style.animationDuration = (.35 + Math.random() * .3) + "s";
      const side = i % 2 ? 1 : -1, ax = ox + side * (40 + Math.random() * 110), ay = Math.max(24, oy - 20 - Math.random() * 60), delay = i * 28 + Math.random() * 25;
      el.animate([{ transform: `translate(${ox - sz / 2}px,${oy - sz / 2}px) scale(.3)`, opacity: 0 }, { opacity: 1, offset: .15 }, { transform: `translate(${ax - sz / 2}px,${ay - sz / 2}px) scale(1)`, opacity: 1 }],
        { duration: 420, delay, easing: "cubic-bezier(.2,.8,.35,1)", fill: "forwards" }).finished.then(() => {
        const target = getT();
        if (!target) { el.remove(); return; }
        const num = target.querySelector("[data-c]"), tr = target.getBoundingClientRect(), tx = tr.left - hr.left + tr.width / 2 + (Math.random() - .5) * 40, ty = tr.top - hr.top + tr.height / 2;
        el.animate([{ transform: `translate(${ax - sz / 2}px,${ay - sz / 2}px) scale(1)` }, { transform: `translate(${(ax * 2 + tx) / 3 - sz / 2}px,${ay - 12 - sz / 2}px) scale(.95)`, offset: .3 },
          { transform: `translate(${tx - sz / 2}px,${ty - sz / 2}px) scale(.45)`, opacity: .9 }], { duration: 360 + Math.random() * 100, easing: "cubic-bezier(.5,0,.75,.4)", fill: "forwards" })
          .finished.then(() => {
            el.remove(); got++;
            if (num) num.textContent = fmt(Math.round(total * got / n));
            haptic("light");
            target.animate([{ transform: "scale(1)" }, { transform: "scale(1.09)" }, { transform: "scale(1)" }], { duration: 180, easing: "ease-out" });
            gSpark(h, tx, ty, 3, 8);
            if (got === n) {
              target.classList.add("gold");
              const r2 = target.getBoundingClientRect(), cx = r2.left - hr.left + r2.width / 2, cy = r2.top - hr.top + r2.height / 2;
              gSpark(h, cx, cy, 10, 16); gWave(h, cx, cy, 0, 4);
              notify("success");
            }
          });
      });
    }
  }
  async function openPresent() {
    const p = cur && cur.key === "present" ? cur.params : null, g = p && p.gift;
    const el = cur && cur.el, h = el && el.querySelector(".hc.gf");
    if (!g || !h || h.classList.contains("opened") || g.status !== "active" || g.mine) return;
    h.classList.add("opened");
    haptic("medium");
    const q = (c) => h.querySelector(c), box = q(".gf-box"), lid = q(".gf-lid"), body = q(".gf-body"), pill = q(".acts .pill");
    if (pill) pill.classList.add("dim");
    const claim = post(`/api/gifts/${encodeURIComponent(g.code)}/claim`).then((r) => ({ r }), (e) => ({ e }));
    // 1 · it fights back: squash, then a shake that grows, light leaking out
    q(".gf-glow").animate([{ opacity: 0, transform: "scale(.5)" }, { opacity: .55, transform: "scale(.8)" }], { duration: 520, easing: "ease-in", fill: "forwards" });
    await box.animate([{ transform: "none" }, { transform: "scale(1.06,.92) translateY(4px)", offset: .22 }, { transform: "rotate(-2deg) scale(1.02,.97)", offset: .4 },
      { transform: "rotate(3deg)", offset: .55 }, { transform: "rotate(-4deg)", offset: .7 }, { transform: "rotate(5deg) scale(.98,1.04)", offset: .85 }, { transform: "scale(1.1,.86) translateY(6px)" }],
      { duration: 560, easing: "ease-in-out" }).finished;
    const res = await claim;
    if (res.e) {
      // The gift stays shut: back to the closed box with the error.
      h.classList.remove("opened");
      if (pill) pill.classList.remove("dim");
      q(".gf-glow").getAnimations().forEach((a) => a.cancel());
      showErr(res.e);
      loadPresent(g.code);
      return;
    }
    const ill = q(".gf-ill");
    if (ill && ill._players) ill._players.forEach((a) => a.pause());
    haptic("heavy");
    // 2 · the lid with the bow is blown off
    lid.animate([{ transform: "none" }, { transform: "translateY(-46px) rotate(-10deg) scale(1.04)", offset: .28 }, { transform: "translate(120px,-150px) rotate(42deg) scale(.8)", opacity: .9, offset: .8 },
      { transform: "translate(150px,-190px) rotate(60deg) scale(.7)", opacity: 0 }], { duration: 900, easing: "cubic-bezier(.25,.8,.35,1)", fill: "forwards" });
    body.animate([{ transform: "scale(1.1,.86)" }, { transform: "scale(.94,1.08)", offset: .35 }, { transform: "scale(1.03,.97)", offset: .65 }, { transform: "none" }], { duration: 620, easing: "ease-out" });
    q(".gf-flash").animate([{ opacity: 0, transform: "scale(.3)" }, { opacity: 1, transform: "scale(1)", offset: .25 }, { opacity: 0, transform: "scale(1.6)" }], { duration: 520, easing: "ease-out" });
    const beam = q(".gf-beam");
    beam.animate([{ opacity: 0, transform: "scale(.08,.15)" }, { opacity: 1, transform: "scale(.35,1.12)", offset: .3 }, { opacity: 1, transform: "scale(1.12,1.04)", offset: .65 }, { opacity: .95, transform: "scale(1)" }],
      { duration: 900, easing: EZ.out }).finished.then(() => { beam.style.opacity = 1; beam.classList.add("breathe"); });
    gMotes(beam);
    q(".gf-rays").animate([{ opacity: 0, scale: .4 }, { opacity: .5, scale: 1 }], { duration: 1100, easing: EZ.out, fill: "forwards" });
    q(".gf-glow").animate([{ opacity: .55, transform: "scale(.8)" }, { opacity: 1, transform: "scale(1.15)" }, { opacity: .75, transform: "scale(1)" }], { duration: 900, easing: EZ.out, fill: "forwards" });
    const r = box.getBoundingClientRect(), hr = h.getBoundingClientRect(), ox = r.left - hr.left + 158, oy = r.top - hr.top + 52;
    gShake(h); gWave(h, ox, oy); gWave(h, ox, oy, 120, 6);
    h.insertAdjacentHTML("afterbegin", '<div class="gf-warm"></div>');
    q(".gf-warm").animate([{ opacity: 0 }, { opacity: 1, offset: .15 }, { opacity: .35 }], { duration: 1400, easing: "ease-out", fill: "forwards" });
    const t0 = performance.now();
    const trail = () => {
      const k = (performance.now() - t0) / 620;
      if (k > 1 || !h.isConnected) return;
      gSpark(h, ox + (k < .3 ? 0 : (k - .3) / .7 * 125), oy + 6 - (k < .3 ? k / .3 * 46 : 46 + (k - .3) / .7 * 110), 2, 9);
      setTimeout(trail, 45);
    };
    trail();
    gBurst(h, ox - 8, oy - 8); gConfetti(h, ox, oy);
    const amount = Number(res.r.amount_rub) || g.amount_rub;
    gCoins(h, ox, oy, () => h.querySelector(".gf-amt"), amount);
    // 3 · the amount takes the title's place and counts up
    await gSleep(200);
    p.opened = true; g.claimed_by_me = true; g.status = "claimed";
    const lf = h.querySelector("[data-left]");
    if (lf && res.r.left != null) {
      lf.textContent = res.r.left;
      const bi = h.querySelector(".gf-bar i");
      if (bi) bi.style.width = `${Math.round((res.r.left / (Number(g.count) || 1)) * 100)}%`;
    }
    if (res.r.balance_rub != null) { me.balance_rub = res.r.balance_rub; store.set("seen_bal", Number(me.balance_rub) || 0); }
    const txt = q(".gf-txt");
    txt.innerHTML = `<div class="N gf-amt"><span data-c>0</span> ₽</div><div class="P gf-days">${gDaysLine(amount)} · уже на балансе</div>`;
    txt.classList.add("gf-swap");
    q(".acts").outerHTML = `<div class="acts gf-swap"><button type="button" class="pill" data-act="gfvpn"><span>${phones().length ? "Открыть VPN" : "Подключить VPN"}</span></button>` +
      `<button type="button" class="rnd" aria-label="Сказать спасибо" data-act="gfthanks">${HEART}</button></div>`;
    load(true).catch(() => {});
  }

  Object.assign(ACT, {
    gftab(b) {
      haptic();
      const tab = b.dataset.v;
      if (!cur || cur.key !== "friends" || cur.params.tab === tab) return;
      cur.params.tab = tab;
      // The tabs stay put; only the content below them fades over, without replaying the screen's entrance.
      cur.el.querySelectorAll(".seg button").forEach((x) => x.classList.toggle("on", x.dataset.v === tab));
      const box = cur.el.querySelector(".tabc");
      const fresh = document.createElement("div");
      fresh.className = "tabc tsw";
      fresh.innerHTML = tab === "give" ? giveTab() : SCR.friends.invite();
      box.replaceWith(fresh);
      sparkle(fresh);
      if (tab === "give") { gGive(fresh); loadGifts(); } else gInvite(fresh);
      cur.sig = SCR.friends.sig(cur.params);
    },
    gfamt(b) {
      haptic();
      const old = gs.amount;
      gs.amount = Number(b.dataset.v); gs.custom = false; gs.count = 1;
      cur.el.querySelectorAll(".hc.gf .chp button").forEach((c) => c.classList.toggle("on", c === b));
      const own = cur.el.querySelector('.hc.gf [data-act="gfown"]');
      if (own) own.textContent = "Своя";
      gPaint(cur.el, old);
      const sx = cur.el.querySelector(".tl .sx b");
      if (sx) sx.textContent = rub(gs.amount);
    },
    gfown() { haptic(); amt.gift = true; amt.cnt = gs.count || 1; amt.v = gs.custom ? String(gs.amount) : ""; amt.mode = "rub"; amt.d = ""; go("amount", { gift: true }); },
    gfsty: (b) => gPick(b.dataset.k),
    gfsend: () => sendGift(false),
    gfcopy: () => sendGift(true),
    gfitem: (b) => giftItem(b.dataset.code),
    gfgive() { haptic(); go("friends", { tab: "give" }); },
    gfgreet() { haptic(); go("greet"); },
    grchip(b) { haptic("light"); const ta = cur.el.querySelector("#grt"); ta.value = b.dataset.v; ta.dispatchEvent(new Event("input")); },
    grdone() { haptic(); gs.greeting = gClean(cur.el.querySelector("#grt").value); gs.greeted = true; back(); },
    gfbox() { if (cur && cur.key === "present") openPresent(); else if (cur) { const i = cur.el.querySelector(".gf-box"); if (i) { haptic(); gShake(i); } } },
    gfopen: () => openPresent(),
    gfresend() { const g = cur.params.gift; if (g) post(`/api/gifts/${encodeURIComponent(g.code)}/share`).then((r) => shareGift(r)).catch(showErr); },
    async gfthanks(b) {
      const g = cur.params.gift;
      if (!g) return;
      haptic("medium");
      b.classList.add("dim");
      try {
        await post(`/api/gifts/${encodeURIComponent(g.code)}/thanks`);
        g.thanked = true;
        notify("success");
        toast(`${g.from_name || "Друг"} получит ваше спасибо ❤️`);
        b.animate([{ transform: "scale(1)" }, { transform: "scale(1.3)" }, { transform: "scale(0)", opacity: 0 }], { duration: 420, easing: "ease-in", fill: "forwards" }).onfinish = () => b.remove();
      } catch (e) { b.classList.remove("dim"); showErr(e); }
    },
    gfvpn() { haptic(); stack = []; go("home", {}, "x"); if (phones().length) resume(); else startWizard(); },
    gfhome() { home(); },
  });

  let loginSeq = 0;
  // Waits for «Да, это я». Returns "approved" (already logged in), "declined", "expired" or "stopped".
  async function pollLogin(seq, id) {
    const started = Date.now();
    while (seq === loginSeq && Date.now() - started < 600000) {
      await new Promise((r) => setTimeout(r, 1400));
      if (seq !== loginSeq) return "stopped";
      try {
        const data = await (await fetch("/api/cabinet-login/status?id=" + encodeURIComponent(id))).json();
        if (seq !== loginSeq) return "stopped";
        if (data && data.token) { loginSeq++; saveToken(data.token); go("boot", {}, "x"); await load(); return "approved"; }
        if (data && (data.status === "declined" || data.status === "expired")) return data.status;
      } catch (_e) { /* keep waiting */ }
    }
    return seq === loginSeq ? "expired" : "stopped";
  }
  async function tgLogin(msg) {
    const seq = ++loginSeq;
    let data = null;
    try {
      const res = await fetch("/api/cabinet-login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ via: "tg" }) });
      data = await res.json();
    } catch (_e) { data = null; }
    if (seq !== loginSeq) return;
    if (!data || !data.link || !data.wait) { go("login", { failed: true }, "x"); return; }
    go("login", { link: data.link, msg }, "x");
    const st = await pollLogin(seq, data.wait);
    if (st === "declined") tgLogin("Вход отклонён в Telegram. Если это были вы — попробуйте ещё раз.");
    else if (st === "expired") tgLogin(); // a fresh link and QR, the old one is no longer valid
  }
  // An unknown or declined login sees an ordinary search page, not a hint that the account exists.
  function decoy(q) {
    q = String(q || "").trim();
    call(() => {
      const params = new URLSearchParams(location.search);
      params.delete("t");
      if (q) params.set("q", q); else params.delete("q");
      history.replaceState({}, "", location.pathname + (params.toString() ? `?${params}` : ""));
    });
    document.title = q ? `${q} — Поиск` : "Поиск";
    const enc = encodeURIComponent(q || "запрос");
    const hits = q ? [["ru.wikipedia.org", `${q} — Википедия`, `https://ru.wikipedia.org/w/index.php?search=${enc}`, `Краткая справка и ссылки по запросу «${q}».`],
      ["www.google.com", `Результаты по запросу ${q}`, `https://www.google.com/search?q=${enc}`, `Документы, новости и страницы, где встречается «${q}».`],
      ["yandex.ru", `${q}: что это и где искать`, `https://yandex.ru/search/?text=${enc}`, "Подборка открытых источников и похожие формулировки."]] : [];
    document.body.innerHTML = `<div class="decoy"><form id="dq"><input name="q" value="${esc(q)}" placeholder="Поиск"><button>Найти</button></form>` +
      (q ? `<div class="stats">Результатов: примерно ${(800000 + (q.length * 17341) % 9000000).toLocaleString("ru-RU")} (0,31 сек.)</div>` : "") +
      hits.map((h) => `<div class="hit"><a href="${esc(h[2])}" target="_blank" rel="noopener noreferrer"><cite>${esc(h[0])}</cite><h3>${esc(h[1])}</h3></a><p>${esc(h[3])}</p></div>`).join("") + "</div>";
    document.getElementById("dq").onsubmit = (e) => { e.preventDefault(); decoy(e.target.q.value); };
  }

  document.addEventListener("click", (ev) => {
    const a = ev.target.closest("[data-act],[data-go]");
    if (!a || !root().contains(a)) return;
    if (a.classList.contains("dim") || a.disabled) return;
    if (a.dataset.go) { haptic(); go(a.dataset.go, a.dataset.amount ? { amount: Number(a.dataset.amount) } : {}); return; }
    const f = ACT[a.dataset.act];
    if (f) f(a);
  });
  call(() => tg.BackButton.onClick(back));
  const wb = document.getElementById("webBack");
  if (wb) wb.onclick = back;

  // =====================================================================
  // data
  // =====================================================================
  let loadSeq = 0;
  let entryDone = false;
  function onboardDone() { return store.get("onboard") === "1"; }
  async function load(quiet) {
    if (!inTelegram() && !lkToken) { go("login", {}, "x"); return; }
    const seq = ++loadSeq;
    const data = await api("/api/me");
    if (seq !== loadSeq) return;
    if (data.maintenance || data.blocked) { me = null; go("maint", { notice: data.notice, blocked: data.blocked }, "x"); return; }
    const prev = me;
    me = data;
    me.balance_enabled = true;
    if (me.brand_name) document.title = me.brand_name;
    if (me.first_device_thanks_pending) thanksArmed = true;
    nfPreload(me.friend_nft);
    if (!cur || SCR[cur.key].bare) { first(); return; }
    // Fresh data repaints screens that show it, only when something they show has changed.
    const s = SCR[cur.key];
    if (s.live) {
      const before = cur.sig, after = s.sig ? s.sig(cur.params) : "";
      if (before !== after) { cur.sig = after; if (prev) rerender(); }
    }
    celebrate(prev);
  }
  // Money that arrived while the cabinet was open (or since the last visit) gets a small celebration.
  function celebrate(prev) {
    if (!cur || cur.key !== "home" || !me.has_paid_topup) return;
    const saved = store.get("seen_bal");
    const was = prev ? Number(prev.balance_rub) : saved == null || saved === "" ? NaN : Number(saved);
    const now = Number(me.balance_rub) || 0;
    store.set("seen_bal", now);
    if (Number.isFinite(was) && now - was >= 10) { boom(); notify("success"); toast(`+${rub(now - was)} на балансе 🎉`); }
  }
  function first() {
    const entry = entryDone ? "" : new URLSearchParams(location.search).get("screen");
    entryDone = true;
    stack = [];
    go("home", {}, "x");
    if (entry === "support") { openSupport(); return; }
    if (entry === "topup") {
      // «Пополнить 50 ₽» in a bot message opens the top-up with that amount already chosen.
      const a = Number(new URLSearchParams(location.search).get("amount"));
      if (amountOk(a)) { pay.amount = a; pay.custom = false; }
      go("topup"); return;
    }
    if (entry === "present") { const code = new URLSearchParams(location.search).get("code"); if (code) { go("present", { code }); return; } }
    if (entry === "giftsend" && me.gifts_enabled) { go("friends", { tab: "give" }); return; }
    if (entry === "friends") { go("friends", { tab: "invite" }); return; }
    if (entry === "browser") { openBrowserSheet(); return; }
    if (entry === "autopay" && me.autopay) { go("autopay"); return; }
    if (entry === "promise") { const t = me.trust || {}; go(t.open || t.available ? "promise" : "topup"); return; }
    if (entry === "gift" && me.trial_available) { go("gift"); return; }
    if (entry === "connect" || entry === "gift") { if (phones().length) resume(); else startWizard(); return; }
    if (showOffer()) { go("gift"); return; }
    if (!(me.devices || []).length && !onboardDone() && !alertState()) { startWizard(); return; }
    celebrate(null);
  }
  function failed(err) {
    const msg = (err && err.message) || "Не удалось загрузить данные";
    if (!inTelegram() && (/недействительна|истекла/i.test(msg) || !lkToken)) { saveToken(""); go("login", {}, "x"); return; }
    go("fail", { msg }, "x");
  }

  if (tg.onEvent) {
    tg.onEvent("invoiceClosed", (ev) => { if ((ev && ev.status) === "paid" || ev === "paid") load(true).catch(() => {}); });
    tg.onEvent("viewportChanged", () => { applyViewport(); fullscreen(); });
    tg.onEvent("fullscreenChanged", applyViewport);
    tg.onEvent("safeAreaChanged", applyViewport);
    tg.onEvent("contentSafeAreaChanged", applyViewport);
    tg.onEvent("activated", () => { call(() => tg.expand()); fullscreen(); applyViewport(); });
  }
  let visTimer = 0;
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "visible" || !me) return;
    clearTimeout(visTimer);
    visTimer = setTimeout(() => load(true).then(() => cur && cur.key === "wait" && checkPaid(cur.el)).catch(() => {}), 400);
  });
  setInterval(() => {
    if (document.visibilityState !== "visible" || !me || !cur) return;
    if (["home", "device", "wiz3", "promise", "autopay"].includes(cur.key)) load(true).catch(() => {});
  }, 15000);

  window.__cab = { go, back, get me() { return me; }, get cur() { return cur; }, load, toast, boom };
  go("boot", {}, "x");
  load().catch(failed);
})();
