import hashlib
import os
import secrets
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db import Base

# Must match whatever embedding model Phase 2 (RAG) settles on — recorded as
# a decision once that choice is made (see DECISIONS.md).
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "1536"))


def generate_source_key() -> str:
    return "src_" + secrets.token_urlsafe(24)


def hash_source_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


class Project(Base):
    """A user's monitored application/service. Owns one or more LogSources.
    owner_id is the Supabase auth user id (a string, not a local FK — the
    user table lives in Supabase, not this database)."""

    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Alerting (feature: webhook notifications on new issues) — a generic
    # webhook URL, POSTed a Slack-compatible {"text": ...} payload so it
    # works with Slack incoming webhooks or any generic endpoint (e.g.
    # webhook.site) without a Slack-specific integration.
    webhook_url = Column(String, nullable=True)

    # GitHub integration (feature: one-click "Open PR" for a suggested fix).
    # github_repo is "owner/name", not sensitive. The token IS sensitive —
    # stored encrypted (see app/crypto.py), never in plaintext, since unlike
    # the deliberately-non-sensitive cloud source config fields, a PAT is a
    # real secret we must actually protect.
    github_repo = Column(String, nullable=True)
    github_token_encrypted = Column(Text, nullable=True)

    sources = relationship("LogSource", back_populates="project", cascade="all, delete-orphan")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")


class ProjectMember(Base):
    """Team sharing: a project owner can invite a teammate by email. The
    invite is matched to a Supabase user id the first time that email signs
    in (see app/routers/projects.py) — Supabase's own user directory isn't
    queryable from our backend, so matching happens lazily on sign-in
    rather than at invite time."""

    __tablename__ = "project_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    email = Column(String, nullable=False)
    user_id = Column(String, nullable=True)  # filled in once that email signs in
    invited_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="members")


class LogSource(Base):
    """One log-ingestion source under a project — see DECISIONS.md:
    "Canonical log schema + per-source adapters". Only source_type="file" is
    actually pollable today (the file-tail adapter); cloud source types are
    modeled and configurable now so their adapters can be dropped in later
    without a schema change, but report status="coming_soon".

    api_key_hash gates POST /logs/ingest — a shipper must present the
    matching plaintext key (as X-API-Key) to submit events for this
    source, closing the originally-unauthenticated ingestion endpoint.
    Only the SHA-256 hash is stored — like a password, the plaintext key
    is shown to the user exactly once, at creation, and is not
    recoverable after that."""

    __tablename__ = "log_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=False)
    source_type = Column(String, nullable=False)  # "file" | "cloudwatch" | "azure_monitor"
    config = Column(JSONB, nullable=False, default=dict)
    status = Column(String, nullable=False, default="active")  # "active" | "coming_soon"
    api_key_hash = Column(String, nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="sources")


class Issue(Base):
    """A deduplicated, grouped error — the unit the dashboard actually
    shows, instead of one row per raw occurrence. Fingerprinted by
    (commit_hash, file_path, line_number) when correlation succeeded
    (falls back to a hash of the message when it didn't), so repeated
    firings of the same bug increment occurrence_count on one row instead
    of flooding the feed — see DECISIONS.md: "Issue grouping"."""

    __tablename__ = "issues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    log_source_id = Column(UUID(as_uuid=True), ForeignKey("log_sources.id"), nullable=False)
    fingerprint = Column(String, nullable=False, index=True)
    title = Column(Text, nullable=False)
    level = Column(String, nullable=False)
    service = Column(String, nullable=False)
    status = Column(String, nullable=False, default="open")  # open | acknowledged | resolved | ignored
    occurrence_count = Column(Integer, nullable=False, default=1)
    first_seen = Column(DateTime, nullable=False)
    last_seen = Column(DateTime, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    commit_hash = Column(String, nullable=True)
    commit_author = Column(String, nullable=True)
    commit_summary = Column(Text, nullable=True)
    file_path = Column(String, nullable=True)
    line_number = Column(Integer, nullable=True)

    log_source = relationship("LogSource")
    events = relationship("LogEventRecord", back_populates="issue")
    fix_suggestions = relationship("FixSuggestionRecord", back_populates="issue")


class LogEventRecord(Base):
    """A single raw ingested event — the full audit trail. The dashboard
    reads from Issue (grouped), not this table, but every occurrence is
    still stored here."""

    __tablename__ = "log_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    log_source_id = Column(UUID(as_uuid=True), ForeignKey("log_sources.id"), nullable=True)
    issue_id = Column(UUID(as_uuid=True), ForeignKey("issues.id"), nullable=True)
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

    issue = relationship("Issue", back_populates="events")


class FixSuggestionRecord(Base):
    """One suggestion per Issue (not per raw event — see Issue grouping):
    re-running the LLM for every occurrence of an already-diagnosed bug
    would be wasteful and pointless, so tasks.py only generates one when an
    Issue is first created."""

    __tablename__ = "fix_suggestions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    issue_id = Column(UUID(as_uuid=True), ForeignKey("issues.id"), nullable=False)
    explanation = Column(Text, nullable=False)
    diff = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    # Set once a human confirms the fix actually resolved the issue -
    # feeds back into the RAG corpus (fix_examples) as a real, verified
    # example rather than an unvalidated LLM output.
    added_to_knowledge_base = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    issue = relationship("Issue", back_populates="fix_suggestions")


class FixExample(Base):
    """RAG corpus: historical (error -> fix) pairs seeded from BugsInPy/
    SWE-bench (see DECISIONS.md: "Data sourcing strategy"), embedded for
    similarity retrieval in Phase 2. Also grown over time from suggestions
    a human confirmed actually worked (see FixSuggestionRecord above)."""

    __tablename__ = "fix_examples"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    error_description = Column(Text, nullable=False)
    fix_diff = Column(Text, nullable=False)
    source = Column(String, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
