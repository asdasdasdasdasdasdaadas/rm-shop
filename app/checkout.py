"""Resolve the latest invoice again when a reminder button is pressed."""
from datetime import datetime, timedelta, timezone

from app import db
from app.rollypay import payment_is_paid


async def resume_checkout(telegram_id: int, token: str, rp) -> tuple[str, str | None]:
    user = await db.get_user(telegram_id)
    if not user or user.get('checkout_token') != token:
        return 'stale', None
    started = user.get('checkout_started_at')
    if not started:
        return 'closed', None
    payment_id = user.get('checkout_payment_id')
    if payment_id:
        if rp is None:
            return 'unavailable', None
        try:
            payment = await rp.get_payment(payment_id)
        except Exception:
            return 'unavailable', None
        status = str(payment.get('status') or '').lower()
        if payment_is_paid(payment) or status == 'refunded':
            await db.cancel_payment_nudge(telegram_id, token)
            return 'closed', None
        if status == 'processing':
            return 'processing', None
        if status in {'expired', 'canceled', 'cancelled', 'failed'}:
            return 'expired', None
        if status not in {'created', 'pending', 'waiting'}:
            return 'unavailable', None
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - started >= timedelta(minutes=20):
        return 'expired', None
    # Recheck after the provider request: payment/new checkout may have raced it.
    latest = await db.get_user(telegram_id)
    if not latest or latest.get('checkout_token') != token or not latest.get('checkout_started_at'):
        return 'stale', None
    url = latest.get('checkout_url')
    if not url and payment_id:
        order = await db.get_rollypay_order_by_payment(payment_id)
        url = order.get('pay_url') if order else None
    return ('active', url) if url else ('expired', None)
