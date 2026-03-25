# Phase 1: Interactive CLI Core - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-25
**Phase:** 01-interactive-cli-core
**Areas discussed:** Splash screen, Menu navigation, Search wizard, Results display
**Mode:** Auto (--auto) — recommended defaults selected

---

## Splash Screen

| Option | Description | Selected |
|--------|-------------|----------|
| Large house + gradient | Big ASCII house with HomerFindr title, Rich gradient colors | ✓ |
| Minimal text banner | Small text-only banner, fast | |
| Animated scene | Multi-frame house animation | |

**User's choice:** [auto] Large house + gradient (recommended default)
**Notes:** Brand moment, keep under 2 seconds

---

## Menu Navigation

| Option | Description | Selected |
|--------|-------------|----------|
| Arrow pointer + highlight | ► indicator with inverted background | ✓ |
| Numbered list | Type number to select | |
| Vim-style j/k | Keyboard shortcuts | |

**User's choice:** [auto] Arrow pointer + highlight (recommended default)
**Notes:** Green/cyan theme on dark terminal

---

## Search Wizard

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-built ranges + skip | Arrow-selectable ranges, Enter to skip optional fields | ✓ |
| Free typing with validation | Type values, validate on submit | |
| Slider controls | Terminal sliders for ranges | |

**User's choice:** [auto] Pre-built ranges + skip (recommended default)
**Notes:** City/ZIP is only typing field. Summary + confirm at end.

---

## Results Display

| Option | Description | Selected |
|--------|-------------|----------|
| Rich colored table | Color-coded columns, arrow select, Enter opens URL | ✓ |
| Card-style panels | One property per Rich panel | |
| Compact list | Minimal one-line-per-result | |

**User's choice:** [auto] Rich colored table (recommended default)
**Notes:** Arrow to scroll, Enter to open listing in browser

---

## Claude's Discretion

- ASCII art font selection
- Spinner animation style
- Exact color values
- Table column widths
- Error message wording

## Deferred Ideas

None
