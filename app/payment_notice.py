"""Durable payment confirmations, independent of panel/referral side effects."""
import logging
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from app import db
from app.funnel_ui import send_funnel_message
from app.keyboards import onboarding_keyboard, cabinet_keyboard
from app.notices import notice_text
from app.texts import rub_text

logger = logging.getLogger(__name__)


def used_vpn(local: dict, devices: list[dict]) -> bool:
    """Any sign the VPN already worked: first online, a device seen online, or traffic on the panel.
    first_online_at alone misses people who connected before it was tracked."""
    return bool(local.get('first_online_at') or int(local.get('lifetime_traffic_bytes') or 0) > 0
                or any(d.get('last_online_at') for d in devices))


async def deliver_payment_notice(bot, receipt):
    if bot is None:
        return
    key, uid = receipt['payment_key'], int(receipt['telegram_id'])
    if not await db.claim_payment_notice(key):
        return
    body = ''
    status = 'pending'
    try:
        local = await db.get_user(uid) or {}
        if receipt['router_days']:
            body = 'Оплата получена. Откройте кабинет, чтобы проверить доступ.'
            markup = cabinet_keyboard()
        else:
            devices = await db.list_devices(uid)
            body = notice_text('topup_ok',amount=rub_text(receipt['amount']))
            body += '\nБаланс: ' + rub_text(int(local.get('balance_rub') or 0)) + '.'
            if used_vpn(local, devices):
                body += '\n\nVPN уже настроен, больше ничего делать не нужно. Если не подключается — напишите в поддержку.'
                markup = cabinet_keyboard()
            elif not devices:
                body += '\n\n📱 Добавьте устройство — покажем, как подключить VPN.'
                markup = onboarding_keyboard()
            else:
                body += '\n\n📱 Продолжите настройку: добавьте ссылку в VPN-приложение и включите VPN.'
                markup = onboarding_keyboard(has_device=True)
        from app.funnel_ui import funnel_body
        body = funnel_body(body)
        await send_funnel_message(bot,uid,body,reply_markup=markup)
        status = 'sent'
        await db.finish_payment_notice(key,status)
    except TelegramForbiddenError:
        status = 'blocked'
        await db.finish_payment_notice(key,status)
    except TelegramRetryAfter as exc:
        await db.finish_payment_notice(key,'pending',max(300,int(exc.retry_after)))
    except Exception:
        logger.exception('Payment confirmation will retry: %s',key)
    try:
        await db.log_bot_message(kind='payment_confirmation',source='pay',telegram_id=uid,
            title='Подтверждение оплаты',body=body,status='sent' if status=='sent' else 'failed',extra={'payment_key':key,'delivery_status':status})
    except Exception:
        logger.exception('Could not log payment confirmation %s',key)
