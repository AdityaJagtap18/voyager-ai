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
