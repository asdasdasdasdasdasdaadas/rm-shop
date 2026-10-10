"""Ambassador attribution and accounting. Mutations serialize before locking users."""

import json
import secrets
from datetime import datetime
from app import db
from app.config import get_settings

LOCK = 73619421


def public(row):
    return {
        k: v.isoformat() if isinstance(v, datetime) else v for k, v in dict(row).items()
    }


async def lock(conn):
    await conn.execute("SELECT pg_advisory_xact_lock($1)", LOCK)


async def audit(conn, action, target, details):
    await conn.execute(
        "INSERT INTO ambassador_audit(action,target,details) VALUES($1,$2,$3::jsonb)",
        action,
        str(target),
        json.dumps(details, ensure_ascii=False),
    )


async def notify(conn, uid, body):
    await conn.execute(
        "INSERT INTO ambassador_notifications(telegram_id,body) VALUES($1,$2)",
        uid,
        body,
    )


async def settings(conn=None):
    return dict(
        await (conn or db._pool_req()).fetchrow(
            "SELECT * FROM ambassador_settings WHERE id=1"
        )
    )


async def register_new(telegram_id, username, first_name, token):
    """Only a new database user can be attributed; existing referral ownership is untouched."""
    async with db._pool_req().acquire() as conn:
        async with conn.transaction():
            await lock(conn)
            member = await conn.fetchrow(
                "SELECT * FROM ambassadors WHERE token=$1 AND status='approved'", token
            )
            if not member or member["telegram_id"] == telegram_id:
                return False
            # Keep attribution during a pause; only new payments can earn after resuming.
            created = await conn.fetchval(
                """INSERT INTO users(telegram_id,username,first_name)
                VALUES($1,$2,$3) ON CONFLICT DO NOTHING RETURNING telegram_id""",
                telegram_id,
                username,
                first_name,
            )
            if not created:
                return False
            await conn.execute(
                "INSERT INTO ambassador_clients(telegram_id,ambassador_id) VALUES($1,$2) ON CONFLICT DO NOTHING",
                telegram_id,
                member["telegram_id"],
            )
            return True


async def reward(conn, receipt):
    """Called inside the payment credit transaction with LOCK already held."""
    uid = receipt["telegram_id"]
    owner = await conn.fetchrow(
        """SELECT a.* FROM ambassadors a JOIN ambassador_clients c ON c.ambassador_id=a.telegram_id
        WHERE c.telegram_id=$1""",
        uid,
    )
    if not owner:
        return
    await conn.execute(
        "UPDATE payment_receipts SET ambassador_id=$2 WHERE payment_key=$1",
        receipt["payment_key"],
        owner["telegram_id"],
    )
    receipt["ambassador_id"] = owner["telegram_id"]
    cfg = await settings(conn)
    eligible = not receipt["router_days"] and receipt["payment_key"].startswith(
        "rollypay:"
    )
    first = not await conn.fetchval(
        "SELECT 1 FROM ambassador_awards WHERE client_id=$1 AND eligible LIMIT 1", uid
    )
    percent = cfg["first_percent"] if first else cfg["recurring_percent"]
    amount = receipt["amount"] * percent
    if first:
        amount = min(amount, cfg["first_cap"] * 100)
    # Ruble topups only. Stars stay outside the program.
    reason = ""
    if not eligible:
        reason = "Stars не участвуют"
    elif not cfg["accruing"] or owner["status"] != "approved":
        reason = "Начисления приостановлены"
    elif not amount:
        reason = "Нулевое вознаграждение"
    else:
        spent = await conn.fetchval(
            "SELECT COALESCE(SUM(amount_cents),0)::bigint FROM ambassador_awards WHERE status<>'skipped'"
        )
        personal = await conn.fetchval(
            "SELECT COALESCE(SUM(amount_cents),0)::bigint FROM ambassador_awards WHERE ambassador_id=$1 AND status<>'skipped'",
            owner["telegram_id"],
        )
        if spent + amount > cfg["budget"] * 100:
            reason = "Бюджет программы исчерпан"
        elif cfg["member_cap"] and personal + amount > cfg["member_cap"] * 100:
            reason = "Лимит участника исчерпан"
    inserted = await conn.fetchval(
        """INSERT INTO ambassador_awards(payment_key,ambassador_id,client_id,payment_rub,
        amount_cents,first_payment,percent,cap_rub,hold_days,available_at,status,reason,eligible)
        VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,NOW()+($9::int*INTERVAL '1 day'),$10,$11,$12)
        ON CONFLICT DO NOTHING RETURNING payment_key""",
        receipt["payment_key"],
        owner["telegram_id"],
        uid,
        receipt["amount"],
        0 if reason else amount,
        first,
        percent,
        cfg["first_cap"],
        cfg["hold_days"],
        "skipped" if reason else "earned",
        reason,
        eligible,
    )
    if inserted and not reason:
        await notify(
            conn,
            owner["telegram_id"],
            f"🎉 Вам начислено {amount/100:.2f} ₽ за оплату клиента. Средства доступны к выводу через {cfg['hold_days']} дней, если платёж не возвращён. Подробности — в разделе «Амбассадор».",
        )


async def wallet(uid, conn=None):
    pool = conn or db._pool_req()
    r = dict(
        await pool.fetchrow(
            """SELECT
      COALESCE(SUM(amount_cents) FILTER(WHERE status='earned'),0)::bigint AS earned,
      COALESCE(SUM(amount_cents) FILTER(WHERE status='earned' AND available_at>NOW()),0)::bigint AS holding,
      COALESCE(SUM(amount_cents) FILTER(WHERE status='earned' AND available_at<=NOW()),0)::bigint AS mature
      FROM ambassador_awards WHERE ambassador_id=$1""",
            uid,
        )
    )
    p = await pool.fetchrow(
        "SELECT COALESCE(SUM(amount_cents) FILTER(WHERE status='pending'),0)::bigint AS pending, COALESCE(SUM(amount_cents) FILTER(WHERE status='paid'),0)::bigint AS paid FROM ambassador_payouts WHERE ambassador_id=$1",
        uid,
    )
    r.update(dict(p))
    r["available"] = r.pop("mature") - r["pending"] - r["paid"]
    return r


async def overview(uid):
    pool = db._pool_req()
    cfg = await settings()
    member = await pool.fetchrow("SELECT * FROM ambassadors WHERE telegram_id=$1", uid)
    stats = await pool.fetchrow(
        """SELECT COUNT(*)::int AS joined,
        COUNT(*) FILTER(WHERE u.first_online_at IS NOT NULL)::int AS connected,
        COUNT(*) FILTER(WHERE EXISTS(SELECT 1 FROM ambassador_awards a WHERE a.client_id=c.telegram_id AND a.eligible AND a.status<>'revoked'))::int AS paid,
        COUNT(*) FILTER(WHERE (SELECT COUNT(*) FROM ambassador_awards a WHERE a.client_id=c.telegram_id AND a.eligible AND a.status<>'revoked')>=2)::int AS repeat_paid
        FROM ambassador_clients c LEFT JOIN users u ON u.telegram_id=c.telegram_id WHERE c.ambassador_id=$1""",
        uid,
    )
    recent = await pool.fetch(
        "SELECT * FROM ambassador_awards WHERE ambassador_id=$1 ORDER BY created_at DESC,payment_key DESC LIMIT 30",
        uid,
    )
    payouts = await pool.fetch(
        "SELECT * FROM ambassador_payouts WHERE ambassador_id=$1 ORDER BY id DESC LIMIT 30",
        uid,
    )
    limits = await pool.fetchrow(
        """SELECT
        COALESCE(SUM(amount_cents) FILTER(WHERE status<>'skipped'),0)::bigint AS used,
        COALESCE(SUM(amount_cents) FILTER(WHERE status<>'skipped' AND ambassador_id=$1),0)::bigint AS personal,
        MIN(available_at) FILTER(WHERE status='earned' AND ambassador_id=$1 AND available_at>NOW()) AS next_release_at
        FROM ambassador_awards""",
        uid,
    )
    capacity = {
        "budget_remaining": max(0, cfg["budget"] * 100 - limits["used"]),
        "member_remaining": (
            max(0, cfg["member_cap"] * 100 - limits["personal"])
            if cfg["member_cap"]
            else None
        ),
        "next_release_at": public(limits)["next_release_at"],
    }
    return {
        "settings": cfg,
        "capacity": capacity,
        "member": public(member) if member else None,
        "wallet": await wallet(uid),
        "stats": dict(stats),
        "awards": [public(r) for r in recent],
        "payouts": [public(r) for r in payouts],
        "link": (
            f"https://t.me/{get_settings().bot_username.lstrip('@')}?start=amb_{member['token']}"
            if member and member["status"] == "approved"
            else ""
        ),
    }


async def apply(uid, application):
    application = str(application or "").strip()
    if not 10 <= len(application) <= 1500:
        raise ValueError(
            "Расскажите, где будете рекомендовать VPN: от 10 до 1500 символов"
        )
    async with db._pool_req().acquire() as conn:
        async with conn.transaction():
            await lock(conn)
            if not (await settings(conn))["recruitment"]:
                raise ValueError("Набор сейчас закрыт")
            row = await conn.fetchrow(
                "SELECT * FROM ambassadors WHERE telegram_id=$1", uid
            )
            if row and row["status"] != "rejected":
                raise ValueError("Заявка уже подана")
            await conn.execute(
                """INSERT INTO ambassadors(telegram_id,application,token,applied_at)
                VALUES($1,$2,$3,NOW())
                ON CONFLICT(telegram_id) DO UPDATE SET application=$2,status='pending',review_note='',
                    reviewed_at=NULL,applied_at=NOW()""",
                uid,
                application,
                secrets.token_urlsafe(15),
            )
            await audit(conn, "application", uid, {"application": application})
            await notify(
                conn,
                uid,
                "✅ Заявка в амбассадоры отправлена. Сообщим, когда рассмотрим её.",
            )


async def request_payout(uid, details):
    details = str(details or "").strip()
    if not 6 <= len(details) <= 300:
        raise ValueError("Укажите реквизиты и имя получателя: от 6 до 300 символов")
    async with db._pool_req().acquire() as conn:
        async with conn.transaction():
            await lock(conn)
            member = await conn.fetchrow(
                "SELECT * FROM ambassadors WHERE telegram_id=$1", uid
            )
            if (
                not member
                or member["status"] not in ("approved", "suspended")
                or member["risk_hold"]
            ):
                raise ValueError("Вывод пока недоступен. Обратитесь в поддержку")
            w = await wallet(uid, conn)
            cfg = await settings(conn)
            if w["pending"]:
                raise ValueError("Предыдущая заявка ещё на проверке")
            if w["available"] < cfg["payout_min"] * 100:
                raise ValueError(f"Вывод доступен от {cfg['payout_min']} ₽")
            row = await conn.fetchrow(
                "INSERT INTO ambassador_payouts(ambassador_id,amount_cents,details) VALUES($1,$2,$3) RETURNING id",
                uid,
                w["available"],
                details,
            )
            await audit(
                conn,
                "payout_requested",
                row["id"],
                {"telegram_id": uid, "amount_cents": w["available"]},
            )
            await notify(
                conn,
                uid,
                f"✅ Заявка на вывод {w['available']/100:.2f} ₽ принята. Сообщим о результате.",
            )


async def admin_data(page=1, uid=None, section="members", status=""):
    allowed = {
        "members": {"pending", "approved", "rejected", "suspended"},
        "awards": {"earned", "skipped", "revoked"},
        "payouts": {"pending", "paid", "rejected"},
        "audit": set(),
        "settings": set(),
        "clients": set(),
    }
    if section not in allowed or (status and status not in allowed[section]):
        raise ValueError("Неизвестный фильтр")
    pool = db._pool_req()
    offset = (max(1, page) - 1) * 25
    result = {"settings": await settings(), "page": page}
    for name, table, order in [
        ("members", "ambassadors", "created_at DESC,telegram_id"),
        ("awards", "ambassador_awards", "created_at DESC,payment_key"),
        ("payouts", "ambassador_payouts", "id"),
        ("audit", "ambassador_audit", "id"),
    ]:
        filters, args = [], []
        if uid and name != "audit":
            args.append(uid)
            field = "telegram_id" if name == "members" else "ambassador_id"
            filters.append(f"{field}=${len(args)}")
        if status and name == section:
            args.append(status)
            filters.append(f"status=${len(args)}")
        condition = " WHERE " + " AND ".join(filters) if filters else ""
        rows = await pool.fetch(
            f"SELECT * FROM {table}{condition} ORDER BY {order} DESC LIMIT 25 OFFSET ${len(args)+1}",
            *args,
            offset,
        )
        result[name] = [public(r) for r in rows]
        result[name + "_total"] = await pool.fetchval(
            f"SELECT COUNT(*) FROM {table}" + condition,
            *args,
        )
    result["summary"] = dict(await pool.fetchrow("""SELECT
        (SELECT COUNT(*) FROM ambassadors WHERE status='pending')::int AS applications,
        (SELECT COUNT(*) FROM ambassadors WHERE status='approved')::int AS active,
        (SELECT COUNT(*) FROM ambassador_clients)::int AS clients,
        (SELECT COUNT(DISTINCT client_id) FROM ambassador_awards WHERE eligible AND status<>'revoked')::int AS payers,
        (SELECT COALESCE(SUM(amount_cents),0)::bigint FROM ambassador_awards WHERE status<>'skipped')::bigint AS budget_used,
        (SELECT COALESCE(SUM(amount_cents),0)::bigint FROM ambassador_payouts WHERE status='paid')::bigint AS paid,
        (SELECT COALESCE(SUM(amount_cents),0)::bigint FROM ambassador_payouts WHERE status='pending')::bigint AS pending
    """))
    if uid:
        result["detail"] = await overview(uid)
        result["clients"] = [
            public(r)
            for r in await pool.fetch(
                """SELECT c.telegram_id,c.created_at,u.first_name,u.first_online_at,
            (SELECT COUNT(*) FROM ambassador_awards a WHERE a.client_id=c.telegram_id AND a.status='earned')::int AS payments
            FROM ambassador_clients c LEFT JOIN users u ON u.telegram_id=c.telegram_id
            WHERE c.ambassador_id=$1 ORDER BY c.created_at DESC LIMIT 25 OFFSET $2""",
                uid,
                offset,
            )
        ]
        result["clients_total"] = await pool.fetchval(
            "SELECT COUNT(*) FROM ambassador_clients WHERE ambassador_id=$1", uid
        )
    return result


async def admin_action(data):
    action = data.get("action")
    note = str(data.get("note") or "").strip()[:1000]
    async with db._pool_req().acquire() as conn:
        async with conn.transaction():
            await lock(conn)
            if action == "settings":
                previous = await settings(conn)
                cfg = dict(previous)
                for key in ("recruitment", "accruing"):
                    if key in data:
                        if not isinstance(data[key], bool):
                            raise ValueError("Некорректный переключатель")
                        cfg[key] = data[key]
                for key, lo, hi in [
                    ("first_percent", 0, 100),
                    ("first_cap", 1, 100000),
                    ("recurring_percent", 0, 100),
                    ("hold_days", 1, 90),
                    ("payout_min", 100, 1000000),
                    ("budget", 0, 100000000),
                    ("member_cap", 0, 10000000),
                    ("max_members", 1, 100000),
                ]:
                    value = data.get(key, cfg[key])
                    if (
                        isinstance(value, bool)
                        or not isinstance(value, int)
                        or not lo <= value <= hi
                    ):
                        raise ValueError("Некорректное значение: " + key)
                    cfg[key] = value
                if cfg["accruing"] and not cfg["budget"]:
                    raise ValueError("Перед запуском задайте бюджет программы")
                keys = [k for k in cfg if k != "id"]
                await conn.execute(
                    "UPDATE ambassador_settings SET "
                    + ",".join(f"{k}=${i}" for i, k in enumerate(keys, 1))
                    + " WHERE id=1",
                    *[cfg[k] for k in keys],
                )
                await audit(conn, "settings", "program", cfg)
                if previous["accruing"] != cfg["accruing"]:
                    text = (
                        "▶️ Начисления амбассадорам возобновлены. Новые оплаты учитываются по текущим условиям."
                        if cfg["accruing"]
                        else "⏸ Начисления амбассадорам приостановлены. Заработанные средства сохраняются. Оплаты во время паузы не принесут вознаграждения."
                    )
                    await conn.execute(
                        "INSERT INTO ambassador_notifications(telegram_id,body) SELECT telegram_id,$1 FROM ambassadors WHERE status IN('approved','suspended')",
                        text,
                    )
                elif any(
                    previous[k] != cfg[k]
                    for k in (
                        "first_percent",
                        "first_cap",
                        "recurring_percent",
                        "hold_days",
                        "payout_min",
                    )
                ):
                    await conn.execute(
                        "INSERT INTO ambassador_notifications(telegram_id,body) SELECT telegram_id,$1 FROM ambassadors WHERE status IN('approved','suspended')",
                        "📢 Условия программы обновлены. Проверьте раздел «Амбассадор». Уже начисленные суммы и сроки ожидания не изменились.",
                    )
                return
            if action in ("approve", "reject", "suspend", "risk_hold", "risk_release"):
                if action in ("reject", "suspend", "risk_hold") and not note:
                    raise ValueError("Укажите причину решения для участника")
                uid = int(data.get("telegram_id") or 0)
                member = await conn.fetchrow(
                    "SELECT * FROM ambassadors WHERE telegram_id=$1", uid
                )
                if not member:
                    raise ValueError("Заявка не найдена")
                if action == "approve":
                    if member["status"] not in ("pending", "suspended"):
                        raise ValueError("Участник уже рассмотрен")
                    cfg = await settings(conn)
                    if (
                        await conn.fetchval(
                            "SELECT COUNT(*) FROM ambassadors WHERE status='approved'"
                        )
                        >= cfg["max_members"]
                    ):
                        raise ValueError("Достигнут лимит участников")
                    await conn.execute(
                        "UPDATE ambassadors SET status='approved',approved_at=COALESCE(approved_at,NOW()),reviewed_at=NOW(),review_note=$2 WHERE telegram_id=$1",
                        uid,
                        note,
                    )
                    message = "🎉 Вы стали амбассадором! Личная ссылка и условия доступны в кабинете, в разделе «Амбассадор»."
                elif action in ("risk_hold", "risk_release"):
                    await conn.execute(
                        "UPDATE ambassadors SET risk_hold=$2,review_note=$3 WHERE telegram_id=$1",
                        uid,
                        action == "risk_hold",
                        note,
                    )
                    message = (
                        "Вывод вознаграждений временно на проверке. Напишите в поддержку, если есть вопросы."
                        if action == "risk_hold"
                        else "✅ Проверка завершена. Вывод вознаграждений снова доступен."
                    )
                else:
                    if action == "reject" and member["status"] != "pending":
                        raise ValueError("Отклонить можно только новую заявку")
                    if action == "suspend" and member["status"] != "approved":
                        raise ValueError("Участник не активен")
                    await conn.execute(
                        "UPDATE ambassadors SET status=$2,reviewed_at=NOW(),review_note=$3 WHERE telegram_id=$1",
                        uid,
                        "rejected" if action == "reject" else "suspended",
                        note,
                    )
                    message = (
                        "Заявка в амбассадоры отклонена. Подробности — в кабинете."
                        if action == "reject"
                        else "Участие в программе приостановлено. Новые вознаграждения не начисляются, заработанное сохраняется."
                    )
                await audit(conn, action, uid, {"note": note})
                await notify(conn, uid, message)
                return
            if action in ("pay", "reject_payout"):
                payout = await conn.fetchrow(
                    "SELECT * FROM ambassador_payouts WHERE id=$1",
                    int(data.get("id") or 0),
                )
                if not payout or payout["status"] != "pending":
                    raise ValueError("Заявка уже обработана или не найдена")
                if not note:
                    raise ValueError(
                        "Укажите подтверждение перевода или причину отказа"
                    )
                uid = payout["ambassador_id"]
                w = await wallet(uid, conn)
                if action == "pay":
                    if (
                        await conn.fetchval(
                            "SELECT risk_hold FROM ambassadors WHERE telegram_id=$1",
                            uid,
                        )
                        or w["available"] < 0
                    ):
                        raise ValueError(
                            "Выплата заблокирована: проверка или возвращённый платёж"
                        )
                await conn.execute(
                    "UPDATE ambassador_payouts SET status=$2,resolved_at=NOW(),note=$3 WHERE id=$1",
                    payout["id"],
                    "paid" if action == "pay" else "rejected",
                    note,
                )
                await audit(conn, action, payout["id"], {"note": note})
                await notify(
                    conn,
                    uid,
                    (
                        "✅ Вознаграждение выплачено. Подробности — в разделе «Амбассадор»."
                        if action == "pay"
                        else "Заявка на вывод отклонена. Средства освобождены из резерва; доступная сумма и причина — в кабинете."
                    ),
                )
                return
            if action == "revoke":
                key = str(data.get("payment_key") or "")
                award = await conn.fetchrow(
                    "SELECT * FROM ambassador_awards WHERE payment_key=$1", key
                )
                if not award or award["status"] != "earned":
                    raise ValueError("Начисление не найдено или уже отменено")
                if not note:
                    raise ValueError("Укажите причину отмены и подтверждение возврата")
                await conn.execute(
                    "UPDATE ambassador_awards SET status='revoked',reason=$2,revoked_at=NOW() WHERE payment_key=$1",
                    key,
                    note,
                )
                w = await wallet(award["ambassador_id"], conn)
                if w["available"] < 0:
                    await conn.execute(
                        "UPDATE ambassadors SET risk_hold=TRUE WHERE telegram_id=$1",
                        award["ambassador_id"],
                    )
                await audit(conn, "revoke", key, {"note": note})
                await notify(
                    conn,
                    award["ambassador_id"],
                    "Вознаграждение отменено после проверки платежа. Причина и сумма — в разделе «Амбассадор».",
                )
                return
            raise ValueError("Неизвестное действие")


APPROVE_AFTER = "5 minutes"


async def approve_due_applications() -> int:
    """Approve applications submitted exactly five minutes ago. The member is not told the wait is fixed."""
    async with db._pool_req().acquire() as conn:
        async with conn.transaction():
            await lock(conn)
            cfg = await settings(conn)
            active = int(
                await conn.fetchval(
                    "SELECT COUNT(*) FROM ambassadors WHERE status='approved'"
                )
                or 0
            )
            slots = int(cfg["max_members"]) - active
            if slots <= 0:
                return 0
            rows = await conn.fetch(
                f"""SELECT telegram_id FROM ambassadors
                    WHERE status='pending'
                      AND COALESCE(applied_at, created_at) <= NOW() - INTERVAL '{APPROVE_AFTER}'
                    ORDER BY COALESCE(applied_at, created_at), telegram_id
                    LIMIT $1
                    FOR UPDATE""",
                slots,
            )
            for row in rows:
                uid = int(row["telegram_id"])
                await conn.execute(
                    """UPDATE ambassadors
                       SET status='approved', approved_at=COALESCE(approved_at,NOW()), reviewed_at=NOW()
                       WHERE telegram_id=$1 AND status='pending'""",
                    uid,
                )
                await audit(conn, "approve", uid, {})
                await notify(
                    conn,
                    uid,
                    "🎉 Вы стали амбассадором! Личная ссылка и условия доступны в кабинете, в разделе «Амбассадор».",
                )
            return len(rows)


async def seconds_until_application_review():
    value = await db._pool_req().fetchval(
        f"""SELECT EXTRACT(EPOCH FROM (COALESCE(applied_at, created_at) + INTERVAL '{APPROVE_AFTER}' - NOW()))
            FROM ambassadors WHERE status='pending'
            ORDER BY COALESCE(applied_at, created_at), telegram_id
            LIMIT 1"""
    )
    return None if value is None else float(value)


async def application_review_loop(bot) -> None:
    import asyncio
    import logging

    logger = logging.getLogger(__name__)
    while True:
        delay = 30.0
        try:
            approved = await approve_due_applications()
            if approved:
                await deliver_notifications(bot)
            wait = await seconds_until_application_review()
            if wait is None:
                delay = 30.0
            elif wait <= 0:
                delay = 30.0 if not approved else 0.0
            else:
                delay = wait
        except Exception:
            logger.exception("Ambassador applications will be reviewed again")
            delay = 30.0
        await asyncio.sleep(delay)


async def deliver_notifications(bot):
    import logging
    from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
    from app.funnel_ui import send_funnel_message
    from app.keyboards import cabinet_keyboard

    for row in await db._pool_req().fetch(
        "SELECT * FROM ambassador_notifications WHERE status='pending' AND retry_at<=NOW() ORDER BY id LIMIT 50"
    ):
        claimed = await db._pool_req().fetchval(
            "UPDATE ambassador_notifications SET retry_at=NOW()+INTERVAL '5 minutes' WHERE id=$1 AND status='pending' AND retry_at<=NOW() RETURNING id",
            row["id"],
        )
        if not claimed:
            continue
        try:
            await send_funnel_message(
                bot, row["telegram_id"], row["body"], reply_markup=cabinet_keyboard()
            )
            await db._pool_req().execute(
                "UPDATE ambassador_notifications SET status='sent' WHERE id=$1",
                row["id"],
            )
            try:
                await db.log_bot_message(
                    kind="ambassador",
                    source="ambassador",
                    telegram_id=row["telegram_id"],
                    title="Программа амбассадоров",
                    body=row["body"],
                    status="sent",
                    extra={"notice_id": row["id"]},
                )
            except Exception:
                logging.getLogger(__name__).exception(
                    "Could not log ambassador notice %s", row["id"]
                )
        except TelegramForbiddenError:
            await db._pool_req().execute(
                "UPDATE ambassador_notifications SET status='blocked' WHERE id=$1",
                row["id"],
            )
        except TelegramRetryAfter as exc:
            await db._pool_req().execute(
                "UPDATE ambassador_notifications SET retry_at=NOW()+($2::int*INTERVAL '1 second') WHERE id=$1",
                row["id"],
                max(300, exc.retry_after),
            )
        except Exception:
            logging.getLogger(__name__).exception(
                "Ambassador notice will retry %s", row["id"]
            )


async def home_summary(uid):
    """Small cabinet payload; financial terms remain owned by the program settings."""
    cfg = await settings()
    member = await db._pool_req().fetchval('SELECT status FROM ambassadors WHERE telegram_id=$1', uid)
    return {'status': member, 'invitation_available': bool(await recruitment_offer(cfg)), **{key: cfg[key] for key in (
        'recruitment', 'accruing', 'first_percent', 'first_cap', 'recurring_percent', 'payout_min')}}


async def recruitment_offer(cfg=None):
    cfg = cfg if cfg is not None else await settings()
    if not cfg['recruitment'] or not cfg['accruing']:
        return None
    capacity = await db._pool_req().fetchrow('''SELECT
        (SELECT COUNT(*) FROM ambassadors WHERE status='approved') AS members,
        (SELECT COALESCE(SUM(amount_cents),0) FROM ambassador_awards WHERE status<>'skipped') AS spent''')
    if capacity['members'] >= cfg['max_members'] or capacity['spent'] >= cfg['budget'] * 100:
        return None
    if cfg['first_percent'] <= 0 and cfg['recurring_percent'] <= 0:
        return None
    return cfg


def _invitation_filters(price_param):
    return f'''u.has_paid_topup
          AND u.first_online_at <= NOW()-INTERVAL '7 days'
          AND u.balance_rub >= {price_param} * GREATEST(1,(SELECT COUNT(*) FROM devices d
              WHERE d.telegram_id=u.telegram_id AND COALESCE(d.kind,'')<>'router'))
          AND EXISTS(SELECT 1 FROM devices d WHERE d.telegram_id=u.telegram_id AND d.last_online_at>NOW()-INTERVAL '3 days')
          AND u.bot_started_at IS NOT NULL AND u.blocked_at IS NULL AND u.bot_blocked_at IS NULL
          AND NOT u.quiet_notifications AND u.vpn_feedback IS DISTINCT FROM 'help'
          AND NOT EXISTS(SELECT 1 FROM ambassadors a WHERE a.telegram_id=u.telegram_id)
          AND NOT EXISTS(SELECT 1 FROM tickets t WHERE t.telegram_id=u.telegram_id AND t.status<>'closed')'''


async def due_invitations(limit, skip_ids, *, first_only=False):
    price = max(1, get_settings().vpn_day_price_rub) * 3
    stage = "u.ambassador_invite_sent_at IS NULL" if first_only else '''(
            u.ambassador_invite_sent_at IS NULL
            OR (COALESCE(u.ambassador_invite_step,0) < 2
                AND u.ambassador_invite_sent_at <= NOW()-INTERVAL '7 days')
          )'''
    rows = await db._pool_req().fetch(
        f'''SELECT u.telegram_id,u.first_name,
            CASE WHEN u.ambassador_invite_sent_at IS NULL THEN 1 ELSE 2 END AS nudge_step
        FROM users u
        WHERE {_invitation_filters('$3')}
          AND {stage}
          AND NOT (u.telegram_id=ANY($2::bigint[]))
        ORDER BY u.first_online_at LIMIT $1''',
        int(limit), list(skip_ids or []), price)
    return [dict(row) for row in rows]


async def invitation_audience_count():
    if not await recruitment_offer():
        return 0
    price = max(1, get_settings().vpn_day_price_rub) * 3
    value = await db._pool_req().fetchval(
        f'''SELECT COUNT(*)::int FROM users u
            WHERE {_invitation_filters('$1')} AND u.ambassador_invite_sent_at IS NULL''',
        price)
    return int(value or 0)


def _invitation_stage(first_only):
    if first_only:
        return "u.ambassador_invite_sent_at IS NULL"
    return '''(
            u.ambassador_invite_sent_at IS NULL
            OR (COALESCE(u.ambassador_invite_step,0) < 2
                AND u.ambassador_invite_sent_at <= NOW()-INTERVAL '7 days')
          )'''


async def due_earn_invitations(limit, skip_ids, *, first_only=False):
    """People with no payment, or whose balance has already run out."""
    rows = await db._pool_req().fetch(
        f'''SELECT u.telegram_id, u.first_name, 'earn' AS segment,
            CASE WHEN u.ambassador_invite_sent_at IS NULL THEN 1 ELSE 2 END AS nudge_step
        FROM users u
        WHERE u.bot_started_at IS NOT NULL
          AND u.bot_started_at <= NOW()-INTERVAL '2 days'
          AND u.blocked_at IS NULL AND u.bot_blocked_at IS NULL
          AND NOT u.quiet_notifications AND u.vpn_feedback IS DISTINCT FROM 'help'
          AND NOT EXISTS(SELECT 1 FROM ambassadors a WHERE a.telegram_id=u.telegram_id)
          AND NOT EXISTS(SELECT 1 FROM tickets t WHERE t.telegram_id=u.telegram_id AND t.status<>'closed')
          AND (
                NOT COALESCE(u.has_paid_topup, FALSE)
                OR (
                    COALESCE(u.balance_rub, 0) <= 0
                    AND (u.balance_exhausted_at IS NOT NULL OR u.trial_used OR u.gift_claimed_at IS NOT NULL)
                )
          )
          AND {_invitation_stage(first_only)}
          AND NOT (u.telegram_id=ANY($2::bigint[]))
        ORDER BY u.bot_started_at, u.telegram_id
        LIMIT $1''',
        int(limit), list(skip_ids or []))
    return [dict(row) for row in rows]


async def mark_invitation_sent(telegram_id, step):
    await db._pool_req().execute(
        '''UPDATE users SET ambassador_invite_sent_at=NOW(), ambassador_invite_step=$2
           WHERE telegram_id=$1''', int(telegram_id), int(step))


def invitation_text(cfg):
    return (
        '🤝 Рекомендуйте VPN и зарабатывайте\n\n'
        f"В программе амбассадоров — {cfg['first_percent']}% первого пополнения нового клиента, до {cfg['first_cap']} ₽, "
        f"и {cfg['recurring_percent']}% следующих пополнений.\n\n"
        f"Вывод от {cfg['payout_min']} ₽. Начисления доступны через {cfg['hold_days']} дней.\n\n"
        'Есть канал, блог или сообщество? Расскажите о нём в заявке. Участие — после одобрения.'
    )


def invitation_followup_text(cfg):
    return (
        '🤝 Место в программе амбассадоров ещё открыто\n\n'
        f"Вам — {cfg['first_percent']}% первого пополнения клиента, до {cfg['first_cap']} ₽, "
        f"и {cfg['recurring_percent']}% следующих.\n\n"
        'Если есть канал или сообщество, оставьте заявку в кабинете. Это займёт минуту.'
    )


def invitation_earn_text(cfg):
    return (
        '💸 VPN может приносить деньги.\n\n'
        f"Станьте амбассадором: {cfg['first_percent']}% первого пополнения нового клиента, до {cfg['first_cap']} ₽, "
        f"и {cfg['recurring_percent']}% следующих.\n\n"
        f"Вывод от {cfg['payout_min']} ₽. Заявка — в кабинете, в разделе «Амбассадор»."
    )


def invitation_earn_followup_text(cfg):
    return (
        '💸 Напоминаем про заработок на рекомендациях.\n\n'
        f"{cfg['first_percent']}% первого пополнения клиента, до {cfg['first_cap']} ₽, "
        f"и {cfg['recurring_percent']}% следующих.\n\n"
        'Если есть канал или знакомые, оставьте заявку в кабинете.'
    )
