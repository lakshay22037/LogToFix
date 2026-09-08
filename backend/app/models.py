import os
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db import Base

# Must match whatever embedding model Phase 2 (RAG) settles on — recorded as
# a decision once that choice is made (see DECISIONS.md).
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "1536"))


class Project(Base):
    """A user's monitored application/service. Owns one or more LogSources.
    owner_id is the Supabase auth user id (a string, not a local FK — the
    user table lives in Supabase, not this database)."""

    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    sources = relationship("LogSource", back_populates="project", cascade="all, delete-orphan")


class LogSource(Base):
    """One log-ingestion source under a project — see DECISIONS.md:
    "Canonical log schema + per-source adapters". Only source_type="file" is
    actually pollable today (the file-tail adapter); cloud source types are
    modeled and configurable now so their adapters can be dropped in later
    without a schema change, but report status="coming_soon"."""

    __tablename__ = "log_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=False)
    source_type = Column(String, nullable=False)  # "file" | "cloudwatch" | "azure_monitor"
    config = Column(JSONB, nullable=False, default=dict)
    status = Column(String, nullable=False, default="active")  # "active" | "coming_soon"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="sources")


class LogEventRecord(Base):
    __tablename__ = "log_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    log_source_id = Column(UUID(as_uuid=True), ForeignKey("log_sources.id"), nullable=True)
    timestamp = Column(DateTime, nullable=False)
    level = Column(String, nullable=False)
    service = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    stack_trace = Column(Text, nullable=True)
    source_type = Column(String, nullable=False)
    raw = Column(Text, nullable=False)
    correlation_id = Column(String, nullable=True)

    commit_hash = Column(String, nullable=True)
    commit_author = Column(String, nullable=True)
    commit_summary = Column(Text, nullable=True)
    file_path = Column(String, nullable=True)
    line_number = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    fix_suggestions = relationship("FixSuggestionRecord", back_populates="log_event")


class FixSuggestionRecord(Base):
    __tablename__ = "fix_suggestions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    log_event_id = Column(UUID(as_uuid=True), ForeignKey("log_events.id"), nullable=False)
    explanation = Column(Text, nullable=False)
    diff = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    log_event = relationship("LogEventRecord", back_populates="fix_suggestions")


class FixExample(Base):
    """RAG corpus: historical (error -> fix) pairs seeded from BugsInPy/
    SWE-bench (see DECISIONS.md: "Data sourcing strategy"), embedded for
    similarity retrieval in Phase 2."""

    __tablename__ = "fix_examples"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    error_description = Column(Text, nullable=False)
    fix_diff = Column(Text, nullable=False)
    source = Column(String, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
