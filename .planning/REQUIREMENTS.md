# Requirements: HomerFindr

**Defined:** 2026-03-25
**Core Value:** Find homes fast across all platforms without juggling multiple websites — zero typing required in the CLI

## v1 Requirements

### Bug Fixes & Cleanup

- [ ] **FIX-01**: Fix double `/api` prefix causing 404 on preview search endpoint
- [ ] **FIX-02**: Fix FastAPI startup deprecation warnings (lifespan migration)
- [ ] **FIX-03**: Fix `result_count` always returning zero in search results
- [ ] **FIX-04**: Pin Tailwind CSS version to v3.x to prevent v4 config breaking changes

### CLI Core

- [ ] **CLI-01**: ASCII art house-themed splash screen with gradient colors on launch
- [ ] **CLI-02**: Animated loading sequence with house/building ASCII art during startup
- [ ] **CLI-03**: Arrow-key main menu with options: New Search, Saved Searches, Settings, Launch Web UI, Exit
- [ ] **CLI-04**: Arrow-key search wizard — all 15 fields (type, property, location, radius, ZIP discovery, price, beds, baths, sqft, lot, year, floors, basement, garage, HOA) navigable with arrows + Enter only
- [ ] **CLI-05**: Pre-built option lists for every search field (no free typing required)
- [ ] **CLI-06**: Animated search progress with Rich spinners/progress bars while scraping providers
- [ ] **CLI-07**: Non-blocking search execution (background thread) so CLI stays responsive
- [ ] **CLI-08**: Colorful search results display with Rich tables/panels showing key property details
- [ ] **CLI-09**: Return to main menu after any action completes

### CLI Settings & Configuration

- [ ] **CFG-01**: Settings page accessible from main menu — view/edit all configuration
- [ ] **CFG-02**: SMTP setup wizard with guided arrow-key flow (server, port, email, password, test send)
- [ ] **CFG-03**: Email recipients management — add/remove recipients via arrow-key interface
- [ ] **CFG-04**: Search defaults configuration — set default location, radius, price range
- [ ] **CFG-05**: First-run experience — guided setup on first launch (location preferences, optional SMTP)
- [ ] **CFG-06**: Saved searches browser — arrow-key list to view, run, toggle active/inactive, delete
- [ ] **CFG-07**: Configuration stored in user-friendly location (~/.homerfindr/config.json)

### Web UI

- [ ] **WEB-01**: Clean, minimal Zillow/Redfin-inspired dashboard layout
- [ ] **WEB-02**: Property cards with thumbnail photos, price, beds/baths/sqft, and click-through to original listing
- [ ] **WEB-03**: Dashboard home page showing saved searches overview and recent results
- [ ] **WEB-04**: Sortable/filterable search results grid
- [ ] **WEB-05**: Responsive design that works on mobile browsers (for sharing with friends/family)
- [ ] **WEB-06**: Professional color scheme and typography (clean real estate aesthetic)

### Desktop & Packaging

- [ ] **PKG-01**: Global `homerfindr` CLI command installable via pipx (works from anywhere in terminal)
- [ ] **PKG-02**: Launch Web UI from CLI — starts FastAPI server as daemon thread + opens browser
- [ ] **PKG-03**: macOS .app shortcut for Dock (via Platypus or .command wrapper)
- [ ] **PKG-04**: Graceful server shutdown when CLI exits
- [ ] **PKG-05**: Port collision handling (fallback to next available port)

### Cross-Cutting

- [ ] **XC-01**: Listing deduplication across providers (same property from Realtor.com and Redfin shown once)
- [ ] **XC-02**: Provider health checks with visible error messages when a provider returns 403/errors
- [ ] **XC-03**: Consistent branding — "HomerFindr" name and house theme across CLI and web

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
| FIX-01 | TBD | Pending |
| FIX-02 | TBD | Pending |
| FIX-03 | TBD | Pending |
| FIX-04 | TBD | Pending |
| CLI-01 | TBD | Pending |
| CLI-02 | TBD | Pending |
| CLI-03 | TBD | Pending |
| CLI-04 | TBD | Pending |
| CLI-05 | TBD | Pending |
| CLI-06 | TBD | Pending |
| CLI-07 | TBD | Pending |
| CLI-08 | TBD | Pending |
| CLI-09 | TBD | Pending |
| CFG-01 | TBD | Pending |
| CFG-02 | TBD | Pending |
| CFG-03 | TBD | Pending |
| CFG-04 | TBD | Pending |
| CFG-05 | TBD | Pending |
| CFG-06 | TBD | Pending |
| CFG-07 | TBD | Pending |
| WEB-01 | TBD | Pending |
| WEB-02 | TBD | Pending |
| WEB-03 | TBD | Pending |
| WEB-04 | TBD | Pending |
| WEB-05 | TBD | Pending |
| WEB-06 | TBD | Pending |
| PKG-01 | TBD | Pending |
| PKG-02 | TBD | Pending |
| PKG-03 | TBD | Pending |
| PKG-04 | TBD | Pending |
| PKG-05 | TBD | Pending |
| XC-01 | TBD | Pending |
| XC-02 | TBD | Pending |
| XC-03 | TBD | Pending |

**Coverage:**
- v1 requirements: 34 total
- Mapped to phases: 0
- Unmapped: 34 ⚠️

---
*Requirements defined: 2026-03-25*
*Last updated: 2026-03-25 after initial definition*
