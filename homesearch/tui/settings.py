"""Comprehensive settings menu — all configuration in one place."""

import os

import questionary
from questionary import Choice
from rich.panel import Panel
from rich.table import Table

from homesearch.tui.config import load_config, save_config
from homesearch.tui.smtp_wizard import run_smtp_wizard_with_test
from homesearch.tui.styles import HOUSE_STYLE, console


# ---------------------------------------------------------------------------
# Top-level menu
# ---------------------------------------------------------------------------

def show_settings_menu() -> None:
    """Top-level settings menu."""
    while True:
        config = load_config()
        _render_settings_overview(config)

        choice = questionary.select(
            "Settings:",
            choices=[
                "\u2190 Back",
                "\U0001f514  Notifications & Alerts",
                "\U0001f4e7  Email & Reports",
                "\U0001f50d  Search Defaults",
                "\U0001f3e0  Providers",
                "\U0001f5c4   Data & Database",
                "\U0001f5a5   Display & UI",
                "\u23f1   Scheduler",
                "\u2139   About HomerFindr",
            ],
            style=HOUSE_STYLE,
        ).ask()
        if choice is None or choice == "\u2190 Back":
            return
        if "Notifications" in choice:
            _show_notifications(config)
        elif "Email" in choice:
            _show_email_settings(config)
        elif "Search Defaults" in choice:
            _show_search_defaults(config)
        elif "Providers" in choice:
            _show_providers(config)
        elif "Data" in choice:
            _show_data(config)
        elif "Display" in choice:
            _show_display(config)
        elif "Scheduler" in choice:
            _show_scheduler(config)
        elif "About" in choice:
            _show_about()


def _render_settings_overview(config: dict) -> None:
    """Show a compact status panel summarising every section."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Section", style="dim", min_width=22)
    table.add_column("Status", style="white")

    n = config.get("notifications", {})
    webhook = n.get("zapier_webhook", "")
    table.add_row(
        "\U0001f514 Notifications",
        f"Webhook: [green]{webhook[:40]}[/green]" if webhook else "[dim]No webhook set[/dim]",
    )

    smtp = config.get("smtp", {})
    table.add_row(
        "\U0001f4e7 Email",
        f"[green]{smtp.get('email', '')}[/green]  ({len(smtp.get('recipients', []))} recipients)"
        if smtp.get("email") else "[dim]Not configured[/dim]",
    )

    d = config.get("defaults", {})
    loc = f"{d.get('city', '')} {d.get('state', '')}".strip()
    table.add_row(
        "\U0001f50d Search Defaults",
        f"{loc or '[dim]No location[/dim]'}  ·  {d.get('radius', 25)} mi  ·  {d.get('listing_type', 'sale')}",
    )

    p = config.get("providers", {})
    active = []
    if p.get("homeharvest_enabled", True):
        active.append("Realtor")
    if p.get("redfin_enabled", True):
        active.append("Redfin")
    table.add_row("\U0001f3e0 Providers", ", ".join(active) if active else "[red]All disabled[/red]")

    sched = config.get("report", {})
    table.add_row(
        "\u23f1  Scheduler",
        f"Daily report {sched.get('hour', 7):02d}:{sched.get('minute', 0):02d}  ·  "
        f"Webhook every {n.get('webhook_interval_minutes', 3)} min",
    )

    disp = config.get("display", {})
    table.add_row(
        "\U0001f5a5  Display",
        f"{disp.get('results_per_page', 50)} per page  ·  sort: {disp.get('default_sort', 'match_score')}",
    )

    console.print(Panel(table, title="[bold cyan]HomerFindr Settings[/bold cyan]", border_style="cyan"))


# ---------------------------------------------------------------------------
# 1. Notifications & Alerts
# ---------------------------------------------------------------------------

def _show_notifications(config: dict) -> None:
    """Global Zapier webhook, desktop alerts, intervals, status-change alerts."""
    while True:
        config = load_config()
        n = config.setdefault("notifications", {})
        webhook = n.get("zapier_webhook", "")
        desktop = n.get("desktop_enabled", True)
        status_change = n.get("alert_on_status_change", True)
        coming_soon = n.get("coming_soon_only", False)
        wh_int = n.get("webhook_interval_minutes", 3)
        dt_int = n.get("desktop_interval_minutes", 10)

        from homesearch.config import settings as env_settings
        effective = webhook or env_settings.zapier_webhook_url or ""
        status_line = f"[green]{effective}[/green]" if effective else "[dim]Not set[/dim]"

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Setting", style="dim", min_width=28)
        table.add_column("Value")
        table.add_row("Global webhook URL", status_line)
        table.add_row("Desktop notifications", "[green]On[/green]" if desktop else "[red]Off[/red]")
        table.add_row("Alert on sale → pending", "[green]On[/green]" if status_change else "[dim]Off[/dim]")
        table.add_row("New-listings only (coming soon)", "[green]On[/green]" if coming_soon else "[dim]Off[/dim]")
        table.add_row("Webhook check interval", f"Every [cyan]{wh_int}[/cyan] min")
        table.add_row("Desktop check interval", f"Every [cyan]{dt_int}[/cyan] min")
        table.add_row("", "")
        table.add_row("[dim]Zapier setup[/dim]", "[dim]zapier.com → Webhooks (Catch Hook) → SMS/Twilio/Slack[/dim]")
        console.print(Panel(table, title="[bold cyan]Notifications & Alerts[/bold cyan]", border_style="cyan"))

        choice = questionary.select(
            "Notifications:",
            choices=[
                "\u2190 Back",
                "Set webhook URL",
                "Clear webhook URL",
                f"Toggle desktop notifications  (now: {'On' if desktop else 'Off'})",
                f"Toggle sale\u2192pending alerts  (now: {'On' if status_change else 'Off'})",
                f"Toggle coming-soon only  (now: {'On' if coming_soon else 'Off'})",
                "Webhook check interval",
                "Desktop check interval",
            ],
            style=HOUSE_STYLE,
        ).ask()
        if choice is None or choice == "\u2190 Back":
            return

        if choice == "Set webhook URL":
            url = questionary.text(
                "Zapier webhook URL:",
                default=webhook,
                style=HOUSE_STYLE,
            ).ask()
            if url is not None:
                n["zapier_webhook"] = url.strip()
                save_config(config)
                _write_env_webhook(url.strip())
                console.print("[green]Webhook saved.[/green]")

        elif choice == "Clear webhook URL":
            n["zapier_webhook"] = ""
            save_config(config)
            _write_env_webhook("")
            console.print("[green]Webhook cleared.[/green]")

        elif choice.startswith("Toggle desktop"):
            n["desktop_enabled"] = not desktop
            save_config(config)
            console.print(f"[green]Desktop notifications: {'On' if not desktop else 'Off'}.[/green]")

        elif choice.startswith("Toggle sale"):
            n["alert_on_status_change"] = not status_change
            save_config(config)
            console.print(f"[green]Sale\u2192pending alerts: {'On' if not status_change else 'Off'}.[/green]")

        elif choice.startswith("Toggle coming-soon"):
            n["coming_soon_only"] = not coming_soon
            save_config(config)
            console.print(f"[green]Coming-soon only: {'On' if not coming_soon else 'Off'}.[/green]")

        elif choice == "Webhook check interval":
            val = questionary.select(
                "Check for new listings every:",
                choices=[Choice("1 minute", 1), Choice("3 minutes", 3), Choice("5 minutes", 5), Choice("10 minutes", 10), Choice("15 minutes", 15)],
                default=wh_int,
                style=HOUSE_STYLE,
            ).ask()
            if val is not None:
                n["webhook_interval_minutes"] = val
                save_config(config)
                console.print(f"[green]Webhook interval: every {val} min.[/green]")

        elif choice == "Desktop check interval":
            val = questionary.select(
                "Check for new listings (desktop-only) every:",
                choices=[Choice("5 minutes", 5), Choice("10 minutes", 10), Choice("15 minutes", 15), Choice("30 minutes", 30), Choice("60 minutes", 60)],
                default=dt_int,
                style=HOUSE_STYLE,
            ).ask()
            if val is not None:
                n["desktop_interval_minutes"] = val
                save_config(config)
                console.print(f"[green]Desktop interval: every {val} min.[/green]")


# ---------------------------------------------------------------------------
# 2. Email & Reports
# ---------------------------------------------------------------------------

def _show_email_settings(config: dict) -> None:
    """SMTP config, recipients, and report settings."""
    while True:
        config = load_config()
        smtp = config["smtp"]
        report = config.setdefault("report", {})

        if smtp.get("email"):
            summary = (
                f"Provider: {smtp.get('provider', 'Custom')}  |  "
                f"Email: {smtp['email']}  |  "
                f"Recipients: {len(smtp.get('recipients', []))}"
            )
        else:
            summary = "SMTP not configured"
        report_time = f"{report.get('hour', 7):02d}:{report.get('minute', 0):02d}"
        new_only = report.get("new_only", False)
        console.print(Panel(
            f"{summary}\n"
            f"Daily report: [cyan]{report_time}[/cyan]  ·  "
            f"New listings only: {'[green]Yes[/green]' if new_only else '[dim]No — all listings[/dim]'}",
            title="[bold cyan]Email & Reports[/bold cyan]",
            border_style="cyan",
        ))

        choice = questionary.select(
            "Email & Reports:",
            choices=[
                "\u2190 Back",
                "Configure SMTP",
                "Manage Recipients",
                "Daily report time",
                f"Toggle new-listings-only emails  (now: {'On' if new_only else 'Off'})",
                "Send report now",
            ],
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

        elif choice == "Daily report time":
            h = questionary.select(
                "Report hour (24h):",
                choices=[Choice(f"{i:02d}:00", i) for i in range(24)],
                default=report.get("hour", 7),
                style=HOUSE_STYLE,
            ).ask()
            m = questionary.select(
                "Report minute:",
                choices=[Choice("00", 0), Choice("15", 15), Choice("30", 30), Choice("45", 45)],
                default=report.get("minute", 0),
                style=HOUSE_STYLE,
            ).ask()
            if h is not None and m is not None:
                config["report"]["hour"] = h
                config["report"]["minute"] = m
                save_config(config)
                console.print(f"[green]Daily report scheduled for {h:02d}:{m:02d}.[/green]")

        elif choice.startswith("Toggle new-listings"):
            config["report"]["new_only"] = not new_only
            save_config(config)
            console.print(f"[green]New-only emails: {'On' if not new_only else 'Off'}.[/green]")

        elif choice == "Send report now":
            from homesearch.services.report_service import generate_report, send_email_report
            with console.status("Generating report..."):
                data = generate_report()
            if not data:
                console.print("[yellow]No active saved searches found.[/yellow]")
            else:
                total_new = sum(len(d["new_listings"]) for d in data.values())
                console.print(f"[bold]{total_new} new listings across {len(data)} searches[/bold]")
                ok = send_email_report(data)
                console.print("[green]Report sent![/green]" if ok else "[red]Failed to send — check SMTP settings.[/red]")


def _manage_recipients(config: dict) -> None:
    while True:
        recipients = config["smtp"].get("recipients", [])
        choices = ["\u2190 Back", "Add new recipient"] + [f"Remove: {r}" for r in recipients]
        choice = questionary.select("Recipients:", choices=choices, style=HOUSE_STYLE).ask()
        if choice is None or choice == "\u2190 Back":
            return
        if choice == "Add new recipient":
            new = questionary.text("Email address:", style=HOUSE_STYLE).ask()
            if new and new.strip() and "@" in new:
                config["smtp"].setdefault("recipients", []).append(new.strip())
                save_config(config)
                console.print(f"[green]Added {new.strip()}.[/green]")
        elif choice.startswith("Remove: "):
            addr = choice[len("Remove: "):]
            if addr in config["smtp"]["recipients"]:
                config["smtp"]["recipients"].remove(addr)
                save_config(config)
                console.print(f"[green]Removed {addr}.[/green]")


# ---------------------------------------------------------------------------
# 3. Search Defaults
# ---------------------------------------------------------------------------

def _show_search_defaults(config: dict) -> None:
    """Default search parameters pre-filled in every new search."""
    while True:
        config = load_config()
        d = config["defaults"]

        price_min = d.get("price_min")
        price_max = d.get("price_max")
        price_str = (f"${price_min:,}" if price_min else "no min") + " – " + (f"${price_max:,}" if price_max else "no max")

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Field", style="dim", min_width=20)
        table.add_column("Value", style="cyan")
        table.add_row("City", d.get("city") or "[dim](none)[/dim]")
        table.add_row("State", d.get("state") or "[dim](none)[/dim]")
        table.add_row("Radius", f"{d.get('radius', 25)} miles")
        table.add_row("Listing type", d.get("listing_type", "sale"))
        table.add_row("Price range", price_str)
        table.add_row("Min bedrooms", str(d.get("bedrooms_min")) if d.get("bedrooms_min") else "[dim](any)[/dim]")
        table.add_row("Min bathrooms", str(d.get("bathrooms_min")) if d.get("bathrooms_min") else "[dim](any)[/dim]")
        table.add_row("Min sqft", f"{d['sqft_min']:,}" if d.get("sqft_min") else "[dim](any)[/dim]")
        table.add_row("HOA max", f"${d['hoa_max']:.0f}/mo" if d.get("hoa_max") is not None else "[dim](any)[/dim]")
        table.add_row("Avoid highways", "[green]Yes[/green]" if d.get("avoid_highways") else "[dim]No[/dim]")
        console.print(Panel(table, title="[bold cyan]Search Defaults[/bold cyan]", border_style="cyan"))

        choice = questionary.select(
            "Search Defaults:",
            choices=[
                "\u2190 Back",
                "City", "State", "Radius", "Listing Type", "Price Range",
                "Min Bedrooms", "Min Bathrooms", "Min Sqft", "HOA Max",
                f"Avoid Highways  (now: {'Yes' if d.get('avoid_highways') else 'No'})",
                "Clear All Defaults",
            ],
            style=HOUSE_STYLE,
        ).ask()
        if choice is None or choice == "\u2190 Back":
            return

        if choice == "City":
            val = questionary.text("Default city:", default=d.get("city", ""), style=HOUSE_STYLE).ask()
            if val is not None:
                config["defaults"]["city"] = val.strip()
                save_config(config)
        elif choice == "State":
            val = questionary.text("Default state:", default=d.get("state", ""), style=HOUSE_STYLE).ask()
            if val is not None:
                config["defaults"]["state"] = val.strip()
                save_config(config)
        elif choice == "Radius":
            val = questionary.select(
                "Default radius:",
                choices=[Choice("5 miles", 5), Choice("10 miles", 10), Choice("25 miles", 25), Choice("50 miles", 50), Choice("100 miles", 100)],
                default=d.get("radius", 25),
                style=HOUSE_STYLE,
            ).ask()
            if val is not None:
                config["defaults"]["radius"] = val
                save_config(config)
        elif choice == "Listing Type":
            val = questionary.select(
                "Default listing type:",
                choices=["sale", "rent", "sold", "coming_soon", "pending"],
                default=d.get("listing_type", "sale"),
                style=HOUSE_STYLE,
            ).ask()
            if val is not None:
                config["defaults"]["listing_type"] = val
                save_config(config)
        elif choice == "Price Range":
            _edit_price_range(config)
        elif choice == "Min Bedrooms":
            val = questionary.select(
                "Default min bedrooms:",
                choices=[Choice("Any", None), Choice("1+", 1), Choice("2+", 2), Choice("3+", 3), Choice("4+", 4), Choice("5+", 5)],
                default=d.get("bedrooms_min"),
                style=HOUSE_STYLE,
            ).ask()
            if val != "__cancelled__":
                config["defaults"]["bedrooms_min"] = val
                save_config(config)
        elif choice == "Min Bathrooms":
            val = questionary.select(
                "Default min bathrooms:",
                choices=[Choice("Any", None), Choice("1+", 1), Choice("1.5+", 1.5), Choice("2+", 2), Choice("2.5+", 2.5), Choice("3+", 3)],
                default=d.get("bathrooms_min"),
                style=HOUSE_STYLE,
            ).ask()
            if val != "__cancelled__":
                config["defaults"]["bathrooms_min"] = val
                save_config(config)
        elif choice == "Min Sqft":
            val = questionary.select(
                "Default min square footage:",
                choices=[
                    Choice("Any", None),
                    Choice("1,000 sqft", 1000), Choice("1,500 sqft", 1500),
                    Choice("2,000 sqft", 2000), Choice("2,500 sqft", 2500),
                    Choice("3,000 sqft", 3000), Choice("4,000 sqft", 4000),
                ],
                default=d.get("sqft_min"),
                style=HOUSE_STYLE,
            ).ask()
            if val != "__cancelled__":
                config["defaults"]["sqft_min"] = val
                save_config(config)
        elif choice == "HOA Max":
            val = questionary.select(
                "Default max monthly HOA:",
                choices=[
                    Choice("Any / No limit", None),
                    Choice("No HOA ($0)", 0),
                    Choice("Up to $100/mo", 100),
                    Choice("Up to $200/mo", 200),
                    Choice("Up to $300/mo", 300),
                    Choice("Up to $500/mo", 500),
                ],
                default=d.get("hoa_max"),
                style=HOUSE_STYLE,
            ).ask()
            if val != "__cancelled__":
                config["defaults"]["hoa_max"] = val
                save_config(config)
        elif choice.startswith("Avoid Highways"):
            config["defaults"]["avoid_highways"] = not d.get("avoid_highways", False)
            save_config(config)
            console.print(f"[green]Avoid highways: {'Yes' if config['defaults']['avoid_highways'] else 'No'}.[/green]")
        elif choice == "Clear All Defaults":
            confirmed = questionary.confirm("Reset all search defaults to blank?", default=False, style=HOUSE_STYLE).ask()
            if confirmed:
                config["defaults"] = {
                    "city": "", "state": "", "radius": 25, "listing_type": "sale",
                    "property_types": [], "price_min": None, "price_max": None,
                    "bedrooms_min": None, "bathrooms_min": None, "sqft_min": None,
                    "hoa_max": None, "avoid_highways": False,
                }
                save_config(config)
                console.print("[green]Search defaults cleared.[/green]")


def _edit_price_range(config: dict) -> None:
    from rich.prompt import Prompt
    d = config["defaults"]
    min_str = Prompt.ask("Min price (Enter for no min)", default=str(d["price_min"]) if d.get("price_min") is not None else "")
    max_str = Prompt.ask("Max price (Enter for no max)", default=str(d["price_max"]) if d.get("price_max") is not None else "")
    try:
        config["defaults"]["price_min"] = int(min_str.strip().replace(",", "").replace("$", "")) if min_str.strip() else None
    except ValueError:
        config["defaults"]["price_min"] = None
    try:
        config["defaults"]["price_max"] = int(max_str.strip().replace(",", "").replace("$", "")) if max_str.strip() else None
    except ValueError:
        config["defaults"]["price_max"] = None
    save_config(config)


# ---------------------------------------------------------------------------
# 4. Providers
# ---------------------------------------------------------------------------

def _show_providers(config: dict) -> None:
    """Enable/disable data providers and set rate limits."""
    while True:
        config = load_config()
        p = config.setdefault("providers", {})
        hh = p.get("homeharvest_enabled", True)
        rf = p.get("redfin_enabled", True)
        rl = p.get("rate_limit_seconds", 1.5)
        mz = p.get("max_zips_per_search", 50)

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Provider", style="dim", min_width=28)
        table.add_column("Status")
        table.add_row("HomeHarvest (Realtor.com / MLS)", "[green]Enabled[/green]" if hh else "[red]Disabled[/red]")
        table.add_row("Redfin", "[green]Enabled[/green]" if rf else "[red]Disabled[/red]")
        table.add_row("Rate limit per ZIP", f"[cyan]{rl}[/cyan] seconds")
        table.add_row("Max ZIPs per search", f"[cyan]{mz}[/cyan]  [dim](capped to avoid slow searches)[/dim]")
        console.print(Panel(table, title="[bold cyan]Data Providers[/bold cyan]", border_style="cyan"))

        choice = questionary.select(
            "Providers:",
            choices=[
                "\u2190 Back",
                f"Toggle HomeHarvest (Realtor)  (now: {'On' if hh else 'Off'})",
                f"Toggle Redfin  (now: {'On' if rf else 'Off'})",
                "Rate limit delay",
                "Max ZIPs per search",
            ],
            style=HOUSE_STYLE,
        ).ask()
        if choice is None or choice == "\u2190 Back":
            return

        if choice.startswith("Toggle HomeHarvest"):
            p["homeharvest_enabled"] = not hh
            save_config(config)
            console.print(f"[green]HomeHarvest: {'On' if not hh else 'Off'}.[/green]")
        elif choice.startswith("Toggle Redfin"):
            p["redfin_enabled"] = not rf
            save_config(config)
            console.print(f"[green]Redfin: {'On' if not rf else 'Off'}.[/green]")
        elif choice == "Rate limit delay":
            val = questionary.select(
                "Delay between ZIP code requests (be respectful):",
                choices=[
                    Choice("0.5 seconds  (fast, risky)", 0.5),
                    Choice("1.0 second", 1.0),
                    Choice("1.5 seconds  (default)", 1.5),
                    Choice("2.0 seconds", 2.0),
                    Choice("3.0 seconds  (slow but safe)", 3.0),
                ],
                default=rl,
                style=HOUSE_STYLE,
            ).ask()
            if val is not None:
                p["rate_limit_seconds"] = val
                save_config(config)
                console.print(f"[green]Rate limit: {val}s.[/green]")
        elif choice == "Max ZIPs per search":
            val = questionary.select(
                "Maximum ZIP codes searched at once:",
                choices=[
                    Choice("10  (fast)", 10), Choice("25", 25), Choice("50  (default)", 50),
                    Choice("100", 100), Choice("200  (slow)", 200),
                ],
                default=mz,
                style=HOUSE_STYLE,
            ).ask()
            if val is not None:
                p["max_zips_per_search"] = val
                save_config(config)
                console.print(f"[green]Max ZIPs: {val}.[/green]")


# ---------------------------------------------------------------------------
# 5. Data & Database
# ---------------------------------------------------------------------------

def _show_data(config: dict) -> None:
    """Database stats, export, prune, and reset."""
    while True:
        from homesearch import database as db
        from homesearch.config import settings as env_settings

        db_path = env_settings.database_path
        try:
            size_bytes = os.path.getsize(db_path)
            size_str = f"{size_bytes / 1024:.1f} KB" if size_bytes < 1_048_576 else f"{size_bytes / 1_048_576:.1f} MB"
        except OSError:
            size_str = "not found"

        conn = db.get_connection()
        try:
            n_searches = conn.execute("SELECT COUNT(*) FROM saved_searches").fetchone()[0]
            n_listings = conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
            n_starred = conn.execute("SELECT COUNT(*) FROM listings WHERE is_starred = 1").fetchone()[0]
            n_results = conn.execute("SELECT COUNT(*) FROM search_results").fetchone()[0]
        except Exception:
            n_searches = n_listings = n_starred = n_results = 0
        finally:
            conn.close()

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Stat", style="dim", min_width=24)
        table.add_column("Value", style="cyan")
        table.add_row("Database path", db_path)
        table.add_row("File size", size_str)
        table.add_row("Saved searches", str(n_searches))
        table.add_row("Listings tracked", str(n_listings))
        table.add_row("Starred listings", str(n_starred))
        table.add_row("Total search results", str(n_results))
        console.print(Panel(table, title="[bold cyan]Data & Database[/bold cyan]", border_style="cyan"))

        choice = questionary.select(
            "Data:",
            choices=[
                "\u2190 Back",
                "Export saved searches to JSON",
                "Export listings to CSV",
                "Clear old listings (prune)",
                "Unstar all listings",
                "Reset ALL data  \u26a0",
            ],
            style=HOUSE_STYLE,
        ).ask()
        if choice is None or choice == "\u2190 Back":
            return

        if choice == "Export saved searches to JSON":
            _export_searches_json()
        elif choice == "Export listings to CSV":
            _export_listings_csv()
        elif choice == "Clear old listings (prune)":
            _prune_old_listings()
        elif choice == "Unstar all listings":
            confirmed = questionary.confirm("Remove star from all listings?", default=False, style=HOUSE_STYLE).ask()
            if confirmed:
                c = db.get_connection()
                c.execute("UPDATE listings SET is_starred = 0")
                c.commit()
                c.close()
                console.print("[green]All stars removed.[/green]")
        elif choice.startswith("Reset ALL"):
            _reset_all_data()


def _export_searches_json() -> None:
    import json as _json
    from homesearch import database as db
    searches = db.get_saved_searches()
    if not searches:
        console.print("[yellow]No saved searches to export.[/yellow]")
        return
    out_path = os.path.expanduser("~/Desktop/homerfindr_searches.json")
    data = [
        {
            "name": s.name,
            "criteria": _json.loads(s.criteria.model_dump_json()),
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
            "is_active": s.is_active,
        }
        for s in searches
    ]
    with open(out_path, "w") as f:
        _json.dump(data, f, indent=2)
    console.print(f"[green]Exported {len(searches)} searches to {out_path}[/green]")


def _export_listings_csv() -> None:
    import csv
    from homesearch import database as db
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT address, city, state, zip_code, price, bedrooms, bathrooms, sqft, "
            "listing_type, property_type, year_built, source_url, is_starred "
            "FROM listings ORDER BY price ASC"
        ).fetchall()
    finally:
        conn.close()
    if not rows:
        console.print("[yellow]No listings to export.[/yellow]")
        return
    out_path = os.path.expanduser("~/Desktop/homerfindr_listings.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Address", "City", "State", "ZIP", "Price", "Beds", "Baths", "Sqft",
                         "Type", "Property", "Year Built", "URL", "Starred"])
        writer.writerows(rows)
    console.print(f"[green]Exported {len(rows)} listings to {out_path}[/green]")


def _prune_old_listings() -> None:
    from homesearch import database as db
    age = questionary.select(
        "Remove listings not seen in:",
        choices=[
            Choice("30 days", 30), Choice("60 days", 60),
            Choice("90 days", 90), Choice("180 days", 180), Choice("1 year", 365),
        ],
        style=HOUSE_STYLE,
    ).ask()
    if age is None:
        return
    conn = db.get_connection()
    try:
        result = conn.execute(
            "DELETE FROM listings WHERE last_seen_at < datetime('now', ?)",
            (f"-{age} days",),
        )
        conn.commit()
        deleted = result.rowcount
    finally:
        conn.close()
    console.print(f"[green]Removed {deleted} listing{'s' if deleted != 1 else ''} older than {age} days.[/green]")


def _reset_all_data() -> None:
    from homesearch import database as db
    from homesearch.config import settings as env_settings
    confirmed = questionary.confirm(
        "DELETE all saved searches, listings, and results? This cannot be undone.",
        default=False,
        style=HOUSE_STYLE,
    ).ask()
    if not confirmed:
        console.print("[dim]Cancelled.[/dim]")
        return
    double = questionary.text(
        "Type DELETE to confirm:",
        style=HOUSE_STYLE,
    ).ask()
    if double and double.strip().upper() == "DELETE":
        conn = db.get_connection()
        conn.execute("DELETE FROM search_results")
        conn.execute("DELETE FROM listings")
        conn.execute("DELETE FROM saved_searches")
        conn.commit()
        conn.close()
        console.print("[bold red]All data deleted.[/bold red]")
    else:
        console.print("[dim]Cancelled.[/dim]")


# ---------------------------------------------------------------------------
# 6. Display & UI
# ---------------------------------------------------------------------------

def _show_display(config: dict) -> None:
    """Results display preferences."""
    while True:
        config = load_config()
        d = config.setdefault("display", {})
        rpp = d.get("results_per_page", 50)
        sort = d.get("default_sort", "match_score")
        starred_first = d.get("starred_first", True)

        _SORT_LABELS = {
            "match_score": "Match score (best first)",
            "price_asc": "Price low → high",
            "price_desc": "Price high → low",
            "newest": "Newest listings first",
        }

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Setting", style="dim", min_width=26)
        table.add_column("Value", style="cyan")
        table.add_row("Results per page", str(rpp))
        table.add_row("Default sort order", _SORT_LABELS.get(sort, sort))
        table.add_row("Starred listings first", "[green]Yes[/green]" if starred_first else "[dim]No[/dim]")
        console.print(Panel(table, title="[bold cyan]Display & UI[/bold cyan]", border_style="cyan"))

        choice = questionary.select(
            "Display:",
            choices=[
                "\u2190 Back",
                "Results per page",
                "Default sort order",
                f"Starred listings first  (now: {'Yes' if starred_first else 'No'})",
            ],
            style=HOUSE_STYLE,
        ).ask()
        if choice is None or choice == "\u2190 Back":
            return

        if choice == "Results per page":
            val = questionary.select(
                "Show how many listings per page?",
                choices=[Choice("25", 25), Choice("50  (default)", 50), Choice("100", 100)],
                default=rpp,
                style=HOUSE_STYLE,
            ).ask()
            if val is not None:
                d["results_per_page"] = val
                save_config(config)
                console.print(f"[green]Results per page: {val}.[/green]")
        elif choice == "Default sort order":
            val = questionary.select(
                "Sort search results by:",
                choices=[
                    Choice("Match score (best first)", "match_score"),
                    Choice("Price low → high", "price_asc"),
                    Choice("Price high → low", "price_desc"),
                    Choice("Newest listings first", "newest"),
                ],
                default=sort,
                style=HOUSE_STYLE,
            ).ask()
            if val is not None:
                d["default_sort"] = val
                save_config(config)
                console.print(f"[green]Default sort: {_SORT_LABELS.get(val, val)}.[/green]")
        elif choice.startswith("Starred listings first"):
            d["starred_first"] = not starred_first
            save_config(config)
            console.print(f"[green]Starred first: {'Yes' if not starred_first else 'No'}.[/green]")


# ---------------------------------------------------------------------------
# 7. Scheduler
# ---------------------------------------------------------------------------

def _show_scheduler(config: dict) -> None:
    """All timing settings in one place."""
    while True:
        config = load_config()
        n = config.setdefault("notifications", {})
        r = config.setdefault("report", {})
        wh_int = n.get("webhook_interval_minutes", 3)
        dt_int = n.get("desktop_interval_minutes", 10)
        rh = r.get("hour", 7)
        rm = r.get("minute", 0)

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Job", style="dim", min_width=34)
        table.add_column("Interval", style="cyan")
        table.add_row("Webhook alert checks", f"Every {wh_int} min")
        table.add_row("Desktop alert checks (no webhook)", f"Every {dt_int} min")
        table.add_row("Daily email report", f"{rh:02d}:{rm:02d}")
        console.print(Panel(table, title="[bold cyan]Scheduler[/bold cyan]", border_style="cyan"))

        choice = questionary.select(
            "Scheduler:",
            choices=[
                "\u2190 Back",
                "Webhook check interval",
                "Desktop check interval",
                "Daily report time",
            ],
            style=HOUSE_STYLE,
        ).ask()
        if choice is None or choice == "\u2190 Back":
            return

        if choice == "Webhook check interval":
            val = questionary.select(
                "Check searches with webhook every:",
                choices=[Choice("1 minute", 1), Choice("3 minutes", 3), Choice("5 minutes", 5), Choice("10 minutes", 10), Choice("15 minutes", 15), Choice("30 minutes", 30)],
                default=wh_int,
                style=HOUSE_STYLE,
            ).ask()
            if val is not None:
                n["webhook_interval_minutes"] = val
                save_config(config)
                console.print(f"[green]Webhook interval: every {val} min.[/green]")

        elif choice == "Desktop check interval":
            val = questionary.select(
                "Check searches without webhook every:",
                choices=[Choice("5 minutes", 5), Choice("10 minutes", 10), Choice("15 minutes", 15), Choice("30 minutes", 30), Choice("60 minutes", 60)],
                default=dt_int,
                style=HOUSE_STYLE,
            ).ask()
            if val is not None:
                n["desktop_interval_minutes"] = val
                save_config(config)
                console.print(f"[green]Desktop interval: every {val} min.[/green]")

        elif choice == "Daily report time":
            h = questionary.select(
                "Report hour (24h):",
                choices=[Choice(f"{i:02d}:00", i) for i in range(24)],
                default=rh,
                style=HOUSE_STYLE,
            ).ask()
            m = questionary.select(
                "Report minute:",
                choices=[Choice("00", 0), Choice("15", 15), Choice("30", 30), Choice("45", 45)],
                default=rm,
                style=HOUSE_STYLE,
            ).ask()
            if h is not None and m is not None:
                r["hour"] = h
                r["minute"] = m
                save_config(config)
                console.print(f"[green]Daily report: {h:02d}:{m:02d}.[/green]")


# ---------------------------------------------------------------------------
# About
# ---------------------------------------------------------------------------

def _show_about() -> None:
    """About page — ASCII house, version, update check."""
    from homesearch import __version__
    from homesearch.services.update_service import check_for_update

    console.print("[bold cyan]  /\\[/bold cyan]")
    console.print("[bold cyan] /  \\[/bold cyan]")
    console.print("[bold cyan]/____\\[/bold cyan]")
    console.print("[bold cyan]| [] |[/bold cyan]")
    console.print()
    console.print(f"[bold cyan]HomerFindr[/bold cyan] v{__version__}")
    console.print("[dim]Find homes fast across all platforms.[/dim]")
    console.print("[dim]github.com/iamtron/HomerFindr[/dim]")
    console.print()

    with console.status("Checking for updates..."):
        latest = check_for_update(__version__)

    if latest:
        console.print(f"[bold yellow]\u2b06  Update available: v{latest}[/bold yellow]")
        console.print("[dim]  Run: pip install --upgrade homesearch[/dim]")
    else:
        console.print("[green]\u2713  You are on the latest version.[/green]")


# ---------------------------------------------------------------------------
# Helper — write webhook URL to .env
# ---------------------------------------------------------------------------

def _write_env_webhook(url: str) -> None:
    env_path = os.path.join(os.path.expanduser("~"), ".homesearch", ".env")
    os.makedirs(os.path.dirname(env_path), exist_ok=True)
    lines = []
    found = False
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("ZAPIER_WEBHOOK_URL="):
                    lines.append(f"ZAPIER_WEBHOOK_URL={url}\n")
                    found = True
                else:
                    lines.append(line)
    if not found:
        lines.append(f"ZAPIER_WEBHOOK_URL={url}\n")
    with open(env_path, "w") as f:
        f.writelines(lines)
