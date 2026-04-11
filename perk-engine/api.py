#!/usr/bin/env python3
"""
Runway Credits — Agent API (Phase 3)

Wraps the matching engine + checklist as an HTTP API consumable by
external agents (Zero/OpenClaw) and automated workflows.

Start:
    uvicorn api:app --host 0.0.0.0 --port 8000

Or:
    python api.py [--host 0.0.0.0] [--port 8000] [--db perk_engine.db]

Endpoints:
    POST /match                  Run matching engine, return personalized program list
    POST /checklist/generate     Run matching + persist checklist to SQLite, return items
    GET  /checklist/{user_ref}   Fetch existing checklist for a user (email or id)
    GET  /kpi                    Intel Pack KPI summary (signups, calls, revenue)
    GET  /health                 Liveness check
    GET  /openapi.json           OpenAPI 3.1 schema (built-in FastAPI)
    GET  /docs                   Swagger UI
"""

from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent
DEFAULT_DB = BASE_DIR / "perk_engine.db"


# ---------------------------------------------------------------------------
# Lazy module loader (reuses same pattern as checklist.py)
# ---------------------------------------------------------------------------

def _load_mod(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _matcher():
    return _load_mod("matcher", BASE_DIR / "matcher.py")


def _setup_db():
    return _load_mod("setup_db", BASE_DIR / "setup_db.py")


def _ensure_db(db_path: Path):
    """Bootstrap the SQLite DB + catalog if it doesn't exist."""
    setup = _setup_db()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    setup.apply_schema(conn)
    catalog_count = conn.execute("SELECT COUNT(*) FROM programs").fetchone()[0]
    if catalog_count == 0:
        setup.import_catalog(conn)
    conn.close()


# ---------------------------------------------------------------------------
# Analytics helpers
# ---------------------------------------------------------------------------

def _log_event(
    db_path: Path,
    event_type: str,
    *,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    caller_type: str = "web_ui",
    caller_agent: Optional[str] = None,
    endpoint: Optional[str] = None,
    program_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Fire-and-forget analytics event write. Silently swallows errors."""
    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """INSERT INTO analytics_events
               (id, event_type, user_id, user_email, caller_type, caller_agent, endpoint, program_id, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                uuid.uuid4().hex[:16],
                event_type,
                user_id,
                user_email,
                caller_type,
                caller_agent,
                endpoint,
                program_id,
                json.dumps(metadata or {}),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # analytics must never break the request


def _caller_type_from_request(request_headers: dict) -> tuple[str, Optional[str]]:
    """Detect whether the caller is the web UI, an agent, or CLI."""
    ua = request_headers.get("user-agent", "")
    agent_id = request_headers.get("x-agent-id")
    if agent_id:
        return "agent_api", agent_id
    if "python" in ua.lower() or "curl" in ua.lower() or "httpie" in ua.lower():
        return "cli", None
    return "web_ui", None


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class UserProfile(BaseModel):
    """
    Input profile for the matching engine.  All fields are optional except
    `entity_type` — the engine needs it to assess US-entity eligibility.
    """
    name: Optional[str] = Field(None, description="Full name or company name")
    email: Optional[str] = Field(None, description="Primary email (used as user key in the checklist DB)")
    entity_type: str = Field(
        ...,
        description="One of: llc, c_corp, s_corp, sole_proprietor, non_us",
        examples=["llc"],
    )
    funding_stage: Optional[str] = Field(
        None,
        description="One of: bootstrapped, pre_seed, seed, series_a, series_b_plus",
        examples=["bootstrapped"],
    )
    funding_raised_usd: Optional[int] = Field(0, description="Total funding raised in USD")
    team_size: Optional[int] = Field(1, description="Number of full-time employees/founders")
    tech_stack: Optional[List[str]] = Field(
        default_factory=list,
        description="Tags from: web, ai_ml, fintech, mobile, saas, backend, frontend, data_analytics",
    )
    available_unlock_methods: Optional[List[str]] = Field(
        default_factory=list,
        description="Accelerator/network memberships that unlock deals: yc, techstars, antler, a16z, 500_startups, sequoia_scout, other",
    )
    has_vc_or_accelerator: Optional[bool] = Field(
        False,
        description="True if the company has VC backing or is in an accelerator",
    )
    current_perks: Optional[List[str]] = Field(
        default_factory=list,
        description="Program IDs the company already holds (they will be skipped). E.g. ['aws_activate', 'brex']",
    )


class ProgramResult(BaseModel):
    program_id: str
    name: str
    provider: Optional[str] = None
    category: Optional[str] = None
    status: str  # recommended | ineligible | conflict
    score: Optional[float] = None
    scoring_notes: Optional[List[str]] = None
    realistic_credit_usd: Optional[int] = None
    credit_range: Optional[str] = None
    duration_months: Optional[int] = None
    sequence_priority: Optional[int] = None
    application_url: Optional[str] = None
    approval_time_days: Optional[int] = None
    unlock_methods: Optional[List[str]] = None
    stacks_well_with: Optional[List[str]] = None
    stacking_notes: Optional[str] = None
    sponsor_warning: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    ineligible_reason: Optional[str] = None
    conflict_reason: Optional[str] = None


class StackingOpportunity(BaseModel):
    stack_name: str
    your_programs: List[str]
    all_programs: List[str]
    value_note: str
    notes: str


class MatchTotals(BaseModel):
    recommended_count: int
    ineligible_count: int
    conflict_count: int
    total_realistic_value_usd: int
    total_max_value_usd: int


class MatchResponse(BaseModel):
    """Full response from the matching engine."""
    profile_summary: Dict[str, Any]
    recommended: List[ProgramResult]
    stacking_opportunities: List[StackingOpportunity]
    ineligible: List[ProgramResult]
    conflicts: List[ProgramResult]
    totals: MatchTotals


class ChecklistItem(BaseModel):
    program_id: str
    name: str
    category: Optional[str] = None
    status: str
    match_score: Optional[float] = None
    match_notes: Optional[str] = None
    realistic_credit_usd: Optional[int] = None
    credit_range: Optional[str] = None
    application_url: Optional[str] = None
    approval_time_days: Optional[int] = None
    stacking_notes: Optional[str] = None
    affiliate_link: Optional[str] = None
    affiliate_notes: Optional[str] = None
    user_notes: Optional[str] = None
    credit_amount_received: Optional[int] = None
    applied_at: Optional[str] = None
    approved_at: Optional[str] = None
    reminder_date: Optional[str] = None
    updated_at: Optional[str] = None


class ChecklistResponse(BaseModel):
    user_id: str
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    total_programs: int
    total_realistic_value_usd: int
    approved_value_usd: int
    items: List[ChecklistItem]


class GenerateChecklistRequest(BaseModel):
    profile: UserProfile
    db: Optional[str] = Field(None, description="Path to SQLite DB (defaults to perk_engine.db next to api.py)")


class KpiResponse(BaseModel):
    generated_at: str
    # acquisition
    total_signups: int = Field(description="Unique user profiles submitted (self-serve UI + API)")
    signups_last_7d: int
    signups_last_30d: int
    # API usage
    total_api_calls: int = Field(description="Total /match + /checklist/generate calls from all callers")
    api_calls_last_7d: int
    unique_api_agents: int = Field(description="Distinct agent callers (x-agent-id header)")
    # conversion
    total_checklists: int
    conversion_rate_pct: float = Field(description="% of signups that generated a checklist (free->engaged)")
    # revenue (Stripe webhook-populated; $0 until credentials provided)
    revenue_total_usd: float
    revenue_last_30d_usd: float
    revenue_stripe_live: bool = Field(description="True once Stripe webhook is connected")
    # affiliate
    affiliate_click_events: int


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Runway Credits Agent API",
    description=(
        "JSON API wrapping the Runway Credits matching engine and checklist. "
        "Designed to be called by Zero/OpenClaw or any agent that needs to assess "
        "a user profile and return a personalized startup-credits roadmap."
    ),
    version="1.0.0",
    contact={"name": "Cashflow CTO", "email": "cto@cashflow.run"},
    license_info={"name": "Proprietary"},
)

# Allow browser requests from any local dev origin (file://, localhost:*)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", summary="Liveness check")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat() + "Z"}


@app.post(
    "/match",
    response_model=MatchResponse,
    summary="Run matching engine",
    description=(
        "Accepts a user profile and returns a personalized, ordered list of "
        "recommended startup credit programs with scores, credit values, stacking "
        "opportunities, and application URLs. No data is persisted."
    ),
)
def match(profile: UserProfile, request: Request) -> MatchResponse:
    caller_type, caller_agent = _caller_type_from_request(dict(request.headers))
    try:
        matcher = _matcher()
        catalog = matcher.load_catalog()
        result = matcher.run_matching(profile.model_dump(), catalog)
        _log_event(
            DEFAULT_DB,
            "match_run",
            user_email=profile.email,
            caller_type=caller_type,
            caller_agent=caller_agent,
            endpoint="/match",
            metadata={"entity_type": profile.entity_type, "funding_stage": profile.funding_stage},
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post(
    "/checklist/generate",
    response_model=ChecklistResponse,
    summary="Generate (or refresh) checklist",
    description=(
        "Runs the matching engine against the supplied profile, persists the "
        "results to SQLite, and returns the full checklist. If a checklist "
        "already exists for this user (matched by email), it is refreshed with "
        "the latest scores. Requires `profile.email` to identify the user."
    ),
)
def generate_checklist(req: GenerateChecklistRequest, request: Request) -> ChecklistResponse:
    profile_dict = req.profile.model_dump()
    if not profile_dict.get("email"):
        raise HTTPException(
            status_code=422,
            detail="profile.email is required to identify the user in the checklist DB",
        )

    db_path = Path(req.db) if req.db else DEFAULT_DB
    caller_type, caller_agent = _caller_type_from_request(dict(request.headers))

    try:
        _ensure_db(db_path)

        matcher = _matcher()
        catalog = matcher.load_catalog()
        result = matcher.run_matching(profile_dict, catalog)

        setup = _setup_db()
        setup.save_checklist_from_result(str(db_path), profile_dict, result)

        checklist = _fetch_checklist(db_path, profile_dict["email"])

        # Log signup + checklist generation
        _log_event(
            db_path, "signup",
            user_id=checklist.user_id,
            user_email=profile_dict.get("email"),
            caller_type=caller_type,
            caller_agent=caller_agent,
            endpoint="/checklist/generate",
            metadata={"entity_type": profile_dict.get("entity_type"), "funding_stage": profile_dict.get("funding_stage")},
        )
        _log_event(
            db_path, "checklist_generated",
            user_id=checklist.user_id,
            user_email=profile_dict.get("email"),
            caller_type=caller_type,
            caller_agent=caller_agent,
            endpoint="/checklist/generate",
            metadata={"programs_matched": checklist.total_programs, "total_value_usd": checklist.total_realistic_value_usd},
        )

        return checklist
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get(
    "/checklist/{user_ref}",
    response_model=ChecklistResponse,
    summary="Fetch checklist for a user",
    description=(
        "Returns the stored checklist for a user identified by email or user ID. "
        "The checklist must have been generated first via POST /checklist/generate."
    ),
)
def get_checklist(user_ref: str) -> ChecklistResponse:
    db_path = DEFAULT_DB
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="No checklist DB found. Call POST /checklist/generate first.")
    try:
        return _fetch_checklist(db_path, user_ref)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# DB query helpers
# ---------------------------------------------------------------------------

def _fetch_checklist(db_path: Path, user_ref: str) -> ChecklistResponse:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    user = conn.execute(
        "SELECT id, name, email FROM users WHERE id=? OR email=?",
        (user_ref, user_ref),
    ).fetchone()
    if not user:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail=f"No user found for '{user_ref}'. Generate a checklist first via POST /checklist/generate",
        )

    user_id = user["id"]

    rows = conn.execute("""
        SELECT
            c.program_id,
            p.name,
            p.category,
            p.realistic_credit_usd,
            p.credit_min_usd,
            p.credit_max_usd,
            p.application_url,
            p.approval_time_days,
            p.stacking_notes,
            c.status,
            c.match_score,
            c.match_notes,
            c.applied_at,
            c.approved_at,
            c.affiliate_link,
            c.affiliate_notes,
            c.user_notes,
            c.credit_amount_received,
            c.reminder_date,
            c.updated_at
        FROM checklists c
        JOIN programs p ON p.id = c.program_id
        WHERE c.user_id = ? AND c.matched = 1
        ORDER BY c.match_score DESC
    """, (user_id,)).fetchall()

    items = []
    total_value = 0
    approved_value = 0
    for r in rows:
        credit = r["realistic_credit_usd"] or 0
        total_value += credit
        if r["status"] == "approved":
            approved_value += credit
        credit_range = None
        if r["credit_min_usd"] is not None and r["credit_max_usd"] is not None:
            credit_range = f"${r['credit_min_usd']:,}-${r['credit_max_usd']:,}"
        items.append(ChecklistItem(
            program_id=r["program_id"],
            name=r["name"],
            category=r["category"],
            status=r["status"],
            match_score=r["match_score"],
            match_notes=r["match_notes"],
            realistic_credit_usd=r["realistic_credit_usd"],
            credit_range=credit_range,
            application_url=r["application_url"],
            approval_time_days=r["approval_time_days"],
            stacking_notes=r["stacking_notes"],
            affiliate_link=r["affiliate_link"],
            affiliate_notes=r["affiliate_notes"],
            user_notes=r["user_notes"],
            credit_amount_received=r["credit_amount_received"],
            applied_at=r["applied_at"],
            approved_at=r["approved_at"],
            reminder_date=r["reminder_date"],
            updated_at=r["updated_at"],
        ))

    conn.close()
    return ChecklistResponse(
        user_id=user_id,
        user_email=user["email"],
        user_name=user["name"],
        total_programs=len(items),
        total_realistic_value_usd=total_value,
        approved_value_usd=approved_value,
        items=items,
    )


# ---------------------------------------------------------------------------
# /kpi endpoint
# ---------------------------------------------------------------------------

@app.get(
    "/kpi",
    response_model=KpiResponse,
    summary="Intel Pack KPI summary",
    description=(
        "Returns a snapshot of revenue and usage KPIs for the Runway Credits Intel Pack. "
        "Reads from the analytics_events and revenue_events tables. "
        "Revenue figures are $0 until Stripe webhooks are connected (NOD-66)."
    ),
)
def get_kpi() -> KpiResponse:
    if not DEFAULT_DB.exists():
        raise HTTPException(status_code=503, detail="KPI DB not initialised yet. Call /checklist/generate first.")
    try:
        return _compute_kpi(DEFAULT_DB)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def _compute_kpi(db_path: Path) -> KpiResponse:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    now_iso = datetime.now(timezone.utc).isoformat()

    def count(sql: str, *params) -> int:
        row = conn.execute(sql, params).fetchone()
        return (row[0] or 0) if row else 0

    # Signups = unique users
    total_signups   = count("SELECT COUNT(*) FROM users")
    signups_last_7d = count("SELECT COUNT(*) FROM users WHERE created_at >= datetime('now', '-7 days')")
    signups_last_30d = count("SELECT COUNT(*) FROM users WHERE created_at >= datetime('now', '-30 days')")

    # API calls = match_run + checklist_generated events
    total_api_calls   = count("SELECT COUNT(*) FROM analytics_events WHERE event_type IN ('match_run','checklist_generated','api_call')")
    api_calls_last_7d = count("SELECT COUNT(*) FROM analytics_events WHERE event_type IN ('match_run','checklist_generated','api_call') AND created_at >= datetime('now', '-7 days')")
    unique_api_agents = count("SELECT COUNT(DISTINCT caller_agent) FROM analytics_events WHERE caller_type='agent_api' AND caller_agent IS NOT NULL")

    # Conversion: signups that have a checklist
    total_checklists = count("SELECT COUNT(DISTINCT user_id) FROM checklists WHERE matched=1")
    conversion_rate  = round((total_checklists / total_signups * 100), 1) if total_signups > 0 else 0.0

    # Revenue (Stripe-sourced only; $0 until live)
    rev_total_cents = count("SELECT COALESCE(SUM(amount_cents),0) FROM revenue_events WHERE amount_cents > 0")
    rev_30d_cents   = count("SELECT COALESCE(SUM(amount_cents),0) FROM revenue_events WHERE amount_cents > 0 AND created_at >= datetime('now', '-30 days')")
    stripe_live     = count("SELECT COUNT(*) FROM revenue_events WHERE source='stripe_webhook'") > 0

    # Affiliate
    affiliate_clicks = count("SELECT COUNT(*) FROM analytics_events WHERE event_type='affiliate_click'")

    conn.close()

    return KpiResponse(
        generated_at=now_iso,
        total_signups=total_signups,
        signups_last_7d=signups_last_7d,
        signups_last_30d=signups_last_30d,
        total_api_calls=total_api_calls,
        api_calls_last_7d=api_calls_last_7d,
        unique_api_agents=unique_api_agents,
        total_checklists=total_checklists,
        conversion_rate_pct=conversion_rate,
        revenue_total_usd=round(rev_total_cents / 100, 2),
        revenue_last_30d_usd=round(rev_30d_cents / 100, 2),
        revenue_stripe_live=stripe_live,
        affiliate_click_events=affiliate_clicks,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Runway Credits Agent API")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Auto-reload on code changes (dev mode)")
    args = parser.parse_args()

    uvicorn.run(
        "api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
