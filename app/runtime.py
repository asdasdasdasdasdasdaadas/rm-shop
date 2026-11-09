from __future__ import annotations

import asyncio

webapp_url = ""
tunnel_proc = None
bot = None
rw = None  # the Remnawave client, set at startup
_panel_cron: asyncio.Lock | None = None


def panel_cron_lock() -> asyncio.Lock:
    global _panel_cron
    if _panel_cron is None:
        _panel_cron = asyncio.Lock()
    return _panel_cron
