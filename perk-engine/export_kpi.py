#!/usr/bin/env python3
"""
Export Intel Pack KPI snapshot to kpi.json.

Run this any time you want to refresh the static KPI data for the
revenue-tracker dashboard (which can't query SQLite directly as a file:// page).

Usage:
    python export_kpi.py
    python export_kpi.py --db perk_engine.db --out ../../../revenue-tracker/kpi.json

Outputs kpi.json next to the revenue-tracker/index.html by default.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).parent
DEFAULT_DB  = BASE_DIR / "perk_engine.db"
DEFAULT_OUT = BASE_DIR.parent.parent / "revenue-tracker" / "kpi.json"


def compute_kpi(db_path: Path) -> dict:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    def count(sql: str, *params) -> int:
        row = conn.execute(sql, params).fetchone()
        return (row[0] or 0) if row else 0

    total_signups    = count("SELECT COUNT(*) FROM users")
    signups_last_7d  = count("SELECT COUNT(*) FROM users WHERE created_at >= datetime('now', '-7 days')")
    signups_last_30d = count("SELECT COUNT(*) FROM users WHERE created_at >= datetime('now', '-30 days')")

    total_api_calls   = count("SELECT COUNT(*) FROM analytics_events WHERE event_type IN ('match_run','checklist_generated','api_call')")
    api_calls_last_7d = count("SELECT COUNT(*) FROM analytics_events WHERE event_type IN ('match_run','checklist_generated','api_call') AND created_at >= datetime('now', '-7 days')")
    unique_api_agents = count("SELECT COUNT(DISTINCT caller_agent) FROM analytics_events WHERE caller_type='agent_api' AND caller_agent IS NOT NULL")

    total_checklists = count("SELECT COUNT(DISTINCT user_id) FROM checklists WHERE matched=1")
    conversion_rate  = round((total_checklists / total_signups * 100), 1) if total_signups > 0 else 0.0

    rev_total_cents = count("SELECT COALESCE(SUM(amount_cents),0) FROM revenue_events WHERE amount_cents > 0")
    rev_30d_cents   = count("SELECT COALESCE(SUM(amount_cents),0) FROM revenue_events WHERE amount_cents > 0 AND created_at >= datetime('now', '-30 days')")
    stripe_live     = count("SELECT COUNT(*) FROM revenue_events WHERE source='stripe_webhook'") > 0

    affiliate_clicks = count("SELECT COUNT(*) FROM analytics_events WHERE event_type='affiliate_click'")

    conn.close()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_signups": total_signups,
        "signups_last_7d": signups_last_7d,
        "signups_last_30d": signups_last_30d,
        "total_api_calls": total_api_calls,
        "api_calls_last_7d": api_calls_last_7d,
        "unique_api_agents": unique_api_agents,
        "total_checklists": total_checklists,
        "conversion_rate_pct": conversion_rate,
        "revenue_total_usd": round(rev_total_cents / 100, 2),
        "revenue_last_30d_usd": round(rev_30d_cents / 100, 2),
        "revenue_stripe_live": stripe_live,
        "affiliate_click_events": affiliate_clicks,
    }


def main():
    parser = argparse.ArgumentParser(description="Export Intel Pack KPI snapshot to JSON")
    parser.add_argument("--db",  default=str(DEFAULT_DB),  help="Path to perk_engine.db")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output kpi.json path")
    args = parser.parse_args()

    db_path  = Path(args.db)
    out_path = Path(args.out)

    if not db_path.exists():
        print(f"ERROR: DB not found at {db_path}")
        print("Run the perk engine API first to initialise the DB.")
        raise SystemExit(1)

    kpi = compute_kpi(db_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(kpi, indent=2))
    print(f"KPI exported to {out_path}")
    print(f"  Signups: {kpi['total_signups']} total, {kpi['signups_last_7d']} last 7d")
    print(f"  API calls: {kpi['total_api_calls']} total")
    print(f"  Checklists: {kpi['total_checklists']} ({kpi['conversion_rate_pct']}% conversion)")
    print(f"  Revenue: ${kpi['revenue_total_usd']:.2f} (Stripe live: {kpi['revenue_stripe_live']})")


if __name__ == "__main__":
    main()
