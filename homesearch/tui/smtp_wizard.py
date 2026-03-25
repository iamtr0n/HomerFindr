"""SMTP setup wizard with provider presets and test-send for HomerFindr."""

import smtplib
from email.mime.text import MIMEText

import questionary
from rich.panel import Panel

from homesearch.tui.config import load_config
from homesearch.tui.styles import HOUSE_STYLE, console

PROVIDER_PRESETS = {
    "Gmail":           {"server": "smtp.gmail.com",        "port": 587},
    "Outlook/Hotmail": {"server": "smtp-mail.outlook.com", "port": 587},
    "Yahoo":           {"server": "smtp.mail.yahoo.com",   "port": 587},
    "Custom":          {"server": "",                       "port": 587},
}


def run_smtp_wizard(existing: dict | None = None) -> dict | None:
    """Collect SMTP credentials via guided wizard. Returns dict or None on Ctrl+C."""
    if existing is None:
        existing = load_config().get("smtp", {})

    provider = questionary.select(
        "Email provider:",
        choices=["Gmail", "Outlook/Hotmail", "Yahoo", "Custom"],
        style=HOUSE_STYLE,
    ).ask()
    if provider is None:
        return None

    if provider == "Gmail":
        console.print("[dim]Gmail tip: Use an App Password from myaccount.google.com/apppasswords[/dim]")

    preset = PROVIDER_PRESETS[provider]

    server = questionary.text(
        "SMTP server:",
        default=preset["server"],
        style=HOUSE_STYLE,
    ).ask()
    if server is None:
        return None

    port_str = questionary.text(
        "Port:",
        default=str(preset["port"]),
        style=HOUSE_STYLE,
    ).ask()
    if port_str is None:
        return None
    try:
        port = int(port_str)
    except ValueError:
        port = 587

    email = questionary.text(
        "Your email address:",
        default=existing.get("email", ""),
        style=HOUSE_STYLE,
    ).ask()
    if email is None:
        return None

    password = questionary.password(
        "App password (input masked):",
        style=HOUSE_STYLE,
    ).ask()
    if password is None:
        return None

    return {
        "provider": provider,
        "server": server,
        "port": port,
        "email": email,
        "password": password,
        "recipients": existing.get("recipients", []),
    }


def test_smtp(smtp_cfg: dict) -> bool:
    """Send a test email to verify SMTP credentials. Returns True on success."""
    try:
        msg = MIMEText("This is a test email from HomerFindr to verify your SMTP configuration.")
        msg["Subject"] = "HomerFindr: SMTP Test"
        msg["From"] = smtp_cfg["email"]
        msg["To"] = smtp_cfg["email"]

        with smtplib.SMTP(smtp_cfg["server"], smtp_cfg["port"], timeout=10) as server:
            server.starttls()
            server.login(smtp_cfg["email"], smtp_cfg["password"])
            server.send_message(msg)

        console.print(Panel("[bold green]Test email sent successfully![/bold green]", border_style="green"))
        return True
    except Exception as e:
        console.print(f"[red]Test failed: {e}[/red]")
        return False


def run_smtp_wizard_with_test(existing: dict | None = None) -> dict | None:
    """Run SMTP wizard, test credentials, offer retry or save-anyway on failure."""
    result = run_smtp_wizard(existing)
    if result is None:
        return None

    if test_smtp(result):
        return result

    # Test failed — offer retry or save anyway
    choice = questionary.select(
        "What would you like to do?",
        choices=["Retry settings", "Save anyway (skip test)"],
        style=HOUSE_STYLE,
    ).ask()
    if choice is None or choice == "Save anyway (skip test)":
        return result
    # "Retry settings"
    return run_smtp_wizard_with_test(existing)
