const tg = window.Telegram && window.Telegram.WebApp
  ? window.Telegram.WebApp
  : {
      ready() {},
      expand() {},
      initData: "",
      colorScheme: "light",
      showAlert: (m) => window.alert(m),
      openLink: (u) => window.open(u, "_blank"),
      openTelegramLink: (u) => window.open(u, "_blank"),
      openInvoice() {},
      setHeaderColor() {},
      setBackgroundColor() {},
      onEvent() {},
      HapticFeedback: { impactOccurred() {}, notificationOccurred() {} },
    };

tg.ready();
tg.expand();

const $ = (id) => document.getElementById(id);

function applyTheme() {
  document.documentElement.classList.toggle("dark", tg.colorScheme === "dark");
  try {
    tg.setHeaderColor("secondary_bg_color");
    tg.setBackgroundColor("secondary_bg_color");
  } catch (_e) {}
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

function daysLabel(n) {
  const abs = Math.abs(n);
  const mod10 = abs % 10;
  const mod100 = abs % 100;
  let word = "дней";
  if (mod10 === 1 && mod100 !== 11) word = "день";
  else if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) word = "дня";
  return `${n} ${word}`;
}

function showErr(err) {
  try {
    tg.HapticFeedback.notificationOccurred("error");
  } catch (_e) {}
  tg.showAlert(err.message || String(err));
}

function showBoot() {
  $("boot").classList.remove("hidden");
  $("fail").classList.add("hidden");
  $("app").classList.add("hidden");
}

function showFail(message) {
  $("boot").classList.add("hidden");
  $("app").classList.add("hidden");
  $("fail").classList.remove("hidden");
  $("failText").textContent = message;
}

function showApp() {
  $("boot").classList.add("hidden");
  $("fail").classList.add("hidden");
  $("app").classList.remove("hidden");
}

function renderPay(me) {
  const row = $("payRow");
  row.innerHTML = "";
  if (me.trial_available) {
    const t = document.createElement("button");
    t.type = "button";
    t.className = "cell action";
    t.textContent = me.balance_enabled
      ? `Попробовать бесплатно · ${me.trial_rub} руб.`
      : `Попробовать бесплатно · ${daysLabel(me.trial_days)}`;
    t.onclick = async () => {
      haptic();
      try {
        await api("/api/trial", { method: "POST", body: "{}" });
        await load();
      } catch (e) {
        showErr(e);
      }
    };
    row.appendChild(t);
  }
  me.plans.forEach((plan) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "cell nav";
    const price = plan.rub ? `${plan.rub} RUB` : `${plan.stars} Stars`;
    const main = document.createElement("div");
    main.className = "plan-main";
    const title = document.createElement("div");
    title.className = "plan-title";
    title.textContent = me.balance_enabled ? `Пополнить · ${plan.title}` : plan.title;
    const sub = document.createElement("div");
    sub.className = "plan-sub";
    sub.textContent = me.balance_enabled ? "на баланс, без вывода" : daysLabel(plan.days);
    main.appendChild(title);
    main.appendChild(sub);
    const cost = document.createElement("span");
    cost.className = "plan-price";
    cost.textContent = price;
    b.appendChild(main);
    b.appendChild(cost);
    b.onclick = async () => {
      haptic();
      try {
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
      } catch (e) {
        showErr(e);
      }
    };
    row.appendChild(b);
  });
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
  body.appendChild(copyRow);
  body.appendChild(copyBtn);
}

function renderDevices(me) {
  const wrap = $("devicesWrap");
  if (!me.balance_enabled) {
    wrap.classList.add("hidden");
    return;
  }
  wrap.classList.remove("hidden");
  const body = $("devicesBody");
  body.innerHTML = "";
  if (!me.devices.length) {
    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = "Устройств пока нет.";
    body.appendChild(p);
    return;
  }
  me.devices.forEach((d) => {
    const el = document.createElement("div");
    el.className = "cell static";
    el.style.alignItems = "flex-start";
    el.style.flexDirection = "column";
    el.style.gap = "4px";
    const title = document.createElement("div");
    title.className = "device-title";
    title.textContent = d.title;
    const meta = document.createElement("div");
    meta.className = "plan-sub";
    meta.textContent = `${d.active ? daysLabel(d.days) : "неактивно"}${d.username ? " · " + d.username : ""}`;
    el.appendChild(title);
    el.appendChild(meta);
    if (d.subscription_url) {
      const url = document.createElement("div");
      url.className = "plan-sub";
      url.style.wordBreak = "break-all";
      url.textContent = d.subscription_url;
      el.appendChild(url);
    }
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
  if (me.balance_enabled) {
    $("daysLabel").textContent = "Баланс";
    $("days").textContent = `${me.balance_rub} руб.`;
    $("devicesNote").textContent =
      `Каждое устройство: ${me.vpn_day_price_rub} руб. в сутки. Списание каждый день. Вывод средств недоступен.`;
    const rub = me.referral_reward_rub || 50;
    $("inviteNote").textContent =
      `Когда друг нажмёт «Попробовать бесплатно», вам и другу начислят по ${rub} руб. Вывод недоступен.`;
  } else {
    $("daysLabel").textContent = "Осталось";
    $("days").textContent = daysLabel(me.days);
    const refDays = me.referral_reward_days || 7;
    const friendDays = me.referral_invitee_days || 5;
    $("inviteNote").textContent =
      `Когда друг нажмёт «Попробовать бесплатно», вам начислят ${refDays} дней, а другу +${friendDays} дней к бесплатному периоду.`;
  }
  $("invite").textContent = me.invite_url;
  $("offerLink").href = me.legal.offer;
  $("privacyLink").href = me.legal.privacy;
  $("supportLink").href = me.legal.support.startsWith("@")
    ? `https://t.me/${me.legal.support.slice(1)}`
    : me.legal.support;
  if (me.promo_enabled) $("promoCard").classList.remove("hidden");
  else $("promoCard").classList.add("hidden");
  renderPay(me);
  renderConnect(me);
  renderDevices(me);
  window.__me = me;
  showApp();
}

async function load() {
  const me = await api("/api/me");
  paint(me);
}

function closeMenu() {
  $("menu").classList.add("hidden");
  $("menuScrim").classList.add("hidden");
}

$("menuBtn").onclick = (e) => {
  e.stopPropagation();
  haptic();
  $("menu").classList.toggle("hidden");
  $("menuScrim").classList.toggle("hidden", $("menu").classList.contains("hidden"));
};
$("menuScrim").onclick = closeMenu;
$("menu").onclick = (e) => e.stopPropagation();

$("shareBtn").onclick = () => {
  haptic();
  const url = window.__me && window.__me.invite_url;
  if (url) {
    const me = window.__me;
    let text;
    if (me && me.balance_enabled) {
      const rub = me.referral_reward_rub || 50;
      text = encodeURIComponent(
        `Подключайся. Нажми «Попробовать бесплатно» по ссылке — получишь ${rub} руб. на баланс, и я тоже.`
      );
    } else {
      const days = (me && me.referral_reward_days) || 7;
      const extra = (me && me.referral_invitee_days) || 5;
      text = encodeURIComponent(
        `Подключайся. Нажми «Попробовать бесплатно» по ссылке — получишь +${extra} дн., а я получу ${days} дн. VPN.`
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

$("addDevice").onclick = async () => {
  haptic();
  try {
    const n = (window.__me && window.__me.devices && window.__me.devices.length) || 0;
    await api("/api/devices", {
      method: "POST",
      body: JSON.stringify({ title: "Устройство " + (n + 1) }),
    });
    await load();
  } catch (e) {
    showErr(e);
  }
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

$("retryBtn").onclick = () => {
  showBoot();
  load().catch((err) => showFail(err.message || "Не удалось загрузить данные"));
};

if (tg.onEvent) {
  tg.onEvent("invoiceClosed", (status) => {
    if (status === "paid") load().catch(() => {});
  });
}
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && window.__me) {
    load().catch(() => {});
  }
});

load().catch((err) => showFail(err.message || "Не удалось загрузить данные"));
