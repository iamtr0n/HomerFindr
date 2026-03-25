"""First-run setup wizard — triggers when no config file exists."""

import questionary
from questionary import Choice
from rich.panel import Panel

from homesearch.tui.config import load_config, save_config
from homesearch.tui.smtp_wizard import run_smtp_wizard_with_test
from homesearch.tui.styles import HOUSE_STYLE, console


def run_first_run_wizard() -> None:
    """Run the first-time setup wizard to collect location defaults and optional SMTP."""
    try:
        console.print(Panel(
            "[bold cyan]Welcome to HomerFindr! Let's get you set up. \U0001f3e0[/bold cyan]",
            border_style="cyan",
            title="First-Time Setup",
        ))
        console.print("[dim]You can change these later from Settings.[/dim]\n")

        # Step 1 — Default city
        city = questionary.text("Default city:", style=HOUSE_STYLE).ask()
        if city is None:
            return

        # Step 2 — Default state
        state = questionary.text("Default state (e.g. TX, CA):", style=HOUSE_STYLE).ask()
        if state is None:
            return

        # Step 3 — Default radius
        radius_choice = questionary.select(
            "Default search radius:",
            choices=[
                Choice(title="5 miles", value=5),
                Choice(title="10 miles", value=10),
                Choice(title="25 miles", value=25),
                Choice(title="50 miles", value=50),
            ],
            default=25,
            style=HOUSE_STYLE,
        ).ask()
        if radius_choice is None:
            return

        # Step 4 — SMTP setup
        smtp_choice = questionary.select(
            "Email reports (SMTP):",
            choices=["Set up now", "Skip for later"],
            style=HOUSE_STYLE,
        ).ask()
        if smtp_choice is None:
            return

        smtp_result = None
        if smtp_choice == "Set up now":
            smtp_result = run_smtp_wizard_with_test()

        # Build and save config once at the end
        config = load_config()
        config["defaults"]["city"] = city.strip()
        config["defaults"]["state"] = state.strip().upper()
        config["defaults"]["radius"] = radius_choice
        if smtp_result is not None:
            config["smtp"] = smtp_result
        save_config(config)

        console.print(Panel(
            "[bold green]Setup complete! Your preferences have been saved. \u2705[/bold green]",
            border_style="green",
        ))

    except KeyboardInterrupt:
        console.print("\n[dim]Setup skipped. You can configure later from Settings.[/dim]")
        return
