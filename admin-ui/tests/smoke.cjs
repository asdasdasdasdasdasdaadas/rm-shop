const { chromium } = require("playwright");
const AxeBuilder = require("@axe-core/playwright").default;
const fs = require("node:fs"),
  assert = require("node:assert/strict"),
  path = require("node:path"),
  os = require("node:os");
const screenshots = fs.mkdtempSync(path.join(os.tmpdir(), "admin-ux-"));
(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1080 },
  });
  const page = await context.newPage(),
    errors = [],
    posts = [];
  page.on("pageerror", (e) => errors.push(e.message));
  let authenticated = false,
    failBalance = true,
    failSettings = true,
    failUsers = false;
  let user = {
    telegram_id: 123,
    first_name: "Александр",
    username: "alex",
    balance_rub: 240,
    device_count: 2,
    trial_used: true,
    paid_total_rub: 900,
    created_at: "2026-09-20T12:00:00Z",
    last_online_at: "2026-09-25T21:00:00Z",
    used_traffic_bytes: 32 * 1073741824,
    panel_status: "ACTIVE",
    invited_count: 3,
  };
  let settings = {
    brand_name: "WAY VPN",
    support_username: "way_support",
    legal_offer_url: "https://example.org/offer",
    legal_privacy_url: "https://example.org/privacy",
    admin_live_chat_id: "",
    welcome_sticker_file_id: "",
    vpn_day_price_rub: 6,
    max_devices: 5,
    remnawave_hwid_limit: 2,
    trial_enabled: true,
    trial_days: 3,
    referral_program_enabled: true,
    referral_mode: "classic",
    referral_payout_enabled: false,
    referral_payout_min: 2000,
    referral_invitee_reward_rub: 0,
    referral_reward_days: 0,
    referral_invitee_days: 0,
    trust_enabled: true,
    trust_days: 3,
    trust_fee_rub: 10,
    balance_topup_min: 50,
    balance_topup_max: 10000,
    balance_topup_step: 50,
    router_enabled: true,
    router_rub: 490,
    router_days: 30,
    plan_1m_rub: 180,
    plan_3m_rub: 500,
    plan_6m_rub: 900,
    plan_12m_rub: 1700,
    pay_methods: [
      { id: "sbp", title: "СБП", note: "Оплата через банк", enabled: true },
    ],
    vpn_apps: [],
    notices: { broadcast_whitelist: "Белые списки включены. Подключайтесь!" },
  };
  const current = {
    entered: 1248,
    trial: 902,
    connected: 740,
    checkout: 428,
    paid: 356,
    repeat_paid: 182,
    no_gift: 120,
    gift_no_online: 150,
    device_no_online: 68,
    online_no_paid: 380,
    checkout_drop: 72,
    paid_no_repeat: 174,
    organic: 690,
    from_ref: 330,
    from_ad: 228,
    promo: 121,
    inv_entered: 330,
    inv_trial: 240,
    inv_connected: 189,
    inv_paid: 96,
  };
  const stats = {
    users: { users_total: 1248, payouts_pending: 3, bot_blocked: 18 },
    online: { day: 410 },
    topups: { payers: 356, amount_rub: 184250 },
    tickets_open: 4,
    funnel: Object.fromEntries(
      ["1d", "7d", "30d", "90d", "all"].map((p) => [
        p,
        { current, from: "2026-09-01", to: "2026-09-26" },
      ]),
    ),
    reminder_results: { groups: [] },
    exit_feedback: {},
    jobs: {},
  };
  const campaigns = {
    items: [
      {
        id: 1,
        started_at: "2026-09-01T09:00:00Z",
        stopped_at: null,
        reward_rub: 540,
        friends: 23,
        awards: 6,
        sent: 1100,
      },
    ],
    next_reward_rub: 540,
  };
  await page.route("http://admin.test/**", async (route) => {
    const req = route.request(),
      url = new URL(req.url()),
      key = url.pathname.replace("/admin/api/", "");
    if (url.pathname.startsWith("/admin/api/")) {
      const method = req.method();
      let payload = {};
      if (method === "POST") {
        try {
          payload = req.postDataJSON() || {};
        } catch {}
        posts.push({ key, payload });
      }
      if (key === "session")
        return route.fulfill(
          authenticated
            ? { json: { ok: true, brand: "WAY VPN" } }
            : { status: 401, json: { ok: false, auth: false } },
        );
      if (key === "login") {
        authenticated = true;
        return route.fulfill({ json: { ok: true, brand: "WAY VPN" } });
      }
      if (key === "logout") {
        authenticated = false;
        return route.fulfill({ json: { ok: true } });
      }
      if (!authenticated)
        return route.fulfill({ status: 401, json: { ok: false, auth: false } });
      let data = {
        ok: true,
        items: [],
        total: 0,
        page: Number(url.searchParams.get("page") || 1),
        limit: 25,
      };
      if (key === "stats") data = stats;
      if (key === "settings") {
        if (method === "POST") {
          if (failSettings) {
            failSettings = false;
            return route.fulfill({
              status: 500,
              json: { error: "Настройки не сохранены. Повторите попытку." },
            });
          }
          settings = { ...settings, ...payload };
        }
        data = {
          values: settings,
          balance_enabled: true,
          notice_fields: [
            {
              key: "broadcast_whitelist",
              title: "Рассылка: белые списки",
              hint: "",
            },
          ],
        };
      }
      if (key === "users") {
        if (failUsers)
          return route.fulfill({
            status: 503,
            json: { error: "База временно недоступна" },
          });
        data = {
          ...data,
          items: url.searchParams.get("q") === "никого" ? [] : [user],
          total: url.searchParams.get("q") === "никого" ? 0 : 1,
        };
      }
      if (key === "users/123/balance") {
        if (failBalance) {
          failBalance = false;
          return route.fulfill({
            status: 500,
            json: { error: "Баланс не изменён. Повторите попытку." },
          });
        }
        user = { ...user, balance_rub: user.balance_rub + payload.amount };
        data = { ok: true, balance_rub: user.balance_rub };
      }
      if (key === "users/123/devices")
        data = {
          items: [
            {
              id: 1,
              title: "iPhone",
              platform: "ios",
              status: "ACTIVE",
              last_online_at: user.last_online_at,
            },
          ],
        };
      if (key === "users/bulk")
        data = {
          ok: true,
          done: payload.ids.length,
          total: payload.ids.length,
          failed: 0,
        };
      if (key === "orders")
        data = {
          ...data,
          items: [
            {
              order_id: "order-1",
              telegram_id: 123,
              first_name: "Александр",
              amount_rub: 240,
              status: "granted",
              created_at: user.created_at,
            },
          ],
          total: 1,
        };
      if (key === "tickets")
        data = {
          ...data,
          items: [
            {
              id: 1,
              telegram_id: 123,
              first_name: "Александр",
              status: "open",
              last_body: "Не получается подключить iPhone",
              created_at: user.created_at,
            },
          ],
          total: 1,
        };
      if (key === "tickets/1")
        data = {
          ticket: { id: 1, status: "open" },
          messages: [
            {
              id: 1,
              author: "user",
              body: "Помогите подключиться",
              created_at: user.created_at,
            },
          ],
        };
      if (key === "broadcast")
        data = {
          ok: true,
          running: false,
          total: 0,
          sent: 0,
          failed: 0,
          audiences: { all: 1248, using: 740, unused: 508 },
          previews: {
            whitelist: settings.notices.broadcast_whitelist,
            invite: "Пригласите друзей и получите награду",
            unused: "Подключите VPN",
          },
        };
      if (key === "announcements")
        data = {
          ...data,
          recipients: 1248,
          broadcast: { running: false },
          defaults: {
            title: "Новости VPN",
            lead: "Стали стабильнее",
            kicker: "Обновление",
            closing: "Спасибо!",
          },
        };
      if (key === "referral-campaigns")
        data = url.searchParams.has("campaign_id")
          ? {
              campaign: campaigns.items[0],
              summary: {
                participants: 10,
                friends: 23,
                paid_rub: 7400,
                one_friend: 2,
                two_friends: 2,
                completed: 6,
              },
              awards: { awards: 6, awarded_rub: 3240 },
              delivery: { sent: 1100, pending: 12, failed: 3 },
              items: [],
              page: 1,
              limit: 50,
            }
          : campaigns;
      if (key === "flags")
        data = {
          ok: true,
          payment_nudge: true,
          trial_nudge: true,
          invite_nudge: true,
          info_nudge: true,
          legal_nudge: false,
          billing_paused: false,
          maintenance: false,
        };
      if (key === "backups") data = { items: [], keep_days: 7 };
      return route.fulfill({ json: data });
    }
    const rel =
      url.pathname.replace("/admin/", "").replace(/^static\//, "") ||
      "index.html";
    const asset = path.resolve(__dirname, "../../admin", rel);
    return fs.existsSync(asset)
      ? route.fulfill({ path: asset })
      : route.fulfill({ status: 404, body: "" });
  });
  const accessibility = async (label) => {
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    assert.deepEqual(
      result.violations.map((v) => ({
        id: v.id,
        impact: v.impact,
        nodes: v.nodes.map((n) => n.target),
      })),
      [],
      label,
    );
  };
  const nav = (label) =>
    page
      .getByRole("navigation", { name: "Разделы админки" })
      .getByRole("button", { name: label, exact: true })
      .click();
  await page.goto("http://admin.test/admin/");
  await page.getByLabel("Пароль", { exact: true }).fill("test-password");
  await page.getByRole("button", { name: "Войти", exact: true }).click();
  await page.getByRole("heading", { name: "Обзор", exact: true }).waitFor();
  await page.screenshot({
    path: path.join(screenshots, "overview.png"),
    fullPage: true,
  });
  await accessibility("Overview");
  await nav("Клиенты");
  await page.getByRole("button", { name: "Открыть", exact: true }).click();
  await page.getByLabel("Сумма изменения баланса").fill("-40");
  await page.getByRole("button", { name: "Применить", exact: true }).click();
  const confirmation = page.getByRole("dialog").filter({
    has: page.getByRole("heading", { name: "Изменить баланс", exact: true }),
  });
  await confirmation
    .getByRole("button", { name: "Применить", exact: true })
    .click();
  await page.getByText("Баланс не изменён. Повторите попытку.").waitFor();
  assert.equal(user.balance_rub, 240);
  await confirmation
    .getByRole("button", { name: "Применить", exact: true })
    .click();
  await confirmation.waitFor({ state: "hidden" });
  assert.equal(user.balance_rub, 200);
  await page.getByRole("tab", { name: "Устройства", exact: true }).click();
  await page.getByText("iPhone", { exact: true }).waitFor();
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Фильтры", exact: true }).click();
  await page.getByRole("combobox", { name: "Оплаты", exact: true }).click();
  await page.getByRole("option", { name: "Ещё не оплачивали" }).click();
  await page.getByRole("button", { name: "Показать пользователей" }).click();
  assert.match(page.url(), /paid=no/);
  await page.getByRole("button", { name: "Открыть", exact: true }).waitFor();
  await page.screenshot({
    path: path.join(screenshots, "clients.png"),
    fullPage: true,
  });
  await nav("Настройки");
  await page.getByLabel("Название сервиса", { exact: true }).waitFor();
  await accessibility("Settings form");
  await page
    .getByLabel("Название сервиса", { exact: true })
    .fill("WAY VPN NEW");
  settings.router_rub = 590; // Concurrent change outside this form must survive.
  await page
    .getByRole("button", { name: "Сохранить изменения", exact: true })
    .click();
  await page
    .getByRole("alert")
    .filter({ hasText: "Настройки не сохранены" })
    .first()
    .waitFor();
  assert.equal(settings.brand_name, "WAY VPN");
  await page
    .getByRole("button", { name: "Сохранить изменения", exact: true })
    .click();
  await page
    .getByText("Есть несохранённые изменения", { exact: true })
    .waitFor({ state: "hidden" });
  assert.equal(settings.brand_name, "WAY VPN NEW");
  assert.equal(settings.router_rub, 590);
  await page.getByLabel("Название сервиса", { exact: true }).fill("UNSAVED");
  await nav("Клиенты");
  await page
    .getByRole("heading", { name: "Несохранённые изменения", exact: true })
    .waitFor();
  await page.getByRole("button", { name: "Отмена", exact: true }).click();
  await page.getByRole("heading", { name: "Настройки", exact: true }).waitFor();
  await page.getByRole("button", { name: "Отменить", exact: true }).click();
  await nav("Рассылки");
  await page.getByRole("button", { name: "Продолжить", exact: true }).click();
  await page
    .getByLabel("Текст рассылки", { exact: true })
    .fill("Новая локация уже доступна.");
  await page.getByRole("button", { name: "Продолжить", exact: true }).click();
  await page
    .getByRole("button", { name: "Отправить 1248 пользователям" })
    .click();
  await page
    .getByRole("heading", { name: "Отправить рассылку?", exact: true })
    .waitFor();
  await page.getByRole("button", { name: "Отмена", exact: true }).click();
  assert.equal(posts.filter((p) => p.key === "broadcast").length, 0);
  await page.screenshot({
    path: path.join(screenshots, "broadcast.png"),
    fullPage: true,
  });
  await nav("Обзор");
  await page.getByRole("button", { name: "Перейти без сохранения" }).click();
  for (const label of [
    "Платежи",
    "Операции по балансу",
    "Поддержка",
    "Реферальная программа",
    "Акции",
    "Промокоды",
    "Источники трафика",
    "Новости сервиса",
    "Журнал доставки",
    "Резервные копии",
    "Настройки",
    "Обзор",
  ]) {
    await nav(label);
    await page
      .getByRole("heading", { name: label, exact: true })
      .first()
      .waitFor();
  }
  await nav("Промокоды");
  await page
    .getByRole("button", { name: "Создать промокод", exact: true })
    .first()
    .click();
  await page.getByLabel("Дни подарка", { exact: true }).fill("5");
  await page.getByRole("button", { name: "Сохранить промокод" }).click();
  await page.getByRole("dialog").waitFor({ state: "hidden" });
  assert.equal(posts.find((p) => p.key === "promos").payload.days, 5);
  assert.equal(posts.filter((p) => p.key === "promos").length, 1);
  await nav("Клиенты");
  await page.getByRole("button", { name: "Открыть", exact: true }).click();
  await page.getByRole("button", { name: "Управление", exact: true }).click();
  await page
    .getByRole("menuitem", { name: "Удалить пользователя", exact: true })
    .click();
  assert.equal(
    await page
      .getByRole("button", { name: "Удалить", exact: true })
      .isDisabled(),
    true,
  );
  await page.getByRole("button", { name: "Отмена", exact: true }).click();
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Переключить тему" }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(250);
  await page.screenshot({
    path: path.join(screenshots, "mobile-clients.png"),
    fullPage: true,
  });
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    true,
  );
  await page.getByRole("button", { name: "Открыть меню" }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Акции", exact: true })
    .click();
  await page.getByRole("heading", { name: "Акции", exact: true }).waitFor();
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    true,
  );
  await page.getByText("Первые оплаты", { exact: true }).waitFor();
  await page.waitForTimeout(250);
  await page.screenshot({
    path: path.join(screenshots, "mobile-campaigns.png"),
    fullPage: true,
  });
  await accessibility("Mobile campaigns");
  assert.deepEqual(errors, []);
  assert.equal(
    posts.some((p) => p.key.endsWith("/delete")),
    false,
  );
  await browser.close();
  console.log(
    "UX workflows verified: login, 14 screens, balance error/retry, filters, isolated settings save, dirty navigation, broadcast cancellation, promo creation, deletion guard, mobile.",
  );
  console.log("Screenshots:", screenshots);
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
