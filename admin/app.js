const $ = (id) => document.getElementById(id);
let userPage = 1;
let orderPage = 1;
let refPage = 1;
let currentUser = null;

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

function showLogin() {
  $("login").classList.remove("hidden");
  $("shell").classList.add("hidden");
}

function showShell() {
  $("login").classList.add("hidden");
  $("shell").classList.remove("hidden");
}

function switchTab(name) {
  document.querySelectorAll("nav [data-tab]").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === name);
  });
  ["overview", "users", "referrals", "orders", "reports", "broadcast", "backups", "settings"].forEach((tab) => {
    $("tab-" + tab).classList.toggle("hidden", tab !== name);
  });
  if (name === "overview") loadStats();
  if (name === "users") loadUsers();
  if (name === "referrals") loadReferrals();
  if (name === "orders") loadOrders();
  if (name === "reports") loadReports();
  if (name === "backups") loadBackups();
  if (name === "settings") loadSettings();
}

function card(label, value) {
  const el = document.createElement("div");
  el.className = "card";
  el.innerHTML = `<div class="n"></div><div class="l"></div>`;
  el.querySelector(".n").textContent = value;
  el.querySelector(".l").textContent = label;
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

function paintFlags(f) {
  const m = !!f.maintenance;
  const p = !!f.billing_paused;
  $("maintBtn").textContent = m ? "Тех. работы: вкл" : "Тех. работы: выкл";
  $("maintBtn").classList.toggle("warn", m);
  $("billBtn").textContent = p ? "Тарификация: стоп" : "Тарификация: идёт";
  $("billBtn").classList.toggle("warn", p);
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
}

async function loadFlags() {
  const f = await api("/admin/api/flags");
  paintFlags(f);
}

async function loadStats() {
  await loadFlags();
  const s = await api("/admin/api/stats");
  const u = s.users || {};
  const cards = $("cards");
  cards.innerHTML = "";
  [
    ["Пользователи", u.users_total || 0],
    ["Оферта принята", u.legal_ok || 0],
    ["Активные подписки", u.active || 0],
    ["Бесплатный период использован", u.trial_used || 0],
    ["Новые за сутки", u.new_1d || 0],
    ["Новые за 7 дней", u.new_7d || 0],
    ["Новые за 30 дней", u.new_30d || 0],
    ["Оборот, рубли", s.revenue_rub || 0],
    ["Промокоды", s.promo_uses || 0],
    ["Stars-платежи", s.stars_payments || 0],
    ["Жалобы VPN", s.vpn_reports || 0],
    ["Пришли по ссылке", (u.referred || 0)],
    ["Реф. награда выдана", (u.referral_rewarded || 0)],
  ].forEach(([l, v]) => cards.appendChild(card(l, v)));
  kv($("orderStats"), s.orders, "Заказов пока нет");
  kv($("planStats"), s.plans, "Оплаченных тарифов нет");
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

async function loadUsers(page) {
  if (page) userPage = page;
  const q = $("userQ").value.trim();
  const data = await api(`/admin/api/users?q=${encodeURIComponent(q)}&page=${userPage}`);
  const body = $("userRows");
  body.innerHTML = "";
  data.items.forEach((u) => {
    const tr = document.createElement("tr");
    const cells = [
      u.telegram_id + (u.username ? ` @${u.username}` : ""),
      u.first_name || "—",
      u.balance_rub == null ? "—" : String(u.balance_rub),
      u.trial_used ? "да" : "нет",
      fmt(u.expire_at),
      u.panel_status || "—",
      u.referred_by
        ? whoLabel(u.referred_by, u.referrer_username, u.referrer_name)
        : "—",
      String(u.invited_count || 0),
    ];
    cells.forEach((t) => {
      const td = document.createElement("td");
      td.textContent = t;
      tr.appendChild(td);
    });
    const td = document.createElement("td");
    const btn = document.createElement("button");
    btn.className = "ghost";
    btn.textContent = "Открыть";
    btn.onclick = () => openUser(u);
    td.appendChild(btn);
    tr.appendChild(td);
    body.appendChild(tr);
  });
  pager($("userPager"), data.page, data.total, data.limit, loadUsers);
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
      row.referral_rewarded ? "выдана" : "ещё нет",
    ].forEach((t) => {
      const td = document.createElement("td");
      td.textContent = t;
      tr.appendChild(td);
    });
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
  data.items.forEach((o) => {
    const tr = document.createElement("tr");
    [o.order_id, o.telegram_id, o.plan_code, o.status, fmt(o.created_at)].forEach((t) => {
      const td = document.createElement("td");
      td.textContent = t;
      tr.appendChild(td);
    });
    body.appendChild(tr);
  });
  pager($("orderPager"), data.page, data.total, data.limit, loadOrders);
}

let reportPage = 1;
async function loadReports(page) {
  if (page) reportPage = page;
  const data = await api(`/admin/api/reports?page=${reportPage}`);
  const body = $("reportRows");
  body.innerHTML = "";
  data.items.forEach((r) => {
    const tr = document.createElement("tr");
    const who = `${r.telegram_id}` + (r.username ? ` @${r.username}` : "") + (r.first_name ? ` · ${r.first_name}` : "");
    [fmt(r.created_at), who, fmt(r.expire_at), r.panel_status || "—"].forEach((t) => {
      const td = document.createElement("td");
      td.textContent = t;
      tr.appendChild(td);
    });
    body.appendChild(tr);
  });
  pager($("reportPager"), data.page, data.total, data.limit, loadReports);
}

async function loadSettings() {
  const s = await api("/admin/api/settings");
  $("settingsBox").textContent = JSON.stringify(s, null, 2);
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
    ` · пригласил друзей: ${u.invited_count || 0}`;
  $("modal").classList.remove("hidden");
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
    loadStats();
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
$("userSearch").onclick = () => loadUsers(1);
$("orderSearch").onclick = () => loadOrders(1);
$("refSearch").onclick = () => loadReferrals(1);
$("userQ").onkeydown = (e) => {
  if (e.key === "Enter") loadUsers(1);
};
$("orderQ").onkeydown = (e) => {
  if (e.key === "Enter") loadOrders(1);
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
  $("modal").classList.add("hidden");
  loadUsers();
};
$("balBtn").onclick = async () => {
  if (!currentUser) return;
  await api(`/admin/api/users/${currentUser.telegram_id}/balance`, {
    method: "POST",
    body: JSON.stringify({ amount: Number($("balAmount").value) }),
  });
  $("modal").classList.add("hidden");
  loadUsers();
};
$("delBtn").onclick = async () => {
  if (!currentUser) return;
  const id = currentUser.telegram_id;
  if (!window.confirm(`Удалить пользователя ${id}? Доступ в панели будет отключён.`)) return;
  await api(`/admin/api/users/${id}/delete`, { method: "POST", body: "{}" });
  $("modal").classList.add("hidden");
  loadUsers();
};
$("trialBtn").onclick = async () => {
  if (!currentUser) return;
  await api(`/admin/api/users/${currentUser.telegram_id}/trial-reset`, {
    method: "POST",
    body: "{}",
  });
  $("modal").classList.add("hidden");
  loadUsers();
};
$("msgBtn").onclick = async () => {
  if (!currentUser) return;
  await api(`/admin/api/users/${currentUser.telegram_id}/message`, {
    method: "POST",
    body: JSON.stringify({ text: $("msgText").value }),
  });
  $("msgText").value = "";
};
$("modalClose").onclick = () => $("modal").classList.add("hidden");
$("modal").onclick = (e) => {
  if (e.target === $("modal")) $("modal").classList.add("hidden");
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

(async () => {
  try {
    const s = await api("/admin/api/session");
    $("brand").textContent = s.brand || "Админка";
    showShell();
    loadStats();
  } catch (_e) {
    showLogin();
  }
})();
