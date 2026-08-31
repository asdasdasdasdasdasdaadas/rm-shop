from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str
    bot_username: str = "your_bot"
    required_channel_id: str
    required_channel_url: str
    admin_ids: str = ""

    remnawave_base_url: str
    remnawave_token: str
    remnawave_squad_uuids: str = ""
    remnawave_hwid_limit: Optional[int] = 1
    remnawave_traffic_limit_gb: int = 0
    remnawave_traffic_strategy: str = "NO_RESET"

    trial_enabled: bool = True
    trial_days: int = 3
    referral_reward_days: int = 7
    referral_invitee_days: int = 5

    legal_offer_url: str
    legal_privacy_url: str

    plan_1m_stars: int = 150
    plan_3m_stars: int = 400
    plan_6m_stars: int = 700
    plan_12m_stars: int = 1200
    plan_1m_rub: float = 199.0
    plan_3m_rub: float = 499.0
    plan_6m_rub: float = 899.0
    plan_12m_rub: float = 1499.0
    stars_enabled: bool = False

    rollypay_api_url: str = "https://rollypay.io"
    rollypay_api_key: str = ""
    rollypay_signing_secret: str = ""
    rollypay_test: bool = True
    rollypay_payment_method: str = ""

    balance_enabled: bool = False
    vpn_day_price_rub: int = 6
    max_devices: int = 5
    balance_topup_min: int = 50
    balance_topup_max: int = 400
    balance_topup_step: int = 50
    referral_reward_rub: int = 50
    balance_charge_interval: int = 600
    promo_enabled: bool = True
    promo_codes: str = "TEST:3"
    webapp_enabled: bool = False
    webapp_host: str = "0.0.0.0"
    webapp_port: int = 8080
    webapp_public_url: str = ""

    brand_name: str = "RM Shop"
    support_username: str = "@way_proxy_support"
    admin_password: str = ""
    database_url: str = "postgresql://rmshop:rmshop@127.0.0.1:5432/rmshop"
    panel_sync_ttl: int = 60
    panel_sync_interval: int = 600
    vpn_report_cooldown_sec: int = 900
    backup_keep_days: int = 14

    @property
    def admin_id_set(self) -> set[int]:
        return {int(x.strip()) for x in self.admin_ids.split(",") if x.strip().isdigit()}

    @property
    def squad_uuids(self) -> list[str]:
        return [x.strip() for x in self.remnawave_squad_uuids.split(",") if x.strip()]

    @property
    def rollypay_configured(self) -> bool:
        return bool(self.rollypay_api_key.strip())

    @property
    def plans(self) -> dict[str, dict]:
        return {
            "1m": {
                "title": "1 месяц",
                "days": 30,
                "stars": self.plan_1m_stars,
                "rub": self.plan_1m_rub,
                "rub_str": f"{self.plan_1m_rub:.2f}",
            },
            "3m": {
                "title": "3 месяца",
                "days": 90,
                "stars": self.plan_3m_stars,
                "rub": self.plan_3m_rub,
                "rub_str": f"{self.plan_3m_rub:.2f}",
            },
            "6m": {
                "title": "6 месяцев",
                "days": 180,
                "stars": self.plan_6m_stars,
                "rub": self.plan_6m_rub,
                "rub_str": f"{self.plan_6m_rub:.2f}",
            },
            "12m": {
                "title": "12 месяцев",
                "days": 365,
                "stars": self.plan_12m_stars,
                "rub": self.plan_12m_rub,
                "rub_str": f"{self.plan_12m_rub:.2f}",
            },
        }

    @property
    def shop_plans(self) -> dict[str, dict]:
        if not self.balance_enabled:
            return self.plans
        result: dict[str, dict] = {}
        amount = self.balance_topup_min
        step = max(1, self.balance_topup_step)
        while amount <= self.balance_topup_max:
            result[f"b{amount}"] = {
                "title": f"{amount} рублей",
                "days": 0,
                "stars": 0,
                "rub": float(amount),
                "rub_str": f"{amount:.2f}",
                "topup_rub": amount,
            }
            amount += step
        return result

    @property
    def promo_map(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for chunk in self.promo_codes.split(","):
            part = chunk.strip()
            if not part or ":" not in part:
                continue
            code, days = part.split(":", 1)
            if code.strip() and days.strip().isdigit():
                result[code.strip().upper()] = int(days.strip())
        return result


SHOP_KEYS = frozenset(
    {
        "brand_name",
        "support_username",
        "legal_offer_url",
        "legal_privacy_url",
        "vpn_day_price_rub",
        "max_devices",
        "remnawave_hwid_limit",
        "trial_enabled",
        "trial_days",
        "referral_reward_rub",
        "referral_reward_days",
        "referral_invitee_days",
        "balance_topup_min",
        "balance_topup_max",
        "balance_topup_step",
        "promo_enabled",
        "promo_codes",
        "plan_1m_rub",
        "plan_3m_rub",
        "plan_6m_rub",
        "plan_12m_rub",
        "vpn_report_cooldown_sec",
        "vpn_apps",
    }
)

_overlay: dict = {}


def set_shop_overlay(data: dict) -> None:
    global _overlay
    _overlay = {k: v for k, v in data.items() if k in SHOP_KEYS}


def shop_overlay() -> dict:
    return dict(_overlay)


@lru_cache
def _env_settings() -> Settings:
    return Settings()


def get_settings() -> Settings:
    base = _env_settings()
    if not _overlay:
        return base
    update = dict(_overlay)
    update.pop("vpn_apps", None)
    if "remnawave_hwid_limit" in update:
        raw = update["remnawave_hwid_limit"]
        update["remnawave_hwid_limit"] = None if raw in (0, None, "") else int(raw)
    if hasattr(base, "model_copy"):
        return base.model_copy(update=update)
    return base.copy(update=update)
