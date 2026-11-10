// Frog UI: the cabinet in the style of our chat widgets.
// Every screen opens with a coloured widget card (illustration, big number, white pill + round glass button);
// the existing nodes are moved into it, so app.js keeps working with the same ids and handlers.
(function () {
  "use strict";
  const D = document;
  const R = D.documentElement;
  R.dataset.ui = "frog";
  const $ = (id) => D.getElementById(id);
  const reduce = () => window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;

  const GP = "M66.5 11.3H33.5c-4.4 0-6.6 0-8.6.6a13.8 13.8 0 0 0-4.8 2.6c-1.6 1.3-2.8 3.2-5.2 6.9L4.4 37.8c-1.6 2.4-2.4 3.7-2.6 5a6.3 6.3 0 0 0 .4 3.4c.5 1.2 1.5 2.2 3.6 4.3l39 39c1.8 1.8 2.7 2.7 3.8 3.1.9.3 1.9.3 2.8 0 1.1-.3 2-1.3 3.8-3.1l39-39c2.1-2.1 3.1-3.1 3.6-4.3a6.3 6.3 0 0 0 .4-3.4c-.2-1.3-1-2.5-2.6-5L85.1 21.5c-2.4-3.7-3.6-5.6-5.2-6.9a13.8 13.8 0 0 0-4.8-2.6c-2-.6-4.2-.6-8.6-.6z";
  const SPK = "M60.3 24.2c.5-1.5 2.6-1.5 3.1 0l3.7 10a2.2 2.2 0 0 0 1.3 1.3l10 3.7c1.5.5 1.5 2.6 0 3.1l-10 3.7a2.2 2.2 0 0 0-1.3 1.3l-3.7 10c-.5 1.5-2.6 1.5-3.1 0l-3.7-10a2.2 2.2 0 0 0-1.3-1.3l-10-3.7c-1.5-.5-1.5-2.6 0-3.1l10-3.7a2.2 2.2 0 0 0 1.3-1.3z";
  const GEM = (w, c) => `<svg width="${w}" height="${w}" viewBox="0 0 100 100" aria-hidden="true"><path fill="#fff" d="${GP}"/><path fill="${c || "#2f86f0"}" d="${SPK}"/></svg>`;
  const FROG = (s, gray) => `<img src="/icons/frog.jpg" width="${s}" height="${s}" alt="" style="border-radius:50%${gray ? ";filter:grayscale(1)" : ""}">`;
  const STAR = (s) => `<svg width="${s}" height="${s}" viewBox="0 0 20 20"><path d="M10 0c.9 5.6 4.4 9.1 10 10-5.6.9-9.1 4.4-10 10-.9-5.6-4.4-9.1-10-10C5.6 9.1 9.1 5.6 10 0z" fill="#fff"/></svg>`;
  const EMO = (e) => `<span class="fh-emo">${e}</span>`;

  function sparkle(card, seed) {
    if (card.querySelector(":scope > .fh-sp")) return;
    for (let i = 0; i < 12; i++) {
      const x = (i * 71 + seed * 37) % 92 + 3; // percent
      const y = (i * 53 + seed * 29) % 150 + 10; // px
      if (Math.abs(x - 50) < 18 && y > 34) continue;
      const s = [6, 10, 14, 8][i % 4];
      const d = D.createElement("i");
      d.className = "fh-sp";
      d.style.cssText = `left:${x}%;top:${y}px;opacity:${[0.5, 0.8, 0.35, 0.6][i % 4]};animation-delay:${((i * 0.37) % 2.6).toFixed(2)}s;animation-duration:${2.2 + (i % 3) * 0.6}s`;
      d.innerHTML = i % 3 ? STAR(s) : "<b></b>";
      card.appendChild(d);
    }
  }

  // Build (once) a widget card at the top of a view and move the given nodes into it.
  function hero(view, color, opts) {
    if (!view) return null;
    let h = view.querySelector(":scope > .fh, :scope .fh-anchor > .fh");
    if (h) return h;
    h = D.createElement("section");
    h.className = "fh fh-" + color + (opts.cls ? " " + opts.cls : "");
    h.innerHTML = `<div class="fh-ov"></div><div class="fh-rb" hidden></div>${opts.ill ? `<div class="fh-ill"><div>${opts.ill}</div></div>` : ""}<div class="fh-body"></div>`;
    const body = h.querySelector(".fh-body");
    (opts.move || []).forEach((n) => n && body.appendChild(n));
    if (opts.after) opts.after.after(h);
    else view.insertBefore(h, view.firstChild);
    sparkle(h, opts.seed || 1);
    return h;
  }
  const ribbon = (h, text) => {
    const r = h && h.querySelector(".fh-rb");
    if (!r) return;
    r.hidden = !text;
    if (text && r.textContent !== text) r.textContent = text;
  };
  const setIll = (h, html) => {
    const i = h && h.querySelector(".fh-ill > div");
    if (i && i.dataset.k !== html) { i.dataset.k = html; i.innerHTML = html; replay(h.querySelector(".fh-ill"), "fh-pop"); }
  };
  function replay(el, cls) {
    if (!el) return;
    el.classList.remove(cls);
    void el.offsetWidth;
    el.classList.add(cls);
  }

  // ---------- count-up ----------
  const fmt = (v) => String(Math.round(v)).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  function countUp(el, from, to, render) {
    if (reduce() || from === to) { render(to); return; }
    const t0 = performance.now();
    el.__counting = true;
    (function f() {
      const k = Math.min(1, (performance.now() - t0) / 800);
      render(from + (to - from) * (1 - Math.pow(1 - k, 3)));
      if (k < 1) requestAnimationFrame(f); else el.__counting = false;
    })();
  }
  // Animate a number inside an element whenever app.js writes a new value there.
  function liveNumber(el) {
    if (!el || el.__live) return;
    el.__live = true;
    let last = null;
    const read = () => {
      const m = el.textContent.replace(/ /g, " ").match(/^([^\d−-]*)([−-]?)([\d ]+)(.*)$/);
      return m ? { pre: m[1], sign: m[2], n: parseInt(m[3].replace(/ /g, ""), 10), suf: m[4] } : null;
    };
    const mo = new MutationObserver(() => {
      if (el.__counting) return;
      const v = read();
      if (!v || isNaN(v.n)) return;
      const from = last == null ? 0 : last;
      last = v.n;
      if (from === v.n) return;
      mo.disconnect();
      countUp(el, from, v.n, (x) => { el.textContent = v.pre + v.sign + fmt(x) + v.suf; });
      setTimeout(() => mo.observe(el, { childList: true, characterData: true, subtree: true }), 850);
    });
    const v = read();
    if (v && !isNaN(v.n)) {
      last = v.n;
      countUp(el, 0, v.n, (x) => { el.textContent = v.pre + v.sign + fmt(x) + v.suf; });
    }
    setTimeout(() => mo.observe(el, { childList: true, characterData: true, subtree: true }), 850);
  }

  // ---------- confetti ----------
  function boom() {
    if (reduce()) return;
    const c = D.createElement("canvas");
    c.className = "fh-confetti";
    const r = window.devicePixelRatio || 1, W = innerWidth, H = innerHeight;
    c.width = W * r; c.height = H * r;
    const x = c.getContext("2d");
    x.scale(r, r);
    D.body.appendChild(c);
    const P = [];
    for (let i = 0; i < 90; i++) P.push({ x: W / 2, y: H * 0.3, vx: Math.random() * 10 - 5, vy: -Math.random() * 9 - 3, c: ["#5ad48f", "#fff", "#30a1f5", "#ffd84d", "#ff8fb1"][i % 5], a: Math.random() * 6, s: Math.random() * 0.3 - 0.15 });
    let t = 0;
    (function f() {
      x.clearRect(0, 0, W, H);
      for (const p of P) { p.x += p.vx; p.y += p.vy; p.vy += 0.25; p.vx *= 0.99; p.a += p.s; x.save(); x.translate(p.x, p.y); x.rotate(p.a); x.fillStyle = p.c; x.fillRect(-3, -4, 6, 8); x.restore(); }
      if (++t < 130) requestAnimationFrame(f); else c.remove();
    })();
  }
  window.frogBoom = boom;

  // ---------- screens ----------
  function setupHome() {
    const v = $("view-home");
    if (!v || v.querySelector(".fh")) return;
    const nav = v.querySelector(".home-nav");
    const h = hero(v, "green", { ill: FROG(78), seed: 1, after: nav, move: [v.querySelector(".modern-overview"), v.querySelector(".status-card")] });
    h.id = "fhHome";
    liveNumber($("modernRemaining"));
    const ref = $("refHomeCard");
    if (ref && !ref.classList.contains("fh")) {
      ref.classList.add("fh", "fh-indigo", "fh-ref");
      const ill = D.createElement("div");
      ill.className = "fh-ill";
      ill.innerHTML = `<div>${EMO("🎁")}</div>`;
      ref.insertBefore(ill, ref.firstChild);
      sparkle(ref, 5);
    }
  }
  function paintHome() {
    const h = $("fhHome"), me = window.__me;
    if (!h || !me) return;
    const devs = (me.devices || []).length;
    const paused = !!me.billing_paused || (devs > 0 && me.has_access === false) || (devs > 0 && Number(me.balance_rub) <= 0);
    const low = !paused && devs > 0 && Number(me.days_left != null ? me.days_left : me.days) <= 3;
    const color = paused ? "red" : low ? "orange" : "green";
    h.className = h.className.replace(/\bfh-(green|orange|red)\b/, "fh-" + color);
    ribbon(h, paused ? "пауза" : devs ? "VPN вкл" : "");
    setIll(h, FROG(78, paused));
  }

  function setupViews() {
    const top = $("view-topup");
    if (top) {
      const h = hero(top, "blue", { ill: GEM(68), seed: 2, move: [top.querySelector(".topup-head"), top.querySelector(".topup-card")] });
      if (h) liveNumber($("topupSum"));
    }
    const pay = $("view-pay");
    if (pay) hero(pay, "blue", { ill: GEM(60), seed: 3, move: [pay.querySelector(".pay-head")] });
    const wz = $("view-wizard");
    if (wz) hero(wz, "teal", { ill: EMO("📱"), seed: 4, move: [wz.querySelector(".view-head"), $("wizLead")] });
    const dv = $("view-device");
    if (dv) hero(dv, "teal", { ill: EMO("📱"), seed: 6, move: [dv.querySelector(".view-head")] });
    const sp = $("view-support");
    if (sp) hero(sp, "green", { ill: FROG(60), seed: 7, cls: "fh-compact", move: [sp.querySelector(".support-head")] });
    const fq = $("view-faq");
    if (fq) hero(fq, "orange", { ill: EMO("💡"), seed: 8, move: [fq.querySelector(".view-head"), fq.querySelector(".topup-hint")] });
    const bl = $("view-billing");
    if (bl) hero(bl, "slate", { ill: EMO("🧾"), seed: 9, move: [bl.querySelector(".view-head"), $("billingSummary")] });
    const of = $("view-offer");
    if (of) {
      const st = of.querySelector(".offer-stage");
      const h = hero(of, "purple", { ill: EMO("🎁"), seed: 10, move: [st && st.querySelector(".offer-kicker"), st && st.querySelector(".offer-title"), $("offerLead"), $("offerTry")] });
      if (h && st) st.before(h);
    }
    // bottom sheets
    const lb = $("lowBalanceSheet");
    if (lb && !lb.querySelector(".fh")) {
      const h = hero(lb, "red", { ill: FROG(72, true), seed: 11, move: [lb.querySelector(".balance-alert-wallet"), $("lowBalanceTitle"), $("lowBalanceDescription")] });
      ribbon(h, "пауза");
      const close = $("lowBalanceClose");
      if (close) h.appendChild(close);
      const grab = $("lowBalanceGrab");
      if (grab) lb.insertBefore(grab, lb.firstChild);
    }
    const ex = $("exitFeedbackSheet");
    if (ex && !ex.querySelector(".fh")) {
      const h = hero(ex, "slate", { ill: FROG(64, true), seed: 12, move: [$("exitFeedbackTitle"), $("exitFeedbackDescription")] });
      const close = $("exitFeedbackClose");
      if (close) h.appendChild(close);
    }
  }

  function paintWizard() {
    const h = $("view-wizard") && $("view-wizard").querySelector(".fh");
    if (!h) return;
    const t = ($("wizTitle") && $("wizTitle").textContent) || "";
    const step = ($("wizStep") && $("wizStep").textContent) || "";
    let ill = EMO("📱");
    if (/прилож/i.test(t)) {
      const logo = D.querySelector("#wizStoreBtn .wiz-app-logo img");
      ill = logo ? `<img src="${logo.getAttribute("src")}" width="88" height="88" alt="" style="border-radius:22px">` : EMO("📲");
    } else if (/подключ|ключ|готов/i.test(t) || /из 2$/.test(step) && /2 из/.test(step)) ill = EMO("🛡️");
    setIll(h, ill);
  }
  function paintDevice() {
    const h = $("view-device") && $("view-device").querySelector(".fh");
    if (!h) return;
    const s = (($("devStatusText") && $("devStatusText").textContent) || "").toLowerCase();
    ribbon(h, s.includes("актив") || s.includes("подключ") || s.includes("онлайн") ? "онлайн" : s.includes("пауз") || s.includes("неактив") ? "пауза" : "");
  }

  // Replay the card entrance whenever a view becomes visible.
  function watchViews() {
    D.querySelectorAll("#app > .view").forEach((v) => {
      new MutationObserver(() => {
        if (v.classList.contains("hidden")) return;
        const h = v.querySelector(".fh");
        if (h) { replay(h, "fh-in"); replay(h.querySelector(".fh-ill"), "fh-pop"); }
        if (v.id === "view-wizard") paintWizard();
        if (v.id === "view-device") paintDevice();
        if (v.id === "view-home") paintHome();
      }).observe(v, { attributes: true, attributeFilter: ["class"] });
    });
    const wt = $("wizTitle");
    if (wt) new MutationObserver(paintWizard).observe(wt, { childList: true, characterData: true, subtree: true });
    const ds = $("devStatusText");
    if (ds) new MutationObserver(paintDevice).observe(ds, { childList: true, characterData: true, subtree: true });
  }

  // ---------- "Баланс пополнен" ----------
  function creditSheet(delta, balance, me) {
    if ($("fhCredit")) return;
    const price = Math.max(1, Number(me.vpn_day_price_rub) || 6) * Math.max(1, (me.devices || []).length);
    const days = Math.floor(balance / price);
    const until = new Date(Date.now() + days * 864e5).toLocaleDateString("ru-RU", { day: "numeric", month: "long" });
    const wrap = D.createElement("div");
    wrap.id = "fhCredit";
    wrap.className = "fh-credit";
    wrap.innerHTML = `<div class="fh-credit-sheet"><section class="fh fh-green fh-in"><div class="fh-ov"></div><div class="fh-rb">зачислено</div><div class="fh-ill fh-pop"><div>${FROG(110)}</div></div>
      <div class="fh-body"><div class="fh-n" id="fhCreditN">+0 ₽</div><div class="fh-p">Баланс пополнен</div></div></section>
      <div class="fh-rows"><div><span>Баланс</span><b>${fmt(balance)} ₽</b></div>${(me.devices || []).length ? `<div><span>Хватит до</span><b>${until}</b></div>` : ""}</div>
      <button type="button" class="fh-ok">Отлично</button></div>`;
    D.body.appendChild(wrap);
    sparkle(wrap.querySelector(".fh"), 13);
    const close = () => { wrap.classList.add("out"); setTimeout(() => wrap.remove(), 300); };
    wrap.querySelector(".fh-ok").onclick = close;
    wrap.onclick = (e) => { if (e.target === wrap) close(); };
    requestAnimationFrame(() => wrap.classList.add("on"));
    const n = $("fhCreditN");
    setTimeout(() => {
      countUp(n, 0, delta, (x) => { n.textContent = "+" + fmt(x) + " ₽"; });
      boom();
      try { window.Telegram.WebApp.HapticFeedback.notificationOccurred("success"); } catch (_e) {}
    }, 250);
  }
  function watchBalance() {
    let seen = null;
    setInterval(() => {
      const me = window.__me;
      if (!me || me === seen || !me.user) return;
      seen = me;
      paintHome();
      const key = "frog_bal_" + me.user.id;
      const bal = Math.round(Number(me.balance_rub) || 0);
      let prev = null;
      try { prev = localStorage.getItem(key); localStorage.setItem(key, String(bal)); } catch (_e) {}
      if (prev != null && prev !== "" && bal - Number(prev) >= 10 && me.has_paid_topup) creditSheet(bal - Number(prev), bal, me);
    }, 400);
  }

  function init() {
    setupHome();
    setupViews();
    watchViews();
    watchBalance();
    paintHome();
  }
  if (D.readyState === "loading") D.addEventListener("DOMContentLoaded", init);
  else init();
})();
