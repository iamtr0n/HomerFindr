"""Settings menu — email, search defaults, and about page."""

import questionary
from questionary import Choice
from rich.panel import Panel

from homesearch.tui.config import load_config, save_config
from homesearch.tui.smtp_wizard import run_smtp_wizard_with_test
from homesearch.tui.styles import HOUSE_STYLE, console


def show_settings_menu() -> None:
    """Top-level settings menu with Email, Search Defaults, and About sub-pages."""
    while True:
        choice = questionary.select(
            "Settings:",
            choices=["\u2190 Back", "Email Settings", "Search Defaults", "About HomerFindr"],
            style=HOUSE_STYLE,
        ).ask()
        if choice is None or choice == "\u2190 Back":
            return
        if choice == "Email Settings":
            _show_email_settings()
        elif choice == "Search Defaults":
            _show_search_defaults()
        elif choice == "About HomerFindr":
            _show_about()


def _show_email_settings() -> None:
    """Email settings sub-page: view SMTP config and manage recipients."""
    while True:
        config = load_config()
        smtp = config["smtp"]
        if smtp.get("email"):
            summary = (
                f"Provider: {smtp.get('provider', 'Custom')}  |  "
                f"Email: {smtp['email']}  |  "
                f"Recipients: {len(smtp.get('recipients', []))}"
            )
        else:
            summary = "SMTP not configured"
        console.print(Panel(summary, title="[bold cyan]Email Settings[/bold cyan]", border_style="cyan"))

        choice = questionary.select(
            "Email Settings:",
            choices=["\u2190 Back", "Configure SMTP", "Manage Recipients"],
            style=HOUSE_STYLE,
        ).ask()
        if choice is None or choice == "\u2190 Back":
            return
        if choice == "Configure SMTP":
            result = run_smtp_wizard_with_test(existing=config["smtp"])
            if result is not None:
                config["smtp"] = result
                save_config(config)
                console.print("[bold green]SMTP settings saved.[/bold green]")
        elif choice == "Manage Recipients":
            _manage_recipients(config)


def _manage_recipients(config: dict) -> None:
    """Add or remove email recipients."""
    while True:
        recipients = config["smtp"].get("recipients", [])
        choices = ["\u2190 Back", "Add new recipient"] + [f"Remove: {r}" for r in recipients]
        choice = questionary.select(
            "Recipients:",
            choices=choices,
            style=HOUSE_STYLE,
        ).ask()
        if choice is None or choice == "\u2190 Back":
            return
        if choice == "Add new recipient":
            new = questionary.text("Email address:", style=HOUSE_STYLE).ask()
            if new and new.strip() and "@" in new:
                config["smtp"].setdefault("recipients", []).append(new.strip())
                save_config(config)
                console.print(f"[green]Added {new.strip()}.[/green]")
        elif choice.startswith("Remove: "):
            email_to_remove = choice[len("Remove: "):]
            if email_to_remove in config["smtp"]["recipients"]:
                config["smtp"]["recipients"].remove(email_to_remove)
                save_config(config)
                console.print(f"[green]Removed {email_to_remove}.[/green]")


def _show_search_defaults() -> None:
    """Search defaults sub-page: set default city, state, radius, listing type, price range."""
    while True:
        config = load_config()
        d = config["defaults"]
        price_min = d.get("price_min")
        price_max = d.get("price_max")
        price_str = (
            f"${price_min:,}" if price_min else "no min"
        ) + " – " + (
            f"${price_max:,}" if price_max else "no max"
        )
        summary = (
            f"City: {d.get('city') or '(none)'}  |  State: {d.get('state') or '(none)'}  |  "
            f"Radius: {d.get('radius', 25)} mi  |  Type: {d.get('listing_type', 'sale')}  |  "
            f"Price: {price_str}"
        )
        console.print(Panel(summary, title="[bold cyan]Search Defaults[/bold cyan]", border_style="cyan"))

        choice = questionary.select(
            "Search Defaults:",
            choices=["\u2190 Back", "City", "State", "Radius", "Listing Type", "Price Range"],
            style=HOUSE_STYLE,
        ).ask()
        if choice is None or choice == "\u2190 Back":
            return
        if choice == "City":
            val = questionary.text(
                "Default city:", default=d.get("city", ""), style=HOUSE_STYLE
            ).ask()
            if val is not None:
                config["defaults"]["city"] = val
                save_config(config)
        elif choice == "State":
            val = questionary.text(
                "Default state:", default=d.get("state", ""), style=HOUSE_STYLE
            ).ask()
            if val is not None:
                config["defaults"]["state"] = val
                save_config(config)
        elif choice == "Radius":
            val = questionary.select(
                "Default radius:",
                choices=[
                    Choice(title="5 miles", value=5),
                    Choice(title="10 miles", value=10),
                    Choice(title="25 miles", value=25),
                    Choice(title="50 miles", value=50),
                ],
                default=d.get("radius", 25),
                style=HOUSE_STYLE,
            ).ask()
            if val is not None:
                config["defaults"]["radius"] = val
                save_config(config)
        elif choice == "Listing Type":
            val = questionary.select(
                "Default listing type:",
                choices=["sale", "rent", "sold"],
                default=d.get("listing_type", "sale"),
                style=HOUSE_STYLE,
            ).ask()
            if val is not None:
                config["defaults"]["listing_type"] = val
                save_config(config)
        elif choice == "Price Range":
            min_str = questionary.text(
                "Min price (leave blank for no limit):",
                default=str(d["price_min"]) if d.get("price_min") is not None else "",
                style=HOUSE_STYLE,
            ).ask()
            max_str = questionary.text(
                "Max price (leave blank for no limit):",
                default=str(d["price_max"]) if d.get("price_max") is not None else "",
                style=HOUSE_STYLE,
            ).ask()
            if min_str is not None and max_str is not None:
                try:
                    config["defaults"]["price_min"] = int(min_str.strip()) if min_str.strip() else None
                except ValueError:
                    config["defaults"]["price_min"] = None
                try:
                    config["defaults"]["price_max"] = int(max_str.strip()) if max_str.strip() else None
                except ValueError:
                    config["defaults"]["price_max"] = None
                save_config(config)


def _show_about() -> None:
    """About page — ASCII house and version info."""
    console.print("[bold cyan]  /\\[/bold cyan]")
    console.print("[bold cyan] /  \\[/bold cyan]")
    console.print("[bold cyan]/____\\[/bold cyan]")
    console.print("[bold cyan]| [] |[/bold cyan]")
    console.print()
    console.print("[bold cyan]HomerFindr[/bold cyan] v1.0")
    console.print("[dim]Find homes fast across all platforms.[/dim]")
    console.print("[dim]github.com/iamtron/HomerFindr[/dim]")
