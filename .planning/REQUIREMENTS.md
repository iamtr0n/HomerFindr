# Requirements: HomerFindr

**Defined:** 2026-03-25
**Core Value:** Find homes fast across all platforms without juggling multiple websites — zero typing required in the CLI

## v1 Requirements

### Bug Fixes & Cleanup

- [x] **FIX-01**: Fix double `/api` prefix causing 404 on preview search endpoint
- [x] **FIX-02**: Fix FastAPI startup deprecation warnings (lifespan migration)
- [x] **FIX-03**: Fix `result_count` always returning zero in search results
- [x] **FIX-04**: Pin Tailwind CSS version to v3.x to prevent v4 config breaking changes

### CLI Core

- [x] **CLI-01**: ASCII art house-themed splash screen with gradient colors on launch
- [x] **CLI-02**: Animated loading sequence with house/building ASCII art during startup
- [x] **CLI-03**: Arrow-key main menu with options: New Search, Saved Searches, Settings, Launch Web UI, Exit
- [x] **CLI-04**: Arrow-key search wizard — all 15 fields (type, property, location, radius, ZIP discovery, price, beds, baths, sqft, lot, year, floors, basement, garage, HOA) navigable with arrows + Enter only
- [x] **CLI-05**: Pre-built option lists for every search field (no free typing required)
- [x] **CLI-06**: Animated search progress with Rich spinners/progress bars while scraping providers
- [x] **CLI-07**: Non-blocking search execution (background thread) so CLI stays responsive
- [x] **CLI-08**: Colorful search results display with Rich tables/panels showing key property details
- [x] **CLI-09**: Return to main menu after any action completes

### CLI Settings & Configuration

- [x] **CFG-01**: Settings page accessible from main menu — view/edit all configuration
- [x] **CFG-02**: SMTP setup wizard with guided arrow-key flow (server, port, email, password, test send)
- [x] **CFG-03**: Email recipients management — add/remove recipients via arrow-key interface
- [x] **CFG-04**: Search defaults configuration — set default location, radius, price range
- [x] **CFG-05**: First-run experience — guided setup on first launch (location preferences, optional SMTP)
- [x] **CFG-06**: Saved searches browser — arrow-key list to view, run, toggle active/inactive, delete
- [x] **CFG-07**: Configuration stored in user-friendly location (~/.homerfindr/config.json)

### Web UI

- [x] **WEB-01**: Clean, minimal Zillow/Redfin-inspired dashboard layout
- [x] **WEB-02**: Property cards with thumbnail photos, price, beds/baths/sqft, and click-through to original listing
- [x] **WEB-03**: Dashboard home page showing saved searches overview and recent results
- [x] **WEB-04**: Sortable/filterable search results grid
- [x] **WEB-05**: Responsive design that works on mobile browsers (for sharing with friends/family)
- [x] **WEB-06**: Professional color scheme and typography (clean real estate aesthetic)

### Desktop & Packaging

- [x] **PKG-01**: Global `homerfindr` CLI command installable via pipx (works from anywhere in terminal)
- [x] **PKG-02**: Launch Web UI from CLI — starts FastAPI server as daemon thread + opens browser
- [x] **PKG-03**: macOS .app shortcut for Dock (via Platypus or .command wrapper)
- [x] **PKG-04**: Graceful server shutdown when CLI exits
- [x] **PKG-05**: Port collision handling (fallback to next available port)

### Cross-Cutting

- [x] **XC-01**: Listing deduplication across providers (same property from Realtor.com and Redfin shown once)
- [x] **XC-02**: Provider health checks with visible error messages when a provider returns 403/errors
- [x] **XC-03**: Consistent branding — "HomerFindr" name and house theme across CLI and web

## v2 Requirements

### Enhanced Search

- **SRCH-01**: Zillow provider integration (via RapidAPI, paid)
- **SRCH-02**: Favorites/starring system — save individual properties across searches
- **SRCH-03**: Price change tracking — alert when saved properties change price
- **SRCH-04**: Map view in web UI with property pins

### Notifications

- **NOTF-01**: Push notifications for new listings matching saved searches
- **NOTF-02**: SMS alerts via Twilio integration

## Out of Scope

| Feature | Reason |
|---------|--------|
| User accounts / authentication | Personal tool for self + friends/family, not a SaaS |
| Cloud deployment / hosting | Runs locally, web UI served from local machine |
| Real-time chat / messaging | Not relevant to home search use case |
| Mortgage calculator | Scope creep — Zillow/Redfin already do this well |
| School ratings / neighborhood data | Scope creep — defer to links to external sites |
| Map integration in v1 | High complexity, defer to v2 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FIX-01 | Phase 3 | Complete |
| FIX-02 | Phase 1 | Complete |
| FIX-03 | Phase 3 | Complete |
| FIX-04 | Phase 3 | Complete |
| CLI-01 | Phase 1 | Complete |
| CLI-02 | Phase 1 | Complete |
| CLI-03 | Phase 1 | Complete |
| CLI-04 | Phase 1 | Complete |
| CLI-05 | Phase 1 | Complete |
| CLI-06 | Phase 1 | Complete |
| CLI-07 | Phase 1 | Complete |
| CLI-08 | Phase 1 | Complete |
| CLI-09 | Phase 1 | Complete |
| CFG-01 | Phase 2 | Complete |
| CFG-02 | Phase 2 | Complete |
| CFG-03 | Phase 2 | Complete |
| CFG-04 | Phase 2 | Complete |
| CFG-05 | Phase 2 | Complete |
| CFG-06 | Phase 2 | Complete |
| CFG-07 | Phase 2 | Complete |
| WEB-01 | Phase 3 | Complete |
| WEB-02 | Phase 3 | Complete |
| WEB-03 | Phase 3 | Complete |
| WEB-04 | Phase 3 | Complete |
| WEB-05 | Phase 3 | Complete |
| WEB-06 | Phase 3 | Complete |
| PKG-01 | Phase 4 | Complete |
| PKG-02 | Phase 4 | Complete |
| PKG-03 | Phase 4 | Complete |
| PKG-04 | Phase 4 | Complete |
| PKG-05 | Phase 4 | Complete |
| XC-01 | Phase 3 | Complete |
| XC-02 | Phase 3 | Complete |
| XC-03 | Phase 3 | Complete |

**Coverage:**
- v1 requirements: 34 total
- Mapped to phases: 34
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-25*
*Last updated: 2026-03-25 after roadmap creation — all 34 requirements mapped*
