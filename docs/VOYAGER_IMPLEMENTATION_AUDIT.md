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

## Bug fix — itinerary scheduling defaulted every activity to 09:00

**Reported symptom**: the itinerary generator assigned 09:00 to practically every activity on a
day, instead of a realistic chronological schedule.

**Root cause** (`app/agents/itinerary_agent.py`): the actual per-activity time-assignment logic
lives in `_integrate_dining()` - it walks each day's attractions in order, keeping a running
`current_time` that advances by each activity's duration, a 15-minute buffer, and any travel time
to the next one, then stamps that onto `scheduled_time`. That logic was correct. The bug was in
`create_schedule()`: it only *called* `_integrate_dining()` inside `if restaurants and
accommodation_location:`. Whenever either was falsy, `_integrate_dining()` never ran at all, so no
attraction ever got a `scheduled_time` - and `_generate_complete_schedule()`'s
`item.get('scheduled_time', '09:00')` fallback fired for literally every activity on the day,
producing the reported pattern.

`accommodation_location` (`best_accommodation_location` in both `app/workflow.py` and
`app/orchestration/crewai_adapter.py`) is `None` whenever the first accommodation result lacks
coordinates - which happens whenever the real hotel search falls back to an LLM-sourced
accommodation (a known, already-documented intermittent behavior from the Phase 10 transportation
slice). So this bug fired on a realistic, recurring path, not just an edge case.

**Fix**: time assignment now always runs. `_integrate_dining()` is called unconditionally with
`restaurants or []` and whatever `accommodation_location` is (including `None`) - it already
degraded gracefully when either is missing (meal-matching is skipped, but the per-activity timing
loop was never conditioned on either argument). The restaurant-geocoding prep step stays gated on
`restaurants` being non-empty (no point geocoding nothing).

**Also added**, per the full scheduling-fix request:

- `time_source: "estimated"` on every scheduled activity/meal - there is no real per-activity
  booking-slot provider in this codebase, so nothing is ever labeled as a confirmed time; the
  label makes that explicit instead of presenting algorithmic estimates as fact.
- `booking_status: "not_booked"` for the same reason.
- `scheduling_status: "ok" | "conflict"` - an activity whose estimated start lands at/after 21:00,
  or that overflows past midnight, is flagged rather than silently presented as part of a working
  day. The day's `warnings` list explains which activity and why.
- A day with more than 5 attractions is flagged with a day-level warning ("more than comfortably
  fits") instead of silently cramming them all in back-to-back.
- `duration_minutes` and `travel_time_before_minutes` on every activity, so the frontend doesn't
  have to re-parse the free-text `duration` string or infer travel time from a neighboring
  activity's `travel_after`.

**Not built**: real per-activity opening-hours and confirmed-booking-slot scheduling - there's no
provider integration for either in this codebase (attractions are LLM-researched or geocoded, not
sourced from a bookable-slots API), so honoring "respect opening hours / confirmed booking slots"
beyond what's structurally possible today would mean fabricating that data. The `time_source` /
`scheduling_status` fields exist specifically so this gap stays visible instead of being papered
over with invented certainty.

**Frontend** (`TripDetail.tsx`, `types.ts`): the Itinerary tab now shows each activity's duration,
any travel time before it, an "Estimated time" tag, and a "Scheduling conflict" tag when flagged;
day-level warnings (conflicts, overloaded days, day-boundary overflow) render in an inline banner
under the day's heading instead of being silently dropped.

**Tests**: new `tests/test_itinerary_agent.py` (9 cases) - the exact reported failure pattern
(multiple same-day activities, no restaurants, no accommodation location → times must be distinct
and increasing, not all "09:00"); the same without restaurants for a different falsy-accommodation
shape; no-overlap/duration-respecting consecutive scheduling; travel time reflected in the next
activity's start; `time_source`/`booking_status` tagging; late-start conflict flagging; overloaded-
day flagging; multi-day trips scheduling each day independently; and confirming dining integration
still works when restaurant/accommodation data *is* available (the pre-existing correct path).
Both LangGraph (`app/workflow.py`) and CrewAI (`app/orchestration/crewai_adapter.py`) call the same
`ItineraryAgent.create_schedule()`, so the fix and its guarantees apply to both frameworks by
construction - no framework-specific scheduling logic exists to diverge. Full suite: 230 passed
(221 pre-existing + 9 new); `tsc --noEmit` clean.

**Live-verified**: created a real trip (Jaipur, 1 day, no start date/origin - forcing the exact
failure trigger, an LLM-sourced accommodation with `coordinates: None`) against the restarted
backend. Before the fix this would have produced four activities all at "09:00"; after the fix the
same trip produced `09:00, 10:15, 12:30, 13:45` - confirmed both via the raw API response and in
the browser UI (desktop and mobile), each activity correctly tagged "Estimated time".

## Budget-aware flight & transportation recommendations (Phase 11)

The spec for this phase ("Voyager AI — Budget-Aware Flight & Transportation Recommendation Engine")
covers five major subsystems: budget allocation, flight recommendations, transportation
recommendations, a unified deterministic scoring engine, and AI-powered conversational interaction
over real data, plus three-tier booking/provider integration. Given the scope, this pass built and
shipped a first real, end-to-end slice rather than a partial pass at everything. What follows is an
honest account of what's working now versus what's explicitly deferred.

**Built and working:**

- **Deterministic budget allocation engine** (`app/services/budget_allocator.py`, 10 tests) - splits
  a trip's total budget across six categories (flights, accommodation, transport, food, activities,
  misc) using level-specific weights (budget/mid-range/premium, with graceful fallback to mid-range
  for unrecognized levels), subtracts already-committed spend (confirmed bookings + logged expenses,
  never pending/cancelled ones), and supports independent flight/transport budget caps with
  proportional redistribution of any capped excess to the remaining categories. Pure arithmetic - no
  LLM involved, explicitly labeled `"basis": "estimated"` in every response so the UI never implies
  it's a forecast of actual spend.
- **Deterministic flight recommendation/scoring engine** (`app/services/flight_recommendations.py`,
  12 tests) - scores real flight offers already present in `trip.plan.flights` (no new provider
  integration; reuses whatever `services/flights_api.py` already returned) across 5 named categories
  (Best Overall, Cheapest, Fastest, Best Value, Most Convenient) via min-max-normalized weighted
  composite scoring with an explicit over-budget penalty. Every recommendation's explanation string
  is built only from real price/duration/stop deltas vs. the cheapest offer (e.g. "costs $10.86 more
  than the cheapest option" is computed, never written by an LLM) - satisfying the spec's "do not
  allow an LLM to fabricate scores or prices" requirement by not using an LLM for this at all in this
  slice. The per-traveler → total-price assumption is explicit and surfaced in the response's
  `assumptions` list rather than silently guessed.
- **New trip-level fields**: `traveler_count` (defaults to 1), `max_flight_budget_amount`,
  `max_transport_budget_amount` - settable at trip creation or via the new
  `PATCH /api/trips/{id}/budget-caps` endpoint.
- **API wiring**: `budget_allocation` and `flight_recommendations` are computed fresh and attached to
  every `TripDetail` response (`_attach_derived_recommendations()` in `app/api.py`) - never persisted,
  always reflecting the live budget/plan/traveler-count state. `flight_recommendations` is `None` when
  there's no flight data; `budget_allocation` is `None` when no budget target is set.
- **Frontend**: the Flights tab shows a recommendations summary (traveler count, flight budget cap,
  an `any_in_budget` warning, assumptions) plus per-offer tag badges, hover-tooltip reasons, an
  over-budget warning, and total-price-for-N-travelers line. The Budget & Expenses tab shows a new
  "Estimated budget allocation" card with a labeled progress bar per category and a "capped" badge
  where a cap redistributed budget away from that category. Plan a Trip gained Travelers and optional
  Max flight budget fields, wired into trip creation.
- **Tests**: 22 new unit tests across the two new service modules plus 12 new API-level tests in
  `tests/test_api.py` covering traveler-count defaults, budget-cap creation, allocation-once-budget-
  is-set, committed-amount subtraction (confirmed-only), flight recommendations keyed off real plan
  data, the new PATCH endpoint (including partial updates not clobbering other fields), and a
  regression test confirming `select_flight` still leaves `trip.plan` byte-for-byte untouched with
  recommendations present. Full suite: 256 passed (230 pre-existing + 26 new, including a migration
  regression test below).
- **Migration bug found and fixed while building this**: adding `Trip.traveler_count` as a
  non-nullable column with a Python-side `default=1` looked safe but broke every pre-existing trip
  row with a live HTTP 500 (`ResponseValidationError`), because SQLite's `ALTER TABLE ADD COLUMN`
  backfills existing rows with `NULL` and never applies a SQLAlchemy-side default - that only fires on
  INSERT. Fixed `app/db.py`'s `_add_missing_sqlite_columns()` to also backfill NULLs for any column
  with a simple scalar default, unconditionally on every startup (not just the run that adds the
  column), so a NULL left over from an earlier partial migration self-heals on the next restart.
  Regression-tested in `tests/test_db_migration.py` (simulates a pre-migration `trips` table, runs the
  real migration function, asserts the backfill lands) and live-verified against the real dev database
  after a restart: `GET /api/trips/{id}` on a pre-existing trip now returns `traveler_count: 1`
  instead of 500.

**Explicitly deferred (scope, not oversight):**

- **Transportation recommendation engine** - no airport-transfer/local-transport/intercity scoring or
  recommendation logic was built this pass. `app/api.py`'s existing maps/routing endpoints (real
  ORS-backed) are untouched; the spec's "intelligent transport planning" (proximity-based, group-cost
  comparisons) has no new code.
- **AI-powered conversational interaction over real data** - no new LLM-explanation layer was added;
  all explanations in this slice are deterministic template strings, not LLM-generated commentary.
  The spec explicitly allows (and this slice satisfies) "deterministic calculations for scores/prices,
  LLM only to explain" - the LLM-explanation half specifically was left out because the deterministic
  reasons already satisfy the anti-fabrication requirement without it, and adding an LLM pass is a
  separable, clearly-scoped follow-up.
- **Three-tier booking/provider integration** (official handoff beyond the existing "search & book on
  Google Flights" link, direct in-app booking) - not built. No new provider adapters were added.
- **Full budget-level taxonomy** - `_CATEGORY_WEIGHTS` covers budget/mid-range/premium only; economy,
  luxury, and fully custom allocations fall back to mid-range weights rather than having their own
  tuned profiles.
- **Itinerary-affecting integration** ("flight arrival affects day-1 schedule") - flight
  recommendations are computed and displayed but don't yet feed back into `ItineraryAgent.create_schedule()`.

None of the above gaps are silently papered over: no code in this slice fabricates transport pricing,
transport recommendations, or LLM-written scores/explanations to look like these subsystems exist.

## Transportation recommendation engine (Phase 11b)

Audited the existing transportation implementation before building: `app/agents/transport_agent.py`
(Phase 10) finds one real ORS-routed airport-to-accommodation driving transfer (distance/duration,
never a price, since no taxi/rental/transit provider is integrated), and `app/agents/itinerary_agent.py`
separately computes real driving-profile distances between consecutive scheduled stops within a day,
attaching them to each activity as `travel_after: {distance_km, duration_h}`. Neither of these was
previously surfaced as a *recommendation* - the frontend just printed the raw airport-transfer numbers,
and the inter-stop distances were only ever used internally to compute travel time, never shown.

**Built**: `app/services/transport_recommendations.py` (18 tests) - a deterministic mode-classification
layer over both real data sources. `classify_distance()` maps a real distance to a recommended mode
(walk / cycle / taxi_or_transit / dedicated_transfer) via fixed km thresholds, never a fare or live
availability. `recommend_airport_transfer()` annotates the existing real transfer with a recommended
mode + reason (collapsing an implausible "walk the airport transfer" result into taxi_or_transit).
`recommend_local_transport()` walks every real `travel_after` hop already computed by the itinerary
agent and returns one mode recommendation per hop - genuinely new information, not previously computed
or shown anywhere, but built entirely from data the itinerary agent already had. `recommend_transport()`
combines both into one `transport_recommendations` response (`None` when there's no real data on either
side) with an explicit `assumptions` list naming the no-pricing-provider limitation.

**API**: wired into the same `_attach_derived_recommendations()` helper as the Phase 11 budget/flight
work; `TripDetail.transport_recommendations` is computed fresh from `trip.plan.transportation` and
`trip.plan.itinerary.itinerary` on every read, never persisted. 5 new API-level tests in `tests/test_api.py`.

**Frontend**: the Transportation tab now shows the assumptions banner, a "Recommended: <mode>" badge
+ reason on the airport transfer card, and a new "Local transport between stops" card listing every
real inter-stop hop with its day, distance, recommended mode, and reason. Verified live at desktop and
mobile widths against a throwaway trip seeded with synthetic-but-realistically-shaped plan data (this
dev environment has no `ORS_API_KEY` configured, so no trip here has real routed data to exercise this
against naturally - the throwaway trip was deleted after verification).

**Explicitly out of scope, by design, not oversight**:
- **Intercity transport** - `intercity_transport` is always `None`. This app models a trip as a single
  destination, so there is no second city for an intercity leg to connect to; this isn't a provider gap,
  it's a mismatch with the current data model. Multi-city trip support would be a separate, larger change.
- **Group-cost comparisons** and **any fare/price** - impossible to do honestly without a rental-car,
  taxi/rideshare, or public-transit pricing provider, none of which is integrated. No price appears
  anywhere in this output.
- **Rental-car/taxi/transit availability** - same provider gap; never fabricated.

Full suite: 278 passed (256 prior + 18 new unit tests in `tests/test_transport_recommendations.py` +
5 new API tests in `tests/test_api.py`).

## Currency converter (Phase 11e)

A standalone, real-data currency converter, built on request alongside the recommendation engine
work rather than as part of the original spec. `app/services/currency_api.py` wraps Frankfurter
(ECB reference rates, free and keyless) with an in-process per-pair cache (1 hour TTL); every
function returns `None` on a provider/network failure rather than estimating or hardcoding a rate
- the same discipline as every other provider integration in this codebase. Two endpoints:
`GET /api/currency/convert` (one real conversion) and `GET /api/currency/rates` (the full live rate
table for one base currency, used to populate the converter UI's dropdowns). A new standalone page
at `/currency` (linked from Home's quick links) lets a user convert any amount between two
currencies, with a swap button and the live rate/date shown alongside the result. 15 new tests (11
unit + 4 API-level); live-verified in the browser at desktop and mobile widths against the real
Frankfurter API (100 USD → 9,369 INR at the live rate of 93.69, correctly dated).

**Follow-up, same phase**: the user clarified the actual want was inline conversion of recommendation
prices (e.g. a USD flight offer shown in the user's own currency), not just a standalone tool. Added a
"Show prices in" selector to the Flights tab: picking a currency fetches the real rate for each
distinct offer currency present (via the same `currency_api.py`/`/api/currency/convert` built above)
and displays the converted total alongside the original, never replacing or hiding the real source
price. No conversion happens until the user asks for one, and a missing/failed rate falls back to the
original price rather than showing a wrong number. Not yet extended to Hotels or the Budget allocation
card (both still show their original currency) - documented here as the next natural extension of this
same mechanism, not built in this pass.

## AI-powered conversational trip assistant (Phase 11c)

A single-turn Q&A layer over one trip's real data, satisfying the original spec's "AI-powered
conversational interaction over real data" requirement with the same discipline used everywhere else
in Phase 11: the LLM explains, it never computes or invents a number. `app/agents/trip_assistant_agent.py`
sends the model a system prompt that embeds a JSON snapshot of the trip's real data (destination,
budget_allocation, flight_recommendations, transport_recommendations, itinerary days, attraction/
restaurant/accommodation names) and instructs it to answer only from that snapshot, saying so plainly
rather than guessing when the data needed isn't present - verified live (the Jaipur trip's "How is my
budget allocated?" correctly got "The budget allocation is not provided in the TRIP_DATA" rather than
a fabricated number, since that trip has no budget set).

**API**: `POST /api/trips/{trip_id}/assistant` - runs the message through the existing guardrails
scanner first (`_run_guardrail_scan`, same as trip-destination and knowledge-ingestion text), 503s if
no model is configured, then grounds the answer in `_build_trip_assistant_context()`. 8 new tests (3
unit tests for the agent with a mocked LLM, 5 API-level tests covering grounding, 404, 503, and two
guardrail-rejection paths).

**Frontend**: a new "Ask Voyager" tab on Trip Detail (`TripAssistant.tsx`) - three suggested starter
questions, a chat-style message list, and a disclosure that answers are grounded only in real computed
data. Live-verified: asked "How many days is this trip and what destination is it?" against a real
trip and got a correct, grounded answer back through the full stack (API → real OpenAI call → UI).

**Explicitly out of scope**: persisted multi-turn conversation history (every question is answered
fresh from the current trip snapshot, with no memory of earlier questions in the same session) - this
was a deliberate scope cut to ship a working, honest single-turn slice rather than a half-built
multi-turn chat; persisting conversation turns would need a new DB table and is a natural next step.
