from __future__ import annotations

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Index, Integer,
    String, Text, func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class SessionRow(Base):
    __tablename__ = "sessions"

    id               = Column(String, primary_key=True)
    name             = Column(Text, nullable=False)
    code             = Column(Text, unique=True)
    mode             = Column(Text)
    settings_json    = Column(Text, nullable=False, default="{}")
    client_id        = Column(Text, nullable=False, default="")
    active_debate_id = Column(String)
    state            = Column(Text, default="idle")
    created_at       = Column(DateTime, server_default=func.now())
    updated_at       = Column(DateTime, server_default=func.now(), onupdate=func.now())

    debates  = relationship("DebateRow",  back_populates="session", cascade="all, delete-orphan")
    messages = relationship("MessageRow", back_populates="session", cascade="all, delete-orphan")


class DebateRow(Base):
    __tablename__ = "debates"

    id                  = Column(String, primary_key=True)
    session_id          = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"))
    topic               = Column(Text, nullable=False)
    pro_position        = Column(Text)
    con_position        = Column(Text)
    status              = Column(Text)
    assignments_json    = Column(Text)
    judge_config_json   = Column(Text)
    analytics_json      = Column(Text)
    cost_summary_json   = Column(Text)
    practice_state_json = Column(Text)
    phase_graph_json    = Column(Text)
    created_at          = Column(DateTime, server_default=func.now())

    session  = relationship("SessionRow", back_populates="debates")
    messages = relationship("MessageRow", back_populates="debate", cascade="all, delete-orphan")


class MessageRow(Base):
    __tablename__ = "messages"

    id          = Column(String, primary_key=True)
    session_id  = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"))
    debate_id   = Column(String, ForeignKey("debates.id",  ondelete="CASCADE"))
    stream_id   = Column(Text)
    role        = Column(Text)
    team        = Column(Text)
    content     = Column(Text)
    round       = Column(Integer)
    phase       = Column(Text)
    model       = Column(Text)
    temperature = Column(Float)
    tokens_in   = Column(Integer, default=0)
    tokens_out  = Column(Integer, default=0)
    cost_usd    = Column(Float,   default=0.0)
    metadata_json = Column(Text)
    created_at  = Column(DateTime, server_default=func.now())

    session = relationship("SessionRow", back_populates="messages")
    debate  = relationship("DebateRow",  back_populates="messages")


class TokenEventRow(Base):
    __tablename__ = "token_events"

    id             = Column(String, primary_key=True)
    session_id     = Column(String, nullable=False)
    debate_id      = Column(String)
    message_id     = Column(String, nullable=False)
    agent_role     = Column(Text)
    model          = Column(Text)
    provider       = Column(Text)
    tokens_in      = Column(Integer, nullable=False)
    tokens_out     = Column(Integer, nullable=False)
    cost_usd       = Column(Float,   nullable=False)
    currency       = Column(Text, default="USD")
    converted_cost = Column(Float, nullable=False)
    timestamp      = Column(DateTime, server_default=func.now())


class IntelligenceRecordRow(Base):
    __tablename__ = "intelligence_records"

    id         = Column(String, primary_key=True)
    session_id = Column(String, nullable=False)
    debate_id  = Column(String, nullable=False)
    type       = Column(Text)
    team       = Column(Text)
    agent_role = Column(Text)
    content    = Column(Text)
    confidence = Column(Float)
    scope      = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class AgentExperienceRow(Base):
    __tablename__ = "agent_experiences"

    id                = Column(String, primary_key=True)
    agent_archetype   = Column(Text, nullable=False)
    lesson_type       = Column(Text)
    content           = Column(Text)
    confidence        = Column(Text)
    use_count         = Column(Integer, default=0)
    last_used_at      = Column(DateTime)
    source_debate_id  = Column(String)
    source_session_id = Column(String)
    embedding_blob    = Column(Text)  # base64 for SQLite; BLOB in Postgres


class UserDebateProfileRow(Base):
    __tablename__ = "user_debate_profiles"

    user_id                    = Column(String, primary_key=True)
    debates_completed          = Column(Integer, default=0)
    practice_debates_completed = Column(Integer, default=0)
    wins_json          = Column(Text)
    side_history_json  = Column(Text)
    strengths_json     = Column(Text)
    weaknesses_json    = Column(Text)
    trainer_notes_json = Column(Text)
    style_tags_json    = Column(Text)
    last_updated_at    = Column(DateTime)


class CostRateRow(Base):
    __tablename__ = "cost_rates"

    model               = Column(String, primary_key=True)
    provider            = Column(Text)
    input_rate_per_1m   = Column(Float)
    output_rate_per_1m  = Column(Float)
    pricing_available   = Column(Boolean)
    source              = Column(Text)
    fetched_at          = Column(DateTime)


class CouncilSettingsRow(Base):
    __tablename__ = "council_settings"

    id            = Column(Integer, primary_key=True)  # singleton — id must be 1
    settings_json = Column(Text, nullable=False)


class RuntimeDiaryRow(Base):
    __tablename__ = "runtime_diary"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    source     = Column(Text)
    event      = Column(Text)
    detail     = Column(Text)
    session_id = Column(Text)
    timestamp  = Column(DateTime, server_default=func.now())


# ─── Indexes ──────────────────────────────────────────────────────────────────

Index("idx_messages_debate",        MessageRow.debate_id)
Index("idx_messages_session",       MessageRow.session_id)
Index("idx_messages_stream",        MessageRow.stream_id)
Index("idx_intelligence_debate",    IntelligenceRecordRow.debate_id)
Index("idx_intelligence_type",      IntelligenceRecordRow.type, IntelligenceRecordRow.agent_role)
Index("idx_token_events_session",   TokenEventRow.session_id)
Index("idx_token_events_debate",    TokenEventRow.debate_id)
Index("idx_agent_exp_archetype",    AgentExperienceRow.agent_archetype)
Index("idx_agent_exp_used",         AgentExperienceRow.last_used_at)
Index("idx_runtime_session",        RuntimeDiaryRow.session_id)
Index("idx_runtime_event",          RuntimeDiaryRow.event)
Index("idx_debates_session_status", DebateRow.session_id, DebateRow.status)
