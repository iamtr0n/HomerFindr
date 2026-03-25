# Technology Stack

**Project:** HomerFindr — UX Polish Milestone
**Researched:** 2026-03-25
**Scope:** Adding arrow-key CLI menus, ASCII art, macOS .app packaging, and professional real estate web UI to an existing Python 3.11 / FastAPI / React / Vite / Tailwind codebase.

---

## Recommended Additions

### Arrow-Key Interactive CLI Menus

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| questionary | 2.1.1 | Arrow-key select/checkbox/confirm prompts | Actively maintained (last release Aug 2025), built on prompt_toolkit 3, supports Python 3.11+, clean API, integrates alongside Typer without conflict |

**Use questionary. Do not use InquirerPy. Do not use simple-term-menu.**

InquirerPy (0.3.4) is in maintenance mode — no PyPI release in 12+ months, multiple unresolved open issues, and Snyk classifies it as Inactive. Its fuzzy-search advantage is irrelevant here since the requirement is pre-built option lists (zero free typing). simple-term-menu (1.6.6, Dec 2024) is Linux-primary; its macOS support works but the library is a lower-level curses wrapper with less integration polish for Rich-based output.

questionary provides `select`, `checkbox`, `confirm`, and `text` prompt types, uses prompt_toolkit under the hood (same as InquirerPy), and is stable with a 2.1.1 release in August 2025. It does not conflict with Typer — questionary calls are invoked inside Typer command functions, replacing `typer.prompt()` calls.

```bash
pip install "questionary>=2.1.1"
```

**Pattern:** questionary handles the interactive selection; Rich handles all display output (tables, panels, progress bars). The two libraries are complementary, not competing.

---

### ASCII Art Splash Screen

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| art | 6.5 | Text-to-ASCII-art for splash screen, headers | 677+ fonts, actively maintained (Apr 2025 release), MIT licensed, one-call API |
| Rich | >=13.7.0 (already in stack) | Color, panels, gradients around ASCII art output | Already installed, handles colorizing the ASCII art output |

**Use art. Do not use pyfiglet as the primary library.**

Both art (6.5, Apr 2025) and pyfiglet (1.0.4, Aug 2025) are actively maintained. However, art has a significantly larger font catalog (677+), a simpler one-call API (`art.text2art("HomerFindr", font="random")`), built-in random-font and typo-tolerance features, and broader Python 3.7+ support. pyfiglet is fine as a fallback if a specific classic FIGlet font is needed that art doesn't have, but for the splash screen use case art is the right primary choice.

Rich is already in the stack and handles the coloring, panels, and layout around the ASCII art output. art + Rich together produce the full "colorful house-themed splash screen" without additional dependencies.

```bash
pip install "art>=6.5"
```

**Example usage:**
```python
from art import text2art
from rich.console import Console
from rich.panel import Panel

console = Console()
ascii_house = text2art("HomerFindr", font="banner3-D")
console.print(Panel(ascii_house, style="bold cyan"))
```

---

### macOS .app / Desktop Packaging

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| PyInstaller | 6.19.0 | Bundle Python CLI into standalone macOS .app | Actively maintained (Feb 2026), Python 3.8-3.14, produces real .app bundles, supports universal2 binaries, large community |

**Use PyInstaller. Do not use py2app. Do not use Briefcase for this use case.**

py2app is macOS-only which matches the target platform, but it has less active community support, fewer recent tutorials, and more friction with modern pyproject.toml-based projects. Briefcase (BeeWare) is optimized for GUI apps (Tkinter, toga) not CLI-over-terminal tools — it adds unnecessary overhead and complexity for a terminal app that launches a browser.

PyInstaller 6.19.0 (released Feb 14, 2026) is the current standard for Python app packaging. It supports:
- `--onefile` for a single executable (easiest for global `homerfindr` command)
- `--windowed` / macOS .app bundle creation (for Dock shortcut)
- `universal2` for Apple Silicon + Intel compatibility
- Python 3.11 (confirmed supported)

**Two packaging targets needed:**

1. **Global `homerfindr` CLI command** — achieved via the existing `pyproject.toml` `[project.scripts]` entry point after `pip install -e .`. PyInstaller is not needed for this; it already works post-install. This is the primary "desktop launchable" path.

2. **macOS .app bundle for Dock** — PyInstaller `--windowed` wraps the CLI entry point into a `.app` that opens Terminal and runs the CLI. This is a secondary convenience target.

```bash
pip install "pyinstaller>=6.19.0"
# Build standalone CLI binary
pyinstaller --onefile --name homerfindr homesearch/main.py
# Build macOS .app bundle
pyinstaller --windowed --name HomerFindr homesearch/main.py
```

**Important caveat (MEDIUM confidence):** PyInstaller's `--windowed` on macOS creates an .app that does not open a visible Terminal window by default — it suppresses stdout. For a CLI tool, a small wrapper shell script or `.command` file placed in the Applications folder is often simpler and more reliable than a full PyInstaller .app bundle. Verify this behavior against the specific Python 3.11 / macOS 15 combination before committing to the PyInstaller .app approach.

---

### Professional Real Estate Web UI

#### Component Library Strategy

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| shadcn/ui | latest (CLI-installed) | Copy-paste React + Tailwind component primitives | Not a dependency — components are owned code. Works with Vite. Has property card pattern. Uses Tailwind already in stack. |
| lucide-react | ^0.424.0 (already in stack) | Icons: bed, bath, sqft, price, garage, etc. | Already installed, shadcn/ui uses lucide-react natively |
| Tailwind CSS | ^3.4.7 (already in stack) | All styling utility classes | Already installed |

**Use shadcn/ui as the source for component primitives. Do not import a pre-built real estate template or third-party component library.**

The existing stack already has Tailwind CSS 3.4.7, React 18, Vite 5, and lucide-react. Adding a heavy component library (Chakra UI, MUI, Ant Design) would conflict with the existing Tailwind setup and balloon the bundle. shadcn/ui is not a library — it is a CLI that copies component source code into `src/components/ui/`. This means zero runtime dependency, full ownership of component code, and no version conflicts.

shadcn/ui has an official Vite installation guide (`npx shadcn@latest init` on Vite projects) and ships with a property card pattern (`/blocks/product-cards-19`) featuring image, price, beds/baths/sqft, badges, and CTA buttons — exactly the HomerFindr property card shape.

**Components to pull from shadcn/ui:**
- `Card`, `CardContent`, `CardHeader` — property listing cards
- `Badge` — listing status (Active, New, Price Drop)
- `Button` — actions (Save, View Listing, Email Report)
- `Table` — sortable results grid
- `Separator`, `Skeleton` — loading states
- `Select`, `Slider` — filter controls (price range, beds)
- `Sheet` — mobile filter sidebar

**Setup on existing Vite project:**
```bash
cd frontend
# Requires TypeScript path aliases — add to vite.config.js:
# resolve: { alias: { "@": path.resolve(__dirname, "./src") } }
npx shadcn@latest init
npx shadcn@latest add card badge button table select slider sheet skeleton separator
```

Note: shadcn/ui requires path alias `@` to resolve to `src/`. The existing Vite config does not have this — it must be added. This is a one-line change to `vite.config.js`.

---

## Full Additions Summary

```bash
# Python additions (add to pyproject.toml [project.dependencies])
pip install "questionary>=2.1.1"
pip install "art>=6.5"

# Python dev addition (add to pyproject.toml [project.optional-dependencies] dev)
pip install "pyinstaller>=6.19.0"

# Frontend (run in frontend/ directory)
npx shadcn@latest init
npx shadcn@latest add card badge button table select slider sheet skeleton separator
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Arrow-key menus | questionary 2.1.1 | InquirerPy 0.3.4 | InquirerPy is inactive/unmaintained since 2022 |
| Arrow-key menus | questionary 2.1.1 | simple-term-menu 1.6.6 | Lower-level curses wrapper, less Rich integration, Linux-primary |
| ASCII art | art 6.5 | pyfiglet 1.0.4 | pyfiglet is fine but art has 677+ fonts vs pyfiglet's ~100, simpler API |
| macOS packaging | PyInstaller 6.19.0 | py2app | Less maintained, more friction with pyproject.toml projects |
| macOS packaging | PyInstaller 6.19.0 | Briefcase | Designed for GUI apps, not terminal CLI tools |
| Web UI components | shadcn/ui | Chakra UI / MUI | Would conflict with existing Tailwind setup; heavier bundle |
| Web UI components | shadcn/ui | Pre-built templates (Hously, etc.) | Opaque code, non-standard, hard to maintain |

---

## Compatibility Notes

- **questionary + Typer:** questionary is called inside Typer command functions. No conflict. Rich output can be printed before/after questionary prompts on the same console.
- **art + Rich:** art produces a plain string. Rich's `Console.print()` handles coloring and panel wrapping. Fully compatible.
- **shadcn/ui + existing Tailwind 3.4.7:** shadcn/ui officially supports Tailwind v3. No upgrade to Tailwind v4 is needed or recommended for this milestone.
- **PyInstaller + Python 3.11:** Confirmed supported. PyInstaller 6.x supports Python 3.8–3.14.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| questionary recommendation | HIGH | PyPI version confirmed, maintenance confirmed via official PyPI page |
| InquirerPy not recommended | HIGH | Snyk Inactive classification, no releases since 2022 confirmed |
| art library | HIGH | PyPI page confirms v6.5 Apr 2025, 677+ fonts, MIT license |
| pyfiglet as alternative | HIGH | PyPI page confirms v1.0.4 Aug 2025, actively maintained |
| PyInstaller macOS .app | MEDIUM | Works for GUI apps; terminal-spawning behavior for CLI apps needs verification against macOS 15 + Python 3.11 |
| Global `homerfindr` command via pip install | HIGH | Standard setuptools entry point, already configured in pyproject.toml pattern |
| shadcn/ui on Vite | HIGH | Official Vite installation guide exists at ui.shadcn.com/docs/installation/vite |
| Tailwind v3 + shadcn/ui | HIGH | shadcn/ui officially supports Tailwind v3, no upgrade needed |

---

## Sources

- [questionary PyPI](https://pypi.org/project/questionary/) — v2.1.1, Aug 28 2025
- [questionary GitHub](https://github.com/tmbo/questionary) — active, Python 3.9–3.14
- [InquirerPy Snyk health](https://snyk.io/advisor/python/inquirerpy) — classified Inactive
- [InquirerPy PyPI](https://pypi.org/project/inquirerpy/) — last release 0.3.4 (no date on page)
- [art PyPI](https://pypi.org/project/art/) — v6.5, Apr 12 2025
- [pyfiglet PyPI](https://pypi.org/project/pyfiglet/) — v1.0.4, Aug 15 2025
- [simple-term-menu PyPI](https://pypi.org/project/simple-term-menu/) — v1.6.6, Dec 2 2024, Linux+macOS
- [PyInstaller PyPI](https://pypi.org/project/pyinstaller/) — v6.19.0, Feb 14 2026
- [PyInstaller macOS docs](https://pyinstaller.org/en/stable/usage.html) — usage, macOS bundle
- [shadcn/ui Vite install](https://ui.shadcn.com/docs/installation/vite) — official Vite guide
- [shadcn/ui property card block](https://www.shadcn.io/blocks/product-cards-19) — property listing card pattern
- [shadcn/ui real estate cards — bundui.io](https://bundui.io/blocks/real-estate/property-cards) — Tailwind + shadcn property card sections
