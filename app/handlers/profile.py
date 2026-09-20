from __future__ import annotations

import logging
import uuid

from aiogram import F, Router
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery, InlineKeyboardButton, InlineKeyboardMarkup

from app import db
from app.checkout import resume_checkout
from app.billing import expire_human, fulfill_rollypay_order, grant_plan, subscription_issued_text
from app.config import get_settings, referral_is_payout
from app.handlers.start import ack, gate_or_continue, show_profile
from app.keyboards import (
    back_profile_keyboard,
    buy_keyboard,
    connect_keyboard,
    faq_keyboard,
    pay_keyboard,
    payment_nudge_keyboard,
    share_keyboard,
    with_referral_share,
)
from app.remnawave import (
    RemnawaveClient,
    RemnawaveError,
    is_subscription_active,
)
from app.referrals import (
    after_topup_keyboard,
    topup_ok_text,
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
    local = await db.get_user(callback.from_user.id)
    if not trial_is_available(local):
        if local and local.get("trial_used"):
            await show_profile(callback, rw)
            return
        await callback.message.edit_text("Сейчас нельзя попробовать бесплатно.", reply_markup=back_profile_keyboard())
        return
    await callback.message.edit_text(
        "🎁 <b>Вам подарок</b>\n\n"
        "Откройте личный кабинет и нажмите «Принять подарок». "
        "После этого сразу перейдёте к добавлению устройства.",
        reply_markup=back_profile_keyboard(cabinet=True),
    )


@router.callback_query(F.data == "share")
async def share(callback: CallbackQuery) -> None:
    if not await gate_or_continue(callback):
        return
    await ack(callback)
    settings = get_settings()
    if not settings.referral_program_enabled:
        await callback.message.edit_text(
            "Реферальная программа приостановлена. Новые награды не начисляются. "
            "Уже начисленный баланс сохраняется.",
            reply_markup=with_referral_share(callback.from_user.id, back_profile_keyboard()))
        return
    local = await db.get_user(callback.from_user.id)
    link = f"https://t.me/{settings.bot_username}?start=ref_{callback.from_user.id}"
    if settings.balance_enabled:
        rub = 50
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
                f"<b>{rub_text(rub)}</b> на баланс плюс 5% с каждого его пополнения, включая первое.{friend_line} "
                f"Вывести можно от <b>{rub_text(settings.referral_payout_min)}</b> реферальных.\n\n"
                f"Ваша ссылка:\n<code>{link}</code>"
            )
        else:
            body = (
                "<b>Приведи друга</b>\n\n"
                f"Когда друг первый раз оплатит VPN по вашей ссылке, вам начислят "
                f"<b>{rub_text(rub)}</b> на баланс плюс 5% с каждого его пополнения, включая первое.{friend_line}\n\n"
                f"Ваша ссылка:\n<code>{link}</code>"
            )

        body += (
            "\n\n«Поделиться реферальной ссылкой» — отправить приглашение через Telegram. "
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
            "«Поделиться реферальной ссылкой» — отправить приглашение через Telegram. "
            "«Скопировать текст» — готовое сообщение в личку."
        )
    await callback.message.edit_text(
        body,
        reply_markup=share_keyboard(
            settings.bot_username,
            callback.from_user.id,
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
        link = await callback.bot.create_invoice_link(
            title=f"Подписка {plan['title']}",
            description=f"Доступ на {days_text(plan['days'])}, трафик безлимитный.",
            payload=f"plan:{code}",
            currency="XTR",
            prices=[LabeledPrice(label=plan["title"], amount=plan["stars"])],
        )
        await db.track_checkout(callback.from_user.id, pay_url=link)
        await callback.message.answer("Счёт готов. Нажмите, чтобы оплатить:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Оплатить", url=link)]]))
        return
    await ack(callback, "Оплата не настроена", alert=True)


@router.callback_query(F.data.startswith("resume_pay:"))
async def resume_payment(callback: CallbackQuery, rp: RollyPayClient | None) -> None:
    if not await gate_or_continue(callback):
        return
    await ack(callback)
    state, url = await resume_checkout(callback.from_user.id, callback.data.split(":", 1)[1], rp)
    if state == "active":
        await callback.message.answer("Ваш счёт ещё действует. Продолжите оплату:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="Оплатить счёт", url=url)
            ]]))
    elif state in {"unavailable", "processing"}:
        await callback.message.answer("Платёж проверяется. Если деньги уже списались, не платите повторно. Попробуйте проверить позже или напишите в поддержку.")
    elif state == "closed":
        await callback.message.answer("Этот счёт уже закрыт. Если вы оплатили, дождитесь зачисления — повторная оплата не нужна.")
    else:
        await callback.message.answer("Этот счёт истёк или заменён новым. Откройте кабинет, чтобы создать новый счёт. Если деньги уже списались, дождитесь зачисления.",
            reply_markup=payment_nudge_keyboard(label="Создать новый счёт"))


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
    from app.pay_methods import public_pay_methods

    if not any(method["id"] == "stars" for method in public_pay_methods()):
        await query.answer(ok=False, error_message="Оплата звёздами отключена. Выберите другой способ в кабинете.")
        return
    from app.pay_methods import stars_price

    payload = query.invoice_payload or ""
    plan = get_settings().plan_by_code(payload[5:]) if payload.startswith("plan:") else None
    try:
        valid = plan is not None and query.currency == "XTR" and query.total_amount == stars_price(plan)
    except ValueError:
        valid = False
    if not valid:
        await query.answer(ok=False, error_message="Счёт устарел. Создайте новый платёж в кабинете.")
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
        user = await grant_plan(message.from_user.id, code, rw, bot=message.bot,
            payment_key=f"stars:{payment.telegram_payment_charge_id}")
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
        await callback.message.edit_text(faq_html(), reply_markup=with_referral_share(callback.from_user.id, faq_keyboard()))
    except Exception:
        await callback.message.answer(faq_html(), reply_markup=with_referral_share(callback.from_user.id, faq_keyboard()))


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
