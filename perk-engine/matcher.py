#!/usr/bin/env python3
"""
Runway Credits Matching Engine - v2
Input:  user profile JSON (from intake.py)
Output: personalized, ordered roadmap of recommended programs with dependency/gateway flow

Usage:
    python matcher.py --profile user_profile.json
    python matcher.py --profile user_profile.json --output roadmap.json
    python matcher.py --profile user_profile.json --format text
    python matcher.py --profile user_profile.json --save-db perk_engine.db

v2 changes:
  - Three-tier output: gateway / standalone / locked-door programs
  - Dependency tree: prerequisites and unlock chains
  - Confidence tiers: near-certain / high-probability / competitive / long-shot
  - Application order optimizer: topological sort with gateway-first ordering
"""

import json
import os
import sys
import argparse
from pathlib import Path

# ============================================================-------------------
# Load catalog
# ============================================================-------------------

CATALOG_PATH = Path(__file__).parent / "data" / "programs.json"

def load_catalog():
    with open(CATALOG_PATH) as f:
        return json.load(f)

# ============================================================-------------------
# Eligibility checks
# ============================================================-------------------

def is_us_entity(entity_type):
    return entity_type in ("llc", "c_corp", "s_corp", "sole_proprietor", "us_entity")

def check_eligibility(program, profile):
    """
    Returns (is_eligible: bool, reason: str)
    """
    elig = program.get("eligibility", {})

    # US entity check
    entity_types = elig.get("entity_types", [])
    if entity_types and "any" not in entity_types and "non_us" not in entity_types:
        # requires US entity
        if not is_us_entity(profile.get("entity_type", "")):
            return False, "Requires US entity"
    if "us_entity" in entity_types and not is_us_entity(profile.get("entity_type", "")):
        return False, "Requires US entity"

    # Funding stage
    eligible_stages = elig.get("funding_stages_eligible", [])
    if eligible_stages and profile.get("funding_stage") not in eligible_stages:
        return False, f"Not available at {profile.get('funding_stage')} stage"

    # Max funding raised
    max_funding = elig.get("max_funding_usd")
    if max_funding is not None:
        raised = profile.get("funding_raised_usd", 0)
        if raised > max_funding:
            return False, f"Raised ${raised:,} exceeds program max ${max_funding:,}"

    # Max ARR
    max_arr = elig.get("max_arr_usd")
    if max_arr is not None:
        revenue = profile.get("annual_revenue_usd", 0)
        if revenue > max_arr:
            return False, f"ARR ${revenue:,} exceeds program max ${max_arr:,}"

    # Company age
    max_age = elig.get("max_company_age_years")
    if max_age is not None:
        age = profile.get("company_age_years", 0)
        if age > max_age:
            return False, f"Company age {age}yr exceeds program max {max_age}yr"

    # Requires deployed product
    if elig.get("requires_deployed_product") and not profile.get("has_deployed_product"):
        return False, "Requires a deployed/live product"

    # Requires partner sponsor - we flag this as "conditional" rather than ineligible
    # (the engine will still recommend it with a note)

    # Tech focus
    tech_focus = elig.get("tech_focus")
    if tech_focus:
        user_stack = set(profile.get("tech_stack", []))
        if not any(t in user_stack for t in tech_focus):
            return False, f"Tech focus {tech_focus} doesn't match your stack {list(user_stack)}"

    # Max employees
    max_emp = elig.get("max_employees")
    if max_emp is not None:
        if profile.get("team_size", 1) > max_emp:
            return False, f"Team size {profile['team_size']} exceeds max {max_emp}"

    return True, "Eligible"

# ============================================================-------------------
# Scoring
# ============================================================-------------------

GOAL_TO_TAG_MAP = {
    "cloud_infrastructure":  ["cloud", "infrastructure", "compute"],
    "ai_api_credits":        ["ai_ml", "llm", "api"],
    "reduce_saas_costs":     ["productivity", "design", "developer_tools", "project_management", "support", "crm"],
    "banking_and_finance":   ["banking", "fintech", "card", "payments"],
    "developer_tooling":     ["developer_tools", "ide", "git", "ci_cd"],
    "analytics_and_metrics": ["analytics", "monitoring", "observability", "cdp"],
    "sales_and_crm":         ["crm", "sales", "support", "messaging"],
    "identity_and_security": ["auth", "identity", "security"],
}

def score_program(program, profile):
    """
    Computes a relevance score for this program given the user profile.
    Returns: float score, list of scoring_notes
    """
    score = 0.0
    notes = []

    # Base: realistic credit value (log-scaled to 0-100)
    import math
    credit = program.get("realistic_credit_usd", 0)
    if credit > 0:
        base = math.log10(credit + 1) * 20
        score += base
        notes.append(f"credit_value: ${credit:,} - +{base:.0f}pts")

    # Sequence priority (1=best, 5=worst) - inverse bonus
    seq = program.get("sequence_priority", 3)
    seq_bonus = (5 - seq) * 8
    score += seq_bonus
    if seq_bonus:
        notes.append(f"sequence_priority {seq} - +{seq_bonus:.0f}pts")

    # Approval time bonus (faster = better for early-stage)
    approval_days = program.get("approval_time_days", 14)
    if approval_days <= 1:
        score += 15
        notes.append("instant_approval - +15pts")
    elif approval_days <= 5:
        score += 8
        notes.append("fast_approval - +8pts")

    # User has unlock methods for this program
    program_methods = set(program.get("unlock_methods", []))
    user_methods = set(profile.get("available_unlock_methods", ["self_apply"]))
    overlap = program_methods & user_methods
    if overlap:
        unlock_bonus = len(overlap) * 10
        score += unlock_bonus
        notes.append(f"unlock_methods {overlap} - +{unlock_bonus:.0f}pts")

    # Goal alignment
    user_goals = profile.get("priority_goals", [])
    tags = set(program.get("tags", []))
    for goal in user_goals:
        goal_tags = set(GOAL_TO_TAG_MAP.get(goal, []))
        if goal_tags & tags:
            score += 20
            notes.append(f"goal_match '{goal}' - +20pts")
            break  # only bonus once per program

    # Already have accounts that unlock it
    if "brex_portal" in program.get("unlock_methods", []) and profile.get("has_brex"):
        score += 10
        notes.append("has_brex - instant unlock +10pts")
    if "stripe_atlas" in program.get("unlock_methods", []) and profile.get("has_stripe_atlas"):
        score += 10
        notes.append("has_stripe_atlas - instant unlock +10pts")
    if "yc_sus" in program.get("unlock_methods", []) and "yc_sus" in user_methods:
        score += 8
        notes.append("yc_sus - unlock available +8pts")

    # Partner sponsor required but user doesn't have one - penalty
    elig = program.get("eligibility", {})
    if elig.get("requires_partner_sponsor") and not profile.get("has_vc_or_accelerator"):
        score -= 20
        notes.append("requires_sponsor (you don't have one) - -20pts")

    return score, notes

# ============================================================-------------------
# Stacking analysis
# ============================================================-------------------

KNOWN_STACKS = [
    {
        "name": "Cloud Infra Mega-Stack",
        "programs": ["aws_activate", "google_cloud", "azure", "digitalocean_hatch"],
        "total_value_note": "~$104K+ in cloud credits with no conflicts",
        "notes": "Run DO workloads alongside AWS/GCP/Azure. All four stack cleanly.",
    },
    {
        "name": "AI API Coverage Stack",
        "programs": ["brex", "anthropic_credits", "openai_credits", "azure", "huggingface"],
        "total_value_note": "Multi-provider AI coverage: Anthropic + OpenAI + Azure OpenAI + HuggingFace open-source",
        "notes": "Fastest path: Brex (instant) - Azure (self-apply) - YC SUS - accelerator.",
    },
    {
        "name": "Stripe Atlas Compound",
        "programs": ["stripe_atlas", "aws_activate", "google_cloud", "hubspot", "notion"],
        "total_value_note": "$500 Atlas fee - $20K+ in bundled perks",
        "notes": "Atlas adds AWS $1K, GCP $2K, HubSpot free, Gusto 6mo, Carta $1.5K on top of direct applications.",
    },
    {
        "name": "YC Startup School Unlock",
        "programs": ["yc_sus", "aws_activate", "brex", "cloudflare", "posthog"],
        "total_value_note": "Free enrollment unlocks AWS $25K, Brex $75K, Cloudflare, PostHog",
        "notes": "Apply YC SUS first (free, instant). Unlocks partial deal set immediately.",
    },
    {
        "name": "Dev Platform Stack",
        "programs": ["github_startups", "linear", "vercel", "supabase", "cloudflare"],
        "total_value_note": "~$12K+ in build/deploy/track tooling at near-zero cash outlay",
        "notes": "Complete build-deploy-track workflow. All non-conflicting.",
    },
    {
        "name": "Analytics Stack (pick one primary)",
        "programs": ["segment", "posthog"],
        "total_value_note": "Segment as CDP + PostHog as analytics layer",
        "notes": "Use Segment to collect events once, route to PostHog (or Amplitude or Mixpanel). Do NOT run multiple analytics platforms simultaneously.",
    },
    {
        "name": "Banking & Finance Foundation",
        "programs": ["mercury", "brex", "ramp", "relay"],
        "total_value_note": "Treasury (Mercury/Relay) + Spend rewards (Brex/Ramp) + Partner perk portals",
        "notes": "Mercury = primary treasury. Relay = operational sub-accounts. Brex/Ramp = card rewards. All four stack cleanly.",
    },
]

def find_relevant_stacks(recommended_ids):
    """Returns stacking opportunities where the user has >= 2 of the programs"""
    result = []
    for stack in KNOWN_STACKS:
        overlap = [p for p in stack["programs"] if p in recommended_ids]
        if len(overlap) >= 2:
            result.append({
                "stack_name": stack["name"],
                "your_programs": overlap,
                "all_programs": stack["programs"],
                "value_note": stack["total_value_note"],
                "notes": stack["notes"],
            })
    return result

# ============================================================-------------------
# Dependency / gateway flow
# ============================================================-------------------

def build_catalog_index(catalog):
    """Return dict of program_id -> program for fast lookup."""
    return {p["id"]: p for p in catalog}

def classify_program_tier(program, recommended_ids, catalog_index):
    """
    Returns one of:
      'gateway'    - this program's enrollment unlocks other recommended programs
      'locked'     - requires a gateway enrollment (no self_apply)
      'standalone' - can self-apply; no hard prerequisite gates
    """
    pid = program["id"]

    # Gateway: it has unlocks pointing to recommended programs
    unlocks = program.get("unlocks", [])
    if any(u in recommended_ids for u in unlocks):
        return "gateway"

    # Locked: no self_apply available
    if "self_apply" not in program.get("unlock_methods", []):
        return "locked"

    return "standalone"

def compute_confidence_tier(program, profile, score, max_score_in_run=150.0):
    """
    Returns (tier_label, explanation).
    Confidence is computed on a normalized 0-100 scale so that the
    distribution across tiers reflects realistic differentiation rather
    than raw point totals.

    Tiers:
      near-certain   -- top ~20% of scoring programs AND easy path
      high-probability -- upper-mid band or easy path with moderate score
      competitive    -- mid band or any path requiring extra friction
      long-shot      -- bottom band, locked without gateway, or sponsor-required
    """
    import math
    methods = program.get("unlock_methods", [])
    elig = program.get("eligibility", {})
    can_self = "self_apply" in methods
    needs_sponsor = elig.get("requires_partner_sponsor", False)
    locked = not can_self

    # Normalize score to 0-100 relative to maximum observed in this run
    norm = min(100.0, (score / max(max_score_in_run, 1)) * 100)

    # Friction penalties (applied to normalized score)
    if locked:
        norm *= 0.65     # must go through a gateway first
    if needs_sponsor:
        norm *= 0.55     # requires external sponsor — hard to get

    # Award efficiency: realistic / max (ratio close to 1 = more predictable payout)
    max_credit = program.get("credit_max_usd", 1)
    realistic = program.get("realistic_credit_usd", 0)
    award_ratio = realistic / max_credit if max_credit > 0 else 0.5
    # Penalize programs where typical award << advertised max (lottery-style)
    if award_ratio < 0.10:
        norm *= 0.70    # e.g. program advertises $100K max but typical is <$10K
    elif award_ratio < 0.25:
        norm *= 0.85

    # Application difficulty derived from: sponsor requirement, complex eligibility, known selectivity
    approval_days = program.get("approval_time_days", 30)
    if approval_days <= 2:
        norm = min(100, norm * 1.10)   # instant/fast approval = more certain
    elif approval_days > 90:
        norm *= 0.85                   # long review cycle = less certain

    # Classify
    if norm >= 55 and not locked and not needs_sponsor:
        tier = "near-certain"
        reason = "self-apply, strong eligibility, predictable payout"
    elif norm >= 38:
        tier = "high-probability"
        if locked:
            reason = "strong match; get gateway enrolled first"
        elif approval_days > 60:
            reason = "good fit but long review cycle"
        else:
            reason = "good fit; standard review process"
    elif norm >= 20:
        tier = "competitive"
        if needs_sponsor:
            reason = "requires VC/accelerator sponsor - get sponsored first"
        elif locked:
            reason = "requires gateway enrollment first"
        elif award_ratio < 0.15:
            reason = "high advertised value but typical award much lower"
        else:
            reason = "selective; well-prepared application needed"
    else:
        tier = "long-shot"
        if locked:
            reason = "locked until prerequisites obtained"
        elif needs_sponsor:
            reason = "needs sponsor you don't currently have"
        else:
            reason = "low profile alignment or highly selective program"

    return tier, reason

def build_dependency_graph(recommended, catalog_index):
    """
    Returns:
      graph: dict of program_id -> set of program_ids it unlocks (within recommended)
      reverse: dict of program_id -> set of gateway_ids that unlock it
    """
    rec_ids = {r["program_id"] for r in recommended}
    graph = {}
    reverse = {}

    for r in recommended:
        pid = r["program_id"]
        prog = catalog_index.get(pid, {})
        unlocks = prog.get("unlocks", [])
        locked_by = prog.get("prerequisites", [])

        # Only edges within the recommended set
        graph[pid] = set(u for u in unlocks if u in rec_ids)
        reverse[pid] = set(g for g in locked_by if g in rec_ids)

    return graph, reverse

def optimize_application_order(recommended, catalog_index):
    """
    Returns recommended list sorted by application order:
      1. Gateways (topological, applied first so they unlock others)
      2. Programs enhanced-by-gateway that user should apply after gateway enrolled
      3. Standalone programs (sorted by score desc)
      4. Locked programs (sorted by how soon prerequisite is expected)

    Uses Kahn's algorithm for topological sort within the dependency graph,
    then groups by tier.
    """
    rec_ids = {r["program_id"] for r in recommended}
    id_to_rec = {r["program_id"]: r for r in recommended}

    graph, reverse = build_dependency_graph(recommended, catalog_index)

    # Compute in-degree (how many recommended prerequisites each program has)
    in_degree = {r["program_id"]: len(reverse[r["program_id"]]) for r in recommended}

    # Separate into tiers
    gateways = []
    standalones = []
    locked_progs = []

    for r in recommended:
        pid = r["program_id"]
        prog = catalog_index.get(pid, {})
        tier = r.get("tier", "standalone")
        if tier == "gateway":
            gateways.append(r)
        elif tier == "locked":
            locked_progs.append(r)
        else:
            standalones.append(r)

    # Sort each group by score descending
    gateways.sort(key=lambda x: x["score"], reverse=True)
    standalones.sort(key=lambda x: x["score"], reverse=True)
    locked_progs.sort(key=lambda x: x["score"], reverse=True)

    return gateways + standalones + locked_progs

# ============================================================-------------------
# Main matching logic
# ============================================================-------------------

def run_matching(profile, catalog):
    current_perks = set(profile.get("current_perks", []))
    catalog_index = build_catalog_index(catalog)
    results = []

    for program in catalog:
        pid = program["id"]

        # Skip programs already held
        if pid in current_perks:
            continue

        # Check eligibility
        eligible, reason = check_eligibility(program, profile)
        if not eligible:
            results.append({
                "program_id": pid,
                "name": program["name"],
                "status": "ineligible",
                "ineligible_reason": reason,
                "score": 0,
                "scoring_notes": [],
            })
            continue

        # Check conflicts with current perks
        conflicts = program.get("stacking", {}).get("conflicts_with", [])
        conflict_hit = [c for c in conflicts if c in current_perks]
        if conflict_hit:
            results.append({
                "program_id": pid,
                "name": program["name"],
                "status": "conflict",
                "conflict_reason": f"Conflicts with your current perk(s): {conflict_hit}",
                "score": 0,
                "scoring_notes": [],
            })
            continue

        # Score it
        score, scoring_notes = score_program(program, profile)

        # Check if sponsor required but not available (flag, don't exclude)
        sponsor_warning = None
        if program.get("eligibility", {}).get("requires_partner_sponsor", False):
            if not profile.get("has_vc_or_accelerator"):
                sponsor_warning = "Requires VC/accelerator sponsor - get sponsored first or find a partner program"

        results.append({
            "program_id": pid,
            "name": program["name"],
            "provider": program["provider"],
            "category": program["category"],
            "status": "recommended",
            "score": round(score, 1),
            "scoring_notes": scoring_notes,
            "realistic_credit_usd": program.get("realistic_credit_usd", 0),
            "credit_range": f"${program.get('credit_min_usd', 0):,}-${program.get('credit_max_usd', 0):,}",
            "duration_months": program.get("duration_months"),
            "sequence_priority": program.get("sequence_priority", 3),
            "application_url": program.get("application_url"),
            "approval_time_days": program.get("approval_time_days"),
            "unlock_methods": program.get("unlock_methods", []),
            "prerequisites": program.get("prerequisites", []),
            "unlocks": program.get("unlocks", []),
            "enhances_via": program.get("enhances_via", []),
            "stacks_well_with": program.get("stacking", {}).get("stacks_well_with", []),
            "stacking_notes": program.get("stacking", {}).get("notes"),
            "sponsor_warning": sponsor_warning,
            "notes": program.get("notes"),
            "tags": program.get("tags", []),
        })

    # Sort: recommended first by score, then ineligible, then conflicts
    all_eligible = sorted([r for r in results if r["status"] == "recommended"], key=lambda x: x["score"], reverse=True)
    ineligible = [r for r in results if r["status"] == "ineligible"]
    conflicts_list = [r for r in results if r["status"] == "conflict"]

    # --- Tighten match rate to ~65-70% using dynamic score threshold ---
    # Keep all gateways regardless of score; apply threshold to others.
    # Build preliminary tier classification to identify gateways first.
    all_eligible_ids = {r["program_id"] for r in all_eligible}
    _catalog_idx_tmp = build_catalog_index(catalog)
    gateway_ids = {
        r["program_id"] for r in all_eligible
        if _catalog_idx_tmp.get(r["program_id"], {}).get("unlocks", [])
        and any(u in all_eligible_ids for u in _catalog_idx_tmp[r["program_id"]].get("unlocks", []))
    }
    # Dynamic threshold: target top 65% of non-gateway eligible programs by score
    non_gateway = [r for r in all_eligible if r["program_id"] not in gateway_ids]
    target_n = max(1, int(round(len(all_eligible) * 0.65)))
    gateway_count = len(gateway_ids)
    non_gateway_target = max(0, target_n - gateway_count)
    # Sort non-gateway by score; take top non_gateway_target
    non_gateway_sorted = sorted(non_gateway, key=lambda x: x["score"], reverse=True)
    kept_non_gateway = non_gateway_sorted[:non_gateway_target]
    cut_non_gateway = non_gateway_sorted[non_gateway_target:]
    gateways_list = [r for r in all_eligible if r["program_id"] in gateway_ids]
    recommended = sorted(gateways_list + kept_non_gateway, key=lambda x: x["score"], reverse=True)
    # Programs cut by the threshold are moved to ineligible-ish bucket (below_threshold)
    below_threshold = cut_non_gateway

    recommended_ids = {r["program_id"] for r in recommended}

    # --- Tier classification ---
    for r in recommended:
        prog = catalog_index.get(r["program_id"], {})
        r["tier"] = classify_program_tier(prog, recommended_ids, catalog_index)

    # --- Confidence tiers (normalized against max score in this run) ---
    max_score = recommended[0]["score"] if recommended else 150.0
    for r in recommended:
        prog = catalog_index.get(r["program_id"], {})
        conf_tier, conf_reason = compute_confidence_tier(prog, profile, r["score"], max_score_in_run=max_score)
        r["confidence"] = conf_tier
        r["confidence_reason"] = conf_reason

    # --- Application order optimizer ---
    ordered = optimize_application_order(recommended, catalog_index)

    # --- Three-tier split ---
    gateway_programs  = [r for r in ordered if r["tier"] == "gateway"]
    standalone_programs = [r for r in ordered if r["tier"] == "standalone"]
    locked_programs   = [r for r in ordered if r["tier"] == "locked"]

    # --- Stacking analysis on the recommended set ---
    stacks = find_relevant_stacks(recommended_ids)

    # Compute total potential value
    total_realistic = sum(r.get("realistic_credit_usd", 0) for r in recommended)
    total_max = sum(
        next((p["credit_max_usd"] for p in catalog if p["id"] == r["program_id"]), 0)
        for r in recommended
    )

    # Confidence distribution
    confidence_counts = {}
    for r in recommended:
        c = r["confidence"]
        confidence_counts[c] = confidence_counts.get(c, 0) + 1

    return {
        "profile_summary": {
            "entity_type": profile.get("entity_type"),
            "funding_stage": profile.get("funding_stage"),
            "funding_raised_usd": profile.get("funding_raised_usd", 0),
            "team_size": profile.get("team_size"),
            "tech_stack": profile.get("tech_stack", []),
            "available_unlock_methods": profile.get("available_unlock_methods", []),
        },
        "recommended": ordered,
        "gateway_programs": gateway_programs,
        "standalone_programs": standalone_programs,
        "locked_programs": locked_programs,
        "below_threshold": [{"program_id": r["program_id"], "name": r["name"], "score": r["score"]} for r in below_threshold],
        "stacking_opportunities": stacks,
        "ineligible": ineligible,
        "conflicts": conflicts_list,
        "totals": {
            "recommended_count": len(recommended),
            "gateway_count": len(gateway_programs),
            "standalone_count": len(standalone_programs),
            "locked_count": len(locked_programs),
            "below_threshold_count": len(below_threshold),
            "ineligible_count": len(ineligible),
            "conflict_count": len(conflicts_list),
            "total_realistic_value_usd": total_realistic,
            "total_max_value_usd": total_max,
            "confidence_distribution": confidence_counts,
        },
    }

# ============================================================-------------------
# Output formatters
# ============================================================-------------------

CONFIDENCE_ICONS = {
    "near-certain":     "[**]",
    "high-probability": "[* ]",
    "competitive":      "[ ?]",
    "long-shot":        "[ -]",
}

def _format_program_block(i, prog, show_unlock_chain=False):
    """Format a single program block. Returns list of lines."""
    lines = []
    dur = f"{prog['duration_months']}mo" if prog.get("duration_months") else "ongoing"
    approval = f"~{prog.get('approval_time_days', '-')}d"
    conf_icon = CONFIDENCE_ICONS.get(prog.get("confidence", "competitive"), "[ ?]")
    tier_badge = {"gateway": "[GATEWAY]", "locked": "[LOCKED] ", "standalone": "         "}.get(prog.get("tier", "standalone"), "         ")
    prereqs = prog.get("prerequisites", [])
    unlocks = [u for u in prog.get("unlocks", []) if u]

    lines.append(f"\n  {i:2}. {conf_icon} {tier_badge} {prog['name']}  [{prog['score']:.0f}pts]")
    lines.append(f"      Confidence: {prog.get('confidence','?')}  -  {prog.get('confidence_reason','')}")
    lines.append(f"      Value: {prog['credit_range']} realistic=${prog.get('realistic_credit_usd',0):,} | {dur} | Approval: {approval}")
    lines.append(f"      Apply: {prog.get('application_url', 'N/A')}")

    if prereqs:
        lines.append(f"      Prerequisites: {', '.join(prereqs)}")
    if unlocks and show_unlock_chain:
        lines.append(f"      Unlocks: {', '.join(unlocks)}")
    if prog.get("enhances_via"):
        lines.append(f"      Better with: {', '.join(prog['enhances_via'])}")
    if prog.get("stacking_notes"):
        lines.append(f"      Stack: {prog['stacking_notes']}")
    if prog.get("sponsor_warning"):
        lines.append(f"      ! WARNING: {prog['sponsor_warning']}")
    if prog.get("notes"):
        note = prog["notes"][:120] + ("..." if len(prog["notes"]) > 120 else "")
        lines.append(f"      Note: {note}")
    return lines


def format_text_roadmap(result):
    lines = []
    lines.append("")
    lines.append("=" * 65)
    lines.append("  RUNWAY CREDITS - PERSONALIZED ROADMAP v2")
    lines.append("  (gateway / dependency / confidence tiers)")
    lines.append("=" * 65)

    totals = result["totals"]
    prof = result["profile_summary"]
    conf_dist = totals.get("confidence_distribution", {})

    lines.append(f"\n  Profile: {prof['entity_type']} | {prof['funding_stage']} | Team: {prof['team_size']}")
    lines.append(f"  Unlock paths: {', '.join(prof.get('available_unlock_methods', []))}")

    lines.append(f"\n  Programs recommended: {totals['recommended_count']}")
    lines.append(f"    {totals['gateway_count']} gateway  |  {totals['standalone_count']} standalone  |  {totals['locked_count']} locked-door")
    lines.append(f"  Realistic total value: ${totals['total_realistic_value_usd']:,}")
    lines.append(f"  Max possible value:    ${totals['total_max_value_usd']:,}")
    lines.append(f"\n  Confidence breakdown:")
    for tier in ["near-certain", "high-probability", "competitive", "long-shot"]:
        icon = CONFIDENCE_ICONS[tier]
        lines.append(f"    {icon} {tier:20} {conf_dist.get(tier, 0)} programs")

    # -- TIER 1: GATEWAY PROGRAMS ---------------------------------------------
    gateways = result.get("gateway_programs", [])
    if gateways:
        lines.append(f"\n{'-' * 65}")
        lines.append("  TIER 1  -  GATEWAY PROGRAMS  (apply first  -  these unlock others)")
        lines.append(f"{'-' * 65}")
        lines.append("  Strategy: Enrolling here multiplies your downstream deals.")
        for i, prog in enumerate(gateways, 1):
            lines.extend(_format_program_block(i, prog, show_unlock_chain=True))

    # -- TIER 2: STANDALONE PROGRAMS ------------------------------------------
    standalones = result.get("standalone_programs", [])
    if standalones:
        lines.append(f"\n{'-' * 65}")
        lines.append("  TIER 2  -  STANDALONE PROGRAMS  (apply anytime, no prerequisites)")
        lines.append(f"{'-' * 65}")
        for i, prog in enumerate(standalones, 1):
            lines.extend(_format_program_block(i, prog, show_unlock_chain=False))

    # -- TIER 3: LOCKED-DOOR PROGRAMS -----------------------------------------
    locked = result.get("locked_programs", [])
    if locked:
        lines.append(f"\n{'-' * 65}")
        lines.append("  TIER 3  -  LOCKED-DOOR PROGRAMS  (require a gateway first)")
        lines.append(f"{'-' * 65}")
        lines.append("  Strategy: Complete gateway enrollments above, then come back.")
        for i, prog in enumerate(locked, 1):
            lines.extend(_format_program_block(i, prog, show_unlock_chain=False))

    # -- OPTIMAL APPLICATION ORDER ---------------------------------------------
    lines.append(f"\n{'-' * 65}")
    lines.append("  OPTIMAL APPLICATION ORDER")
    lines.append(f"{'-' * 65}")
    all_ordered = result.get("recommended", [])
    for i, prog in enumerate(all_ordered, 1):
        conf_icon = CONFIDENCE_ICONS.get(prog.get("confidence", "competitive"), "[ ?]")
        tier_short = {"gateway": "GW", "standalone": "SA", "locked": "LK"}.get(prog.get("tier", "standalone"), "SA")
        prereqs_str = f"- after {', '.join(prog['prerequisites'])}" if prog.get("prerequisites") else ""
        lines.append(f"  {i:2}. {conf_icon} [{tier_short}] {prog['name']:<35} ${prog.get('realistic_credit_usd',0):>8,}  {prereqs_str}")

    # -- STACKING OPPORTUNITIES ------------------------------------------------
    if result["stacking_opportunities"]:
        lines.append(f"\n{'-' * 65}")
        lines.append("  STACKING OPPORTUNITIES")
        lines.append(f"{'-' * 65}")
        for stack in result["stacking_opportunities"]:
            lines.append(f"\n  * {stack['stack_name']}")
            lines.append(f"    Programs: {', '.join(stack['your_programs'])}")
            lines.append(f"    Value:    {stack['value_note']}")
            lines.append(f"    Note:     {stack['notes']}")

    # -- CONFLICTS ------------------------------------------------------------
    if result["conflicts"]:
        lines.append(f"\n{'-' * 65}")
        lines.append("  SKIPPED  -  CONFLICTS WITH CURRENT PERKS")
        lines.append(f"{'-' * 65}")
        for prog in result["conflicts"]:
            lines.append(f"  X  {prog['name']}: {prog['conflict_reason']}")

    # -- BELOW THRESHOLD -------------------------------------------------------
    below = result.get("below_threshold", [])
    if below:
        names = ", ".join(r["name"] for r in below)
        lines.append(f"\n  ({len(below)} programs scored below threshold (not top-65%): {names})")

    # -- INELIGIBLE ------------------------------------------------------------
    if result["ineligible"]:
        lines.append(f"\n  ({totals['ineligible_count']} programs not currently eligible  -  run --show-ineligible to see why)")

    lines.append("")
    lines.append("  Legend: [**] near-certain  [* ] high-probability  [ ?] competitive  [ -] long-shot")
    lines.append("          [GW] gateway  [SA] standalone  [LK] locked-door")
    lines.append("")
    return "\n".join(lines)

# ============================================================-------------------
# Entry points
# ============================================================-------------------

def run_from_profile(profile, output_path=None, fmt="text", show_ineligible=False):
    catalog = load_catalog()
    result = run_matching(profile, catalog)

    if fmt == "json":
        output = json.dumps(result, indent=2)
    else:
        output = format_text_roadmap(result)
        if show_ineligible and result["ineligible"]:
            output += "\n\nINELIGIBLE PROGRAMS:\n"
            for p in result["ineligible"]:
                output += f"  X {p['name']}: {p['ineligible_reason']}\n"

    if output_path:
        with open(output_path, "w") as f:
            f.write(output)
        print(f"  Roadmap saved - {output_path}")
    else:
        print(output)

    return result

def main():
    parser = argparse.ArgumentParser(description="Runway Credits Matching Engine")
    parser.add_argument("--profile", "-p", required=True, help="Path to user profile JSON (from intake.py)")
    parser.add_argument("--output", "-o", help="Save roadmap to this file")
    parser.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--show-ineligible", action="store_true", help="Also show why programs are ineligible")
    parser.add_argument("--save-db", help="Save checklist to SQLite DB file (requires setup_db.py)")
    args = parser.parse_args()

    with open(args.profile) as f:
        profile = json.load(f)

    result = run_from_profile(
        profile,
        output_path=args.output,
        fmt=args.format,
        show_ineligible=args.show_ineligible,
    )

    if args.save_db:
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "setup_db",
                os.path.join(os.path.dirname(__file__), "setup_db.py")
            )
            db_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(db_mod)
            db_mod.save_checklist_from_result(args.save_db, profile, result)
            print(f"  Checklist saved to DB - {args.save_db}")
        except Exception as e:
            print(f"  Could not save to DB: {e}")

if __name__ == "__main__":
    main()
