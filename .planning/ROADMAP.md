# Roadmap: HomerFindr

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-03-26)
- 🚧 **v1.1 Polish & Verification** — Phases 5-7 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-4) — SHIPPED 2026-03-26</summary>

- [x] Phase 1: Interactive CLI Core (4/4 plans) — completed 2026-03-25
- [x] Phase 2: CLI Settings and Configuration (3/3 plans) — completed 2026-03-25
- [x] Phase 3: Web UI Redesign (4/4 plans) — completed 2026-03-25
- [x] Phase 4: Bridge and Desktop Packaging (2/2 plans) — completed 2026-03-26

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

### 🚧 v1.1 Polish & Verification (In Progress)

**Milestone Goal:** Verify all v1.0 features end-to-end, fix edge cases found, and ship three targeted improvements — property card thumbnail photos, CLI search progress bars, and confirmed-working Settings/Saved Searches menu paths.

- [x] **Phase 5: Property Card Photos** - Real listing thumbnail images visible in web dashboard property cards (completed 2026-03-26)
- [ ] **Phase 6: CLI Progress Bar Polish** - Rich progress bar with provider label replaces hand-rolled spinner during search
- [ ] **Phase 7: End-to-End Verification** - All v1.0 features verified and edge cases patched

## Phase Details

### Phase 5: Property Card Photos
**Goal**: Users can see real listing thumbnail photos in web dashboard property cards, with a polished fallback for listings without images
**Depends on**: Phase 4 (v1.0 complete)
**Requirements**: PHOTO-01, PHOTO-02
**Success Criteria** (what must be TRUE):
  1. User runs a search and sees photo thumbnails on property cards in the web dashboard for listings that have photos
  2. Listing photo loads without a 403 error — no blocked images in DevTools Network tab
  3. Property cards for listings without photos show a styled placeholder (Home icon) instead of a broken image or grey rectangle
**Plans**: 1 plan

Plans:
- [x] 05-01-PLAN.md — Diagnose photo pipeline, fix CDN hotlink blocking, add alt_photos fallback, polish placeholder

### Phase 6: CLI Progress Bar Polish
**Goal**: Users see a rich.progress.Progress bar with percentage and provider label during CLI search — no more static braille spinner
**Depends on**: Phase 5
**Requirements**: CLI-01, CLI-02
**Success Criteria** (what must be TRUE):
  1. User starts a CLI search and sees a progress bar that updates as each ZIP code is searched
  2. Progress bar labels show which provider (Realtor.com / Redfin) is currently running
  3. Progress bar clears cleanly when search completes — results table appears without terminal corruption or residual spinner artifacts
**Plans**: TBD

Plans:
- [ ] 06-01: Replace braille spinner with rich.progress.Progress in tui/results.py

### Phase 7: End-to-End Verification
**Goal**: All v1.0 features are confirmed working end-to-end on a real run; discovered edge cases are patched
**Depends on**: Phase 6
**Requirements**: VERIFY-01, VERIFY-02
**Success Criteria** (what must be TRUE):
  1. User can install via `pipx install .`, launch `homerfindr`, and reach the main menu on a fresh terminal session with no errors
  2. All four main menu paths (New Search, Saved Searches, Settings, Launch Web UI) navigate and return without exceptions
  3. Saved Search "Run Now" executes a real search and updates last_run_at; deleting a search immediately refreshes the list without restart
  4. SMTP wizard completes without KeyError on empty/default config; email report sends successfully when configured
**Plans**: TBD

Plans:
- [ ] 07-01: Walk every CLI and web UI path; patch edge cases found

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Interactive CLI Core | v1.0 | 4/4 | Complete | 2026-03-25 |
| 2. CLI Settings and Configuration | v1.0 | 3/3 | Complete | 2026-03-25 |
| 3. Web UI Redesign | v1.0 | 4/4 | Complete | 2026-03-25 |
| 4. Bridge and Desktop Packaging | v1.0 | 2/2 | Complete | 2026-03-26 |
| 5. Property Card Photos | v1.1 | 1/1 | Complete   | 2026-03-26 |
| 6. CLI Progress Bar Polish | v1.1 | 0/? | Not started | - |
| 7. End-to-End Verification | v1.1 | 0/? | Not started | - |
