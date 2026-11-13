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
  const GEM = (w) => `<svg width="${w}" height="${w}" viewBox="0 0 100 100"><path fill="#fff" d="${GP}"/><path class="gst" fill="#2f86f0" style="transition:fill .7s" d="${SPK}"/></svg>`;
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
    const acts = o.pill ? `<div class="acts"><button type="button" class="pill${o.pd ? " dim" : ""}" ${o.pa || ""}>${o.pi ? IC[o.pi] : ""}<span>${o.pill}</span></button>${
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
      stores: { ios: "https://apps.apple.com/search?term=Incy", macos: "https://apps.apple.com/search?term=Incy", appletv: "https://apps.apple.com/search?term=Incy" } },
    { id: "happ", name: "Happ", icon: "/icons/happ.png", deep_link: "happ://add/{url}", platforms: ["ios", "macos", "appletv", "android", "androidtv", "windows"],
      stores: { ios: "https://apps.apple.com/app/id6504287215", macos: "https://apps.apple.com/app/id6504287215", appletv: "https://apps.apple.com/app/id6504287215",
        android: "https://play.google.com/store/apps/details?id=com.happproxy", androidtv: "https://play.google.com/store/apps/details?id=com.happproxy",
        windows: "https://github.com/Happ-proxy/happ-desktop/releases" } },
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
  const platTitle = (id) => (PLATFORMS.find((p) => p.id === id) || { title: "Устройство" }).title;
  const storeName = (p) => (["ios", "macos", "appletv"].includes(p) ? "App Store" : ["android", "androidtv"].includes(p) ? "Google Play" : "интернете");
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
    tg.openLink(new URL("open.html", location.href).href + "?to=" + encodeURIComponent(deep));
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
  SCR.home = {
    live: true,
    h() {
      const devs = phones(), alert = alertState(), bal = Number(me.balance_rub) || 0;
      const from = Number(store.get("shown_bal"));
      const N = cnt(Math.abs(bal), " ₽", bal < 0 ? "−" : "", Number.isFinite(from) && from >= 0 ? from : 0);
      const trust = me.trust || {};
      let hero;
      if (alert === "empty") {
        hero = hc("red", { rb: "пауза", ill: FROG(78, true), n: N,
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
        hero = hc(low ? "orange" : "green", { rb: me.billing_paused ? "пауза" : "VPN вкл", ill: FROG(78), n: N,
          p: low ? `Осталось меньше суток — пополните заранее` : (me.billing_paused ? "Списания приостановлены. VPN доступен." : runway()),
          x: me.cabinet_price_enabled ? `<div class="chip">${dayPrice()} ₽ в день за устройство</div>` : "",
          pill: "Пополнить", pi: "plus", pa: 'data-go="topup"', r: "ref", rl: "Обновить", ra: 'data-act="refresh"' });
      }
      const cap = Number(me.max_devices) || 0;
      const devRows = devs.map((d) => [E(devIcon(d)) + TT(esc(d.title || "Устройство"),
        devLine(d)) + V(CV), `data-act="device" data-id="${d.id}"`]);
      const dupes = dupeGroup();
      if (devs.length && !(cap > 0 && devs.length >= cap)) devRows.push([E("＋") + "Добавить устройство", 'data-act="wizard"', "blue"]);
      const invitee = Number(me.referral_invitee_reward_rub) || 0;
      const showInvitee = me.referral_program_enabled && me.referred && !me.has_paid_topup && invitee > 0;
      const survey = me.first_online_at && !me.has_paid_topup && !me.vpn_feedback;
      const giftLater = me.trial_available && !showOffer() ? [E("🎁") + "Попробовать бесплатно" + V(rub(me.trial_rub) + " " + CV), 'data-go="gift"'] : null;
      return hero +
        (showInvitee ? NOTE(`Вы пришли по ссылке друга — после первого пополнения на баланс ещё ${rub(invitee)}.`, true) : "") +
        (dupes ? dupeCard(dupes) : "") +
        (devRows.length ? ST(`Устройства${cap ? ` <span style="color:var(--hint);font-weight:500">· ${devs.length} из ${cap}</span>` : ""}`) + cd(devRows) : "") +
        (survey ? ST("Как работает VPN?") + cd([[E("✅") + "Всё работает", 'data-act="vfb" data-v="ok"'], [E("🆘") + "Нужна помощь", 'data-act="vfb" data-v="help"'],
          [E("🤔") + "Не подошли условия", 'data-act="vfb" data-v="terms"']]) : "") +
        `<div style="height:12px"></div>` +
        cd([
          giftLater,
          [E("🎁") + "Пригласить друзей" + V((me.referral_program_enabled ? `+${rub(me.referral_reward_rub || 50)} ` : "") + CV), 'data-go="friends"'],
          trustShown() ? [E("🤝") + "Обещанный платёж" + V((trust.open ? "открыт " : "") + CV), 'data-go="promise"'] : null,
          [E("⚙️") + "Настройки" + V(CV), 'data-go="settings"'],
        ]);
    },
    on() {
      store.set("shown_bal", Number(me.balance_rub) || 0);
      track("cabinet");
    },
    sig: () => JSON.stringify([me.balance_rub, me.hours_left, me.billing_paused, me.devices, me.first_online_at, me.trust, me.trial_available, me.vpn_feedback, me.has_paid_topup]),
  };

  // ---------- gift for newcomers ----------
  SCR.gift = {
    h() {
      const n = Number((me.trial_notice && me.trial_notice.days) || me.trial_days) || 3;
      const bot = me.trial_notice && me.trial_notice.kind === "start_bot";
      const gb = Number(me.traffic_limit_gb) || 0;
      return hc("purple", { ill: "🎁", h: `Дарим ${days(n)} VPN`, p: "Попробуйте бесплатно на одном устройстве. Карта не нужна",
        pill: bot ? "Запустить бота" : "Забрать подарок", pa: 'data-act="gift"' }) +
        ST("Как это работает") +
        tl([["1", "Забираете подарок", me.trial_rub ? `<b>+${rub(me.trial_rub)}</b> на баланс сразу` : "сразу на баланс"],
          ["2", "Добавляете устройство", "iPhone, Android, Mac или Windows"],
          ["3", `Платите ${dayPrice()} ₽ в день`, "только пока пользуетесь"]]) +
        (gb ? NOTE(`В пробный период доступно ${gb} ГБ`) : "");
    },
    on() { track("gift_view"); },
  };

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
  const METHOD_EMO = { ton: "💎", stars: "⭐", sbp: "🏦", card: "💳", crypto: "🪙" };
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
  const SBPBIG = (w) => `<div style="width:${w}px;height:${w}px;border-radius:${Math.round(w * .28)}px;background:#fff;display:flex;align-items:center;justify-content:center;box-shadow:0 10px 24px rgba(0,0,0,.25)"><img src="/icons/sbp.svg" width="${Math.round(w * .5)}" height="${Math.round(w * .58)}" alt=""></div>`;
  const CARDBIG = (w) => `<svg width="${w}" height="${Math.round(w * .72)}" viewBox="0 0 100 72"><rect x="2" y="2" width="96" height="68" rx="12" fill="#fff"/><rect x="2" y="16" width="96" height="12" fill="#2b3a66"/>` +
    `<rect x="12" y="40" width="22" height="16" rx="3" fill="#f2c14e"/><rect x="44" y="46" width="40" height="5" rx="2.5" fill="#c9cfdc"/></svg>`;
  const LOOK = {
    ton: { c: "blue", ill: (w) => GEM(w) },
    stars: { c: "stars", ill: (w) => STARBIG(w + 28) },
    sbp: { c: "sbp", ill: (w) => SBPBIG(w + 4) },
    card: { c: "cardpay", ill: (w) => CARDBIG(w + 14) },
    crypto: { c: "slate", ill: () => "🪙" },
  };
  const look = (m) => LOOK[(m && m.id) || ""] || LOOK.ton;
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
      const firstPay = !me.has_paid_topup, start = firstPay ? 100 : 500;
      if (!amountOk(pay.amount)) pay.amount = amountOk(start) ? start : Number(me.topup_min) || 100;
      const chips = [...new Set(firstPay ? [Number(me.topup_min) || 50, 100, 300, 500] : [100, 300, 500, 1000])].filter(amountOk);
      const m = curMethod();
      const inChips = chips.includes(pay.amount) && !pay.custom;
      const L = look(m);
      return hc(L.c, { ill: L.ill(72), n: `<span id="amtN">${rub(pay.amount)}</span>`, p: `<span id="amtP">${amountLine()}</span>`,
        x: `<div class="chp">${chips.map((v) => `<button type="button" data-act="amt" data-v="${v}" class="${inChips && v === pay.amount ? "on" : ""}">${fmt(v)}</button>`).join("")}` +
          `<button type="button" data-act="amtc" class="${inChips ? "" : "on"}">${inChips ? "Своя" : fmt(pay.amount) + " ✎"}</button></div>`,
        pill: m ? `Оплатить ${rub(pay.amount)}` : "Оплата недоступна", pd: !m || !amountOk(pay.amount), pa: 'data-act="pay" id="payB"' }) +
        (m ? ST("Способ оплаты") + cd([[E(METHOD_EMO[m.id] || "💳") + TT(esc(m.title), esc(methodSub(m))) + (payMethods().length > 1 ? V("Изменить " + CV) : ""),
          payMethods().length > 1 ? 'data-go="method"' : ""]]) : NOTE("Оплата временно недоступна. Попробуйте позже или напишите в поддержку.", true)) +
        NOTE(`Баланс ${rub(me.balance_rub)} · разовая оплата, автоплатежей нет`, true);
    },
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
  }

  // ---------- own amount: big number, own keypad, live hints ----------
  const GRAM = (w) => `<svg width="${w}" height="${w}" viewBox="0 0 100 100"><path fill="#30A1F5" d="${GP}"/><path fill="#fff" d="${SPK}"/></svg>`;
  const AM_ICON = { ton: () => GRAM(42), stars: () => STARBIG(52), sbp: () => `<img src="/icons/sbp.svg" width="30" height="35" alt="">`, card: () => CARDBIG(40), crypto: () => "🪙" };
  const AM_TONE = { ton: "", stars: "gold", sbp: "green", card: "green", crypto: "" };
  const amt = { v: "", d: "", mode: "rub", rolling: false };
  const amN = () => Number(amt.v) || 0;
  const amBig = () => (amt.mode === "rub" ? fmt(amN()) : fmt(Number(amt.d) || 0));
  // In days mode the keypad types days; the ruble amount follows as days × price of a day for all devices.
  const amPerDay = () => dayPrice() * Math.max(1, phones().length);
  const amDays = () => (amt.mode === "rub" ? daysFor(amN()) : Number(amt.d) || 0);
  const amRow = (m) => cd([[E(METHOD_EMO[m.id] || "💳") + TT(esc(m.title), `Баланс ${rub(me.balance_rub)}`) + (payMethods().length > 1 ? V("Изменить " + CV) : ""),
    payMethods().length > 1 ? 'data-go="method"' : ""]]);
  SCR.amount = {
    h() {
      const m = curMethod();
      const id = (m && m.id) || "ton";
      return `<div class="am ${AM_TONE[id] || ""}" id="am">` +
        (m ? amRow(m) : NOTE("Оплата временно недоступна. Попробуйте позже или напишите в поддержку.", true)) +
        `<div class="am-stage zero" id="amStage"><svg width="0" height="0" style="position:absolute"><filter id="amGoo"><feGaussianBlur stdDeviation="3.5"/><feColorMatrix values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 22 -9"/></filter></svg><div class="am-glow"></div>` +
          `<div class="am-w" id="amW"><button type="button" class="am-ico in" id="amIco" data-act="amtico" aria-label="Сменить способ оплаты"><span class="am-ic">${(AM_ICON[id] || AM_ICON.ton)()}</span></button>` +
          `<div class="am-num" id="amNum"><span>0</span></div><div class="am-caret"></div><div class="am-unit" id="amUnit">₽</div></div>` +
          `<button type="button" class="am-sub" id="amSub" data-act="amtsw"><span id="amSubT"></span><span class="sw">⇅</span></button>` +
          `<div class="am-hint">Наберите сумму</div></div>` +
        `<div class="am-bottom"><div class="am-quick">${[100, 500, 1000].map((q) => `<button type="button" data-act="amtq" data-v="${q}">+${fmt(q)}</button>`).join("")}</div>` +
          `<button type="button" class="am-pay off" id="amPay" data-act="amtpay"><span>Введите сумму</span></button>` +
          `<div class="am-padw"><div><div class="am-pad">${["1", "2", "3", "4", "5", "6", "7", "8", "9", "c", "0", "b"].map((k) =>
            `<button type="button" data-act="amtk" data-v="${k}"${k === "c" || k === "b" ? ' class="fn"' : ""} aria-label="${k === "b" ? "Стереть" : k === "c" ? "Очистить" : k}">${k === "b" ? "⌫" : k === "c" ? "C" : k}</button>`).join("")}</div></div></div></div>` +
        `</div>`;
    },
    on(el) {
      amt.rolling = false;
      amSetNum(el, amBig(), null);
      amSide(el);
      // The keypad slides up with a ring, like tapping the amount in Telegram.
      timers.push(setTimeout(() => {
        if (!cur || cur.el !== el) return;
        const r = el.querySelector("#amW").getBoundingClientRect();
        amRing(r.left + r.width / 2, r.top + r.height / 2);
        el.querySelector("#am").classList.add("open");
      }, 380));
    },
  };
  function amRing(x, y) {
    const r = document.createElement("div");
    r.className = "am-ring";
    r.style.left = `${x}px`; r.style.top = `${y}px`;
    cur.el.querySelector("#am").appendChild(r);
    setTimeout(() => r.remove(), 650);
  }
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
    const n = amN(), ok = amountOk(n), min = Number(me.topup_min) || 1, max = Number(me.topup_max) || 100000;
    el.querySelector("#amStage").classList.toggle("zero", !n);
    const sub = el.querySelector("#amSub");
    sub.classList.toggle("bad", Boolean(n) && !ok);
    el.querySelector("#amSubT").textContent = !n ? "" : n < min ? `Минимум ${rub(min)}` : n > max ? `Максимум ${rub(max)}`
      : amt.mode === "rub" ? `≈ ${days(daysFor(n))} VPN` : rub(n);
    const u = el.querySelector("#amUnit");
    u.textContent = amt.mode === "rub" ? "₽" : pl(amDays(), "день", "дня", "дней");
    u.classList.toggle("days", amt.mode !== "rub");
    el.querySelector(".am-hint").textContent = amt.mode === "rub" ? "Наберите сумму" : "Наберите количество дней";
    const p = el.querySelector("#amPay");
    p.classList.toggle("off", !ok || !curMethod());
    p.querySelector("span").textContent = !curMethod() ? "Оплата недоступна" : ok ? `Оплатить ${rub(n)}` : "Введите сумму";
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
    if (amN() > (Number(me.topup_max) || 100000)) amtShake();
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
    const r = b.getBoundingClientRect();
    amRing(r.left + r.width / 2, r.top + r.height / 2);
    amt.v = String(Math.min(Number(me.topup_max) || 100000, amN() + Number(b.dataset.v)));
    amt.mode = "rub";
    cur.el.querySelector("#am").classList.add("open");
    amRoll();
  }
  function amSwap(b) {
    if (!amN() || amt.rolling) return;
    haptic("medium");
    const r = b.getBoundingClientRect();
    amRing(r.left + r.width / 2, r.top + r.height / 2);
    amt.mode = amt.mode === "rub" ? "days" : "rub";
    if (amt.mode === "days") { const d = daysFor(amN()); amt.d = d ? String(d) : ""; }
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
    const r = ico.getBoundingClientRect();
    amRing(r.left + r.width / 2, r.top + r.height / 2);
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
      return hc(L.c, { ill: L.ill(64), h: "Чем оплатить?", p: `${rub(pay.amount)} на баланс · без автоплатежей` }) +
        ST("Способы") + cd(payMethods().map((m) => [E(METHOD_EMO[m.id] || "💳") + TT(esc(m.title), esc(methodSub(m))) + V(RD(m.id === pay.method)), `data-act="meth" data-v="${esc(m.id)}"`])) +
        `<div class="bot"><button type="button" class="bbtn" data-act="back">Готово</button></div>`;
    },
    bot: true,
  };

  // ---------- waiting for the money ----------
  SCR.wait = {
    h() {
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
    countTo(N.firstChild, 0, delta, " ₽", "+");
    h.querySelector(".P").textContent = "Баланс: " + rub(me.balance_rub);
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
        return hc("teal", { ill: other ? "📋" : appIcon(own, 92), h: other ? "Своё приложение" : `${esc(own.name)} уже стоит`,
          p: other ? "Создадим ключ — вы вставите его в своё приложение" : `Создадим ключ и добавим его в ${esc(own.name)}`,
          x: '<div class="dots"><i class="on"></i><i class="on"></i><i></i></div>',
          pill: "Создать ключ", pa: 'data-act="create" id="wizOk"' }) +
          ST("Как это работает") +
          tl([["1", "Нажмите «Создать ключ»", "<b>отдельный ключ</b> для этого устройства"],
            ["2", other ? "Скопируйте ключ и вставьте в приложение" : `Подтвердите добавление в ${esc(own.name)}`, other ? "обычно «+» → «Импорт из буфера»" : "кнопка откроет приложение"],
            ["3", "Включите VPN", `${dayPrice()} ₽ в день, пока пользуетесь`]]) +
          cd([[E("🔄") + "Выбрать другое приложение" + V(CV), 'data-act="hasyes"']]);
      }
      if (!list.some((a) => a.id === wiz.client)) wiz.client = prefApp(wiz.platform);
      const a = appById(wiz.client);
      if (!a) {
        return hc("teal", { ill: PLAT_EMO[wiz.platform] || "📱", h: "Пока нет инструкции", p: `Для ${esc(platTitle(wiz.platform))} напишите в поддержку — поможем`,
          pill: "Написать в поддержку", pa: 'data-act="support"' });
      }
      const dl = (a.stores || {})[wiz.platform];
      return hc("teal", { ill: appIcon(a, 92), h: `Установите ${esc(a.name)}`, p: `Бесплатно в ${storeName(wiz.platform)}. Уже стоит — жмите ✓`,
        x: '<div class="dots"><i class="on"></i><i class="on"></i><i></i></div>',
        pill: dl ? "Скачать" : "Готово, установлено", pa: dl ? 'data-act="store"' : 'data-act="create"', r: "chk", rl: "Приложение установлено", ra: 'data-act="create" id="wizOk"' }) +
        guideRow(a) + appMore(list, a) +
        ST("Как это работает") +
        tl([["1", `Установите ${esc(a.name)}`, "займёт полминуты"], ["2", "Вернитесь сюда и нажмите ✓", "<b>создадим ключ</b> для этого устройства"],
          ["3", "Подключите в один тап", `${dayPrice()} ₽ в день, пока пользуетесь`]]) +
        cd([[E(PLAT_EMO[wiz.platform] || "📱") + esc(platTitle(wiz.platform)) + V("Другое устройство " + CV), 'data-act="replat"']]);
    },
    on() {
      track("wizard_2");
      // «Можно выбрать другое приложение» shows once per user, under the apps row.
      if (cur && cur.el.querySelector(".atip")) store.set("alt_tip", 1);
    },
  };
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
  const nameKey = (t) => String(t || "").trim().toLowerCase();
  function dupeGroup() {
    const by = {};
    phones().forEach((d) => { (by[nameKey(d.title)] = by[nameKey(d.title)] || []).push(d); });
    const g = Object.values(by).find((x) => x.length > 1);
    if (!g) return null;
    const key = g.map((d) => d.id).join(",") + ":" + nameKey(g[0].title);
    return store.get("dupe_off") === key ? null : g;
  }
  function dupeCard(g) {
    const n = g.length, word = n === 2 ? "Два" : n === 3 ? "Три" : n === 4 ? "Четыре" : String(n);
    return `<div class="nudge"><span class="ne">🤔</span><span class="nt"><b>${word} «${esc(g[0].title || "Устройство")}»</b>` +
      `<span>Подпишите, чтобы не путать</span></span><button type="button" class="nb" data-act="dupes">Подписать</button>` +
      `<button type="button" class="nx" data-act="dupesx" aria-label="Скрыть">✕</button></div>`;
  }
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
        if (multi) store.set("dupe_off", "");
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
      return hc("teal", { rb: !d.active ? "пауза" : fresh ? "ждёт" : "онлайн", ill: devIcon(d), h: esc(d.title || "Устройство"),
        p: !d.active ? "Неактивно — пополните баланс" : fresh ? `Ключ готов — добавьте его в ${esc((a && a.name) || "приложение")} и включите VPN`
          : `Активно · ${dayPrice()} ₽ в день`,
        ...(a && a.id === "other" ? { pill: "Скопировать ключ", pa: 'data-act="devcopy"' }
          : { pill: `Открыть в ${esc((a && a.name) || "приложении")}`, pa: `data-act="devopen"`, r: "copy", rl: "Скопировать ключ", ra: 'data-act="devcopy"' }) }) +
        ST("Устройство") +
        cd([[E("✏️") + TT("Название", esc(d.title || "Устройство")) + V(CV), 'data-act="rename"'],
          a ? [`<span class="e">${appIcon(a, 26)}</span>` + TT("Приложение", a.id === "other" ? "Своё — ключ вставляется вручную" : esc(a.name)) + V("сменить " + CV), 'data-act="devapp"'] : null,
          `${E("🔑")}${TT("Ключ подписки", `<span style="font-family:ui-monospace,Menlo,monospace">${esc((d.subscription_url || "").replace(/^https?:\/\//, "").slice(0, 34))}…</span>`)}`,
          fresh ? null : [E("💡") + TT("Перестал работать VPN?", "Выпустим новый ключ, старый отключится") + V(CV), 'data-act="reissue"'],
          [E("🆘") + "Помощь с подключением" + V(CV), 'data-act="helpdevice"']]) +
        `<div style="height:12px"></div>` +
        cd([[E("🗑️") + "Удалить устройство", 'data-act="delete"', "red"]]) +
        NOTE(me.balance_enabled ? "Удалите устройство, если больше не пользуетесь, — списания за него прекратятся." : "");
    },
    sig: (p) => JSON.stringify(deviceById(p.id) || null),
  };

  // ---------- after deleting the last device ----------
  const EXIT = [["expensive", "Дорого"], ["not_working", "Не работает — нужна помощь"], ["not_needed", "Больше не нужен"], ["other", "Другое"]];
  SCR.feedback = {
    h(p) {
      return hc("slate", { ill: FROG(70, true), h: "Устройство удалено", p: "Подскажите, что нам улучшить" }) +
        ST("Почему?") + cd(EXIT.map(([v, t]) => [RD(v === p.reason) + t, `data-act="fb" data-v="${v}"`])) +
        `<div class="bot"><button type="button" class="bbtn" data-act="sendfb">Отправить</button><button type="button" class="lnk" data-act="home">Пропустить</button></div>`;
    },
    bot: true,
  };

  // ---------- friends ----------
  SCR.friends = {
    live: true,
    h() {
      const on = Boolean(me.referral_program_enabled);
      const reward = Number(me.referral_reward_rub) || 50;
      const terms = me.referral_terms && typeof me.referral_terms === "object" ? me.referral_terms : {};
      const friends = Array.isArray(me.referrals) ? me.referrals : [];
      const invited = Number(me.invited_count) || 0, earned = Number(me.referral_earned) || 0;
      const hero = hc("indigo", { ill: "🎁", h: on ? `Пригласите друзей и получайте по ${rub(reward)}` : "Пригласите друзей",
        p: on ? "Как только друг откроет бота по вашей ссылке, вы оба получите бонус на баланс" : "Пользоваться вместе приятнее. Сейчас новые награды не начисляются",
        pill: "Поделиться", pi: "share", pa: 'data-act="share"', r: "copy", rl: "Скопировать", ra: 'data-act="copyinvite"', cls: "ref" });
      const how = on ? ST("Как это работает") + tl([["1", "Друг открывает бота по ссылке", esc(terms.friend || "и получает подарок")],
        ["2", "Начинает пользоваться VPN", esc(terms.when || "")], ["🎁", `Вам ${rub(reward)} на баланс`, earned ? `<b>+${rub(earned)}</b> уже получено` : esc(terms.how || "")]]) : "";
      const stats = ST("Ваши друзья") + cd([E("👥") + "Приглашено" + V(String(invited)), E("💰") + "Получено" + V(rub(earned))]);
      const list = friends.length ? cd(friends.map((f) => E(f.paid ? "✅" : "⏳") + TT(esc(f.name || "друг") + (f.username ? ` · @${esc(f.username)}` : ""), f.paid ? "есть оплата" : "ещё без оплаты"))) : "";
      return hero + how + stats + list + (terms.note ? NOTE(esc(terms.note)) : "");
    },
    sig: () => JSON.stringify([me.invited_count, me.referral_earned, me.referrals, me.referral_program_enabled]),
  };

  // ---------- history ----------
  const BILL = { charge: "VPN", pause: "Пауза тарификации", disable: "Отключение", revive: "Включение", trial: "Подарок", admin_balance: "Баланс",
    admin_grant: "Начисление", trust: "Обещанный платёж", trust_collect: "Возврат обещанного", device_delete: "Удаление устройства", referral: "Бонус за друга",
    referral_payout: "Реферальная награда", referral_revoke: "Возврат за друга", story: "Награда за историю", topup: "Пополнение", router: "Роутер", promo: "Промокод" };
  SCR.history = {
    h(p) {
      const data = p.data;
      if (!data) {
        return hc("slate", { cls: "shim", ill: "🧾", h: "История", p: "Загружаю…" }) + `<div class="cd" style="height:150px"></div>`;
      }
      if (data.error) return hc("slate", { ill: "🧾", h: "История", p: esc(data.error), pill: "Повторить", pa: 'data-act="rehistory"' });
      const items = data.items || [];
      const charged = Math.abs(Number(data.charged_rub) || 0);
      const now = new Date(), byDay = [];
      for (let i = 6; i >= 0; i--) {
        const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - i);
        byDay.push({ key: d.toDateString(), sum: 0 });
      }
      items.forEach((e) => {
        const d = parseDate(e.created_at), v = Number(e.amount);
        if (!d || !(v < 0)) return;
        const slot = byDay.find((x) => x.key === d.toDateString());
        if (slot) slot.sum += -v;
      });
      const max = Math.max(1, ...byDay.map((x) => x.sum));
      const bars = `<div class="bars">${byDay.map((x, i) => `<i class="${i === 6 ? "on" : ""}" style="height:${Math.max(6, Math.round((x.sum / max) * 100))}%;animation-delay:${0.2 + i * 0.06}s"></i>`).join("")}</div>`;
      const hero = hc("slate", { n: charged ? cnt(charged, " ₽", "−") : "0 ₽", p: items.length ? `списано за 7 дней · ${items.length} ${pl(items.length, "операция", "операции", "операций")}` : "Пока не было списаний и начислений", x: bars });
      if (!items.length) return hero + NOTE("Здесь появятся списания и пополнения баланса.", true);
      const groups = [];
      items.forEach((e) => {
        const d = parseDate(e.created_at);
        const label = d ? dayLabel(d) : "Ранее";
        let g = groups[groups.length - 1];
        if (!g || g.label !== label) { g = { label, rows: [] }; groups.push(g); }
        const v = Number(e.amount);
        const sub = [e.device_title, e.note, d ? timeHM(d) : ""].filter(Boolean).map(esc).join(" · ");
        const amt = Number.isFinite(v) && v ? `<span class="${v > 0 ? "pos" : "neg"}">${v > 0 ? "+" : "−"}${rub(Math.abs(v))}</span>` : "";
        g.rows.push(TT(esc(BILL[e.kind] || "Операция"), sub) + V(amt));
      });
      return hero + groups.map((g) => ST(g.label) + cd(g.rows)).join("");
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
      const hero = hc("green", { cls: "compact", rb: status, ill: FROG(64), h: "Поддержка", p: t ? `Обращение №${t.id} · ответ придёт сюда и в бот` : "Напишите нам — ответ придёт сюда и в бот" });
      let chat = "";
      const msgs = (t && t.messages) || [];
      if (!p.loaded) chat = `<div class="empty"><span class="typing"><span></span><span></span><span></span></span></div>`;
      else if (!msgs.length) {
        chat = `<div class="empty">${support.context ? "Опишите, что не получилось. Устройство, приложение и этап настройки приложим сами." :
          t && t.status === "closed" ? "Нужна помощь? Напишите — откроем новое обращение." : "Что случилось? Опишите проблему — поможем разобраться."}</div>`;
      } else {
        let last = "";
        msgs.forEach((m) => {
          const d = parseDate(m.created_at);
          if (d && dayLabel(d) !== last) { last = dayLabel(d); chat += `<div class="day">${last}</div>`; }
          const op = m.author === "admin";
          const atts = (m.attachments || []).map((a) => ((a.kind === "photo" || String(a.mime || "").startsWith("image/")) && a.url
            ? `<a href="${esc(a.url)}" target="_blank" rel="noopener"><img src="${esc(a.url)}" alt="${esc(a.original_name || "Фото")}"></a>`
            : `<a class="file" href="${esc(a.url || "#")}" target="_blank" rel="noopener">${esc(a.original_name || "Файл")}</a>`)).join("");
          chat += `<div class="bub ${op ? "op" : "me"}">${op ? '<span class="who">Поддержка</span>' : ""}${esc(m.body || "")}${atts}${d ? `<i>${timeHM(d)}</i>` : ""}</div>`;
        });
      }
      let actions = "";
      if (t && t.status !== "closed" && msgs.length) actions = `<button type="button" class="lnk" data-act="tclose">Вопрос решён</button>`;
      if (t && t.status === "closed") {
        actions = t.support_rating ? NOTE(`Спасибо! Ваша оценка: ${t.support_rating} из 5`, true)
          : NOTE("Как вам помощь?", true) + `<div class="rate">${[1, 2, 3, 4, 5].map((r) => `<button type="button" data-act="trate" data-v="${r}">${r} ★</button>`).join("")}</div>`;
      }
      const files = support.files.map((f, i) => `<button type="button" data-act="unfile" data-v="${i}">📎 ${esc(f.name)} ✕</button>`).join("");
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
      support.poll = setInterval(() => { if (cur && cur.key === "support") loadTickets(true); else clearInterval(support.poll); }, 8000);
    },
  };
  function scrollChat() { requestAnimationFrame(() => window.scrollTo(0, document.body.scrollHeight)); }
  async function loadTickets(silent) {
    try {
      const data = await api("/api/tickets");
      if (!cur || cur.key !== "support") return;
      const before = JSON.stringify(cur.params.ticket || null);
      cur.params.ticket = data.current || null;
      const changed = !cur.params.loaded || before !== JSON.stringify(cur.params.ticket);
      cur.params.loaded = true;
      if (changed) { rerender(false); scrollChat(); }
    } catch (e) {
      if (!silent) showErr(e);
      if (cur && cur.key === "support" && !cur.params.loaded) { cur.params.loaded = true; rerender(false); }
    }
  }

  // ---------- faq ----------
  SCR.faq = {
    h() {
      const items = (me.faq || []).filter((x) => x && x.q);
      return hc("orange", { ill: "💡", h: "Частые вопросы", p: "Подключение, оплата и деньги", pill: "Написать в поддержку", pa: 'data-act="support"', r: "msg", rl: "Поддержка", ra: 'data-act="support"' }) +
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
      return hc("slate", { ill: photo, h: esc(u.name || "Профиль"), p: esc(u.username || `ID ${u.id || ""}`), pill: "Скопировать ID", pa: 'data-act="copyid"', r: "msg", rl: "Поддержка", ra: 'data-act="support"' }) +
        (me.notification_settings_available ? ST("Уведомления") + cd([["Режим тишины" + `<span class="tg ${quiet ? "" : "off"}"></span>`, 'data-act="quiet"']]) +
          NOTE("Без приглашений, акций и напоминаний. Сообщения о деньгах, доступе и ответы поддержки останутся.") : "") +
        ST("Ещё") +
        cd([me.promo_enabled ? [E("🎟️") + "Промокод" + V(CV), 'data-go="promo"'] : null,
          [E("💡") + "Частые вопросы" + V(CV), 'data-go="faq"'],
          [E("🧾") + "История" + V(CV), 'data-go="history"'],
          me.legal && me.legal.offer ? [E("📄") + "Пользовательское соглашение" + V(CV), `data-act="link" data-v="${esc(me.legal.offer)}"`] : null,
          me.legal && me.legal.privacy ? [E("🔒") + "Политика конфиденциальности" + V(CV), `data-act="link" data-v="${esc(me.legal.privacy)}"`] : null]);
    },
    sig: () => JSON.stringify([me.user, me.quiet_notifications, me.notification_settings_available, me.promo_enabled]),
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
  SCR.login = {
    bare: true,
    h(p) {
      return hc("blue", { cls: p.waiting ? "shim" : "", ill: FROG(78), h: "Вход в кабинет", p: esc(p.msg || "Введите ваш логин Telegram"),
        x: `<div class="inp"><input id="loginUser" autocomplete="username" autocapitalize="off" placeholder="@username"${p.waiting ? " disabled" : ""}></div>`,
        pill: p.waiting ? "Ждём подтверждения…" : "Войти", pd: p.waiting, pa: 'data-act="login"' }) +
        NOTE("Пришлём запрос на вход в чат с ботом — подтвердите его там.", true);
    },
    on(el) {
      const i = el.querySelector("#loginUser");
      if (!i.disabled) setTimeout(() => i.focus(), 60);
      i.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); ACT.login(); } });
    },
  };

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
    if (cur && cur.key === "feedback") { go("home", {}, "x"); return; }
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
    const show = Boolean(cur && cur.key !== "home" && !SCR[cur.key].bare);
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
    if (p) { wiz.platform = p; wiz.client = prefApp(p); wiz.has = wiz.client === "other"; go("wiz2"); }
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
  async function createDevice(btn) {
    if (creating) return;
    creating = true;
    if (btn) btn.classList.add("dim");
    try {
      const names = { ios: "Мой iPhone", android: "Мой Android", macos: "MacBook", windows: "Ноутбук", androidtv: "Телевизор", appletv: "Apple TV" };
      const title = names[wiz.platform] || "Моё устройство";
      const made = await post("/api/devices", { title, platform: wiz.platform, client: wiz.client });
      if (wiz.client) store.set("app_" + wiz.platform, wiz.client);
      Object.assign(wiz, { title, url: made.subscription_url || "", deviceId: made.device_id });
      if (made.first_device) thanksArmed = true;
      store.set("onboard", 1);
      await load(true).catch(() => {});
      notify("success");
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
    back,
    home,
    refresh(b) {
      b.classList.remove("spin"); void b.offsetWidth; b.classList.add("spin");
      haptic();
      load(true).then(() => { if (cur && cur.key === "wait") checkPaid(cur.el); else toast(`Обновлено в ${timeHM(new Date())}`); }).catch(showErr);
    },
    wizard: () => startWizard(),
    resume,
    support: () => openSupport(),
    helpconnect: () => openSupport(connectContext()),
    helpdevice: () => openSupport(connectContext(deviceById(cur.params.id))),
    device: (b) => { haptic(); go("device", { id: b.dataset.id }); },
    link: (b) => tg.openLink(b.dataset.v),
    async vfb(b) {
      const value = b.dataset.v;
      try {
        const res = await post("/api/vpn-feedback", { value });
        me.vpn_feedback = value;
        if (value === "help") openSupport();
        else if (value === "terms") { toast("Напишите, что не подошло — учтём"); openSupport(); }
        else if (res.access_active === false) go("topup");
        else { toast("Отлично! Пользуйтесь на здоровье 💚"); rerender(); }
      } catch (e) { showErr(e); }
    },
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
    amt(b) {
      haptic();
      const old = pay.amount;
      pay.amount = Number(b.dataset.v);
      pay.custom = false;
      cur.el.querySelectorAll(".chp button").forEach((c) => c.classList.toggle("on", c === b));
      cur.el.querySelector("#amtI").hidden = true;
      paintAmount(cur.el, old);
    },
    amtc() { haptic(); amt.v = pay.custom && amountOk(pay.amount) ? String(pay.amount) : ""; amt.mode = "rub"; amt.d = ""; go("amount"); },
    amtk(b) { amtPress(b.dataset.v); },
    amtq(b) { amtQuick(b); },
    amtsw(b) { amSwap(b); },
    amtico() { amCycle(); },
    amtpay(b) {
      const n = Number(amt.v) || 0;
      if (!amountOk(n)) return amtShake();
      pay.amount = n; pay.custom = true;
      startPay(b);
    },
    pay: (b) => startPay(b),
    meth(b) {
      haptic();
      pay.method = b.dataset.v;
      cur.el.querySelectorAll(".rd").forEach((r) => r.classList.toggle("on", r.closest("[data-v]").dataset.v === pay.method));
      // The widget on top changes to the chosen method's look.
      const h = cur.el.querySelector(".hc"), L = look(curMethod());
      Object.values(LOOK).forEach((x) => h.classList.remove(x.c));
      h.classList.add(L.c);
      const ill = h.querySelector(".ill");
      const fresh = ill.cloneNode(false);
      fresh.innerHTML = `<div>${L.ill(64)}</div>`;
      ill.replaceWith(fresh);
    },
    reopen: () => pay.url && tg.openLink(pay.url),
    plat(b) { haptic(); wiz.platform = b.dataset.v; wiz.client = prefApp(wiz.platform); wiz.has = wiz.client === "other"; go("wiz2"); },
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
        const g = el.querySelector(".gde"), ng = tmp.querySelector(".gde");
        if (ng) ng.classList.add("still");
        if (g && ng) swap(g, ng); else if (g) g.remove(); else if (ng) { const w = el.querySelector(".altw"); if (w) w.before(ng); }
        swap(el.querySelector(".alt"), tmp.querySelector(".alt"), true);
        const tl = el.querySelector(".tl"), ntl = tmp.querySelector(".tl");
        swap(tl && tl.parentNode, ntl && ntl.parentNode, true);
      }, alt ? 280 : 0);
    },
    store() {
      const a = appById(wiz.client);
      const url = a && (a.stores || {})[wiz.platform];
      if (url) { haptic(); tg.openLink(url); }
    },
    create: () => createDevice(cur.el.querySelector("#wizOk")),
    connect: () => openClient(wiz.client, wiz.url),
    copykey: () => copy(wiz.url, "Ключ скопирован"),
    devopen() {
      const d = deviceById(cur.params.id);
      if (d) openClient((devApp(d) || {}).id, d.subscription_url);
    },
    devapp() { const d = deviceById(cur.params.id); if (d) { haptic(); appSheet(d); } },
    devcopy() { const d = deviceById(cur.params.id); if (d) copy(d.subscription_url, "Ключ скопирован"); },
    rename() { const d = deviceById(cur.params.id); if (d) { haptic(); nameSheet([d]); } },
    dupes() { const g = dupeGroup(); if (g) { haptic(); nameSheet(g); } },
    dupesx() {
      const g = dupeGroup();
      if (!g) return;
      store.set("dupe_off", g.map((d) => d.id).join(",") + ":" + nameKey(g[0].title));
      rerender();
    },
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
        const res = await api(`/api/devices/${d.id}`, { method: "DELETE" });
        store.set("onboard", 1);
        await load(true).catch(() => {});
        toast("Устройство удалено");
        if (res.exit_feedback_token && !(me.devices || []).length) { stack = []; go("feedback", { token: res.exit_feedback_token, reason: "" }, "f"); stack = []; syncBack(); }
        else home();
      } catch (e) { showErr(e); }
    },
    fb(b) {
      haptic();
      cur.params.reason = b.dataset.v;
      cur.el.querySelectorAll(".rd").forEach((r) => r.classList.toggle("on", r.closest("[data-v]").dataset.v === cur.params.reason));
    },
    async sendfb(b) {
      const { token, reason } = cur.params;
      if (!reason) { toast("Выберите ответ или нажмите «Пропустить»"); return; }
      b.disabled = true;
      try { await post("/api/exit-feedback", { token, reason }); } catch (_e) { /* the answer is optional */ }
      if (reason === "not_working") {
        stack = [];
        openSupport({ prefill: "Не удалось подключить VPN. Удалил последнее устройство. Нужна помощь с настройкой." });
        stack = [{ key: "home", params: {} }];
        syncBack();
        return;
      }
      toast(reason === "not_needed" ? "Спасибо. Напоминания приостановлены до нового подключения" : "Спасибо! Мы прочитаем 💚");
      setTimeout(home, 700);
    },
    share: () => shareInvite(false),
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
      go("login", { waiting: true, msg: "Входим…" }, "x");
      try {
        const res = await fetch("/api/cabinet-login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username }) });
        const data = await res.json().catch(() => ({}));
        if (data && data.token) { saveToken(data.token); go("boot", {}, "x"); await load(); return; }
        if (data && data.wait) { await waitLogin(data.wait, username); return; }
        decoy(username);
      } catch (_e) { decoy(username); }
    },
  };

  let loginSeq = 0;
  async function waitLogin(id, username) {
    const seq = ++loginSeq;
    go("login", { waiting: true, msg: "Подтвердите вход в Telegram — мы прислали запрос в чат с ботом" }, "x");
    const started = Date.now();
    while (seq === loginSeq && Date.now() - started < 600000) {
      await new Promise((r) => setTimeout(r, 1400));
      if (seq !== loginSeq) return;
      try {
        const data = await (await fetch("/api/cabinet-login/status?id=" + encodeURIComponent(id))).json();
        if (data && data.token) { saveToken(data.token); go("boot", {}, "x"); await load(); return; }
        if (data && data.status === "declined") { decoy(username); return; }
        if (data && data.status === "expired") break;
      } catch (_e) { /* keep waiting */ }
    }
    if (seq === loginSeq) go("login", { msg: "Время подтверждения истекло. Попробуйте ещё раз." }, "x");
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
    if (a.dataset.go) { haptic(); go(a.dataset.go); return; }
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
    if (entry === "topup") { go("topup"); return; }
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
    if (["home", "device", "wiz3", "promise"].includes(cur.key)) load(true).catch(() => {});
  }, 15000);

  window.__cab = { go, back, get me() { return me; }, get cur() { return cur; }, load, toast, boom };
  go("boot", {}, "x");
  load().catch(failed);
})();
