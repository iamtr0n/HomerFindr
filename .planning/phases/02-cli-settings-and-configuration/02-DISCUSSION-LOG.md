# Phase 2: CLI Settings and Configuration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.

**Date:** 2026-03-25
**Phase:** 02-cli-settings-and-configuration
**Areas discussed:** SMTP wizard, First-run experience, Saved searches browser, Config structure
**Mode:** Auto (--auto)

---

## SMTP Wizard

| Option | Description | Selected |
|--------|-------------|----------|
| Provider shortcuts + test | Gmail/Outlook/Yahoo pre-fills, password mask, test send | ✓ |
| Manual entry only | Type everything manually | |

**User's choice:** [auto] Provider shortcuts + test (recommended)

---

## First-Run Experience

| Option | Description | Selected |
|--------|-------------|----------|
| 3-step guided wizard | City, radius, optional SMTP — triggered by missing config | ✓ |
| Full setup wizard | All settings at once | |
| No first-run | Let users discover settings menu | |

**User's choice:** [auto] 3-step guided wizard (recommended)

---

## Saved Searches Browser

| Option | Description | Selected |
|--------|-------------|----------|
| Table + action sub-menu | Rich table with Run/Toggle/Rename/Delete sub-menu | ✓ |
| Simple list | Basic list with limited actions | |

**User's choice:** [auto] Table + action sub-menu (recommended)

---

## Config Structure

| Option | Description | Selected |
|--------|-------------|----------|
| ~/.homerfindr/config.json | Separate from .env, user-home location | ✓ |
| Extend existing .env | Add to current pydantic settings | |

**User's choice:** [auto] ~/.homerfindr/config.json (recommended)

---

## Claude's Discretion

- Welcome banner size, first-run step order, config migration, error handling for corrupt configs
