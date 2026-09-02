const $ = (id) => document.getElementById(id);
let userPage = 1;
let orderPage = 1;
let refPage = 1;
let billPage = 1;
let currentUser = null;
let selectedUsers = new Set();
let lastUserItems = [];
const TABS = ["overview", "users", "referrals", "orders", "billing", "reports", "broadcast", "backups", "settings"];
let toastTimer = 0;

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

function tabFromHash() {
  const name = (location.hash || "").replace("#", "").trim();
  return TABS.includes(name) ? name : "overview";
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    credentials: "same-origin",
    ...opts,
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
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

function deviceCell(u) {
  const n = Number(u.device_count) || 0;
  const titles = String(u.device_titles || "").trim();
  if (n < 1) return u.remnawave_id ? "подписка" : "—";
  return titles ? n + " · " + titles : String(n);
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
  document.querySelectorAll("nav [data-tab]").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === name);
    if (b.dataset.tab === name) {
      if ($("pageTitle")) $("pageTitle").textContent = b.dataset.title || name;
      if ($("pageLead")) $("pageLead").textContent = b.dataset.lead || "";
    }
  });
  TABS.forEach((tab) => {
    $("tab-" + tab).classList.toggle("hidden", tab !== name);
  });
  if (!opts.skipHash && location.hash.replace("#", "") !== name) {
    history.replaceState(null, "", "#" + name);
  }
  if (name === "overview") loadStats();
  if (name === "users") loadUsers();
  if (name === "referrals") loadReferrals();
  if (name === "orders") loadOrders();
  if (name === "billing") loadBilling();
  if (name === "reports") loadReports();
  if (name === "backups") loadBackups();
  if (name === "settings") loadSettings();
  setNavOpen(false);
}

function card(label, value, tab) {
  const el = document.createElement("div");
  el.className = tab ? "card card-link" : "card";
  el.innerHTML = `<div class="l"></div><div class="n"></div>`;
  el.querySelector(".n").textContent = value;
  el.querySelector(".l").textContent = label;
  if (tab) {
    el.tabIndex = 0;
    el.setAttribute("role", "button");
    el.onclick = () => switchTab(tab);
    el.onkeydown = (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        switchTab(tab);
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
      "Как продлевали": billing.extend_mode || "нет",
      "Как отключали": billing.disable_mode || "нет",
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
      Страниц: sync.pages ?? 0,
      "Учёток в панели": sync.seen ?? 0,
      "Обновлено у нас": sync.applied ?? 0,
      "Секунд": sync.seconds ?? 0,
    });
  }
}

function paintFlags(f) {
  const m = !!f.maintenance;
  const p = !!f.billing_paused;
  const n = !!f.trial_nudge;
  $("maintBtn").textContent = m ? "Тех. работы: вкл" : "Тех. работы: выкл";
  $("maintBtn").classList.toggle("warn", m);
  $("billBtn").textContent = p ? "Тарификация: стоп" : "Тарификация: идёт";
  $("billBtn").classList.toggle("warn", p);
  if ($("nudgeBtn")) {
    $("nudgeBtn").textContent = n ? "Напоминание: вкл" : "Напоминание: выкл";
    $("nudgeBtn").classList.toggle("warn", n);
  }
  if (typeof f.maintenance_notice === "string") {
    $("maintNotice").value = f.maintenance_notice;
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
    ? "Тех. работы включены: на любое действие в боте уходят сохранённые текст и картинка."
    : p
      ? "Устройства продлеваются, плата не списывается."
      : "";
  const fm = $("flagMaint");
  const fb = $("flagBill");
  const fn = $("flagNudge");
  if (fm) {
    fm.textContent = m ? "Техработы" : "Сервис работает";
    fm.className = "flag " + (m ? "flag-warn" : "flag-ok");
  }
  if (fb) {
    fb.textContent = p ? "Тарификация на паузе" : "Тарификация идёт";
    fb.className = "flag " + (p ? "flag-warn" : "flag-ok");
  }
  if (fn) {
    fn.textContent = n ? "Напоминание о триале" : "Напоминание о триале выкл";
    fn.className = "flag " + (n ? "flag-warn" : "flag-ok");
  }
}

async function loadFlags() {
  const f = await api("/admin/api/flags");
  paintFlags(f);
}

async function loadStats() {
  await loadFlags();
  loadSubJob();
  const s = await api("/admin/api/stats");
  const u = s.users || {};
  const cards = $("cards");
  cards.innerHTML = "";
  [
    ["Пользователи", u.users_total || 0, "users"],
    ["Оферта принята", u.legal_ok || 0],
    ["Активные подписки", u.active || 0],
    ["Бесплатный период использован", u.trial_used || 0],
    ["Новые за сутки", u.new_1d || 0],
    ["Новые за 7 дней", u.new_7d || 0],
    ["Новые за 30 дней", u.new_30d || 0],
    ["Оборот, рубли", s.revenue_rub || 0, "orders"],
    ["Промокоды", s.promo_uses || 0],
    ["Stars-платежи", s.stars_payments || 0],
    ["Жалобы VPN", s.vpn_reports || 0, "reports"],
    ["Заблокированы", u.blocked || 0, "users"],
    ["Пришли по ссылке", u.referred || 0, "referrals"],
    ["Реф. награда выдана", u.referral_rewarded || 0, "referrals"],
  ].forEach(([l, v, tab]) => cards.appendChild(card(l, v, tab)));
  kv($("orderStats"), s.orders, "Заказов пока нет");
  kv($("planStats"), s.plans, "Оплаченных тарифов нет");
  paintJobs(s.jobs || {});
}

function pager(el, page, total, limit, onPage) {
  el.innerHTML = "";
  const pages = Math.max(1, Math.ceil(total / limit));
  const info = document.createElement("span");
  info.className = "muted";
  info.textContent = `${total} записей, стр. ${page}/${pages}`;
  el.appendChild(info);
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
  const q = $("userQ").value.trim();
  const data = await api(`/admin/api/users?q=${encodeURIComponent(q)}&page=${userPage}`);
  lastUserItems = data.items || [];
  const body = $("userRows");
  body.innerHTML = "";
  if (!lastUserItems.length) {
    body.appendChild(emptyRow(11, q ? "Никого не нашли" : "Пользователей пока нет"));
  }
  lastUserItems.forEach((u) => {
    const tr = document.createElement("tr");
    tr.className = "row-link" + (u.blocked_at ? " is-blocked" : "");
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
    const tdDev = tdText(deviceCell(u));
    tdDev.className = "wrap";
    tdDev.title = deviceCell(u);
    tr.appendChild(tdDev);
    tr.appendChild(onlineCell(u.last_online_at));
    tr.appendChild(tdText(u.trial_used ? "да" : "нет"));
    tr.appendChild(tdText(fmt(u.expire_at)));
    tr.appendChild(tdPill(u.blocked_at ? "блок" : (u.panel_status || "—")));
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
  if (!window.confirm(confirmText)) return;
  $("bulkOut").textContent = "Выполняю...";
  try {
    const r = await api("/admin/api/users/bulk", {
      method: "POST",
      body: JSON.stringify(payload),
    });
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
  const q = $("refQ").value.trim();
  const data = await api(`/admin/api/referrals?q=${encodeURIComponent(q)}&page=${refPage}`);
  const body = $("refRows");
  body.innerHTML = "";
  if (!data.items.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 4;
    td.className = "muted";
    td.textContent = "Пока никто не приходил по рефссылке";
    tr.appendChild(td);
    body.appendChild(tr);
  }
  data.items.forEach((row) => {
    const tr = document.createElement("tr");
    [
      whoLabel(row.invitee_id, row.invitee_username, row.invitee_name),
      whoLabel(row.referrer_id, row.referrer_username, row.referrer_name),
      fmt(row.invitee_at),
    ].forEach((t) => tr.appendChild(tdText(t)));
    tr.appendChild(tdPill(row.referral_rewarded ? "выдана" : "ещё нет"));
    body.appendChild(tr);
  });
  pager($("refPager"), data.page, data.total, data.limit, loadReferrals);
}

async function loadOrders(page) {
  if (page) orderPage = page;
  const q = $("orderQ").value.trim();
  const data = await api(`/admin/api/orders?q=${encodeURIComponent(q)}&page=${orderPage}`);
  const body = $("orderRows");
  body.innerHTML = "";
  if (!data.items.length) {
    body.appendChild(emptyRow(5, q ? "Заказов не нашли" : "Заказов пока нет"));
  }
  data.items.forEach((o) => {
    const tr = document.createElement("tr");
    tr.appendChild(tdText(o.order_id));
    tr.appendChild(tdText(o.telegram_id));
    tr.appendChild(tdText(o.plan_code));
    tr.appendChild(tdPill(o.status));
    tr.appendChild(tdText(fmt(o.created_at)));
    body.appendChild(tr);
  });
  pager($("orderPager"), data.page, data.total, data.limit, loadOrders);
}

const BILL_KIND = {
  charge: "списание",
  disable: "отключение",
  pause: "пауза",
  revive: "включение",
  admin_balance: "баланс",
  admin_grant: "начисление",
  trust: "обещанный",
  trust_collect: "возврат обещанного",
  device_delete: "удаление",
  error: "ошибка",
};
const BILL_SOURCE = { cron: "тарификация", admin: "админка", user: "кабинет" };

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
  const q = $("billQ").value.trim();
  const data = await api(`/admin/api/billing?q=${encodeURIComponent(q)}&page=${billPage}`);
  const body = $("billRows");
  body.innerHTML = "";
  if (!data.items.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 7;
    td.className = "muted";
    td.textContent = "Пока нет событий биллинга";
    tr.appendChild(td);
    body.appendChild(tr);
  }
  data.items.forEach((e) => {
    const tr = document.createElement("tr");
    const cells = billRowCells(e);
    tr.appendChild(tdText(cells[0]));
    tr.appendChild(tdText(cells[1]));
    tr.appendChild(tdPill(cells[2]));
    tr.appendChild(tdText(cells[3]));
    tr.appendChild(tdText(cells[4]));
    tr.appendChild(tdText(cells[5]));
    tr.appendChild(tdText(cells[6]));
    if (e.note) tr.title = e.note;
    body.appendChild(tr);
  });
  pager($("billPager"), data.page, data.total, data.limit, loadBilling);
}

async function loadUserDevices(telegramId) {
  const body = $("userDeviceRows");
  if (!body) return;
  body.innerHTML = "";
  const wait = document.createElement("tr");
  const waitTd = document.createElement("td");
  waitTd.colSpan = 5;
  waitTd.className = "muted";
  waitTd.textContent = "Загружаю из панели...";
  wait.appendChild(waitTd);
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
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 5;
      td.className = "muted";
      td.textContent = "Устройств нет";
      tr.appendChild(td);
      body.appendChild(tr);
      return;
    }
    items.forEach((d) => {
      const tr = document.createElement("tr");
      [
        d.title || "Устройство",
        d.client || "—",
        d.platform || "—",
      ].forEach((t) => tr.appendChild(tdText(t)));
      tr.appendChild(tdPill(d.status || "—"));
      const tdOn = onlineCell(d.last_online_at);
      tr.appendChild(tdOn);
      body.appendChild(tr);
    });
  } catch (_e) {
    body.innerHTML = "";
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 5;
    td.className = "muted";
    td.textContent = "Не удалось загрузить устройства";
    tr.appendChild(td);
    body.appendChild(tr);
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

let reportPage = 1;
async function loadReports(page) {
  if (page) reportPage = page;
  const data = await api(`/admin/api/reports?page=${reportPage}`);
  const body = $("reportRows");
  body.innerHTML = "";
  data.items.forEach((r) => {
    const tr = document.createElement("tr");
    tr.style.cursor = "pointer";
    const who = `${r.telegram_id}` + (r.username ? ` @${r.username}` : "") + (r.first_name ? ` · ${r.first_name}` : "");
    const why = Array.isArray(r.payload && r.payload.why) ? (r.payload.why[0] || "—") : "—";
    [fmt(r.created_at), who, fmt(r.expire_at), r.panel_status || "—", why].forEach((t) => {
      const td = document.createElement("td");
      td.textContent = t;
      tr.appendChild(td);
    });
    tr.onclick = () => {
      $("reportDetail").textContent = JSON.stringify(r.payload || r, null, 2);
    };
    body.appendChild(tr);
  });
  pager($("reportPager"), data.page, data.total, data.limit, loadReports);
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
  set("setMaxDev", v.max_devices);
  set("setHwid", v.remnawave_hwid_limit);
  set("setDayPrice", v.vpn_day_price_rub);
  set("setTopMin", v.balance_topup_min);
  set("setTopMax", v.balance_topup_max);
  set("setTopStep", v.balance_topup_step);
  set("setRefRub", v.referral_reward_rub);
  set("setStoryOn", v.story_reward_enabled);
  set("setStoryRub", v.story_reward_rub);
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
  set("setReportCd", v.vpn_report_cooldown_sec);
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
  return { id: "", name: "", mark: "", deep_link: "", platforms: ["ios"], stores: {} };
}

function renderVpnApps(list) {
  const box = $("vpnAppsList");
  if (!box) return;
  box.innerHTML = "";
  (list.length ? list : [emptyVpnApp()]).forEach((app) => box.appendChild(vpnAppCard(app)));
}

function vpnAppCard(app) {
  const wrap = document.createElement("div");
  wrap.className = "vpn-app";
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
  head.appendChild(mk("va-id", "id, латиница", app.id || "", { maxLength: 24 }));
  head.appendChild(mk("va-name", "Название", app.name || "", { maxLength: 40 }));
  head.appendChild(mk("va-mark", "Значок", app.mark || "", { maxLength: 4 }));
  head.appendChild(mk("va-deep", "happ://add/{url}", app.deep_link || "", { maxLength: 200 }));
  const del = document.createElement("button");
  del.type = "button";
  del.className = "ghost";
  del.textContent = "Убрать";
  del.onclick = () => wrap.remove();
  head.appendChild(del);
  wrap.appendChild(head);
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
  wrap.appendChild(plats);
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
      deep_link: (card.querySelector(".va-deep") || {}).value || "",
      platforms,
      stores,
    };
  });
}

$("shopForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const num = (id) => Number($(id).value);
  const payload = {
    brand_name: $("setBrand").value,
    support_username: $("setSupport").value,
    legal_offer_url: $("setOffer").value,
    legal_privacy_url: $("setPrivacy").value,
    max_devices: num("setMaxDev"),
    remnawave_hwid_limit: num("setHwid"),
    vpn_day_price_rub: num("setDayPrice"),
    balance_topup_min: num("setTopMin"),
    balance_topup_max: num("setTopMax"),
    balance_topup_step: num("setTopStep"),
    referral_reward_rub: num("setRefRub"),
    story_reward_enabled: $("setStoryOn").checked,
    story_reward_rub: num("setStoryRub"),
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
    vpn_report_cooldown_sec: num("setReportCd"),
    promo_enabled: $("setPromoOn").checked,
    promo_codes: $("setPromo").value,
    vpn_apps: collectVpnApps(),
    notices: collectNotices(),
  };
  $("shopOut").textContent = "Сохраняю...";
  try {
    await api("/admin/api/settings", { method: "POST", body: JSON.stringify(payload) });
    $("shopOut").textContent = "Сохранено. Кабинет и бот уже берут новые значения.";
    toast("Настройки сохранены");
    await loadSettings();
  } catch (err) {
    $("shopOut").textContent = err.message || "Не удалось сохранить";
  }
});

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
    (u.blocked_at ? " · заблокирован" : "");
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
    (u.blocked_at ? " · заблокирован" : "");
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

document.querySelectorAll("nav [data-tab]").forEach((b) => {
  b.onclick = () => switchTab(b.dataset.tab);
});
document.querySelectorAll("#setNav [data-jump]").forEach((b) => {
  b.onclick = () => {
    const el = $(b.dataset.jump);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  };
});
document.querySelectorAll("#modalTabs [data-pane]").forEach((b) => {
  b.onclick = () => setModalPane(b.dataset.pane);
});
["flagMaint", "flagBill", "flagNudge"].forEach((id) => {
  const el = $(id);
  if (el) el.onclick = () => switchTab("overview");
});
$("navToggle").onclick = () => setNavOpen(!document.body.classList.contains("nav-open"));
$("navScrim").onclick = () => setNavOpen(false);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
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
    const map = { users: "userQ", referrals: "refQ", orders: "orderQ", billing: "billQ" };
    const id = map[tab];
    if (id && $(id)) $(id).focus();
  }
});
window.addEventListener("hashchange", () => switchTab(tabFromHash(), { skipHash: true }));
window.addEventListener("resize", () => {
  if (window.matchMedia("(min-width: 901px)").matches) setNavOpen(false);
});
$("userSearch").onclick = () => {
  selectedUsers.clear();
  loadUsers(1);
};
$("orderSearch").onclick = () => loadOrders(1);
$("billSearch").onclick = () => loadBilling(1);
$("refSearch").onclick = () => loadReferrals(1);
$("userQ").oninput = debounce(() => {
  selectedUsers.clear();
  loadUsers(1);
}, 280);
$("orderQ").oninput = debounce(() => loadOrders(1), 280);
$("billQ").oninput = debounce(() => loadBilling(1), 280);
$("refQ").oninput = debounce(() => loadReferrals(1), 280);
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
$("bulkDeleteMatch").onclick = () => {
  const q = $("userQ").value.trim();
  const label = q ? `по поиску «${q}»` : "всех в базе";
  runBulk(
    { action: "delete", all_matching: true, q },
    `Удалить ${label}? Не больше 500 за раз. Админы пропускаются.`
  );
};
$("orderQ").onkeydown = (e) => {
  if (e.key === "Enter") loadOrders(1);
};
$("billQ").onkeydown = (e) => {
  if (e.key === "Enter") loadBilling(1);
};
$("refQ").onkeydown = (e) => {
  if (e.key === "Enter") loadReferrals(1);
};

$("broadcastBtn").onclick = async () => {
  $("broadcastOut").textContent = "Отправка...";
  try {
    const r = await api("/admin/api/broadcast", {
      method: "POST",
      body: JSON.stringify({ text: $("broadcastText").value }),
    });
    $("broadcastOut").textContent = `Отправлено: ${r.sent}, ошибок: ${r.failed}`;
    toast(`Отправлено: ${r.sent}`);
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
  if (!window.confirm(warn)) return;
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
  if (!window.confirm(`Удалить пользователя ${id}? Доступ в панели будет отключён.`)) return;
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
  if (!window.confirm(msg)) return;
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
    if (!window.confirm("Включить тех. работы? На любое действие в боте уйдут сохранённые текст и картинка.")) return;
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
  if (!window.confirm("Удалить сохранённую картинку?")) return;
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
  if (next && !window.confirm("Остановить тарификацию? Устройства останутся активными, плата списываться не будет.")) return;
  paintFlags(await api("/admin/api/flags", { method: "POST", body: JSON.stringify({ billing_paused: next }) }));
};

$("nudgeBtn").onclick = async () => {
  const f = await api("/admin/api/flags");
  const next = !f.trial_nudge;
  if (
    next &&
    !window.confirm(
      "Включить напоминание? Тем, кто запустил бота больше суток назад и не брал пробный период, уйдёт сообщение."
    )
  ) {
    return;
  }
  paintFlags(await api("/admin/api/flags", { method: "POST", body: JSON.stringify({ trial_nudge: next }) }));
};

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
  if (!window.confirm("Заменить подписки у всех: " + bits.join(" и ") + "?")) return;
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
  try {
    const s = await api("/admin/api/session");
    $("brand").textContent = s.brand || "Админка";
    showShell();
    switchTab(tabFromHash());
  } catch (_e) {
    showLogin();
  }
})();
