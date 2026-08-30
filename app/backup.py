from __future__ import annotations

import asyncio
import gzip
import json
import logging
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aiogram import Bot
from aiogram.types import BufferedInputFile

from app import db
from app.config import ROOT, get_settings

logger = logging.getLogger("rm-shop.backup")
MSK = timezone(timedelta(hours=3))
TG_FILE_LIMIT = 49 * 1024 * 1024
_lock = asyncio.Lock()
SAFE_NAME = re.compile(r"^rm-shop-\d{4}-\d{2}-\d{2}T\d{4}-MSK\.sql\.gz$")


def backup_dir() -> Path:
    path = ROOT / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _stamp() -> str:
    return datetime.now(MSK).strftime("%Y-%m-%dT%H%M-MSK")


def list_backups() -> list[dict]:
    items = []
    for path in sorted(backup_dir().glob("rm-shop-*.sql.gz"), reverse=True):
        stat = path.stat()
        items.append(
            {
                "name": path.name,
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            }
        )
    return items


def backup_path(name: str) -> Path | None:
    if not SAFE_NAME.match(name):
        return None
    path = (backup_dir() / name).resolve()
    if path.parent != backup_dir().resolve() or not path.is_file():
        return None
    return path


def _prune() -> None:
    keep_days = max(1, get_settings().backup_keep_days)
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
    files = sorted(backup_dir().glob("rm-shop-*.sql.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    for i, path in enumerate(files):
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if i >= 7 and mtime < cutoff:
            try:
                path.unlink()
            except OSError:
                logger.exception("Не удалось удалить старый бэкап %s", path.name)


def _sql_literal(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, (dict, list)):
        dumped = json.dumps(value, ensure_ascii=False)
        return "'" + dumped.replace("'", "''") + "'"
    if isinstance(value, datetime):
        return "'" + value.isoformat() + "'"
    if isinstance(value, bytes):
        return r"'\x" + value.hex() + "'"
    text = str(value).replace("'", "''")
    return "'" + text + "'"


async def _dump_via_sql() -> bytes:
    pool = db._pool_req()
    async with pool.acquire() as conn:
        tables = await conn.fetch(
            """
            SELECT tablename
            FROM pg_catalog.pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
            """
        )
        names = [str(r["tablename"]) for r in tables]
        chunks = [
            "-- rm-shop backup",
            "SET client_encoding = 'UTF8';",
            "BEGIN;",
        ]
        if names:
            quoted = ", ".join('"' + n.replace('"', '""') + '"' for n in names)
            chunks.append(f"TRUNCATE TABLE {quoted} CASCADE;")
        for name in names:
            qname = '"' + name.replace('"', '""') + '"'
            cols = await conn.fetch(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = $1
                ORDER BY ordinal_position
                """,
                name,
            )
            col_names = [str(c["column_name"]) for c in cols]
            if not col_names:
                continue
            col_sql = ", ".join('"' + c.replace('"', '""') + '"' for c in col_names)
            rows = await conn.fetch(f"SELECT * FROM {qname}")
            for row in rows:
                values = ", ".join(_sql_literal(row[c]) for c in col_names)
                chunks.append(f"INSERT INTO {qname} ({col_sql}) VALUES ({values});")
            for col in col_names:
                seq = await conn.fetchval("SELECT pg_get_serial_sequence($1, $2)", name, col)
                if not seq:
                    continue
                qcol = '"' + col.replace('"', '""') + '"'
                chunks.append(
                    f"SELECT setval('{seq}', COALESCE((SELECT MAX({qcol}) FROM {qname}), 1), true);"
                )
        chunks.append("COMMIT;")
        return ("\n".join(chunks) + "\n").encode("utf-8")


async def _dump_via_pg_dump() -> bytes:
    pg_dump = shutil.which("pg_dump")
    if not pg_dump:
        raise FileNotFoundError("pg_dump")
    proc = await asyncio.create_subprocess_exec(
        pg_dump,
        "--no-owner",
        "--no-acl",
        "--dbname",
        get_settings().database_url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError((err or out or b"pg_dump failed").decode("utf-8", "replace")[:500])
    if not out:
        raise RuntimeError("pg_dump вернул пустой дамп")
    return out


async def create_backup(*, reason: str, bot: Bot | None) -> dict:
    async with _lock:
        try:
            raw = await _dump_via_pg_dump()
            method = "pg_dump"
        except Exception as exc:
            logger.warning("pg_dump недоступен (%s), пишу SQL через приложение", exc)
            raw = await _dump_via_sql()
            method = "sql"
        packed = gzip.compress(raw, compresslevel=6)
        name = f"rm-shop-{_stamp()}.sql.gz"
        path = backup_dir() / name
        path.write_bytes(packed)
        _prune()
        sent = 0
        failed = 0
        settings = get_settings()
        caption = (
            f"Бэкап базы ({reason})\n"
            f"{name}\n"
            f"{len(packed)} байт, способ: {method}"
        )
        if bot and settings.admin_id_set and len(packed) <= TG_FILE_LIMIT:
            document = BufferedInputFile(packed, filename=name)
            for admin_id in settings.admin_id_set:
                try:
                    await bot.send_document(
                        admin_id,
                        BufferedInputFile(packed, filename=name),
                        caption=caption,
                    )
                    sent += 1
                except Exception:
                    failed += 1
                    logger.exception("Не удалось отправить бэкап админу %s", admin_id)
        elif bot and settings.admin_id_set and len(packed) > TG_FILE_LIMIT:
            note = caption + "\nФайл слишком большой для Telegram, лежит на диске."
            for admin_id in settings.admin_id_set:
                try:
                    await bot.send_message(admin_id, note)
                    sent += 1
                except Exception:
                    failed += 1
        logger.info("Бэкап %s готов, sent=%s failed=%s", name, sent, failed)
        return {
            "ok": True,
            "name": name,
            "size": len(packed),
            "method": method,
            "sent": sent,
            "failed": failed,
            "telegram": bool(settings.admin_id_set),
        }


def seconds_until_msk_0001() -> float:
    now = datetime.now(MSK)
    target = now.replace(hour=0, minute=1, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    return max(1.0, (target - now).total_seconds())


async def backup_loop(bot: Bot) -> None:
    while True:
        wait = seconds_until_msk_0001()
        logger.info("Следующий автобэкап через %.0f сек (00:01 МСК)", wait)
        await asyncio.sleep(wait)
        try:
            await create_backup(reason="расписание 00:01 МСК", bot=bot)
        except Exception:
            logger.exception("Автобэкап не удался")
            await asyncio.sleep(60)
