"""Configuration load/save foundation for HomerFindr."""

import copy
import json
from pathlib import Path

from homesearch.tui.styles import console

CONFIG_PATH = Path.home() / ".homerfindr" / "config.json"

DEFAULT_CONFIG = {
    "defaults": {
        "city": "",
        "state": "",
        "radius": 25,
        "listing_type": "sale",
        "property_types": [],
        "price_min": None,
        "price_max": None,
    },
    "smtp": {
        "provider": "",
        "server": "",
        "port": 587,
        "email": "",
        "password": "",
        "recipients": [],
    },
    "version": "1.0",
}


def config_exists() -> bool:
    """Return True if the config file exists on disk."""
    return CONFIG_PATH.exists()


def load_config() -> dict:
    """Load config from disk, merging over defaults. Returns defaults on missing/corrupt file."""
    if not CONFIG_PATH.exists():
        return copy.deepcopy(DEFAULT_CONFIG)
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        console.print("[dim]Config file unreadable -- using defaults.[/dim]")
        return copy.deepcopy(DEFAULT_CONFIG)

    merged = copy.deepcopy(DEFAULT_CONFIG)
    for key in merged:
        if key in data and isinstance(data[key], dict):
            merged[key].update(data[key])
        elif key in data:
            merged[key] = data[key]
    return merged


def save_config(config: dict) -> None:
    """Write config dict to ~/.homerfindr/config.json as formatted JSON."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
