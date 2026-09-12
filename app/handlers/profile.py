from __future__ import annotations

import logging
import uuid

from aiogram import F, Router
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from app import db
from app.billing import expire_human, fulfill_rollypay_order, grant_plan, subscription_issued_text
from app.config import get_settings, referral_is_payout
from app.handlers.start import ack, gate_or_continue, show_profile
from app.keyboards import (
    back_profile_keyboard,
    buy_keyboard,
    connect_keyboard,
    faq_keyboard,
    pay_keyboard,
    pay_method_keyboard,
    share_keyboard,
)
from app.remnawave import (
    RemnawaveClient,
    RemnawaveError,
    is_subscription_active,
)
from app.referrals import (
    after_topup_keyboard,
    invitee_extra_days,
    topup_ok_text,
    trial_grant_days,
    trial_grant_rub,
    trial_is_available,
)
from app.reports import ReportCooldown, submit_vpn_report
from app.rollypay import RollyPayClient, RollyPayError, payment_is_paid, resolve_payment_method
from app.sync import fetch_panel
from app.notices import notice_text
from app.texts import days_text, minutes_text, rub_text

router = Router()
logger = logging.getLogger("rm-shop.profile")


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
    if not trial_is_available(local):
        if local and local.get("trial_used"):
            await show_profile(callback, rw)
            return
        await callback.message.edit_text("Сейчас нельзя попробовать бесплатно.", reply_markup=back_profile_keyboard())
        return
    if settings.balance_enabled:
        amount = trial_grant_rub()
        after = await db.claim_trial_balance(callback.from_user.id, amount)
        if after is None:
            await show_profile(callback, rw)
            return
        await db.log_billing_event(
            callback.from_user.id,
            "trial",
            source="user",
            amount=amount,
            balance_after=after,
            note=f"Триал {settings.trial_days} дн.",
        )
        await callback.message.edit_text(
            "<b>Бесплатный период</b>\n\n"
            f"На баланс начислено <b>{rub_text(amount)}</b> "
            f"({days_text(settings.trial_days)} × {rub_text(settings.vpn_day_price_rub)}).\n\n"
            "Нажмите «Открыть кабинет», добавьте устройство и импортируйте ссылку в Happ или Incy. "
            "Пока устройств нет, баланс не списывается.",
            reply_markup=back_profile_keyboard(cabinet=True),
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
    local = await db.get_user(callback.from_user.id)
    link = f"https://t.me/{settings.bot_username}?start=ref_{callback.from_user.id}"
    story_offer = bool(
        settings.balance_enabled
        and settings.story_reward_enabled
        and settings.story_reward_rub > 0
        and local
        and local.get("first_online_at")
        and not local.get("story_rewarded_at")
        and not local.get("story_pending_at")
    )
    if settings.balance_enabled:
        rub = settings.referral_reward_rub
        friend = int(settings.referral_invitee_reward_rub or 0)
        friend_line = (
            f" Другу после первой оплаты тоже <b>{rub_text(friend)}</b> на баланс."
            if friend > 0
            else " Другу за переход деньги не даём."
        )
        if referral_is_payout():
            body = (
                "<b>Приведи друга</b>\n\n"
                f"Когда друг первый раз оплатит VPN по вашей ссылке, вам начислят "
                f"<b>{rub_text(rub)}</b> на баланс.{friend_line} "
                f"Вывести можно от <b>{rub_text(settings.referral_payout_min)}</b> реферальных.\n\n"
                f"Ваша ссылка:\n<code>{link}</code>"
            )
        else:
            body = (
                "<b>Приведи друга</b>\n\n"
                f"Когда друг первый раз оплатит VPN по вашей ссылке, вам начислят "
                f"<b>{rub_text(rub)}</b> на баланс.{friend_line}\n\n"
                f"Ваша ссылка:\n<code>{link}</code>"
            )
        if story_offer:
            body += (
                f"\n\nМожно также выложить историю в Telegram и получить "
                f"<b>{rub_text(settings.story_reward_rub)}</b> на баланс — кнопка ниже откроет редактор."
            )
        body += (
            "\n\n«Отправить другу» — шаринг Telegram. "
            "«Скопировать текст» — готовое сообщение в личку, без слов про вашу награду."
        )
    else:
        extra = settings.referral_invitee_days
        extra_line = (
            f" Другу при бесплатном периоде <b>+{days_text(extra)}</b>."
            if extra > 0
            else ""
        )
        body = (
            "<b>Приведи друга</b>\n\n"
            f"Отправьте ссылку. Когда друг первый раз оплатит, вам начислят "
            f"<b>{days_text(settings.referral_reward_days)}</b>.{extra_line}\n\n"
            f"Ваша ссылка:\n<code>{link}</code>\n\n"
            "«Отправить другу» — шаринг Telegram. "
            "«Скопировать текст» — готовое сообщение в личку."
        )
    await callback.message.edit_text(
        body,
        reply_markup=share_keyboard(
            settings.bot_username,
            callback.from_user.id,
            story_offer=story_offer,
        ),
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
            "Устройства добавляются в кабинете.",
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


@router.callback_query(F.data == "reissue_sub")
async def reissue_sub(callback: CallbackQuery, rw: RemnawaveClient) -> None:
    if not await gate_or_continue(callback):
        return
    await ack(callback)
    settings = get_settings()
    if settings.balance_enabled:
        await callback.message.edit_text(
            "Ссылку подписки можно обновить в кабинете, на экране устройства.",
            reply_markup=back_profile_keyboard(),
        )
        return
    try:
        user = await _panel_user(rw, callback.from_user.id)
        if not user:
            await callback.message.edit_text(
                "Подписка ещё не создана.",
                reply_markup=buy_keyboard(),
            )
            return
        user = await rw.revoke_subscription(user)
    except RemnawaveError as exc:
        await callback.message.edit_text(str(exc), reply_markup=back_profile_keyboard())
        return
    await db.save_panel_snapshot(callback.from_user.id, user)
    sub_url = user.get("subscriptionUrl") or ""
    await callback.message.edit_text(
        "<b>Ссылка перевыпущена</b>\n\n"
        "Старая больше не действует. Обновите подписку в клиенте.\n\n"
        f"<code>{sub_url}</code>",
        reply_markup=connect_keyboard(sub_url) if sub_url else back_profile_keyboard(),
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
    plan = settings.plan_by_code(code)
    if not plan:
        await ack(callback, "Тариф не найден", alert=True)
        return
    if settings.rollypay_configured:
        await ack(callback)
        await callback.message.edit_text(
            f"<b>{plan['title']}</b> — {plan['rub_str']} рублей\n\n"
            "Как оплатить?",
            reply_markup=pay_method_keyboard(code),
        )
        return
    await _create_plan_invoice(callback, rp, code, "sbp")


@router.callback_query(F.data.startswith("rpm:"))
async def buy_plan_method(callback: CallbackQuery, rp: RollyPayClient | None) -> None:
    if not await gate_or_continue(callback):
        return
    parts = callback.data.split(":")
    if len(parts) < 3:
        await ack(callback, "Тариф не найден", alert=True)
        return
    await _create_plan_invoice(callback, rp, parts[1], parts[2])


async def _create_plan_invoice(
    callback: CallbackQuery,
    rp: RollyPayClient | None,
    code: str,
    method: str,
) -> None:
    settings = get_settings()
    plan = settings.plan_by_code(code)
    if not plan:
        await ack(callback, "Тариф не найден", alert=True)
        return
    if settings.rollypay_configured:
        if rp is None:
            await ack(callback, "Оплата не настроена", alert=True)
            return
        try:
            pay_method = resolve_payment_method(method)
        except ValueError as exc:
            await ack(callback, str(exc), alert=True)
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
                payment_method=pay_method,
            )
        except RollyPayError as exc:
            logger.exception("RollyPay create failed: %s", exc)
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
    plan = settings.plan_by_code(order["plan_code"]) or {"title": "пополнение"}
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
        user = await fulfill_rollypay_order(order_id, rw, bot=callback.bot)
    except RemnawaveError as exc:
        await callback.message.edit_text(
            notice_text("payment_panel_error", error=exc),
            reply_markup=back_profile_keyboard(),
        )
        return
    if user is None and not settings.balance_enabled:
        await callback.message.edit_text(
            notice_text("payment_duplicate"),
            reply_markup=back_profile_keyboard(),
        )
        return
    if settings.balance_enabled:
        local = await db.get_user(callback.from_user.id)
        can_share = bool(local and local.get("first_online_at"))
        await callback.message.edit_text(
            topup_ok_text(
                rub_text(int(plan.get("topup_rub") or 0)) if plan.get("topup_rub") else plan.get("title"),
                can_share=can_share,
            ),
            reply_markup=await after_topup_keyboard(callback.from_user.id),
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
    plan = settings.plan_by_code(code)
    if not plan:
        await message.answer(notice_text("payment_unknown"))
        return
    inserted = await db.save_payment(
        message.from_user.id,
        code,
        payment.total_amount,
        payment.telegram_payment_charge_id,
    )
    if not inserted:
        await message.answer(notice_text("payment_duplicate"))
        return
    try:
        user = await grant_plan(message.from_user.id, code, rw, bot=message.bot)
    except RemnawaveError as exc:
        await message.answer(notice_text("payment_panel_error", error=exc))
        return
    if settings.balance_enabled:
        local = await db.get_user(message.from_user.id)
        can_share = bool(local and local.get("first_online_at"))
        await message.answer(
            topup_ok_text(
                rub_text(int(plan.get("topup_rub") or 0)) if plan.get("topup_rub") else plan.get("title"),
                can_share=can_share,
            ),
            reply_markup=await after_topup_keyboard(message.from_user.id),
        )
        return
    sub_url = (user or {}).get("subscriptionUrl") or ""
    await message.answer(
        subscription_issued_text(user or {}, f"Подписка оформлена: {plan['title']}"),
        reply_markup=connect_keyboard(sub_url) if sub_url else back_profile_keyboard(),
    )


@router.callback_query(F.data == "faq")
async def show_faq(callback: CallbackQuery) -> None:
    if not await gate_or_continue(callback):
        return
    from app.faq import faq_html

    await ack(callback)
    try:
        await callback.message.edit_text(faq_html(), reply_markup=faq_keyboard())
    except Exception:
        await callback.message.answer(faq_html(), reply_markup=faq_keyboard())


@router.callback_query(F.data == "vpn_down")
async def vpn_down(callback: CallbackQuery, rw: RemnawaveClient) -> None:
    if not await gate_or_continue(callback):
        return
    user = callback.from_user
    try:
        await submit_vpn_report(
            callback.bot,
            rw,
            user.id,
            user.username,
            user.first_name,
            client_context={
                "source": "bot",
                "view": "telegram",
                "telegram": {
                    "language": user.language_code,
                    "isPremium": bool(getattr(user, "is_premium", False)),
                    "platform": None,
                },
            },
        )
    except ReportCooldown as exc:
        minutes = max(1, exc.wait_sec // 60)
        await ack(callback, f"Сообщение уже отправлено. Повторно можно через {minutes_text(minutes)}.", alert=True)
        return
    except Exception:
        await ack(callback, "Не удалось отправить. Попробуйте позже.", alert=True)
        return
    await ack(callback, "Принято. Мы уже смотрим.", alert=True)
