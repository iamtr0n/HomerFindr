# Requirements: HomerFindr

**Defined:** 2026-03-25
**Core Value:** Find homes fast across all platforms without juggling multiple websites — zero typing required in the CLI

## v1.1 Requirements

### Photos

- [ ] **PHOTO-01**: User can see real listing thumbnail photos in property cards on the web dashboard
- [ ] **PHOTO-02**: Property cards display a polished placeholder when no listing photo is available

### CLI Polish

- [ ] **CLI-01**: User sees a progress bar with percentage during search execution
- [ ] **CLI-02**: Progress bar shows which provider (Realtor.com / Redfin) is currently running

### Verification

- [ ] **VERIFY-01**: All v1.0 features verified end-to-end — install, CLI menu paths, web UI, saved searches, email reports
- [ ] **VERIFY-02**: Edge cases discovered during walkthrough are patched (SMTP config errors, stale list after delete, etc.)

## Future Requirements

### Photos

- **PHOTO-F01**: Photo gallery with multiple images per listing
- **PHOTO-F02**: Full-screen photo lightbox in web dashboard

### CLI Polish

- **CLI-F01**: Animated ASCII art loading sequence between menu transitions

## Out of Scope

| Feature | Reason |
|---------|--------|
| Photo proxy endpoint | Not needed — `referrerPolicy="no-referrer"` resolves CDN blocking without backend changes |
| pytest suite for live scrapers | Scrapers are network-dependent; unit tests would need mocking that diverges from real behavior |
| Pagination for CLI results | Table is capped at 50 rows intentionally — keeps output readable |
| Cloud deployment | Local-first by design |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PHOTO-01 | Phase 5 | Pending |
| PHOTO-02 | Phase 5 | Pending |
| CLI-01 | Phase 6 | Pending |
| CLI-02 | Phase 6 | Pending |
| VERIFY-01 | Phase 7 | Pending |
| VERIFY-02 | Phase 7 | Pending |

**Coverage:**
- v1.1 requirements: 6 total
- Mapped to phases: 6
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-25*
*Last updated: 2026-03-25 after v1.1 milestone start*
