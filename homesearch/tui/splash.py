"""HomerFindr splash screen — ASCII art, version badge, typewriter reveal."""

import os
import time

from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from homesearch import __version__
from homesearch.tui.styles import console

# ---------------------------------------------------------------------------
# Hardcoded ASCII logo — no library dependency, always renders correctly
# ---------------------------------------------------------------------------

_HOMER = [
    r"  ██╗  ██╗ ██████╗ ███╗   ███╗███████╗██████╗ ",
    r"  ██║  ██║██╔═══██╗████╗ ████║██╔════╝██╔══██╗",
    r"  ███████║██║   ██║██╔████╔██║█████╗  ██████╔╝",
    r"  ██╔══██║██║   ██║██║╚██╔╝██║██╔══╝  ██╔══██╗",
    r"  ██║  ██║╚██████╔╝██║ ╚═╝ ██║███████╗██║  ██║",
    r"  ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝",
]

_FINDR = [
    r"  ███████╗██╗███╗   ██╗██████╗ ██████╗ ",
    r"  ██╔════╝██║████╗  ██║██╔══██╗██╔══██╗",
    r"  █████╗  ██║██╔██╗ ██║██║  ██║██████╔╝",
    r"  ██╔══╝  ██║██║╚██╗██║██║  ██║██╔══██╗",
    r"  ██║     ██║██║ ╚████║██████╔╝██║  ██║",
    r"  ╚═╝     ╚═╝╚═╝  ╚═══╝╚═════╝ ╚═╝  ╚═╝",
]

_HOUSE = [
    r"              /\    /\              ",
    r"             /  \  /  \            ",
    r"            / /\ \/ /\ \           ",
    r"           /_/ /\ \ \ \_\          ",
    r"          |  _/  \_  _  |          ",
    r"          | | .--. | || |          ",
    r"          | | |  | | || |          ",
    r"          |_|_|__|_|_||_|          ",
]


def _build_frame(rendered: Text, version: str) -> Panel:
    return Panel(
        rendered,
        border_style="green",
        subtitle=f"[dim]v{version}  ·  Realtor.com  ·  Redfin[/dim]",
        padding=(0, 2),
    )


def show_splash() -> None:
    """Display the HomerFindr ASCII splash with typewriter animation.

    Starts an update-check thread so results are ready by the time
    the menu loop starts. Clears the terminal before returning.
    """
    try:
        cols = os.get_terminal_size().columns
    except OSError:
        cols = 80

    rendered = Text()

    # Collapse to compact mode on very narrow terminals
    compact = cols < 60

    with Live(console=console, refresh_per_second=20) as live:
        # --- house art ---
        if not compact:
            for line in _HOUSE:
                rendered.append(line + "\n", style="bold green")
                live.update(_build_frame(rendered, __version__))
                time.sleep(0.04)
            rendered.append("\n")

        # --- HOMER block (green → cyan gradient) ---
        for i, line in enumerate(_HOMER):
            ratio = i / max(len(_HOMER) - 1, 1)
            style = "bold green" if ratio < 0.35 else ("bold cyan" if ratio < 0.7 else "bold bright_cyan")
            rendered.append(line + "\n", style=style)
            live.update(_build_frame(rendered, __version__))
            time.sleep(0.04)

        rendered.append("\n")

        # --- FINDR block (cyan → bright_cyan) ---
        for i, line in enumerate(_FINDR):
            ratio = i / max(len(_FINDR) - 1, 1)
            style = "bold cyan" if ratio < 0.5 else "bold bright_cyan"
            rendered.append(line + "\n", style=style)
            live.update(_build_frame(rendered, __version__))
            time.sleep(0.035)

        rendered.append("\n")

        # --- tagline ---
        rendered.append(
            "  Search every listing.  Find the one.\n",
            style="dim white",
        )
        live.update(_build_frame(rendered, __version__))

        # Brief hold so the full logo is visible before menu appears
        time.sleep(0.8)

    # Live fully exited — logo stays visible above the menu
    from rich.columns import Columns
    from rich.text import Text as RText
    cmds = (
        "[bold cyan]homesearch[/bold cyan]          [dim]Launch TUI (this menu)[/dim]\n"
        "[bold cyan]homesearch search[/bold cyan]   [dim]Jump straight to search wizard[/dim]\n"
        "[bold cyan]homesearch serve[/bold cyan]    [dim]Start the web UI server[/dim]\n"
        "[bold cyan]homesearch report[/bold cyan]   [dim]Send email report now[/dim]\n"
        "[bold cyan]homesearch saved[/bold cyan]    [dim]list / run / delete / toggle[/dim]"
    )
    console.print(Panel(cmds, title="[dim]CLI Commands[/dim]", border_style="dim", padding=(0, 2)))
