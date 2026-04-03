"""Application configuration loaded from environment / .env file."""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_path: str = str(Path.home() / ".homesearch" / "homesearch.db")

    # SMTP for daily reports
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    report_email: str = ""

    # Report schedule
    report_hour: int = 7
    report_minute: int = 0

    # Web server
    host: str = "0.0.0.0"
    port: int = 8000

    # Optional paid API keys
    rapidapi_key: str = ""

    # Global Zapier webhook — fires for all saved searches that don't override it
    zapier_webhook_url: str = ""

    # Background polling for all saved searches
    background_polling_enabled: bool = True
    background_poll_interval_minutes: int = 15

    # Web Push (VAPID)
    vapid_public_key: str = ""
    vapid_private_key_path: str = ""

    # User timezone (e.g. "America/New_York") — used for report scheduling and display
    user_timezone: str = ""

    # Work address for commute estimation
    work_address: str = ""
    work_lat: float | None = None
    work_lng: float | None = None

    # Shared household session — all devices connecting to this server use the same session
    # so dismissals, saved searches, and stars sync automatically across phone/desktop/tablet.
    household_session: str = ""

    model_config = {
        # Read from both the home dir config and any local .env (local wins)
        "env_file": [str(Path.home() / ".homesearch" / ".env"), ".env"],
        "env_file_encoding": "utf-8",
    }


settings = Settings()
