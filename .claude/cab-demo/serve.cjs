// Local preview of the cabinet (webapp/) with a fake /api/me, to look at screens without Telegram or the bot.
const http = require("http"), fs = require("fs"), path = require("path");
const WEB = path.resolve(__dirname, "../../webapp");
const types = { ".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript", ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml", ".json": "application/json", ".mp4": "video/mp4" };
const apple = ["ios", "macos", "appletv"], droid = ["android", "androidtv"];
const store = (plats, url) => Object.fromEntries(plats.map((p) => [p, url]));
const apps = [
  { id: "incy", name: "Incy", mark: "IN", icon: "/icons/incy.png", deep_link: "incy://import/{url}", guide: "https://telegra.ph/Kak-ustanovit-Incy", platforms: apple, stores: store(apple, "https://apps.apple.com/search?term=Incy") },
  { id: "happ", name: "Happ", mark: "H", icon: "/icons/happ.png", deep_link: "happ://add/{url}", guide: "https://telegra.ph/Kak-ustanovit-Happ", platforms: [...apple, ...droid, "windows"], stores: store([...apple, ...droid, "windows"], "https://www.happ.su"), direct: { android: "https://github.com/Happ-proxy/happ-android/releases/latest/download/Happ.apk" } },
  { id: "rabbithole", name: "RabbitHole", mark: "RH", icon: "/icons/rabbithole.png", deep_link: "rabbithole://add/{url}", platforms: apple, stores: store(apple, "https://apps.apple.com/app/id6683309629") },
  { id: "streisand", name: "Streisand", mark: "S", icon: "", deep_link: "", platforms: apple, stores: store(apple, "https://apps.apple.com/search?term=Streisand") },
  { id: "v2raytun", name: "v2RayTun", mark: "VT", icon: "", deep_link: "v2raytun://import/{url}", platforms: [...apple, ...droid], stores: store([...apple, ...droid], "https://v2raytun.com") },
  { id: "karing", name: "Karing", mark: "KA", icon: "/icons/karing.png", deep_link: "karing://install-config?url={enc}", platforms: [...apple, ...droid, "windows"], stores: { ios: "https://apps.apple.com/app/id6472431552", appletv: "https://apps.apple.com/app/id6472431552", macos: "https://github.com/KaringX/karing/releases/latest", android: "https://github.com/KaringX/karing/releases/latest", androidtv: "https://github.com/KaringX/karing/releases/latest", windows: "https://github.com/KaringX/karing/releases/latest" } },
  { id: "v2rayng", name: "v2rayNG", mark: "v2", icon: "/icons/v2rayng.png", deep_link: "v2rayng://install-sub?url={enc}", platforms: droid, stores: store(droid, "https://play.google.com/store/apps/details?id=com.v2ray.ang") },
  { id: "hiddify", name: "Hiddify", mark: "HD", icon: "", deep_link: "hiddify://import/{url}", platforms: droid, stores: store(droid, "https://play.google.com/store/apps/details?id=app.hiddify.com") },
];
const me = { ok: true, user: { id: 7, name: "Демо", username: "demo" }, brand_name: "Лягушка VPN", balance_rub: 120, balance_enabled: true, devices: [], vpn_apps: apps,
  vpn_day_price_rub: 6, trial_available: false, has_paid_topup: true, max_devices: 10 };
if (process.env.DEMO_DEVICE || process.env.DEMO_DEVICE === undefined) Object.assign(me, { balance_rub: 46, days_left: 7, hours_left: 170, first_online_at: "2026-11-01T10:00:00Z",
  devices: [{ id: 1, title: "Мой iPhone", icon: "", platform: "ios", app: "happ", active: true, connected: true, online_at: new Date().toISOString(), created_at: "2026-11-01T09:00:00Z" }, { id: 2, title: "Мой iPhone", icon: "", platform: "ios", app: "happ", active: true, connected: false, created_at: "2026-11-13T09:00:00Z" }],
  pay_methods: [{ id: "card", title: "Банковская карта", hint: "Visa, Mastercard, МИР" }, { id: "sbp", title: "СБП", hint: "Через приложение банка" }],
  topup_min: 50, trust: { enabled: true, available: false } });
Object.assign(me, { browser_login: false, cabinet_site_url: "https://lk.frog-vpn.ru" });
// «Подарить другу»: friends' gifts by code (?screen=present&code=OPEN1234), the giver's list in /api/gifts.
Object.assign(me, { gifts_enabled: true, gift_min: 60, gift_max: 20000, balance_rub: 5120 });
Object.assign(me, { referral_program_enabled: true, referral_reward_rub: 50, gift_season: process.env.DEMO_NY === "0" ? "" : "ny" });
const gifts = { sent: [{ code: "WAIT1234", url: "https://t.me/way_proxy_bot?start=present_WAIT1234", amount_rub: 300, count: 15, claimed_count: 8, status: "active", created_at: new Date().toISOString() },
  { code: "DONE1234", amount_rub: 180, status: "claimed", friend_name: "Оля", created_at: "2026-11-10T10:00:00Z", claimed_at: "2026-11-11T10:00:00Z" }] };
const giftView = (code) => ({ OPEN1234: { status: "active" }, NYGF1234: { status: "active", style: "tangerine", amount_rub: 500, greeting: "С Новым годом! Пусть в новом году всё открывается с первого раза 🎄" }, MINE1234: { status: "active", mine: true }, USED1234: { status: "claimed" },
  PACK1234: { status: "active", amount_rub: 300, count: 15, left: 7 }, GONE1234: { status: "claimed", amount_rub: 300, count: 15, left: 0 } })[code];
const base = JSON.parse(JSON.stringify(me));
const lk = { status: "pending", n: 0 };
let demoStyle = "violet";
http.createServer((req, res) => {
  const url = new URL(req.url, "http://x");
  const m = url.pathname.match(/^\/api\/devices\/(\d+)$/);
  if (url.pathname === "/api/devices" && req.method === "POST") {
    let b = ""; req.on("data", (c) => (b += c));
    return req.on("end", () => {
      const j = JSON.parse(b || "{}"), id = Math.max(0, ...me.devices.map((x) => x.id)) + 1;
      me.devices.push({ id, title: j.title, platform: j.platform, client: j.client || "", icon: "", active: true, connected: false, subscription_url: "https://sub.frog-vpn.ru/s/demo" + id, created_at: new Date().toISOString() });
      res.setHeader("Content-Type", "application/json");
      res.end(JSON.stringify({ ok: true, device_id: id, subscription_url: "https://sub.frog-vpn.ru/s/demo" + id }));
    });
  }
  if (m && req.method === "PATCH") {
    let b = ""; req.on("data", (c) => (b += c));
    return req.on("end", () => {
      const d = me.devices.find((x) => x.id === +m[1]), j = JSON.parse(b || "{}");
      if (j.title !== undefined) d.title = j.title; if (j.icon !== undefined) d.icon = j.icon; if (j.client !== undefined) d.client = j.client;
      res.setHeader("Content-Type", "application/json");
      res.end(JSON.stringify({ ok: true, title: d.title, icon: d.icon }));
    });
  }
  // browser login: POST /api/cabinet-login → link; /__lk?s=approved|declined plays the bot's answer
  if (url.pathname === "/__lk") { lk.status = url.searchParams.get("s") || "pending"; res.writeHead(200); return res.end(lk.status); }
  if (url.pathname === "/api/cabinet-login" && req.method === "POST") {
    let b = ""; req.on("data", (c) => (b += c));
    return req.on("end", () => {
      const j = JSON.parse(b || "{}"); lk.status = "pending"; lk.n++;
      res.setHeader("Content-Type", "application/json");
      res.end(JSON.stringify(j.via === "tg" ? { ok: true, wait: "demo" + lk.n, link: "https://t.me/way_proxy_bot?start=lk_demoABCDEFGHIJKLMNO" + lk.n } : { ok: true, wait: "demo" + lk.n }));
    });
  }
  if (url.pathname === "/api/cabinet-login/status") {
    res.setHeader("Content-Type", "application/json");
    return res.end(JSON.stringify(lk.status === "approved" ? { ok: true, status: "approved", token: "demo-token" } : { ok: true, status: lk.status }));
  }
  const gm = url.pathname.match(/^\/api\/gifts(?:\/([\w-]+)(?:\/(\w+))?)?$/);
  if (gm) {
    const send = (o, st = 200) => setTimeout(() => { res.writeHead(st, { "Content-Type": "application/json" }); res.end(JSON.stringify(o)); }, 350);
    const [, code, op] = gm;
    if (!code && req.method === "GET") return send({ ok: true, giftable_rub: 4000, sent: gifts.sent });
    if (!code) { let b = ""; req.on("data", (c) => (b += c)); return req.on("end", () => { const n = JSON.parse(b || "{}").amount; if (n * (JSON.parse(b || "{}").count || 1) > 4000) return send({ ok: false, error: "Можно подарить до 400 ₽" }, 400);
      const j = JSON.parse(b || "{}"), cnt = j.count || 1; demoStyle = j.style || "violet"; me.balance_rub -= n * cnt; send({ ok: true, count: cnt, code: "NEW12345", url: "https://t.me/way_proxy_bot?start=present_NEW12345", amount_rub: n, share_text: "🎁 Демо дарит вам " + n + " ₽", prepared_id: null, balance_rub: me.balance_rub }); }); }
    const g = giftView(code);
    if (!g) return send({ ok: false, error: "Подарок не найден" }, 404);
    if (op === "claim") { if (g.status !== "active" || g.mine) return send({ ok: false, error: "Этот подарок уже открыли" }, 400); const a = g.amount_rub || 180; me.balance_rub += a; return send({ ok: true, amount_rub: a, balance_rub: me.balance_rub, from_name: "Иван", count: g.count || 1, left: (g.left || 1) - 1 }); }
    if (op) return send({ ok: true, url: "https://t.me/x", share_text: "Подарок", amount_rub: 180, balance_rub: me.balance_rub });
    return send({ ok: true, code, amount_rub: 180, from_name: "Иван", mine: false, claimed_by_me: false, thanked: false, style: url.searchParams.get("style") || demoStyle, ...g });
  }
  // Demo payment: /api/invoice credits the amount (+ the bonus) a few seconds later.
  if (url.pathname === "/api/invoice" && req.method === "POST") {
    let b = ""; req.on("data", (c) => (b += c));
    return req.on("end", () => {
      const j = JSON.parse(b || "{}"), amount = Number(String(j.plan || "").slice(1)) || 0;
      setTimeout(() => {
        const bonus = me.first_bonus && amount >= me.first_bonus.min_rub ? Math.floor(amount * me.first_bonus.percent / 100) : 0;
        me.balance_rub += amount + bonus; me.has_paid_topup = true; me.first_bonus = null;
      }, 2500);
      res.setHeader("Content-Type", "application/json");
      res.end(JSON.stringify({ ok: true, pay_url: "https://example.com/pay" }));
    });
  }
  if (url.pathname === "/api/billing") {
    const d = (n, h) => new Date(Date.now() - n * 864e5 - (h || 0) * 36e5).toISOString();
    res.setHeader("Content-Type", "application/json");
    const items = [];
    for (let i = 0; i < 20; i++) {
      items.push({ kind: "charge", amount: -10, device_title: "iPhone", created_at: d(i, 1) });
      if (i < 4) items.push({ kind: "charge", amount: -10, device_title: "MacBook", created_at: d(i, 1) });
    }
    items.push({ kind: "referral_payout", amount: 50, note: "Аня подключила VPN", created_at: d(0, 0.5) }, { kind: "topup", amount: 300, note: "СБП", created_at: d(3, -5) },
      { kind: "topup", amount: 300, created_at: d(15) }, { kind: "first_bonus", amount: 50, created_at: d(15) });
    items.sort((x, y) => y.created_at.localeCompare(x.created_at));
    return res.end(JSON.stringify({ ok: true, charged_rub: 110, items }));
  }
  if (url.pathname === "/api/tickets") {
    const d = (m) => new Date(Date.now() - m * 6e4).toISOString();
    res.setHeader("Content-Type", "application/json");
    if (!url.searchParams.has("x") && process.env.DEMO_TICKET === "0") return res.end(JSON.stringify({ ok: true, items: [], current: null, reply_minutes: 15 }));
    return res.end(JSON.stringify({ ok: true, items: [], reply_minutes: 15, current: { id: 1842, status: "open", admin_seen_at: d(3), typing: true, messages: [
      { author: "user", body: "Не подключается на айфоне", created_at: d(6), attachments: [] },
      { author: "user", body: "Вот скриншот", created_at: d(5), attachments: [{ kind: "photo", url: "/static/stories_img.jpg", original_name: "shot.png" }] },
      { author: "admin", body: "Здравствуйте! Сейчас посмотрим", created_at: d(2), attachments: [] },
      { author: "user", body: "Спасибо", created_at: d(1), attachments: [] }] } }));
  }
  if (url.pathname.startsWith("/api/")) {
    res.writeHead(200, { "Content-Type": "application/json" });
    return res.end(JSON.stringify(url.pathname === "/api/me" ? me : { ok: true }));
  }
  // /?tg=1 pretends to be inside Telegram; &first=1 just connected; &low=1 balance for under a day.
  if (url.pathname === "/" && url.searchParams.get("tg")) {
    Object.assign(me, JSON.parse(JSON.stringify(base)));
    if (url.searchParams.get("first")) me.first_online_at = new Date(Date.now() - 3600e3).toISOString();
    if (url.searchParams.get("low")) Object.assign(me, { balance_rub: 6, days_left: 0, hours_left: 10 });
    // NFT gifts for friends: &nfn=7 counted, &nfc=2 on check, &nfw=1 the last earned one waits, &nfoff=1 the promotion is off.
    {
      const q = url.searchParams, set = JSON.parse(fs.readFileSync(path.join(__dirname, "nft-set.json"), "utf8"));
      const n = Number(q.get("nfn") || 7), c = Number(q.get("nfc") ?? 2), steps = [5, 10, 15, 25, 40];
      const rewards = steps.map((need, i) => ({ id: i + 1, need, gift: set[i], status: "given", nft_link: "https://t.me/nft/x-1" })).filter((r) => n >= r.need);
      if (q.get("nfw") && rewards.length) rewards[rewards.length - 1].status = "wait";
      const names = ["Оля", "Дима", "Аня", "Саша", "Катя", "Миша", "Лена", "Гоша", "Вика", "Тимур"];
      const friends = [...Array.from({ length: c }, (_, i) => ({ name: names[i % 10], st: "check", day: 2 + i * 2 })),
        { name: "Пользователь 8…", st: "bad", day: 7, reason: "оплатил вашей картой" }, { name: "Петя", st: "pay", day: 0 },
        ...Array.from({ length: n }, (_, i) => ({ name: names[(i + c) % 10], st: "ok", day: 7 }))];
      me.friend_nft = q.get("nfoff") ? { enabled: false, rewards } : { enabled: true, counted: n, checking: c, checking_left: c ? 3 : 0, friends, rewards,
        steps: steps.map((need, i) => { const r = rewards.find((x) => x.need === need); return { need, gift: set[i], state: r ? (r.status === "given" ? "got" : "wait") : "none", reward_id: r ? r.id : null }; }),
        period: Number(q.get("nfp") || 4), period_days: 3, next_at: new Date(Date.now() + Number(q.get("nfs") || 2.3 * 864e5) ).toISOString(), check_days: 7, online_days: 3, min_rub: 100 };
    }
    // &mac=1: the second device is a MacBook waiting for its first connection.
    if (url.searchParams.get("mac")) me.devices = me.devices.map((d) => d.id === 2 ? { ...d, title: "MacBook", platform: "macos", app: "rabbithole" } : d);
    // &ab=new|old: the install-step A/B group.
    if (url.searchParams.get("ab")) me.install_ab = url.searchParams.get("ab");
    // &new=1: a newcomer straight from /start — no devices, no money, the gift not taken yet.
    if (url.searchParams.get("new")) Object.assign(me, { has_paid_topup: false, balance_rub: 0, days_left: 0, hours_left: 0, devices: [],
      first_online_at: null, trial_available: true, trial_days: 3, friend_nft: { enabled: false, rewards: [] } });
    // &rb=1: a payer whose money ran out got «Возвращайтесь с бонусом».
    if (url.searchParams.get("rb")) Object.assign(me, { has_paid_topup: true, balance_rub: 0, days_left: 0, hours_left: 0,
      first_bonus: { min_rub: 200, percent: 20, hours_left: 150, kind: "return", until: "25 ноября" } });
    // &fb=1: a newcomer on the gift who can still get «+3 дня за первую оплату».
    if (url.searchParams.get("fb")) Object.assign(me, { has_paid_topup: false, balance_rub: 10, days_left: 1, hours_left: 38, devices: me.devices.slice(0, 1),
      first_bonus: { min_rub: 200, percent: 35, hours_left: 38 } });
    const html = fs.readFileSync(path.join(WEB, "index.html"), "utf8").replace('<link rel="stylesheet"',
      `<script>(function(){var w=(window.Telegram&&Telegram.WebApp)||{BackButton:{show(){},hide(){},onClick(){}},HapticFeedback:{impactOccurred(){},notificationOccurred(){}},ready(){},expand(){},onEvent(){}};var o=Object.create(w);Object.defineProperty(o,"initData",{value:"demo"});window.Telegram={WebApp:o};})()</script><link rel="stylesheet"`);
    const clk = url.searchParams.get("click");
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" });
    return res.end(clk ? html.replace("</body>", `<script>try{localStorage.clear()}catch(e){};setTimeout(()=>{const e=document.querySelector(${JSON.stringify(clk)});e&&e.click()},2500)</script></body>`) : html);
  }
  if (url.pathname === "/__bonus") { res.writeHead(200, { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" }); return res.end(fs.readFileSync(path.join(__dirname, "bonus.html"))); }
  const dm = url.pathname.match(/^\/__doc\/([\w-]+)$/);
  if (dm) { const f = path.resolve(__dirname, "../../docs/growth", dm[1] + ".html"); if (!fs.existsSync(f)) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" }); return res.end(fs.readFileSync(f, "utf8").replaceAll("../../webapp/", "/")); }
  if (url.pathname === "/__grow") { res.writeHead(200, { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" }); return res.end(fs.readFileSync(path.join(__dirname, "grow.html"))); }
  if (url.pathname === "/__cards") { res.writeHead(200, { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" }); return res.end(fs.readFileSync(path.join(__dirname, "cards.html"))); }
  if (url.pathname === "/__card") { res.writeHead(200, { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" }); return res.end(fs.readFileSync(path.join(__dirname, "card.html"))); }
  if (url.pathname === "/__style") { res.writeHead(200, { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" }); return res.end(fs.readFileSync(path.join(__dirname, "style.html"))); }
  if (url.pathname === "/__gifts") { res.writeHead(200, { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" }); return res.end(fs.readFileSync(path.join(__dirname, "gifts.html"))); }
  if (url.pathname === "/api/browser-link") { res.writeHead(200, { "Content-Type": "application/json" }); return res.end(JSON.stringify({ ok: true })); }
  const rel = url.pathname === "/" ? "index.html" : url.pathname.replace(/^\/static\//, "").replace(/^\//, "");
  const file = path.join(WEB, decodeURIComponent(rel));
  if (!file.startsWith(WEB) || !fs.existsSync(file) || !fs.statSync(file).isFile()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "Content-Type": types[path.extname(file)] || "application/octet-stream", "Cache-Control": "no-store" });
  fs.createReadStream(file).pipe(res);
}).listen(Number(process.env.PORT) || 8790, "127.0.0.1");
