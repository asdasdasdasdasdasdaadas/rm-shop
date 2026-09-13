(function () {
  const STATE_LABEL = { busy: "занят", idle: "на месте", offline: "офлайн" };
  const POLL_MS = 5000;
  let timer = 0;
  let running = false;

  function $(id) {
    return document.getElementById(id);
  }

  function fmtAgo(dt) {
    if (!dt) return "ещё не отмечался";
    const d = new Date(dt);
    if (Number.isNaN(d.getTime())) return "ещё не отмечался";
    const sec = Math.round((Date.now() - d.getTime()) / 1000);
    if (sec < 90) return "только что";
    if (sec < 3600) return Math.floor(sec / 60) + " мин назад";
    if (sec < 86400) return Math.floor(sec / 3600) + " ч назад";
    return d.toLocaleString("ru-RU");
  }

  function paint(data) {
    const room = $("officeRoom");
    const err = $("officeErr");
    const meta = $("officeMeta");
    if (err) err.classList.add("hidden");
    const agents = (data && data.agents) || [];
    agents.forEach((agent) => {
      const desk = room && room.querySelector('.office-desk[data-agent="' + agent.id + '"]');
      if (!desk) return;
      const state = agent.state === "busy" || agent.state === "idle" ? agent.state : "offline";
      desk.classList.toggle("is-busy", state === "busy");
      desk.classList.toggle("is-idle", state === "idle");
      desk.classList.toggle("is-offline", state === "offline");
      const plate = desk.querySelector(".agent-plate");
      if (!plate) return;
      const nameEl = plate.querySelector(".agent-name");
      const roleEl = plate.querySelector(".agent-role");
      const stateEl = plate.querySelector(".agent-state");
      const doingEl = plate.querySelector(".agent-doing");
      const agoEl = plate.querySelector(".agent-ago");
      if (nameEl) nameEl.textContent = agent.name || agent.id;
      if (roleEl) roleEl.textContent = agent.role || "";
      if (stateEl) stateEl.textContent = STATE_LABEL[state] || state;
      if (doingEl) {
        doingEl.textContent = agent.message || (state === "offline" ? "тишина" : "без комментария");
        doingEl.title = agent.message || "";
      }
      if (agoEl) agoEl.textContent = fmtAgo(agent.updated_at || agent.source_ts);
    });
    if (meta) {
      const minutes = data && data.stale_minutes ? data.stale_minutes : 8;
      meta.textContent = "Опрос каждые 5 сек · офлайн после " + minutes + " мин без сигнала · " + new Date().toLocaleTimeString("ru-RU");
    }
  }

  async function tick() {
    if (!running) return;
    try {
      const res = await fetch("/admin/api/office", { credentials: "same-origin" });
      const data = await res.json().catch(() => ({ ok: false, error: "Ошибка ответа" }));
      if (!res.ok || data.ok === false) throw new Error(data.error || "Нет доступа");
      paint(data);
    } catch (err) {
      const box = $("officeErr");
      if (box) {
        box.textContent = (err && err.message) || "Не удалось загрузить офис";
        box.classList.remove("hidden");
      }
    }
    if (running) {
      clearTimeout(timer);
      timer = setTimeout(tick, POLL_MS);
    }
  }

  window.OfficeBoard = {
    start() {
      if (running) return;
      running = true;
      tick();
    },
    stop() {
      running = false;
      clearTimeout(timer);
      timer = 0;
    },
  };

  const hashTab = (location.hash || "").replace(/^#/, "").split("?")[0];
  if (hashTab === "office") {
    window.OfficeBoard.start();
  }
})();
