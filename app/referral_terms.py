"""Public referral terms shared by the bot, FAQ and cabinet."""
from app.config import get_settings

# The friend gets it on reaching the bot's main menu; the inviter once the friend first connects VPN.
REFERRAL_BONUS_RUB = 50
REFERRAL_REWARD_LABEL = "другу 50 ₽ сразу, вам 50 ₽, когда друг подключит VPN"


def referral_terms(settings=None) -> dict[str, str]:
    settings = settings or get_settings()
    bonus = f"{REFERRAL_BONUS_RUB} ₽"
    if not settings.referral_program_enabled:
        return {
            "note": "Реферальная программа приостановлена. Новые награды не начисляются, уже полученный баланс сохраняется.",
            "when": "Во время паузы начислений нет. Друзьям, пришедшим за время паузы, бонус позже не начисляется.",
            "how": f"Условия при включении: другу {bonus} сразу, вам {bonus}, когда друг подключит VPN.",
            "friend": "",
        }
    return {
        "note": "Награды начисляются, пока программа активна.",
        "when": f"🎁 Другу {bonus} сразу, вам {bonus}, когда друг подключит VPN. Друг должен прийти по вашей ссылке.",
        "how": f"Другу {bonus} на баланс сразу, как он откроет бота, вам {bonus} — когда он впервые подключит VPN. Один раз за каждого нового друга.",
        "friend": "",
    }
