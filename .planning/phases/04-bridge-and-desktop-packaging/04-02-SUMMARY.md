---
phase: 04-bridge-and-desktop-packaging
plan: "02"
subsystem: packaging
tags: [pipx, macos, launcher, desktop, cli]
dependency_graph:
  requires: []
  provides: [packaging/HomerFindr.command, packaging/homerfindr_launcher.sh, packaging/README.md]
  affects: [pyproject.toml]
tech_stack:
  added: []
  patterns: [pipx-install, macos-command-launcher, platypus-wrapper, osascript]
key_files:
  created:
    - packaging/HomerFindr.command
    - packaging/homerfindr_launcher.sh
    - packaging/README.md
  modified:
    - pyproject.toml
decisions:
  - "Use .command file as primary macOS launcher (zero dependency, works on any Mac)"
  - "Platypus .app build is developer-optional; documented in README but not auto-built"
  - "homerfindr entry point already in pyproject.toml; only description update needed"
metrics:
  duration: "2 minutes"
  completed: "2026-03-26T00:33:29Z"
  tasks_completed: 2
  files_changed: 4
---

# Phase 04 Plan 02: CLI Global Install and macOS Desktop Launcher Summary

macOS double-click launcher (.command) and Platypus wrapper script (.sh) for HomerFindr desktop launch, with comprehensive pipx install instructions — both entry points (homerfindr, homesearch) validated in pyproject.toml.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create packaging directory with macOS launchers and install instructions | 460aec9 | packaging/HomerFindr.command, packaging/homerfindr_launcher.sh, packaging/README.md |
| 2 | Validate pyproject.toml entry points and add HomerFindr project metadata | f9ae7d1 | pyproject.toml |

## What Was Built

### packaging/HomerFindr.command

A macOS double-click launcher. The `.command` extension causes Terminal.app to open and execute the script. It:
- Prepends `$HOME/.local/bin` to PATH (Pitfall 6 from research: Finder-launched Terminal may not have pipx bin in PATH)
- Sources `~/.zshrc` and `~/.bashrc` for additional PATH entries
- Checks for `homerfindr` with `command -v` and runs it if found
- Shows a friendly install message with exact pipx commands if not found

### packaging/homerfindr_launcher.sh

A Platypus wrapper script for creating a polished Dock-pinnable `.app` bundle. Uses `osascript` to open a real Terminal.app window running `homerfindr`. This is the correct approach per research — Platypus `Interface: None` + osascript delegation, because Platypus Text Window lacks interactive stdin (which questionary requires for arrow-key navigation).

### packaging/README.md

Comprehensive installation and packaging documentation covering:
- pipx install (production and editable dev install)
- Verification steps and PATH troubleshooting
- .command launcher setup and macOS security bypass
- Platypus .app build with exact CLI invocation
- Uninstall instructions
- Troubleshooting guide for common issues

### pyproject.toml

Description updated from `"Universal home search aggregator - find your perfect home across all platforms"` to `"HomerFindr - universal home search aggregator across all platforms"` for branded display in `pipx list` and `homerfindr --help`.

Both entry points confirmed present and valid:
- `homerfindr = "homesearch.main:app"`
- `homesearch = "homesearch.main:app"`

## Decisions Made

1. `.command` file is the primary deliverable — zero tooling dependency, works immediately on any Mac with pipx installed. Platypus `.app` is documented as a developer-optional enhancement.

2. Platypus is NOT built automatically — it requires Platypus.app + CLI tool to be installed by the developer. The plan correctly delineates committed artifacts (scripts, README) from build-time artifacts (.app).

3. No code changes to the Python package were needed — entry points were already correctly defined in pyproject.toml from initial project setup.

## Deviations from Plan

None — plan executed exactly as written. All files match the specified content patterns and acceptance criteria.

## Known Stubs

None. The packaging scripts are complete and functional. No placeholder content or wired-but-empty data paths.

## Self-Check: PASSED

- packaging/HomerFindr.command exists: FOUND
- packaging/homerfindr_launcher.sh exists: FOUND
- packaging/README.md exists: FOUND
- pyproject.toml updated: FOUND
- Commit 460aec9 exists: VERIFIED
- Commit f9ae7d1 exists: VERIFIED
