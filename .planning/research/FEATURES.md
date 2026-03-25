# Feature Landscape

**Domain:** Home search aggregator — dual-interface (polished CLI + web dashboard)
**Researched:** 2026-03-25
**Overall confidence:** HIGH (web-verified against real estate apps + CLI tool patterns)

---

## Table Stakes

Features users expect. Missing = product feels incomplete or broken.

### CLI Interface

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Arrow-key navigation throughout | Zero-typing requirement is core value prop; typing menus break the contract | Medium | InquirerPy list/fuzzy prompts cover this natively |
| Contextual help overlay (? key) | lazygit pattern — users should never be stuck wondering what to press | Low | Rich Panel or InquirerPy instruction lines |
| Visual focus indicator | Without clear highlight, which item is selected is ambiguous | Low | InquirerPy handles with cursor/highlight style |
| Progress feedback during search | Scraping Realtor.com/Redfin takes seconds; silent wait feels broken | Low | Rich spinner + status message |
| Search results in scrollable table | Raw print output for 50+ listings is unusable | Medium | Rich Table with pagination or scrollable list |
| Clear error messages with recovery hints | "Connection error" with no next step is a dead end | Low | Rich `[red]` styled messages with suggested action |
| Exit/back at every screen | Users must always be able to go back; trapping them destroys trust | Low | ESC or "Back" option in every InquirerPy menu |
| Saved searches accessible from main menu | Core persistence feature; burying it defeats the purpose | Low | Top-level menu item |
| Sort results (price, beds, date listed) | Unsorted 50-listing dumps are unusable for comparison | Medium | In-memory sort before rendering Rich table |

### Web Interface

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Property cards with photo thumbnail | Zillow/Redfin trained users to expect visual property previews | Medium | React card component; use first photo URL from provider |
| Key stats visible on card | Price, beds/baths, sqft — users scan cards, not details pages | Low | Card layout with icon + stat pairs |
| Click-through to original listing | Users need to act on a listing; dead cards are frustrating | Low | Link to provider URL in every card |
| Filter panel (price, beds, baths, sqft) | Industry standard since Craigslist; absence is jarring | Medium | Sidebar or top filter bar |
| Sort dropdown | Price (low→high), newest first, sqft — expected from any list view | Low | React state sort, no backend needed |
| Saved searches sidebar or dashboard | Without quick access to saved searches, the persistence feature is invisible | Medium | Dashboard route showing saved search cards |
| Results count / "X homes found" | Users need to calibrate whether filters are too narrow | Low | Count in results header |
| Loading state / skeleton cards | Without feedback during API fetch, white screen looks broken | Low | Tailwind skeleton shimmer or spinner |
| Responsive layout | Most real estate browsing happens on phones even for personal tools | Medium | Tailwind responsive grid |
| Empty state with guidance | "No results" with zero guidance makes users think the app is broken | Low | Friendly message + filter adjustment suggestions |

### Both Interfaces

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Deduplication across providers | Same listing on Realtor.com and Redfin appearing twice destroys trust | Medium | Match by address/MLS ID in existing provider architecture |
| Persistent filter state | Losing filters on navigation is a top-cited real estate app complaint | Low | URL params (web) / saved state (CLI) |
| First-run setup wizard | Without SMTP config guidance, email reports silently fail | Medium | Guided arrow-key flow; skip option required |

---

## Differentiators

Features that set HomerFindr apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| ASCII art splash screen (house-themed) | Instantly memorable; signals craft and personality vs generic Typer apps | Low | pyfiglet + Rich coloring; shown on launch, skip after ~1s |
| Colorful animated house loading | Turns a 3-second search wait into a delightful moment | Low | Rich status spinner with house emoji/ASCII frames |
| Zero-account, zero-cloud operation | Privacy-first; no login walls; no "sign up to see results" friction | N/A | Already the architecture; market it deliberately |
| Multi-platform aggregation in one view | The entire value prop — no Zillow, no Redfin, no Realtor.com tab juggling | High | Existing; polish the "X results from 2 sources" header |
| Main menu with settings/SMTP wizard | Most CLI tools dump config to raw env files; guided wizard is rare and valued | Medium | Arrow-key SMTP configuration flow |
| Desktop launchable (macOS .app + global command) | Personal tools that require `cd ~/projects && python main.py` get abandoned | Medium | pyinstaller or AppleScript wrapper |
| Inline result comparison (side-by-side in CLI) | Checking two properties in the terminal without switching to web | High | Rich Columns layout; complex for MVP, strong differentiator |
| "Launch Web UI" from CLI menu | Bridges both interfaces; one command opens browser to local dashboard | Low | `webbrowser.open()` in menu handler |
| Quick-action favorites from CLI | Star a listing from the CLI results view, see it in web dashboard | High | Requires favorites table + sync endpoint |
| Email report as rich HTML | Jinja2 template already available; plain-text email vs formatted HTML with photos is a big gap | Medium | HTML template with property cards; not plain text |

---

## Anti-Features

Features to explicitly NOT build. Build these and the project drifts, slows, or becomes maintenance burden.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| User accounts / authentication | Adds OAuth, session management, security surface for a personal tool used by <10 people | Hard-code "personal use" architecture; no login walls ever |
| Cloud deployment / hosting | Adds infra cost, DNS, SSL cert management, uptime monitoring — zero added value for local use | Stay localhost; document `homerfindr serve` as the startup command |
| Map-based search (interactive map UI) | Maps require Mapbox/Google Maps API keys, billing, and a complex React component — Zillow has this because they need it; a personal tool does not | Radius-based ZIP search already covers the use case without a map |
| Draw-on-map / polygon search | Same problem as map UI; Redfin differentiator that requires paid map API and significant engineering | ZIP radius covers 95% of the need |
| School ratings / neighborhood data overlay | Requires GreatSchools API or web scraping; adds data pipeline complexity for a feature most users can check separately | Link out to Google Maps or Walk Score from property detail |
| Virtual tours / 3D walkthroughs | Matterport integration is a separate paid service; not a scraping concern | Deep link to provider's own virtual tour page |
| Mortgage calculator | Every real estate site has one; it's noise, not signal for a search aggregator | Link to external calculator if needed; don't build the math |
| Agent / scheduler / lead capture | Irrelevant to personal tool; adds forms, CRM thinking, and complexity | Out of scope by definition |
| Push notifications / real-time alerts | WebSocket infra, service workers, browser permissions for local-only tool | Email reports via SMTP already cover this; APScheduler is sufficient |
| Pagination with server-side cursor | For <500 listings from free scrapers, client-side sort/filter is faster to build and fast enough | Client-side filtering in React + in-memory for CLI |
| Dark/light mode toggle | Added complexity for a personal tool where the user sets their terminal/browser theme | Respect OS preference via `prefers-color-scheme`; build one theme |

---

## Feature Dependencies

```
First-run wizard → SMTP config → Email reports (currently fails silently without config)
Global CLI command → Desktop launchable (.app / dock shortcut)
Property cards with thumbnails → Photo URL extraction from providers
Favorites/starred listings → Quick-action favorites from CLI → Sync endpoint
Deduplication → Multi-platform aggregation appearing clean
Sort + filter → Scrollable/paginated results (sort before render)
"Launch Web UI" menu item → Web server auto-start or already-running check
```

---

## MVP Recommendation

For this milestone (UX polish on existing working app), prioritize in this order:

**Must ship (table stakes):**
1. Arrow-key navigation + visual focus indicators throughout CLI (InquirerPy replacement of all Typer prompts)
2. Rich progress spinner during search
3. Scrollable sorted results table in CLI (Rich Table)
4. ASCII art splash screen + colorful CLI theme (pyfiglet + Rich colors)
5. Web property cards with photos, key stats, click-through links
6. Web filter panel + sort dropdown
7. Web loading states + empty states
8. First-run setup wizard (CLI, arrow-key SMTP flow)
9. Global `homerfindr` CLI command

**Ship if time allows (differentiators that complement table stakes):**
10. "Launch Web UI" from CLI main menu
11. Email report as HTML (Jinja2 template)
12. macOS .app / dock shortcut

**Defer:**
- Inline result comparison (High complexity, limited immediate value)
- Quick-action favorites from CLI (Requires new DB table + API endpoint)
- Client-side favorites/starring (Worth a future milestone after core UX is solid)

---

## Sources

- [UX patterns for CLI tools](https://lucasfcosta.com/2022/06/01/ux-patterns-cli-tools.html) — CLI UX principles
- [lazygit GitHub](https://github.com/jesseduffield/lazygit) — Panel-based TUI, ? help overlay, vim/arrow navigation patterns
- [The Complete Guide to Building Developer CLI Tools in 2026](https://dev.to/chengyixu/the-complete-guide-to-building-developer-cli-tools-in-2026-a96) — Current CLI UX standards
- [Using Maps As The Core UX In Real Estate Platforms](https://raw.studio/blog/using-maps-as-the-core-ux-in-real-estate-platforms/) — Why map-based UX is core at scale (and why it's not needed for personal tools)
- [Redesigning Zillow App using Design Thinking Approach](https://insights.daffodilsw.com/blog/redesigning-zillow-app-using-design-thinking-approach) — Zillow UX patterns
- [Redesigning UI/UX of the Redfin App](https://insights.daffodilsw.com/blog/redesigning-ui-ux-of-the-redfin-app) — Redfin UX patterns
- [7 Best Real Estate Website UX Design Examples](https://www.designmonks.co/blog/real-estate-website-ux-design-examples) — Property card and search patterns
- [Real Estate App UX Mistakes to Avoid](https://pitangent.com/real-estate-application-development/real-estate-software-from-these-ux-mistakes/) — Anti-patterns confirmed
- [Top UI/UX Mistakes to Avoid in Property Rental App Development](https://oyelabs.com/top-ui-ux-mistakes-property-rental-app-development/) — Filter persistence, registration barriers
- [Rich Python library docs](https://rich.readthedocs.io/en/latest/progress.html) — Progress bars, spinners, live display, panels, tables (HIGH confidence, official docs)
- [InquirerPy GitHub](https://github.com/kazhala/InquirerPy) — Arrow-key prompts, fuzzy search, customizable key bindings (HIGH confidence, official)
- [pyfiglet PyPI](https://pypi.org/project/pyfiglet/) — ASCII art fonts for splash screen
- [17 Best House Hunting Apps to Find Homes in 2026](https://www.infowindtech.com/best-house-hunting-apps-to-find-homes/) — Table stakes features confirmed against market
- [10 Best Real Estate Apps of 2026](https://solguruz.com/blog/7-real-estate-mobile-apps-that-are-making-good-sales/) — Feature expectations across real estate apps
