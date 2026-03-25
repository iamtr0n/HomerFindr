"""Shared questionary styles and Rich console for the HomerFindr TUI."""

from questionary import Style
from rich.console import Console

# Shared Rich console instance — all TUI modules use this
console = Console()

# questionary arrow-key menu style — green/cyan house theme (per D-04, D-05)
HOUSE_STYLE = Style([
    ("qmark",       "fg:#00FF7F bold"),       # green question mark
    ("question",    "fg:#00CED1 bold"),       # cyan question text
    ("pointer",     "fg:#00FF7F bold"),       # green arrow pointer
    ("highlighted", "fg:#000000 bg:#00CED1 bold"),  # inverted cyan highlight
    ("selected",    "fg:#00FF7F"),            # green selected
    ("answer",      "fg:#00FF7F bold"),       # green answer
])

# Rich color constants for results table (per D-13)
COLOR_PRICE = "green"
COLOR_BEDS_BATHS = "cyan"
COLOR_SQFT = "yellow"
COLOR_ADDRESS = "white"
COLOR_ACCENT = "bold cyan"
COLOR_SUCCESS = "bold green"
COLOR_WARNING = "yellow"
COLOR_ERROR = "bold red"
