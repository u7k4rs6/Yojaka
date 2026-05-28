# Yojaka Backend — Claude Code Build Spec

> **For Claude Code.** This is a build specification, not a reference document. Read top to bottom and execute.
> **Target**: full Python 3.11 backend rebuild. External contracts (WS events, REST routes, settings keys) are frozen — the existing frontend depends on them.
> **Mode**: greenfield rebuild into `backend/` (assume empty). If a `backend/` exists, archive it to `backend_old/` before starting.

---

## 0. Read This First — Hard Rules

These are invariants. Violating any of them is a bug.

1. **No LLM call without budget reservation.** Every provider call is preceded by `SessionBudget.reserve()`; if `False`, raise `BudgetExhausted` and trigger `early_stop`.
2. **Append-only token ledger.** `token_events` rows are INSERT-only. Never UPDATE or DELETE. `SessionBudget` is the in-memory projection.
3. **Ordered streaming per `stream_id`.** Chunks for a given `stream_id` MUST arrive in generation order on the WS. Use one `asyncio.Queue` per WS client.
4. **Phase order is immutable per debater count.** Parallel execution only where both teams run the same role (e.g. Pro Closing ∥ Con Closing). Never parallelize Pro vs Con within different roles.
5. **Memory scope is explicit.** Every `MemoryManager.get_relevant()` call MUST pass `scope="universal"` or `scope="chat"`. No defaults.
6. **External contracts frozen.** WS event names, payload shapes, REST paths, and settings JSON keys in §12 are exact. Do not rename, restructure, or "improve" them.
7. **Lock order.** When acquiring multiple locks: `budget → context → stream`. Never reverse. Never nest beyond two.
8. **No `print()`.** All logging via `observability/runtime_diary.py` or stdlib `logging`. Diary writes are persisted; logging is stdout.
9. **Async all the way down.** SQLAlchemy 2.x async, `httpx.AsyncClient` for providers, `asyncio.gather` for parallel work. No sync DB or HTTP calls in request paths.
10. **One archetype = one module.** Each agent archetype lives in its own file under `agents/`. Shared logic in `agents/base.py`.

---

## 1. Tech Stack — Pinned

| Layer | Library | Version |
|-------|---------|---------|
| Runtime | Python | 3.11+ |
| API | FastAPI | ≥0.110 |
| ASGI server | Uvicorn | ≥0.27 |
| ORM | SQLAlchemy | 2.x async |
| Migrations | Alembic | ≥1.13 |
| DB driver (dev) | aiosqlite | latest |
| DB driver (prod) | asyncpg | latest |
| HTTP client | httpx | ≥0.27 |
| Validation | Pydantic | 2.x |
| Vector (dev) | faiss-cpu | latest |
| Vector (prod) | pgvector | latest |
| Cache (dev) | cachetools | latest |
| Cache (prod) | redis (asyncio) | ≥5 |
| Testing | pytest, pytest-asyncio, httpx | latest |

**Deployment switch**: `YOJAKA_DEPLOYMENT=dev|prod` env var picks SQLite+FAISS+in-memory vs Postgres+pgvector+Redis. All access goes through factories in `storage/database.py` and `memory/semantic.py`.

---

## 2. Build Order — Execute in This Sequence

Each step has a **checkpoint**: a command that must succeed before moving on. Do not skip ahead.

### Step 1 — Scaffold
- Create folder structure exactly as in §3.
- Write `pyproject.toml` with pinned deps.
- Write `.env.example` with all env vars listed in §11.
- Write `README.md` with run instructions.
- **Checkpoint**: `pip install -e .` succeeds.

### Step 2 — Config & Storage
- Implement `config.py` (Pydantic Settings, reads env).
- Implement `storage/models.py` (all SQLAlchemy ORM models from §5).
- Implement `storage/database.py` (engine factory: SQLite or Postgres based on `YOJAKA_DEPLOYMENT`).
- Initialize Alembic; generate the initial migration from models.
- **Checkpoint**: `alembic upgrade head` creates all tables on a fresh SQLite file.

### Step 3 — Repositories
- Implement every repository in `repositories/` per §6 signatures.
- All methods are `async`. All return Pydantic models, not ORM rows.
- **Checkpoint**: `pytest tests/unit/test_repositories.py` passes (write basic CRUD tests).

### Step 4 — Budget, Tokens, Cost
- Implement `budget/tokenizer.py`, `budget/cost_rates.py`, `budget/session_budget.py`, `budget/accountant.py` per §7.
- **Checkpoint**: `pytest tests/unit/test_budget.py` passes the acceptance tests in §7.

### Step 5 — Providers
- Implement `providers/base.py` (abstract `ProviderClient`).
- Implement each concrete provider in §8 (Google, Groq, OpenAI, Anthropic, OpenRouter, Moonshot, Mock).
- Implement `providers/router.py` (slot system + health cache).
- Implement `providers/utility_tier.py`.
- **Checkpoint**: `pytest tests/unit/test_providers.py` passes; Mock provider streams correctly; router falls over on simulated failures.

### Step 6 — Memory Layers
- Implement L1 `memory/context_window.py`, L2 `memory/semantic.py`, L3 `memory/experience.py`, L4 `memory/user_profile.py`.
- **Checkpoint**: `pytest tests/unit/test_memory.py` passes; smart selection ranks correctly.

### Step 7 — Events & Streaming
- Implement `events/bus.py` (internal pub/sub, asyncio-based).
- Implement `events/stream_manager.py` (WS fan-out, per-client bounded queues).
- **Checkpoint**: `pytest tests/unit/test_streaming.py` passes; verify ordering and slow-consumer disconnect.

### Step 8 — Agents
- Implement `agents/base.py` (`AgentExecutor`).
- Implement each archetype in §9, one file each.
- **Checkpoint**: `pytest tests/integration/test_agents.py` passes; each archetype produces a valid `Message` against Mock provider.

### Step 9 — Analytics
- Implement `analytics/` per §10.
- **Checkpoint**: `pytest tests/unit/test_analytics.py` passes; verify metric formulas against fixtures.

### Step 10 — Safety, Intent, Session Manager
- Implement `core/safety_guard.py`, `core/intent_router.py`, `core/session_manager.py`.
- **Checkpoint**: `pytest tests/integration/test_routing.py` passes.

### Step 11 — Orchestrator
- Implement `core/phase_scheduler.py` (PhaseGraphBuilder).
- Implement `core/orchestrator.py` (DebateOrchestrator).
- Implement `core/practice_controller.py`.
- **Checkpoint**: `pytest tests/integration/test_orchestrator.py` passes end-to-end Mock-provider debate.

### Step 12 — API Layer
- Implement every REST route in §12.2.
- Implement WS handler `/ws/debates/{session_id}` per §12.1.
- Implement `main.py` (FastAPI app factory).
- **Checkpoint**: `uvicorn main:app` starts; `curl /health` returns 200; manual WS test with Mock provider completes a debate.

### Step 13 — Observability
- Implement `observability/runtime_diary.py` (writes to DB) and `observability/metrics.py` (Prometheus exporters).
- Wire diary writes at every state transition listed in §13.
- **Checkpoint**: `GET /api/runtime-diary/recent` returns recent events; `/metrics` exposes Prometheus format.

### Step 14 — E2E Tests
- Write E2E tests in `tests/e2e/`: full AI vs AI debate, full practice mode, chat fallback, safety block, budget exhaustion, provider failover.
- **Checkpoint**: `pytest tests/e2e/` all green.

### Step 15 — Smoke
- Run a full debate end-to-end with Mock provider through the WS.
- Verify the existing frontend (untouched) connects and renders correctly.

---

## 3. Folder Structure (Exact)

```
backend/
├── pyproject.toml
├── .env.example
├── README.md
├── alembic.ini
├── alembic/
│   └── versions/
├── main.py                          # FastAPI app factory
├── config.py                        # Pydantic Settings
│
├── api/
│   ├── __init__.py
│   ├── rest/
│   │   ├── __init__.py
│   │   ├── system.py                # /health, /api/models
│   │   ├── sessions.py              # /api/sessions/*
│   │   ├── settings.py              # /api/sessions/{id}/settings, /api/council-settings
│   │   ├── messages.py              # /api/sessions/{id}/messages, /debates
│   │   ├── analytics.py             # /api/sessions/{id}/analytics, /intelligence
│   │   ├── user_profile.py          # /api/user-debate-profile/*
│   │   └── observability.py         # /api/runtime-diary
│   └── ws/
│       ├── __init__.py
│       └── debates.py               # /ws/debates/{session_id}
│
├── core/
│   ├── __init__.py
│   ├── orchestrator.py              # DebateOrchestrator
│   ├── phase_scheduler.py           # PhaseGraphBuilder, Phase dataclass
│   ├── intent_router.py             # IntentRouter
│   ├── safety_guard.py              # SafetyGuard
│   ├── session_manager.py           # SessionManager
│   └── practice_controller.py       # PracticeController
│
├── agents/
│   ├── __init__.py
│   ├── base.py                      # AgentExecutor
│   ├── lead_advocate.py
│   ├── rebuttal_critic.py
│   ├── evidence_researcher.py
│   ├── cross_examiner.py
│   ├── judge.py
│   ├── judge_assistant.py
│   ├── council_assistant.py
│   ├── practice_debater.py
│   └── debate_trainer.py
│
├── providers/
│   ├── __init__.py
│   ├── base.py                      # ProviderClient ABC
│   ├── router.py                    # ProviderRouter + slot system
│   ├── utility_tier.py              # Cheap yes/no calls
│   ├── health_cache.py              # TTL cache (15m/2m/6h)
│   ├── google.py
│   ├── groq.py
│   ├── openai.py
│   ├── anthropic.py
│   ├── openrouter.py
│   ├── moonshot.py
│   └── mock.py
│
├── memory/
│   ├── __init__.py
│   ├── manager.py                   # MemoryManager (facade)
│   ├── context_window.py            # L1
│   ├── semantic.py                  # L2 (FAISS or pgvector)
│   ├── experience.py                # L3
│   └── user_profile.py              # L4
│
├── budget/
│   ├── __init__.py
│   ├── tokenizer.py                 # estimate_tokens, count_tokens
│   ├── session_budget.py            # SessionBudget
│   ├── accountant.py                # TokenAccountant
│   └── cost_rates.py                # CostRate lookup + local fallback table
│
├── analytics/
│   ├── __init__.py
│   ├── engine.py                    # AnalyticsEngine (facade)
│   ├── metrics.py                   # confidence, novelty, credibility, stance
│   ├── bayesian.py
│   ├── argument_graph.py
│   ├── delphi.py
│   ├── game_theory.py
│   └── moe.py
│
├── events/
│   ├── __init__.py
│   ├── bus.py                       # EventBus (internal pub/sub)
│   └── stream_manager.py            # StreamManager (WS fan-out)
│
├── repositories/
│   ├── __init__.py
│   ├── sessions_repo.py
│   ├── debates_repo.py
│   ├── messages_repo.py
│   ├── token_events_repo.py
│   ├── intelligence_repo.py
│   ├── agent_experience_repo.py
│   ├── user_profile_repo.py
│   ├── cost_rates_repo.py
│   └── runtime_diary_repo.py
│
├── storage/
│   ├── __init__.py
│   ├── database.py                  # Engine factory (sqlite | postgres)
│   └── models.py                    # All SQLAlchemy ORM models
│
├── prompts/
│   ├── __init__.py
│   ├── archetypes/                  # One file per archetype
│   │   ├── lead_advocate.py
│   │   ├── rebuttal_critic.py
│   │   ├── evidence_researcher.py
│   │   ├── cross_examiner.py
│   │   ├── judge.py
│   │   ├── judge_assistant.py
│   │   ├── council_assistant.py
│   │   ├── practice_debater.py
│   │   └── debate_trainer.py
│   ├── phases/
│   │   ├── constructive.py
│   │   ├── cross_exam.py
│   │   ├── evidence.py
│   │   ├── discussion.py
│   │   ├── rebuttal.py
│   │   ├── closing.py
│   │   └── judgment.py
│   └── safety/
│       └── classifier.py
│
├── observability/
│   ├── __init__.py
│   ├── runtime_diary.py
│   └── metrics.py
│
└── tests/
    ├── __init__.py
    ├── conftest.py                  # Pytest fixtures (mock DB, mock provider)
    ├── unit/
    │   ├── test_budget.py
    │   ├── test_providers.py
    │   ├── test_memory.py
    │   ├── test_analytics.py
    │   ├── test_streaming.py
    │   └── test_repositories.py
    ├── integration/
    │   ├── test_agents.py
    │   ├── test_orchestrator.py
    │   └── test_routing.py
    └── e2e/
        ├── test_ai_vs_ai.py
        ├── test_practice.py
        ├── test_chat.py
        ├── test_safety.py
        ├── test_budget_exhaustion.py
        └── test_provider_failover.py
```

---

## 4. Pydantic Domain Models (Single Source of Truth)

Implement in `storage/models.py` as ORM, but expose Pydantic equivalents in `core/schemas.py` for the API layer. Below are the Pydantic shapes — ORM mirrors them.

```python
# core/schemas.py
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field

# ─── Enums ──────────────────────────────────────────────────────────────────

class SessionMode(str, Enum):
    AI_VS_AI = "ai_vs_ai"
    AI_VS_HUMAN = "ai_vs_human"
    CHAT = "chat"

class DebateStatus(str, Enum):
    PREPARING = "preparing"
    ACTIVE = "active"
    JUDGING = "judging"
    COMPLETED = "completed"
    EARLY_STOPPED = "early_stopped"

class Team(str, Enum):
    PRO = "pro"
    CON = "con"
    NEUTRAL = "neutral"

class Archetype(str, Enum):
    LEAD_ADVOCATE = "lead_advocate"
    REBUTTAL_CRITIC = "rebuttal_critic"
    EVIDENCE_RESEARCHER = "evidence_researcher"
    CROSS_EXAMINER = "cross_examiner"
    JUDGE = "judge"
    JUDGE_ASSISTANT = "judge_assistant"
    COUNCIL_ASSISTANT = "council_assistant"
    PRACTICE_DEBATER = "practice_debater"
    DEBATE_TRAINER = "debate_trainer"

class IntelligenceType(str, Enum):
    CLAIM = "claim"
    EVIDENCE = "evidence"
    CHALLENGE = "challenge"
    MEMORY_SAVED = "memory_saved"
    LOW_CONFIDENCE = "low_confidence"
    JUDGE_SCORECARD = "judge_scorecard"
    POST_DEBATE_FEEDBACK = "post_debate_feedback"
    VERDICT_REVIEW = "verdict_review"

class Currency(str, Enum):
    USD = "USD"; CNY = "CNY"; HKD = "HKD"; EUR = "EUR"
    JPY = "JPY"; GBP = "GBP"; AUD = "AUD"; CAD = "CAD"; SGD = "SGD"

# ─── Embedded Settings (validated JSON) ─────────────────────────────────────

class AgentSettings(BaseModel):
    model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    response_length: Optional[Literal["Concise", "Normal", "Detailed"]] = None
    web_search: bool = False

class SessionSettings(BaseModel):
    # Debate Structure
    debaters_per_team: int = Field(1, ge=1, le=4)
    debate_rounds: int = Field(1, ge=1, le=6)
    discussion_messages_per_team: int = Field(2, ge=1, le=4)
    # Inference
    overall_model: Optional[str] = None
    temperature: float = Field(0.55, ge=0.0, le=1.0)
    max_tokens: int = Field(400, gt=0)
    response_length: Literal["Concise", "Normal", "Detailed"] = "Normal"
    context_window: int = Field(2, ge=0, le=6)
    # Behavior
    debate_tone: str = "Academic"
    language: str = "English"
    evidence_strictness: str = "Normal"
    fact_check_mode: bool = False
    judge_assistant_enabled: bool = False
    # Display
    auto_scroll: bool = True
    show_timestamps: bool = True
    show_token_count: bool = True
    show_money_cost: bool = True
    show_model_costs: bool = False
    show_every_message_cost_in_debate: bool = False
    cost_currency: Currency = Currency.USD
    # Memory
    use_experience: bool = True
    # Practice
    human_side: Literal["Auto", "Pro", "Con"] = "Auto"
    practice_flow: Literal["Free", "Structured"] = "Free"
    structured_rounds: int = Field(3, ge=1, le=12)
    use_user_profile: bool = True
    trainer_style: Literal["Coach", "Direct", "Gentle", "Examiner"] = "Coach"
    training_focus: Literal["Full Debate", "Rebuttal", "Evidence", "Clarity", "Cross-Examination"] = "Full Debate"
    opponent_difficulty: Literal["Adaptive", "Beginner", "Normal", "Hard"] = "Adaptive"
    # Judging
    judge_panel_size: Literal[1, 3, 5] = 1
    analytics_weight: float = Field(0.25, ge=0.0, le=0.75)
    allow_verdict_challenge: bool = True
    # Per-agent overrides (keyed by Archetype value)
    agent_settings: dict[str, AgentSettings] = Field(default_factory=dict)

class CouncilSettings(BaseModel):
    universal_experience: bool = True
    use_agent_identity_profiles: bool = True
    use_user_debate_profile: bool = True
    debate_intelligence_depth: Literal["Light", "Normal", "Deep"] = "Light"
    use_value_consequence_system: bool = False
    default_judge_mode: Literal["Debate Performance", "Truth-Seeking", "Hybrid"] = "Debate Performance"
    theme: Literal["Light", "Dark", "System"] = "System"

# ─── Core Entities ──────────────────────────────────────────────────────────

class Session(BaseModel):
    id: UUID
    name: str
    code: Optional[str]
    mode: SessionMode
    settings: SessionSettings
    active_debate_id: Optional[UUID]
    state: Literal["idle", "running", "archived"] = "idle"
    created_at: datetime
    updated_at: datetime

class AgentAssignment(BaseModel):
    team: Team
    archetype: Archetype
    slot: Literal[0, 1, 2]
    model: Optional[str]
    settings: AgentSettings = AgentSettings()
    state: Literal["idle", "queued", "streaming", "completed"] = "idle"

class Debate(BaseModel):
    id: UUID
    session_id: UUID
    topic: str
    pro_position: Optional[str]
    con_position: Optional[str]
    status: DebateStatus
    assignments: list[AgentAssignment] = []
    judge_config: dict = {}
    analytics: Optional[dict] = None
    cost_summary: Optional[dict] = None
    practice_state: Optional[dict] = None
    phase_graph: Optional[dict] = None
    created_at: datetime

class Message(BaseModel):
    id: UUID
    session_id: UUID
    debate_id: Optional[UUID]
    stream_id: Optional[str]
    role: str
    team: Optional[Team]
    content: str
    round: Optional[int]
    phase: Optional[str]
    model: Optional[str]
    temperature: Optional[float]
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    metadata: dict = {}
    created_at: datetime

class TokenEvent(BaseModel):
    id: UUID
    session_id: UUID
    debate_id: Optional[UUID]
    message_id: UUID
    agent_role: str
    model: str
    provider: str
    tokens_in: int = Field(ge=0)
    tokens_out: int = Field(ge=0)
    cost_usd: Decimal = Field(ge=0)
    currency: Currency = Currency.USD
    converted_cost: Decimal = Field(ge=0)
    timestamp: datetime

class IntelligenceRecord(BaseModel):
    id: UUID
    session_id: UUID
    debate_id: UUID
    type: IntelligenceType
    team: Team
    agent_role: str
    content: str
    confidence: float = Field(ge=0.0, le=1.0)
    scope: Literal["universal", "chat"]
    created_at: datetime

class AgentExperience(BaseModel):
    id: UUID
    agent_archetype: str
    lesson_type: Literal["debate_observation", "judge_scorecard", "user_feedback"]
    content: str
    confidence: Literal["low", "medium", "high"]
    use_count: int = 0
    last_used_at: Optional[datetime] = None
    source_debate_id: Optional[UUID] = None
    source_session_id: Optional[UUID] = None

class UserDebateProfile(BaseModel):
    user_id: str
    debates_completed: int = 0
    practice_debates_completed: int = 0
    wins: dict = Field(default_factory=lambda: {"pro": 0, "con": 0, "unclear": 0})
    side_history: dict = Field(default_factory=lambda: {"pro": 0, "con": 0, "auto": 0})
    strengths: list[str] = []     # max 18
    weaknesses: list[str] = []    # max 18
    trainer_notes: list[str] = [] # max 30
    style_tags: list[str] = []    # max 12
    last_updated_at: Optional[datetime] = None

class CostRate(BaseModel):
    model: str
    provider: str
    input_rate_per_1m: float = Field(ge=0)
    output_rate_per_1m: float = Field(ge=0)
    pricing_available: bool
    source: Literal["openrouter_api", "local_fallback", "unavailable"]
    fetched_at: Optional[datetime] = None
```

---

## 5. Database Schema

DDL is portable across SQLite and Postgres. Use `TEXT` for UUIDs in SQLite, `UUID` in Postgres (handled by SQLAlchemy dialect).

```sql
CREATE TABLE sessions (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    code            TEXT UNIQUE,
    mode            TEXT CHECK(mode IN ('ai_vs_ai','ai_vs_human','chat')),
    settings_json   TEXT NOT NULL,
    active_debate_id TEXT,
    state           TEXT DEFAULT 'idle',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE debates (
    id                  TEXT PRIMARY KEY,
    session_id          TEXT REFERENCES sessions(id) ON DELETE CASCADE,
    topic               TEXT NOT NULL,
    pro_position        TEXT,
    con_position        TEXT,
    status              TEXT CHECK(status IN ('preparing','active','judging','completed','early_stopped')),
    assignments_json    TEXT,
    judge_config_json   TEXT,
    analytics_json      TEXT,
    cost_summary_json   TEXT,
    practice_state_json TEXT,
    phase_graph_json    TEXT,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id              TEXT PRIMARY KEY,
    session_id      TEXT REFERENCES sessions(id) ON DELETE CASCADE,
    debate_id       TEXT REFERENCES debates(id) ON DELETE CASCADE,
    stream_id       TEXT,
    role            TEXT,
    team            TEXT CHECK(team IN ('pro','con','neutral')),
    content         TEXT,
    round           INTEGER,
    phase           TEXT,
    model           TEXT,
    temperature     REAL,
    tokens_in       INTEGER DEFAULT 0,
    tokens_out      INTEGER DEFAULT 0,
    cost_usd        REAL DEFAULT 0,
    metadata_json   TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE token_events (
    id               TEXT PRIMARY KEY,
    session_id       TEXT NOT NULL,
    debate_id        TEXT,
    message_id       TEXT NOT NULL,
    agent_role       TEXT,
    model            TEXT,
    provider         TEXT,
    tokens_in        INTEGER NOT NULL,
    tokens_out       INTEGER NOT NULL,
    cost_usd         REAL NOT NULL,
    currency         TEXT DEFAULT 'USD',
    converted_cost   REAL NOT NULL,
    timestamp        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE intelligence_records (
    id           TEXT PRIMARY KEY,
    session_id   TEXT NOT NULL,
    debate_id    TEXT NOT NULL,
    type         TEXT CHECK(type IN ('claim','evidence','challenge','memory_saved','low_confidence','judge_scorecard','post_debate_feedback','verdict_review')),
    team         TEXT CHECK(team IN ('pro','con','neutral')),
    agent_role   TEXT,
    content      TEXT,
    confidence   REAL,
    scope        TEXT CHECK(scope IN ('universal','chat')),
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE agent_experiences (
    id                  TEXT PRIMARY KEY,
    agent_archetype     TEXT NOT NULL,
    lesson_type         TEXT,
    content             TEXT,
    confidence          TEXT CHECK(confidence IN ('low','medium','high')),
    use_count           INTEGER DEFAULT 0,
    last_used_at        TIMESTAMP,
    source_debate_id    TEXT,
    source_session_id   TEXT,
    embedding_blob      BLOB
);

CREATE TABLE user_debate_profiles (
    user_id                       TEXT PRIMARY KEY,
    debates_completed             INTEGER DEFAULT 0,
    practice_debates_completed    INTEGER DEFAULT 0,
    wins_json                     TEXT,
    side_history_json             TEXT,
    strengths_json                TEXT,
    weaknesses_json               TEXT,
    trainer_notes_json            TEXT,
    style_tags_json               TEXT,
    last_updated_at               TIMESTAMP
);

CREATE TABLE cost_rates (
    model              TEXT PRIMARY KEY,
    provider           TEXT,
    input_rate_per_1m  REAL,
    output_rate_per_1m REAL,
    pricing_available  INTEGER,
    source             TEXT,
    fetched_at         TIMESTAMP
);

CREATE TABLE council_settings (
    id                  INTEGER PRIMARY KEY CHECK(id = 1),  -- singleton
    settings_json       TEXT NOT NULL
);

CREATE TABLE runtime_diary (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source      TEXT,
    event       TEXT,
    detail      TEXT,
    session_id  TEXT,
    timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_messages_debate           ON messages(debate_id);
CREATE INDEX idx_messages_session          ON messages(session_id);
CREATE INDEX idx_messages_stream           ON messages(stream_id);
CREATE INDEX idx_intelligence_debate       ON intelligence_records(debate_id);
CREATE INDEX idx_intelligence_type         ON intelligence_records(type, agent_role);
CREATE INDEX idx_token_events_session      ON token_events(session_id);
CREATE INDEX idx_token_events_debate       ON token_events(debate_id);
CREATE INDEX idx_agent_exp_archetype       ON agent_experiences(agent_archetype);
CREATE INDEX idx_agent_exp_used            ON agent_experiences(last_used_at);
CREATE INDEX idx_runtime_session           ON runtime_diary(session_id);
CREATE INDEX idx_runtime_event             ON runtime_diary(event);
CREATE INDEX idx_debates_session_status    ON debates(session_id, status);
```

---

## 6. Repository Signatures

All async. All return Pydantic models. All in `repositories/`.

```python
# repositories/sessions_repo.py
class SessionsRepo:
    async def create(self, name: str, mode: SessionMode, settings: SessionSettings) -> Session: ...
    async def get(self, session_id: UUID) -> Optional[Session]: ...
    async def list_all(self) -> list[Session]: ...
    async def rename(self, session_id: UUID, name: str) -> Session: ...
    async def delete(self, session_id: UUID) -> None: ...
    async def delete_all(self) -> int: ...
    async def update_settings(self, session_id: UUID, settings: SessionSettings) -> Session: ...
    async def set_active_debate(self, session_id: UUID, debate_id: Optional[UUID]) -> None: ...
    async def clear_history(self, session_id: UUID) -> None: ...   # marks messages/debates hidden
    async def clear_memory(self, session_id: UUID) -> None: ...    # hard delete cascade

# repositories/debates_repo.py
class DebatesRepo:
    async def create(self, session_id: UUID, topic: str, mode: SessionMode, assignments: list[AgentAssignment]) -> Debate: ...
    async def get(self, debate_id: UUID) -> Optional[Debate]: ...
    async def list_for_session(self, session_id: UUID, include_hidden: bool = False) -> list[Debate]: ...
    async def update_status(self, debate_id: UUID, status: DebateStatus) -> None: ...
    async def attach_analytics(self, debate_id: UUID, analytics: dict) -> None: ...
    async def attach_cost_summary(self, debate_id: UUID, summary: dict) -> None: ...
    async def attach_phase_graph(self, debate_id: UUID, graph: dict) -> None: ...
    async def rename(self, debate_id: UUID, topic: str) -> Debate: ...
    async def hide(self, debate_id: UUID) -> None: ...

# repositories/messages_repo.py
class MessagesRepo:
    async def insert(self, msg: Message) -> Message: ...
    async def list_for_session(self, session_id: UUID) -> list[Message]: ...
    async def list_for_debate(self, debate_id: UUID) -> list[Message]: ...
    async def get(self, message_id: UUID) -> Optional[Message]: ...

# repositories/token_events_repo.py
class TokenEventsRepo:
    async def insert(self, event: TokenEvent) -> None: ...     # append-only
    async def sum_for_session(self, session_id: UUID) -> tuple[int, int, Decimal]: ...   # (in, out, cost)
    async def sum_for_debate(self, debate_id: UUID) -> tuple[int, int, Decimal]: ...

# repositories/intelligence_repo.py
class IntelligenceRepo:
    async def insert(self, record: IntelligenceRecord) -> IntelligenceRecord: ...
    async def list_for_debate(self, debate_id: UUID, team: Optional[Team] = None) -> list[IntelligenceRecord]: ...
    async def list_for_session(self, session_id: UUID) -> list[IntelligenceRecord]: ...

# repositories/agent_experience_repo.py
class AgentExperienceRepo:
    async def upsert(self, exp: AgentExperience) -> AgentExperience: ...
    async def fetch_by_archetype(self, archetype: str, limit: int = 5) -> list[AgentExperience]: ...
    async def fetch_session_scoped(self, debate_id: UUID, archetype: str, limit: int = 5) -> list[IntelligenceRecord]: ...
    async def bump_usage(self, experience_id: UUID) -> None: ...
    async def reset_all(self) -> int: ...

# repositories/user_profile_repo.py
class UserProfileRepo:
    async def get(self, user_id: str = "default") -> UserDebateProfile: ...   # creates if missing
    async def update(self, profile: UserDebateProfile) -> UserDebateProfile: ...
    async def reset(self, user_id: str = "default") -> None: ...

# repositories/cost_rates_repo.py
class CostRatesRepo:
    async def get(self, model: str) -> Optional[CostRate]: ...
    async def upsert(self, rate: CostRate) -> None: ...
    async def list_all(self) -> list[CostRate]: ...

# repositories/runtime_diary_repo.py
class RuntimeDiaryRepo:
    async def log(self, source: str, event: str, detail: str, session_id: Optional[UUID] = None) -> None: ...
    async def recent(self, limit: int = 100) -> list[dict]: ...
```

---

## 7. Budget Subsystem — Signatures + Acceptance Tests

### 7.1 Signatures

```python
# budget/tokenizer.py
def estimate_tokens(text: str) -> int:
    """CJK=1.6 chars/tok, Latin=1.3 chars/tok, min 1."""

def count_tokens(text: str) -> int:
    """Same formula as estimate; used for actual output counting."""

def count_cjk(text: str) -> int: ...

# budget/cost_rates.py
LOCAL_FALLBACK_RATES: dict[str, CostRate] = {
    # Pre-populated for every model in §8.
    # source = "local_fallback"
}

async def fetch_openrouter_pricing(client: httpx.AsyncClient) -> dict[str, CostRate]:
    """Fetches live OpenRouter pricing. Returns empty dict on failure."""

# budget/session_budget.py
class SessionBudget:
    def __init__(self, session_id: UUID, cap: int):
        self.session_id = session_id
        self.cap = cap
        self.consumed = 0
        self.reserved = 0
        self._lock = asyncio.Lock()

    @property
    def status(self) -> Literal["healthy", "warning", "exhausted"]:
        used = self.consumed + self.reserved
        if used >= self.cap: return "exhausted"
        if used >= self.cap * 0.9: return "warning"
        return "healthy"

    async def reserve(self, amount: int) -> bool: ...
    async def charge(self, actual_out: int, reserved: int) -> None: ...
    async def hydrate_from_ledger(self, repo: TokenEventsRepo) -> None:
        """Project consumed from token_events on session load."""

# budget/accountant.py
class TokenAccountant:
    def __init__(self, rates_repo: CostRatesRepo, events_repo: TokenEventsRepo): ...

    def estimate_tokens(self, text: str) -> int: ...
    def count_tokens(self, text: str) -> int: ...

    async def compute_cost(self, tokens_in: int, tokens_out: int, model: str) -> Decimal: ...
    async def convert_currency(self, usd: Decimal, currency: Currency) -> Decimal: ...

    async def record(
        self,
        *,
        session_id: UUID,
        debate_id: Optional[UUID],
        message_id: UUID,
        agent_role: str,
        model: str,
        provider: str,
        tokens_in: int,
        tokens_out: int,
        currency: Currency = Currency.USD,
    ) -> TokenEvent: ...
```

### 7.2 Acceptance Tests (write these in `tests/unit/test_budget.py`)

```python
@pytest.mark.asyncio
async def test_estimate_tokens_empty():
    assert estimate_tokens("") == 1

@pytest.mark.asyncio
async def test_estimate_tokens_cjk():
    assert estimate_tokens("你好世界") == 2     # 4 / 1.6 = 2.5 → floor → 2

@pytest.mark.asyncio
async def test_estimate_tokens_latin():
    assert estimate_tokens("Hello world") == 8  # 11 / 1.3 = 8.46 → floor → 8

@pytest.mark.asyncio
async def test_estimate_tokens_mixed():
    assert estimate_tokens("Hello 世界") == 5   # 5/1.3 + 2/1.6 ≈ 5.1 → 5

@pytest.mark.asyncio
async def test_reserve_succeeds_within_cap():
    b = SessionBudget(uuid4(), cap=1000)
    assert await b.reserve(500) is True
    assert b.reserved == 500

@pytest.mark.asyncio
async def test_reserve_fails_over_cap():
    b = SessionBudget(uuid4(), cap=1000)
    await b.reserve(900)
    assert await b.reserve(200) is False

@pytest.mark.asyncio
async def test_charge_reconciles_reservation():
    b = SessionBudget(uuid4(), cap=1000)
    await b.reserve(500)
    await b.charge(actual_out=300, reserved=500)
    assert b.reserved == 0
    assert b.consumed == 300

@pytest.mark.asyncio
async def test_budget_status_transitions():
    b = SessionBudget(uuid4(), cap=1000)
    assert b.status == "healthy"
    await b.reserve(900)
    assert b.status == "warning"
    await b.charge(actual_out=950, reserved=900)
    # consumed=950, reserved=0 → 95% → still warning
    await b.reserve(60)
    assert b.status == "exhausted"

@pytest.mark.asyncio
async def test_concurrent_reservations_no_overshoot():
    b = SessionBudget(uuid4(), cap=1000)
    results = await asyncio.gather(*[b.reserve(600) for _ in range(3)])
    assert sum(results) == 1  # only one succeeds
    assert b.reserved == 600
```

---

## 8. Providers

### 8.1 `ProviderClient` ABC (in `providers/base.py`)

```python
class ProviderClient(ABC):
    name: str
    available: bool

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[dict],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        """Yields text chunks. Raises ProviderError on failure."""

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        *,
        model: str,
        max_tokens: int = 100,
    ) -> str: ...

    @abstractmethod
    async def probe(self) -> bool:
        """Send a 4-token test; True if healthy."""
```

### 8.2 Models Per Provider

| Provider | Models | Context |
|----------|--------|---------|
| Google | `gemini-3.1-pro`, `gemini-3-flash`, `gemini-2.5-flash-lite`, `gemini-2.0-flash` | 128K |
| Groq | `llama-3.1-8b-instant`, `llama-3.3-70b-versatile` | 32K |
| OpenRouter | `openrouter-auto`, `llama-3.3-70b-or`, `claude-3.5-sonnet-or` | varies |
| OpenRouter Free | `deepseek-r1-free`, `qwq-32b-free`, `llama-3.1-8b-free`, `gemma-3-27b-free`, `qwen3-14b-free` | varies |
| Moonshot | `kimi-latest`, `kimi-k2-thinking`, `kimi-k2-turbo-preview`, `kimi-k2.5-vision`, `moonshot-v1-128k` | 128K |
| MiniMax | `minimax-m2.7` | 32K |
| Fireworks | `kimi-fw`, `llama-3.1-70b-fw` | varies |
| OpenAI | `gpt-4o`, `gpt-4o-mini` | 128K / 8K |
| Anthropic | `claude-opus-4-6`, `claude-sonnet-4-6`, `claude-haiku-4-5`, `claude-3.5-sonnet` | 200K |
| Mock | `mock-debate-model` | 32K |

### 8.3 Router & Slot System

```python
# providers/router.py
class ProviderRouter:
    def __init__(self, clients: dict[str, ProviderClient], health_cache: HealthCache): ...

    def resolve_model(self, assignment: AgentAssignment, council: CouncilSettings, user_primary: str) -> str:
        """
        Slot rules:
          Slot 0 (judge, judge_assistant, council_assistant, practice_debater, debate_trainer)
            → user_primary
          Slot 1 (Pro team)        → second available provider
          Slot 2 (Con team)        → third available provider
        Per-agent override (assignment.settings.model) always wins.
        """

    async def call(
        self,
        *,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        """
        Streams chunks. On RateLimitError: cache provider unhealthy 2min, failover.
        On AuthError: cache unhealthy 6hr, raise.
        On healthy probe: cache OK 15min.
        """

# providers/health_cache.py
class HealthCache:
    HEALTHY_TTL = 15 * 60
    SOFT_FAIL_TTL = 2 * 60
    HARD_FAIL_TTL = 6 * 60 * 60

    def get(self, provider: str) -> Optional[bool]: ...
    def set(self, provider: str, healthy: bool, ttl: int) -> None: ...

# providers/utility_tier.py
class UtilityTier:
    PRIORITY = [
        "llama-3.1-8b-instant",
        "gemini-2.5-flash-lite",
        # then any Groq model, then user_primary
    ]
    async def ask_yes_no(self, prompt: str, context: str = "") -> Literal["YES", "NO"]: ...
    async def complete(self, prompt: str, max_tokens: int = 120) -> str: ...
```

### 8.4 Acceptance

- Mock provider streams 5 chunks of fixed text in order.
- Router falls over: simulate Provider A raises RateLimitError → next call uses Provider B; Provider A is unhealthy in cache.
- AuthError caches 6h; subsequent calls skip that provider without retrying.

---

## 9. Agents

### 9.1 `AgentExecutor` Base (in `agents/base.py`)

```python
class AgentExecutor:
    def __init__(
        self,
        assignment: AgentAssignment,
        context_window: ContextWindow,
        memory_manager: MemoryManager,
        budget: SessionBudget,
        accountant: TokenAccountant,
        stream_manager: StreamManager,
        provider_router: ProviderRouter,
        intelligence_repo: IntelligenceRepo,
        diary: RuntimeDiaryRepo,
        debate: Debate,
        council: CouncilSettings,
    ): ...

    async def execute_turn(self, phase: Phase) -> Message:
        """
        Lifecycle (do not deviate):
          1. Retrieve memory (L1 + L3 if council.universal_experience, L2 own team)
          2. Build system prompt (role + experience injection)
          3. Build user prompt (phase-specific from prompts/phases/)
          4. estimate_in = estimate_tokens(system + history + user)
          5. await budget.reserve(estimate_in + assignment.max_tokens)
             → if False: raise BudgetExhausted
          6. stream = await provider_router.call(...)
          7. message = await stream_manager.stream_to_message(stream, assignment)
          8. actual_out = count_tokens(message.content)
          9. await budget.charge(actual_out, reserved=assignment.max_tokens)
         10. await accountant.record(...)   # writes TokenEvent
         11. context_window.push(message)
         12. asyncio.create_task(self._extract_intelligence(message))
         13. return message
        """

    async def _extract_intelligence(self, message: Message) -> None:
        """
        Sentence-split; tag claims/evidence/challenges via keyword detection.
        Insert IntelligenceRecord per finding.
        Mark low_confidence if uncertainty markers detected.
        """
```

### 9.2 Archetypes

Each archetype subclasses `AgentExecutor` only to provide:
- `system_prompt_template` (loaded from `prompts/archetypes/<name>.py`)
- Optional `_build_phase_prompt` override

Implement these (one file each):

| File | Purpose |
|------|---------|
| `agents/lead_advocate.py` | Build team's central case. Min debaters: 1. |
| `agents/rebuttal_critic.py` | Attack opposing strongest point. Min debaters: 2. |
| `agents/evidence_researcher.py` | Add evidence + uncertainty notes. Min debaters: 3. Supports web search. |
| `agents/cross_examiner.py` | Socratic pressure questions. Min debaters: 4. |
| `agents/judge.py` | Final verdict via Bayesian + analytics weighting. |
| `agents/judge_assistant.py` | Pre-judgment audit. Optional. |
| `agents/council_assistant.py` | Chat-mode Q&A with session context. |
| `agents/practice_debater.py` | AI opponent in practice mode. Difficulty-adaptive. |
| `agents/debate_trainer.py` | Post-practice coaching feedback. |

### 9.3 Acceptance

- Each archetype produces a `Message` with non-empty content against Mock provider.
- `_extract_intelligence` inserts ≥1 `claim` record per turn for advocates/critics.
- Streaming returns chunks in order; `message.content` equals `"".join(chunks)`.

---

## 10. Analytics

### 10.1 Signatures

```python
# analytics/metrics.py
def compute_confidence(text: str, base: float = 0.5) -> float:
    """base + Σ(certainty_markers) * 0.05, clamped [0.2, 1.25]."""

def compute_novelty(text: str, prior_texts: list[str]) -> float:
    """1 - jaccard(words(text), words(' '.join(prior_texts)))."""

def detect_stance(text: str, role: Optional[Archetype] = None) -> Literal["Support", "Oppose", "Mixed"]: ...
def detect_evidence(text: str) -> bool: ...
def detect_rebuttal(text: str) -> bool: ...

CERTAINTY_MARKERS = {"definitely", "certainly", "proven", "must", "always"}
SUPPORT_MARKERS   = {"support", "agree", "benefit", "advantage"}
OPPOSE_MARKERS    = {"oppose", "disagree", "flaw", "risk", "however"}
EVIDENCE_MARKERS  = {"because", "data", "study", "research", "observed"}
REBUTTAL_MARKERS  = {"however", "flaw", "counter", "unless"}

ROLE_WEIGHTS = {
    Archetype.LEAD_ADVOCATE: 1.0,
    Archetype.REBUTTAL_CRITIC: 1.1,
    Archetype.EVIDENCE_RESEARCHER: 1.15,
    Archetype.CROSS_EXAMINER: 1.05,
}

# analytics/engine.py
class AnalyticsEngine:
    async def analyze_turn(self, message: Message, prior_turns: list[Message]) -> TurnMetrics: ...
    async def update_bayesian(self, turn_metrics: TurnMetrics) -> None: ...
    async def build_argument_graph(self, debate_id: UUID) -> dict: ...
    async def compute_delphi(self) -> float: ...
    async def compute_nash_pressure(self) -> float: ...
    async def finalize(self, debate_id: UUID) -> dict:
        """Returns the full analytics payload (see §10.2)."""

class TurnMetrics(BaseModel):
    confidence: float
    novelty: float
    credibility: float
    stance: Literal["Support", "Oppose", "Mixed"]
    has_evidence: bool
    is_rebuttal: bool
    weighted_score: float
```

### 10.2 Analytics Payload Shape (must match this exactly)

```json
{
  "debate_id": "uuid",
  "rounds": [
    {
      "round_number": 1,
      "turns": [
        {
          "speaker": "lead_advocate",
          "team": "pro",
          "metrics": {
            "confidence": 0.85,
            "novelty": 0.72,
            "credibility": 1.1,
            "stance": "Support",
            "has_evidence": true,
            "is_rebuttal": false,
            "weighted_score": 0.6732
          }
        }
      ],
      "ensemble_vote": "Support",
      "bayesian": {"support": 0.6, "oppose": 0.3, "mixed": 0.1},
      "delphi_variance": 0.15,
      "nash_pressure": 0.82
    }
  ],
  "argument_graph": {
    "nodes": [{"id": "claim_1", "text": "...", "speaker": "lead_advocate"}],
    "edges": [{"from": "claim_1", "to": "claim_2", "type": "attacks"}]
  },
  "strongest_claims": [{"id": "claim_1", "score": 0.95}]
}
```

---

## 11. Environment Variables

```bash
# .env.example
YOJAKA_DEPLOYMENT=dev                 # dev | prod
DATABASE_URL=sqlite+aiosqlite:///./yojaka.db
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost/yojaka  # prod

SESSION_TOKEN_BUDGET=40000
MAX_AGENT_OUTPUT_TOKENS=400
CONTEXT_WINDOW_TURNS=6

# Provider keys (omit to disable a provider)
GOOGLE_API_KEY=
GROQ_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
OPENROUTER_API_KEY=
MOONSHOT_API_KEY=
MINIMAX_API_KEY=
FIREWORKS_API_KEY=

# Defaults
DEFAULT_MODEL=gemini-2.0-flash
ENABLE_MOCK_PROVIDER=true

# Production only
REDIS_URL=
PROMETHEUS_ENABLED=false
```

---

## 12. External Contracts (FROZEN — do not change)

### 12.1 WebSocket — `WS /ws/debates/{session_id}`

**Client → Server**:

| Event | Payload |
|-------|---------|
| `start_debate` | `{"topic": str, "model"?: str}` |
| `start_interaction` | `{"topic": str, "model"?: str, "practice_side"?: "Auto"\|"Pro"\|"Con"}` |
| `end_practice_debate` | `{"model"?: str}` |

**Server → Client**:

| Event | Payload |
|-------|---------|
| `debate_started` | `{"debate": Debate, "topic": str, "positions": dict, "selected_model": str, "assignments": list, "judge": dict, "active_debates": int}` |
| `team_preparation_started` | `{"debate_id": str, "message": str}` |
| `team_preparation_completed` | `{"debate_id": str, "message": str}` |
| `message_started` | `{"stream_id": str, "message": Message (empty content), "round": int}` |
| `message_chunk` | `{"stream_id": str, "delta": str}` |
| `message_completed` | `{"stream_id": str, "message": Message, "cost_summary": dict}` |
| `analysis_updated` | `{"round": int, "analysis": dict}` |
| `early_stop` | `{"reason": "consensus"\|"budget_exhausted", "tokens_used": int, "debate_id": str}` |
| `debate_completed` | `{"debate_id": str, "judge_summary": dict, "active_debates": int, "cost_summary": dict}` |
| `practice_started` | `{"debate": Debate, "state": dict, "selected_model": str}` |
| `practice_state_updated` | `{"state": dict}` (set `state.ending = true` when finalizing) |
| `practice_completed` | `{"debate_id": str, "profile": UserDebateProfile, "cost_summary": dict}` |
| `interaction_started` | `{"mode": str, "debate": Debate, "selected_model": str}` |
| `interaction_completed` | `{"mode": str, "debate_id": str, "cost_summary": dict}` |
| `error` | `{"message": str}` |

### 12.2 REST

System:
- `GET /health` → `{"status": "ok", "db_path": str, "active_debates": int}`
- `GET /api/models` → `{"models": [...], "providers": [...], "mock_mode": bool}`

Sessions:
- `GET /api/sessions`
- `POST /api/sessions` body: `{name, mode, settings}`
- `DELETE /api/sessions`
- `PATCH /api/sessions/{id}` body: `{name}`
- `DELETE /api/sessions/{id}`
- `POST /api/sessions/{id}/clear-history`
- `POST /api/sessions/{id}/clear-memory`

Settings:
- `GET /api/sessions/{id}/settings`
- `PATCH /api/sessions/{id}/settings`
- `GET /api/council-settings`
- `PATCH /api/council-settings`
- `POST /api/council-settings/reset-agent-experience` body: `{"confirm": "RESET COUNCIL IDENTITIES"}`

Messages & debates:
- `GET /api/sessions/{id}/messages`
- `GET /api/sessions/{id}/debates`
- `PATCH /api/sessions/{id}/debates/{did}` body: `{topic}`
- `DELETE /api/sessions/{id}/debates/{did}`
- `GET /api/sessions/{id}/practice-state`

Analytics & intelligence:
- `GET /api/sessions/{id}/analytics`
- `GET /api/sessions/{id}/intelligence`
- `POST /api/sessions/{id}/debates/{did}/feedback` body: `{answers: [str, str, str]}`
- `POST /api/sessions/{id}/debates/{did}/verdict-review` body: `{action: "challenge"|"override", reason: str}`

Profile:
- `GET /api/user-debate-profile`
- `GET /api/user-debate-profile/overview`
- `POST /api/user-debate-profile/reset` body: `{"confirm": "RESET USER DEBATE PROFILE"}`
- `GET /api/ai-debater-experiences`

Observability:
- `POST /api/runtime-diary` body: `{source, event, detail, session_id?}`

---

## 13. Runtime Diary — Required Log Points

Every one of these MUST write a diary row:

| Source | Event | When |
|--------|-------|------|
| `backend terminal` | `startup` | App boot |
| `backend terminal` | `interaction_received` | Any WS message in |
| `backend terminal` | `intent_routed` | After IntentRouter decision |
| `backend terminal` | `safety_lock_routed` | Safety block fired |
| `backend terminal` | `safety_lock_classifier_fallback` | LLM safety classifier failed → regex used |
| `backend terminal` | `debate_started` | Orchestrator begins |
| `backend terminal` | `private_notebook_fallback` | Notebook LLM call failed → template used |
| `backend terminal` | `early_consensus` | Consensus check returned YES |
| `backend terminal` | `debate_completed` | Final verdict in |
| `backend terminal` | `debate_client_disconnected` | WS closed mid-debate |
| `backend terminal` | `debate_failed` | Orchestrator exception |
| `backend terminal` | `ws_handler_error` | WS layer exception |

---

## 14. Concurrency Rules (Critical)

1. **Lock acquisition order**: budget → context → stream. Never reverse.
2. **Parallel phases use `asyncio.gather(..., return_exceptions=True)`**. Inspect results; `BudgetExhausted` triggers `early_stop` for the whole debate, not just the failed branch.
3. **WS per-client queues bounded at 256**. Slow consumer = disconnect that client; other clients continue.
4. **No `time.sleep`**. Use `asyncio.sleep`.
5. **No nested `asyncio.Lock` acquisitions** within a single coroutine beyond the two-lock max.

---

## 15. Failure Modes — Required Handling

| Failure | Detection | Response |
|---------|-----------|----------|
| Provider rate-limit (429) | HTTP status | Cache unhealthy 2min; failover to next slot's provider |
| Provider auth error (401/403) | HTTP status | Cache unhealthy 6h; raise; agent emits `error` event |
| Provider stream disconnect | Generator raises | Save partial response with `metadata.partial=true`; continue debate |
| Notebook prep LLM failure | Try/except | Use deterministic notebook template; diary `private_notebook_fallback` |
| Consensus check LLM failure | UtilityTier raises | Skip consensus this phase; do not block |
| Budget exhausted | Reservation refused | Emit `early_stop`; current stream completes |
| WS client disconnect | Send raises | Orchestrator continues; messages persist; reconnect replays from DB |
| Orchestrator crash | Unhandled exception | Catch at boundary; debate.status = `early_stopped`; WS `error` |
| DB write failure | SQLAlchemy raises | Retry 3× exponential backoff; if persistent, abort with `error` |
| WS slow consumer | Queue > 256 | Disconnect that client only |

---

## 16. Self-Verification Checklist (run before claiming done)

```bash
# Step-by-step, do not skip
pip install -e .                                          # passes
alembic upgrade head                                      # creates all tables
pytest tests/unit/                                        # all green
pytest tests/integration/                                 # all green
pytest tests/e2e/                                         # all green

# Boot
uvicorn main:app --port 8000

# Smoke
curl http://localhost:8000/health                         # → {"status": "ok", ...}
curl http://localhost:8000/api/models                     # → models list
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"name":"smoke","mode":"ai_vs_ai","settings":{}}'   # → 201 + Session JSON

# WS test (write tests/smoke_ws.py)
python tests/smoke_ws.py                                  # completes Mock debate end-to-end
```

After all of the above pass, the existing frontend should connect to `ws://localhost:8000/ws/debates/{session_id}` and render a Mock-provider debate without modification.

---

## 17. Phase Configuration Matrix (for PhaseGraphBuilder)

| Debaters | Phases | Parallel Groups |
|----------|--------|-----------------|
| 1 | Constructive → Cross-exam → Discussion(N rounds) → Closing | Closing (Pro ∥ Con) |
| 2 | + Rebuttal Critic phases | + Rebuttal (Pro ∥ Con) |
| 3 | + Evidence Researcher phases | + Evidence (Pro ∥ Con) |
| 4 | + Cross-Examiner phases | + Cross-exam (Pro ∥ Con), Researcher Cross-exam (Pro ∥ Con) |

Phase dataclass:

```python
@dataclass
class Phase:
    id: UUID
    type: str                       # 'constructive' | 'cross_exam' | 'evidence' | 'discussion' | 'rebuttal' | 'closing' | 'judgment'
    execution: Literal["SEQUENTIAL", "PARALLEL"]
    dependencies: list[UUID]        # Must be COMPLETED before this runs
    participants: list[AgentAssignment]
    round_number: int = 1
```

`PhaseGraphBuilder.build(debate: Debate) -> list[Phase]` returns the materialized queue. Store on `debate.phase_graph_json` for replay.

---

## 18. Done Definition

This rebuild is "done" when:

1. All 16 build steps pass their checkpoints.
2. The smoke command in §16 completes a Mock-provider debate end-to-end.
3. The unmodified frontend connects and renders correctly against the new backend.
4. `pytest` shows 0 failures across `unit/`, `integration/`, and `e2e/`.
5. `runtime_diary` shows entries for every event listed in §13 during the smoke run.

Anything less is not done. Do not skip the self-verification.
