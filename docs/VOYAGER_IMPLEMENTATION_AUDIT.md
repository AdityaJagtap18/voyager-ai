# Voyager AI — Implementation Audit

Verified against the running code (`app/`, `web/src/`), not against the PRD's own claims. Each row
reflects what actually executes today, checked by reading the route/agent/component source and,
where noted, by driving the live frontend against the live backend.

Legend: **Working** = real, end-to-end, verified · **Partial** = real but incomplete/fallback-only ·
**Stub** = UI shell with no backend, or `ComingSoon` placeholder · **Fixed this pass** = found broken,
fixed and tested in this audit.

## Travel Workspace

| Feature | Status | Evidence | Notes |
|---|---|---|---|
| Home dashboard | Partial | `web/src/pages/Home.tsx` | Correct IA (hero, 6 quick links, trip list) but visually a plain approximation of `docs/design/references/*` — flat gradient hero (no photo), no top search bar, no bell/avatar, monochrome icons, no trip cover photos. Rebuild tracked separately. |
| Plan a Trip | Working | `app/api.py:257` → `MultiAgentWorkflow`/`CrewAIOrchestrator` | 4-agent pipeline runs for real; not yet visually aligned to reference. |
| My Trips / Trip Detail | Working | `app/api.py:244,249`, `TripDetail.tsx` | Itinerary, accommodations, restaurants (now with Live/AI-suggestion badges), flights/hotels/weather/map tabs all backed by real endpoints. |
| Bookings & Wallet | Partial | `app/api.py:362-394` (bookings CRUD only) | No wallet/payment concept exists server-side; the nav label overstates scope — it's booking-reference tracking only. |
| Budget & Expenses | Working | `app/api.py:405-424` | Real CRUD against `models_db.py`. |
| Group Trips | **Stub** | `App.tsx:55` → `ComingSoon` | No backend support at all. |
| Travel Companion | **Stub** | `App.tsx:56` → `ComingSoon` | No backend support at all. |
| Flights search | Working | `app/api.py:592-613`, `Flights.tsx` | Real provider-backed autocomplete + search. |
| Hotels search | Working | `app/api.py:613-644`, `Hotels.tsx` | Real provider-backed; same `services/hotels_api.py` used for accommodation fusion. |
| Weather | Working | `app/api.py:644` | Real forecast API. |
| Maps / routing | Working | `app/api.py:654-664` | Real ORS-backed search + route. |
| Document upload/download, share links | Working | `app/api.py:502-592` | Real, file-backed. |

## AI Engineering Workspace

| Feature | Status | Evidence | Notes |
|---|---|---|---|
| Agent Studio | Partial | `AgentStudio.tsx`, `app/api.py:196` (`/api/agents` lists agents) | Lists real agents/frameworks; the "visual workflow" graph and Run/Test Run controls in the reference image are not wired to a live execution — informational only. |
| Models & Routing | Partial | `ModelsRouting.tsx`, `app/api.py:173` | Lists real configured models (`llm_gateway.py`); no live routing-policy editor. |
| RAG & Knowledge | Working | `app/api.py:206-244`, `app/rag/` | Real ingestion + search against the knowledge base, used by `get_context_for_destination` in the agent pipeline. |
| Workflows (LangGraph) | **Stub** | `App.tsx:61` → `ComingSoon` | `app/workflow.py`'s LangGraph pipeline is real and runs on every trip, but there is no dedicated UI for it — the nav item is a placeholder. |
| Observability | Partial | `Observability.tsx`, trace embedded in `/api/trips/{id}` response | Real per-run trace (step/status/duration/error) from `workflow.py`/`crewai_adapter.py`'s `trace` list — not the LangSmith/Langfuse/model-comparison dashboard shown in the reference; those integrations don't exist. Previously crashed intermittently for accommodation traces (see Bug fix below) — fixed this pass. |
| Evaluations | Working | `app/api.py:438-477` | Real evaluation runs against stored cases. |
| Security Lab | Working | `app/api.py:488-493` (guardrails scan/events) | Real guardrail-scan endpoint; not a generic "security lab" beyond this. |

## Bug fixed this pass: Observability `'<' not supported between NoneType and NoneType`

**Root cause:** `app/agents/accommodation_agent.py`'s sort key,
`x.get('avg_distance_to_attractions', float('inf'))`, only applies its default when the key is
*missing*. `_calculate_attraction_proximity` (same file) explicitly sets
`accommodation['avg_distance_to_attractions'] = None` — a present key with a `None` value — whenever
an accommodation can't be geocoded or the distance matrix fails/errors. With two or more such
accommodations in the list, Python's `sort()` tries to compare `None < None` and raises
`TypeError: '<' not supported between instances of 'NoneType' and 'NoneType'`, which surfaced in the
trip's trace as a failed `accommodation` step in Observability.

**Fix:** the sort key now treats an explicit `None` the same as a missing key (`float('inf')`), so
un-rankable accommodations sort last instead of crashing the comparison.

**Regression test:** `tests/test_accommodation_agent.py::test_find_accommodations_sorts_without_crashing_when_multiple_have_no_distance`
reproduces it directly (two accommodations that fail to geocode) and asserts the call no longer raises.

## MCP dependency / test-collection

Checked this pass: `tests/test_mcp_server.py` currently collects and passes (7/7) against the
installed `mcp==1.30.0`, which still exposes `mcp.server.fastmcp.FastMCP` as used by
`app/mcp_server.py`. The *risk* flagged earlier was real, though: `requirements.txt` had `mcp`
unpinned, so a fresh `pip install` today can resolve `mcp` 2.x, which renamed `FastMCP` →
`MCPServer` and breaks that import (and collection of this test file) on a clean environment. Pinned
to `mcp<2` in `requirements.txt` to prevent recurrence; no code change was needed since the currently
installed version already works.

## Design/UI gap (reference vs. current)

Reviewed all 4 images in `docs/design/references/` (Home, Agent Studio, Trip Detail/Itinerary,
Observability) against the live app. The current implementation already matches the reference's
**information architecture** closely — same sidebar sections/order, same page set, same tab
structures — so this is a visual-fidelity gap, not a rebuild from scratch. Concretely missing/wrong
on every page, most visible on Home:

- No logo mark (paper-plane icon) next to the "Voyager AI" wordmark — text-only today.
- No persistent top bar: reference has a global "Ask Voyager anything…" search field, notification
  bell, and avatar; current layout has none.
- Hero banner is a flat two-color gradient with 2 CTAs; reference uses a photographic background
  (mountain/lake/temple) with a gradient overlay and 3 CTAs (Plan a Trip / AI Engineering / Explore
  Demos).
- Quick-link tiles use plain small monochrome icons; reference uses colored icon badges (rounded
  square per category color) with larger bold labels.
- Trip cards have no cover photo and a plain status pill; reference uses a destination photo with an
  overlaid status pill (Upcoming/Planning/Completed) and bolder typography.
- The 45-file icon/illustration library at `Voyager-AI-SVG-Components/Voyager-AI-SVG-Components/`
  (Navigation, Travel, AI-Engineering, Status, Components, Illustrations, Logos — not the "354 files"
  initially reported, which was build-tool noise from `.venv_run`'s bundled vendor assets) is already
  referenced by path convention in `Home.tsx` (`/icons/<Category>/<file>.svg`) but is under-used:
  colors/badges, the logo mark, and illustration assets aren't applied yet.

Remaining UI-fidelity work (Home/Plan a Trip/Observability rebuild, full design-token system, the
other pages, breakpoint verification) is tracked as an in-progress follow-on to this audit, not yet
complete as of this document.

## Architecture (unchanged by this pass)

4-agent pipeline (Research → Accommodation → Dining → Itinerary) orchestrated by either
`app/workflow.py` (LangGraph) or `app/orchestration/crewai_adapter.py` (CrewAI), both producing an
identical trace/result shape consumed by the same frontend. Real provider integrations: ORS
(geocoding/routing), `hotels_api.py` / `restaurants_api.py` (RapidAPI), flights/weather providers,
RAG knowledge base, guardrails. No microservices/Redis/Kafka/Kubernetes were introduced or are
needed for anything audited here.

## Phase 10 — Real flight grounding (scoped first slice of the "CRITICAL PRODUCT EXPANSION" request)

A new, much larger task arrived mid-project asking Voyager to become a complete travel
planning/discovery/comparison/booking platform (flights, accommodation, transportation,
activities, restaurants, unified trip proposal, 3-level booking, budget intelligence, My Trips
command center). Attempting the whole thing in one pass would mean fabricating most of it — the
task's own acceptance criteria explicitly forbid that ("Do not use mock data to claim live booking
functionality"). This pass implements one real, honestly-scoped slice and documents the rest as
named gaps rather than faking them.

**What was built — real flight search grounding the itinerary:**

- `Trip.origin` (nullable, free-text departure city/airport) added to `app/models_db.py`,
  `TripCreateRequest`/`TripSummary` in `app/schemas.py`, and threaded through `create_trip` in
  `app/api.py`. Since this project has no migration framework (SQLite via `Base.metadata.create_all`,
  which only creates missing *tables*, never adds columns to an existing one), `app/db.py` gained a
  small `_add_missing_sqlite_columns()` step that `ALTER TABLE`s in any model column absent from the
  on-disk table — verified live: the pre-existing "Goa" trip survived the restart with `origin: null`
  rather than the whole `trips` table being dropped/recreated.
- `services/flights_api.py` gained `search_flights_for_trip(origin_query, destination_query,
  depart_date)`: resolves both free-text places via the existing `autocomplete_place()`, then calls
  the existing `search_one_way()`. Returns `None` (never a fabricated list) when the provider is
  unconfigured, a place can't be resolved, no offers come back, or the provider errors — mirroring
  `accommodation_agent.py`'s `_get_real_hotels()` fallback-to-None pattern. Each offer is tagged
  `"source": "real"`.
- Wired into both orchestrators as a new `flights` step with its own trace entry: a "research →
  flights → accommodation → dining → itinerary" node in `app/workflow.py` (LangGraph), and a
  `search_flights` CrewAI tool/agent/task in `app/orchestration/crewai_adapter.py`, inserted the same
  way in both so the trace shape and step ordering stay identical across frameworks (same as every
  other step in this pipeline). The step records `"skipped"` (not an error) when no `origin`/
  `start_date` was given, so a trip created without them costs nothing extra and shows no false error.
- Frontend: `PlanTrip.tsx` gained a "Departure from" field; `TripDetail.tsx` gained a Flights tab
  showing each real offer (airline, price, stops, duration, departure/arrival) with a **Level-2
  booking handoff** link, labeled "Search & book on Google Flights →", plus an explicit caption
  ("Voyager can't link directly to this exact offer, and no booking is completed here"). This
  honesty constraint exists because **neither `flights_api.py` nor `hotels_api.py` returns a
  booking deep-link for a specific offer** — confirmed by reading both services fully — so any
  "continue to book" link can only be a generic provider search URL, never a link to the exact
  bookable instance. Claiming otherwise would violate the task's "do not pretend a booking has been
  completed if only a provider link was opened" constraint.
- Tests added: `tests/test_flights_api.py` (5 new cases for `search_flights_for_trip` — unconfigured,
  unresolvable origin, no offers, success tagging, provider error), `tests/test_workflow.py` (3 new
  cases for the `flights` node — skipped/success/error), `tests/test_crewai_adapter.py` (2 new cases
  for the `search_flights` tool). Existing trace-order assertions in both orchestrator test files
  updated to include the new `flights` step. Full suite: **196 passed**.
- Live-verified against the real RapidAPI key (not mocked): restarted the dev backend (user
  confirmed first, since a standing instruction says not to tear it down unspoken), confirmed the
  pre-existing trip survived the schema migration, then created a trip with `origin: "Mumbai"` and
  `start_date: "2026-12-10"` — got back 5 real Air India/Air India Express offers (BOM→GOI/GOX,
  $48–$64, with real departure/arrival timestamps), trace `flights: success`. Re-checked the
  pre-existing trip's Flights tab shows the honest "No real flight data for this trip... add a
  departure city and start date" message instead of an empty table or fabricated content.

**What was explicitly NOT built this pass, and why (per the task's own instruction to document
limitations rather than fake them):**

- **Transportation discovery** (airport transfers, rental cars, public transit, taxis, intercity) —
  no provider integrated for any of these; would need a dedicated adapter and credentials this
  project doesn't have.
- **Activity/attraction ticketing** (tour/ticket prices, availability, booking) — attractions today
  come only from the LLM-generated research step, not a real ticketing provider.
- **Restaurant reservation booking** — `restaurants_api.py` (RapidAPI local-business-data) is
  discovery-only; it has no reservation/booking endpoint.
- **"Replace one selection without regenerating the whole trip"** — the pipeline is still a single
  linear run per trip; there's no per-section state model yet that would let a user swap just the
  hotel and recompute only the affected budget/itinerary sections. This is a real architecture
  change (stateful section storage + partial re-run), not a quick addition.
- **Level 3 direct booking** — no provider here offers partner/booking API access; everything
  booking-related stays Level 1 (discovery) or Level 2 (honest handoff link), per the acceptance
  criteria's own instruction to implement the adapter interface and document the limitation rather
  than fabricate completed bookings.
- **Full "My Trips command center"** (chronological timeline, readiness checklist, proactive
  alerts, cross-trip travel-document view) — My Trips today is the trip list + existing per-trip
  tabs (Itinerary/Flights/Restaurants/Accommodations/Bookings/Budget/Documents/Share); the
  dashboard-style rollup across all of a user's trips hasn't been built.
- **Budget intelligence labeling real vs. estimated costs together** — the Budget tab still tracks
  only the user-set target vs. logged `Expense` rows; it doesn't yet pull in the real flight price
  or LLM-estimated accommodation/dining costs into one rollup with clear real/estimated labels. The
  Flights/Accommodations/Restaurants tabs individually label each item "Live listing"/"Live
  pricing"/"AI suggestion" (pre-existing pattern), but a trip-level combined total isn't computed.

These are the concrete remaining gaps against the expansion request; each needs its own scoped
increment rather than being attempted (and faked) in this one.

## Phase 10 (second slice) — real transportation discovery

Follow-on to the flight-grounding slice above: adds one more honestly-scoped real capability from
the expansion request's Transportation section, rather than fabricating rental-car listings, taxi
fares, or public-transit schedules — none of which has an integrated provider.

**What was built**: `app/agents/transport_agent.py`'s `TransportAgent.find_airport_transfer()`
geocodes "`<destination> Airport`" via the existing ORS geocoding (`services/ors_api.py`, already
used by the accommodation/itinerary agents) and routes it to the trip's chosen accommodation with
ORS Directions (`driving-car` profile, also already used for the itinerary's travel-time
calculations) — giving a **real routed distance and drive time**. It deliberately returns only
those two numbers, never a price: ORS doesn't expose fares, and no rental-car/taxi/public-transit
pricing API is integrated, so no price is shown or estimated for this step, per the anti-fabrication
constraints. Returns `None` (not a fabricated route) when ORS is unconfigured, there's no
accommodation location yet, the airport can't be geocoded, or the routing call errors.

Wired into both orchestrators as a new `transportation` step (after `accommodation`, since it needs
the chosen accommodation's coordinates; before `dining`): a `_transportation_node` in
`app/workflow.py`, and a `find_airport_transfer` CrewAI tool/agent/task in
`app/orchestration/crewai_adapter.py`. Added a `TripDetail.tsx` "Transportation" tab showing the
real distance/drive-time when found, with an explicit "not a fare" caption, and an honest empty
state naming exactly what isn't covered (rental cars, taxi fares, public transit - no provider).
`ors_api.py` gained an `is_configured()` helper (mirroring `flights_api.py`/`hotels_api.py`) instead
of relying on a bare `ORS_API_KEY` check at each call site.

**Tests**: new `tests/test_transport_agent.py` (5 cases: unconfigured, no accommodation location,
unresolvable airport, real route success, routing error) plus 2 cases each added to
`tests/test_workflow.py`/`tests/test_crewai_adapter.py` for the new orchestrator step (skip/success/
error), with both files' mocked-agent builders updated to also mock `TransportAgent`. 206 tests pass.

**Live-verified** (user approved restarting the dev backend again): created a Mumbai→Goa trip with
the real ORS key configured; the `transportation` trace step ran (`status: success`) but returned
`null` because this session had already exhausted ORS's free daily Matrix/Directions quota
("Quota exceeded", visible in the backend log) from the many live verifications run earlier in this
project - confirming the "never fabricate, return None instead" path actually fires under a real
provider failure, not just in a mocked test. The Trip Detail Transportation tab correctly rendered
the honest "no real transfer route" empty state rather than inventing a distance. The success-path
rendering (a real route found) is covered by `test_transport_agent.py`'s mocked test instead, since
the quota didn't allow demonstrating it live today.

**Still not built** (unchanged from the flights slice's gap list): rental-car listings, taxi fare
estimates, public-transit schedules/fares, intercity transport options - all need a provider this
project doesn't have access to; the adapter-interface pattern here (`TransportAgent`, returning
`None` on any failure) is the template a future provider integration would slot into.

## Phase 10 (third slice) — labeled real-vs-estimated budget rollup

Third slice of the expansion request's budget-intelligence section: "never mix estimated
LLM-generated costs with confirmed provider prices without clearly labeling them."

**What was built**: `TripBudget.tsx` (the Budget & Expenses tab) now shows two clearly separated
things instead of one blurred number:

- **"Live reference quotes"** - the cheapest real (`source: "real"`) flight offer and real
  accommodation nightly rate found during planning, each with its own currency shown as returned
  (no fabricated FX conversion or combining different currencies into one figure). Explicitly
  labeled "not booked, and not counted in the totals below" - these are informational, not summed,
  since summing every alternative search result would misrepresent them as cumulative cost.
- **Committed total vs. budget target** - unchanged target-tracking UI, but now sums **confirmed
  bookings** (`Booking` rows with `status: "confirmed"`) together with **logged expenses**
  (`Expense` rows, unchanged), broken out separately in a caption ("Confirmed bookings: ₹X · Logged
  expenses: ₹Y"). Pending/cancelled bookings and AI-estimated accommodation/dining price ranges are
  explicitly excluded from this total and stated as excluded, rather than parsed and summed - an
  LLM-generated range like "₹2000–3500" has no reliable single numeric value, and guessing one
  would be exactly the kind of estimated-vs-confirmed mixing this requirement forbids.
- Backend: `accommodation_agent.py`'s real-hotel fusion (`_get_real_hotels`) now also carries
  `price_raw`/`currency` numeric fields alongside the existing display string `price_per_night`, so
  the frontend can show/compare a real nightly rate without parsing free-text formatting - never
  derived from the display string, straight from the provider's own numeric field.

**What was deliberately not attempted**: a single grand total across real flights + real
accommodation + LLM-estimated dining/activities + confirmed bookings + logged expenses. Building
one number out of sources with different confidence levels and different currencies would be the
literal violation this requirement warns against, so the rollup keeps those sources visually and
textually separate instead. Per-traveler cost division was also not added - the `Trip` model has no
traveler-count field yet (a separate, scoped addition if wanted).

**Tests**: `tests/test_accommodation_agent.py`'s real-hotel test extended to assert the new
`price_raw`/`currency` fields. `tsc --noEmit` clean. 206 backend tests still pass (no backend
contract change beyond the two new accommodation fields).

**Live-verified** (third approved backend restart): created a trip with a real flight search,
set a ₹20,000 budget target, added one confirmed ₹4,500 booking and one logged ₹1,200 expense.
The Budget tab correctly showed "$45 USD cheapest live flight (Air India Express)" in the live-quotes
card (not counted in the total) and "₹5,700 committed of ₹20,000" with the ₹4,500/₹1,200 breakdown
caption - confirmed via screenshot. This trip's real-hotel search fell back to the LLM path (no
real accommodation offers found for this query), so the accommodation live-quote card correctly did
not render rather than showing nothing or a fabricated placeholder.

## Phase 10 (fourth slice) — My Trips command center: readiness, alerts, timeline

Fourth slice of the expansion request. Re-reading the request's "My Trips command center" list
against what already exists: flights/accommodation/transportation/restaurants/itinerary/bookings/
budget tabs already exist per-trip on Trip Detail (built in earlier Phase 10 slices and before), and
generic document upload (`TripDocuments.tsx`) already covers "upload external booking confirmations
when sync unavailable" - any file, including a booking confirmation PDF, not booking-type-specific
but functionally equivalent. What was actually missing was the cross-trip rollup: a readiness
checklist, alerts, and a chronological timeline, all absent until now.

**What was built** (`MyTrips.tsx`, `TripCard.tsx` - frontend only, no backend changes): fetches each
trip's full detail + bookings + documents (same `Promise.all` pattern `Observability.tsx` already
uses for its stat tiles) and computes, per trip, purely from data that's already real:

- **Readiness checklist** (6 real checks, no fabricated scoring): itinerary planned, real flight
  data found, accommodation chosen, budget target set, a booking confirmed, travel documents
  attached. Shown as an "N/6 ready" badge on each `TripCard`.
- **Alerts**: a trip starting within 14 real days with no confirmed booking, or no documents
  attached, surfaces a plain-language alert; a trip whose planning actually failed (`status ===
  "failed"`) surfaces too, linking to its real error. All derived from present/absent real data and
  real date math - no predicted risk score, no invented urgency.
- **Chronological timeline**: trips with a real `start_date` in the future, sorted soonest-first,
  with the real date and a real day-count.

**Live-verified**: loaded `/trips` with 6 existing real trips - the 5/6-ready trip (the one with a
confirmed booking + logged expense from the earlier budget-rollup verification) and a 1/6-ready trip
(no origin, so no real flights) both showed correct badges. Created a trip dated 6 days out with no
booking/documents; the Alerts card correctly appeared with both expected messages, and the timeline
correctly sorted it first. `tsc --noEmit` clean; 206 backend tests still pass (no backend changed).

**Not built**: a live map or cross-trip calendar view (Maps page already exists per-trip, not
aggregated); push-style notifications (no infra for that - these are rendered, not delivered,
alerts). These would be reasonable follow-ons but weren't asked for as explicitly as the checklist/
alerts/timeline were.

## Phase 10 (fifth slice) — per-section selection without full regeneration

Fifth slice: "Allow replacing individual selections without regenerating entire trip (e.g.,
changing hotel must not regenerate flight/itinerary). Recalculate only affected budget/itinerary
sections on change." Read literally, the parenthetical and the following sentence seem to
disagree (itinerary depends on accommodation location in this app's existing design, so it can't
both "not regenerate" and "recalculate... on change") - treated the second sentence as the actual
requirement: don't touch *unrelated* sections, but do recompute what genuinely depends on the
changed selection.

**What was built**: `Trip` gained two nullable index columns, `selected_accommodation_index` and
`selected_flight_index` (positions into the plan's own `accommodations`/`flights` lists - these
options have no separate id). Two new endpoints:

- `PATCH /api/trips/{id}/select-flight {index}` - validates the index, sets it, and touches
  nothing else. Flights don't feed into anything else in this pipeline today, so this is a clean
  demonstration of "change one thing, regenerate nothing."
- `PATCH /api/trips/{id}/select-accommodation {index}` - validates the index, then re-runs *only*
  `ItineraryAgent.create_schedule()` with the newly selected accommodation's coordinates (research/
  accommodation-search/dining/flights are never re-run), replaces `plan.itinerary` with the result,
  and appends an `itinerary_recompute` trace entry. If the recompute itself fails (e.g. ORS down),
  the selection still succeeds and the *old* itinerary is kept rather than lost - handled the same
  "never silently lose real data" way the rest of this phase has.

Frontend: `TripDetail.tsx`'s Flights and Accommodations tabs got a "Select"/"Selected" control per
option, with a note on the Accommodations tab stating exactly what does and doesn't get
recalculated. `types.ts`/`client.ts` extended for the new fields/endpoints.

**Tests**: 6 new cases in `tests/test_api.py` - select-flight sets the index and changes nothing
else (asserted via full plan-dict equality), out-of-range and no-options-yet rejections for both
endpoints, select-accommodation's itinerary recompute (asserts the new accommodation's coordinates
were passed to `create_schedule`, and that attractions/flights/accommodations in the plan are
unchanged), and the recompute-failure path keeping the old itinerary. 212 tests pass; `tsc --noEmit`
clean.

**Live-verified** (backend restarted in the background, confirmed healthy before testing): selected
accommodation index 1 on a real trip - response showed `selected_accommodation_index: 1`, all 5
accommodations still present and unchanged, and a new `itinerary_recompute: success` trace entry.
Selected a real flight offer in the browser - the UI correctly showed "Selected" on the chosen
offer and "Select" on the rest, persisting after reload.

**Not built**: recalculating a *budget* section on selection change - there's still no structured,
parseable numeric budget rollup across plan sections (per the budget-rollup slice's own documented
decision not to parse LLM-estimated price ranges), so there's no "affected budget section" to
recompute yet beyond what the Budget tab's live-quotes card already shows dynamically from
whichever flight/accommodation happens to be cheapest - it doesn't yet prefer the *selected* one.
That's a reasonable, small follow-on once this is wanted.
