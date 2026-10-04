"""Personal five-day recovery offers, with durable retries and shared contact limits."""
import logging
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from app import db
from app.config import get_settings
from app.keyboards import mini_app_url
from app.notices import notice_text
from app.texts import rub_text

logger = logging.getLogger(__name__)


def keyboard():
    url = mini_app_url()
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Личный кабинет',web_app=WebAppInfo(url=url),style='success')]
        if url else [InlineKeyboardButton(text='Личный кабинет',callback_data='help:connect',style='success')],
        [InlineKeyboardButton(text='Главное меню',callback_data='profile')],
    ])


def message(code: str, count: int, amount: int) -> str:
    body = notice_text('winback_promo', code=code, devices=str(count), amount=rub_text(amount))
    # Required redemption terms remain visible even with a short custom template.
    body += (f'\n\n<code>{code}</code>\n\n'
             f'Начислим {rub_text(amount)} — на 5 дней для ваших устройств: {count}. '
             'Минус погасим отдельно.\n\n'
             'Введите код в разделе «Промокод» в кабинете. '
             'Он действует 7 дней, только для вас и один раз. '
             'Если добавите устройства, подарка хватит на меньший срок.')
    return body


async def send_due(bot, skip_ids=None):
    from app.nudge import _deliver_unbudgeted
    if not await db.flag_on('winback_promo') or await db.flag_on('maintenance') or await db.flag_on('billing_paused'):
        return 0, []
    await db.backfill_balance_exhaustion()
    sent, touched = 0, []
    for row in await db.list_due_winback_offers(skip_ids or []):
        uid = int(row['telegram_id'])
        if not await db.flag_on('winback_promo'):
            break
        if not await db.nudge_delivery_allowed(uid, 'nudge_winback'):
            continue
        slot = await db.reserve_optional_message(uid, 'nudge_winback')
        if slot is None:
            continue
        delivered = False
        offer = None
        try:
            offer = await db.prepare_winback_offer(uid, max(1,get_settings().vpn_day_price_rub))
            if offer is None:
                continue
            touched.append(uid)
            delivered = await _deliver_unbudgeted(bot,kind='nudge_winback',telegram_id=uid,
                first_name=row.get('first_name'),title='Промокод: 5 дней для возвращения',
                body=message(offer['code'],offer['device_count'],offer['gift_rub']),reply_markup=keyboard(),
                extra={'offer_id':offer['id'],'promo_id':offer['promo_id']})
            if delivered:
                # Keep reservation even if accounting of delivery fails after Telegram accepts.
                await db.finish_optional_message(slot, True)
                await db.finish_winback_offer(offer['id'], True)
                sent += 1
            else:
                await db.finish_winback_offer(offer['id'], False)
        except Exception:
            logger.exception('Recovery offer delivery failed for %s',uid)
        finally:
            await db.finish_optional_message(slot, delivered)
    return sent, touched
