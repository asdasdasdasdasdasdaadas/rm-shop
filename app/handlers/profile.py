from __future__ import annotations
from app.funnel_ui import answer_funnel, edit_funnel


import logging

from aiogram import F, Router
from aiogram.types import LinkPreviewOptions, CallbackQuery, Message, PreCheckoutQuery, InlineKeyboardButton, InlineKeyboardMarkup

from app import db
from app.checkout import resume_checkout
from app.billing import grant_plan
from app.config import get_settings
from app.handlers.start import ack, gate_or_continue, show_profile
from app.keyboards import (
    back_profile_keyboard,
    buy_keyboard,
    payment_nudge_keyboard,
    share_keyboard,
    invite_message,
    about_service_content,
)
from app.remnawave import (
    RemnawaveClient,
    RemnawaveError,
)
from app.referrals import (
    trial_is_available,
)
from app.cispay import CISPayClient, payment_is_paid
from app.notices import notice_text
from app.texts import rub_text

router = Router()
logger = logging.getLogger("rm-shop.profile")


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
        await edit_funnel(callback.message, "Подарок сейчас недоступен. Если нужна помощь — напишите в поддержку.", reply_markup=back_profile_keyboard())
        return
    await edit_funnel(callback.message,
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
    from app.live import user_action
    await user_action(dict(telegram_id=callback.from_user.id, first_name=callback.from_user.first_name,
                     username=callback.from_user.username), 'invite')
    body = invite_message(callback.from_user.id, settings)
    markup = share_keyboard(settings.bot_username, callback.from_user.id)
    # A live referral card in place of the menu message; on any error keep the plain invite text.
    from app.widgets import send_referral_widget
    try:
        await send_referral_widget(callback.bot, callback.from_user.id, caption=body, reply_markup=markup)
    except Exception:
        logger.warning("Виджет рефералки не отправился, показываем текст", exc_info=True)
    else:
        try:
            await callback.message.delete()
        except Exception:
            logger.debug("Меню под карточкой рефералки не удалено", exc_info=True)
        return
    await edit_funnel(callback.message,
        body,
        preserve=True,
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(is_disabled=True),
        reply_markup=share_keyboard(
            settings.bot_username,
            callback.from_user.id,
        ),
    )


@router.callback_query(F.data == "buy")
async def buy_menu(callback: CallbackQuery, rw: RemnawaveClient) -> None:
    if not await gate_or_continue(callback):
        return
    await ack(callback)
    settings = get_settings()
    text = (
        "<b>Пополнение баланса</b>\n\n"
        f"Сутки на одно устройство: {rub_text(settings.vpn_day_price_rub)}. "
        "Пока устройств нет, баланс не списывается."
    )
    await edit_funnel(callback.message, text, reply_markup=buy_keyboard(callback.from_user.id))


@router.callback_query(F.data.startswith("resume_pay:"))
async def resume_payment(callback: CallbackQuery, rp: CISPayClient | None) -> None:
    if not await gate_or_continue(callback):
        return
    await ack(callback)
    state, url = await resume_checkout(callback.from_user.id, callback.data.split(":", 1)[1], rp)
    if state == "active":
        await answer_funnel(callback.message, "Ваш счёт ещё действует. Продолжите оплату:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="Оплатить счёт", url=url)
            ]]))
    elif state in {"unavailable", "processing"}:
        await answer_funnel(callback.message, "Платёж проверяется. Если деньги уже списались, не платите повторно. Попробуйте проверить позже или напишите в поддержку.")
    elif state == "closed":
        await answer_funnel(callback.message, "Этот счёт уже закрыт. Если вы оплатили, дождитесь зачисления — повторная оплата не нужна.")
    else:
        await answer_funnel(callback.message, "Этот счёт истёк или заменён новым. Откройте кабинет, чтобы создать новый счёт. Если деньги уже списались, дождитесь зачисления.",
            reply_markup=payment_nudge_keyboard(label="Создать новый счёт"))


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
        await answer_funnel(message, notice_text("payment_unknown"))
        return
    try:
        await grant_plan(message.from_user.id, code, rw, bot=message.bot,
            payment_key=f"stars:{payment.telegram_payment_charge_id}", stars=payment.total_amount)
    except RemnawaveError as exc:
        await answer_funnel(message, notice_text("payment_panel_error", error=exc))
        return


# Buttons of removed screens (old balance view, tariffs in the chat, FAQ, «VPN не работает») still sit
# in old chats: a tap opens the main menu instead of hanging.
STALE_BUTTONS = {"my_sub", "connect", "reissue_sub", "faq", "vpn_down", "help:feedback"}
STALE_PREFIXES = ("buy:", "rpm:", "rpc:")


@router.callback_query(F.data.in_(STALE_BUTTONS) | F.data.startswith(STALE_PREFIXES))
async def stale_button(callback: CallbackQuery, rw: RemnawaveClient) -> None:
    if not await gate_or_continue(callback):
        return
    await ack(callback)
    await show_profile(callback, rw)


@router.callback_query(F.data == "about_service")
async def show_about_service(callback: CallbackQuery) -> None:
    if not await gate_or_continue(callback):
        return
    await ack(callback)
    from app.live import user_action
    await user_action(dict(telegram_id=callback.from_user.id, first_name=callback.from_user.first_name,
                     username=callback.from_user.username), 'about')
    body, markup = about_service_content()
    await edit_funnel(callback.message, body,
        reply_markup=markup,
        preserve=True,
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@router.callback_query(F.data.startswith('paywhy:') | F.data.startswith('payreason:'))
async def checkout_reason(callback: CallbackQuery, rp: CISPayClient | None) -> None:
    from app import checkout_feedback
    from app.keyboards import help_connect_reply_keyboard
    parts = callback.data.split(':')
    token = parts[-1]
    row = await checkout_feedback.current(callback.from_user.id, token)
    if not row:
        await callback.answer('Этот счёт уже закрыт или заменён новым.', show_alert=True)
        return
    if row.get('checkout_payment_id'):
        try:
            payment = await rp.get_payment(row['checkout_payment_id']) if rp else None
        except Exception:
            payment = None
        if not payment:
            await callback.answer('Проверяем платёж. Попробуйте позже.', show_alert=True)
            return
        if payment_is_paid(payment) or str(payment.get('status') or '').lower() == 'refunded':
            await callback.answer('Спасибо! Этот платёж уже обработан.', show_alert=True)
            return
        if str(payment.get('status') or '').lower() not in {'created','pending','processing','waiting','expired','canceled','cancelled','failed'}:
            await callback.answer('Статус платежа уточняется. Попробуйте позже.', show_alert=True)
            return
    if parts[0] == 'paywhy':
        await callback.answer()
        from app.funnel_ui import funnel_keyboard
        keyboard = checkout_feedback.answers(token)
        navigation = funnel_keyboard().inline_keyboard
        keyboard = keyboard.model_copy(update={'inline_keyboard': navigation + keyboard.inline_keyboard})
        await answer_funnel(callback.message, 'Что остановило оплату? Ответьте одной кнопкой — это поможет нам стать лучше.', reply_markup=keyboard, preserve=True)
        return
    reason = parts[1] if len(parts) == 3 else ''
    if not await checkout_feedback.save(callback.from_user.id, token, reason):
        await callback.answer('Ответ уже учтён или счёт больше не актуален.')
        return
    await callback.answer('Спасибо, ответ записан')
    messages = {
        'broken': 'Передали обращение в поддержку. Предложения пока приостановили. Напишите, что не заработало, и на каком устройстве. Можно приложить скриншот.',
        'price': 'Спасибо, учтём ваш ответ. Сделаем паузу в предложениях на неделю. Актуальная стоимость — в кабинете.',
        'payment': 'Напишите, какой способ оплаты был бы удобнее. На сутки приостановили предложения. Если деньги уже списались, не платите повторно — поможем проверить платёж.',
        'later': 'Поняли. Сделаем паузу в предложениях на неделю. Если вернётесь раньше, поможем продолжить.',
    }
    await answer_funnel(callback.message, messages[reason], reply_markup=help_connect_reply_keyboard() if reason in {'broken','payment'} else None)
