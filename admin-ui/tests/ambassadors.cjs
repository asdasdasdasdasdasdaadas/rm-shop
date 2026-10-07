const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs"),
  path = require("node:path"),
  os = require("node:os");
const screenshots = fs.mkdtempSync(path.join(os.tmpdir(), "ambassador-ux-"));
(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  try {
    const page = await browser.newPage({
        viewport: { width: 1440, height: 1000 },
      }),
      errors = [],
      posts = [],
      queries = [];
    page.on("pageerror", (e) => errors.push(e.message));
    const cfg = {
      recruitment: true,
      accruing: true,
      first_percent: 100,
      first_cap: 500,
      recurring_percent: 5,
      hold_days: 14,
      payout_min: 2000,
      budget: 50000,
      member_cap: 0,
      max_members: 20,
    };
    const data = {
      settings: cfg,
      summary: {
        applications: 1,
        active: 1,
        clients: 14,
        payers: 6,
        budget_used: 245000,
        paid: 0,
        pending: 205000,
      },
      members: [
        {
          telegram_id: 123,
          application: "Канал про технологии, 2000 подписчиков",
          status: "pending",
          created_at: "2026-10-05T12:00:00Z",
          risk_hold: false,
        },
      ],
      members_total: 1,
      awards: [
        {
          payment_key: "rollypay:one",
          ambassador_id: 123,
          client_id: 456,
          payment_rub: 500,
          amount_cents: 50000,
          status: "earned",
          created_at: "2026-10-05T12:00:00Z",
          available_at: "2026-10-19T12:00:00Z",
        },
      ],
      awards_total: 1,
      payouts: [
        {
          id: 1,
          ambassador_id: 123,
          amount_cents: 205000,
          details: "+79990000000 Тестовый банк, Анна",
          status: "pending",
          created_at: "2026-10-05T12:00:00Z",
        },
      ],
      payouts_total: 1,
      audit: [],
      audit_total: 0,
    };
    await page.route("http://admin.test/**", async (route) => {
      const url = new URL(route.request().url());
      if (url.pathname.startsWith("/admin/api/")) {
        const key = url.pathname.slice("/admin/api/".length);
        if (key === "session")
          return route.fulfill({ json: { ok: true, brand: "WAY VPN" } });
        if (key === "ambassadors") {
          queries.push(url.searchParams.toString());
          if (route.request().method() === "POST") {
            const p = route.request().postDataJSON();
            posts.push(p);
            if (p.action === "approve") data.members[0].status = "approved";
            if (p.action === "settings")
              data.settings = { ...data.settings, ...p };
            if (p.action === "pay") data.payouts[0].status = "paid";
          }
          return route.fulfill({ json: { ok: true, ...data } });
        }
        return route.fulfill({ json: { ok: true, items: [] } });
      }
      const rel =
        url.pathname.replace("/admin/", "").replace(/^static\//, "") ||
        "index.html";
      return route.fulfill({
        path: path.resolve(__dirname, "../../admin", rel),
      });
    });
    await page.goto("http://admin.test/admin/#ambassadors");
    await page.getByRole("combobox").click();
    await page
      .getByRole("option", { name: "На рассмотрении", exact: true })
      .click();
    await page.getByRole("button", { name: "Одобрить", exact: true }).waitFor();
    assert.ok(
      queries.some(
        (q) => q.includes("section=members") && q.includes("status=pending"),
      ),
    );
    await page.getByRole("combobox").click();
    await page
      .getByRole("option", { name: "Все статусы", exact: true })
      .click();
    await page.getByRole("button", { name: "Одобрить", exact: true }).click();
    await page
      .getByLabel("Комментарий или подтверждение перевода")
      .fill("Условия согласованы");
    await page
      .getByRole("button", { name: "Подтвердить", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Приостановить участие", exact: true })
      .waitFor();
    assert.equal(posts[0].action, "approve");
    await page
      .getByRole("tab", { name: "Условия и запуск", exact: true })
      .click();
    await page.getByLabel("Общий бюджет, ₽", { exact: true }).fill("60000");
    await page
      .getByRole("button", { name: "Сохранить условия", exact: true })
      .click();
    await page.getByText("Условия сохранены", { exact: true }).waitFor();
    assert.equal(posts.find((p) => p.action === "settings").budget, 60000);
    await page.getByRole("tab", { name: "Выплаты", exact: true }).click();
    await page
      .getByRole("button", { name: "Перевод выполнен", exact: true })
      .click();
    await page.getByText(/Сначала выполните перевод вручную/).waitFor();
    await page
      .getByLabel("Комментарий или подтверждение перевода")
      .fill("Перевод 100500");
    await page
      .getByRole("button", { name: "Подтвердить", exact: true })
      .click();
    await page.getByText("Выплачено", { exact: true }).waitFor();
    await page.screenshot({
      path: path.join(screenshots, "admin-payouts.png"),
      fullPage: true,
    });
    await page.setViewportSize({ width: 390, height: 844 });
    await page
      .getByRole("tab", { name: "Условия и запуск", exact: true })
      .click();
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      true,
    );
    await page.screenshot({
      path: path.join(screenshots, "admin-mobile.png"),
      fullPage: true,
    });
    const cab = await browser.newPage({
      viewport: { width: 390, height: 844 },
    });
    cab.on("pageerror", (e) => errors.push(e.message));
    await cab.setContent(
      '<html lang="ru"><head><title>Кабинет амбассадора</title></head><body><main style="padding:20px"><h1>Амбассадор</h1><div id="ambassadorContent"></div></main></body></html>',
    );
    await cab.addStyleTag({
      path: path.resolve(__dirname, "../../webapp/app.css"),
    });
    await cab.evaluate(() => {
      window.$ = (id) => document.getElementById(id);
      window.tg = { showAlert: (m) => (window.alertText = m) };
      window.api = async (url, opts) => {
        window.lastRequest = JSON.parse(opts.body);
        if (window.lastRequest.action === "apply")
          window.fixture.member = { status: "pending" };
        if (window.lastRequest.action === "payout") {
          window.fixture.wallet.pending = 205000;
          window.fixture.wallet.available = 0;
        }
        return window.fixture;
      };
    });
    const source = fs.readFileSync(
      path.resolve(__dirname, "../../webapp/app.js"),
      "utf8",
    );
    await cab.addScriptTag({
      content: source.slice(source.indexOf("// Ambassador funds")),
    });
    const fixture = {
      settings: cfg,
      member: null,
      capacity: {
        budget_remaining: 0,
        member_remaining: null,
        next_release_at: "2099-10-19T12:00:00Z",
      },
      wallet: { available: 205000, holding: 40000, pending: 0, paid: 0 },
      stats: { joined: 14, connected: 12, paid: 6, repeat_paid: 2 },
      link: "https://t.me/test?start=amb_test",
      awards: data.awards,
      payouts: [],
    };
    await cab.evaluate((f) => {
      window.fixture = f;
      paintAmbassador(f);
    }, fixture);
    await cab
      .getByLabel("Где вы планируете рекомендовать VPN?")
      .fill("Канал про технологии");
    await cab.getByRole("button", { name: "Отправить заявку" }).click();
    await cab.getByRole("heading", { name: "На рассмотрении" }).waitFor();
    assert.equal(await cab.evaluate(() => lastRequest.action), "apply");
    await cab.evaluate(() => {
      fixture.member = { status: "approved", risk_hold: false };
      paintAmbassador(fixture);
    });
    await cab.getByText(/Лимит вознаграждений исчерпан/).waitFor();
    await cab.getByText(/Ближайшее начисление станет доступно/).waitFor();
    await cab
      .getByLabel("Телефон для СБП, банк и имя получателя")
      .fill("79990000000 Банк Анна");
    await cab.getByRole("button", { name: /Запросить 2/ }).click();
    await cab
      .getByText(
        "Ваша заявка уже на рассмотрении. Повторная станет доступна после решения.",
      )
      .waitFor();
    assert.equal(await cab.evaluate(() => lastRequest.action), "payout");
    assert.equal(
      await cab.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      true,
    );
    await cab.screenshot({
      path: path.join(screenshots, "cabinet.png"),
      fullPage: true,
    });
    assert.deepEqual(errors, []);
    console.log(
      "Ambassador application, approval, settings, manual payout and mobile cabinet verified. Screenshots: " +
        screenshots,
    );
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
