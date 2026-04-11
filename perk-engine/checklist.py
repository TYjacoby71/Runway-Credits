#!/usr/bin/env python3
"""
Runway Credits -- Interactive Checklist CLI (Phase 2)

Manages your personalized startup-credits checklist: view status, track
applications, store affiliate/referral links, and export to CSV.

Usage examples:
    # 1. Generate your checklist from a profile (runs matcher, saves to SQLite)
    python checklist.py generate --profile my_profile.json

    # 2. View your checklist
    python checklist.py view --user you@company.com

    # 3. Update application status for a program
    python checklist.py update --user you@company.com --program aws_activate --status applied

    # 4. Store your affiliate/referral link for a program
    python checklist.py set-link --user you@company.com --program brex --link https://brex.com/r/yourcode

    # 5. View all your stored affiliate links
    python checklist.py links --user you@company.com

    # 6. Export checklist to CSV (Google Sheets compatible)
    python checklist.py export --user you@company.com --output my_checklist.csv

Global options:
    --db   Path to SQLite DB (default: perk_engine.db in same directory)
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
DEFAULT_DB = BASE_DIR / "perk_engine.db"

VALID_STATUSES = [
    "not_started",
    "researching",
    "applied",
    "approved",
    "rejected",
    "not_eligible",
    "skipped",
]

STATUS_DISPLAY = {
    "not_started":  "[ ] Not started",
    "researching":  "[~] Researching",
    "applied":      "[>] Applied",
    "approved":     "[+] Approved",
    "rejected":     "[x] Rejected",
    "not_eligible": "[-] Not eligible",
    "skipped":      "[s] Skipped",
}


# -----------------------------------------------------------------------------
# DB helpers
# -----------------------------------------------------------------------------

def get_connection(db_path):
    import sqlite3
    if not Path(db_path).exists():
        print(f"  ERROR: DB not found at {db_path}")
        print(f"  Run: python setup_db.py  to create it first, or")
        print(f"       python checklist.py generate --profile <profile.json>")
        sys.exit(1)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def resolve_user_id(conn, user_ref):
    """Accept user id or email; return the canonical id row or None."""
    row = conn.execute(
        "SELECT id, name, email FROM users WHERE id=? OR email=?",
        (user_ref, user_ref)
    ).fetchone()
    return row


def require_user(conn, user_ref):
    row = resolve_user_id(conn, user_ref)
    if not row:
        print(f"  ERROR: No user found for '{user_ref}'")
        print(f"  Run: python checklist.py generate --profile <profile.json>  to create a profile first.")
        sys.exit(1)
    return row


# -----------------------------------------------------------------------------
# Command: generate
# -----------------------------------------------------------------------------

def cmd_generate(args):
    """Run matching engine against a profile and save/update the checklist."""
    import importlib.util

    profile_path = Path(args.profile)
    if not profile_path.exists():
        print(f"  ERROR: Profile file not found: {profile_path}")
        sys.exit(1)

    with open(profile_path) as f:
        profile = json.load(f)

    db_path = Path(args.db)

    # Bootstrap DB if it doesn't exist
    if not db_path.exists():
        print(f"  DB not found -- creating new DB at {db_path}")
        setup_mod = _load_module("setup_db", BASE_DIR / "setup_db.py")
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        setup_mod.apply_schema(conn)
        setup_mod.import_catalog(conn)
        conn.close()

    # Run matcher
    matcher_mod = _load_module("matcher", BASE_DIR / "matcher.py")
    catalog = matcher_mod.load_catalog()
    result = matcher_mod.run_matching(profile, catalog)

    # Print roadmap summary
    totals = result["totals"]
    print(f"\n  Matching complete:")
    print(f"    {totals['recommended_count']} programs recommended")
    print(f"    Realistic value:  ${totals['total_realistic_value_usd']:,}")
    print(f"    Max value:        ${totals['total_max_value_usd']:,}")
    if result.get("stacking_opportunities"):
        print(f"    Stacking combos:  {len(result['stacking_opportunities'])}")

    # Save checklist to DB
    setup_mod = _load_module("setup_db", BASE_DIR / "setup_db.py")
    setup_mod.save_checklist_from_result(str(db_path), profile, result)

    # Report user id
    user_ref = profile.get("email") or profile.get("name")
    if user_ref:
        print(f"\n  To view your checklist:")
        print(f"    python checklist.py view --user {user_ref}")
        print(f"\n  To export to CSV:")
        print(f"    python checklist.py export --user {user_ref}")


def _load_module(name, path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# -----------------------------------------------------------------------------
# Command: view
# -----------------------------------------------------------------------------

def cmd_view(args):
    """Display the user's checklist as a table."""
    conn = get_connection(args.db)
    user = require_user(conn, args.user)
    user_id = user["id"]

    # Build WHERE clause for optional status filter
    status_filter = ""
    params = [user_id]
    if args.status:
        status_filter = " AND c.status = ?"
        params.append(args.status)

    rows = conn.execute(f"""
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
        {status_filter}
        ORDER BY c.match_score DESC
    """, params).fetchall()

    if not rows:
        msg = f"No checklist items found for user '{user['email'] or user_id}'"
        if args.status:
            msg += f" with status '{args.status}'"
        print(f"\n  {msg}")
        conn.close()
        return

    name_str = user["name"] or user["email"] or user_id
    print(f"\n{'='*80}")
    print(f"  RUNWAY CREDITS CHECKLIST -- {name_str}")
    print(f"{'='*80}")

    # Summary counts
    all_rows = conn.execute("""
        SELECT c.status, COUNT(*) as cnt, SUM(p.realistic_credit_usd) as val
        FROM checklists c JOIN programs p ON p.id=c.program_id
        WHERE c.user_id=? AND c.matched=1
        GROUP BY c.status
    """, (user_id,)).fetchall()

    status_counts = {r["status"]: (r["cnt"], r["val"] or 0) for r in all_rows}
    total_programs = sum(v[0] for v in status_counts.values())
    total_value = sum(v[1] for v in status_counts.values())
    approved_value = status_counts.get("approved", (0, 0))[1]

    print(f"\n  Total: {total_programs} programs | ${total_value:,} potential value | ${approved_value:,} approved so far")
    print(f"\n  Status breakdown:")
    for status in VALID_STATUSES:
        if status in status_counts:
            cnt, val = status_counts[status]
            print(f"    {STATUS_DISPLAY[status]:<22}  {cnt:>2} program(s)   ${val:>10,}")

    # Main table
    print(f"\n{'-'*80}")
    header = f"  {'#':>3}  {'Program':<35} {'Status':<16} {'Value':>8}  {'Applied':>10}"
    print(header)
    print(f"{'-'*80}")

    for i, r in enumerate(rows, 1):
        val_str = f"${r['realistic_credit_usd']:,}" if r["realistic_credit_usd"] else "  --"
        applied_str = _fmt_date(r["applied_at"]) if r["applied_at"] else "--"
        status_str = STATUS_DISPLAY.get(r["status"], r["status"])

        # Truncate long names
        prog_name = r["name"]
        if len(prog_name) > 34:
            prog_name = prog_name[:31] + "..."

        print(f"  {i:>3}  {prog_name:<35} {status_str:<16} {val_str:>8}  {applied_str:>10}")

        # Show affiliate link if present (or if --show-links flag)
        if r["affiliate_link"] or args.show_links:
            if r["affiliate_link"]:
                link_label = "  Affiliate link"
                print(f"         {link_label}: {r['affiliate_link']}")
            elif args.show_links:
                print(f"         Affiliate link: (not set)  ->  set with: python checklist.py set-link --user {user['email'] or user_id} --program {r['program_id']} --link <url>")

        # Show application URL for not_started/researching
        if args.show_urls and r["application_url"]:
            print(f"         Apply at: {r['application_url']}")

        # Show stacking notes
        if args.show_stacking and r["stacking_notes"]:
            print(f"         Stack:    {r['stacking_notes']}")

        # Show user notes
        if r["user_notes"]:
            print(f"         Notes:    {r['user_notes']}")

    print(f"{'-'*80}\n")

    # Next action hints
    not_started = status_counts.get("not_started", (0, 0))[0]
    if not_started:
        print(f"  Next: {not_started} program(s) not yet started. Begin with the top-ranked item above.")
        top = next((r for r in rows if r["status"] == "not_started"), None)
        if top:
            print(f"        -> {top['name']}")
            if top["application_url"]:
                print(f"          Apply: {top['application_url']}")

    print(f"\n  Quick commands:")
    uid = user["email"] or user_id
    print(f"    Update status:   python checklist.py update --user {uid} --program <id> --status applied")
    print(f"    Add aff. link:   python checklist.py set-link --user {uid} --program <id> --link <url>")
    print(f"    View aff. links: python checklist.py links --user {uid}")
    print(f"    Export CSV:      python checklist.py export --user {uid}\n")

    conn.close()


def _fmt_date(dt_str):
    if not dt_str:
        return "--"
    try:
        return dt_str[:10]  # YYYY-MM-DD
    except Exception:
        return str(dt_str)


# -----------------------------------------------------------------------------
# Command: update
# -----------------------------------------------------------------------------

def cmd_update(args):
    """Update the application status for a checklist item."""
    status = args.status.lower().strip()
    if status not in VALID_STATUSES:
        print(f"  ERROR: Invalid status '{status}'")
        print(f"  Valid values: {', '.join(VALID_STATUSES)}")
        sys.exit(1)

    conn = get_connection(args.db)
    user = require_user(conn, args.user)
    user_id = user["id"]

    # Verify the program exists in the user's checklist
    existing = conn.execute(
        "SELECT id, status FROM checklists WHERE user_id=? AND program_id=?",
        (user_id, args.program)
    ).fetchone()

    if not existing:
        # Check if program exists at all
        prog = conn.execute("SELECT name FROM programs WHERE id=?", (args.program,)).fetchone()
        if prog:
            print(f"  ERROR: '{args.program}' is not in your checklist.")
            print(f"  (It exists in the catalog as '{prog['name']}' but wasn't matched to your profile.)")
        else:
            print(f"  ERROR: Program '{args.program}' not found. Check the program ID.")
            _show_program_ids(conn)
        conn.close()
        sys.exit(1)

    old_status = existing["status"]

    # Build timestamp updates
    now = datetime.utcnow().isoformat()
    applied_at_sql = ""
    approved_at_sql = ""
    if status == "applied" and old_status not in ("applied", "approved"):
        applied_at_sql = f", applied_at='{now}'"
    if status == "approved":
        approved_at_sql = f", approved_at='{now}'"
        if old_status not in ("applied",):
            applied_at_sql = f", applied_at=COALESCE(applied_at, '{now}')"

    conn.execute(f"""
        UPDATE checklists
        SET status=?, updated_at=datetime('now') {applied_at_sql} {approved_at_sql}
        WHERE user_id=? AND program_id=?
    """, (status, user_id, args.program))
    conn.commit()

    prog_name = conn.execute("SELECT name FROM programs WHERE id=?", (args.program,)).fetchone()["name"]
    print(f"\n  OK  {prog_name}")
    print(f"      {STATUS_DISPLAY.get(old_status, old_status)}  ->  {STATUS_DISPLAY.get(status, status)}")

    if status == "applied":
        print(f"\n  Tip: When you get a decision, update again:")
        print(f"       python checklist.py update --user {args.user} --program {args.program} --status approved")
        print(f"       python checklist.py update --user {args.user} --program {args.program} --status rejected")
    elif status == "approved":
        print(f"\n  Great! Don't forget to store your affiliate/referral link:")
        print(f"       python checklist.py set-link --user {args.user} --program {args.program} --link <your-referral-url>")

    conn.close()


def _show_program_ids(conn):
    rows = conn.execute("SELECT id, name FROM programs ORDER BY name LIMIT 20").fetchall()
    if rows:
        print(f"\n  Available program IDs (first 20):")
        for r in rows:
            print(f"    {r['id']:<35} {r['name']}")


# -----------------------------------------------------------------------------
# Command: set-link
# -----------------------------------------------------------------------------

def cmd_set_link(args):
    """Store or update the affiliate/referral link for a program."""
    conn = get_connection(args.db)
    user = require_user(conn, args.user)
    user_id = user["id"]

    existing = conn.execute(
        "SELECT id, affiliate_link FROM checklists WHERE user_id=? AND program_id=?",
        (user_id, args.program)
    ).fetchone()

    if not existing:
        print(f"  ERROR: '{args.program}' is not in your checklist.")
        conn.close()
        sys.exit(1)

    old_link = existing["affiliate_link"]

    conn.execute("""
        UPDATE checklists
        SET affiliate_link=?, affiliate_notes=?, updated_at=datetime('now')
        WHERE user_id=? AND program_id=?
    """, (args.link, args.notes or None, user_id, args.program))
    conn.commit()

    prog_name = conn.execute("SELECT name FROM programs WHERE id=?", (args.program,)).fetchone()["name"]
    print(f"\n  OK  Affiliate link saved for {prog_name}")
    if old_link and old_link != args.link:
        print(f"      Previous: {old_link}")
    print(f"      Current:  {args.link}")
    if args.notes:
        print(f"      Notes:    {args.notes}")

    print(f"\n  View all your links: python checklist.py links --user {args.user}")
    conn.close()


# -----------------------------------------------------------------------------
# Command: links
# -----------------------------------------------------------------------------

def cmd_links(args):
    """Display all affiliate/referral links stored for the user."""
    conn = get_connection(args.db)
    user = require_user(conn, args.user)
    user_id = user["id"]

    rows = conn.execute("""
        SELECT
            c.program_id, p.name, p.provider, p.category,
            c.affiliate_link, c.affiliate_notes,
            c.status, c.credit_amount_received,
            p.realistic_credit_usd
        FROM checklists c
        JOIN programs p ON p.id = c.program_id
        WHERE c.user_id = ? AND c.matched = 1
        ORDER BY
            CASE WHEN c.affiliate_link IS NOT NULL AND c.affiliate_link != '' THEN 0 ELSE 1 END,
            c.match_score DESC
    """, (user_id,)).fetchall()

    name_str = user["name"] or user["email"] or user_id
    print(f"\n{'='*80}")
    print(f"  AFFILIATE & REFERRAL LINKS -- {name_str}")
    print(f"{'='*80}")

    with_links = [r for r in rows if r["affiliate_link"]]
    without_links = [r for r in rows if not r["affiliate_link"]]

    if with_links:
        print(f"\n  STORED LINKS ({len(with_links)} program(s)):")
        print(f"  {'-'*76}")
        for r in with_links:
            status_icon = "+" if r["status"] == "approved" else (">" if r["status"] == "applied" else " ")
            earned = f"  | Earned: ${r['credit_amount_received']:,}" if r["credit_amount_received"] else ""
            print(f"\n  [{status_icon}] {r['name']}")
            print(f"      Link:     {r['affiliate_link']}")
            if r["affiliate_notes"]:
                print(f"      Notes:    {r['affiliate_notes']}")
            print(f"      Status:   {STATUS_DISPLAY.get(r['status'], r['status'])}{earned}")
    else:
        print(f"\n  No affiliate links stored yet.")

    if without_links:
        print(f"\n  PROGRAMS WITHOUT LINKS ({len(without_links)} program(s)):")
        print(f"  (Add your referral link once you sign up for a program's affiliate program)")
        print(f"  {'-'*76}")
        uid = user["email"] or user_id
        for r in without_links:
            prog_name = r["name"]
            if len(prog_name) > 38:
                prog_name = prog_name[:35] + "..."
            val_str = f"${r['realistic_credit_usd']:,}" if r["realistic_credit_usd"] else "--"
            print(f"  {prog_name:<40} {val_str:>8}  ->  add: python checklist.py set-link --user {uid} --program {r['program_id']} --link <url>")

    print(f"\n{'='*80}\n")
    conn.close()


# -----------------------------------------------------------------------------
# Command: export
# -----------------------------------------------------------------------------

def cmd_export(args):
    """Export checklist to CSV (Google Sheets compatible)."""
    conn = get_connection(args.db)
    user = require_user(conn, args.user)
    user_id = user["id"]

    rows = conn.execute("""
        SELECT
            c.program_id       AS program_id,
            p.name             AS program_name,
            p.provider         AS provider,
            p.category         AS category,
            p.credit_min_usd   AS credit_min_usd,
            p.credit_max_usd   AS credit_max_usd,
            p.realistic_credit_usd AS realistic_credit_usd,
            p.duration_months  AS duration_months,
            p.application_url  AS application_url,
            p.approval_time_days AS approval_time_days,
            p.stacking_notes   AS stacking_notes,
            c.status           AS status,
            c.match_score      AS match_score,
            c.match_notes      AS match_notes,
            c.applied_at       AS applied_at,
            c.approved_at      AS approved_at,
            c.credit_amount_received AS credit_amount_received,
            c.affiliate_link   AS affiliate_link,
            c.affiliate_notes  AS affiliate_notes,
            c.user_notes       AS user_notes,
            c.reminder_date    AS reminder_date,
            c.updated_at       AS updated_at
        FROM checklists c
        JOIN programs p ON p.id = c.program_id
        WHERE c.user_id = ? AND c.matched = 1
        ORDER BY c.match_score DESC
    """, (user_id,)).fetchall()

    if not rows:
        print(f"\n  No checklist found for user '{user['email'] or user_id}'")
        conn.close()
        return

    # Determine output path
    if args.output:
        out_path = Path(args.output)
    else:
        name_part = (user["email"] or user_id or "user").replace("@", "_").replace(".", "_")
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        out_path = BASE_DIR / f"checklist_{name_part}_{timestamp}.csv"

    # CSV columns (Google Sheets friendly names)
    fieldnames = [
        "program_id",
        "program_name",
        "provider",
        "category",
        "status",
        "realistic_credit_usd",
        "credit_range",
        "duration_months",
        "approval_time_days",
        "match_score",
        "application_url",
        "affiliate_link",
        "affiliate_notes",
        "applied_at",
        "approved_at",
        "credit_amount_received",
        "stacking_notes",
        "match_notes",
        "user_notes",
        "reminder_date",
        "last_updated",
    ]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            credit_range = ""
            if r["credit_min_usd"] or r["credit_max_usd"]:
                credit_range = f"${r['credit_min_usd']:,}-${r['credit_max_usd']:,}"
            writer.writerow({
                "program_id":            r["program_id"],
                "program_name":          r["program_name"],
                "provider":              r["provider"],
                "category":              r["category"],
                "status":                r["status"],
                "realistic_credit_usd":  r["realistic_credit_usd"] or "",
                "credit_range":          credit_range,
                "duration_months":       r["duration_months"] or "ongoing",
                "approval_time_days":    r["approval_time_days"] or "",
                "match_score":           round(r["match_score"], 1) if r["match_score"] else "",
                "application_url":       r["application_url"] or "",
                "affiliate_link":        r["affiliate_link"] or "",
                "affiliate_notes":       r["affiliate_notes"] or "",
                "applied_at":            _fmt_date(r["applied_at"]),
                "approved_at":           _fmt_date(r["approved_at"]),
                "credit_amount_received": r["credit_amount_received"] or "",
                "stacking_notes":        r["stacking_notes"] or "",
                "match_notes":           r["match_notes"] or "",
                "user_notes":            r["user_notes"] or "",
                "reminder_date":         r["reminder_date"] or "",
                "last_updated":          _fmt_date(r["updated_at"]),
            })

    total_value = sum(r["realistic_credit_usd"] or 0 for r in rows)
    print(f"\n  OK  Exported {len(rows)} programs to: {out_path}")
    print(f"      Total potential value: ${total_value:,}")
    print(f"\n  Import to Google Sheets: File -> Import -> Upload -> {out_path.name}\n")

    conn.close()


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        description="Runway Credits -- Interactive Checklist CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--db", default=str(DEFAULT_DB), help=f"SQLite DB path (default: {DEFAULT_DB})")

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # generate
    p_gen = sub.add_parser("generate", help="Run matcher and create/update checklist from a profile JSON")
    p_gen.add_argument("--profile", "-p", required=True, help="Path to user profile JSON (from intake.py)")

    # view
    p_view = sub.add_parser("view", help="Display your checklist as a table")
    p_view.add_argument("--user", "-u", required=True, help="User ID or email")
    p_view.add_argument("--status", "-s", choices=VALID_STATUSES, help="Filter by status")
    p_view.add_argument("--show-links", action="store_true", help="Show affiliate link column for all items")
    p_view.add_argument("--show-urls", action="store_true", help="Show application URLs")
    p_view.add_argument("--show-stacking", action="store_true", help="Show stacking notes")

    # update
    p_upd = sub.add_parser("update", help="Update application status for a program")
    p_upd.add_argument("--user", "-u", required=True, help="User ID or email")
    p_upd.add_argument("--program", "-p", required=True, help="Program ID (e.g. aws_activate)")
    p_upd.add_argument("--status", "-s", required=True, choices=VALID_STATUSES,
                        help=f"New status. One of: {', '.join(VALID_STATUSES)}")

    # set-link
    p_link = sub.add_parser("set-link", help="Store your affiliate/referral link for a program")
    p_link.add_argument("--user", "-u", required=True, help="User ID or email")
    p_link.add_argument("--program", "-p", required=True, help="Program ID (e.g. brex)")
    p_link.add_argument("--link", "-l", required=True, help="Your affiliate/referral URL")
    p_link.add_argument("--notes", "-n", help="Optional notes about this affiliate program")

    # links
    p_links = sub.add_parser("links", help="View all your stored affiliate/referral links")
    p_links.add_argument("--user", "-u", required=True, help="User ID or email")

    # export
    p_exp = sub.add_parser("export", help="Export checklist to CSV (Google Sheets compatible)")
    p_exp.add_argument("--user", "-u", required=True, help="User ID or email")
    p_exp.add_argument("--output", "-o", help="Output CSV file path (default: auto-named in perk-engine/)")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "generate": cmd_generate,
        "view":     cmd_view,
        "update":   cmd_update,
        "set-link": cmd_set_link,
        "links":    cmd_links,
        "export":   cmd_export,
    }

    fn = dispatch.get(args.command)
    if fn:
        fn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
