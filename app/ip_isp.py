"""Which provider an IP belongs to (МТС, Билайн, Ростелеком…), looked up on our own server.

The table is the public IP-to-ASN dump from iptoasn.com (ranges → AS number, country, AS name), downloaded
into data/ once a week. Lookups never send a client's IP anywhere. Until the file is there, lookups return None.
"""
from __future__ import annotations

import asyncio
import gzip
import ipaddress
import logging
import os
import re
import time
from array import array
from bisect import bisect_right
from pathlib import Path

from app.config import ROOT

logger = logging.getLogger("rm-shop.ip-isp")

SOURCE_URL = "https://iptoasn.com/data/ip2asn-combined.tsv.gz"
FILE = ROOT / "data" / "ip2asn-combined.tsv.gz"
REFRESH_DAYS = 7
RETRY_SECONDS = 6 * 3600

# AS names are cryptic («PVIMPELCOM», «MTSNET»): the big Russian ones by a name people know.
KNOWN = (
    (r"\bT2[- ]?MOBILE|TELE2", "Tele2", "мобильный"),
    (r"SCARTEL|\bYOTA", "Yota", "мобильный"),
    (r"MEGAFON|SONIC.?DUO|NETBYNET", "МегаФон", ""),
    (r"VIMPELCOM|BEELINE|CORBINA", "Билайн", ""),
    (r"\bMGTS\b|MOSCOW CITY TELEPHONE", "МГТС", "домашний"),
    (r"\bMTS\b|MTSNET|MOBILE TELESYSTEMS", "МТС", ""),
    (r"ROSTELECOM|\bRTCOMM", "Ростелеком", ""),
    (r"ER-TELECOM|DOM\.RU", "Дом.ру", "домашний"),
    (r"TRANSTELECOM|\bTTK\b", "ТТК", "домашний"),
    (r"AKADO", "Акадо", "домашний"),
    (r"KYIVSTAR", "Киевстар", ""),
    (r"KAZTELECOM|KAZAKHTELECOM", "Казахтелеком", ""),
)
_KNOWN = [(re.compile(p, re.I), name, kind) for p, name, kind in KNOWN]


class _Index:
    def __init__(self) -> None:
        self.v4_start, self.v4_end, self.v4_ref = array("I"), array("I"), array("I")
        self.v6_start: list[int] = []
        self.v6_end: list[int] = []
        self.v6_ref: list[int] = []
        self.meta: list[tuple[int, str, str]] = []   # (asn, country, AS name), shared by many ranges

    def lookup(self, ip: str) -> tuple[int, str, str] | None:
        try:
            addr = ipaddress.ip_address(ip.strip().strip("[]"))
        except ValueError:
            return None
        if addr.version == 6 and addr.ipv4_mapped:
            addr = addr.ipv4_mapped
        n = int(addr)
        starts, ends, refs = ((self.v4_start, self.v4_end, self.v4_ref) if addr.version == 4
                              else (self.v6_start, self.v6_end, self.v6_ref))
        i = bisect_right(starts, n) - 1
        if i < 0 or n > ends[i]:
            return None
        meta = self.meta[refs[i]]
        return meta if meta[0] else None   # AS 0: not routed


def load(path: Path = FILE) -> _Index:
    idx, seen = _Index(), {}
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 5:
                continue
            try:
                start, end, asn = ipaddress.ip_address(parts[0]), ipaddress.ip_address(parts[1]), int(parts[2])
            except ValueError:
                continue
            key = (asn, parts[3], parts[4])
            ref = seen.get(key)
            if ref is None:
                ref = seen[key] = len(idx.meta)
                idx.meta.append(key)
            if start.version == 4:
                idx.v4_start.append(int(start)); idx.v4_end.append(int(end)); idx.v4_ref.append(ref)
            else:
                idx.v6_start.append(int(start)); idx.v6_end.append(int(end)); idx.v6_ref.append(ref)
    return idx


_index: _Index | None = None
_loaded_mtime = 0.0


# Same AS name for home and mobile: the mobile networks by number.
MOBILE_AS = {31133: "МегаФон", 16345: "Билайн", 15378: "Tele2", 12958: "Tele2", 48190: "Tele2"}
# A client coming from a data centre most likely has another VPN or proxy turned on.
HOSTING = re.compile(r"SELECTEL|TIMEWEB|AEZA|REG\.?RU|BEGET|CLOUD\.RU|EDGECENTER|HETZNER|DIGITALOCEAN|AMAZON|"
                     r"\bOVH|M247|DATACAMP|CLOUDFLARE|LINODE|AKAMAI|VULTR|CHOOPA|CONTABO|SERVERS\.COM|GCORE|"
                     r"\bHOSTING\b|DATACENTER|DATA CENTER|\bVDS\b|\bVPS", re.I)
_LEGAL = re.compile(r'\b(?:PJSC|OJSC|CJSC|JSC|LLC|Ltd|Limited Liability Company|Joint Stock Company|Inc|GmbH)\b\.?|B\.V\.|[",]', re.I)


def label(asn: int, country: str, name: str) -> dict:
    """{asn, country, name, kind, raw}: a known name when there is one, else the AS name made readable."""
    if asn in MOBILE_AS:
        return {"asn": asn, "country": country, "name": MOBILE_AS[asn], "kind": "мобильный", "raw": name}
    for rx, known, kind in _KNOWN:
        if rx.search(name):
            return {"asn": asn, "country": country, "name": known, "kind": kind, "raw": name}
    # «TimeWeb-AS JSC "TIMEWEB"», «CLOUDFLARENET - Cloudflare, Inc.»: drop the AS handle and the legal form
    head, _, rest = name.partition(" ")
    org = rest.removeprefix("- ").strip() if rest and head == head.split()[0] else name
    short = re.sub(r"\s+", " ", _LEGAL.sub(" ", org)).strip(" -") or head
    return {"asn": asn, "country": country, "name": short[:48], "kind": "хостинг" if HOSTING.search(name) else "",
            "raw": name}


def lookup(ip: str) -> dict | None:
    """The provider of this IP, or None (no table yet, private or unknown address)."""
    if _index is None or not ip:
        return None
    got = _index.lookup(str(ip))
    return label(*got) if got else None


async def device_providers(device_id: int) -> list[dict]:
    """The providers this device came from in the last day, newest first, one entry per provider."""
    from app import db
    out, seen = [], set()
    for row in await db.device_ips_recent(int(device_id)):
        info = lookup(row["ip"])
        if info and info["name"] not in seen:
            seen.add(info["name"])
            out.append(info)
    return out


def text(info: dict | None) -> str:
    if not info:
        return ""
    extra = ", ".join(x for x in (info.get("kind"), info.get("country")) if x)
    return info["name"] + (f" ({extra})" if extra else "")


async def ensure(path: Path = FILE) -> bool:
    """Load the table from disk when it is new or changed; True when lookups work."""
    global _index, _loaded_mtime
    try:
        mtime = path.stat().st_mtime
    except FileNotFoundError:
        return _index is not None
    if _index is None or mtime != _loaded_mtime:
        started = time.monotonic()
        try:
            _index = await asyncio.to_thread(load, path)
        except Exception:
            logger.warning("Таблица провайдеров не прочиталась: %s", path, exc_info=True)
            return _index is not None
        _loaded_mtime = mtime
        logger.info("Провайдеры по IP: %s диапазонов за %.1f с",
                    len(_index.v4_start) + len(_index.v6_start), time.monotonic() - started)
    return True


async def download(path: Path = FILE) -> bool:
    import aiohttp
    tmp = path.with_suffix(".part")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=300)) as http:
            async with http.get(SOURCE_URL) as resp:
                resp.raise_for_status()
                with open(tmp, "wb") as fh:
                    async for chunk in resp.content.iter_chunked(1 << 16):
                        fh.write(chunk)
        await asyncio.to_thread(load, tmp)   # a broken download never replaces a good table
        os.replace(tmp, path)
        return True
    except Exception:
        logger.warning("Таблица провайдеров не скачалась", exc_info=True)
        tmp.unlink(missing_ok=True)
        return False


def _stale(path: Path = FILE) -> bool:
    try:
        return time.time() - path.stat().st_mtime > REFRESH_DAYS * 86400
    except FileNotFoundError:
        return True


async def refresh_loop() -> None:
    while True:
        if _stale():
            await download()
        await ensure()
        await asyncio.sleep(RETRY_SECONDS)
