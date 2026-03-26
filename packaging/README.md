# HomerFindr — Installation and Packaging

HomerFindr ships as a Python package with two launch interfaces: a global CLI command and a macOS desktop launcher.

---

## Install with pipx (Recommended)

[pipx](https://pipx.pypa.io/) installs Python CLI tools in isolated virtual environments while making them available globally on your PATH.

**Install from project root:**

```bash
cd /path/to/HomerFindr
pipx install .
```

This installs two entry points:

- `homerfindr` — primary command
- `homesearch` — alias

**Verify the install:**

```bash
homerfindr --help
which homerfindr   # should print ~/.local/bin/homerfindr
```

**If `homerfindr` is not found after install:**

```bash
pipx ensurepath
```

Then restart your terminal and try again. This adds `~/.local/bin` to your shell's `$PATH`.

---

## Development Install

For live development where source changes take effect immediately (without reinstalling):

```bash
pipx install --editable .
```

Note: changes to entry point definitions in `pyproject.toml` still require a reinstall.

---

## macOS Launcher (.command)

The `packaging/HomerFindr.command` file is a double-click launcher for macOS.

**Setup:**

1. Ensure HomerFindr is installed via pipx (see above)
2. Copy `HomerFindr.command` to your Desktop or Applications folder
3. Make it executable if not already:
   ```bash
   chmod +x HomerFindr.command
   ```
4. Double-click the file — Terminal will open and launch HomerFindr

macOS may show a security prompt on first run ("cannot be opened because the developer cannot be verified"). To allow it: right-click the file → Open → Open.

---

## macOS App Bundle (Platypus)

For a polished Dock-pinnable `.app` bundle, use [Platypus](https://sveinbjorn.org/platypus) (free, open source).

**Requirements:**

- Platypus 5.5+ installed from the Platypus website
- CLI tool enabled: open Platypus.app → Preferences → Install Command Line Tool

**Build the .app:**

```bash
/usr/local/bin/platypus \
  --name "HomerFindr" \
  --interface-type None \
  --author "HomerFindr" \
  --bundle-identifier "com.homerfindr.app" \
  --overwrite \
  packaging/homerfindr_launcher.sh \
  packaging/HomerFindr.app
```

**Install to Applications:**

```bash
cp -r packaging/HomerFindr.app /Applications/
```

**How it works:** The `.app` uses `Interface: None` and delegates to Terminal.app via `osascript`. The `.app` is a launcher only — it opens a new Terminal window running `homerfindr`. This is required because Platypus's built-in output windows do not support interactive stdin (which HomerFindr needs for arrow-key navigation).

**Pin to Dock:** After copying to `/Applications/`, drag `HomerFindr.app` to your Dock.

---

## Uninstall

```bash
pipx uninstall homesearch
```

This removes both the `homerfindr` and `homesearch` entry points.

---

## Troubleshooting

**`homerfindr: command not found` after install**

Run `pipx ensurepath` to add `~/.local/bin` to your shell profile, then restart your terminal.

**Double-clicking `.command` says "homerfindr not found"**

The `.command` script prepends `~/.local/bin` to PATH, but if pipx installed to a different location, check with `which homerfindr` in a regular terminal and update the script's `export PATH` line.

**Port already in use when launching web UI**

HomerFindr automatically scans ports 8000–8010 for an available port. If all are occupied, close other local servers and try again.

**macOS security warning on `.command` or `.app`**

Right-click the file → Open → Open (bypasses Gatekeeper for unsigned local scripts).
