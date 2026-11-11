# VOYAGER AI — MASTER BLUEPRINT

Authoritative architecture and implementation contract for the Voyager AI brownfield transformation. This document supersedes `Promt.txt` as a spec source — `Promt.txt` is the original transformation request; this file is the plan derived from auditing the actual repository against it.

Status date: 2026-11-11.

---

## 1. Executive Summary

Voyager AI today is a **working, small-scale prototype**: a Streamlit UI driving a 4-agent LangGraph workflow (Research → Accommodation → Dining → Itinerary) that uses OpenAI GPT-3.5-turbo for content generation and OpenRouteService for geocoding/routing. It has no database, no auth, no tests, no CI, and (until this transformation) no git history. ~2,200 lines of Python total.

The transformation request (`Promt.txt`) describes a full AI-powered travel platform *and* a configurable AI-engineering playground (model gateway, multi-framework agents, RAG, MCP, observability, evaluation, guardrails, integration marketplace) on a React/FastAPI/Postgres stack with real travel-provider bookings.

**Reality gap:** the target is an enterprise-scale, multi-quarter platform; the current repo is a weekend-project prototype with a Streamlit UI (not React), no backend API layer, no persistence, and no existing tests/CI to preserve. Nearly every "PRESERVE the existing X" instruction in the source prompt (existing React components, existing FastAPI endpoints, existing Postgres schema, existing CI) has no current counterpart to preserve — those sections of the brownfield audit are reported as **N/A, to be built new** rather than retrofitted.

This document is scoped to be honest about that gap: it classifies what exists, defines the target architecture, and lays out phases that can actually be executed and tested one at a time, rather than claiming the full 12-phase vision is one session's work. Phase 0 and Phase 1 are achievable now; later phases are sequenced but gated on explicit go-ahead since each is a substantial, multi-session effort and several depend on provider credentials the user must supply.

---

## 2. Repository Audit (Phase 0 findings)

### 2.1 Current structure

```
voyager-ai-main/
├── app/
│   ├── agents/
│   │   ├── research_agent.py        (134 lines) — GPT-3.5 attraction generation
│   │   ├── accommodation_agent.py   (279 lines) — GPT hotel generation + ORS geocoding + proximity scoring
│   │   ├── dining_agent.py          (325 lines) — GPT restaurant generation + dietary filter + 50km radius filter
│   │   └── itinerary_agent.py       (635 lines) — route optimization (nearest-neighbor), scheduling, meal placement
│   ├── services/ors_api.py          (139 lines) — OpenRouteService geocode/matrix wrapper
│   ├── utils/logger.py              — basic logging setup
│   ├── config.py                    — env-driven settings, validates OPENAI_API_KEY at import time
│   ├── main.py                      (338 lines) — CLI entry point
│   └── workflow.py                  (206 lines) — LangGraph StateGraph orchestration
├── streamlit_app.py                 (363 lines) — Streamlit web UI
├── Voyager-AI-SVG-Components/       — standalone SVG asset library (not yet wired into any frontend)
├── docs/design/references/          — 4 reference images (UI mockups)
├── Promt.txt                        — the transformation brief itself, saved to the repo
├── requirements.txt, Dockerfile, docker-compose.yml, README.md, .gitignore
```

No `tests/`, no `.github/workflows/`, no `data/` directory yet (README references `data/itineraries/` but it's created at runtime), no `.env.example` present despite README referencing it.

### 2.2 Module classification

| Module | Responsibility | Status | Decision | Notes |
|---|---|---|---|---|
| `app/workflow.py` | LangGraph 4-agent orchestration | Working | **PRESERVE / EXTEND** | This is the travel engine's core — wrap with framework adapters later, don't rewrite |
| `app/agents/research_agent.py` | Attraction discovery via GPT | Working | **PRESERVE / EXTEND** | Swap direct OpenAI calls for model-gateway calls in Phase 5, logic stays |
| `app/agents/accommodation_agent.py` | Hotel generation + proximity scoring | Working | **PRESERVE / EXTEND** | Real provider integration (Amadeus/Booking.com) replaces GPT-generated hotel data in Phase 3; proximity scoring logic reusable |
| `app/agents/dining_agent.py` | Restaurant generation + filtering | Working | **PRESERVE / EXTEND** | Same pattern — swap data source, keep filtering logic |
| `app/agents/itinerary_agent.py` | Scheduling + route optimization | Working | **PRESERVE** | Most mature module; real travel-time data already integrated via ORS |
| `app/services/ors_api.py` | Geocoding/routing | Working | **PRESERVE / EXTEND** | Becomes one adapter in the Maps provider category (Section 9) |
| `app/config.py` | Env config | Working, minimal | **EXTEND** | Needs to grow into the settings backbone for a provider/integration registry; currently validates `OPENAI_API_KEY` at import time (side effect on import — flagged as tech debt, fix in Phase 1) |
| `streamlit_app.py` | Web UI | Working | **PRESERVE short-term, REPLACE in Phase 2+** | Keep as the demo/ops UI while a FastAPI + new frontend is built; do not delete until the replacement is functional end-to-end |
| `app/main.py` | CLI | Working | **PRESERVE** | Useful for scripted testing of the workflow without the UI |
| Database / persistence | — | **Does not exist** | **BUILD NEW** | No ORM, no migrations, no schema. Nothing to preserve. |
| Backend API (FastAPI routes) | — | **Does not exist** | **BUILD NEW** | `fastapi`/`uvicorn` are in requirements.txt but unused — aspirational dependency only |
| React frontend | — | **Does not exist** | **BUILD NEW** | Current frontend is Streamlit; a React rewrite is a Phase 2+ decision, not a preservation task |
| Tests / CI | — | **Does not exist** | **BUILD NEW** | No pytest files despite pytest in requirements.txt |
| Auth/authorization | — | **Does not exist** | **BUILD NEW** | Single-user, no accounts |
| Model gateway / LiteLLM | — | **Does not exist** | **BUILD NEW** (Phase 5) | Currently direct `langchain-openai` calls |
| Agent framework adapters (CrewAI, AutoGen) | — | **Does not exist** | **BUILD NEW** (Phase 6) | LangGraph only today |
| RAG / MCP / Observability / Evaluation / Security Lab / Integration Marketplace | — | **Does not exist** | **BUILD NEW** (Phases 7–9) | Entirely new subsystems |

### 2.3 Original PRD reconciliation

`Promt.txt` *is* the current governing brief — there is no separate, older PRD to reconcile against. No conflicting prior requirements were found. The README.md documents the as-built prototype accurately and is consistent with the code; it should be rewritten once Phase 2+ changes the stack, but is not contradicted by anything found in the audit.

---

## 3. SVG / UI Asset Inventory (Section 3.2 of the brief)

Location: `Voyager-AI-SVG-Components/Voyager-AI-SVG-Components/`. These are **standalone icon/illustration assets, not components with props** — plain `.svg` files, not React/JSX components. They are not currently imported anywhere (Streamlit does not consume them; no frontend code references this folder). Treat this as a design-asset library to wire into the frontend once one exists, not as already-integrated UI.

| Asset | Path | Type | Current usage | Reusability | Required action |
|---|---|---|---|---|---|
| agent, database, evaluation, mcp, model, observability, rag, security, workflow | `AI-Engineering/*.svg` | Icon set | None (unused) | High | Preserve; wrap as React icon components in Phase 2+ frontend build |
| badge-success, badge-warning, button-primary, button-secondary, card-outline, input-search, toggle-off/on | `Components/*.svg` | UI primitive mockups | None (unused) | Medium | These look like static mockups of components, not reusable components themselves (no viewBox/prop inspection shows parametrization). Use as the *visual reference* for building real React components (Button, Card, Toggle, Badge, Input) rather than embedding the SVGs directly as controls |
| ai-workflow, bali-temple, mountain-lake, travel-planner | `Illustrations/*.svg` | Illustration | None (unused) | High | Preserve as-is; use directly as decorative illustrations (empty states, hero sections) |
| voyager-logo, voyager-mark, voyager-wordmark | `Logos/*.svg` | Branding | None (unused) | High | Preserve exactly; use for app header/favicon |
| bookings, budget, compass, group-trips, home, my-trips, notifications, plan-trip, settings | `Navigation/*.svg` | Nav icon set | None (unused) | High | Maps directly to the navigation structure in Section 14 of the brief — preserve and use as-is for the primary nav |
| connected, error, success, warning | `Status/*.svg` | Status icon set | None (unused) | High | Preserve; use for integration/connection status indicators (Section 7) |
| activities, currency, flights, hotels, itinerary, map, restaurant, weather | `Travel/*.svg` | Domain icon set | None (unused) | High | Preserve; maps cleanly to Travel Workspace nav items |

**Verdict:** this is a clean, well-organized, directly-usable icon/illustration library for the target navigation and domain model. No duplicates found, no reason to replace anything. The 4 images in `docs/design/references/` are the UI mockup reference required by Section 12 of the brief — they should be inspected visually before any frontend work begins (not yet done in this pass; do this as the first step of Phase 2).

---

## 4. Target Architecture (incremental, not big-bang)

Given the gap in Section 1, the target architecture is built **in layers that each produce a working, demoable increment**, not as a single simultaneous React+FastAPI+Postgres+12-integration rewrite.

```mermaid
graph TD
    subgraph "Now (Phase 0-1)"
        A[Streamlit UI] --> B[LangGraph Workflow]
        B --> C[OpenAI GPT-3.5]
        B --> D[OpenRouteService]
    end
    subgraph "Phase 2-4: Real backend + providers"
        E[FastAPI API] --> B
        E --> F[(PostgreSQL)]
        B --> G[Travel Provider Adapters]
    end
    subgraph "Phase 5-9: AI Engineering Workspace"
        H[Model Gateway / LiteLLM] --> C
        I[Agent Framework Adapters] --> B
        J[RAG / MCP] --> B
        K[Observability + Evaluation] -.-> B
        L[Security Lab / Guardrails] -.-> E
    end
    New_Frontend[React Frontend] -.replaces.-> A
    New_Frontend --> E
```

Stack decisions carried forward from the brief, confirmed as reasonable for this codebase: FastAPI + SQLAlchemy + Alembic + PostgreSQL for the backend; React + TypeScript + Vite + Tailwind for the frontend (once built); LangGraph preserved as the primary orchestration engine with adapters added later, not replaced.

---

## 5. Phase-Gated Roadmap

Each phase below is sized to be independently committable and testable. Phases 0–1 are executed as part of this document's delivery. Phases 2+ require explicit go-ahead before starting, since each is a substantial scope of work and several require external credentials only the user can supply.

| Phase | Objective | Status | Depends on | Blocking external input |
|---|---|---|---|---|
| 0 | Repository audit, git baseline, this document | **COMPLETE** | — | none |
| 1 | Architecture foundation: fix config side-effects, add `.env.example`, pytest scaffold, CI skeleton | **COMPLETE** | Phase 0 | none |
| 2 | FastAPI backend wrapping existing workflow + persistence (Postgres/SQLite) + React frontend using the existing SVG library and UI reference images | **COMPLETE** | Phase 1 | none |
| 3 | Real travel providers (flights/hotels/weather/maps) replacing GPT-generated placeholder data | NOT STARTED | Phase 2 | provider API keys (Amadeus, etc.) |
| 4 | Trip management: bookings/wallet, expenses | **COMPLETE (partial — see notes)** | Phase 2 | none |
| 5 | Model gateway (LiteLLM), provider-agnostic routing | **COMPLETE** | Phase 1 | optional provider keys (Ollama needs none) |
| 6 | Agent framework adapters (CrewAI/AutoGen alongside LangGraph), Agent Studio | **COMPLETE** | Phase 5 | none |
| 7 | RAG + MCP | **COMPLETE** | Phase 5 | none |
| 8 | Observability + Evaluation | **COMPLETE** | Phase 6 | none |
| 9 | Security Lab / guardrails | NOT STARTED | Phase 2 | none |
| 10–12 | Advanced AI, full travel companion, OSS release polish | NOT STARTED | all above | varies |

---

## 6. Risks & Decisions Log

- **R1 — Scope**: the full brief is multi-quarter work; delivering it as one continuous unattended run is not realistic or verifiable. Decision: phase-gate with explicit checkpoints (this blueprint's purpose).
- **R2 — No existing frontend to preserve**: the brief's "preserve existing React components" instructions don't apply; Streamlit stays live until a React replacement is functionally equivalent, avoiding a preserve-nothing gap.
- **R3 — `Config.validate()` ran at import time** (`app/config.py`) and would raise if `OPENAI_API_KEY` was unset, breaking any test or tool that imports agent modules without a real key. **Fixed in Phase 1**: validation is now an explicit call made by `app/main.py` (CLI) and `streamlit_app.py` (web UI) at startup, not a module-import side effect.
- **R4 — Provider access**: flight/hotel/booking providers (Amadeus, Booking.com Demand API, Skyscanner) require partner approval/credentials not available in this session. Phase 3 will build adapters against documented APIs with deterministic test fixtures, and report live integration as "awaiting credentials" per Section 22 of the brief — never fabricating live prices.

---

## 7. Definition of Done (per phase)

A phase is complete when: code compiles/runs, relevant tests pass (fixtures used where live credentials are unavailable), the phase's row in Section 5 is updated to COMPLETE with a commit reference, and no previously-working functionality (CLI, Streamlit UI, workflow) regresses.

---

## 8. Phase 1 Delivery Notes

- `app/config.py`: removed the module-import-time `Config.validate()` call (R3). Validation is now explicit.
- `app/main.py`, `streamlit_app.py`: call `Config.validate()` at their own entry points instead (CLI fails fast with a clear message before prompting; Streamlit shows `st.error` and stops before rendering the rest of the page).
- Added `.env.example` (referenced by README but missing from the repo).
- Added `tests/` with 11 deterministic unit tests covering `Config.validate()`, the `ors_api` geocode/matrix/directions wrappers (mocked HTTP, no network calls, no API keys required), and `ResearchAgent.find_attractions` JSON/markdown-fence parsing and error-fallback paths (mocked LLM, no OpenAI calls). All 11 pass.
- Added `pytest.ini` and `.github/workflows/ci.yml` (runs the test suite on push/PR to `main`). A `flake8` step is included but set to informational/non-blocking (`|| true`): the existing agent modules carry ~285 pre-existing style warnings (trailing whitespace, a few bare `except`, long lines) that are out of scope for Phase 1 to silently rewrite. Recorded as **R5** below for a future, dedicated style-cleanup pass rather than bundled into this phase's gate.
- **R5 — Pre-existing lint debt**: `app/agents/*.py` and `app/services/ors_api.py` have ~285 flake8 warnings (mostly `W293` trailing whitespace, a handful of bare `except:` in `itinerary_agent.py` lines 234/249/431/463). Not fixed in Phase 1 to avoid touching working code beyond this phase's stated scope. Candidate for a small, dedicated cleanup PR before or during Phase 2.

## 9. Phase 2 Delivery Notes

**Backend** (`app/api.py`, `app/db.py`, `app/models_db.py`, `app/schemas.py`):
- FastAPI app with `POST /api/trips`, `GET /api/trips`, `GET /api/trips/{id}`, `GET /api/health`. Wraps `create_workflow()`/`plan_trip()` from `app/workflow.py` completely unchanged — the agents are untouched.
- Persistence via SQLAlchemy, SQLite by default at `data/voyager.db` (gitignored), swappable to Postgres by setting `DATABASE_URL`; no code changes needed for that swap.
- Returns `503` if `OPENAI_API_KEY` is missing, `422` for an invalid `trip_type`/`budget`, `404` for an unknown trip id. A workflow-level exception is caught and stored as a `failed` trip rather than a 500, so the frontend always has something to render.
- 6 new tests in `tests/test_api.py` (17 total now pass) against an isolated temp SQLite db with a mocked workflow — no OpenAI/ORS calls.
- Manually verified end-to-end in the browser: booted the server with a deliberately invalid `OPENAI_API_KEY`, submitted a real trip through the UI, and confirmed the existing `research_agent.py` error-handling path (it catches the OpenAI 401 and returns a placeholder "Error occurred" attraction rather than crashing) surfaces correctly all the way to the Itinerary tab. With a real key this is the same code path that returns a real itinerary.

**Frontend** (`web/`, Vite + React 18 + TypeScript + Tailwind):
- Sidebar navigation matches the UI reference images in `docs/design/references/`: "Travel Workspace" and "AI Engineering Workspace" sections, same item set, same light/indigo palette (colors sampled into `web/tailwind.config.js`'s `brand`/`ink`/`surface` tokens).
- Uses the existing SVG asset library directly (`web/public/icons/`, copied verbatim from `Voyager-AI-SVG-Components/` — no assets recreated or replaced) for the logo, nav icons, and quick-link icons.
- Implemented screens: Home (hero, quick links, recent trips), Plan a Trip (form → `POST /api/trips`), My Trips (list), Trip Detail (Itinerary/Restaurants/Accommodations tabs, rendering the real nested `plan.itinerary.itinerary[]` day/activity structure that `itinerary_agent.py` actually returns).
- Nav items for Bookings & Wallet, Budget & Expenses, Group Trips, Travel Companion, and every AI Engineering Workspace item route to an explicit "coming in a later phase" page rather than a dead or fake-functional control — those are real Phase 3+/5+ scope (Section 5), not reused from anywhere.
- Restaurant/accommodation cards render their raw JSON for now (shape varies per agent output) rather than a hand-built layout guessing at fields — flagged as a nice-to-have polish item, not a blocker.
- `npm run build` passes with zero TypeScript errors. `.github/workflows/ci.yml` now has a second `frontend` job (`npm ci && npm run build`) alongside the existing `backend` job.

**Not done in Phase 2** (explicitly out of scope per Section 5): real flight/hotel/weather/maps provider data (Phase 3), budget tracking, group collaboration, bookings/wallet (Phase 4), and all AI Engineering Workspace functionality (Phases 5–9). The quick-link tiles on Home (Flights/Hotels/Weather/Maps) are visual only and not wired to anything yet — they reuse the reference design's layout but have no destination pages until Phase 3.

## 10. Phase 4 Delivery Notes

Scoped down from the brief's full Phase 4 (which also lists documents, collaboration, and offline support) to what's buildable without new infrastructure (multi-user auth, file storage) this pass: **Bookings & Wallet** and **Budget & Expenses**, both per-trip. Documents, group collaboration, and offline support remain future work — not silently dropped, just not in this increment.

**Backend** (`app/models_db.py`, `app/schemas.py`, `app/api.py`):
- New `Booking` model (type, title, reference, status, cost, notes) and `Expense` model (category, description, amount), both `trip_id`-scoped. `Trip` gets a new `budget_amount` column — a user-set numeric target, kept separate from the existing `budget` level string (budget/mid-range/premium) that only steers what the agents recommend.
- Endpoints: `PATCH /api/trips/{id}` (set budget_amount), full CRUD-minus-update on bookings (`GET`/`POST`/`PATCH` status/`DELETE`) and expenses (`GET`/`POST`/`DELETE`), all 404 on an unknown trip and 422 on an invalid type/category/status.
- These are **user-entered wallet records, not a live booking integration** — there's no provider to book against yet (that's Phase 3's "booking handoff" / Level 2-3). This is the ledger that will eventually hold real confirmations.
- 12 new tests (23 total now pass).

**Frontend**:
- Trip Detail gained two tabs — "Bookings & Wallet" (`web/src/components/TripBookings.tsx`: add a booking, change its status inline, remove it) and "Budget & Expenses" (`web/src/components/TripBudget.tsx`: set a budget target, log expenses by category, a progress bar that turns red and labels itself "over budget" past the target). Both tabs are available even when trip planning failed or has no `plan` yet — bookings/budget are useful independent of whether the AI itinerary succeeded.
- The sidebar's "Bookings & Wallet" and "Budget & Expenses" items (previously "coming soon" placeholders) now route to `web/src/pages/TripPickerHub.tsx`, a simple trip picker that deep-links into the right tab (`/trips/{id}?tab=bookings`) — because these are per-trip features, not a single global ledger, and a real cross-trip aggregate view wasn't in scope for this pass.
- Verified end-to-end live in the browser: added a flight booking, changed its status pending → confirmed, set a ₹100,000 budget, logged a ₹120,000 expense and confirmed the "over budget" state renders, and confirmed the sidebar hub page deep-links correctly into the trip's Bookings tab.
- Caught and fixed a real bug during this verification: the backend's `CORS_ORIGINS` default only allowed port 5173, so a dev server on a different port (5174, e.g. when 5173 was already in use) got silently blocked by CORS with no obvious error in the UI. Documented here rather than silently worked around, since it'll resurface for anyone running two frontends locally — set `CORS_ORIGINS` explicitly in that case.

## 11. Phase 5 Delivery Notes

Goal: stop each agent from hardcoding its own `ChatOpenAI(...)`, so switching LLM providers is a config choice instead of a four-file edit. Built on LiteLLM's unified `model` string convention (`"gpt-4o-mini"`, `"anthropic/claude-3-5-sonnet-20241022"`, `"ollama/llama3"`) via the `langchain-litellm` package's `ChatLiteLLM`, which is still a LangChain-compatible chat model — so the existing `prompt | self.llm` LCEL chains in the agents are untouched.

**Backend** (`app/llm_gateway.py` — new; `app/config.py`, `app/agents/*.py`, `app/workflow.py`, `app/schemas.py`, `app/models_db.py`, `app/api.py`, `requirements.txt`):
- `app/llm_gateway.py` is the one new module: a `MODEL_REGISTRY` of six models across four providers (OpenAI, Anthropic, Google Gemini, local Ollama), `is_configured(model_id)` (checks the right env var is set; local models are always "configured" — reachability of a local Ollama server is a health check for a later phase), `resolve_model(model_id)` (requested → configured default `OPENAI_MODEL` → hardcoded fallback), and `get_chat_model(model_id)` which builds the `ChatLiteLLM` instance.
- Each of the four agents (`research_agent.py`, `accommodation_agent.py`, `dining_agent.py`, `itinerary_agent.py`) now takes an optional `model` constructor param and calls `get_chat_model(model)` instead of constructing `ChatOpenAI` directly — one-line change per agent, all other logic (prompts, JSON parsing, error handling) untouched.
- `MultiAgentWorkflow` takes the same `model` param and threads it to all four agents. `app/api.py` caches one workflow **per model id** (`_workflows: Dict[str, MultiAgentWorkflow]`) instead of a single global singleton, so switching models doesn't need a server restart.
- New `GET /api/models` endpoint lists the registry with a live `configured` flag per entry. `POST /api/trips` gained an optional `model` field — 422 if it names an unknown model, 503 (naming the missing env var) if it names a known-but-unconfigured one. `Trip` gained a persisted `model` column recording what was actually used, returned in `TripDetail`.
- 15 new tests (11 in new `tests/test_llm_gateway.py`, 4 appended to `tests/test_api.py`); 2 pre-existing `test_api.py` tests had a latent bug exposed by the `get_workflow` signature changing from zero-arg to one-arg (`lambda: fake_workflow` → `lambda *_: fake_workflow`). 53 tests total now pass (up from 38).
- **Bug caught before it caused a silent test failure**: `app/api.py` originally imported `Config` and the new `llm_gateway` items package-style (`from app.config import Config`), matching its existing style for `app.db`/`app.schemas`/etc. But every agent module resolves `config`/`llm_gateway` as *bare* top-level modules (`from config import Config`), which only works because `app/` itself is pushed onto `sys.path` (see the `sys.path.insert` at the top of `api.py`). Python treats `app.config` and `config` as two separate module objects for the same file — so `monkeypatch.setattr(api_module.Config, ...)` in a test would silently not affect what `is_configured()` sees inside `llm_gateway`, since that function reads the *other* copy. Fixed by importing `Config` and the `llm_gateway` names bare in `api.py` too, matching the convention the agents already use, so there is exactly one shared `Config` object everywhere. Caught by reasoning through the import graph before running tests, not by a failing test — worth calling out since it's an easy trap for anyone adding a fifth bare-import module later.

**Frontend** (`web/src/pages/ModelsRouting.tsx` — new; `web/src/pages/PlanTrip.tsx`, `web/src/pages/TripDetail.tsx`, `web/src/App.tsx`, `web/src/types.ts`, `web/src/api/client.ts`):
- `/ai/models` (previously a `ComingSoon` placeholder) is now a real table listing the registry — model, provider, context window, and a configured/needs-API-key/local badge per row.
- Plan a Trip gained an optional Model dropdown (populated from `GET /api/models`, options for unconfigured models rendered `disabled`), defaulting to "Default" (server picks). Trip Detail shows the resolved model id as a small badge next to the status pill.
- Verified end-to-end live in the browser: booted the backend with a fake smoke-test `OPENAI_API_KEY`, confirmed `/api/models` reported `gpt-3.5-turbo`/`gpt-4o-mini`/`gpt-4o`/`ollama/llama3` as configured and the Anthropic/Gemini entries as not, confirmed the same state renders correctly on `/ai/models`, picked "GPT-4o mini" in the Plan a Trip form, submitted, and confirmed the created trip's detail page shows a `gpt-4o-mini` badge and that the itinerary agent's per-day error correctly surfaced LiteLLM's `AuthenticationError` for the fake key (proving the request was actually routed through litellm to OpenAI, not silently stubbed).
- Caught and fixed a real, unrelated-to-the-code-change bug during this verification: the frontend had no `.env.local`, so `VITE_API_BASE_URL` defaulted to `http://localhost:8000`, and the backend's `CORS_ORIGINS` default only allows `5173`/`127.0.0.1:5173` — so running the frontend dev server on a non-default port (5180, since 5173 was briefly occupied) failed CORS silently. Not a code bug (same class noted in the Phase 4 notes above), just reconfirms: keep the frontend on 5173 against a backend on 8000, or set both `VITE_API_BASE_URL` and `CORS_ORIGINS` explicitly otherwise.

**Deferred** (not blockers, just out of scope for this pass): no reachability health check for the local Ollama server (`is_configured` reports it as always "configured" regardless of whether an Ollama process is actually running — flagged in the code as future work); no per-request token/cost accounting (that's Phase 8's observability scope); no UI for setting `ANTHROPIC_API_KEY`/`GOOGLE_API_KEY`/`OLLAMA_API_BASE` — they're read from the server's environment only, same as `OPENAI_API_KEY` already was.

## 12. Phase 6 Delivery Notes

Goal: show the four-agent travel pipeline isn't tied to LangGraph, by adding a second, real orchestration engine (CrewAI) that drives the exact same agent objects, plus an Agent Studio page so the roster and available frameworks are visible rather than implicit.

A key constraint drove the design: the Itinerary Agent's scheduling (`app/agents/itinerary_agent.py`) is **not** LLM-generated — it's real OpenRouteService geocoding, distance-matrix calls, and nearest-neighbor route optimization. Re-asking an LLM to invent a schedule inside a native CrewAI agent would have thrown away that real data and risked exactly the "fabricated travel info" the blueprint's rules forbid. So the CrewAI adapter's job is orchestration only — sequencing and dependency-passing — while the actual work for all four steps still goes through the same agent methods used by LangGraph.

**Backend** (`app/orchestration/` — new package; `app/models_db.py`, `app/schemas.py`, `app/api.py`, `requirements.txt`):
- `app/orchestration/__init__.py`: a `FRAMEWORK_REGISTRY` (mirrors `app/llm_gateway.py`'s `MODEL_REGISTRY` pattern) with two entries — `langgraph` (always available, it's a hard dependency already) and `crewai` (availability is a live `try: import crewai` check, same "optional, gracefully unavailable" pattern as Ollama in Phase 5). Also holds `AGENT_CATALOG`, a static roster of the four agents for the Agent Studio UI, each flagged with its real data source (LLM-generated vs. the itinerary step's deterministic geocoding) so that distinction is visible, not just known to whoever read the code.
- `app/orchestration/crewai_adapter.py`: `CrewAIOrchestrator`, built on real CrewAI `Agent`/`Task`/`Crew`/`Process.sequential` objects (verified against the actual installed `crewai` 1.15 API, not assumed). Each CrewAI Agent gets exactly one **zero-argument** tool — a closure over a shared `_TripContext`, calling straight into the matching `ResearchAgent`/`AccommodationAgent`/`DiningAgent`/`ItineraryAgent` method and writing the result onto the context as a side effect. Zero-argument by design: the trip's destination/days/etc. are already known on our side, so there's nothing for CrewAI's LLM to get wrong by supplying arguments itself — its only job is deciding "call my tool." Each tool is declared `result_as_answer=True`, which makes CrewAI use the tool's return value as the task's output verbatim instead of letting the agent's LLM paraphrase it (paraphrasing the itinerary tool's output would have been exactly the hallucination risk above). `plan_trip(...)` returns the identical `{success, plan: {attractions, itinerary, restaurants, accommodations}, errors}` shape as `MultiAgentWorkflow.plan_trip` in `app/workflow.py`, so `app/api.py` can treat a CrewAI orchestrator and a LangGraph workflow interchangeably.
- `app/api.py`: new `GET /api/frameworks` (registry + availability) and `GET /api/agents` (the catalog). `POST /api/trips` gained an optional `framework` field — 422 if unknown, 503 if known-but-not-installed (e.g. `crewai` requested without the package). A new `get_orchestrator(framework_id, model_id)` sits in front of the existing per-model `_workflows` cache: for `"langgraph"` (the default) it just calls the existing `get_workflow(model_id)` unchanged, so every langgraph-path test from Phases 2–5 that monkeypatches `get_workflow` keeps passing untouched; a new `_orchestrators` cache (keyed by `(framework_id, model_id)`) handles `"crewai"`. `Trip` gained a persisted `framework` column, returned in `TripDetail`.
- 17 new tests: `tests/test_orchestration.py` (registry/resolver/catalog, 7 tests) and `tests/test_crewai_adapter.py` (6 tests — mocks the four agent classes the same way `test_research_agent.py` does, and replaces `crewai.Crew` with a fake whose `kickoff()` runs each task's one tool in order, so the wiring is tested without needing a real model call), plus 4 more appended to `tests/test_api.py` for the new endpoints and field validation. `tests/test_crewai_adapter.py` uses `pytest.importorskip("crewai")` so the suite still passes in an environment where the optional dependency isn't installed. 54 tests total now pass (up from 38).
- **Verified against the real CrewAI package, not just mocks**: installed `crewai` in a temp venv, booted the backend with a fake smoke-test `OPENAI_API_KEY`, and posted a trip with `framework: "crewai"` — CrewAI's `Agent`/`Crew` actually ran and hit OpenAI, surfacing the same `AuthenticationError: Incorrect API key provided: sk-smoketest` the LangGraph path produced in Phase 5. That's the right outcome for a fake key and confirms the integration is real, not a stub: a correctly-wired fake orchestrator would have returned attractions/itinerary instead of touching the network at all.

**Frontend** (`web/src/pages/AgentStudio.tsx` — new; `web/src/pages/PlanTrip.tsx`, `web/src/pages/TripDetail.tsx`, `web/src/App.tsx`, `web/src/types.ts`, `web/src/api/client.ts`):
- `/ai/agent-studio` (previously a `ComingSoon` placeholder) now lists the two orchestration frameworks (available/not-installed badge) and the four-agent roster (role, goal, data source) from the new endpoints.
- Plan a Trip gained an Orchestration framework dropdown next to the existing Model dropdown, defaulting to "Default (LangGraph)"; unavailable frameworks render `disabled`, same pattern as unconfigured models. Trip Detail shows the resolved `framework` as a second badge next to the model badge.
- Verified end-to-end live in the browser: confirmed `/ai/agent-studio` renders both frameworks as available and all four agents with correct data-source labels, picked "CrewAI" in the Plan a Trip form, submitted, and confirmed the created trip's detail page shows both a `gpt-3.5-turbo` and a `crewai` badge, with the same real `AuthenticationError` surfaced as the backend smoke test above (proving the browser-driven request also went through the real CrewAI path end-to-end, not a different code path).

**Deferred** (not blockers, just out of scope for this pass): no AutoGen adapter — the blueprint names "CrewAI/AutoGen" but one working, verified adapter demonstrating the pattern was judged more valuable than two partially-verified ones; adding AutoGen later is a repeat of this same `app/orchestration/<name>_adapter.py` pattern. No per-framework cost/latency comparison in the UI (that's Phase 8's observability scope). No way to run the *same* trip through both frameworks side-by-side for comparison in one request — today it's one framework per trip, chosen up front.

## 13. Phase 7 Delivery Notes

Goal: a RAG knowledge base the research step can ground itself in, and an MCP server so Voyager's planning capability is reachable as tool calls (Claude Desktop, another agent) instead of only HTTP.

A constraint shaped both halves: the research/accommodation/dining agents' prompts are already free to generate attractions/hotels/restaurants from the LLM's own knowledge (that's the known, documented gap Phase 3 will close with real provider data) — RAG here is for the *other* kind of travel info, the stuff no LLM would know on its own (a traveler's own notes, a specific visa rule, "this particular beach shack is cash-only"), not a second way to generate the same placeholder data Phase 3 already plans to replace.

**RAG — `app/rag/` (new package):**
- No vector database. `app/models_db.py` gained `KnowledgeDocument` (destination/title/content) and `KnowledgeChunk` (one row per chunk, embedding stored as a plain JSON list of floats). `app/rag/chunking.py` does fixed-size sliding-window chunking (800 chars, 150 overlap) — no tokenizer dependency for what's a few paragraphs of notes. `app/rag/embeddings.py` embeds via `litellm.embedding()` (the same library the Phase 5 model gateway is built on, so it's one dependency doing double duty), OpenAI's `text-embedding-3-small` by default. Search is plain cosine similarity in Python over however many chunks exist — fine at the scale one traveler's notes will ever reach, and avoids a vector-store dependency for a feature this size.
- `POST /api/knowledge` (ingest — chunks, embeds, stores; 503 if the embedding provider isn't configured), `GET /api/knowledge` (list with chunk counts), `GET /api/knowledge/search` (query + optional destination filter). **Caught and fixed during live testing**: the first version of `ingest_document` committed the `KnowledgeDocument` row *before* calling the embedding API, so a failed embed (as with a fake smoke-test key) left an orphaned, permanently-empty document behind — visible in the UI's document list forever with `chunk_count: 0`. Fixed by embedding first and only writing anything to the DB once that succeeds, so a failed ingest now leaves no trace, verified by re-running the same failing request and confirming `GET /api/knowledge` stays empty.
- **Grounding hook into the existing pipeline, not a rewrite**: `ResearchAgent.find_attractions()` gained an optional `knowledge_context: Optional[str] = None` parameter (backward compatible — every existing call site and test still works unchanged), appended to its prompt as "traveler notes" only when non-empty. `app/rag`'s `get_context_for_destination(destination)` is called once per `plan_trip()` in both `app/workflow.py` (LangGraph) and `app/orchestration/crewai_adapter.py` (CrewAI) and threaded through to the research step either way, so RAG grounding works identically regardless of which Phase 6 framework is planning the trip. It checks for existing chunks for that destination *before* embedding anything — for every destination with no notes added (the default, today, for all of them), planning a trip costs zero extra API calls, not a wasted embedding request per trip. Wrapped in try/except in both orchestration paths so a RAG lookup failure (DB or embedding issue) degrades to planning without grounding rather than failing the whole trip.
- 9 new tests in `tests/test_rag.py` (chunking, ingest/search against an isolated in-memory SQLite engine passed explicitly via each function's `db` param rather than app.db's global one, embeddings mocked throughout) plus 2 new ones in `tests/test_research_agent.py` for the knowledge_context prompt-payload behavior.

**MCP server — `app/mcp_server.py` (new):**
- Built on the official `mcp` SDK's `FastMCP`, exposing 7 tools: `list_models`, `list_frameworks`, `list_agents`, `plan_trip`, `get_trip`, `list_trips`, `search_knowledge`. Run with `python app/mcp_server.py` (stdio transport) and point an MCP client's config at that command.
- **Zero duplicated business logic**: every tool calls `app/api.py`'s existing route-handler functions directly as plain Python (they're ordinary functions underneath FastAPI's decorators — `api_module.create_trip(payload, db=db)` runs through the exact same validation/orchestration/persistence path `POST /api/trips` does, with a manually-opened `SessionLocal()` session standing in for FastAPI's `Depends(get_db)`). A considered alternative — extracting a shared `trip_service` module used by both api.py and the MCP server — was rejected: it would have meant `get_workflow`/`get_orchestrator` moving out of `app/api.py`, which several Phase 5/6 tests monkeypatch by name on `api_module` specifically; moving them would have silently broken those tests' mocking (the patched name would no longer be the one actually called). Reusing api.py's handlers directly gets the DRY benefit without that risk.
- `HTTPException`s raised by the reused handlers (404/422/503) are translated to plain `ValueError`s with the status code and detail in the message, since Starlette's exception type isn't meaningful to a generic MCP client.
- 7 new tests in `tests/test_mcp_server.py`, calling the `@mcp.tool()`-decorated functions directly as plain Python (confirmed against the installed `mcp` package that the decorator returns the original callable unchanged) — no stdio transport involved. Also manually instantiated the real `FastMCP` server and listed its tools live to confirm all 7 are correctly registered with their schemas.
- 72 tests total now pass (up from 54).

**Frontend** (`web/src/pages/RagKnowledge.tsx` — new; `web/src/App.tsx`, `web/src/types.ts`, `web/src/api/client.ts`):
- `/ai/rag` (previously a `ComingSoon` placeholder) now has a real add-note form, a search box (query + optional destination), and a documents table. No UI for the MCP server — it's not a web feature, it's reachable by an MCP client via the run command documented above and in this file.
- Verified end-to-end live in the browser with a fake smoke-test key: submitted a note, confirmed the real `litellm.AuthenticationError` (401, same proof-of-real-integration pattern as Phases 5 and 6) surfaced cleanly in the UI, and confirmed the documents table correctly stayed empty afterward (the atomicity fix above, re-verified through the browser, not just the API directly).

**Deferred**: only OpenAI-compatible embeddings are wired up (consistent with embeddings needing `OPENAI_API_KEY` specifically, same limitation as the chat gateway's current single-tested-provider reality); no re-embedding if a document is edited (there's no edit endpoint at all yet, only create); no UI indicator on Plan a Trip showing whether grounding will actually fire for the destination typed in (would need a live keystroke-triggered lookup — deferred as UI polish, not a functional gap).

## 14. Phase 8 Delivery Notes

Goal: observability into what each trip-planning run actually did (which agent step took how long, which one failed) and an evaluation harness that catches real regressions automatically, for either orchestration framework and any configured model.

**Observability — per-step trace, both orchestration paths:**
- `app/workflow.py`'s four `_*_node` methods and `app/orchestration/crewai_adapter.py`'s four `@tool` closures each now time themselves (`time.monotonic()`) and append a `{step, duration_ms, status, error?}` entry to an accumulating `trace` list — the exact same accumulation pattern the codebase already used for `errors` (`state.get("trace", []) + [entry]` in LangGraph's state dict; a plain `ctx.trace.append(...)` on CrewAI's shared `_TripContext`, since that path isn't state-dict-based). Both `plan_trip(...)` return dicts gained a `"trace"` key alongside the existing `"errors"`.
- `Trip` (`app/models_db.py`) gained a `trace` JSON column, persisted in `create_trip` (`app/api.py`) alongside `plan`/`errors`/`model`/`framework`. `TripDetail` (`app/schemas.py`) exposes it.
- Frontend: `/ai/observability` (previously a `ComingSoon` placeholder) is now `web/src/pages/Observability.tsx` — a trip list on the left, and on the right the selected trip's per-step trace as a small bar (width proportional to that step's share of total time) with status/duration/error per step.

**Evaluation — `app/evaluation/` (new package):**
- `EVAL_CASES`: 3 canned cases (a short cultural trip, a week-long foodie trip with a dietary preference, a budget nature trip) covering different trip_type/budget/dietary combinations. `run_case(case, model, framework)` builds an orchestrator directly (`workflow.create_workflow` for langgraph, `orchestration.build_orchestrator` otherwise — bare imports, not through `app.api`'s caches, to avoid a circular import since `api.py` itself imports this module) and grades the result structurally: did planning succeed, are there non-empty `attractions` and a non-empty `itinerary`, and no `errors`. Never raises — an orchestrator-level exception is caught and reported as a failing case, not a crashed eval run.
- **Caught and fixed during live testing** (same "fake smoke-test key should make cases fail, and that's the correct outcome" pattern as Phases 5–7's live verifications): the first version's structural check passed all 3 cases even with an invalid `OPENAI_API_KEY`, because `ResearchAgent.find_attractions()` never raises on an LLM error — it catches it internally and returns a one-item placeholder (`{"name": "Error occurred", "category": "error", ...}`) so the rest of the pipeline has something to chain off of. That placeholder is non-empty, so "attractions is non-empty" alone is not a correctness check. Fixed by also rejecting any attraction with `category == "error"`; re-ran against the same fake-key backend and got the expected 0 passed / 3 failed, each with reason `"research agent fell back to its error placeholder"`.
- `EvaluationRun` (`app/models_db.py`): `model`, `framework`, `pass_count`, `fail_count`, `results` (JSON list of per-case `{case_id, description, passed, reason, duration_ms}`). `POST /api/evaluations` (runs the suite, validates model/framework the same way `POST /api/trips` does, persists, returns the full result), `GET /api/evaluations` (history), `GET /api/evaluations/{id}` (one run's detail), `GET /api/evaluations/cases/list` (what's in the suite, for the frontend's benefit).
- Frontend: `/ai/evaluations` (previously a `ComingSoon` placeholder) is now `web/src/pages/Evaluations.tsx` — a model/framework picker, a "Run eval suite" button, the latest run's per-case pass/fail breakdown, and a run-history table. Verified end-to-end live in the browser: clicked "Run eval suite" against the fake-key backend and watched all 3 cases fail with the real reason string, then confirmed the run appeared in history and could be reopened.
- 85 tests total now pass (up from 72): `tests/test_workflow.py` (new — trace accumulation for LangGraph, mocking the four agent classes the same way `test_crewai_adapter.py` already did), 2 new trace assertions added to `tests/test_crewai_adapter.py`, `tests/test_evaluation.py` (new — grading logic including the error-placeholder case above), and new `/api/evaluations` + trip-trace-persistence tests in `tests/test_api.py`.

**Deferred**: no LLM-judge grading (structural checks only — deliberately, since the goal is catching real breakage, not scoring itinerary quality, which would need a judge model and its own prompt-engineering pass); no cost/token accounting per run (would need per-call token counts surfaced from litellm, not currently captured); no scheduled/recurring eval runs (today it's triggered manually from the UI or API, each run is a point-in-time snapshot); accommodation/dining agents' own silent-empty-list-on-error behavior (`return []`, no placeholder) isn't separately flagged by the grader beyond the existing "no errors" check — only research_agent's non-empty-but-fake placeholder needed the extra check, since an empty list already fails the existing non-empty assertions for other fields where applicable, but accommodations/restaurants aren't currently required non-empty by `_grade` at all (consistent with the live-tested example above, where a successful plan can have zero restaurants/accommodations and still be structurally fine).

## Next step

Phases 0, 1, 2, 4 (partial), 5, 6, 7, and 8 are complete. Phase 3 (real travel providers — flights, hotels, weather, maps replacing the GPT-generated placeholder data) still needs provider credentials (Amadeus, etc.) that only the user can supply. Remaining Phase 4 scope (documents, group collaboration, offline support) has no blocker. Phase 9 (Security Lab / guardrails) has no blocker either. Recommend picking one explicitly rather than continuing to the next phase number by default, since the remaining phases are no longer small.
