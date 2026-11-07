"""Public referral terms shared by the bot, FAQ and cabinet."""
from app.config import get_settings

# Paid to both the inviter and the friend once the friend reaches the bot's main menu.
REFERRAL_BONUS_RUB = 50
REFERRAL_REWARD_LABEL = "50 ₽ вам и другу"


def referral_terms(settings=None) -> dict[str, str]:
    settings = settings or get_settings()
    bonus = f"{REFERRAL_BONUS_RUB} ₽"
    if not settings.referral_program_enabled:
        return {
            "note": "Реферальная программа приостановлена. Новые награды не начисляются, уже полученный баланс сохраняется.",
            "when": "Во время паузы начислений нет. Друзьям, пришедшим за время паузы, бонус позже не начисляется.",
            "how": f"Условия при включении: по {bonus} вам и новому другу, когда он откроет меню бота.",
            "friend": "",
        }
    return {
        "note": "Награды начисляются, пока программа активна.",
        "when": f"🎁 По {bonus} вам и другу, как только он откроет меню бота. Друг должен прийти по вашей ссылке.",
        "how": f"{bonus} вам и {bonus} другу один раз за каждого нового друга — сразу, как он дойдёт до главного меню.",
        "friend": f"Другу по вашей ссылке — {bonus} на баланс сразу при входе в меню.",
    }
