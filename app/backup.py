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

from app import db
from app.config import ROOT, get_settings

logger = logging.getLogger("rm-shop.backup")
MSK = timezone(timedelta(hours=3))
_lock = asyncio.Lock()
SAFE_NAME = re.compile(r"^rm-shop-\d{4}-\d{2}-\d{2}T\d{4}-MSK(-imported)?\.sql\.gz$")


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


async def create_backup(*, reason: str) -> dict:
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
        logger.info("Бэкап %s готов (%s, %s байт)", name, reason, len(packed))
        return {
            "ok": True,
            "name": name,
            "size": len(packed),
            "method": method,
        }


def seconds_until_msk_0001() -> float:
    now = datetime.now(MSK)
    target = now.replace(hour=0, minute=1, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    return max(1.0, (target - now).total_seconds())


async def _prune_billing_events() -> None:
    days = get_settings().billing_events_keep_days
    n = await db.purge_old_billing_events(days)
    if n:
        logger.info("Удалены старые события биллинга: %s", n)


async def backup_loop(_bot: Bot | None = None) -> None:
    await asyncio.sleep(45)
    try:
        await _prune_billing_events()
    except Exception:
        logger.exception("Очистка billing_events не удалась")
    while True:
        wait = seconds_until_msk_0001()
        logger.info("Следующий автобэкап через %.0f сек (00:01 МСК)", wait)
        await asyncio.sleep(wait)
        try:
            await create_backup(reason="расписание 00:01 МСК")
        except Exception:
            logger.exception("Автобэкап не удался")
            await asyncio.sleep(60)
            continue
        try:
            await _prune_billing_events()
        except Exception:
            logger.exception("Очистка billing_events не удалась")


MAX_UPLOAD = 80 * 1024 * 1024


def _unpack_dump(data: bytes, filename: str) -> bytes:
    name = (filename or "").lower()
    if name.endswith(".gz") or data[:2] == b"\x1f\x8b":
        try:
            data = gzip.decompress(data)
        except OSError as exc:
            raise ValueError("Не удалось распаковать gzip") from exc
    return data


def _sanitize_dump(sql: bytes) -> bytes:
    kept: list[bytes] = []
    for line in sql.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith(b"\\restrict") or stripped.startswith(b"\\unrestrict"):
            continue
        if stripped.lower().startswith(b"set transaction_timeout"):
            continue
        kept.append(line)
    return b"".join(kept)


def _validate_dump(sql: bytes) -> str:
    head = sql[:8000].decode("utf-8", "replace")
    if "PostgreSQL database dump" in head:
        kind = "pg_dump"
    elif "rm-shop backup" in head:
        kind = "sql"
    else:
        raise ValueError("Файл не похож на бэкап PostgreSQL этого бота")
    low = sql.lower()
    if b"copy " in low and b" program " in low:
        raise ValueError("В дампе запрещена конструкция COPY PROGRAM")
    return kind


async def _run_psql(payload: bytes) -> None:
    psql = shutil.which("psql")
    if not psql:
        raise RuntimeError("В контейнере нет psql. Пересоберите образ бота.")
    proc = await asyncio.create_subprocess_exec(
        psql,
        "--dbname",
        get_settings().database_url,
        "-v",
        "ON_ERROR_STOP=1",
        "--quiet",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _out, err = await proc.communicate(payload)
    if proc.returncode != 0:
        raise RuntimeError((err or b"psql error").decode("utf-8", "replace")[:800])


async def restore_backup(data: bytes, filename: str) -> dict:
    if len(data) > MAX_UPLOAD:
        raise ValueError("Файл больше 80 МБ")
    sql = _sanitize_dump(_unpack_dump(data, filename))
    if not sql.strip():
        raise ValueError("Пустой дамп")
    kind = _validate_dump(sql)
    prelude = (
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        "WHERE datname = current_database() AND pid <> pg_backend_pid();\n"
        "DROP SCHEMA IF EXISTS public CASCADE;\n"
        "CREATE SCHEMA public;\n"
        "GRANT ALL ON SCHEMA public TO CURRENT_USER;\n"
        "GRANT ALL ON SCHEMA public TO public;\n"
    ).encode("utf-8")
    async with _lock:
        await db.close_db()
        schema_ready = False
        try:
            if kind == "pg_dump":
                await _run_psql(prelude + sql)
            else:
                await db.init_db()
                schema_ready = True
                await _run_psql(sql)
        finally:
            if not schema_ready:
                await db.init_db()
        saved = backup_dir() / f"rm-shop-{_stamp()}-imported.sql.gz"
        saved.write_bytes(gzip.compress(sql, compresslevel=6))
        _prune()
        logger.info("Импорт бэкапа %s (%s) завершён", filename, kind)
        return {"ok": True, "filename": filename, "kind": kind, "bytes": len(sql)}
