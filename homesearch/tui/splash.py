"""ASCII art house-themed splash screen with typewriter reveal animation."""

import os
import time

from art import text2art
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from homesearch.tui.styles import console


def show_splash():
    """Display the HomerFindr ASCII art splash with typewriter animation.

    Per D-01: Large ASCII house art with gradient green-cyan via Rich.
    Per D-02: Typewriter-style reveal using Rich Live, ~2s display, then clear.
    Per D-03: Shows on every launch.

    CRITICAL: The Live context MUST be fully exited before any questionary
    prompt fires. Rich Live and questionary both take terminal ownership.
    """
    try:
        cols = os.get_terminal_size().columns
    except OSError:
        cols = 80

    # Generate ASCII art — fall back to smaller font on narrow terminals
    ascii_art = text2art("HomerFindr", font="banner3-D")
    first_line = ascii_art.splitlines()[0] if ascii_art.splitlines() else ""
    if len(first_line) > cols - 4:
        ascii_art = text2art("HomerFindr", font="small")

    lines = ascii_art.splitlines()

    # House ASCII art to display above the title
    house = [
        "        /\\",
        "       /  \\",
        "      /    \\",
        "     /______\\",
        "     |  __  |",
        "     | |  | |",
        "     |_|__|_|",
    ]

    rendered = Text()

    with Live(console=console, refresh_per_second=20) as live:
        # Typewriter reveal: house first
        for line in house:
            rendered.append(line + "\n", style="bold green")
            live.update(
                Panel(
                    rendered,
                    border_style="green",
                    title="[bold green]HomerFindr[/bold green]",
                    subtitle="[dim cyan]Find your home faster[/dim cyan]",
                )
            )
            time.sleep(0.05)

        rendered.append("\n", style="")

        # Then the ASCII title with gradient (green to cyan)
        for i, line in enumerate(lines):
            # Gradient: early lines green, middle blend, later lines cyan
            ratio = i / max(len(lines) - 1, 1)
            if ratio < 0.4:
                style = "bold green"
            elif ratio < 0.7:
                style = "bold cyan"
            else:
                style = "bold bright_cyan"

            rendered.append(line + "\n", style=style)
            live.update(
                Panel(
                    rendered,
                    border_style="green",
                    title="[bold green]HomerFindr[/bold green]",
                    subtitle="[dim cyan]Find your home faster[/dim cyan]",
                )
            )
            time.sleep(0.04)

        # Hold splash before clearing (per D-02: ~2 seconds total)
        time.sleep(1.5)

    # Live context fully exited — safe for questionary now
    console.clear()
