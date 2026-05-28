from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ─── Enums ───────────────────────────────────────────────────────────────────

class SessionMode(str, Enum):
    AI_VS_AI   = "ai_vs_ai"
    AI_VS_HUMAN = "ai_vs_human"
    CHAT       = "chat"


class DebateStatus(str, Enum):
    PREPARING    = "preparing"
    ACTIVE       = "active"
    JUDGING      = "judging"
    COMPLETED    = "completed"
    EARLY_STOPPED = "early_stopped"


class Team(str, Enum):
    PRO     = "pro"
    CON     = "con"
    NEUTRAL = "neutral"


class Archetype(str, Enum):
    LEAD_ADVOCATE      = "lead_advocate"
    REBUTTAL_CRITIC    = "rebuttal_critic"
    EVIDENCE_RESEARCHER = "evidence_researcher"
    CROSS_EXAMINER     = "cross_examiner"
    JUDGE              = "judge"
    JUDGE_ASSISTANT    = "judge_assistant"
    COUNCIL_ASSISTANT  = "council_assistant"
    PRACTICE_DEBATER   = "practice_debater"
    DEBATE_TRAINER     = "debate_trainer"


class IntelligenceType(str, Enum):
    CLAIM               = "claim"
    EVIDENCE            = "evidence"
    CHALLENGE           = "challenge"
    MEMORY_SAVED        = "memory_saved"
    LOW_CONFIDENCE      = "low_confidence"
    JUDGE_SCORECARD     = "judge_scorecard"
    POST_DEBATE_FEEDBACK = "post_debate_feedback"
    VERDICT_REVIEW      = "verdict_review"


class Currency(str, Enum):
    USD = "USD"; CNY = "CNY"; HKD = "HKD"; EUR = "EUR"
    JPY = "JPY"; GBP = "GBP"; AUD = "AUD"; CAD = "CAD"; SGD = "SGD"


# ─── Embedded Settings ────────────────────────────────────────────────────────

class AgentSettings(BaseModel):
    model:           Optional[str]   = None
    temperature:     Optional[float] = Field(None, ge=0.0, le=1.0)
    max_tokens:      Optional[int]   = Field(None, gt=0)
    response_length: Optional[Literal["Concise", "Normal", "Detailed"]] = None
    web_search:      bool            = False


class SessionSettings(BaseModel):
    # Debate Structure
    debaters_per_team:            int   = Field(1, ge=1, le=4)
    debate_rounds:                int   = Field(1, ge=1, le=6)
    discussion_messages_per_team: int   = Field(2, ge=1, le=4)
    # Inference
    overall_model:    Optional[str]  = None
    temperature:      float          = Field(0.55, ge=0.0, le=1.0)
    max_tokens:       int            = Field(400, gt=0)
    response_length:  Literal["Concise", "Normal", "Detailed"] = "Normal"
    context_window:   int            = Field(2, ge=0, le=6)
    # Behavior
    debate_tone:         str  = "Academic"
    language:            str  = "English"
    evidence_strictness: str  = "Normal"
    fact_check_mode:     bool = False
    judge_assistant_enabled: bool = False
    # Display
    auto_scroll:                        bool     = True
    show_timestamps:                    bool     = True
    show_token_count:                   bool     = True
    show_money_cost:                    bool     = True
    show_model_costs:                   bool     = False
    show_every_message_cost_in_debate:  bool     = False
    cost_currency:                      Currency = Currency.USD
    # Memory
    use_experience: bool = True
    # Practice
    human_side:       Literal["Auto", "Pro", "Con"] = "Auto"
    practice_flow:    Literal["Free", "Structured"]  = "Free"
    structured_rounds: int = Field(3, ge=1, le=12)
    use_user_profile: bool = True
    trainer_style:    Literal["Coach", "Direct", "Gentle", "Examiner"] = "Coach"
    training_focus:   Literal["Full Debate", "Rebuttal", "Evidence", "Clarity", "Cross-Examination"] = "Full Debate"
    opponent_difficulty: Literal["Adaptive", "Beginner", "Normal", "Hard"] = "Adaptive"
    # Judging
    judge_panel_size:       Literal[1, 3, 5] = 1
    analytics_weight:       float = Field(0.25, ge=0.0, le=0.75)
    allow_verdict_challenge: bool = True
    # Per-agent overrides
    agent_settings: dict[str, AgentSettings] = Field(default_factory=dict)


class CouncilSettings(BaseModel):
    universal_experience:        bool = True
    use_agent_identity_profiles: bool = True
    use_user_debate_profile:     bool = True
    debate_intelligence_depth:   Literal["Light", "Normal", "Deep"] = "Light"
    use_value_consequence_system: bool = False
    default_judge_mode:          Literal["Debate Performance", "Truth-Seeking", "Hybrid"] = "Debate Performance"
    theme:                       Literal["Light", "Dark", "System"] = "System"


# ─── Core Entities ────────────────────────────────────────────────────────────

class Session(BaseModel):
    id:              UUID
    name:            str
    code:            Optional[str]
    mode:            SessionMode
    settings:        SessionSettings
    client_id:       str = ""
    active_debate_id: Optional[UUID]
    state:           Literal["idle", "running", "archived"] = "idle"
    created_at:      datetime
    updated_at:      datetime


class AgentAssignment(BaseModel):
    team:      Team
    archetype: Archetype
    slot:      Literal[0, 1, 2]
    model:     Optional[str]
    settings:  AgentSettings = AgentSettings()
    state:     Literal["idle", "queued", "streaming", "completed"] = "idle"


class Debate(BaseModel):
    id:              UUID
    session_id:      UUID
    topic:           str
    pro_position:    Optional[str]
    con_position:    Optional[str]
    status:          DebateStatus
    assignments:     list[AgentAssignment] = []
    judge_config:    dict = {}
    analytics:       Optional[dict] = None
    cost_summary:    Optional[dict] = None
    practice_state:  Optional[dict] = None
    phase_graph:     Optional[dict] = None
    created_at:      datetime


class Message(BaseModel):
    id:         UUID
    session_id: UUID
    debate_id:  Optional[UUID]
    stream_id:  Optional[str]
    role:       str
    team:       Optional[Team]
    content:    str
    round:      Optional[int]
    phase:      Optional[str]
    model:      Optional[str]
    temperature: Optional[float]
    tokens_in:   int = 0
    tokens_out:  int = 0
    cost_usd:    float = 0.0
    metadata:    dict = {}
    created_at:  datetime


class TokenEvent(BaseModel):
    id:             UUID
    session_id:     UUID
    debate_id:      Optional[UUID]
    message_id:     UUID
    agent_role:     str
    model:          str
    provider:       str
    tokens_in:      int     = Field(ge=0)
    tokens_out:     int     = Field(ge=0)
    cost_usd:       Decimal = Field(ge=0)
    currency:       Currency = Currency.USD
    converted_cost: Decimal = Field(ge=0)
    timestamp:      datetime


class IntelligenceRecord(BaseModel):
    id:         UUID
    session_id: UUID
    debate_id:  UUID
    type:       IntelligenceType
    team:       Team
    agent_role: str
    content:    str
    confidence: float = Field(ge=0.0, le=1.0)
    scope:      Literal["universal", "chat"]
    created_at: datetime


class AgentExperience(BaseModel):
    id:                UUID
    agent_archetype:   str
    lesson_type:       Literal["debate_observation", "judge_scorecard", "user_feedback"]
    content:           str
    confidence:        Literal["low", "medium", "high"]
    use_count:         int = 0
    last_used_at:      Optional[datetime] = None
    source_debate_id:  Optional[UUID] = None
    source_session_id: Optional[UUID] = None


class UserDebateProfile(BaseModel):
    user_id:                   str
    debates_completed:         int = 0
    practice_debates_completed: int = 0
    wins:         dict = Field(default_factory=lambda: {"pro": 0, "con": 0, "unclear": 0})
    side_history: dict = Field(default_factory=lambda: {"pro": 0, "con": 0, "auto": 0})
    strengths:    list[str] = []   # max 18
    weaknesses:   list[str] = []   # max 18
    trainer_notes: list[str] = [] # max 30
    style_tags:   list[str] = []   # max 12
    last_updated_at: Optional[datetime] = None


class CostRate(BaseModel):
    model:               str
    provider:            str
    input_rate_per_1m:   float = Field(ge=0)
    output_rate_per_1m:  float = Field(ge=0)
    pricing_available:   bool
    source:              Literal["openrouter_api", "local_fallback", "unavailable"]
    fetched_at:          Optional[datetime] = None
