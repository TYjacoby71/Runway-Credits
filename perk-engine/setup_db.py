#!/usr/bin/env python3
"""
Runway Credits — DB Setup & Catalog Import
Creates the SQLite database, applies the schema, and imports programs.json.

Usage:
    python setup_db.py                           # create/reset perk_engine.db
    python setup_db.py --db my.db                # custom DB path
    python setup_db.py --create-checklist        # create checklist from last matched roadmap
    python setup_db.py --profile user.json       # import user profile into DB

    # Called from matcher.py:
    python setup_db.py --save-checklist result.json --profile user.json
"""

import sqlite3
import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

BASE_DIR    = Path(__file__).parent
SCHEMA_PATH = BASE_DIR / "schema.sql"
CATALOG_PATH = BASE_DIR / "data" / "programs.json"
DEFAULT_DB  = Path(os.environ.get("DB_PATH", str(BASE_DIR / "perk_engine.db")))

# ─────────────────────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_connection(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def apply_schema(conn):
    schema = SCHEMA_PATH.read_text()
    conn.executescript(schema)
    conn.commit()
    print(f"  OK Schema applied")

# ─────────────────────────────────────────────────────────────────────────────
# Catalog import
# ─────────────────────────────────────────────────────────────────────────────

def import_catalog(conn):
    with open(CATALOG_PATH) as f:
        programs = json.load(f)

    inserted = 0
    updated = 0
    for p in programs:
        stacking = p.get("stacking", {})
        elig = p.get("eligibility", {})

        # Determine if US entity is required
        entity_types = elig.get("entity_types", [])
        requires_us = 1 if ("us_entity" in entity_types or "us_delaware_c_corp" in entity_types or "us_llc" in entity_types) and "any" not in entity_types else 0

        row = (
            p["id"],
            p.get("name", ""),
            p.get("provider", ""),
            p.get("category", ""),
            p.get("credit_min_usd", 0),
            p.get("credit_max_usd", 0),
            p.get("realistic_credit_usd", 0),
            p.get("duration_months"),
            p.get("application_url"),
            p.get("approval_time_days"),
            p.get("sequence_priority", 3),
            json.dumps(stacking.get("conflicts_with", [])),
            json.dumps(stacking.get("stacks_well_with", [])),
            stacking.get("notes"),
            json.dumps(p.get("unlock_methods", [])),
            json.dumps(p.get("tags", [])),
            p.get("notes"),
            elig.get("max_company_age_years"),
            elig.get("max_funding_usd"),
            elig.get("max_arr_usd"),
            requires_us,
            1 if elig.get("requires_partner_sponsor") else 0,
            1 if elig.get("requires_deployed_product") else 0,
            json.dumps(elig.get("funding_stages_eligible", [])),
            json.dumps(elig.get("tech_focus")) if elig.get("tech_focus") else None,
            json.dumps(p),
        )

        existing = conn.execute("SELECT id FROM programs WHERE id = ?", (p["id"],)).fetchone()
        if existing:
            conn.execute("""
                UPDATE programs SET
                    name=?, provider=?, category=?,
                    credit_min_usd=?, credit_max_usd=?, realistic_credit_usd=?,
                    duration_months=?, application_url=?, approval_time_days=?,
                    sequence_priority=?, conflicts_with=?, stacks_well_with=?,
                    stacking_notes=?, unlock_methods=?, tags=?, notes=?,
                    elig_max_company_age_years=?, elig_max_funding_usd=?, elig_max_arr_usd=?,
                    elig_requires_us_entity=?, elig_requires_sponsor=?, elig_requires_product=?,
                    elig_funding_stages=?, elig_tech_focus=?, raw_json=?,
                    updated_at=datetime('now')
                WHERE id=?
            """, row[1:] + (p["id"],))
            updated += 1
        else:
            conn.execute("""
                INSERT INTO programs (
                    id, name, provider, category,
                    credit_min_usd, credit_max_usd, realistic_credit_usd,
                    duration_months, application_url, approval_time_days,
                    sequence_priority, conflicts_with, stacks_well_with,
                    stacking_notes, unlock_methods, tags, notes,
                    elig_max_company_age_years, elig_max_funding_usd, elig_max_arr_usd,
                    elig_requires_us_entity, elig_requires_sponsor, elig_requires_product,
                    elig_funding_stages, elig_tech_focus, raw_json
                ) VALUES (
                    ?,?,?,?, ?,?,?, ?,?,?, ?,?,?, ?,?,?,?, ?,?,?, ?,?,?, ?,?,?
                )
            """, row)
            inserted += 1

    conn.commit()
    print(f"  OK Catalog imported: {inserted} new, {updated} updated ({inserted+updated} total programs)")

    # Import stacking rules
    with open(CATALOG_PATH) as f:
        programs = json.load(f)

    rules_added = 0
    for p in programs:
        stacking = p.get("stacking", {})
        for conflict_id in stacking.get("conflicts_with", []):
            # Check if the conflicting program exists
            exists = conn.execute("SELECT id FROM programs WHERE id=?", (conflict_id,)).fetchone()
            if not exists:
                continue
            # Check if rule already exists
            existing_rule = conn.execute(
                "SELECT id FROM stacking_rules WHERE program_a=? AND program_b=? AND relationship=?",
                (p["id"], conflict_id, "conflicts")
            ).fetchone()
            if not existing_rule:
                conn.execute(
                    "INSERT OR IGNORE INTO stacking_rules (program_a, program_b, relationship) VALUES (?, ?, ?)",
                    (p["id"], conflict_id, "conflicts")
                )
                rules_added += 1

        for stack_id in stacking.get("stacks_well_with", []):
            exists = conn.execute("SELECT id FROM programs WHERE id=?", (stack_id,)).fetchone()
            if not exists:
                continue
            existing_rule = conn.execute(
                "SELECT id FROM stacking_rules WHERE program_a=? AND program_b=? AND relationship=?",
                (p["id"], stack_id, "stacks_well")
            ).fetchone()
            if not existing_rule:
                conn.execute(
                    "INSERT OR IGNORE INTO stacking_rules (program_a, program_b, relationship) VALUES (?, ?, ?)",
                    (p["id"], stack_id, "stacks_well")
                )
                rules_added += 1

    conn.commit()
    print(f"  OK Stacking rules imported: {rules_added} rules")

# ─────────────────────────────────────────────────────────────────────────────
# User profile import
# ─────────────────────────────────────────────────────────────────────────────

def import_user(conn, profile):
    uid = profile.get("email") or profile.get("name") or f"user_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    # Use email as the ID if available, else generate
    user_id = profile.get("email") or uid

    existing = conn.execute("SELECT id FROM users WHERE id=? OR email=?", (user_id, profile.get("email",""))).fetchone()

    row_data = {
        "id": user_id,
        "email": profile.get("email") or None,
        "name": profile.get("name") or None,
        "entity_type": profile.get("entity_type", "llc"),
        "company_age_years": profile.get("company_age_years", 0),
        "funding_stage": profile.get("funding_stage", "bootstrapped"),
        "funding_raised_usd": profile.get("funding_raised_usd", 0),
        "annual_revenue_usd": profile.get("annual_revenue_usd", 0),
        "team_size": profile.get("team_size", 1),
        "tech_stack": json.dumps(profile.get("tech_stack", [])),
        "has_deployed_product": 1 if profile.get("has_deployed_product") else 0,
        "has_vc_or_accelerator": 1 if profile.get("has_vc_or_accelerator") else 0,
        "accelerator_memberships": json.dumps(profile.get("accelerator_memberships", [])),
        "has_brex": 1 if profile.get("has_brex") else 0,
        "has_stripe_atlas": 1 if profile.get("has_stripe_atlas") else 0,
        "has_mercury": 1 if profile.get("has_mercury") else 0,
        "has_ramp": 1 if profile.get("has_ramp") else 0,
        "current_perks": json.dumps(profile.get("current_perks", [])),
    }

    if existing:
        conn.execute("""
            UPDATE users SET
                name=:name, entity_type=:entity_type,
                company_age_years=:company_age_years, funding_stage=:funding_stage,
                funding_raised_usd=:funding_raised_usd, annual_revenue_usd=:annual_revenue_usd,
                team_size=:team_size, tech_stack=:tech_stack,
                has_deployed_product=:has_deployed_product, has_vc_or_accelerator=:has_vc_or_accelerator,
                accelerator_memberships=:accelerator_memberships, has_brex=:has_brex,
                has_stripe_atlas=:has_stripe_atlas, has_mercury=:has_mercury, has_ramp=:has_ramp,
                current_perks=:current_perks, updated_at=datetime('now')
            WHERE id=:id OR email=:email
        """, row_data)
        print(f"  OK Updated user profile: {user_id}")
        return existing["id"]
    else:
        conn.execute("""
            INSERT INTO users (
                id, email, name, entity_type, company_age_years, funding_stage,
                funding_raised_usd, annual_revenue_usd, team_size, tech_stack,
                has_deployed_product, has_vc_or_accelerator, accelerator_memberships,
                has_brex, has_stripe_atlas, has_mercury, has_ramp, current_perks
            ) VALUES (
                :id, :email, :name, :entity_type, :company_age_years, :funding_stage,
                :funding_raised_usd, :annual_revenue_usd, :team_size, :tech_stack,
                :has_deployed_product, :has_vc_or_accelerator, :accelerator_memberships,
                :has_brex, :has_stripe_atlas, :has_mercury, :has_ramp, :current_perks
            )
        """, row_data)
        conn.commit()
        print(f"  OK Created user profile: {user_id}")
        return user_id

# ─────────────────────────────────────────────────────────────────────────────
# Checklist save
# ─────────────────────────────────────────────────────────────────────────────

def save_checklist_from_result(db_path, profile, result):
    """Called by matcher.py to persist the roadmap as a checklist in SQLite."""
    conn = get_connection(db_path)

    # Ensure schema + catalog exist
    apply_schema(conn)
    catalog_count = conn.execute("SELECT COUNT(*) FROM programs").fetchone()[0]
    if catalog_count == 0:
        import_catalog(conn)

    # Import/update user
    user_id = import_user(conn, profile)

    # Save recommended programs as checklist rows
    saved = 0
    for prog in result.get("recommended", []):
        pid = prog["program_id"]
        existing = conn.execute(
            "SELECT id FROM checklists WHERE user_id=? AND program_id=?",
            (user_id, pid)
        ).fetchone()

        if existing:
            conn.execute("""
                UPDATE checklists SET
                    matched=1, match_score=?, match_notes=?, updated_at=datetime('now')
                WHERE user_id=? AND program_id=?
            """, (
                prog.get("score", 0),
                "; ".join(prog.get("scoring_notes", [])),
                user_id, pid
            ))
        else:
            conn.execute("""
                INSERT INTO checklists (user_id, program_id, matched, match_score, match_notes, status)
                VALUES (?, ?, 1, ?, ?, 'not_started')
            """, (
                user_id,
                pid,
                prog.get("score", 0),
                "; ".join(prog.get("scoring_notes", [])),
            ))
        saved += 1

    conn.commit()
    print(f"  OK Checklist saved: {saved} programs for user {user_id}")
    conn.close()

def list_checklist(conn, user_id):
    """Print the checklist for a user."""
    rows = conn.execute("""
        SELECT c.program_id, p.name, c.status, c.match_score, c.affiliate_link, c.user_notes
        FROM checklists c
        JOIN programs p ON p.id = c.program_id
        WHERE c.user_id = ? AND c.matched = 1
        ORDER BY c.match_score DESC
    """, (user_id,)).fetchall()

    if not rows:
        print("  No checklist found for this user.")
        return

    print(f"\n  Checklist for {user_id}:")
    print(f"  {'#':>3}  {'Program':<40} {'Status':<15} {'Score':>6}  {'Affiliate Link'}")
    print(f"  {'─'*3}  {'─'*40} {'─'*15} {'─'*6}  {'─'*30}")
    for i, r in enumerate(rows, 1):
        affiliate = r["affiliate_link"] or "—"
        print(f"  {i:>3}  {r['name']:<40} {r['status']:<15} {r['match_score']:>6.0f}  {affiliate}")

# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Runway Credits DB Setup")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite DB path")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate the DB")
    parser.add_argument("--import-catalog", action="store_true", default=True, help="Import programs.json (default: True)")
    parser.add_argument("--profile", help="Import a user profile JSON file")
    parser.add_argument("--save-checklist", help="Path to matcher result JSON to save as checklist")
    parser.add_argument("--list-checklist", help="List checklist for this user_id/email")
    parser.add_argument("--update-affiliate", nargs=3, metavar=("USER_ID", "PROGRAM_ID", "LINK"),
                        help="Set affiliate link: --update-affiliate user@email.com aws_activate https://...")
    parser.add_argument("--update-status", nargs=3, metavar=("USER_ID", "PROGRAM_ID", "STATUS"),
                        help="Update program status: --update-status user@email.com aws_activate applied")
    args = parser.parse_args()

    db_path = Path(args.db)

    if args.reset and db_path.exists():
        db_path.unlink()
        print(f"  OK Removed existing DB: {db_path}")

    print(f"  DB: {db_path}")
    conn = get_connection(db_path)
    apply_schema(conn)

    if args.import_catalog:
        import_catalog(conn)

    if args.profile:
        with open(args.profile) as f:
            profile = json.load(f)
        import_user(conn, profile)

    if args.save_checklist and args.profile:
        with open(args.save_checklist) as f:
            result = json.load(f)
        with open(args.profile) as f:
            profile = json.load(f)
        save_checklist_from_result(str(db_path), profile, result)

    if args.list_checklist:
        list_checklist(conn, args.list_checklist)

    if args.update_affiliate:
        user_id, program_id, link = args.update_affiliate
        conn.execute("""
            UPDATE checklists SET affiliate_link=?, updated_at=datetime('now')
            WHERE (user_id=? OR user_id IN (SELECT id FROM users WHERE email=?))
              AND program_id=?
        """, (link, user_id, user_id, program_id))
        conn.commit()
        print(f"  OK Affiliate link updated for {program_id}")

    if args.update_status:
        user_id, program_id, status = args.update_status
        valid_statuses = ["not_started", "researching", "applied", "approved", "rejected", "not_eligible", "skipped"]
        if status not in valid_statuses:
            print(f"  ! Invalid status. Use one of: {valid_statuses}")
        else:
            applied_at = "datetime('now')" if status == "applied" else "NULL"
            approved_at = "datetime('now')" if status == "approved" else "NULL"
            conn.execute(f"""
                UPDATE checklists SET status=?, updated_at=datetime('now')
                WHERE (user_id=? OR user_id IN (SELECT id FROM users WHERE email=?))
                  AND program_id=?
            """, (status, user_id, user_id, program_id))
            conn.commit()
            print(f"  OK Status updated: {program_id} → {status}")

    # Summary
    prog_count = conn.execute("SELECT COUNT(*) FROM programs").fetchone()[0]
    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    checklist_count = conn.execute("SELECT COUNT(*) FROM checklists").fetchone()[0]
    print(f"\n  DB stats: {prog_count} programs | {user_count} users | {checklist_count} checklist items")
    conn.close()

if __name__ == "__main__":
    main()
