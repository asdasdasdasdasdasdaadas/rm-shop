const $ = (id) => document.getElementById(id);
let userPage = 1;
let orderPage = 1;
let refPage = 1;
let payPage = 1;
let billPage = 1;
let currentUser = null;
let selectedUsers = new Set();
let lastUserItems = [];
const TABS = ["overview", "users", "referrals", "ads", "orders", "billing", "tickets", "messages", "broadcast", "promo", "backups", "settings"];
const TAB_KEYS = {
  overview: ["dash", "fp", "fs", "fl", "fi", "step"],
  users: ["q", "status", "trial", "devices", "online", "bal_sign", "bal_min", "bal_max", "from", "to", "paid"],
  referrals: ["q", "reward", "from", "to"],
  orders: ["q", "status", "from", "to"],
  billing: ["q", "kind", "source", "from", "to"],
  tickets: ["q", "status", "from", "to"],
  messages: ["q", "channel", "source", "kind", "from", "to"],
};
const MSG_KIND_LABEL = {
  broadcast: "Рассылка",
  admin_dm: "Сообщение из админки",
  nudge_trial: "Напоминание: триал",
  nudge_invite: "Напоминание: друзья",
  nudge_info: "Напоминание: кабинет",
  nudge_story: "Напоминание: история",
  nudge_device: "Напоминание: устройство",
  nudge_first_online: "Напоминание: после онлайна",
  nudge_trial_end: "Напоминание: сутки до отключения",
  welcome_intro: "Первый запуск",
  first_device_thanks: "После первого устройства",
  cabinet_link: "Ссылка на кабинет",
  low_balance: "Мало баланса",
  maintenance_hit: "Обращение при техработах",
  maintenance_out: "Ответ техработ",
};
const MSG_STATUS_LABEL = { sent: "ушло", failed: "ошибка", hit: "обращение" };
const MSG_SOURCE_LABEL = { auto: "авто", manual: "вручную" };
const MSG_CHANNEL_LABEL = { announce: "объявления", maint: "техработы" };
const MSG_FILTER_IDS = {
  q: "msgQ",
  channel: "msgChannel",
  source: "msgSource",
  kind: "msgKind",
  from: "msgFrom",
  to: "msgTo",
};
const TICKET_STATUS_LABEL = { open: "ждёт ответа", pending: "есть ответ", closed: "закрыт" };
const TICKET_FILTER_IDS = { q: "ticketQ", status: "ticketStatus", from: "ticketFrom", to: "ticketTo" };
let toastTimer = 0;
let pageLimit = Number(localStorage.getItem("way-admin-limit") || 25);
if (![25, 50, 100].includes(pageLimit)) pageLimit = 25;
let skipHashWrite = false;

function toast(msg) {
  const el = $("toast");
  if (!el || !msg) return;
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 2800);
}

function debounce(fn, ms) {
  let t = 0;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

function emptyRow(cols, text) {
  const tr = document.createElement("tr");
  const td = document.createElement("td");
  td.colSpan = cols;
  td.className = "muted empty-cell";
  td.textContent = text;
  tr.appendChild(td);
  return tr;
}

function closeModal() {
  $("modal").classList.add("hidden");
}

function setModalPane(name) {
  document.querySelectorAll("#modalTabs [data-pane]").forEach((b) => {
    b.classList.toggle("active", b.dataset.pane === name);
  });
  ["act", "dev", "bill"].forEach((pane) => {
    const el = $("pane-" + pane);
    if (el) el.classList.toggle("hidden", pane !== name);
  });
}

function confirmAction(title, body, danger) {
  return new Promise((resolve) => {
    const dlg = $("confirmDlg");
    if (!dlg) {
      resolve(window.confirm(body || title));
      return;
    }
    $("confirmTitle").textContent = title || "Подтверждение";
    $("confirmBody").textContent = body || "";
    $("confirmOk").className = danger === false ? "" : "danger";
    dlg.classList.remove("hidden");
    const done = (ok) => {
      dlg.classList.add("hidden");
      $("confirmOk").onclick = null;
      $("confirmCancel").onclick = null;
      resolve(ok);
    };
    $("confirmOk").onclick = () => done(true);
    $("confirmCancel").onclick = () => done(false);
  });
}

function parseRoute() {
  const raw = (location.hash || "#overview").replace(/^#/, "");
  const i = raw.indexOf("?");
  const tab = ((i >= 0 ? raw.slice(0, i) : raw) || "overview").trim();
  const params = new URLSearchParams(i >= 0 ? raw.slice(i + 1) : "");
  return { tab: TABS.includes(tab) ? tab : "overview", params };
}

function writeRoute(tab, params) {
  const keys = TAB_KEYS[tab] || [];
  const next = new URLSearchParams();
  keys.forEach((k) => {
    const v = params.get(k);
    if (v) next.set(k, v);
  });
  const qs = next.toString();
  const hash = "#" + tab + (qs ? "?" + qs : "");
  if (location.hash !== hash) {
    skipHashWrite = true;
    history.replaceState(null, "", hash);
    skipHashWrite = false;
  }
}

function tabFromHash() {
  return parseRoute().tab;
}

function applyTheme(t) {
  const theme = t === "light" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("way-admin-theme", theme);
  document.querySelectorAll(".theme-icon-sun").forEach((el) => el.classList.toggle("hidden", theme === "light"));
  document.querySelectorAll(".theme-icon-moon").forEach((el) => el.classList.toggle("hidden", theme !== "light"));
}

function toggleTheme() {
  applyTheme(document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light");
}

function setSidebarCollapsed(on) {
  document.documentElement.classList.toggle("sidebar-collapsed", on);
  localStorage.setItem("way-admin-sidebar", on ? "1" : "0");
  const btn = $("sidebarCollapse");
  if (btn) btn.textContent = on ? "Меню" : "Свернуть";
}

function syncSidebarDefault() {
  if (localStorage.getItem("way-admin-sidebar") != null) return;
  const w = window.innerWidth;
  if (w >= 768 && w < 1024) document.documentElement.classList.add("sidebar-collapsed");
}

function labelRow(tr, labels) {
  [...tr.children].forEach((td, i) => {
    if (labels[i]) td.setAttribute("data-label", labels[i]);
  });
}

function paintChips(boxId, items, onClear) {
  const box = $(boxId);
  if (!box) return;
  box.innerHTML = "";
  items.forEach(([key, label]) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "filter-chip";
    b.textContent = label + " x";
    b.onclick = () => onClear(key);
    box.appendChild(b);
  });
}

function val(id) {
  const el = $(id);
  return el ? String(el.value || "").trim() : "";
}

function setVal(id, v) {
  const el = $(id);
  if (el) el.value = v || "";
}

function collectUserFilters() {
  return {
    q: val("userQ"),
    status: val("userStatus"),
    trial: val("userTrial"),
    devices: val("userDevices"),
    online: val("userOnline"),
    bal_sign: val("userBalSign"),
    bal_min: val("userBalMin"),
    bal_max: val("userBalMax"),
    from: val("userFrom"),
    to: val("userTo"),
    paid: val("userPaid"),
  };
}

const USER_FILTER_IDS = {
  q: "userQ",
  status: "userStatus",
  trial: "userTrial",
  devices: "userDevices",
  online: "userOnline",
  bal_sign: "userBalSign",
  bal_min: "userBalMin",
  bal_max: "userBalMax",
  from: "userFrom",
  to: "userTo",
  paid: "userPaid",
};

function applyUserFilters(values) {
  Object.entries(USER_FILTER_IDS).forEach(([key, id]) => setVal(id, values[key] || ""));
}

function fillFromParams(map, params) {
  Object.entries(map).forEach(([key, id]) => setVal(id, params.get(key) || ""));
}

function queryString(obj) {
  const p = new URLSearchParams();
  Object.entries(obj).forEach(([k, v]) => {
    if (v != null && String(v).trim() !== "") p.set(k, String(v).trim());
  });
  p.set("limit", String(pageLimit));
  return p.toString();
}

function hasAny(obj) {
  return Object.values(obj).some((v) => v != null && String(v).trim() !== "");
}

async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (!(opts.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(path, {
    credentials: "same-origin",
    ...opts,
    headers,
  });
  const data = await res.json().catch(() => ({ ok: false, error: "Ошибка ответа" }));
  if (!res.ok || data.ok === false) {
    const err = new Error(data.error || "Ошибка запроса");
    err.status = res.status;
    throw err;
  }
  return data;
}

function fmt(dt) {
  if (!dt) return "—";
  const d = new Date(dt);
  if (Number.isNaN(d.getTime())) return String(dt);
  return d.toLocaleString("ru-RU");
}

function fmtBytes(n) {
  if (n == null || n === "") return "—";
  const num = Number(n);
  if (!Number.isFinite(num) || num < 0) return "—";
  if (num === 0) return "0 Б";
  const units = ["Б", "КБ", "МБ", "ГБ", "ТБ"];
  let value = num;
  let i = 0;
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024;
    i += 1;
  }
  const shown = value >= 10 || i === 0 ? value.toFixed(0) : value.toFixed(1);
  return shown.replace(/\.0$/, "") + " " + units[i];
}

function trafficBytes(used, life) {
  const a = Number(used);
  const b = Number(life);
  const nums = [a, b].filter((n) => Number.isFinite(n) && n > 0);
  if (nums.length) return Math.max(...nums);
  if (Number.isFinite(a) && a >= 0) return a;
  if (Number.isFinite(b) && b >= 0) return b;
  return null;
}

function fmtTraffic(used, life) {
  return fmtBytes(trafficBytes(used, life));
}

function fmtAgo(dt) {
  if (!dt) return "—";
  const d = new Date(dt);
  if (Number.isNaN(d.getTime())) return "—";
  const sec = Math.round((Date.now() - d.getTime()) / 1000);
  if (sec < 90) return "только что";
  if (sec < 3600) return Math.floor(sec / 60) + " мин назад";
  if (sec < 86400) return Math.floor(sec / 3600) + " ч назад";
  if (sec < 86400 * 7) return Math.floor(sec / 86400) + " дн назад";
  return fmt(dt);
}

function onlineCell(dt) {
  const td = document.createElement("td");
  td.className = "who-cell";
  const ago = fmtAgo(dt);
  const abs = fmt(dt);
  td.title = abs;
  const main = document.createElement("div");
  main.textContent = ago;
  td.appendChild(main);
  if (ago !== "—" && abs !== "—") {
    const sub = document.createElement("div");
    sub.className = "who-sub";
    sub.textContent = abs;
    td.appendChild(sub);
  }
  return td;
}

function paintModalOnline(dt) {
  const el = $("modalOnline");
  if (!el) return;
  if (!dt) {
    el.textContent = "Онлайн: нет данных из панели";
    return;
  }
  el.textContent = "Онлайн: " + fmtAgo(dt) + " · " + fmt(dt);
}

function deviceBreakdownCell(u) {
  const td = document.createElement("td");
  td.className = "wrap device-break";
  const list = Array.isArray(u.devices) ? u.devices : [];
  if (!list.length) {
    td.textContent = u.remnawave_id ? "подписка" : "—";
    return td;
  }
  list.forEach((d) => {
    const row = document.createElement("div");
    row.className = "dev-break-row";
    const title = document.createElement("div");
    title.className = "dev-break-title";
    title.textContent = d.title || "Устройство";
    const meta = document.createElement("div");
    meta.className = "who-sub";
    const how = [d.client, d.platform].filter(Boolean).join(" · ") || "клиент не указан";
    const when = fmtAgo(d.last_online_at);
    const traffic = fmtTraffic(d.used_traffic_bytes, d.lifetime_traffic_bytes);
    meta.textContent = how + " · " + when + " · " + traffic;
    row.appendChild(title);
    row.appendChild(meta);
    td.appendChild(row);
  });
  const n = Number(u.device_count) || list.length;
  td.title = n + " устройств. Трафик в строке — сумма по всем.";
  return td;
}

function setNavOpen(open) {
  document.body.classList.toggle("nav-open", open);
  const toggle = $("navToggle");
  if (toggle) toggle.setAttribute("aria-expanded", open ? "true" : "false");
}

function showLogin() {
  setNavOpen(false);
  $("login").classList.remove("hidden");
  $("shell").classList.add("hidden");
  const pw = $("password");
  if (pw) pw.focus();
}

function showShell() {
  $("login").classList.add("hidden");
  $("shell").classList.remove("hidden");
}

function switchTab(name, opts = {}) {
  if (!TABS.includes(name)) name = "overview";
  const route = parseRoute();
  if (!opts.skipFill) {
    if (name === "overview") applyOverviewRoute(route.params);
    if (name === "users") {
      fillFromParams(USER_FILTER_IDS, route.tab === "users" ? route.params : new URLSearchParams());
    }
    if (name === "referrals") {
      fillFromParams(
        { q: "refQ", reward: "refReward", from: "refFrom", to: "refTo" },
        route.tab === "referrals" ? route.params : new URLSearchParams()
      );
    }
    if (name === "orders") {
      fillFromParams(
        { q: "orderQ", status: "orderStatus", from: "orderFrom", to: "orderTo" },
        route.tab === "orders" ? route.params : new URLSearchParams()
      );
    }
    if (name === "billing") {
      fillFromParams(
        { q: "billQ", kind: "billKind", source: "billSource", from: "billFrom", to: "billTo" },
        route.tab === "billing" ? route.params : new URLSearchParams()
      );
    }
    if (name === "tickets") {
      fillFromParams(TICKET_FILTER_IDS, route.tab === "tickets" ? route.params : new URLSearchParams());
    }
    if (name === "messages") {
      fillFromParams(MSG_FILTER_IDS, route.tab === "messages" ? route.params : new URLSearchParams());
    }
  }
  document.querySelectorAll("nav [data-tab], .bottom-nav [data-tab]").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === name);
    if (b.dataset.tab === name && b.dataset.title) {
      if ($("pageTitle")) $("pageTitle").textContent = b.dataset.title;
      if ($("pageLead")) $("pageLead").textContent = b.dataset.lead || "";
    }
  });
  const titleBtn = document.querySelector(`nav [data-tab="${name}"]`);
  if (titleBtn) {
    if ($("pageTitle")) $("pageTitle").textContent = titleBtn.dataset.title || name;
    if ($("pageLead")) $("pageLead").textContent = titleBtn.dataset.lead || "";
    if ($("pageCrumb")) $("pageCrumb").textContent = "Админка / " + (titleBtn.dataset.title || name);
  }
  TABS.forEach((tab) => {
    $("tab-" + tab).classList.toggle("hidden", tab !== name);
  });
  if (!opts.skipHash) {
    const params = new URLSearchParams();
    if (name === "users") Object.entries(collectUserFilters()).forEach(([k, v]) => v && params.set(k, v));
    if (name === "referrals") {
      [["q", "refQ"], ["reward", "refReward"], ["from", "refFrom"], ["to", "refTo"]].forEach(([k, id]) => {
        const v = val(id);
        if (v) params.set(k, v);
      });
    }
    if (name === "orders") {
      [["q", "orderQ"], ["status", "orderStatus"], ["from", "orderFrom"], ["to", "orderTo"]].forEach(([k, id]) => {
        const v = val(id);
        if (v) params.set(k, v);
      });
    }
    if (name === "billing") {
      [["q", "billQ"], ["kind", "billKind"], ["source", "billSource"], ["from", "billFrom"], ["to", "billTo"]].forEach(([k, id]) => {
        const v = val(id);
        if (v) params.set(k, v);
      });
    }
    if (name === "tickets") {
      Object.entries(collectTicketFilters()).forEach(([k, v]) => v && params.set(k, v));
    }
    if (name === "messages") {
      Object.entries(collectMsgFilters()).forEach(([k, v]) => v && params.set(k, v));
    }
    if (name === "overview") {
      Object.entries(collectOverviewParams()).forEach(([k, v]) => v && params.set(k, v));
    }
    writeRoute(name, params);
  }
  if (name === "overview") loadStats();
  if (name === "users") {
    loadUsers();
    loadBroadcastJob();
  }
  if (name === "referrals") {
    loadSettings();
    loadReferrals();
    loadPayouts();
  }
  if (name === "ads") loadAds();
  if (name === "orders") loadOrders();
  if (name === "billing") loadBilling();
  if (name === "tickets") loadTickets();
  if (name === "messages") loadMessages();
  if (name === "backups") loadBackups();
  if (name === "broadcast") loadBroadcastJob();
  if (name === "settings" || name === "promo") loadSettings();
  setNavOpen(false);
}

function card(label, value, tab, extra) {
  extra = extra || {};
  const el = document.createElement("div");
  el.className = tab ? "card card-link" : "card";
  const l = document.createElement("div");
  l.className = "l";
  l.textContent = label;
  const n = document.createElement("div");
  n.className = "n";
  n.textContent = value;
  el.appendChild(l);
  el.appendChild(n);
  if (extra.delta != null) {
    const d = document.createElement("div");
    const delta = Number(extra.delta) || 0;
    d.className = "delta " + (delta > 0 ? "delta-up" : delta < 0 ? "delta-down" : "delta-flat");
    const arrow = delta > 0 ? "↑ +" : delta < 0 ? "↓ " : "→ ";
    d.textContent = arrow + delta + (extra.compare || " к прошлому периоду");
    el.appendChild(d);
  }
  if (tab) {
    el.tabIndex = 0;
    el.setAttribute("role", "button");
    const go = () => {
      if (extra.filters) {
        if (tab === "users") applyUserFilters(extra.filters);
        if (tab === "orders" && extra.filters.status) setVal("orderStatus", extra.filters.status);
      }
      switchTab(tab, extra.filters && tab === "users" ? { skipFill: true } : {});
    };
    el.onclick = go;
    el.onkeydown = (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        go();
      }
    };
  }
  return el;
}

function kv(box, map, empty) {
  box.innerHTML = "";
  const keys = Object.keys(map || {});
  if (!keys.length) {
    box.textContent = empty;
    return;
  }
  keys.forEach((k) => {
    const row = document.createElement("div");
    row.className = "kv";
    row.innerHTML = "<span></span><b></b>";
    row.querySelector("span").textContent = k;
    row.querySelector("b").textContent = map[k];
    box.appendChild(row);
  });
}

function jobWhen(at) {
  if (!at) return "неизвестно";
  const d = new Date(at);
  if (Number.isNaN(d.getTime())) return String(at);
  return d.toLocaleString("ru-RU", { timeZone: "Europe/Moscow" });
}

function paintJobs(jobs) {
  const billing = jobs.billing;
  const sync = jobs.panel_sync;
  if (!billing) {
    kv(
      $("jobBilling"),
      {},
      "Ещё не было цикла после деплоя. Первый проход крона (до 10 минут) покажет, приняла ли панель пакет: «пакет» или «по одному»."
    );
  } else {
    kv($("jobBilling"), {
      Когда: jobWhen(billing.at),
      "Устройств в очереди": billing.pending ?? 0,
      Продлили: billing.extended ?? 0,
      Отключили: billing.disabled ?? 0,
      "Включили снова": billing.revived ?? 0,
      "Как продлевали": billing.extend_mode || "нет",
      "Как отключали": billing.disable_mode || "нет",
      "Как включали снова": billing.revive_mode || "нет",
      "Пауза тарификации": billing.paused ? "да" : "нет",
      "Секунд": billing.seconds ?? 0,
    });
  }
  if (!sync) {
    kv(
      $("jobSync"),
      {},
      "Ещё не было сверки после деплоя. Крон раз в 10 минут."
    );
  } else {
    kv($("jobSync"), {
      Когда: jobWhen(sync.at),
      Как: sync.mode || "нет",
      "За этот цикл": sync.partial ? "часть списка" : "до конца",
      Страниц: sync.pages ?? 0,
      "Учёток в панели": sync.seen ?? 0,
      "Обновлено у нас": sync.applied ?? 0,
      "Секунд": sync.seconds ?? 0,
    });
  }
}

function paintSwitch(id, on, opts = {}) {
  const el = $(id);
  if (!el) return;
  const alertOn = !!opts.alert;
  el.classList.toggle("is-on", on);
  el.classList.toggle("is-off", !on);
  el.classList.toggle("is-alert", alertOn);
  el.setAttribute("aria-checked", on ? "true" : "false");
  const state = el.querySelector(".switch-state");
  if (state) state.textContent = on ? (opts.onText || "Вкл") : (opts.offText || "Выкл");
}

function paintFlag(id, on, onText, offText, warnOn) {
  const el = $(id);
  if (!el) return;
  el.textContent = on ? onText : offText;
  el.className = "flag " + (warnOn ? "flag-warn" : on ? "flag-ok" : "flag-off");
}

function paintFlags(f) {
  const m = !!f.maintenance;
  const p = !!f.billing_paused;
  const n = !!f.trial_nudge;
  const inv = !!f.invite_nudge;
  const inf = !!f.info_nudge;
  const st = !!f.story_nudge;
  paintSwitch("maintBtn", m, { alert: m, onText: "Вкл", offText: "Выкл" });
  paintSwitch("billBtn", !p, { onText: "Идёт", offText: "Пауза" });
  paintSwitch("nudgeBtn", n);
  paintSwitch("inviteNudgeBtn", inv);
  paintSwitch("infoNudgeBtn", inf);
  paintSwitch("storyNudgeBtn", st);
  if (typeof f.maintenance_notice === "string") {
    $("maintNotice").value = f.maintenance_notice;
    const phone = $("maintPhonePreview");
    if (phone) phone.textContent = f.maintenance_notice || "Текст оповещения появится здесь";
  }
  const preview = $("maintPreview");
  if (f.maintenance_has_photo) {
    preview.classList.remove("hidden");
    preview.src = "/admin/api/maintenance/photo?t=" + Date.now();
    $("maintPhotoHint").textContent = "Картинка сохранена и будет уходить вместе с текстом.";
  } else {
    preview.classList.add("hidden");
    preview.removeAttribute("src");
    $("maintPhotoHint").textContent = "Загрузите картинку и нажмите «Сохранить».";
  }
  $("opsHint").textContent = m
    ? "Техработы включены: на любое действие в боте уходят сохранённые текст и картинка."
    : p
      ? "Тарификация на паузе: устройства продлеваются, плата не списывается."
      : "";
  paintFlag("flagMaint", m, "Техработы: вкл", "Техработы: выкл", m);
  paintFlag("flagBill", !p, "Тарификация: идёт", "Тарификация: пауза", p);
  paintFlag("flagNudge", n, "Триал: вкл", "Триал: выкл", false);
  paintFlag("flagInvite", inv, "Друзья: вкл", "Друзья: выкл", false);
  paintFlag("flagInfo", inf, "Справка: вкл", "Справка: выкл", false);
  paintFlag("flagStory", st, "История: вкл", "История: выкл", false);
}

async function loadFlags() {
  const f = await api("/admin/api/flags");
  paintFlags(f);
}

const FUNNEL_MAIN = [
  ["entered", "Зашли в бота", "регистрация"],
  ["legal", "Приняли оферту", "обязательный шаг"],
  ["trial", "Взяли триал", "можно пропустить и сразу платить"],
  ["device", "Добавили устройство", "создали в кабинете"],
  ["connected", "Реально подключались", "есть онлайн в панели"],
  ["checkout", "Начали оплату", "создали заказ в кассе"],
  ["paid", "Оплатили", "успешный платёж кассы"],
  ["repeat_paid", "Пополнили ещё раз", "два и больше granted"],
  ["referred", "Привели друга", "хотя бы один пришёл по ссылке"],
];
const FUNNEL_SOURCE = [
  ["entered", "Всего зашли", "старт"],
  ["organic", "Сами / без метки", "не реф и не реклама"],
  ["from_ref", "По рефссылке", "есть пригласивший"],
  ["from_ad", "По рекламе", "закрепилась ad-ссылка"],
  ["promo", "Ввели промокод", "хотя бы один код"],
];
const FUNNEL_LEAK = [
  ["no_legal", "Без оферты", "ещё не приняли"],
  ["device_no_online", "Устройство без онлайна", "создали, но не коннектились"],
  ["checkout_drop", "Бросили оплату", "заказ есть, granted нет"],
  ["blocked", "Заблокированы", "из этой когорты"],
];
const FUNNEL_INV = [
  ["inv_entered", "Пришли по ссылке", "когорта кого-то привела"],
  ["inv_legal", "Приняли оферту", "от пришедших"],
  ["inv_trial", "Взяли триал", "можно пропустить"],
  ["inv_device", "Добавили устройство", "создали в кабинете"],
  ["inv_connected", "Подключались", "есть онлайн"],
  ["inv_checkout", "Начали оплату", "заказ в кассе"],
  ["inv_paid", "Оплатили", "успешный платёж"],
];

let funnelCache = null;
let lastStats = null;
let overviewDash = "check";
let funnelStep = "";
const FUNNEL_PERIODS = ["1d", "7d", "30d", "90d", "all"];
let funnelPeriods = {
  main: localStorage.getItem("way-funnel-period") || "30d",
  source: "30d",
  leak: "30d",
  invite: "30d",
};
["main", "source", "leak", "invite"].forEach((k) => {
  const saved = localStorage.getItem("way-funnel-" + k);
  if (FUNNEL_PERIODS.includes(saved)) funnelPeriods[k] = saved;
});
if (!FUNNEL_PERIODS.includes(funnelPeriods.main)) funnelPeriods.main = "30d";
let funnelPeriod = funnelPeriods.main;

function collectOverviewParams() {
  return {
    dash: overviewDash === "check" ? "" : overviewDash,
    fp: funnelPeriods.main !== "30d" ? funnelPeriods.main : "",
    fs: funnelPeriods.source !== "30d" ? funnelPeriods.source : "",
    fl: funnelPeriods.leak !== "30d" ? funnelPeriods.leak : "",
    fi: funnelPeriods.invite !== "30d" ? funnelPeriods.invite : "",
    step: funnelStep || "",
  };
}

function applyOverviewRoute(params) {
  const dash = params.get("dash") || params.get("tab") || "check";
  overviewDash = ["check", "funnels", "sources", "issues"].includes(dash) ? dash : "check";
  const map = { fp: "main", fs: "source", fl: "leak", fi: "invite" };
  Object.entries(map).forEach(([q, key]) => {
    const v = params.get(q);
    if (FUNNEL_PERIODS.includes(v)) funnelPeriods[key] = v;
  });
  funnelPeriod = funnelPeriods.main;
  const step = params.get("step") || "";
  funnelStep = step === "payment" ? "paid" : step;
  paintOverviewDash();
}

function paintOverviewDash() {
  document.querySelectorAll("#overviewDash [data-dash]").forEach((b) => {
    b.classList.toggle("active", b.dataset.dash === overviewDash);
  });
  ["check", "funnels", "sources", "issues"].forEach((name) => {
    const el = $("dash-" + name);
    if (el) el.classList.toggle("hidden", name !== overviewDash);
  });
}

function setOverviewDash(name) {
  if (!["check", "funnels", "sources", "issues"].includes(name)) name = "check";
  overviewDash = name;
  paintOverviewDash();
  syncOverviewHash();
}

function syncOverviewHash() {
  if (tabFromHash() !== "overview") return;
  const params = new URLSearchParams();
  Object.entries(collectOverviewParams()).forEach(([k, v]) => v && params.set(k, v));
  writeRoute("overview", params);
}

function cohortRange(period) {
  if (period === "all") return { from: "", to: "" };
  const days = { "1d": 1, "7d": 7, "30d": 30, "90d": 90 }[period] || 30;
  const to = new Date();
  const from = new Date(to);
  from.setDate(from.getDate() - (days - 1));
  const fmt = (d) =>
    d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  return { from: fmt(from), to: fmt(to) };
}

function worstDropIndex(steps, convs) {
  let worst = -1;
  let worstV = 101;
  convs.forEach((c, i) => {
    if (i && c != null && c < worstV) {
      worstV = c;
      worst = i;
    }
  });
  return worst;
}

const FUNNEL_STEP_FILTER = {
  trial: { trial: "yes" },
  device: { devices: "yes" },
  connected: { online: "30d" },
  paid: { paid: "yes" },
  repeat_paid: { paid: "yes" },
  blocked: { status: "block" },
  device_no_online: { devices: "yes", online: "never" },
  checkout_drop: { paid: "no" },
  no_legal: { trial: "no" },
  inv_trial: { trial: "yes" },
  inv_device: { devices: "yes" },
  inv_connected: { online: "30d" },
  inv_paid: { paid: "yes" },
};

function sourceHoverText(cur) {
  if (!cur) return "";
  const entered = Number(cur.entered) || 0;
  if (!entered) return "";
  return (
    "Откуда зашедшие: сами " +
    funnelPctText(funnelPct(cur.organic, entered)) +
    ", реф " +
    funnelPctText(funnelPct(cur.from_ref, entered)) +
    ", реклама " +
    funnelPctText(funnelPct(cur.from_ad, entered))
  );
}

function funnelPct(n, d) {
  if (!d) return null;
  return Math.round((1000 * Number(n || 0)) / Number(d)) / 10;
}

function funnelPctText(v) {
  if (v == null || Number.isNaN(v)) return "—";
  return String(v).replace(".", ",") + "%";
}

function mapFunnelSteps(spec, row) {
  return spec.map(([key, title, hint]) => ({
    key,
    title,
    hint,
    n: Number((row && row[key]) || 0),
  }));
}

function paintFunnelRows(boxId, steps, prevSteps, compareLabel, mode, opts) {
  const box = $(boxId);
  if (!box) return;
  opts = opts || {};
  box.innerHTML = "";
  if (!steps.some((s) => s.n > 0)) {
    box.innerHTML = '<p class="funnel-empty">За этот период никого нет.</p>';
    return;
  }
  const share = mode === "share";
  const startN = steps[0] ? steps[0].n : 0;
  const convs = steps.map((s, i) => {
    if (share) return i === 0 ? 100 : funnelPct(s.n, startN);
    return i === 0 ? 100 : funnelPct(s.n, steps[i - 1].n);
  });
  const startShare = steps.map((s, i) => (i === 0 ? 100 : funnelPct(s.n, startN)));
  const prevConvs = (prevSteps || []).map((s, i) => {
    if (!prevSteps || !prevSteps.length) return null;
    if (share) return i === 0 ? 100 : funnelPct(s.n, prevSteps[0].n);
    return i === 0 ? 100 : funnelPct(s.n, prevSteps[i - 1].n);
  });
  const worst = share ? -1 : worstDropIndex(steps, convs);
  const maxN = Math.max(...steps.map((s) => s.n), 1);
  const srcHint = opts.sourceCur ? sourceHoverText(opts.sourceCur) : "";
  steps.forEach((s, i) => {
    const row = document.createElement("div");
    const conv = convs[i];
    const fromStart = startShare[i];
    const prevC = prevConvs[i];
    let deltaCls = "flat";
    let deltaTxt = "";
    if (i && compareLabel && conv != null && prevC != null) {
      const d = Math.round((conv - prevC) * 10) / 10;
      if (d > 0.4) {
        deltaCls = "up";
        deltaTxt = "+" + String(d).replace(".", ",") + " п.п. " + compareLabel;
      } else if (d < -0.4) {
        deltaCls = "down";
        deltaTxt = String(d).replace(".", ",") + " п.п. " + compareLabel;
      } else {
        deltaTxt = "без сдвига " + compareLabel;
      }
    }
    const lost = !share && i ? Math.max(0, steps[i - 1].n - s.n) : 0;
    row.className =
      "funnel-row" +
      (i === worst ? " is-drop" : deltaCls === "up" ? " is-up" : "") +
      (funnelStep && funnelStep === s.key ? " is-active" : "");
    const bar = Math.max(4, Math.round((100 * s.n) / maxN));
    const tips = [];
    if (i === 0) tips.push(share ? s.hint || "старт" : "старт когорты");
    else {
      tips.push("от предыдущего шага " + funnelPctText(conv));
      tips.push("от старта " + funnelPctText(fromStart));
      if (lost) tips.push("ушло " + lost);
      if (s.hint) tips.push(s.hint);
    }
    if (srcHint) tips.push(srcHint);
    if (deltaTxt) tips.push(deltaTxt);
    row.title = tips.join(". ");
    row.innerHTML =
      '<div><div class="funnel-name"></div><div class="funnel-meta"></div></div>' +
      '<div class="funnel-track"><div class="funnel-fill"></div></div>' +
      '<div class="funnel-nums"><span class="funnel-count"></span><span class="funnel-conv"></span>' +
      (deltaTxt ? '<span class="funnel-delta"></span>' : "") +
      "</div>";
    row.querySelector(".funnel-name").textContent = s.title;
    row.querySelector(".funnel-meta").textContent = lost ? "ушло " + lost : "";
    row.querySelector(".funnel-fill").style.width = bar + "%";
    row.querySelector(".funnel-count").textContent = String(s.n);
    row.querySelector(".funnel-conv").textContent = i === 0 && !share ? "100%" : funnelPctText(conv);
    if (deltaTxt) {
      const dEl = row.querySelector(".funnel-delta");
      dEl.textContent = deltaTxt;
      dEl.classList.add(deltaCls);
    }
    row.onclick = () => {
      funnelStep = funnelStep === s.key ? "" : s.key;
      if (funnelStep && overviewDash !== "funnels" && overviewDash !== "sources") {
        overviewDash = "funnels";
        paintOverviewDash();
      }
      syncOverviewHash();
      paintFunnel(funnelCache);
      loadFunnelClients();
    };
    box.appendChild(row);
  });
  return { convs, worst };
}

function paintFunnelInsight(pack, main, convs, worst) {
  const el = $("funnelInsight");
  if (!el) return;
  el.textContent = "";
  if (!main.some((s) => s.n > 0)) {
    el.textContent = "Выберите период, в котором уже есть регистрации.";
    return;
  }
  const bits = [];
  const cur = pack.current || {};
  const entered = Number(cur.entered) || 0;
  const paid = Number(cur.paid) || 0;
  if (entered) {
    const line = document.createElement("span");
    line.textContent =
      "Из " +
      entered +
      " зашедших оплатили " +
      paid +
      " (" +
      funnelPctText(funnelPct(paid, entered)) +
      ").";
    bits.push(line);
  }
  if (worst > 0 && convs[worst] != null) {
    const from = main[worst - 1].title.toLowerCase();
    const to = main[worst].title.toLowerCase();
    const strong = document.createElement("strong");
    strong.className = "drop";
    strong.textContent =
      " Узкое место: " + from + " → " + to + ", доходит " + funnelPctText(convs[worst]) + ".";
    bits.push(strong);
  }
  const leakBits = [];
  if (cur.checkout_drop) leakBits.push("не дожали оплату: " + cur.checkout_drop);
  if (cur.device_no_online) leakBits.push("устройство без онлайна: " + cur.device_no_online);
  if (cur.no_legal) leakBits.push("без оферты: " + cur.no_legal);
  if (leakBits.length) {
    bits.push(document.createTextNode(" Потери: " + leakBits.join(", ") + "."));
  }
  const prev = pack.previous;
  const compare = pack.compare;
  if (prev && compare && convs.length) {
    let bestI = -1;
    let bestD = 0;
    convs.forEach((c, i) => {
      if (!i || c == null) return;
      const pc = funnelPct(prev[FUNNEL_MAIN[i][0]], prev[FUNNEL_MAIN[i - 1][0]]);
      if (pc == null) return;
      const d = c - pc;
      if (d > bestD) {
        bestD = d;
        bestI = i;
      }
    });
    if (bestI > 0 && bestD > 0.4) {
      const strong = document.createElement("strong");
      strong.className = "up";
      strong.textContent =
        " Рост: «" +
        main[bestI].title +
        "» +" +
        String(Math.round(bestD * 10) / 10).replace(".", ",") +
        " п.п. " +
        compare +
        ".";
      bits.push(document.createTextNode(" "));
      bits.push(strong);
    }
  }
  if (!bits.length) {
    el.textContent = "Конверсии по шагам. Красная полоса — самое узкое место между соседними шагами.";
    return;
  }
  bits.forEach((n) => el.appendChild(n));
}

function packFor(card) {
  const period = funnelPeriods[card] || "30d";
  return funnelCache && funnelCache[period];
}

function paintFunnelPeriodButtons() {
  document.querySelectorAll(".funnel-seg[data-funnel-card]").forEach((seg) => {
    const card = seg.dataset.funnelCard;
    const period = funnelPeriods[card] || "30d";
    seg.querySelectorAll("[data-funnel]").forEach((b) => {
      b.classList.toggle("active", b.dataset.funnel === period);
    });
  });
}

function paintFunnel(data) {
  funnelCache = data || funnelCache;
  funnelPeriod = funnelPeriods.main;
  paintFunnelPeriodButtons();
  const pack = packFor("main");
  if (!pack || !pack.current) {
    paintFunnelRows("funnelMain", [], null, "");
    paintFunnelRows("funnelSource", [], null, "", "share");
    paintFunnelRows("funnelLeak", [], null, "", "share");
    paintFunnelRows("funnelInvite", [], null, "");
    const insight = $("funnelInsight");
    if (insight) insight.textContent = "";
    return;
  }
  const compare = pack.compare || "";
  const main = mapFunnelSteps(FUNNEL_MAIN, pack.current);
  const prevMain = pack.previous ? mapFunnelSteps(FUNNEL_MAIN, pack.previous) : null;
  const painted = paintFunnelRows("funnelMain", main, prevMain, compare, "", { sourceCur: pack.current });
  const srcPack = packFor("source") || pack;
  paintFunnelRows(
    "funnelSource",
    mapFunnelSteps(FUNNEL_SOURCE, srcPack.current || {}),
    srcPack.previous ? mapFunnelSteps(FUNNEL_SOURCE, srcPack.previous) : null,
    srcPack.compare || compare,
    "share",
    { sourceCur: srcPack.current }
  );
  const leakPack = packFor("leak") || pack;
  paintFunnelRows(
    "funnelLeak",
    mapFunnelSteps([["entered", "Когорта", "база потерь"], ...FUNNEL_LEAK], leakPack.current || {}),
    leakPack.previous
      ? mapFunnelSteps([["entered", "Когорта", "база потерь"], ...FUNNEL_LEAK], leakPack.previous)
      : null,
    leakPack.compare || compare,
    "share"
  );
  const invPack = packFor("invite") || pack;
  paintFunnelRows(
    "funnelInvite",
    mapFunnelSteps(FUNNEL_INV, invPack.current || {}),
    invPack.previous ? mapFunnelSteps(FUNNEL_INV, invPack.previous) : null,
    invPack.compare || compare
  );
  paintFunnelInsight(pack, main, (painted && painted.convs) || [], painted ? painted.worst : -1);
}

function kpiCell(label, value, delta) {
  const el = document.createElement("div");
  el.className = "kpi-cell";
  const l = document.createElement("div");
  l.className = "l";
  l.textContent = label;
  const n = document.createElement("div");
  n.className = "n";
  n.textContent = value;
  el.appendChild(l);
  el.appendChild(n);
  if (delta) {
    const d = document.createElement("div");
    d.className = "d" + (delta.cls ? " " + delta.cls : "");
    d.textContent = delta.text;
    el.appendChild(d);
  }
  return el;
}

function paintKpiStrip(s) {
  const box = $("kpiStrip");
  if (!box) return;
  box.innerHTML = "";
  const u = s.users || {};
  const on = s.online || {};
  const top = s.topups || {};
  const pack = s.funnel && s.funnel[funnelPeriods.main];
  const cur = (pack && pack.current) || {};
  const prev = (pack && pack.previous) || {};
  const conv = funnelPct(cur.paid, cur.entered);
  const convPrev = funnelPct(prev.paid, prev.entered);
  let convDelta = null;
  if (conv != null && convPrev != null) {
    const d = Math.round((conv - convPrev) * 10) / 10;
    convDelta = {
      cls: d > 0.4 ? "up" : d < -0.4 ? "down" : "",
      text: (d > 0 ? "+" : "") + String(d).replace(".", ",") + " п.п.",
    };
  }
  const day = Number(on.day) || 0;
  const dayPrev = Number(on.day_prev) || 0;
  const dayD = day - dayPrev;
  box.appendChild(kpiCell("Оборот", String(s.revenue_rub || 0) + " ₽"));
  box.appendChild(kpiCell("Платежи", String(top.payments || 0)));
  box.appendChild(kpiCell("Новые 7д", String(u.new_7d || 0)));
  box.appendChild(
    kpiCell("Онлайн", String(day), {
      cls: dayD > 0 ? "up" : dayD < 0 ? "down" : "",
      text: (dayD > 0 ? "+" : "") + dayD + " к суткам",
    })
  );
  box.appendChild(kpiCell("В оплату", funnelPctText(conv), convDelta));
}

function paintProblemsBadge(s) {
  const el = $("problemsBadge");
  if (!el) return;
  const n = Number(s.tickets_open) || 0;
  if (!n) {
    el.classList.add("hidden");
    el.classList.remove("has-fire");
    el.textContent = "Проблемы";
    return;
  }
  el.classList.remove("hidden");
  el.classList.add("has-fire");
  el.innerHTML = "Проблемы<span class=\"n\">" + n + "</span>";
}

function worstMainKey(row) {
  if (!row) return "";
  const steps = mapFunnelSteps(FUNNEL_MAIN, row);
  const convs = steps.map((s, i) => (i === 0 ? 100 : funnelPct(s.n, steps[i - 1].n)));
  const idx = worstDropIndex(steps, convs);
  return idx > 0 ? steps[idx].key : "";
}

function paintStatusAlert(s) {
  const el = $("statusAlert");
  if (!el) return;
  const lines = [];
  const tickets = Number(s.tickets_open) || 0;
  if (tickets) {
    lines.push("Есть открытые обращения: " + tickets + " тикет" + (tickets === 1 ? "" : "ов") + ".");
  }
  const pack = s.funnel && s.funnel[funnelPeriods.main];
  const cur = pack && pack.current;
  const prev = pack && pack.previous;
  if (cur && prev) {
    const conv = funnelPct(cur.paid, cur.entered);
    const convPrev = funnelPct(prev.paid, prev.entered);
    if (conv != null && convPrev && convPrev > 0 && (conv - convPrev) / convPrev < -0.2) {
      lines.push(
        "Конверсия в оплату упала больше чем на 20%: " +
          funnelPctText(conv) +
          " против " +
          funnelPctText(convPrev) +
          "."
      );
    }
    const nowKey = worstMainKey(cur);
    const prevKey = worstMainKey(prev);
    if (nowKey && prevKey && nowKey !== prevKey) {
      const title = (FUNNEL_MAIN.find((x) => x[0] === nowKey) || [])[1] || nowKey;
      lines.push("Узкое место сместилось: сейчас «" + title + "».");
    }
  }
  const shown = lines.slice(0, 2);
  if (!shown.length) {
    el.classList.add("hidden");
    el.innerHTML = "";
    return;
  }
  el.classList.remove("hidden");
  el.classList.toggle("is-danger", tickets > 0);
  el.innerHTML = shown.map((t) => "<p></p>").join("");
  Array.from(el.querySelectorAll("p")).forEach((p, i) => {
    p.textContent = shown[i];
  });
}

function paintOverviewChrome(s) {
  lastStats = s;
  paintKpiStrip(s);
  paintProblemsBadge(s);
  paintStatusAlert(s);
}

async function loadFunnelClients() {
  const body = $("funnelClientRows");
  const hint = $("funnelClientHint");
  if (!body) return;
  body.innerHTML = "";
  if (!funnelStep) {
    if (hint) hint.textContent = "Выберите шаг воронки. Список строится из текущих фильтров пользователей за период когорты.";
    body.appendChild(emptyRow(5, "Шаг не выбран"));
    return;
  }
  if ($("funnelCardMain")) $("funnelCardMain").open = true;
  const period = funnelPeriods.main;
  const range = cohortRange(period);
  const extra = { ...(FUNNEL_STEP_FILTER[funnelStep] || {}) };
  if ((funnelStep === "connected" || funnelStep === "inv_connected") && extra.online === "30d") {
    extra.online = period === "1d" || period === "7d" ? period : "30d";
  }
  const title = (
    FUNNEL_MAIN.find((x) => x[0] === funnelStep) ||
    FUNNEL_SOURCE.find((x) => x[0] === funnelStep) ||
    FUNNEL_LEAK.find((x) => x[0] === funnelStep) ||
    FUNNEL_INV.find((x) => x[0] === funnelStep) ||
    [funnelStep, funnelStep]
  )[1];
  if (hint) {
    hint.textContent =
      "Приближение по полям списка пользователей для шага «" +
      title +
      "»" +
      (range.from ? ", когорта " + range.from + " — " + range.to : "") +
      ". Это не точная выборка воронки.";
  }
  try {
    const data = await api(
      `/admin/api/users?${queryString({
        ...extra,
        from: range.from,
        to: range.to,
        page: 1,
      })}`
    );
    const items = data.items || [];
    if (!items.length) {
      body.appendChild(emptyRow(5, "Никого не нашли по этому приближению"));
      return;
    }
    items.forEach((u) => {
      const tr = document.createElement("tr");
      tr.className = "row-link";
      const tdWho = document.createElement("td");
      tdWho.className = "who-cell";
      const idLine = document.createElement("div");
      idLine.textContent = u.telegram_id + (u.username ? " @" + u.username : "");
      const nameLine = document.createElement("div");
      nameLine.className = "who-sub";
      nameLine.textContent = u.first_name || "без имени";
      tdWho.appendChild(idLine);
      tdWho.appendChild(nameLine);
      tr.appendChild(tdWho);
      tr.appendChild(tdText(u.balance_rub == null ? "—" : String(u.balance_rub)));
      tr.appendChild(tdText(u.trial_used ? "да" : "нет"));
      const nDev = Array.isArray(u.devices) ? u.devices.length : 0;
      tr.appendChild(tdText(nDev ? String(nDev) : u.remnawave_id ? "подписка" : "—"));
      tr.appendChild(tdText(paidLine(u)));
      tr.onclick = () => openUser(u);
      body.appendChild(tr);
    });
  } catch (e) {
    body.appendChild(emptyRow(5, (e && e.message) || "Не удалось загрузить список"));
  }
}

function paidLine(u) {
  const n = Number(u && u.paid_topup_count) || 0;
  const sum = Number(u && u.paid_topup_rub) || 0;
  if (!n && !sum) return "нет";
  return sum + " ₽ · " + n + (n === 1 ? " раз" : " раз");
}

function paintModalPaid(u) {
  const el = $("modalPaid");
  if (!el) return;
  const n = Number(u && u.paid_topup_count) || 0;
  const sum = Number(u && u.paid_topup_rub) || 0;
  if (!n && !sum) {
    el.textContent = "Пополнения: не было успешных оплат кассы";
    return;
  }
  el.textContent =
    "Пополнил: " +
    sum +
    " ₽ · " +
    n +
    " платеж(ей)" +
    (u.last_paid_at ? " · последний " + fmtAgo(u.last_paid_at) + " · " + fmt(u.last_paid_at) : "");
}

function paintTopupPayers(items) {
  const body = $("topupPayerRows");
  if (!body) return;
  body.innerHTML = "";
  const labels = ["Клиент", "Платежей", "Сумма", "Последний"];
  if (!items.length) {
    body.appendChild(emptyRow(4, "Успешных пополнений пока нет"));
    return;
  }
  items.forEach((row) => {
    const tr = document.createElement("tr");
    tr.className = "row-link";
    tr.appendChild(tdText(whoLabel(row.telegram_id, row.username, row.first_name)));
    tr.appendChild(tdText(String(row.payments || 0)));
    tr.appendChild(tdText((Number(row.amount_rub) || 0) + " ₽"));
    tr.appendChild(tdText(row.last_paid_at ? fmtAgo(row.last_paid_at) + " · " + fmt(row.last_paid_at) : "—"));
    labelRow(tr, labels);
    tr.onclick = () => {
      applyUserFilters({ q: String(row.telegram_id), paid: "yes" });
      switchTab("users", { skipFill: true });
    };
    body.appendChild(tr);
  });
}

async function loadStats() {
  const err = $("statsErr");
  if (err) {
    err.classList.add("hidden");
    err.textContent = "";
  }
  try {
    await loadFlags();
    loadSubJob();
    const s = await api("/admin/api/stats");
    const u = s.users || {};
    const fill = (id, rows) => {
      const box = $(id);
      if (!box) return;
      box.innerHTML = "";
      rows.forEach(([l, v, tab, extra]) => box.appendChild(card(l, v, tab, extra)));
    };
    const on = s.online || {};
    const onlineCard = (label, cur, prev, filter, compare) => {
      const c = Number(cur) || 0;
      const p = Number(prev) || 0;
      return [label, c, "users", { delta: c - p, compare, filters: { online: filter } }];
    };
    fill("cardsOnline", [
      onlineCard("Онлайн за сутки", on.day, on.day_prev, "1d", " к прошлым суткам"),
      onlineCard("Онлайн за неделю", on.week, on.week_prev, "7d", " к прошлой неделе"),
      onlineCard("Онлайн за месяц", on.month, on.month_prev, "30d", " к прошлому месяцу"),
    ]);
    fill("cardsAudience", [
      ["Пользователи", u.users_total || 0, "users"],
      ["Оферта принята", u.legal_ok || 0],
      ["Активные подписки", u.active || 0],
      ["Бесплатный период использован", u.trial_used || 0],
      ["Новые за сутки", u.new_1d || 0],
      ["Новые за 7 дней", u.new_7d || 0],
      ["Новые за 30 дней", u.new_30d || 0],
      ["Пришли по ссылке", u.referred || 0, "referrals"],
    ]);
    fill("cardsFinance", [
      ["Оборот, рубли", s.revenue_rub || 0, "orders"],
      ["Промокоды", s.promo_uses || 0, "promo"],
      ["Stars-платежи", s.stars_payments || 0],
      ["Реф. награда выдана", u.referral_rewarded || 0, "referrals"],
      ["Заявки на вывод", u.payouts_pending || 0, "referrals"],
    ]);
    const top = s.topups || {};
    fill("cardsTopup", [
      ["Плативших", top.payers || 0, "users", { filters: { paid: "yes" } }],
      ["Платежей", top.payments || 0, "orders", { filters: { status: "granted" } }],
      ["Сумма пополнений, ₽", top.amount_rub || 0, "orders", { filters: { status: "granted" } }],
    ]);
    paintTopupPayers(top.items || []);
    fill("cardsIssues", [
      ["Открытые тикеты", s.tickets_open || 0, "tickets"],
      ["Заблокированы в магазине", u.blocked || 0, "users", { filters: { status: "block" } }],
      ["Заблокировали бота", u.bot_blocked || 0, "users", { filters: { status: "bot_block" } }],
      ["Блок бота без триала", u.bot_blocked_idle || 0, "users", { filters: { status: "bot_block", trial: "no", paid: "no" } }],
    ]);
    kv($("orderStats"), s.orders, "Заказов пока нет");
    kv($("planStats"), s.plans, "Оплаченных тарифов нет");
    paintFunnel(s.funnel);
    paintOverviewChrome(s);
    paintOverviewDash();
    loadFunnelClients();
    paintJobs(s.jobs || {});
    const today = s.billing_today || {};
    if ($("billToday")) {
      $("billToday").textContent =
        "За сегодня: " +
        (today.charges || 0) +
        " списаний, " +
        (today.errors || 0) +
        " ошибок, " +
        (today.credited || 0) +
        " ₽ начислено";
    }
    if ($("broadcastCount") && !document.querySelector('input[name="bcTpl"]:checked')) {
      $("broadcastCount").textContent = "Уйдёт примерно " + (s.broadcast_users || 0) + " пользователям (без заблокированных).";
    }
  } catch (e) {
    if (err) {
      err.classList.remove("hidden");
      err.textContent = (e && e.message) || "Не удалось загрузить обзор";
    }
  }
}

function pager(el, page, total, limit, onPage) {
  el.innerHTML = "";
  const pages = Math.max(1, Math.ceil(total / limit));
  const info = document.createElement("span");
  info.className = "muted";
  info.textContent = `${total} записей, стр. ${page}/${pages}`;
  el.appendChild(info);
  const sel = document.createElement("select");
  sel.setAttribute("aria-label", "На странице");
  [25, 50, 100].forEach((n) => {
    const o = document.createElement("option");
    o.value = String(n);
    o.textContent = n + " на стр.";
    if (n === pageLimit) o.selected = true;
    sel.appendChild(o);
  });
  sel.onchange = () => {
    pageLimit = Number(sel.value) || 25;
    localStorage.setItem("way-admin-limit", String(pageLimit));
    onPage(1);
  };
  el.appendChild(sel);
  if (page > 1) {
    const prev = document.createElement("button");
    prev.className = "ghost";
    prev.textContent = "Назад";
    prev.onclick = () => onPage(page - 1);
    el.appendChild(prev);
  }
  if (page < pages) {
    const next = document.createElement("button");
    next.className = "ghost";
    next.textContent = "Вперёд";
    next.onclick = () => onPage(page + 1);
    el.appendChild(next);
  }
}

function whoLabel(id, username, name) {
  if (!id) return "—";
  return `${id}` + (username ? ` @${username}` : "") + (name ? ` · ${name}` : "");
}

function pillKind(text) {
  const v = String(text || "").toLowerCase();
  if (v.includes("блок") || v === "disabled" || v === "expired" || v === "failed" || v === "отключение" || v === "ошибка") return "bad";
  if (v === "active" || v === "granted" || v === "выдана" || v === "paid" || v === "списание" || v === "включение" || v === "начисление" || v === "обещанный") return "ok";
  if (v === "created" || v === "ещё нет" || v === "pending" || v === "пауза" || v === "баланс" || v === "возврат обещанного" || v === "удаление") return "warn";
  return "";
}

function tdText(text) {
  const td = document.createElement("td");
  td.textContent = text;
  return td;
}

function tdPill(text) {
  const td = document.createElement("td");
  const s = document.createElement("span");
  const kind = pillKind(text);
  s.className = kind ? `pill pill-${kind}` : "pill";
  s.textContent = text;
  td.appendChild(s);
  return td;
}

async function loadUsers(page) {
  if (page) userPage = page;
  const f = collectUserFilters();
  const reset = $("userReset");
  if (reset) reset.classList.toggle("hidden", !hasAny(f));
  const chips = [];
  if (f.status) chips.push(["status", "Статус: " + ({ ok: "активен", block: "блок в магазине", bot_block: "блок бота" }[f.status] || f.status)]);
  if (f.trial) chips.push(["trial", "Триал: " + f.trial]);
  if (f.devices) chips.push(["devices", "Устройства: " + f.devices]);
  if (f.paid) chips.push(["paid", f.paid === "yes" ? "были оплаты" : "без оплат"]);
  if (f.online) {
    const names = { now: "сейчас", "1h": "час", "1d": "сутки", "7d": "неделя", "30d": "месяц", never: "не было" };
    chips.push(["online", "Онлайн: " + (names[f.online] || f.online)]);
  }
  if (f.bal_sign) {
    const names = { pos: "больше нуля", zero: "ноль", neg: "минус" };
    chips.push(["bal_sign", "Баланс: " + (names[f.bal_sign] || f.bal_sign)]);
  }
  if (f.bal_min) chips.push(["bal_min", "Баланс от " + f.bal_min]);
  if (f.bal_max) chips.push(["bal_max", "Баланс до " + f.bal_max]);
  if (f.from) chips.push(["from", "с " + f.from]);
  if (f.to) chips.push(["to", "по " + f.to]);
  if (f.q) chips.push(["q", "поиск: " + f.q]);
  paintChips("userChips", chips, (key) => {
    setVal(USER_FILTER_IDS[key], "");
    selectedUsers.clear();
    loadUsers(1);
  });
  writeRoute("users", new URLSearchParams(Object.entries(f).filter(([, v]) => v)));
  const data = await api(`/admin/api/users?${queryString({ ...f, page: userPage })}`);
  lastUserItems = data.items || [];
  const body = $("userRows");
  body.innerHTML = "";
  const labels = ["", "Клиент", "Баланс", "Пополнил", "Устройства", "Онлайн", "Трафик", "Триал", "До", "Статус", "Пригласил", "Друзей", ""];
  if (!lastUserItems.length) {
    body.appendChild(emptyRow(13, hasAny(f) ? "Никого не нашли по фильтрам" : "Пользователей пока нет"));
  }
  lastUserItems.forEach((u) => {
    const tr = document.createElement("tr");
    tr.className = "row-link" + (u.blocked_at || u.bot_blocked_at ? " is-blocked" : "");
    const tdCheck = document.createElement("td");
    tdCheck.className = "check-col";
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = selectedUsers.has(u.telegram_id);
    cb.onclick = (e) => e.stopPropagation();
    cb.onchange = () => {
      if (cb.checked) selectedUsers.add(u.telegram_id);
      else selectedUsers.delete(u.telegram_id);
      paintUserSel();
    };
    tdCheck.appendChild(cb);
    tr.appendChild(tdCheck);
    const tdWho = document.createElement("td");
    tdWho.className = "who-cell";
    const idLine = document.createElement("div");
    idLine.textContent = u.telegram_id + (u.username ? " @" + u.username : "");
    const nameLine = document.createElement("div");
    nameLine.className = "who-sub";
    nameLine.textContent = u.first_name || "без имени";
    tdWho.appendChild(idLine);
    tdWho.appendChild(nameLine);
    tr.appendChild(tdWho);
    tr.appendChild(tdText(u.balance_rub == null ? "—" : String(u.balance_rub)));
    const tdPaid = tdText(paidLine(u));
    if (u.last_paid_at) tdPaid.title = fmt(u.last_paid_at);
    tr.appendChild(tdPaid);
    tr.appendChild(deviceBreakdownCell(u));
    tr.appendChild(onlineCell(u.last_online_at));
    const tdTraffic = tdText(fmtTraffic(u.used_traffic_bytes, u.lifetime_traffic_bytes));
    tdTraffic.title = "Сейчас: " + fmtBytes(u.used_traffic_bytes) + ". Всего: " + fmtBytes(u.lifetime_traffic_bytes);
    tr.appendChild(tdTraffic);
    tr.appendChild(tdText(u.trial_used ? "да" : "нет"));
    tr.appendChild(tdText(fmt(u.expire_at)));
    tr.appendChild(tdPill(u.blocked_at ? "блок" : (u.bot_blocked_at ? "блок бота" : (u.panel_status || "—"))));
    tr.appendChild(tdText(
      u.referred_by
        ? whoLabel(u.referred_by, u.referrer_username, u.referrer_name)
        : "—"
    ));
    tr.appendChild(tdText(String(u.invited_count || 0)));
    const td = document.createElement("td");
    const btn = document.createElement("button");
    btn.className = "ghost";
    btn.textContent = "Открыть";
    btn.onclick = (e) => {
      e.stopPropagation();
      openUser(u);
    };
    td.appendChild(btn);
    tr.appendChild(td);
    tr.onclick = () => openUser(u);
    labelRow(tr, labels);
    body.appendChild(tr);
  });
  pager($("userPager"), data.page, data.total, data.limit, loadUsers);
  paintUserSel();
}

function paintUserSel() {
  const n = selectedUsers.size;
  $("userSelCount").textContent = "Выбрано: " + n;
  const bar = $("bulkBar");
  if (bar) bar.classList.toggle("is-empty", n === 0);
  const pageIds = lastUserItems.map((u) => u.telegram_id);
  $("userSelectAll").checked = pageIds.length > 0 && pageIds.every((id) => selectedUsers.has(id));
  $("userSelectAll").indeterminate =
    pageIds.some((id) => selectedUsers.has(id)) && !$("userSelectAll").checked;
}

function bulkSummary(r) {
  let text = `Готово: ${r.done} из ${r.total}`;
  if (r.skipped) text += `, пропущено ${r.skipped}`;
  if (r.failed) text += `, ошибок ${r.failed}`;
  return text;
}

async function runBulk(payload, confirmText) {
  if (!(await confirmAction("Массовое действие", confirmText))) return;
  $("bulkOut").textContent = "Выполняю...";
  try {
    const r = await api("/admin/api/users/bulk", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (payload.action === "message" && (r.queued || r.running)) {
      $("bulkOut").textContent = "Запущено";
      loadBroadcastJob();
      return;
    }
    $("bulkOut").textContent = bulkSummary(r);
    toast(bulkSummary(r));
    if (payload.action === "delete") {
      selectedUsers.clear();
      closeModal();
    }
    await loadUsers();
  } catch (err) {
    $("bulkOut").textContent = err.message || "Не удалось выполнить";
  }
}

async function loadReferrals(page) {
  if (page) refPage = page;
  const f = { q: val("refQ"), reward: val("refReward"), from: val("refFrom"), to: val("refTo") };
  const reset = $("refReset");
  if (reset) reset.classList.toggle("hidden", !hasAny(f));
  const chips = [];
  if (f.q) chips.push(["q", "поиск: " + f.q]);
  if (f.reward) chips.push(["reward", "награда: " + f.reward]);
  if (f.from) chips.push(["from", "с " + f.from]);
  if (f.to) chips.push(["to", "по " + f.to]);
  paintChips("refChips", chips, (key) => {
    setVal({ q: "refQ", reward: "refReward", from: "refFrom", to: "refTo" }[key], "");
    loadReferrals(1);
  });
  writeRoute("referrals", new URLSearchParams(Object.entries(f).filter(([, v]) => v)));
  const data = await api(`/admin/api/referrals?${queryString({ ...f, page: refPage })}`);
  const body = $("refRows");
  body.innerHTML = "";
  const labels = ["Пришёл", "Пригласил", "Когда", "Награда"];
  if (!data.items.length) {
    body.appendChild(emptyRow(4, hasAny(f) ? "Ничего не нашли" : "Пока никто не приходил по рефссылке"));
  }
  data.items.forEach((row) => {
    const tr = document.createElement("tr");
    [
      whoLabel(row.invitee_id, row.invitee_username, row.invitee_name),
      whoLabel(row.referrer_id, row.referrer_username, row.referrer_name),
      fmt(row.invitee_at),
    ].forEach((t) => tr.appendChild(tdText(t)));
    tr.appendChild(tdPill(row.referral_rewarded ? "выдана" : "ещё нет"));
    labelRow(tr, labels);
    body.appendChild(tr);
  });
  pager($("refPager"), data.page, data.total, data.limit, loadReferrals);
}

async function loadAds() {
  const body = $("adRows");
  if (!body) return;
  const archived = $("adShowArchived") && $("adShowArchived").checked;
  const data = await api("/admin/api/ads" + (archived ? "?archived=1" : ""));
  body.innerHTML = "";
  const labels = ["Название", "Ссылка", "Клики", "Пришли", "Триал", "Оплатили", "Создана", ""];
  if (!data.items.length) {
    body.appendChild(emptyRow(8, archived ? "Скрытых ссылок нет" : "Пока нет рекламных ссылок"));
  }
  data.items.forEach((row) => {
    const tr = document.createElement("tr");
    if (row.archived) tr.classList.add("is-muted");
    tr.appendChild(tdText(row.title + (row.archived ? " (скрыта)" : "")));
    const linkTd = document.createElement("td");
    const code = document.createElement("code");
    code.textContent = "ad_" + row.slug;
    linkTd.appendChild(code);
    tr.appendChild(linkTd);
    tr.appendChild(tdText(String(row.clicks || 0)));
    tr.appendChild(tdText(String(row.users || 0)));
    tr.appendChild(tdText(String(row.trial || 0)));
    tr.appendChild(tdText(String(row.paid || 0)));
    tr.appendChild(tdText(fmt(row.created_at)));
    const td = document.createElement("td");
    const copyBtn = document.createElement("button");
    copyBtn.type = "button";
    copyBtn.className = "ghost";
    copyBtn.textContent = "Копировать";
    copyBtn.onclick = async (e) => {
      e.stopPropagation();
      try {
        await navigator.clipboard.writeText(row.url);
        toast("Ссылка скопирована");
      } catch (_e) {
        toast(row.url);
      }
    };
    td.appendChild(copyBtn);
    if (!row.archived) {
      const hideBtn = document.createElement("button");
      hideBtn.type = "button";
      hideBtn.className = "ghost";
      hideBtn.textContent = "Скрыть";
      hideBtn.onclick = async (e) => {
        e.stopPropagation();
        if (!(await confirmAction("Скрыть ссылку", "Из списка пропадёт, по старой ссылке люди всё ещё смогут зайти."))) return;
        try {
          await api(`/admin/api/ads/${row.id}/archive`, { method: "POST", body: "{}" });
          loadAds();
        } catch (err) {
          toast(err.message || "Не удалось скрыть");
        }
      };
      td.appendChild(hideBtn);
    }
    tr.appendChild(td);
    labelRow(tr, labels);
    body.appendChild(tr);
  });
}

async function loadPayouts(page) {
  if (page) payPage = page;
  const f = { q: val("payQ"), status: val("payStatus") };
  const reset = $("payReset");
  if (reset) reset.classList.toggle("hidden", !hasAny(f));
  const data = await api(`/admin/api/payouts?${queryString({ ...f, page: payPage })}`);
  const body = $("payRows");
  if (!body) return;
  body.innerHTML = "";
  const labels = ["Клиент", "Сумма", "Реквизиты", "Статус", "Когда", ""];
  const stMap = { pending: "ожидает", paid: "выплачено", rejected: "отклонено" };
  if (!data.items.length) {
    body.appendChild(emptyRow(6, hasAny(f) ? "Ничего не нашли" : "Заявок на вывод нет"));
  }
  data.items.forEach((row) => {
    const tr = document.createElement("tr");
    tr.appendChild(tdText(whoLabel(row.telegram_id, row.username, row.first_name)));
    tr.appendChild(tdText(String(row.amount || 0) + " ₽"));
    tr.appendChild(tdText(row.details || "—"));
    tr.appendChild(tdPill(stMap[row.status] || row.status || "—"));
    tr.appendChild(tdText(fmt(row.created_at)));
    const td = document.createElement("td");
    if (row.status === "pending") {
      const ok = document.createElement("button");
      ok.type = "button";
      ok.textContent = "Выплачено";
      ok.onclick = (e) => {
        e.stopPropagation();
        resolvePayout(row.id, "paid");
      };
      const no = document.createElement("button");
      no.type = "button";
      no.className = "ghost";
      no.textContent = "Отказать";
      no.onclick = (e) => {
        e.stopPropagation();
        resolvePayout(row.id, "rejected");
      };
      td.appendChild(ok);
      td.appendChild(no);
    }
    tr.appendChild(td);
    labelRow(tr, labels);
    body.appendChild(tr);
  });
  pager($("payPager"), data.page, data.total, data.limit, loadPayouts);
}

async function resolvePayout(id, action) {
  const title = action === "paid" ? "Подтвердить выплату" : "Отклонить заявку";
  const text =
    action === "paid"
      ? "Отметить, что деньги уже перевели клиенту?"
      : "Вернуть сумму на баланс клиента?";
  if (!(await confirmAction(title, text))) return;
  try {
    const r = await api(`/admin/api/payouts/${id}`, {
      method: "POST",
      body: JSON.stringify({ action }),
    });
    toast(r.result || "Готово");
    await loadPayouts();
  } catch (err) {
    toast(err.message || "Не удалось обработать");
  }
}

async function loadOrders(page) {
  if (page) orderPage = page;
  const f = { q: val("orderQ"), status: val("orderStatus"), from: val("orderFrom"), to: val("orderTo") };
  const reset = $("orderReset");
  if (reset) reset.classList.toggle("hidden", !hasAny(f));
  const chips = [];
  if (f.q) chips.push(["q", "поиск: " + f.q]);
  if (f.status) chips.push(["status", f.status]);
  if (f.from) chips.push(["from", "с " + f.from]);
  if (f.to) chips.push(["to", "по " + f.to]);
  paintChips("orderChips", chips, (key) => {
    setVal({ q: "orderQ", status: "orderStatus", from: "orderFrom", to: "orderTo" }[key], "");
    loadOrders(1);
  });
  writeRoute("orders", new URLSearchParams(Object.entries(f).filter(([, v]) => v)));
  const data = await api(`/admin/api/orders?${queryString({ ...f, page: orderPage })}`);
  const body = $("orderRows");
  body.innerHTML = "";
  const labels = ["Заказ", "Пользователь", "Сумма", "Тариф", "Статус", "Создан"];
  if (!data.items.length) {
    body.appendChild(emptyRow(6, hasAny(f) ? "Заказов не нашли" : "Заказов пока нет"));
  }
  data.items.forEach((o) => {
    const tr = document.createElement("tr");
    tr.className = "row-link";
    tr.appendChild(tdText(o.order_id));
    tr.appendChild(tdText(whoLabel(o.telegram_id, o.username, o.first_name)));
    tr.appendChild(tdText(o.status === "granted" || o.amount_rub ? (Number(o.amount_rub) || 0) + " ₽" : "—"));
    tr.appendChild(tdText(o.plan_code));
    tr.appendChild(tdPill(o.status));
    tr.appendChild(tdText(fmt(o.created_at)));
    labelRow(tr, labels);
    tr.onclick = () => {
      applyUserFilters({ q: String(o.telegram_id) });
      switchTab("users", { skipFill: true });
    };
    body.appendChild(tr);
  });
  pager($("orderPager"), data.page, data.total, data.limit, loadOrders);
}

const BILL_KIND = {
  charge: "списание",
  disable: "отключение",
  pause: "пауза",
  revive: "включение",
  trial: "триал",
  admin_balance: "баланс",
  admin_grant: "начисление",
  referral: "реферал",
  referral_payout: "вывод рефералки",
  referral_revoke: "возврат рефералки",
  trust: "обещанный",
  trust_collect: "возврат обещанного",
  device_delete: "удаление",
  error: "ошибка",
};
const BILL_SOURCE = { cron: "тарификация", admin: "админка", user: "кабинет", signup: "регистрация" };

function billKindLabel(kind) {
  return BILL_KIND[kind] || kind || "—";
}

function billAmount(n) {
  if (n == null || n === 0) return "—";
  const v = Number(n);
  if (!Number.isFinite(v)) return String(n);
  return (v > 0 ? "+" : "") + v + " ₽";
}

function billRowCells(e) {
  return [
    fmt(e.created_at),
    whoLabel(e.telegram_id, e.username, e.first_name),
    billKindLabel(e.kind),
    e.device_title || "—",
    billAmount(e.amount),
    e.balance_after == null ? "—" : `${e.balance_after} ₽`,
    BILL_SOURCE[e.source] || e.source || "—",
  ];
}

async function loadBilling(page) {
  if (page) billPage = page;
  const f = {
    q: val("billQ"),
    kind: val("billKind"),
    source: val("billSource"),
    from: val("billFrom"),
    to: val("billTo"),
  };
  const reset = $("billReset");
  if (reset) reset.classList.toggle("hidden", !hasAny(f));
  const chips = [];
  if (f.q) chips.push(["q", "поиск: " + f.q]);
  if (f.kind) chips.push(["kind", billKindLabel(f.kind)]);
  if (f.source) chips.push(["source", BILL_SOURCE[f.source] || f.source]);
  if (f.from) chips.push(["from", "с " + f.from]);
  if (f.to) chips.push(["to", "по " + f.to]);
  paintChips("billChips", chips, (key) => {
    setVal({ q: "billQ", kind: "billKind", source: "billSource", from: "billFrom", to: "billTo" }[key], "");
    loadBilling(1);
  });
  writeRoute("billing", new URLSearchParams(Object.entries(f).filter(([, v]) => v)));
  const data = await api(`/admin/api/billing?${queryString({ ...f, page: billPage })}`);
  const body = $("billRows");
  body.innerHTML = "";
  const labels = ["Время", "Пользователь", "Событие", "Устройство", "Сумма", "Баланс после", "Источник"];
  const items = data.items || [];
  if (!items.length) {
    body.appendChild(emptyRow(7, hasAny(f) ? "Ничего не нашли" : "Пока нет событий биллинга"));
  }
  const grouped = [];
  for (let i = 0; i < items.length; i++) {
    const e = items[i];
    if (e.kind === "error") {
      const key = String(e.telegram_id) + "|" + (e.device_title || "") + "|" + (e.note || "");
      const kids = [e];
      while (i + 1 < items.length && items[i + 1].kind === "error") {
        const n = items[i + 1];
        const nk = String(n.telegram_id) + "|" + (n.device_title || "") + "|" + (n.note || "");
        if (nk !== key) break;
        kids.push(n);
        i++;
      }
      grouped.push({ kids, sample: e });
    } else {
      grouped.push({ kids: [e], sample: e });
    }
  }
  grouped.forEach((g) => {
    const e = g.sample;
    const tr = document.createElement("tr");
    const amount = Number(e.amount || 0);
    if (e.kind === "error") tr.classList.add("bill-row-error");
    else if (amount > 0) tr.classList.add("bill-row-plus");
    const cells = billRowCells(e);
    if (g.kids.length > 1) {
      cells[2] = billKindLabel(e.kind) + " · " + g.kids.length + " повтор.";
      tr.classList.add("group-row");
    }
    tr.appendChild(tdText(cells[0]));
    tr.appendChild(tdText(cells[1]));
    tr.appendChild(tdPill(cells[2]));
    tr.appendChild(tdText(cells[3]));
    tr.appendChild(tdText(cells[4]));
    tr.appendChild(tdText(cells[5]));
    tr.appendChild(tdText(cells[6]));
    if (e.note) tr.title = e.note;
    labelRow(tr, labels);
    body.appendChild(tr);
    if (g.kids.length > 1) {
      tr.onclick = () => {
        const open = tr.dataset.open === "1";
        tr.dataset.open = open ? "0" : "1";
        let next = tr.nextElementSibling;
        while (next && next.classList.contains("bill-child")) {
          const cur = next;
          next = next.nextElementSibling;
          if (open) cur.remove();
        }
        if (!open) {
          g.kids.slice(1).reverse().forEach((child) => {
            const cr = document.createElement("tr");
            cr.className = "bill-child bill-row-error";
            const cc = billRowCells(child);
            cr.appendChild(tdText(cc[0]));
            cr.appendChild(tdText(cc[1]));
            cr.appendChild(tdPill(cc[2]));
            cr.appendChild(tdText(cc[3]));
            cr.appendChild(tdText(cc[4]));
            cr.appendChild(tdText(cc[5]));
            cr.appendChild(tdText(cc[6]));
            labelRow(cr, labels);
            tr.after(cr);
          });
        }
      };
    }
  });
  pager($("billPager"), data.page, data.total, data.limit, loadBilling);
}

function kvLine(label, value) {
  const row = document.createElement("div");
  row.className = "dev-kv";
  const k = document.createElement("span");
  k.textContent = label;
  const v = document.createElement("span");
  v.textContent = value || "—";
  row.appendChild(k);
  row.appendChild(v);
  return row;
}

function nodeLine(node) {
  if (!node || typeof node !== "object") return "—";
  const parts = [node.name, node.address].filter(Boolean);
  return parts.join(" · ") || node.uuid || "—";
}

function paintDeviceCard(d) {
  const card = document.createElement("article");
  card.className = "dev-card";
  const head = document.createElement("div");
  head.className = "dev-card-head";
  const title = document.createElement("div");
  title.className = "dev-card-title";
  title.textContent = d.title || "Устройство";
  head.appendChild(title);
  const pill = document.createElement("span");
  const kind = pillKind(d.status || "—");
  pill.className = kind ? `pill pill-${kind}` : "pill";
  pill.textContent = d.status || "—";
  head.appendChild(pill);
  card.appendChild(head);
  const how = [d.client, d.platform].filter(Boolean).join(" · ");
  card.appendChild(kvLine("Клиент", how || "не указан в кабинете"));
  card.appendChild(kvLine("Сейчас", fmtTraffic(d.used_traffic_bytes, d.lifetime_traffic_bytes)));
  const life = fmtTraffic(d.lifetime_traffic_bytes, d.used_traffic_bytes);
  card.appendChild(kvLine("Всего", life));
  const last = d.last_online_at
    ? fmtAgo(d.last_online_at) + " · " + fmt(d.last_online_at)
    : "нет данных";
  card.appendChild(kvLine("Последний выход", last));
  card.appendChild(
    kvLine(
      "Первый коннект",
      d.first_connected_at ? fmt(d.first_connected_at) + " · " + fmtAgo(d.first_connected_at) : "нет"
    )
  );
  card.appendChild(kvLine("Нода", nodeLine(d.node)));
  card.appendChild(kvLine("User-agent", d.user_agent || "нет"));
  if (d.sub_last_opened_at) {
    card.appendChild(
      kvLine("Подписка открыта", fmtAgo(d.sub_last_opened_at) + " · " + fmt(d.sub_last_opened_at))
    );
  }
  const sessions = Array.isArray(d.sessions) ? d.sessions : [];
  const sessTitle = document.createElement("div");
  sessTitle.className = "dev-sess-title";
  sessTitle.textContent = sessions.length
    ? "Выходы в сеть (HWID): " + sessions.length
    : "HWID-сессий панель не отдала";
  card.appendChild(sessTitle);
  sessions.forEach((s) => {
    const row = document.createElement("div");
    row.className = "hwid-row";
    const main = document.createElement("div");
    main.textContent = [s.platform, s.model].filter(Boolean).join(" · ") || s.hwid || "устройство";
    row.appendChild(main);
    const sub = document.createElement("div");
    sub.className = "who-sub";
    const parts = [];
    if (s.hwid) parts.push(s.hwid);
    if (s.user_agent) parts.push(s.user_agent);
    const seen = s.last_seen_at || s.created_at;
    if (seen) parts.push(fmtAgo(seen) + " · " + fmt(seen));
    sub.textContent = parts.join(" · ") || "без деталей";
    row.appendChild(sub);
    card.appendChild(row);
  });
  return card;
}

async function loadUserDevices(telegramId) {
  const body = $("userDeviceList");
  if (!body) return;
  body.innerHTML = "";
  const wait = document.createElement("p");
  wait.className = "muted";
  wait.textContent = "Загружаю устройства и выходы в сеть...";
  body.appendChild(wait);
  try {
    const data = await api(`/admin/api/users/${encodeURIComponent(String(telegramId))}/devices`);
    body.innerHTML = "";
    const items = data.items || [];
    let latest = null;
    items.forEach((d) => {
      const t = d.last_online_at ? new Date(d.last_online_at).getTime() : 0;
      if (t && (!latest || t > latest.t)) latest = { t, raw: d.last_online_at };
    });
    paintModalOnline(latest ? latest.raw : null);
    if (!items.length) {
      const empty = document.createElement("p");
      empty.className = "muted";
      empty.textContent = "Устройств нет";
      body.appendChild(empty);
      return;
    }
    items.forEach((d) => body.appendChild(paintDeviceCard(d)));
  } catch (_e) {
    body.innerHTML = "";
    const err = document.createElement("p");
    err.className = "muted";
    err.textContent = "Не удалось загрузить устройства";
    body.appendChild(err);
  }
}

async function loadUserBilling(telegramId) {
  const body = $("userBillRows");
  if (!body) return;
  body.innerHTML = "";
  try {
    const data = await api(`/admin/api/billing?telegram_id=${encodeURIComponent(String(telegramId))}&page=1&limit=12`);
    const items = data.items || [];
    if (!items.length) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 4;
      td.className = "muted";
      td.textContent = "Пока пусто";
      tr.appendChild(td);
      body.appendChild(tr);
      return;
    }
    items.forEach((e) => {
      const tr = document.createElement("tr");
      [fmt(e.created_at), billKindLabel(e.kind), billAmount(e.amount), e.balance_after == null ? "—" : `${e.balance_after} ₽`].forEach((t, i) => {
        tr.appendChild(i === 1 ? tdPill(t) : tdText(t));
      });
      if (e.note || e.device_title) tr.title = [e.device_title, e.note].filter(Boolean).join(" · ");
      body.appendChild(tr);
    });
  } catch (_e) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 4;
    td.className = "muted";
    td.textContent = "Не удалось загрузить";
    tr.appendChild(td);
    body.appendChild(tr);
  }
}

function collectTicketFilters() {
  return {
    q: val("ticketQ"),
    status: val("ticketStatus"),
    from: val("ticketFrom"),
    to: val("ticketTo"),
  };
}

function ticketWho(r) {
  return `${r.telegram_id}` + (r.username ? ` @${r.username}` : "") + (r.first_name ? ` · ${r.first_name}` : "");
}

function isTicketImage(att) {
  return (att && att.kind === "photo") || String((att && att.mime) || "").startsWith("image/");
}

function paintTicketAttachments(wrap, atts) {
  if (!wrap || !atts || !atts.length) return;
  const box = document.createElement("div");
  box.className = "ticket-atts";
  atts.forEach((a) => {
    if (isTicketImage(a) && a.url) {
      const link = document.createElement("a");
      link.href = a.url;
      link.target = "_blank";
      link.rel = "noopener";
      const img = document.createElement("img");
      img.className = "ticket-att-img";
      img.alt = a.original_name || "Фото";
      img.src = a.url;
      link.appendChild(img);
      box.appendChild(link);
    } else {
      const link = document.createElement("a");
      link.className = "ticket-att-file";
      link.href = a.url || "#";
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = a.original_name || "Файл";
      box.appendChild(link);
    }
  });
  wrap.appendChild(box);
}

function paintTicketPending() {
  const box = $("ticketAttachList");
  if (!box) return;
  box.innerHTML = "";
  ticketPending.forEach((file, i) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "ticket-attach-chip";
    chip.textContent = file.name || "Файл";
    chip.onclick = () => {
      ticketPending.splice(i, 1);
      paintTicketPending();
    };
    box.appendChild(chip);
  });
}

function paintTicketThread(messages) {
  const box = $("ticketThread");
  if (!box) return;
  box.innerHTML = "";
  if (!messages || !messages.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "Сообщений пока нет";
    box.appendChild(empty);
    return;
  }
  messages.forEach((m) => {
    const wrap = document.createElement("div");
    wrap.className = "ticket-bubble " + (m.author === "admin" ? "admin" : "user");
    const meta = document.createElement("div");
    meta.className = "ticket-bubble-meta";
    meta.textContent = (m.author === "admin" ? "Поддержка" : "Клиент") + " · " + fmt(m.created_at);
    wrap.appendChild(meta);
    if (m.body) {
      const body = document.createElement("div");
      body.className = "ticket-bubble-body";
      body.textContent = m.body;
      wrap.appendChild(body);
    }
    paintTicketAttachments(wrap, m.attachments);
    box.appendChild(wrap);
  });
  box.scrollTop = box.scrollHeight;
}

let ticketPage = 1;
let selectedTicketId = 0;
let ticketPending = [];

async function loadTicket(id) {
  selectedTicketId = Number(id) || 0;
  ticketPending = [];
  paintTicketPending();
  const head = $("ticketHead");
  const meta = $("ticketMeta");
  if (!selectedTicketId) {
    if (head) head.textContent = "Выберите тикет";
    if (meta) meta.textContent = "Ответ появится в чате бота и в кабинете.";
    paintTicketThread([]);
    return;
  }
  let data;
  try {
    data = await api(`/admin/api/tickets/${selectedTicketId}`);
  } catch (_e) {
    if (head) head.textContent = "Не удалось открыть тикет";
    return;
  }
  const t = data.ticket || {};
  if (head) head.textContent = `Тикет #${t.id} · ${TICKET_STATUS_LABEL[t.status] || t.status || ""}`;
  if (meta) meta.textContent = ticketWho(t);
  paintTicketThread(data.messages || []);
  document.querySelectorAll("#ticketRows tr").forEach((tr) => {
    tr.classList.toggle("is-selected", Number(tr.dataset.id) === selectedTicketId);
  });
}

async function loadTickets(page) {
  if (page) ticketPage = page;
  const f = collectTicketFilters();
  const reset = $("ticketReset");
  if (reset) reset.classList.toggle("hidden", !hasAny(f));
  const chips = [];
  if (f.status) chips.push(["status", TICKET_STATUS_LABEL[f.status] || f.status]);
  if (f.q) chips.push(["q", f.q]);
  if (f.from) chips.push(["from", "с " + f.from]);
  if (f.to) chips.push(["to", "по " + f.to]);
  paintChips("ticketChips", chips, (key) => {
    setVal(TICKET_FILTER_IDS[key], "");
    loadTickets(1);
  });
  writeRoute("tickets", new URLSearchParams(Object.entries(f).filter(([, v]) => v)));
  const body = $("ticketRows");
  if (!body) return;
  body.innerHTML = "";
  const labels = ["Номер", "Обновлён", "Пользователь", "Статус", "Последнее"];
  let data;
  try {
    data = await api(`/admin/api/tickets?${queryString({ ...f, page: ticketPage })}`);
  } catch (_e) {
    body.appendChild(emptyRow(5, "Не удалось загрузить тикеты"));
    return;
  }
  if (!data.items.length) {
    body.appendChild(emptyRow(5, hasAny(f) ? "Тикетов не нашли" : "Тикетов пока нет"));
  }
  data.items.forEach((r) => {
    const tr = document.createElement("tr");
    tr.dataset.id = String(r.id);
    tr.style.cursor = "pointer";
    if (Number(r.id) === selectedTicketId) tr.classList.add("is-selected");
    ["#" + r.id, fmt(r.last_message_at || r.created_at), ticketWho(r), TICKET_STATUS_LABEL[r.status] || r.status || "—", msgPreview(r.last_body)].forEach((t) => {
      const td = document.createElement("td");
      td.textContent = t;
      tr.appendChild(td);
    });
    labelRow(tr, labels);
    tr.onclick = () => loadTicket(r.id);
    body.appendChild(tr);
  });
  pager($("ticketPager"), data.page, data.total, data.limit, loadTickets);
  if (selectedTicketId && data.items.some((r) => Number(r.id) === selectedTicketId)) {
    loadTicket(selectedTicketId);
  } else if (!selectedTicketId && data.items.length) {
    loadTicket(data.items[0].id);
  }
}

function collectMsgFilters() {
  return {
    q: val("msgQ"),
    channel: val("msgChannel"),
    source: val("msgSource"),
    kind: val("msgKind"),
    from: val("msgFrom"),
    to: val("msgTo"),
  };
}

function msgPreview(text) {
  const s = String(text || "").replace(/\s+/g, " ").trim();
  if (!s) return "—";
  return s.length > 90 ? s.slice(0, 90) + "…" : s;
}

function msgError(r) {
  if (r && r.error) return String(r.error);
  const extra = r && r.extra;
  if (extra && typeof extra === "object") return String(extra.error || extra.error_raw || "");
  return "";
}

function msgLine(r) {
  if (r.status === "failed") {
    return msgError(r) || "Telegram не принял сообщение. Причина в старых записях не сохранялась.";
  }
  return msgPreview(r.body || r.title);
}

function msgWho(r) {
  if (!r.telegram_id) return "—";
  return `${r.telegram_id}` + (r.username ? ` @${r.username}` : "") + (r.first_name ? ` · ${r.first_name}` : "");
}

let msgPage = 1;
let selectedMsg = null;

function msgCanRetry(r) {
  return Boolean(r && r.status === "failed" && r.telegram_id && r.kind !== "maintenance_hit");
}

function paintMsgDetail(r) {
  selectedMsg = r || null;
  const btn = $("msgRetry");
  if (btn) btn.disabled = !msgCanRetry(r);
  if (!r) {
    $("msgDetail").textContent = "Выберите строку";
    return;
  }
  const reason = r.status === "failed"
    ? "Почему не ушло: " + msgLine(r) + "\n\n"
    : "";
  const extra = r.extra && typeof r.extra === "object" && Object.keys(r.extra).length
    ? "\n\n" + JSON.stringify(r.extra, null, 2)
    : "";
  $("msgDetail").textContent =
    `${r.title || MSG_KIND_LABEL[r.kind] || "Сообщение"}\n${msgWho(r)}\n\n${reason}${r.body || "—"}${extra}`;
}

async function loadMessages(page) {
  if (page) msgPage = page;
  const f = collectMsgFilters();
  const reset = $("msgReset");
  if (reset) reset.classList.toggle("hidden", !hasAny(f));
  const chips = [];
  if (f.channel) chips.push(["channel", MSG_CHANNEL_LABEL[f.channel] || f.channel]);
  if (f.source) chips.push(["source", MSG_SOURCE_LABEL[f.source] || f.source]);
  if (f.kind) chips.push(["kind", MSG_KIND_LABEL[f.kind] || f.kind]);
  if (f.q) chips.push(["q", f.q]);
  if (f.from) chips.push(["from", "с " + f.from]);
  if (f.to) chips.push(["to", "по " + f.to]);
  paintChips("msgChips", chips, (key) => {
    setVal(MSG_FILTER_IDS[key], "");
    loadMessages(1);
  });
  writeRoute("messages", new URLSearchParams(Object.entries(f).filter(([, v]) => v)));
  const body = $("msgRows");
  if (!body) return;
  body.innerHTML = "";
  const labels = ["Время", "Тип", "Источник", "Пользователь", "Статус", "Текст / причина"];
  let data;
  try {
    data = await api(`/admin/api/messages?${queryString({ ...f, page: msgPage })}`);
  } catch (_e) {
    body.appendChild(emptyRow(6, "Не удалось загрузить журнал"));
    return;
  }
  if (!data.items.length) {
    body.appendChild(emptyRow(6, hasAny(f) ? "Сообщений не нашли" : "Журнал пока пуст"));
  }
  data.items.forEach((r) => {
    const tr = document.createElement("tr");
    tr.style.cursor = "pointer";
    tr.dataset.id = String(r.id);
    if (selectedMsg && Number(selectedMsg.id) === Number(r.id)) tr.classList.add("is-selected");
    [
      fmt(r.created_at),
      MSG_KIND_LABEL[r.kind] || r.kind || "—",
      MSG_SOURCE_LABEL[r.source] || r.source || "—",
      msgWho(r),
      MSG_STATUS_LABEL[r.status] || r.status || "—",
      msgLine(r),
    ].forEach((t, i) => {
      const td = document.createElement("td");
      td.textContent = t;
      if (i === 5 && r.status === "failed") td.title = t;
      tr.appendChild(td);
    });
    labelRow(tr, labels);
    tr.onclick = () => {
      body.querySelectorAll("tr.is-selected").forEach((el) => el.classList.remove("is-selected"));
      tr.classList.add("is-selected");
      paintMsgDetail(r);
    };
    body.appendChild(tr);
  });
  if (selectedMsg && !data.items.some((r) => Number(r.id) === Number(selectedMsg.id))) {
    paintMsgDetail(null);
  } else if (selectedMsg) {
    const fresh = data.items.find((r) => Number(r.id) === Number(selectedMsg.id));
    if (fresh) paintMsgDetail(fresh);
  }
  pager($("msgPager"), data.page, data.total, data.limit, loadMessages);
}

async function loadSettings() {
  const s = await api("/admin/api/settings");
  const v = s.values || {};
  const set = (id, val) => {
    const el = $(id);
    if (!el) return;
    if (el.type === "checkbox") el.checked = !!val;
    else el.value = val == null ? "" : String(val);
  };
  set("setBrand", v.brand_name);
  set("setSupport", v.support_username);
  set("setOffer", v.legal_offer_url);
  set("setPrivacy", v.legal_privacy_url);
  set("setLiveChat", v.admin_live_chat_id);
  set("setWelcomeSticker", v.welcome_sticker_file_id);
  const hint = s.live_chat_hint;
  const hintEl = $("liveChatHint");
  const hintBtn = $("liveChatUseHint");
  if (hintEl && hintBtn) {
    if (hint && hint.id) {
      const title = hint.title || "без названия";
      const uname = hint.username ? " @" + hint.username : "";
      hintEl.textContent =
        "Бот уже админ в «" + title + "»" + uname + ". Id " + hint.id + " — это как раз приватный канал.";
      hintEl.classList.remove("hidden");
      hintBtn.classList.remove("hidden");
      hintBtn.onclick = () => {
        if ($("setLiveChat")) $("setLiveChat").value = String(hint.id);
      };
    } else {
      hintEl.textContent = "";
      hintEl.classList.add("hidden");
      hintBtn.classList.add("hidden");
      hintBtn.onclick = null;
    }
  }
  set("setMaxDev", v.max_devices);
  set("setHwid", v.remnawave_hwid_limit);
  set("setDayPrice", v.vpn_day_price_rub);
  set("setTopMin", v.balance_topup_min);
  set("setTopMax", v.balance_topup_max);
  set("setTopStep", v.balance_topup_step);
  set("setRefRub", v.referral_reward_rub);
  set("setRefInviteeRub", v.referral_invitee_reward_rub);
  set("setRefPayoutMin", v.referral_payout_min);
  window.__adminBalanceOn = Boolean(s.balance_enabled);
  const refMode = v.referral_mode || (v.referral_payout_enabled ? "payout" : "classic");
  if ($("setRefModeClassic")) $("setRefModeClassic").checked = refMode !== "payout";
  if ($("setRefModePayout")) $("setRefModePayout").checked = refMode === "payout";
  set("setStoryOn", v.story_reward_enabled);
  set("setStoryRub", v.story_reward_rub);
  set("setStoryCheck", v.story_check_minutes);
  set("setStoryText", v.story_share_text);
  set("setTrustOn", v.trust_enabled);
  set("setTrustDays", v.trust_days);
  set("setTrustFee", v.trust_fee_rub);
  set("setP1", v.plan_1m_rub);
  set("setP3", v.plan_3m_rub);
  set("setP6", v.plan_6m_rub);
  set("setP12", v.plan_12m_rub);
  set("setRefDays", v.referral_reward_days);
  set("setRefInvitee", v.referral_invitee_days);
  set("setTrialOn", v.trial_enabled);
  set("setTrialDays", v.trial_days);
  set("setPromoOn", v.promo_enabled);
  set("setPromo", v.promo_codes);
  renderVpnApps(Array.isArray(v.vpn_apps) ? v.vpn_apps : []);
  renderNotices(s.notice_fields || [], v.notices || {});
  document.querySelectorAll(".shop-balance").forEach((el) => {
    el.classList.toggle("hidden", !s.balance_enabled);
  });
  document.querySelectorAll(".shop-plans").forEach((el) => {
    el.classList.toggle("hidden", !!s.balance_enabled);
  });
  window.__adminBalanceOn = Boolean(s.balance_enabled);
  syncRefModeUi();
}

function syncRefModeUi() {
  const balanceOn = Boolean(window.__adminBalanceOn);
  const payoutEl = $("setRefModePayout");
  if (payoutEl) {
    payoutEl.disabled = !balanceOn;
    if (!balanceOn) {
      payoutEl.checked = false;
      if ($("setRefModeClassic")) $("setRefModeClassic").checked = true;
    }
  }
  const payout = payoutEl && payoutEl.checked;
  const box = $("refPayoutFields");
  if (box) box.classList.toggle("hidden", !payout);
  const note = $("refModeBalanceNote");
  if (note) note.classList.toggle("hidden", balanceOn);
}

const VPN_PLATS = [
  ["ios", "iOS"],
  ["macos", "macOS"],
  ["appletv", "Apple TV"],
  ["android", "Android"],
  ["androidtv", "Android TV"],
  ["windows", "Windows"],
];

function emptyVpnApp() {
  return { id: "", name: "", mark: "", icon: "", deep_link: "", platforms: ["ios"], stores: {} };
}

function renderVpnApps(list) {
  const box = $("vpnAppsList");
  if (!box) return;
  box.innerHTML = "";
  (list.length ? list : [emptyVpnApp()]).forEach((app) => box.appendChild(vpnAppCard(app)));
}

function vpnAppCard(app) {
  const wrap = document.createElement("details");
  wrap.className = "vpn-app panel";
  const sum = document.createElement("summary");
  const platsN = (app.platforms || []).length;
  sum.textContent = (app.name || "Приложение") + " · " + platsN + " платформ";
  wrap.appendChild(sum);
  const body = document.createElement("div");
  body.className = "vpn-app-body";
  const head = document.createElement("div");
  head.className = "vpn-app-head";
  const mk = (cls, placeholder, value, extra) => {
    const el = document.createElement("input");
    el.className = cls;
    el.type = "text";
    el.placeholder = placeholder;
    el.value = value || "";
    if (extra) Object.assign(el, extra);
    return el;
  };
  const nameIn = mk("va-name", "Название", app.name || "", { maxLength: 40 });
  nameIn.oninput = () => {
    const n = wrap.querySelectorAll(".va-plat input[type=checkbox]:checked").length;
    sum.textContent = (nameIn.value || "Приложение") + " · " + n + " платформ";
  };
  head.appendChild(mk("va-id", "id, латиница", app.id || "", { maxLength: 24 }));
  head.appendChild(nameIn);
  head.appendChild(mk("va-mark", "Значок", app.mark || "", { maxLength: 4 }));
  head.appendChild(mk("va-icon", "Иконка /icons/имя.png", app.icon || "", { maxLength: 500 }));
  head.appendChild(mk("va-deep", "happ://add/{url}", app.deep_link || "", { maxLength: 200 }));
  const del = document.createElement("button");
  del.type = "button";
  del.className = "ghost";
  del.textContent = "Убрать";
  del.onclick = (e) => {
    e.preventDefault();
    wrap.remove();
  };
  head.appendChild(del);
  body.appendChild(head);
  const plats = document.createElement("div");
  plats.className = "va-plats";
  const on = new Set(app.platforms || []);
  const stores = app.stores || {};
  VPN_PLATS.forEach(([id, label]) => {
    const row = document.createElement("label");
    row.className = "va-plat";
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.dataset.plat = id;
    cb.checked = on.has(id);
    cb.onchange = () => {
      const n = wrap.querySelectorAll(".va-plat input[type=checkbox]:checked").length;
      sum.textContent = (nameIn.value || "Приложение") + " · " + n + " платформ";
    };
    const name = document.createElement("span");
    name.textContent = label;
    const store = document.createElement("input");
    store.type = "url";
    store.className = "va-store";
    store.dataset.plat = id;
    store.placeholder = "Ссылка магазина";
    store.value = stores[id] || "";
    row.appendChild(cb);
    row.appendChild(name);
    row.appendChild(store);
    plats.appendChild(row);
  });
  body.appendChild(plats);
  wrap.appendChild(body);
  return wrap;
}

function collectVpnApps() {
  return [...document.querySelectorAll("#vpnAppsList .vpn-app")].map((card) => {
    const platforms = [];
    const stores = {};
    card.querySelectorAll(".va-plat").forEach((row) => {
      const cb = row.querySelector("input[type=checkbox]");
      const store = row.querySelector(".va-store");
      if (!cb || !cb.checked) return;
      platforms.push(cb.dataset.plat);
      if (store && store.value.trim()) stores[cb.dataset.plat] = store.value.trim();
    });
    return {
      id: (card.querySelector(".va-id") || {}).value || "",
      name: (card.querySelector(".va-name") || {}).value || "",
      mark: (card.querySelector(".va-mark") || {}).value || "",
      icon: (card.querySelector(".va-icon") || {}).value || "",
      deep_link: (card.querySelector(".va-deep") || {}).value || "",
      platforms,
      stores,
    };
  });
}

$("shopForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  await saveShopSettings();
});
if ($("promoForm")) {
  $("promoForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    await saveShopSettings("promoOut");
  });
}
["setRefModeClassic", "setRefModePayout"].forEach((id) => {
  const el = $(id);
  if (el) el.onchange = syncRefModeUi;
});
syncRefModeUi();
if ($("refModeSave")) {
  $("refModeSave").onclick = () => saveShopSettings("refModeOut");
}

async function saveShopSettings(outId) {
  const num = (id) => Number($(id).value);
  const payload = {
    brand_name: $("setBrand").value,
    support_username: $("setSupport").value,
    legal_offer_url: $("setOffer").value,
    legal_privacy_url: $("setPrivacy").value,
    admin_live_chat_id: $("setLiveChat") ? $("setLiveChat").value : "",
    welcome_sticker_file_id: $("setWelcomeSticker") ? $("setWelcomeSticker").value : "",
    max_devices: num("setMaxDev"),
    remnawave_hwid_limit: num("setHwid"),
    vpn_day_price_rub: num("setDayPrice"),
    balance_topup_min: num("setTopMin"),
    balance_topup_max: num("setTopMax"),
    balance_topup_step: num("setTopStep"),
    referral_reward_rub: num("setRefRub"),
    referral_invitee_reward_rub: $("setRefInviteeRub") ? num("setRefInviteeRub") : 0,
    referral_mode: $("setRefModePayout") && $("setRefModePayout").checked ? "payout" : "classic",
    referral_payout_enabled: Boolean($("setRefModePayout") && $("setRefModePayout").checked),
    referral_payout_min: $("setRefPayoutMin") && $("setRefPayoutMin").value
      ? num("setRefPayoutMin")
      : 2000,
    story_reward_enabled: $("setStoryOn").checked,
    story_reward_rub: num("setStoryRub"),
    story_check_minutes: num("setStoryCheck"),
    story_share_text: $("setStoryText").value,
    trust_enabled: $("setTrustOn").checked,
    trust_days: num("setTrustDays"),
    trust_fee_rub: num("setTrustFee"),
    plan_1m_rub: num("setP1"),
    plan_3m_rub: num("setP3"),
    plan_6m_rub: num("setP6"),
    plan_12m_rub: num("setP12"),
    referral_reward_days: num("setRefDays"),
    referral_invitee_days: num("setRefInvitee"),
    trial_enabled: $("setTrialOn").checked,
    trial_days: num("setTrialDays"),
    promo_enabled: $("setPromoOn").checked,
    promo_codes: $("setPromo").value,
    vpn_apps: collectVpnApps(),
    notices: collectNotices(),
  };
  const out = $(outId || "shopOut");
  const other = outId === "promoOut" ? $("shopOut") : $("promoOut");
  if (out) out.textContent = "Сохраняю...";
  try {
    await api("/admin/api/settings", { method: "POST", body: JSON.stringify(payload) });
    if (out) out.textContent = "Сохранено. Кабинет и бот уже берут новые значения.";
    if (other) other.textContent = "";
    toast("Настройки сохранены");
    await loadSettings();
  } catch (err) {
    if (out) out.textContent = err.message || "Не удалось сохранить";
  }
}

$("vpnAppAdd").onclick = () => {
  const box = $("vpnAppsList");
  if (box) box.appendChild(vpnAppCard(emptyVpnApp()));
};

function renderNotices(fields, values) {
  const box = $("noticesList");
  if (!box) return;
  box.innerHTML = "";
  (fields || []).forEach((field) => {
    const wrap = document.createElement("div");
    wrap.className = "notice-field";
    const lab = document.createElement("label");
    lab.className = "ops-label";
    lab.textContent = field.title || field.key;
    const ta = document.createElement("textarea");
    ta.dataset.notice = field.key;
    ta.rows = 4;
    ta.value = values[field.key] || "";
    wrap.appendChild(lab);
    if (field.hint) {
      const hint = document.createElement("p");
      hint.className = "muted tight";
      hint.textContent = "Плейсхолдеры: " + field.hint;
      wrap.appendChild(hint);
    }
    wrap.appendChild(ta);
    box.appendChild(wrap);
  });
}

function collectNotices() {
  const out = {};
  document.querySelectorAll("#noticesList [data-notice]").forEach((el) => {
    out[el.dataset.notice] = el.value;
  });
  return out;
}

function openUser(u) {
  currentUser = u;
  $("modalTitle").textContent = u.first_name || String(u.telegram_id);
  $("modalMeta").textContent =
    `ID ${u.telegram_id}` +
    (u.username ? ` · @${u.username}` : "") +
    (u.balance_rub == null ? "" : ` · баланс ${u.balance_rub} рублей`) +
    (u.referred_by
      ? ` · пригласил ${whoLabel(u.referred_by, u.referrer_username, u.referrer_name)}`
      : " · пришёл без рефссылки") +
    ` · пригласил друзей: ${u.invited_count || 0}` +
    (u.blocked_at ? " · заблокирован в магазине" : "") +
    (u.bot_blocked_at ? " · заблокировал бота" : "");
  paintModalPaid(u);
  $("blockBtn").textContent = u.blocked_at ? "Разблокировать" : "Заблокировать";
  $("blockBtn").className = u.blocked_at ? "ghost" : "danger";
  paintModalOnline(u.last_online_at);
  setModalPane("act");
  $("modal").classList.remove("hidden");
  loadUserDevices(u.telegram_id);
  loadUserBilling(u.telegram_id);
}

async function refreshOpenUser() {
  await loadUsers();
  if (!currentUser) return;
  const u = lastUserItems.find((x) => x.telegram_id === currentUser.telegram_id);
  if (!u) return;
  currentUser = u;
  $("modalTitle").textContent = u.first_name || String(u.telegram_id);
  $("modalMeta").textContent =
    `ID ${u.telegram_id}` +
    (u.username ? ` · @${u.username}` : "") +
    (u.balance_rub == null ? "" : ` · баланс ${u.balance_rub} рублей`) +
    (u.referred_by
      ? ` · пригласил ${whoLabel(u.referred_by, u.referrer_username, u.referrer_name)}`
      : " · пришёл без рефссылки") +
    ` · пригласил друзей: ${u.invited_count || 0}` +
    (u.blocked_at ? " · заблокирован в магазине" : "") +
    (u.bot_blocked_at ? " · заблокировал бота" : "");
  paintModalPaid(u);
  $("blockBtn").textContent = u.blocked_at ? "Разблокировать" : "Заблокировать";
  $("blockBtn").className = u.blocked_at ? "ghost" : "danger";
  paintModalOnline(u.last_online_at);
  loadUserDevices(u.telegram_id);
  loadUserBilling(u.telegram_id);
}

$("loginForm").onsubmit = async (e) => {
  e.preventDefault();
  $("loginErr").classList.add("hidden");
  try {
    await api("/admin/api/login", {
      method: "POST",
      body: JSON.stringify({ password: $("password").value }),
    }).then((s) => {
      $("brand").textContent = s.brand || "Админка";
    });
    showShell();
    switchTab(tabFromHash());
  } catch (err) {
    $("loginErr").textContent = err.message;
    $("loginErr").classList.remove("hidden");
  }
};

$("logout").onclick = async () => {
  await api("/admin/api/logout", { method: "POST", body: "{}" });
  showLogin();
};

document.querySelectorAll("nav [data-tab], .bottom-nav [data-tab]").forEach((b) => {
  b.onclick = () => switchTab(b.dataset.tab);
});
document.querySelectorAll("#setNav [data-jump]").forEach((b) => {
  b.onclick = () => {
    const el = $(b.dataset.jump);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  };
});
if ($("setNavSelect")) {
  $("setNavSelect").onchange = () => {
    const el = $($("setNavSelect").value);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  };
}
document.querySelectorAll("#modalTabs [data-pane]").forEach((b) => {
  b.onclick = () => setModalPane(b.dataset.pane);
});
["flagMaint", "flagBill", "flagNudge", "flagInvite", "flagInfo", "flagStory"].forEach((id) => {
  const el = $(id);
  if (el) {
    el.onclick = () => {
      switchTab("overview");
      setOverviewDash("check");
    };
  }
});
document.querySelectorAll("#overviewDash [data-dash]").forEach((b) => {
  b.onclick = () => setOverviewDash(b.dataset.dash);
});
if ($("problemsBadge")) {
  $("problemsBadge").onclick = () => {
    switchTab("overview");
    setOverviewDash("issues");
  };
}
document.querySelectorAll(".funnel-seg[data-funnel-card]").forEach((seg) => {
  seg.querySelectorAll("[data-funnel]").forEach((b) => {
    b.onclick = () => {
      const card = seg.dataset.funnelCard;
      const period = b.dataset.funnel;
      if (!FUNNEL_PERIODS.includes(period)) return;
      funnelPeriods[card] = period;
      localStorage.setItem("way-funnel-" + card, period);
      if (card === "main") {
        funnelPeriod = period;
        localStorage.setItem("way-funnel-period", period);
      }
      syncOverviewHash();
      paintFunnel(funnelCache);
      if (lastStats) paintKpiStrip(lastStats);
      if (lastStats) paintStatusAlert(lastStats);
      if (card === "main") loadFunnelClients();
    };
  });
});
$("navToggle").onclick = () => setNavOpen(!document.body.classList.contains("nav-open"));
$("navScrim").onclick = () => setNavOpen(false);
if ($("themeToggle")) $("themeToggle").onclick = toggleTheme;
if ($("loginThemeToggle")) $("loginThemeToggle").onclick = toggleTheme;
if ($("sidebarCollapse")) {
  $("sidebarCollapse").onclick = () =>
    setSidebarCollapsed(!document.documentElement.classList.contains("sidebar-collapsed"));
}
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    if ($("confirmDlg") && !$("confirmDlg").classList.contains("hidden")) {
      $("confirmCancel").click();
      return;
    }
    if (!$("modal").classList.contains("hidden")) {
      closeModal();
      return;
    }
    setNavOpen(false);
    return;
  }
  const tag = (e.target && e.target.tagName) || "";
  if (e.key === "/" && !e.metaKey && !e.ctrlKey && !e.altKey && tag !== "INPUT" && tag !== "TEXTAREA") {
    e.preventDefault();
    const tab = tabFromHash();
    const map = { users: "userQ", referrals: "refQ", orders: "orderQ", billing: "billQ", tickets: "ticketQ" };
    const id = map[tab];
    if (id && $(id)) $(id).focus();
  }
});
window.addEventListener("hashchange", () => {
  if (skipHashWrite) return;
  switchTab(tabFromHash(), { skipHash: true });
});
window.addEventListener("resize", () => {
  if (window.matchMedia("(min-width: 901px)").matches) setNavOpen(false);
});
$("userSearch").onclick = () => {
  selectedUsers.clear();
  loadUsers(1);
};
if ($("userReset")) {
  $("userReset").onclick = () => {
    ["userQ", "userStatus", "userTrial", "userDevices", "userOnline", "userPaid", "userBalSign", "userBalMin", "userBalMax", "userFrom", "userTo"].forEach((id) => setVal(id, ""));
    selectedUsers.clear();
    loadUsers(1);
  };
}
$("orderSearch").onclick = () => loadOrders(1);
if ($("orderReset")) {
  $("orderReset").onclick = () => {
    ["orderQ", "orderStatus", "orderFrom", "orderTo"].forEach((id) => setVal(id, ""));
    loadOrders(1);
  };
}
$("billSearch").onclick = () => loadBilling(1);
if ($("billReset")) {
  $("billReset").onclick = () => {
    ["billQ", "billKind", "billSource", "billFrom", "billTo"].forEach((id) => setVal(id, ""));
    loadBilling(1);
  };
}
$("refSearch").onclick = () => loadReferrals(1);
if ($("adCreate")) {
  $("adCreate").onclick = async () => {
    const out = $("adOut");
    try {
      const data = await api("/admin/api/ads", {
        method: "POST",
        body: JSON.stringify({ title: val("adTitle"), slug: val("adSlug") }),
      });
      setVal("adTitle", "");
      setVal("adSlug", "");
      if (out) out.textContent = "Готово. Ссылка скопирована.";
      try {
        await navigator.clipboard.writeText(data.item.url);
      } catch (_e) {
        if (out) out.textContent = data.item.url;
      }
      toast("Ссылка скопирована");
      loadAds();
    } catch (err) {
      if (out) out.textContent = err.message || "Не удалось создать";
    }
  };
}
if ($("adShowArchived")) $("adShowArchived").onchange = () => loadAds();
if ($("refReset")) {
  $("refReset").onclick = () => {
    ["refQ", "refReward", "refFrom", "refTo"].forEach((id) => setVal(id, ""));
    loadReferrals(1);
  };
}
if ($("paySearch")) $("paySearch").onclick = () => loadPayouts(1);
if ($("payReset")) {
  $("payReset").onclick = () => {
    ["payQ", "payStatus"].forEach((id) => setVal(id, ""));
    loadPayouts(1);
  };
}
if ($("payQ")) $("payQ").oninput = debounce(() => loadPayouts(1), 300);
if ($("payStatus")) $("payStatus").onchange = () => loadPayouts(1);
const userReload = debounce(() => {
  selectedUsers.clear();
  loadUsers(1);
}, 300);
$("userQ").oninput = userReload;
["userStatus", "userTrial", "userDevices", "userOnline", "userPaid", "userBalSign", "userBalMin", "userBalMax", "userFrom", "userTo"].forEach((id) => {
  const el = $(id);
  if (el) el.onchange = userReload;
});
$("orderQ").oninput = debounce(() => loadOrders(1), 300);
["orderStatus", "orderFrom", "orderTo"].forEach((id) => {
  const el = $(id);
  if (el) el.onchange = () => loadOrders(1);
});
$("billQ").oninput = debounce(() => loadBilling(1), 300);
["billKind", "billSource", "billFrom", "billTo"].forEach((id) => {
  const el = $(id);
  if (el) el.onchange = () => loadBilling(1);
});
$("refQ").oninput = debounce(() => loadReferrals(1), 300);
["refReward", "refFrom", "refTo"].forEach((id) => {
  const el = $(id);
  if (el) el.onchange = () => loadReferrals(1);
});
if ($("ticketSearch")) $("ticketSearch").onclick = () => loadTickets(1);
if ($("ticketReset")) {
  $("ticketReset").onclick = () => {
    Object.values(TICKET_FILTER_IDS).forEach((id) => setVal(id, ""));
    loadTickets(1);
  };
}
if ($("ticketQ")) {
  $("ticketQ").oninput = debounce(() => loadTickets(1), 300);
  $("ticketQ").onkeydown = (e) => {
    if (e.key === "Enter") loadTickets(1);
  };
}
["ticketStatus", "ticketFrom", "ticketTo"].forEach((id) => {
  const el = $(id);
  if (el) el.onchange = () => loadTickets(1);
});
if ($("ticketFiles")) {
  $("ticketFiles").onchange = (e) => {
    Array.from(e.target.files || []).forEach((file) => {
      if (ticketPending.length >= 5) return;
      ticketPending.push(file);
    });
    paintTicketPending();
    e.target.value = "";
  };
}
if ($("ticketSend")) {
  $("ticketSend").onclick = async () => {
    if (!selectedTicketId) return;
    const text = val("ticketReply");
    if (!text && !ticketPending.length) {
      toast("Напишите ответ или прикрепите файл");
      return;
    }
    try {
      const fd = new FormData();
      fd.append("action", "reply");
      fd.append("text", text);
      ticketPending.forEach((file) => fd.append("files", file, file.name));
      await api(`/admin/api/tickets/${selectedTicketId}`, {
        method: "POST",
        body: fd,
      });
      $("ticketReply").value = "";
      ticketPending = [];
      paintTicketPending();
      toast("Ответ отправлен");
      await loadTickets();
      await loadTicket(selectedTicketId);
    } catch (err) {
      toast(err.message || "Не удалось ответить");
    }
  };
}
if ($("ticketClose")) {
  $("ticketClose").onclick = async () => {
    if (!selectedTicketId) return;
    const ok = await confirmAction("Закрыть тикет", "Пользователь получит сообщение, что тикет закрыт.", false);
    if (!ok) return;
    try {
      await api(`/admin/api/tickets/${selectedTicketId}`, {
        method: "POST",
        body: JSON.stringify({ action: "close" }),
      });
      toast("Тикет закрыт");
      await loadTickets();
      await loadTicket(selectedTicketId);
    } catch (err) {
      toast(err.message || "Не удалось закрыть");
    }
  };
}
if ($("msgSearch")) $("msgSearch").onclick = () => loadMessages(1);
if ($("msgReset")) {
  $("msgReset").onclick = () => {
    Object.values(MSG_FILTER_IDS).forEach((id) => setVal(id, ""));
    loadMessages(1);
  };
}
if ($("msgQ")) {
  $("msgQ").oninput = debounce(() => loadMessages(1), 300);
  $("msgQ").onkeydown = (e) => {
    if (e.key === "Enter") loadMessages(1);
  };
}
["msgChannel", "msgSource", "msgKind", "msgFrom", "msgTo"].forEach((id) => {
  const el = $(id);
  if (el) el.onchange = () => loadMessages(1);
});
if ($("msgRetry")) {
  $("msgRetry").onclick = async () => {
    if (!msgCanRetry(selectedMsg)) return;
    const who = msgWho(selectedMsg);
    if (!(await confirmAction("Отправить снова", `Отправить сообщение ${who}?`))) return;
    try {
      await api(`/admin/api/messages/${selectedMsg.id}/retry`, { method: "POST", body: "{}" });
      toast("Отправлено");
      paintMsgDetail(null);
      await loadMessages();
    } catch (err) {
      toast(err.message || "Не удалось отправить");
      await loadMessages();
    }
  };
}
if ($("msgRetryFailed")) {
  $("msgRetryFailed").onclick = async () => {
    if (
      !(await confirmAction(
        "Повторить ошибки",
        "Отправить снова все ошибки по текущему фильтру? За раз не больше 80."
      ))
    ) {
      return;
    }
    try {
      const r = await api(`/admin/api/messages/retry-failed?${queryString(collectMsgFilters())}`, {
        method: "POST",
        body: "{}",
      });
      const extra = r.capped ? ` (из ${r.total}, лимит 80)` : "";
      toast(`Ушло ${r.sent}, ошибок ${r.failed}${extra}`);
      paintMsgDetail(null);
      await loadMessages();
    } catch (err) {
      toast(err.message || "Не удалось повторить");
      await loadMessages();
    }
  };
}
$("userQ").onkeydown = (e) => {
  if (e.key === "Enter") {
    selectedUsers.clear();
    loadUsers(1);
  }
};
$("userSelectAll").onchange = () => {
  const on = $("userSelectAll").checked;
  lastUserItems.forEach((u) => {
    if (on) selectedUsers.add(u.telegram_id);
    else selectedUsers.delete(u.telegram_id);
  });
  loadUsers();
};
$("bulkBlock").onclick = () => {
  const ids = [...selectedUsers];
  if (!ids.length) {
    $("bulkOut").textContent = "Никого не выбрано";
    return;
  }
  runBulk(
    { action: "block", ids },
    `Заблокировать ${ids.length} пользователей? VPN отключится, бот и кабинет станут недоступны. Админы пропускаются.`
  );
};
$("bulkUnblock").onclick = () => {
  const ids = [...selectedUsers];
  if (!ids.length) {
    $("bulkOut").textContent = "Никого не выбрано";
    return;
  }
  runBulk(
    { action: "unblock", ids },
    `Разблокировать ${ids.length} пользователей?`
  );
};
$("bulkDelete").onclick = () => {
  const ids = [...selectedUsers];
  if (!ids.length) {
    $("bulkOut").textContent = "Никого не выбрано";
    return;
  }
  runBulk(
    { action: "delete", ids },
    `Удалить ${ids.length} пользователей? Доступ в панели будет отключён. Админы из списка пропускаются.`
  );
};
$("bulkTrial").onclick = () => {
  const ids = [...selectedUsers];
  if (!ids.length) {
    $("bulkOut").textContent = "Никого не выбрано";
    return;
  }
  runBulk({ action: "trial_reset", ids }, `Сбросить бесплатный период у ${ids.length} пользователей?`);
};
$("bulkReissue").onclick = () => {
  const ids = [...selectedUsers];
  if (!ids.length) {
    $("bulkOut").textContent = "Никого не выбрано";
    return;
  }
  runBulk(
    { action: "reissue", ids },
    `Перевыпустить ссылки у ${ids.length} пользователей? Старые перестанут работать, в кабинете будут новые, уйдёт уведомление.`
  );
};
$("bulkMsg").onclick = () => {
  const ids = [...selectedUsers];
  if (!ids.length) {
    $("bulkOut").textContent = "Никого не выбрано";
    return;
  }
  const text = window.prompt("Текст сообщения выбранным:");
  if (text == null) return;
  if (!String(text).trim()) {
    $("bulkOut").textContent = "Пустой текст";
    return;
  }
  runBulk(
    { action: "message", ids, text: String(text).trim() },
    `Отправить сообщение ${ids.length} пользователям?`
  );
};
if ($("bulkLkLink")) {
  $("bulkLkLink").onclick = () => {
    const ids = [...selectedUsers];
    if (!ids.length) {
      $("bulkOut").textContent = "Никого не выбрано";
      return;
    }
    runBulk(
      { action: "cabinet_link", ids },
      `Отправить ссылку на кабинет в браузере ${ids.length} пользователям? Старый токен перестанет действовать.`
    );
  };
}
$("bulkDeleteMatch").onclick = () => {
  const f = collectUserFilters();
  const label = hasAny(f) ? "по текущим фильтрам" : "всех в базе";
  runBulk(
    { action: "delete", all_matching: true, ...f },
    `Удалить ${label}? Не больше 500 за раз. Админы пропускаются.`
  );
};
if ($("purgeBotBlockers")) {
  $("purgeBotBlockers").onclick = async () => {
    if (
      !(await confirmAction(
        "Удалить блок бота без триала",
        "Удалит пользователей, которые заблокировали бота и не взяли триал. Если за них уже выплатили рефералку, сумма спишется у пригласившего. За раз не больше 200."
      ))
    ) {
      return;
    }
    try {
      const r = await api("/admin/api/users/purge-bot-blockers", { method: "POST", body: "{}" });
      const extra = r.remaining ? `. Осталось ${r.remaining}, нажмите ещё раз.` : "";
      toast(`Удалено ${r.deleted}, возвратов ${r.clawed}${extra}`);
      loadStats();
      loadUsers();
    } catch (err) {
      toast(err.message || "Не удалось удалить");
    }
  };
}
$("orderQ").onkeydown = (e) => {
  if (e.key === "Enter") loadOrders(1);
};
$("billQ").onkeydown = (e) => {
  if (e.key === "Enter") loadBilling(1);
};
$("refQ").onkeydown = (e) => {
  if (e.key === "Enter") loadReferrals(1);
};

let bcPoll = 0;
let bcPreviews = { invite: "", unused: "" };
let bcAudiences = { all: 0, using: 0, unused: 0 };

function bcTpl() {
  const el = document.querySelector('input[name="bcTpl"]:checked');
  return (el && el.value) || "custom";
}

function paintBroadcastAudience() {
  const tpl = bcTpl();
  const wrap = $("bcAudienceWrap");
  const ta = $("broadcastText");
  if (wrap) wrap.classList.toggle("hidden", tpl !== "custom");
  const audience = tpl === "invite"
    ? "using"
    : tpl === "unused"
      ? "unused"
      : (($("bcAudience") && $("bcAudience").value) || "all");
  const n = Number(bcAudiences[audience] || 0);
  const labels = {
    all: "всем незаблокированным",
    using: "тем, у кого есть устройство",
    unused: "тем, у кого нет устройств",
  };
  if ($("broadcastCount")) {
    $("broadcastCount").textContent = `Уйдёт ${n} пользователям (${labels[audience] || "выбранным"}).`;
  }
  if ($("bcCountInvite")) $("bcCountInvite").textContent = "Получатели: " + (bcAudiences.using || 0);
  if ($("bcCountUnused")) $("bcCountUnused").textContent = "Получатели: " + (bcAudiences.unused || 0);
  if ($("bcCountCustom")) $("bcCountCustom").textContent = "Получатели: " + (bcAudiences[($("bcAudience") && $("bcAudience").value) || "all"] || 0);
  if (ta) {
    if (tpl === "invite" || tpl === "unused") {
      ta.value = bcPreviews[tpl] || "";
      ta.readOnly = true;
    } else {
      ta.readOnly = false;
    }
  }
  if ($("broadcastPreview")) {
    $("broadcastPreview").textContent = (ta && ta.value.trim()) || "Превью сообщения";
  }
}

function paintBroadcastJob(j) {
  const out = $("broadcastOut");
  const btn = $("broadcastBtn");
  const bulkBtn = $("bulkMsg");
  const bulkOut = $("bulkOut");
  if (btn) btn.disabled = !!j.running;
  if (bulkBtn) bulkBtn.disabled = !!j.running;
  if (j.audiences) bcAudiences = j.audiences;
  if (j.previews) bcPreviews = { ...bcPreviews, ...j.previews };
  const progress = () => {
    const total = j.total || 0;
    return total
      ? `Идёт: ${j.sent || 0} из ${total}` + (j.failed ? `, ошибок ${j.failed}` : "")
      : "Запущено, собираю получателей...";
  };
  if (out) {
    if (j.running) out.textContent = progress();
    else if (j.message) out.textContent = j.message;
  }
  if (bulkOut && j.scope === "selected" && !j.template) {
    if (j.running) bulkOut.textContent = progress();
    else if (j.message) bulkOut.textContent = j.message;
  }
  paintBroadcastAudience();
}

async function loadBroadcastJob() {
  try {
    const j = await api("/admin/api/broadcast");
    paintBroadcastJob(j);
    if (j.running) {
      if (bcPoll) clearTimeout(bcPoll);
      bcPoll = setTimeout(loadBroadcastJob, 1000);
    }
  } catch (_e) {
    /* ignore */
  }
}

$("broadcastBtn").onclick = async () => {
  const tpl = bcTpl();
  let payload;
  let title = "Рассылка";
  let lead = "";
  if (tpl === "invite" || tpl === "unused") {
    const n = tpl === "invite" ? bcAudiences.using : bcAudiences.unused;
    payload = { template: tpl };
    title = tpl === "invite" ? "Пользуются VPN" : "Не подключались";
    lead = `Сообщение уйдёт ${n || 0} пользователям. Отменить рассылку нельзя.`;
  } else {
    const text = $("broadcastText").value.trim();
    if (!text) {
      $("broadcastOut").textContent = "Введите текст";
      return;
    }
    const audience = ($("bcAudience") && $("bcAudience").value) || "all";
    payload = { text, audience };
    const n = bcAudiences[audience] || 0;
    lead = `Сообщение уйдёт ${n} пользователям. Отменить рассылку нельзя.`;
  }
  if (!(await confirmAction(title, lead))) return;
  $("broadcastOut").textContent = "Запускаю...";
  try {
    await api("/admin/api/broadcast", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    toast("Рассылка запущена");
    loadBroadcastJob();
  } catch (err) {
    $("broadcastOut").textContent = err.message;
  }
};

function fmtSize(n) {
  if (n < 1024) return `${n} Б`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} КБ`;
  return `${(n / 1024 / 1024).toFixed(1)} МБ`;
}

function fmtWait(sec) {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  return `${h} ч ${m} мин`;
}

async function loadBackups() {
  const data = await api("/admin/api/backups");
  $("backupOut").textContent =
    `Следующий автобэкап через ${fmtWait(data.next_in_sec || 0)}. Храним ${data.keep_days} дн.`;
  const body = $("backupRows");
  body.innerHTML = "";
  if (!data.items.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 4;
    td.className = "muted";
    td.textContent = "Файлов пока нет";
    tr.appendChild(td);
    body.appendChild(tr);
    return;
  }
  data.items.forEach((item) => {
    const tr = document.createElement("tr");
    [item.name, fmtSize(item.size), fmt(item.created_at)].forEach((t) => {
      const td = document.createElement("td");
      td.textContent = t;
      tr.appendChild(td);
    });
    const td = document.createElement("td");
    const a = document.createElement("a");
    a.href = `/admin/api/backups/${encodeURIComponent(item.name)}`;
    a.textContent = "Скачать";
    td.appendChild(a);
    a.style.marginRight = "10px";
    const rest = document.createElement("button");
    rest.type = "button";
    rest.className = "ghost";
    rest.textContent = "Восстановить";
    rest.onclick = () => restoreBackup({ name: item.name });
    td.appendChild(rest);
    tr.appendChild(td);
    labelRow(tr, ["Файл", "Размер", "Создан", ""]);
    body.appendChild(tr);
  });
}

$("backupBtn").onclick = async () => {
  $("backupOut").textContent = "Создаю бэкап...";
  $("backupBtn").disabled = true;
  try {
    const r = await api("/admin/api/backups", { method: "POST", body: "{}" });
    await loadBackups();
    $("backupOut").textContent =
      `Готово: ${r.name} (${fmtSize(r.size)}).`;
  } catch (err) {
    $("backupOut").textContent = err.message || "Не удалось сделать бэкап";
  }
  $("backupBtn").disabled = false;
};

async function restoreBackup(opts) {
  const warn =
    "Текущая база будет полностью заменена данными из бэкапа. Продолжить?";
  if (!(await confirmAction("Восстановление базы", warn))) return;
  $("restoreOut").textContent = "Восстанавливаю...";
  try {
    let data;
    if (opts.file) {
      const fd = new FormData();
      fd.append("file", opts.file);
      const res = await fetch("/admin/api/backups/restore", {
        method: "POST",
        credentials: "same-origin",
        body: fd,
      });
      data = await res.json().catch(() => ({ ok: false, error: "Ошибка ответа" }));
      if (!res.ok || data.ok === false) throw new Error(data.error || "Ошибка импорта");
    } else {
      data = await api("/admin/api/backups/restore", {
        method: "POST",
        body: JSON.stringify({ name: opts.name }),
      });
    }
    await loadBackups();
    $("restoreOut").textContent = `База восстановлена из ${data.filename}.`;
  } catch (err) {
    $("restoreOut").textContent = err.message || "Не удалось восстановить";
  }
}

$("restoreUploadBtn").onclick = () => {
  const input = $("backupFile");
  const file = input.files && input.files[0];
  if (!file) {
    $("restoreOut").textContent = "Выберите файл .sql или .sql.gz";
    return;
  }
  restoreBackup({ file });
};

$("grantBtn").onclick = async () => {
  if (!currentUser) return;
  await api(`/admin/api/users/${currentUser.telegram_id}/grant`, {
    method: "POST",
    body: JSON.stringify({ days: Number($("grantDays").value) }),
  });
  toast("Дни начислены");
  await refreshOpenUser();
};
$("balBtn").onclick = async () => {
  if (!currentUser) return;
  await api(`/admin/api/users/${currentUser.telegram_id}/balance`, {
    method: "POST",
    body: JSON.stringify({ amount: Number($("balAmount").value) }),
  });
  toast("Баланс изменён");
  await refreshOpenUser();
};
$("delBtn").onclick = async () => {
  if (!currentUser) return;
  const id = currentUser.telegram_id;
  if (!(await confirmAction("Удалить пользователя", `Удалить пользователя ${id}? Доступ в панели будет отключён.`))) return;
  await api(`/admin/api/users/${id}/delete`, { method: "POST", body: "{}" });
  closeModal();
  loadUsers();
};
$("trialBtn").onclick = async () => {
  if (!currentUser) return;
  await api(`/admin/api/users/${currentUser.telegram_id}/trial-reset`, {
    method: "POST",
    body: "{}",
  });
  toast("Триал сброшен");
  await refreshOpenUser();
};
$("blockBtn").onclick = async () => {
  if (!currentUser) return;
  const on = !currentUser.blocked_at;
  const msg = on
    ? `Заблокировать ${currentUser.telegram_id}? VPN отключится, бот и кабинет станут недоступны.`
    : `Разблокировать ${currentUser.telegram_id}?`;
  if (!(await confirmAction(on ? "Блокировка" : "Разблокировка", msg))) return;
  await api(`/admin/api/users/${currentUser.telegram_id}/block`, {
    method: "POST",
    body: JSON.stringify({ blocked: on }),
  });
  toast(on ? "Заблокирован" : "Разблокирован");
  await refreshOpenUser();
};
$("msgBtn").onclick = async () => {
  if (!currentUser) return;
  await api(`/admin/api/users/${currentUser.telegram_id}/message`, {
    method: "POST",
    body: JSON.stringify({ text: $("msgText").value }),
  });
  $("msgText").value = "";
  toast("Сообщение отправлено");
};
if ($("lkLinkBtn")) {
  $("lkLinkBtn").onclick = async () => {
    if (!currentUser) return;
    if (
      !(await confirmAction(
        "Ссылка на кабинет",
        "Отправить ссылку на кабинет в браузере? Действует 10 дней. Старый токен перестанет работать."
      ))
    ) {
      return;
    }
    try {
      await api(`/admin/api/users/${currentUser.telegram_id}/cabinet-link`, {
        method: "POST",
        body: "{}",
      });
      toast("Ссылка отправлена");
    } catch (err) {
      toast(err.message || "Не удалось отправить ссылку");
    }
  };
}
$("modalClose").onclick = closeModal;
$("modal").onclick = (e) => {
  if (e.target === $("modal")) closeModal();
};

$("maintBtn").onclick = async () => {
  try {
    const f = await api("/admin/api/flags");
    const next = !f.maintenance;
    if (!next) {
      paintFlags(await api("/admin/api/flags", { method: "POST", body: JSON.stringify({ maintenance: false }) }));
      return;
    }
    const message = $("maintNotice").value.trim();
    if (!message) {
      $("opsHint").textContent = "Сначала сохраните текст оповещения.";
      $("maintNotice").focus();
      return;
    }
    if (!(await confirmAction("Тех. работы", "Включить тех. работы? На любое действие в боте уйдут сохранённые текст и картинка."))) return;
    const r = await api("/admin/api/flags", {
      method: "POST",
      body: JSON.stringify({ maintenance: true, message }),
    });
    paintFlags(r);
    $("opsHint").textContent =
      "Тех. работы включены: на любое действие в боте уходят сохранённые текст и картинка.";
  } catch (err) {
    $("opsHint").textContent = err.message || "Не удалось включить тех. работы";
  }
};

$("maintSaveBtn").onclick = async () => {
  const message = $("maintNotice").value.trim();
  if (!message) {
    $("opsHint").textContent = "Введите текст оповещения.";
    return;
  }
  $("opsHint").textContent = "Сохраняю...";
  try {
    const fd = new FormData();
    fd.append("message", message);
    const file = $("maintPhoto").files && $("maintPhoto").files[0];
    if (file) fd.append("file", file);
    const res = await fetch("/admin/api/maintenance", {
      method: "POST",
      credentials: "same-origin",
      body: fd,
    });
    const data = await res.json().catch(() => ({ ok: false, error: "Ошибка ответа" }));
    if (!res.ok || data.ok === false) throw new Error(data.error || "Не удалось сохранить");
    $("maintPhoto").value = "";
    paintFlags(data);
    $("opsHint").textContent = "Текст и картинка сохранены. Их можно включить кнопкой тех. работ.";
  } catch (err) {
    $("opsHint").textContent = err.message || "Не удалось сохранить";
  }
};

$("maintPhotoDel").onclick = async () => {
  if (!(await confirmAction("Картинка", "Удалить сохранённую картинку?"))) return;
  try {
    const res = await fetch("/admin/api/maintenance/photo", {
      method: "DELETE",
      credentials: "same-origin",
    });
    const data = await res.json().catch(() => ({ ok: false, error: "Ошибка ответа" }));
    if (!res.ok || data.ok === false) throw new Error(data.error || "Не удалось удалить");
    const f = await api("/admin/api/flags");
    paintFlags(f);
    $("opsHint").textContent = "Картинка удалена. Текст остался.";
  } catch (err) {
    $("opsHint").textContent = err.message || "Не удалось удалить картинку";
  }
};

$("billBtn").onclick = async () => {
  const f = await api("/admin/api/flags");
  const next = !f.billing_paused;
  if (next && !(await confirmAction("Тарификация", "Остановить тарификацию? Устройства останутся активными, плата списываться не будет."))) return;
  paintFlags(await api("/admin/api/flags", { method: "POST", body: JSON.stringify({ billing_paused: next }) }));
};

$("nudgeBtn").onclick = async () => {
  const f = await api("/admin/api/flags");
  const next = !f.trial_nudge;
  if (
    next &&
    !(await confirmAction(
      "Напоминание о триале",
      "Включить напоминание? Тем, кто запустил бота больше суток назад и ещё не добавил устройство, уйдёт сообщение."
    ))
  ) {
    return;
  }
  paintFlags(await api("/admin/api/flags", { method: "POST", body: JSON.stringify({ trial_nudge: next }) }));
};

$("inviteNudgeBtn").onclick = async () => {
  const f = await api("/admin/api/flags");
  const next = !f.invite_nudge;
  if (
    next &&
    !(await confirmAction(
      "Приглашение друга",
      "Включить рассылку? Тем, кто запустил бота больше двух суток назад, уйдёт ссылка «приведи друга»."
    ))
  ) {
    return;
  }
  paintFlags(await api("/admin/api/flags", { method: "POST", body: JSON.stringify({ invite_nudge: next }) }));
};

$("infoNudgeBtn").onclick = async () => {
  const f = await api("/admin/api/flags");
  const next = !f.info_nudge;
  if (
    next &&
    !(await confirmAction(
      "Справка о кабинете",
      "Включить рассылку? Тем, кто в боте уже четыре суток, уйдёт короткое объяснение кабинета и списания."
    ))
  ) {
    return;
  }
  paintFlags(await api("/admin/api/flags", { method: "POST", body: JSON.stringify({ info_nudge: next }) }));
};

if ($("storyNudgeBtn")) {
  $("storyNudgeBtn").onclick = async () => {
    const f = await api("/admin/api/flags");
    const next = !f.story_nudge;
    if (
      next &&
      !(await confirmAction(
        "Выложить историю",
        "Тем, у кого есть устройство и награда за историю ещё не получена, сразу уйдёт предложение выложить историю. Если сообщение не дошло, бот отправит его снова."
      ))
    ) {
      return;
    }
    paintFlags(await api("/admin/api/flags", { method: "POST", body: JSON.stringify({ story_nudge: next }) }));
  };
}

let subPoll = null;

function paintSubJob(j) {
  const out = $("subReplaceOut");
  const btn = $("subReplaceBtn");
  if (!out || !j) return;
  if (btn) btn.disabled = !!j.running;
  if (j.running) {
    const total = j.total || 0;
    out.textContent = total
      ? `Идёт: ${j.done || 0} из ${total}` + (j.failed ? `, ошибок ${j.failed}` : "")
      : "Запущено, собираю список учёток...";
    return;
  }
  if (j.message) out.textContent = j.message;
}

async function loadSubJob() {
  if (!$("subReplaceOut")) return;
  try {
    const j = await api("/admin/api/subscriptions/replace");
    paintSubJob(j);
    if (j.running) {
      if (subPoll) clearTimeout(subPoll);
      subPoll = setTimeout(loadSubJob, 1000);
    }
  } catch (_e) {
    /* ignore */
  }
}

$("subReplaceBtn").onclick = async () => {
  const applySquads = $("subApplySquads").checked;
  const revoke = $("subRevoke").checked;
  if (!applySquads && !revoke) {
    $("subReplaceOut").textContent = "Включите сквады и/или перевыпуск ссылок";
    return;
  }
  const bits = [];
  if (applySquads) bits.push("сквады из .env");
  if (revoke) bits.push("новые ссылки, обновление кабинета и уведомление");
  if (!(await confirmAction("Замена подписок", "Заменить подписки у всех: " + bits.join(" и ") + "?"))) return;
  $("subReplaceOut").textContent = "Запускаю...";
  try {
    await api("/admin/api/subscriptions/replace", {
      method: "POST",
      body: JSON.stringify({ apply_squads: applySquads, revoke }),
    });
    loadSubJob();
  } catch (err) {
    $("subReplaceOut").textContent = err.message || "Не удалось запустить";
  }
};

(async () => {
  applyTheme(document.documentElement.getAttribute("data-theme") || "dark");
  syncSidebarDefault();
  setSidebarCollapsed(document.documentElement.classList.contains("sidebar-collapsed"));
  if ($("broadcastText") && $("broadcastPreview")) {
    $("broadcastText").oninput = () => {
      $("broadcastPreview").textContent = $("broadcastText").value.trim() || "Превью сообщения";
    };
    document.querySelectorAll('input[name="bcTpl"]').forEach((el) => {
      el.onchange = () => paintBroadcastAudience();
    });
    if ($("bcAudience")) $("bcAudience").onchange = () => paintBroadcastAudience();
  }
  if ($("maintNotice") && $("maintPhonePreview")) {
    $("maintNotice").oninput = () => {
      $("maintPhonePreview").textContent = $("maintNotice").value.trim() || "Текст оповещения появится здесь";
    };
  }
  try {
    const s = await api("/admin/api/session");
    $("brand").textContent = s.brand || "Админка";
    showShell();
    switchTab(tabFromHash());
  } catch (_e) {
    showLogin();
  }
})();
