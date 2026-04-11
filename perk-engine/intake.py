#!/usr/bin/env python3
"""
Runway Credits Intake Form — CLI v1
Collects user profile for the matching engine.

Usage:
    python intake.py                    # interactive CLI
    python intake.py --output user.json # save profile to file
    python intake.py --load user.json   # load existing profile and re-run

Output: a user profile JSON object compatible with matcher.py
"""

import json
import sys
import os
import argparse
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# Field definitions
# ─────────────────────────────────────────────────────────────────────────────

ENTITY_TYPES = {
    "1": ("llc", "LLC (US)"),
    "2": ("c_corp", "C-Corporation (US Delaware or other)"),
    "3": ("s_corp", "S-Corporation (US)"),
    "4": ("sole_proprietor", "Sole Proprietor / DBA"),
    "5": ("non_us", "Non-US entity"),
}

FUNDING_STAGES = {
    "1": ("bootstrapped", "Bootstrapped (no outside funding)"),
    "2": ("pre_seed", "Pre-seed (friends/family/angels, <$500K)"),
    "3": ("seed", "Seed ($500K–$3M)"),
    "4": ("series_a", "Series A ($3M+)"),
    "5": ("series_b_plus", "Series B or later"),
}

TECH_STACKS = {
    "1": "web",
    "2": "ai_ml",
    "3": "fintech",
    "4": "mobile",
    "5": "saas",
    "6": "backend",
    "7": "frontend",
    "8": "data_analytics",
}

ACCELERATORS = {
    "1": "yc",
    "2": "techstars",
    "3": "antler",
    "4": "a16z",
    "5": "500_startups",
    "6": "sequoia_scout",
    "7": "other",
}

COMMON_PERKS = {
    "1": ("aws_activate", "AWS Activate"),
    "2": ("google_cloud", "Google Cloud for Startups"),
    "3": ("azure", "Microsoft for Startups (Azure)"),
    "4": ("stripe_atlas", "Stripe Atlas"),
    "5": ("yc_sus", "YC Startup School"),
    "6": ("brex", "Brex"),
    "7": ("vercel", "Vercel Startup"),
    "8": ("notion", "Notion for Startups"),
    "9": ("supabase", "Supabase Startup"),
    "10": ("hubspot", "HubSpot for Startups"),
    "11": ("linear", "Linear Startup"),
    "12": ("github_startups", "GitHub for Startups"),
    "13": ("digitalocean_hatch", "DigitalOcean Hatch"),
    "14": ("datadog", "Datadog for Startups"),
    "15": ("posthog", "PostHog for Startups"),
    "16": ("mercury", "Mercury Banking"),
    "17": ("ramp", "Ramp"),
    "18": ("relay", "Relay Banking"),
    "19": ("auth0", "Auth0 for Startups"),
    "20": ("anthropic_credits", "Anthropic Claude API Credits"),
}

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def header(text):
    width = 60
    print()
    print("=" * width)
    print(f"  {text}")
    print("=" * width)

def prompt(question, default=None):
    suffix = f" [{default}]" if default is not None else ""
    answer = input(f"  {question}{suffix}: ").strip()
    if not answer and default is not None:
        return default
    return answer

def prompt_number(question, default=None, min_val=0, max_val=None):
    while True:
        raw = prompt(question, default=str(default) if default is not None else None)
        try:
            val = float(raw)
            if max_val is not None and val > max_val:
                print(f"    ! Value must be <= {max_val}")
                continue
            if val < min_val:
                print(f"    ! Value must be >= {min_val}")
                continue
            return val
        except ValueError:
            print("    ! Please enter a number.")

def prompt_choice(question, choices, allow_multiple=False):
    """
    choices: dict of key -> (value, label) or key -> label
    Returns: single value or list of values (if allow_multiple=True)
    """
    print(f"\n  {question}")
    for k, v in choices.items():
        label = v[1] if isinstance(v, tuple) else v
        print(f"    {k}) {label}")

    if allow_multiple:
        print("    (Enter comma-separated numbers, or 0 to skip)")
        while True:
            raw = input("  Choice(s): ").strip()
            if raw == "0" or raw == "":
                return []
            parts = [p.strip() for p in raw.split(",")]
            results = []
            valid = True
            for p in parts:
                if p not in choices:
                    print(f"    ! Invalid choice: {p}")
                    valid = False
                    break
                v = choices[p]
                results.append(v[0] if isinstance(v, tuple) else v)
            if valid:
                return results
    else:
        while True:
            raw = input("  Choice: ").strip()
            if raw not in choices:
                print(f"    ! Invalid choice. Enter one of: {', '.join(choices.keys())}")
                continue
            v = choices[raw]
            return v[0] if isinstance(v, tuple) else v

def prompt_yes_no(question, default=True):
    default_str = "Y/n" if default else "y/N"
    while True:
        raw = input(f"  {question} [{default_str}]: ").strip().lower()
        if raw == "":
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("    ! Please enter y or n.")

# ─────────────────────────────────────────────────────────────────────────────
# Intake sections
# ─────────────────────────────────────────────────────────────────────────────

def collect_identity():
    header("1 / 7 — WHO ARE YOU?")
    name = prompt("Your name (optional)") or ""
    email = prompt("Email (optional, used as profile ID)") or ""
    return {"name": name, "email": email}

def collect_entity():
    header("2 / 7 — COMPANY STRUCTURE")
    entity_type = prompt_choice("What type of entity is your company?", ENTITY_TYPES)

    age = prompt_number("How old is your company? (years, e.g. 0.5 for 6 months)", default=0.0)

    has_product = prompt_yes_no("Do you have a deployed/live product?", default=False)

    return {
        "entity_type": entity_type,
        "company_age_years": age,
        "has_deployed_product": has_product,
    }

def collect_funding():
    header("3 / 7 — FUNDING & REVENUE")
    stage = prompt_choice("What is your current funding stage?", FUNDING_STAGES)

    raised = 0
    if stage not in ("bootstrapped",):
        raised = int(prompt_number("How much have you raised total? (USD, e.g. 500000)", default=0))

    revenue = int(prompt_number("Annual revenue (USD, 0 if pre-revenue)", default=0))

    has_vc = prompt_yes_no("Are you affiliated with a VC, accelerator, or incubator?", default=False)
    accelerators = []
    if has_vc:
        accelerators = prompt_choice(
            "Which accelerator(s) / VC(s)? (select all that apply)",
            ACCELERATORS,
            allow_multiple=True,
        )

    return {
        "funding_stage": stage,
        "funding_raised_usd": raised,
        "annual_revenue_usd": revenue,
        "has_vc_or_accelerator": has_vc,
        "accelerator_memberships": accelerators,
    }

def collect_team_and_stack():
    header("4 / 7 — TEAM & TECH STACK")
    team_size = int(prompt_number("Team size (including founders)", default=1, min_val=1))

    tech_stack = prompt_choice(
        "What tech areas best describe your product? (select all that apply)",
        TECH_STACKS,
        allow_multiple=True,
    )
    if not tech_stack:
        tech_stack = ["saas"]

    return {
        "team_size": team_size,
        "tech_stack": tech_stack,
    }

def collect_accounts():
    header("5 / 7 — FINANCIAL ACCOUNTS")
    has_brex = prompt_yes_no("Do you have a Brex account?", default=False)
    has_ramp = prompt_yes_no("Do you have a Ramp account?", default=False)
    has_mercury = prompt_yes_no("Do you have a Mercury account?", default=False)
    has_stripe_atlas = prompt_yes_no("Did you incorporate via Stripe Atlas?", default=False)

    return {
        "has_brex": has_brex,
        "has_ramp": has_ramp,
        "has_mercury": has_mercury,
        "has_stripe_atlas": has_stripe_atlas,
    }

def collect_current_perks():
    header("6 / 7 — PERKS YOU ALREADY HAVE")
    print("  (Skip any you don't have — this helps avoid re-recommending programs)")
    have = prompt_choice(
        "Which programs are you already enrolled in? (select all that apply)",
        COMMON_PERKS,
        allow_multiple=True,
    )

    # Allow manual entry of other perks
    print("\n  Any other programs not listed? (comma-separated slugs or press Enter to skip)")
    extra_raw = input("  Other perks: ").strip()
    extra = [e.strip() for e in extra_raw.split(",") if e.strip()] if extra_raw else []

    return {"current_perks": list(set(have + extra))}

def collect_goals():
    header("7 / 7 — YOUR PRIMARY GOALS")
    print("  This helps us weight the matching output.\n")
    print("  What matters most right now? (select all that apply)")
    goals_map = {
        "1": "cloud_infrastructure",
        "2": "ai_api_credits",
        "3": "reduce_saas_costs",
        "4": "banking_and_finance",
        "5": "developer_tooling",
        "6": "analytics_and_metrics",
        "7": "sales_and_crm",
        "8": "identity_and_security",
    }
    goals_labels = {
        "1": "Maximize cloud compute credits (AWS/GCP/Azure)",
        "2": "AI API credits (Anthropic/OpenAI/HuggingFace)",
        "3": "Reduce SaaS costs (design, PM, support tools)",
        "4": "Banking, cards, and financial infrastructure",
        "5": "Developer tooling (GitHub, JetBrains, Linear)",
        "6": "Analytics and product monitoring",
        "7": "Sales/CRM infrastructure (HubSpot, Intercom)",
        "8": "Identity, auth, and security",
    }
    print()
    for k, v in goals_labels.items():
        print(f"    {k}) {v}")
    print("    (Enter comma-separated numbers, or press Enter to skip)")
    raw = input("  Goal(s): ").strip()
    goals = []
    if raw:
        for p in raw.split(","):
            p = p.strip()
            if p in goals_map:
                goals.append(goals_map[p])
    return {"priority_goals": goals}

# ─────────────────────────────────────────────────────────────────────────────
# Main intake flow
# ─────────────────────────────────────────────────────────────────────────────

def run_intake(preload=None):
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║   RUNWAY CREDITS — Startup Perk Matching Engine          ║")
    print("║   Personalized roadmap in 7 quick questions              ║")
    print("╚══════════════════════════════════════════════════════════╝")

    if preload:
        print(f"\n  Loaded existing profile from: {preload}")

    profile = {}
    profile.update(collect_identity())
    profile.update(collect_entity())
    profile.update(collect_funding())
    profile.update(collect_team_and_stack())
    profile.update(collect_accounts())
    profile.update(collect_current_perks())
    profile.update(collect_goals())
    profile["created_at"] = datetime.utcnow().isoformat() + "Z"

    # Derive unlock_methods user has available
    unlock_methods = ["self_apply"]
    if profile.get("has_brex"):
        unlock_methods.append("brex_portal")
    if profile.get("has_stripe_atlas"):
        unlock_methods.append("stripe_atlas")
    if profile.get("has_vc_or_accelerator"):
        unlock_methods.append("vc_sponsor")
        if "yc" in profile.get("accelerator_memberships", []):
            unlock_methods.append("yc_sus")
        if any(a in profile.get("accelerator_memberships", []) for a in ["techstars", "antler", "500_startups"]):
            unlock_methods.append("accelerator")
    profile["available_unlock_methods"] = unlock_methods

    return profile

def print_summary(profile):
    header("PROFILE SUMMARY")
    print(f"  Entity:        {profile['entity_type']} | Age: {profile['company_age_years']}yr | Team: {profile['team_size']}")
    print(f"  Funding:       {profile['funding_stage']} | Raised: ${profile.get('funding_raised_usd', 0):,}")
    print(f"  Revenue:       ${profile.get('annual_revenue_usd', 0):,}/yr")
    print(f"  Tech:          {', '.join(profile.get('tech_stack', []))}")
    print(f"  Has product:   {'Yes' if profile.get('has_deployed_product') else 'No'}")
    print(f"  Accelerator:   {'Yes' if profile.get('has_vc_or_accelerator') else 'No'}")
    if profile.get("accelerator_memberships"):
        print(f"  Memberships:   {', '.join(profile['accelerator_memberships'])}")
    print(f"  Unlock paths:  {', '.join(profile.get('available_unlock_methods', []))}")
    print(f"  Current perks: {', '.join(profile.get('current_perks', [])) or 'None'}")
    print()

# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Runway Credits Intake Form")
    parser.add_argument("--output", "-o", help="Save profile to this JSON file")
    parser.add_argument("--load", "-l", help="Load existing profile JSON (re-run intake from it)")
    parser.add_argument("--run-matcher", action="store_true", help="Run matcher immediately after intake")
    args = parser.parse_args()

    preload_path = args.load
    profile = run_intake(preload=preload_path)
    print_summary(profile)

    output_path = args.output or "user_profile.json"
    with open(output_path, "w") as f:
        json.dump(profile, f, indent=2)
    print(f"  Profile saved → {output_path}")
    print()

    if args.run_matcher:
        # Import and run matcher inline
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "matcher",
                os.path.join(os.path.dirname(__file__), "matcher.py")
            )
            matcher_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(matcher_mod)
            matcher_mod.run_from_profile(profile)
        except Exception as e:
            print(f"  Could not auto-run matcher: {e}")
            print(f"  Run manually: python matcher.py --profile {output_path}")
    else:
        print(f"  Next step → python matcher.py --profile {output_path}")

if __name__ == "__main__":
    main()
