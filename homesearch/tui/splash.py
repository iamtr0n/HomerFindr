"""HomerFindr splash screen — ASCII art, version badge, typewriter reveal."""

import os
import time

from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from homesearch import __version__
from homesearch.tui.styles import console

# ---------------------------------------------------------------------------
# ASCII logo blocks
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

# House sits to the right of the logo — 13 lines to align with HOMER+spacer+FINDR
_HOUSE = [
    r"        /\    /\       ",
    r"       /  \  /  \      ",
    r"      / /\ \/ /\ \     ",
    r"     /_/  /\/  \_\     ",
    r"     |  .--------.  |  ",
    r"     | .| .----. |. |  ",
    r"     | || |    | || |  ",
    r"     | || |    | || |  ",
    r"     | '| '----' |' |  ",
    r"     |  '--------'  |  ",
    r"     |   .      .   |  ",
    r"     |   |      |   |  ",
    r"     |___|      |___|  ",
]


def show_splash() -> None:
    """Animate HOMER+FINDR text on the left and house art on the right simultaneously."""
    try:
        cols = os.get_terminal_size().columns
    except OSError:
        cols = 80

    compact = cols < 90

    # Build the full sequence of (line, style) for the left column
    logo_items: list[tuple[str, str]] = []
    for i, line in enumerate(_HOMER):
        ratio = i / max(len(_HOMER) - 1, 1)
        style = "bold green" if ratio < 0.35 else ("bold cyan" if ratio < 0.7 else "bold bright_cyan")
        logo_items.append((line, style))
    logo_items.append(("", ""))                                          # spacer
    for i, line in enumerate(_FINDR):
        ratio = i / max(len(_FINDR) - 1, 1)
        style = "bold cyan" if ratio < 0.5 else "bold bright_cyan"
        logo_items.append((line, style))
    logo_items.append(("", ""))
    logo_items.append(("  Search every listing.  Find the one.", "dim white"))

    # Pre-build the static house text
    _house_text = Text()
    for hl in _HOUSE:
        _house_text.append(hl + "\n", style="bold green")

    def _frame(reveal: int) -> Panel:
        logo = Text()
        for line, style in logo_items[:reveal]:
            logo.append(line + "\n", style=style)

        if compact:
            content: object = logo
        else:
            grid = Table.grid(padding=(0, 2))
            grid.add_column("logo", no_wrap=True)
            grid.add_column("house", no_wrap=True, vertical="top")
            grid.add_row(logo, _house_text)
            content = grid

        return Panel(
            content,
            border_style="green",
            subtitle=f"[dim]v{__version__}  ·  Realtor.com  ·  Redfin[/dim]",
            padding=(0, 2),
        )

    with Live(console=console, refresh_per_second=20) as live:
        for i in range(1, len(logo_items) + 1):
            live.update(_frame(i))
            time.sleep(0.05)
        time.sleep(0.8)

    # Logo stays visible above the menu — print commands reference below it
    cmds = (
        "[bold cyan]homesearch[/bold cyan]          [dim]Launch TUI (this menu)[/dim]\n"
        "[bold cyan]homesearch search[/bold cyan]   [dim]Jump straight to search wizard[/dim]\n"
        "[bold cyan]homesearch serve[/bold cyan]    [dim]Start the web UI server[/dim]\n"
        "[bold cyan]homesearch report[/bold cyan]   [dim]Send email report now[/dim]\n"
        "[bold cyan]homesearch saved[/bold cyan]    [dim]list / run / delete / toggle[/dim]"
    )
    console.print(Panel(cmds, title="[dim]CLI Commands[/dim]", border_style="dim", padding=(0, 2)))
