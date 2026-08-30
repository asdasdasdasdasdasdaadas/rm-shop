from __future__ import annotations

import uuid

from aiogram import F, Router
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from app import db
from app.billing import expire_human, fulfill_rollypay_order, grant_plan, subscription_issued_text
from app.config import get_settings
from app.handlers.start import ack, gate_or_continue, show_profile
from app.keyboards import (
    back_profile_keyboard,
    buy_keyboard,
    connect_keyboard,
    pay_keyboard,
    share_keyboard,
)
from app.remnawave import (
    RemnawaveClient,
    RemnawaveError,
    is_subscription_active,
)
from app.referrals import maybe_reward_referrer, invitee_extra_days, trial_grant_days, trial_grant_rub
from app.reports import ReportCooldown, submit_vpn_report
from app.rollypay import RollyPayClient, RollyPayError, payment_is_paid
from app.sync import fetch_panel
from app.texts import days_text, minutes_text, rub_text

router = Router()


def _status_human(user: dict | None) -> str:
    if not user:
        return "не создана"
    if is_subscription_active(user):
        return "активна"
    return str(user.get("status") or "неактивна")


@router.callback_query(F.data == "trial")
async def activate_trial(callback: CallbackQuery, rw: RemnawaveClient) -> None:
    if not await gate_or_continue(callback):
        return
    await ack(callback)
    settings = get_settings()
    local = await db.get_user(callback.from_user.id)
    if not settings.trial_enabled:
        await callback.message.edit_text("Сейчас нельзя попробовать бесплатно.", reply_markup=back_profile_keyboard())
        return
    if local and local["trial_used"]:
        await show_profile(callback, rw)
        return
    if settings.balance_enabled:
        amount = trial_grant_rub()
        await db.add_balance_rub(callback.from_user.id, amount)
        await db.mark_trial_used(callback.from_user.id)
        await maybe_reward_referrer(
            callback.bot, rw, callback.from_user.id, callback.from_user.first_name
        )
        await callback.message.edit_text(
            "<b>Бесплатный период</b>\n\n"
            f"На баланс начислено <b>{rub_text(amount)}</b> "
            f"({days_text(settings.trial_days)} × {rub_text(settings.vpn_day_price_rub)}).\n"
            "Добавьте устройство в кабинете.",
            reply_markup=back_profile_keyboard(),
        )
        return
    try:
        panel_id = int(local["remnawave_id"]) if local and local.get("remnawave_id") else None
        user = await rw.extend_subscription(
            callback.from_user.id,
            trial_grant_days(local),
            tag="TRIAL",
            panel_user_id=panel_id,
        )
    except RemnawaveError as exc:
        await callback.message.edit_text(f"Не удалось включить бесплатный период: {exc}", reply_markup=back_profile_keyboard())
        return
    rw_id = user.get("id")
    panel_pk = int(rw_id) if rw_id is not None and str(rw_id).isdigit() else None
    await db.mark_trial_used(callback.from_user.id, panel_pk)
    await db.save_panel_snapshot(callback.from_user.id, user)
    await maybe_reward_referrer(
        callback.bot, rw, callback.from_user.id, callback.from_user.first_name
    )
    sub_url = user.get("subscriptionUrl") or ""
    text = subscription_issued_text(user, "Подписка оформлена")
    extra = invitee_extra_days(local)
    if extra:
        text += f"\n\nБонус за переход по ссылке: <b>+{days_text(extra)}</b>"
    await callback.message.edit_text(
        text,
        reply_markup=connect_keyboard(sub_url) if sub_url else back_profile_keyboard(),
    )


@router.callback_query(F.data == "share")
async def share(callback: CallbackQuery) -> None:
    if not await gate_or_continue(callback):
        return
    await ack(callback)
    settings = get_settings()
    link = f"https://t.me/{settings.bot_username}?start=ref_{callback.from_user.id}"
    if settings.balance_enabled:
        rub = settings.referral_reward_rub
        body = (
            "<b>Приведи друга</b>\n\n"
            f"Когда друг нажмёт «Попробовать бесплатно», вам и другу начислят "
            f"по <b>{rub_text(rub)}</b> на баланс.\n\n"
            f"Ваша ссылка:\n<code>{link}</code>"
        )
    else:
        body = (
            "<b>Приведи друга</b>\n\n"
            f"Отправьте ссылку. Когда друг нажмёт «Попробовать бесплатно», вам начислят "
            f"<b>{days_text(settings.referral_reward_days)}</b>, а другу "
            f"<b>+{days_text(settings.referral_invitee_days)}</b> к бесплатному периоду.\n\n"
            f"Ваша ссылка:\n<code>{link}</code>"
        )
    await callback.message.edit_text(
        body,
        reply_markup=share_keyboard(settings.bot_username, callback.from_user.id),
    )


async def _panel_user(rw: RemnawaveClient, telegram_id: int) -> dict | None:
    return await fetch_panel(rw, telegram_id)


@router.callback_query(F.data == "my_sub")
async def my_sub(callback: CallbackQuery, rw: RemnawaveClient) -> None:
    if not await gate_or_continue(callback):
        return
    await ack(callback)
    settings = get_settings()
    if settings.balance_enabled:
        local = await db.get_user(callback.from_user.id)
        rub = int((local or {}).get("balance_rub") or 0)
        n = await db.device_count(callback.from_user.id)
        await callback.message.edit_text(
            "<b>Баланс</b>\n\n"
            f"Сейчас: <b>{rub_text(rub)}</b>\n"
            f"Устройств: <b>{n}</b>\n"
            f"Списание: <b>{rub_text(settings.vpn_day_price_rub)}</b> в сутки за устройство, "
            "только пока есть хотя бы одно устройство.\n"
            "Устройства добавляются в личном кабинете.",
            reply_markup=buy_keyboard(),
        )
        return
    try:
        user = await _panel_user(rw, callback.from_user.id)
    except RemnawaveError as exc:
        await callback.message.edit_text(str(exc), reply_markup=back_profile_keyboard())
        return
    sub_url = (user or {}).get("subscriptionUrl") or ""
    extra = f"\n\nСсылка подписки:\n<code>{sub_url}</code>" if sub_url and is_subscription_active(user) else ""
    await callback.message.edit_text(
        "<b>Моя подписка</b>\n\n"
        f"Статус: <b>{_status_human(user)}</b>\n"
        f"Действует до: <b>{expire_human(user)}</b>"
        f"{extra}",
        reply_markup=connect_keyboard(sub_url) if sub_url else buy_keyboard(),
    )


@router.callback_query(F.data == "connect")
async def connect(callback: CallbackQuery, rw: RemnawaveClient) -> None:
    if not await gate_or_continue(callback):
        return
    await ack(callback)
    try:
        user = await _panel_user(rw, callback.from_user.id)
    except RemnawaveError as exc:
        await callback.message.edit_text(str(exc), reply_markup=back_profile_keyboard())
        return
    sub_url = (user or {}).get("subscriptionUrl")
    if not user or not sub_url:
        await callback.message.edit_text(
            "Подписка ещё не создана. Нажмите «Попробовать бесплатно» или купите подписку.",
            reply_markup=buy_keyboard(),
        )
        return
    if not is_subscription_active(user):
        await callback.message.edit_text(
            "Подписка неактивна. Оформите тариф ниже.",
            reply_markup=buy_keyboard(),
        )
        return
    await callback.message.edit_text(
        "<b>Подключение</b>\n\n"
        "1. Установите клиент (Happ / v2RayTun / Streisand).\n"
        "2. Импортируйте ссылку подписки.\n\n"
        f"<code>{sub_url}</code>",
        reply_markup=connect_keyboard(sub_url),
    )


@router.callback_query(F.data == "buy")
async def buy_menu(callback: CallbackQuery, rw: RemnawaveClient) -> None:
    if not await gate_or_continue(callback):
        return
    await ack(callback)
    try:
        user = await _panel_user(rw, callback.from_user.id)
    except RemnawaveError:
        user = None
    settings = get_settings()
    if settings.balance_enabled:
        text = (
            "<b>Пополнение баланса</b>\n\n"
            f"Сутки на одно устройство: {rub_text(settings.vpn_day_price_rub)}. "
            "Пока устройств нет, баланс не списывается."
        )
    else:
        text = (
            "<b>Покупка подписки</b>\n\n"
            f"Сейчас: <b>{_status_human(user)}</b>\n"
            f"До: <b>{expire_human(user)}</b>\n\n"
            "Если подписка ещё действует, оплаченный срок добавится к текущей дате."
        )
    await callback.message.edit_text(text, reply_markup=buy_keyboard())


@router.callback_query(F.data.startswith("buy:"))
async def buy_plan(callback: CallbackQuery, rp: RollyPayClient | None) -> None:
    if not await gate_or_continue(callback):
        return
    code = callback.data.split(":", 1)[1]
    settings = get_settings()
    plan = settings.shop_plans.get(code)
    if not plan:
        await ack(callback, "Тариф не найден", alert=True)
        return
    if settings.rollypay_configured:
        if rp is None:
            await ack(callback, "Оплата не настроена", alert=True)
            return
        await ack(callback)
        order_id = uuid.uuid4().hex
        try:
            data = await rp.create_payment(
                amount_rub=plan["rub_str"],
                order_id=order_id,
                description=f"{settings.brand_name}: {plan['title']}",
                customer_id=str(callback.from_user.id),
                metadata={"telegram_id": str(callback.from_user.id), "plan": code},
            )
        except RollyPayError as exc:
            await callback.message.edit_text(
                "Не удалось создать платёж.",
                reply_markup=back_profile_keyboard(),
            )
            return
        pay_url = str(data.get("pay_url") or "")
        payment_id = str(data.get("payment_id") or "")
        if not pay_url or not payment_id:
            await callback.message.edit_text(
                "Не удалось получить ссылку на оплату.",
                reply_markup=back_profile_keyboard(),
            )
            return
        await db.save_rollypay_order(
            order_id, callback.from_user.id, code, payment_id, pay_url
        )
        await callback.message.edit_text(
            f"<b>{plan['title']}</b> — {plan['rub_str']} рублей\n\n"
            "Нажмите «Оплатить», затем вернитесь и нажмите «Проверить оплату».",
            reply_markup=pay_keyboard(pay_url, order_id),
        )
        return
    if settings.stars_enabled:
        await ack(callback)
        await callback.message.answer_invoice(
            title=f"Подписка {plan['title']}",
            description=f"Доступ на {days_text(plan['days'])}, трафик безлимитный.",
            payload=f"plan:{code}",
            currency="XTR",
            prices=[LabeledPrice(label=plan["title"], amount=plan["stars"])],
        )
        return
    await ack(callback, "Оплата не настроена", alert=True)


@router.callback_query(F.data.startswith("rpc:"))
async def check_rollypay(callback: CallbackQuery, rw: RemnawaveClient, rp: RollyPayClient | None) -> None:
    if not await gate_or_continue(callback):
        return
    order_id = callback.data.split(":", 1)[1]
    order = await db.get_rollypay_order(order_id)
    if not order or int(order["telegram_id"]) != callback.from_user.id:
        await ack(callback, "Заказ не найден", alert=True)
        return
    if rp is None:
        await ack(callback, "Оплата не настроена", alert=True)
        return
    settings = get_settings()
    plan = settings.shop_plans.get(order["plan_code"]) or {"title": "пополнение"}
    try:
        payment = await rp.get_payment(order["payment_id"])
    except RollyPayError:
        await ack(callback, "Не удалось проверить оплату.", alert=True)
        return
    status = str(payment.get("status") or "")
    if not payment_is_paid(payment):
        await ack(callback, f"Статус оплаты: {status or 'неизвестно'}", alert=True)
        return
    if order["status"] == "granted":
        await ack(callback, "Этот платёж уже обработан", alert=True)
        return
    await ack(callback)
    try:
        user = await fulfill_rollypay_order(order_id, rw)
    except RemnawaveError as exc:
        await callback.message.edit_text(
            f"Оплата прошла, но панель не ответила: {exc}\nНапишите в поддержку.",
            reply_markup=back_profile_keyboard(),
        )
        return
    if user is None and not settings.balance_enabled:
        await callback.message.edit_text(
            "Этот платёж уже обработан.",
            reply_markup=back_profile_keyboard(),
        )
        return
    if settings.balance_enabled:
        await callback.message.edit_text(
            f"Баланс пополнен на {rub_text(int(plan.get('topup_rub') or 0)) if plan.get('topup_rub') else plan.get('title')}.",
            reply_markup=back_profile_keyboard(),
        )
        return
    sub_url = (user or {}).get("subscriptionUrl") or ""
    await callback.message.edit_text(
        subscription_issued_text(user or {}, f"Подписка оформлена: {plan.get('title')}"),
        reply_markup=connect_keyboard(sub_url) if sub_url else back_profile_keyboard(),
    )


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    if await db.flag_on("maintenance"):
        await query.answer(ok=False, error_message="Сервис временно недоступен")
        return
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message, rw: RemnawaveClient) -> None:
    payment = message.successful_payment
    payload = payment.invoice_payload or ""
    if not payload.startswith("plan:"):
        return
    code = payload.split(":", 1)[1]
    settings = get_settings()
    plan = settings.shop_plans.get(code)
    if not plan:
        await message.answer("Платёж получен, но тариф неизвестен. Напишите в поддержку.")
        return
    inserted = await db.save_payment(
        message.from_user.id,
        code,
        payment.total_amount,
        payment.telegram_payment_charge_id,
    )
    if not inserted:
        await message.answer("Этот платёж уже обработан.")
        return
    try:
        user = await grant_plan(message.from_user.id, code, rw)
    except RemnawaveError as exc:
        await message.answer(
            f"Оплата прошла, но панель не ответила: {exc}\n"
            "Напишите в поддержку."
        )
        return
    if settings.balance_enabled:
        await message.answer(
            f"Баланс пополнен на {rub_text(int(plan.get('topup_rub') or 0)) if plan.get('topup_rub') else plan.get('title')}."
        )
        return
    sub_url = (user or {}).get("subscriptionUrl") or ""
    await message.answer(
        subscription_issued_text(user or {}, f"Подписка оформлена: {plan['title']}"),
        reply_markup=connect_keyboard(sub_url) if sub_url else back_profile_keyboard(),
    )


@router.callback_query(F.data == "vpn_down")
async def vpn_down(callback: CallbackQuery, rw: RemnawaveClient) -> None:
    if not await gate_or_continue(callback):
        return
    user = callback.from_user
    try:
        await submit_vpn_report(callback.bot, rw, user.id, user.username, user.first_name)
    except ReportCooldown as exc:
        minutes = max(1, exc.wait_sec // 60)
        await ack(callback, f"Сообщение уже отправлено. Повторно можно через {minutes_text(minutes)}.", alert=True)
        return
    except Exception:
        await ack(callback, "Не удалось отправить. Попробуйте позже.", alert=True)
        return
    await ack(callback, "Принято. Мы уже смотрим.", alert=True)
