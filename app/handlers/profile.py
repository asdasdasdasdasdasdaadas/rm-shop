from __future__ import annotations
from app.funnel_ui import answer_funnel, edit_funnel

from app.referral_terms import referral_terms

import logging
import uuid

from aiogram import F, Router
from aiogram.types import LinkPreviewOptions, CallbackQuery, LabeledPrice, Message, PreCheckoutQuery, InlineKeyboardButton, InlineKeyboardMarkup

from app import db
from app.checkout import resume_checkout
from app.billing import fulfill_rollypay_order, grant_plan
from app.config import get_settings, referral_is_payout
from app.handlers.start import ack, gate_or_continue, show_profile
from app.keyboards import (
    back_profile_keyboard,
    buy_keyboard,
    faq_keyboard,
    pay_keyboard,
    payment_nudge_keyboard,
    share_keyboard,
    with_referral_share,
)
from app.remnawave import (
    RemnawaveClient,
    RemnawaveError,
)
from app.referrals import (
    after_topup_keyboard,
    topup_ok_text,
    trial_is_available,
)
from app.reports import ReportCooldown, submit_vpn_report
from app.rollypay import RollyPayClient, RollyPayError, payment_is_paid, resolve_payment_method
from app.notices import notice_text
from app.texts import minutes_text, rub_text

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
    terms = referral_terms(settings)
    link = f"https://t.me/{settings.bot_username}?start=ref_{callback.from_user.id}"
    body = "<b>Пригласить друга</b>\n\n" + "\n\n".join(
        text for text in (terms["note"], terms["when"], terms["friend"]) if text
    )
    if referral_is_payout():
        body += f"\n\nВывести уже начисленные реферальные средства можно от {rub_text(settings.referral_payout_min)}."
    body += f"\n\nВаша ссылка:\n<code>{link}</code>"
    await edit_funnel(callback.message,
        body,
        reply_markup=share_keyboard(
            settings.bot_username,
            callback.from_user.id,
        ),
    )


@router.callback_query(F.data == "my_sub")
async def my_sub(callback: CallbackQuery, rw: RemnawaveClient) -> None:
    if not await gate_or_continue(callback):
        return
    await ack(callback)
    settings = get_settings()
    local = await db.get_user(callback.from_user.id)
    rub = int((local or {}).get("balance_rub") or 0)
    n = await db.device_count(callback.from_user.id)
    await edit_funnel(callback.message,
        "<b>Баланс</b>\n\n"
        f"Сейчас: <b>{rub_text(rub)}</b>\n"
        f"Устройств: <b>{n}</b>\n"
        f"Списание: <b>{rub_text(settings.vpn_day_price_rub)}</b> в сутки за устройство, "
        "только пока есть хотя бы одно устройство.\n"
        "Устройства добавляются в кабинете.",
        reply_markup=buy_keyboard(),
    )


@router.callback_query(F.data == "connect")
async def connect(callback: CallbackQuery, rw: RemnawaveClient) -> None:
    if not await gate_or_continue(callback):
        return
    await ack(callback)
    await edit_funnel(callback.message,
        "Подключение — в кабинете: добавьте устройство и откройте его ссылку.",
        reply_markup=back_profile_keyboard(cabinet=True),
    )


@router.callback_query(F.data == "reissue_sub")
async def reissue_sub(callback: CallbackQuery, rw: RemnawaveClient) -> None:
    if not await gate_or_continue(callback):
        return
    await ack(callback)
    await edit_funnel(callback.message,
        "Ссылку подписки можно обновить в кабинете, на экране устройства.",
        reply_markup=back_profile_keyboard(),
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
    await edit_funnel(callback.message, text, reply_markup=buy_keyboard())


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
            await ack(callback, "Оплата временно недоступна. Попробуйте позже", alert=True)
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
            await edit_funnel(callback.message,
                "Не удалось создать платёж.",
                reply_markup=back_profile_keyboard(),
            )
            return
        pay_url = str(data.get("pay_url") or "")
        payment_id = str(data.get("payment_id") or "")
        if not pay_url or not payment_id:
            await edit_funnel(callback.message,
                "Не удалось получить ссылку на оплату.",
                reply_markup=back_profile_keyboard(),
            )
            return
        await db.save_rollypay_order(
            order_id, callback.from_user.id, code, payment_id, pay_url
        )
        await edit_funnel(callback.message,
            f"<b>{plan['title']}</b> — {plan['rub_str']} рублей\n\n"
            "Нажмите «Оплатить», затем вернитесь и нажмите «Проверить оплату».",
            reply_markup=pay_keyboard(pay_url, order_id),
        )
        return
    if settings.stars_enabled:
        await ack(callback)
        link = await callback.bot.create_invoice_link(
            title=f"Пополнение: {plan['title']}",
            description=f"Пополнение на {plan.get('title') or plan['rub_str']}.",
            payload=f"plan:{code}",
            currency="XTR",
            prices=[LabeledPrice(label=plan["title"], amount=plan["stars"])],
        )
        await db.track_checkout(callback.from_user.id, pay_url=link)
        await answer_funnel(callback.message, "Счёт готов. Нажмите, чтобы оплатить:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Оплатить", url=link)]]))
        return
    await ack(callback, "Оплата временно недоступна. Попробуйте позже", alert=True)


@router.callback_query(F.data.startswith("resume_pay:"))
async def resume_payment(callback: CallbackQuery, rp: RollyPayClient | None) -> None:
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
        await ack(callback, "Оплата временно недоступна. Попробуйте позже", alert=True)
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
        await ack(callback, f"Подтверждение оплаты пока не пришло. Если деньги списались, повторно платить не нужно.", alert=True)
        return
    if order["status"] == "granted":
        await ack(callback, "Этот платёж уже обработан", alert=True)
        return
    await ack(callback)
    try:
        user = await fulfill_rollypay_order(order_id, rw, bot=callback.bot)
    except RemnawaveError as exc:
        await edit_funnel(callback.message,
            notice_text("payment_panel_error", error=exc),
            reply_markup=back_profile_keyboard(),
        )
        return


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
        user = await grant_plan(message.from_user.id, code, rw, bot=message.bot,
            payment_key=f"stars:{payment.telegram_payment_charge_id}", stars=payment.total_amount)
    except RemnawaveError as exc:
        await answer_funnel(message, notice_text("payment_panel_error", error=exc))
        return


@router.callback_query(F.data == "about_service")
async def show_about_service(callback: CallbackQuery) -> None:
    if not await gate_or_continue(callback):
        return
    await ack(callback)
    settings = get_settings()
    await edit_funnel(callback.message,
        notice_text("about_service", brand=settings.brand_name,
                    price=rub_text(settings.vpn_day_price_rub)),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="В главное меню", callback_data="profile")
        ]]),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@router.callback_query(F.data == "faq")
async def show_faq(callback: CallbackQuery) -> None:
    if not await gate_or_continue(callback):
        return
    from app.faq import faq_pages

    await ack(callback)
    pages = faq_pages()
    try:
        await edit_funnel(callback.message, pages[0], reply_markup=faq_keyboard())
    except Exception:
        await answer_funnel(callback.message, pages[0], reply_markup=faq_keyboard())
    for page in pages[1:]:
        await answer_funnel(callback.message, page, reply_markup=faq_keyboard())



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
    await ack(callback, "✅ Сообщение отправлено в поддержку.", alert=True)
