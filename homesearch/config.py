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
    host: str = "127.0.0.1"
    port: int = 8000

    # Optional paid API keys
    rapidapi_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
