#!/usr/bin/env python3
"""
Batch Matching Engine Runner — NOD-143
Runs 50 diverse startup profiles through the matching engine and outputs a summary report.

Usage:
    python batch_runner.py
    python batch_runner.py --output batch_results.json
    python batch_runner.py --format text
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add parent dir so we can import matcher
sys.path.insert(0, str(Path(__file__).parent))
from matcher import run_matching, load_catalog

# ─────────────────────────────────────────────────────────────────────────────
# 50 Diverse Startup Profiles
# Covers: entity types, funding stages, team sizes, tech stacks, geographies,
#         existing perks, priority goals — designed to show product breadth.
# ─────────────────────────────────────────────────────────────────────────────

BATCH_PROFILES = [
    # 1 — Board member baseline (reference case)
    {
        "id": "CO-001",
        "name": "Romans 15:13 Capital LLC (Board Member Baseline)",
        "entity_type": "llc",
        "company_age_years": 2.0,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 25000,
        "has_vc_or_accelerator": False,
        "team_size": 1,
        "tech_stack": ["web", "ai_ml", "backend"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": True,
        "has_stripe_atlas": False,
        "current_perks": ["posthog", "mercury"],
        "priority_goals": ["cloud_infrastructure", "ai_api_credits"],
        "available_unlock_methods": ["self_apply"],
        "location": "nevada",
    },
    # 2 — Solo SaaS founder, Oregon-based, pre-seed
    {
        "id": "CO-002",
        "name": "Cascade SaaS Labs",
        "entity_type": "llc",
        "company_age_years": 1.0,
        "has_deployed_product": True,
        "funding_stage": "pre_seed",
        "funding_raised_usd": 150000,
        "annual_revenue_usd": 18000,
        "has_vc_or_accelerator": False,
        "team_size": 2,
        "tech_stack": ["web", "saas", "backend"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": False,
        "has_stripe_atlas": False,
        "current_perks": [],
        "priority_goals": ["cloud_infrastructure", "developer_tooling"],
        "available_unlock_methods": ["self_apply"],
        "location": "oregon",
    },
    # 3 — AI startup, seed stage, small team
    {
        "id": "CO-003",
        "name": "NeuralBridge AI",
        "entity_type": "c_corp",
        "company_age_years": 1.5,
        "has_deployed_product": True,
        "funding_stage": "seed",
        "funding_raised_usd": 1500000,
        "annual_revenue_usd": 80000,
        "has_vc_or_accelerator": True,
        "accelerator_memberships": ["techstars"],
        "team_size": 5,
        "tech_stack": ["ai_ml", "backend", "data_analytics"],
        "has_brex": True,
        "has_ramp": False,
        "has_mercury": False,
        "has_stripe_atlas": False,
        "current_perks": ["brex", "github_startups"],
        "priority_goals": ["ai_api_credits", "cloud_infrastructure"],
        "available_unlock_methods": ["self_apply", "yc_sus", "brex_portal"],
        "location": "california",
    },
    # 4 — Bootstrapped fintech, sole proprietor
    {
        "id": "CO-004",
        "name": "ClearLedger Accounting Tools",
        "entity_type": "sole_proprietor",
        "company_age_years": 3.0,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 55000,
        "has_vc_or_accelerator": False,
        "team_size": 1,
        "tech_stack": ["web", "fintech", "backend"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": True,
        "has_stripe_atlas": False,
        "current_perks": ["mercury"],
        "priority_goals": ["banking_and_finance", "reduce_saas_costs"],
        "available_unlock_methods": ["self_apply"],
        "location": "texas",
    },
    # 5 — Mobile app startup, pre-seed, small team
    {
        "id": "CO-005",
        "name": "TrailMap Mobile",
        "entity_type": "llc",
        "company_age_years": 0.5,
        "has_deployed_product": True,
        "funding_stage": "pre_seed",
        "funding_raised_usd": 50000,
        "annual_revenue_usd": 5000,
        "has_vc_or_accelerator": False,
        "team_size": 2,
        "tech_stack": ["mobile", "web", "backend"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": False,
        "has_stripe_atlas": False,
        "current_perks": [],
        "priority_goals": ["cloud_infrastructure", "developer_tooling"],
        "available_unlock_methods": ["self_apply"],
        "location": "colorado",
    },
    # 6 — Oregon AI startup, seed, YC SUS member
    {
        "id": "CO-006",
        "name": "PNW Intelligence Labs",
        "entity_type": "c_corp",
        "company_age_years": 1.0,
        "has_deployed_product": True,
        "funding_stage": "seed",
        "funding_raised_usd": 750000,
        "annual_revenue_usd": 40000,
        "has_vc_or_accelerator": False,
        "team_size": 3,
        "tech_stack": ["ai_ml", "backend", "data_analytics"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": True,
        "has_stripe_atlas": False,
        "current_perks": ["mercury", "yc_sus"],
        "priority_goals": ["ai_api_credits", "cloud_infrastructure"],
        "available_unlock_methods": ["self_apply", "yc_sus"],
        "location": "oregon",
    },
    # 7 — E-commerce / marketplace, bootstrapped
    {
        "id": "CO-007",
        "name": "PNW Makers Market",
        "entity_type": "llc",
        "company_age_years": 4.0,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 120000,
        "has_vc_or_accelerator": False,
        "team_size": 3,
        "tech_stack": ["web", "backend"],
        "has_brex": False,
        "has_ramp": True,
        "has_mercury": False,
        "has_stripe_atlas": False,
        "current_perks": ["ramp"],
        "priority_goals": ["reduce_saas_costs", "analytics_and_metrics"],
        "available_unlock_methods": ["self_apply"],
        "location": "oregon",
    },
    # 8 — Developer tools startup, seed, YC alumni
    {
        "id": "CO-008",
        "name": "DevPipeline.io",
        "entity_type": "c_corp",
        "company_age_years": 2.0,
        "has_deployed_product": True,
        "funding_stage": "seed",
        "funding_raised_usd": 2000000,
        "annual_revenue_usd": 200000,
        "has_vc_or_accelerator": True,
        "accelerator_memberships": ["yc"],
        "team_size": 8,
        "tech_stack": ["web", "backend", "saas"],
        "has_brex": True,
        "has_ramp": False,
        "has_mercury": False,
        "has_stripe_atlas": True,
        "current_perks": ["brex", "stripe_atlas", "yc_sus", "aws_activate", "github_startups"],
        "priority_goals": ["developer_tooling", "analytics_and_metrics"],
        "available_unlock_methods": ["self_apply", "yc_sus", "brex_portal", "stripe_atlas"],
        "location": "new_york",
    },
    # 9 — Healthcare tech, bootstrapped, Oregon
    {
        "id": "CO-009",
        "name": "PacificRim Health Analytics",
        "entity_type": "llc",
        "company_age_years": 2.5,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 85000,
        "has_vc_or_accelerator": False,
        "team_size": 2,
        "tech_stack": ["data_analytics", "backend", "saas"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": True,
        "has_stripe_atlas": False,
        "current_perks": ["mercury"],
        "priority_goals": ["analytics_and_metrics", "cloud_infrastructure"],
        "available_unlock_methods": ["self_apply"],
        "location": "oregon",
    },
    # 10 — Nonprofit tech spinoff, bootstrapped
    {
        "id": "CO-010",
        "name": "CivicCode Collective",
        "entity_type": "llc",
        "company_age_years": 1.0,
        "has_deployed_product": False,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 8000,
        "has_vc_or_accelerator": False,
        "team_size": 2,
        "tech_stack": ["web", "frontend"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": False,
        "has_stripe_atlas": False,
        "current_perks": [],
        "priority_goals": ["reduce_saas_costs", "developer_tooling"],
        "available_unlock_methods": ["self_apply"],
        "location": "oregon",
    },
    # 11 — AgTech startup, pre-seed
    {
        "id": "CO-011",
        "name": "Willamette Valley AgSense",
        "entity_type": "c_corp",
        "company_age_years": 1.5,
        "has_deployed_product": True,
        "funding_stage": "pre_seed",
        "funding_raised_usd": 200000,
        "annual_revenue_usd": 30000,
        "has_vc_or_accelerator": False,
        "team_size": 4,
        "tech_stack": ["data_analytics", "ai_ml", "backend"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": True,
        "has_stripe_atlas": False,
        "current_perks": ["mercury"],
        "priority_goals": ["cloud_infrastructure", "ai_api_credits"],
        "available_unlock_methods": ["self_apply"],
        "location": "oregon",
    },
    # 12 — EdTech solo founder, bootstrapped
    {
        "id": "CO-012",
        "name": "SkillStack Learning",
        "entity_type": "llc",
        "company_age_years": 1.0,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 22000,
        "has_vc_or_accelerator": False,
        "team_size": 1,
        "tech_stack": ["web", "saas", "frontend"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": False,
        "has_stripe_atlas": False,
        "current_perks": [],
        "priority_goals": ["reduce_saas_costs", "analytics_and_metrics"],
        "available_unlock_methods": ["self_apply"],
        "location": "washington",
    },
    # 13 — Logistics tech, seed funded
    {
        "id": "CO-013",
        "name": "FleetForward Logistics AI",
        "entity_type": "c_corp",
        "company_age_years": 2.0,
        "has_deployed_product": True,
        "funding_stage": "seed",
        "funding_raised_usd": 1200000,
        "annual_revenue_usd": 150000,
        "has_vc_or_accelerator": True,
        "accelerator_memberships": ["antler"],
        "team_size": 7,
        "tech_stack": ["ai_ml", "backend", "data_analytics"],
        "has_brex": True,
        "has_ramp": False,
        "has_mercury": False,
        "has_stripe_atlas": False,
        "current_perks": ["brex", "aws_activate"],
        "priority_goals": ["ai_api_credits", "cloud_infrastructure"],
        "available_unlock_methods": ["self_apply", "brex_portal"],
        "location": "california",
    },
    # 14 — Security startup, bootstrapped, 2 people
    {
        "id": "CO-014",
        "name": "CipherShield Security",
        "entity_type": "llc",
        "company_age_years": 1.5,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 65000,
        "has_vc_or_accelerator": False,
        "team_size": 2,
        "tech_stack": ["backend", "saas", "web"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": True,
        "has_stripe_atlas": False,
        "current_perks": ["mercury"],
        "priority_goals": ["identity_and_security", "cloud_infrastructure"],
        "available_unlock_methods": ["self_apply"],
        "location": "virginia",
    },
    # 15 — Creative tools SaaS, pre-seed, design focus
    {
        "id": "CO-015",
        "name": "Artboard Studio",
        "entity_type": "llc",
        "company_age_years": 0.75,
        "has_deployed_product": True,
        "funding_stage": "pre_seed",
        "funding_raised_usd": 75000,
        "annual_revenue_usd": 12000,
        "has_vc_or_accelerator": False,
        "team_size": 2,
        "tech_stack": ["web", "frontend", "saas"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": False,
        "has_stripe_atlas": False,
        "current_perks": [],
        "priority_goals": ["reduce_saas_costs", "developer_tooling"],
        "available_unlock_methods": ["self_apply"],
        "location": "new_york",
    },
    # 16 — Proptech, bootstrapped, Oregon
    {
        "id": "CO-016",
        "name": "Cascade Property Intel",
        "entity_type": "llc",
        "company_age_years": 2.0,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 95000,
        "has_vc_or_accelerator": False,
        "team_size": 2,
        "tech_stack": ["web", "backend", "data_analytics"],
        "has_brex": False,
        "has_ramp": True,
        "has_mercury": True,
        "has_stripe_atlas": False,
        "current_perks": ["ramp", "mercury"],
        "priority_goals": ["analytics_and_metrics", "cloud_infrastructure"],
        "available_unlock_methods": ["self_apply"],
        "location": "oregon",
    },
    # 17 — Food delivery platform, pre-seed
    {
        "id": "CO-017",
        "name": "LocalBite Delivery Network",
        "entity_type": "c_corp",
        "company_age_years": 1.0,
        "has_deployed_product": True,
        "funding_stage": "pre_seed",
        "funding_raised_usd": 300000,
        "annual_revenue_usd": 45000,
        "has_vc_or_accelerator": False,
        "team_size": 6,
        "tech_stack": ["mobile", "backend", "web"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": True,
        "has_stripe_atlas": False,
        "current_perks": ["mercury"],
        "priority_goals": ["cloud_infrastructure", "analytics_and_metrics"],
        "available_unlock_methods": ["self_apply"],
        "location": "oregon",
    },
    # 18 — Climate tech, seed, VC backed
    {
        "id": "CO-018",
        "name": "GreenGrid Energy Analytics",
        "entity_type": "c_corp",
        "company_age_years": 2.0,
        "has_deployed_product": True,
        "funding_stage": "seed",
        "funding_raised_usd": 2500000,
        "annual_revenue_usd": 180000,
        "has_vc_or_accelerator": True,
        "accelerator_memberships": ["other"],
        "team_size": 10,
        "tech_stack": ["data_analytics", "backend", "ai_ml"],
        "has_brex": True,
        "has_ramp": False,
        "has_mercury": False,
        "has_stripe_atlas": False,
        "current_perks": ["brex", "google_cloud", "aws_activate"],
        "priority_goals": ["ai_api_credits", "analytics_and_metrics"],
        "available_unlock_methods": ["self_apply", "brex_portal"],
        "location": "washington",
    },
    # 19 — Social commerce startup, bootstrapped
    {
        "id": "CO-019",
        "name": "CreatorCart",
        "entity_type": "llc",
        "company_age_years": 1.5,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 38000,
        "has_vc_or_accelerator": False,
        "team_size": 2,
        "tech_stack": ["web", "mobile", "saas"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": False,
        "has_stripe_atlas": False,
        "current_perks": [],
        "priority_goals": ["sales_and_crm", "analytics_and_metrics"],
        "available_unlock_methods": ["self_apply"],
        "location": "florida",
    },
    # 20 — Legal tech, small team, bootstrapped
    {
        "id": "CO-020",
        "name": "ContractClear AI",
        "entity_type": "llc",
        "company_age_years": 1.0,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 42000,
        "has_vc_or_accelerator": False,
        "team_size": 2,
        "tech_stack": ["ai_ml", "backend", "saas"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": True,
        "has_stripe_atlas": False,
        "current_perks": ["mercury"],
        "priority_goals": ["ai_api_credits", "cloud_infrastructure"],
        "available_unlock_methods": ["self_apply"],
        "location": "oregon",
    },
    # 21 — Gaming studio, indie, Oregon
    {
        "id": "CO-021",
        "name": "Crater Lake Games",
        "entity_type": "llc",
        "company_age_years": 3.0,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 72000,
        "has_vc_or_accelerator": False,
        "team_size": 3,
        "tech_stack": ["web", "frontend", "backend"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": False,
        "has_stripe_atlas": False,
        "current_perks": [],
        "priority_goals": ["cloud_infrastructure", "reduce_saas_costs"],
        "available_unlock_methods": ["self_apply"],
        "location": "oregon",
    },
    # 22 — IoT startup, seed stage
    {
        "id": "CO-022",
        "name": "SensorNet Systems",
        "entity_type": "c_corp",
        "company_age_years": 2.0,
        "has_deployed_product": True,
        "funding_stage": "seed",
        "funding_raised_usd": 900000,
        "annual_revenue_usd": 60000,
        "has_vc_or_accelerator": True,
        "accelerator_memberships": ["500_startups"],
        "team_size": 6,
        "tech_stack": ["backend", "data_analytics", "ai_ml"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": True,
        "has_stripe_atlas": False,
        "current_perks": ["mercury", "github_startups"],
        "priority_goals": ["cloud_infrastructure", "ai_api_credits"],
        "available_unlock_methods": ["self_apply"],
        "location": "texas",
    },
    # 23 — HR tech platform, bootstrapped
    {
        "id": "CO-023",
        "name": "TeamFlow HR",
        "entity_type": "llc",
        "company_age_years": 2.5,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 110000,
        "has_vc_or_accelerator": False,
        "team_size": 4,
        "tech_stack": ["web", "saas", "backend"],
        "has_brex": False,
        "has_ramp": True,
        "has_mercury": True,
        "has_stripe_atlas": False,
        "current_perks": ["ramp", "mercury", "hubspot"],
        "priority_goals": ["sales_and_crm", "analytics_and_metrics"],
        "available_unlock_methods": ["self_apply"],
        "location": "oregon",
    },
    # 24 — Crypto / Web3 startup, pre-seed
    {
        "id": "CO-024",
        "name": "BlockPath Labs",
        "entity_type": "c_corp",
        "company_age_years": 1.0,
        "has_deployed_product": False,
        "funding_stage": "pre_seed",
        "funding_raised_usd": 250000,
        "annual_revenue_usd": 0,
        "has_vc_or_accelerator": False,
        "team_size": 3,
        "tech_stack": ["backend", "web", "ai_ml"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": False,
        "has_stripe_atlas": False,
        "current_perks": [],
        "priority_goals": ["cloud_infrastructure", "developer_tooling"],
        "available_unlock_methods": ["self_apply"],
        "location": "wyoming",
    },
    # 25 — Marketplace for freelancers, bootstrapped
    {
        "id": "CO-025",
        "name": "GigHarbor Marketplace",
        "entity_type": "llc",
        "company_age_years": 1.5,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 48000,
        "has_vc_or_accelerator": False,
        "team_size": 2,
        "tech_stack": ["web", "saas", "backend"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": True,
        "has_stripe_atlas": False,
        "current_perks": ["mercury"],
        "priority_goals": ["reduce_saas_costs", "sales_and_crm"],
        "available_unlock_methods": ["self_apply"],
        "location": "washington",
    },
    # 26 — Video production SaaS, bootstrapped
    {
        "id": "CO-026",
        "name": "ClipForge Video Platform",
        "entity_type": "llc",
        "company_age_years": 1.0,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 35000,
        "has_vc_or_accelerator": False,
        "team_size": 2,
        "tech_stack": ["web", "saas", "ai_ml"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": False,
        "has_stripe_atlas": False,
        "current_perks": [],
        "priority_goals": ["ai_api_credits", "cloud_infrastructure"],
        "available_unlock_methods": ["self_apply"],
        "location": "california",
    },
    # 27 — Transportation network, pre-seed
    {
        "id": "CO-027",
        "name": "RideSpark Mobility",
        "entity_type": "c_corp",
        "company_age_years": 0.75,
        "has_deployed_product": False,
        "funding_stage": "pre_seed",
        "funding_raised_usd": 400000,
        "annual_revenue_usd": 0,
        "has_vc_or_accelerator": False,
        "team_size": 5,
        "tech_stack": ["mobile", "backend", "data_analytics"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": True,
        "has_stripe_atlas": False,
        "current_perks": ["mercury"],
        "priority_goals": ["cloud_infrastructure", "analytics_and_metrics"],
        "available_unlock_methods": ["self_apply"],
        "location": "oregon",
    },
    # 28 — Fitness/wellness app, bootstrapped
    {
        "id": "CO-028",
        "name": "PaceTracker Fitness",
        "entity_type": "llc",
        "company_age_years": 2.0,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 28000,
        "has_vc_or_accelerator": False,
        "team_size": 1,
        "tech_stack": ["mobile", "web", "backend"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": False,
        "has_stripe_atlas": False,
        "current_perks": [],
        "priority_goals": ["reduce_saas_costs", "analytics_and_metrics"],
        "available_unlock_methods": ["self_apply"],
        "location": "colorado",
    },
    # 29 — Research software, university spinout
    {
        "id": "CO-029",
        "name": "QuantumSpec Research Tools",
        "entity_type": "c_corp",
        "company_age_years": 1.0,
        "has_deployed_product": True,
        "funding_stage": "pre_seed",
        "funding_raised_usd": 100000,
        "annual_revenue_usd": 20000,
        "has_vc_or_accelerator": False,
        "team_size": 3,
        "tech_stack": ["data_analytics", "ai_ml", "backend"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": False,
        "has_stripe_atlas": False,
        "current_perks": [],
        "priority_goals": ["cloud_infrastructure", "ai_api_credits"],
        "available_unlock_methods": ["self_apply"],
        "location": "oregon",
    },
    # 30 — Sustainability reporting platform, bootstrapped
    {
        "id": "CO-030",
        "name": "EcoReport Analytics",
        "entity_type": "llc",
        "company_age_years": 1.5,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 55000,
        "has_vc_or_accelerator": False,
        "team_size": 2,
        "tech_stack": ["data_analytics", "saas", "web"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": True,
        "has_stripe_atlas": False,
        "current_perks": ["mercury"],
        "priority_goals": ["analytics_and_metrics", "cloud_infrastructure"],
        "available_unlock_methods": ["self_apply"],
        "location": "oregon",
    },
    # 31 — Customer support AI, seed
    {
        "id": "CO-031",
        "name": "SupportAI Automation",
        "entity_type": "c_corp",
        "company_age_years": 1.5,
        "has_deployed_product": True,
        "funding_stage": "seed",
        "funding_raised_usd": 800000,
        "annual_revenue_usd": 95000,
        "has_vc_or_accelerator": True,
        "accelerator_memberships": ["antler"],
        "team_size": 5,
        "tech_stack": ["ai_ml", "saas", "backend"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": False,
        "has_stripe_atlas": False,
        "current_perks": ["aws_activate"],
        "priority_goals": ["ai_api_credits", "sales_and_crm"],
        "available_unlock_methods": ["self_apply"],
        "location": "california",
    },
    # 32 — Open source dev tools, no revenue yet
    {
        "id": "CO-032",
        "name": "OpenDeploy Infrastructure",
        "entity_type": "llc",
        "company_age_years": 0.5,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 0,
        "has_vc_or_accelerator": False,
        "team_size": 2,
        "tech_stack": ["backend", "web", "saas"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": False,
        "has_stripe_atlas": False,
        "current_perks": [],
        "priority_goals": ["developer_tooling", "cloud_infrastructure"],
        "available_unlock_methods": ["self_apply"],
        "location": "washington",
    },
    # 33 — Fashion / retail tech, bootstrapped
    {
        "id": "CO-033",
        "name": "StyleSync Retail Platform",
        "entity_type": "llc",
        "company_age_years": 2.0,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 78000,
        "has_vc_or_accelerator": False,
        "team_size": 3,
        "tech_stack": ["web", "mobile", "backend"],
        "has_brex": False,
        "has_ramp": True,
        "has_mercury": False,
        "has_stripe_atlas": False,
        "current_perks": ["ramp"],
        "priority_goals": ["reduce_saas_costs", "analytics_and_metrics"],
        "available_unlock_methods": ["self_apply"],
        "location": "texas",
    },
    # 34 — Construction tech, bootstrapped
    {
        "id": "CO-034",
        "name": "BuildTrack PM Tools",
        "entity_type": "llc",
        "company_age_years": 3.0,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 135000,
        "has_vc_or_accelerator": False,
        "team_size": 4,
        "tech_stack": ["web", "mobile", "saas"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": True,
        "has_stripe_atlas": False,
        "current_perks": ["mercury", "hubspot"],
        "priority_goals": ["sales_and_crm", "reduce_saas_costs"],
        "available_unlock_methods": ["self_apply"],
        "location": "oregon",
    },
    # 35 — Travel booking aggregator, bootstrapped
    {
        "id": "CO-035",
        "name": "WanderRoute Travel Tech",
        "entity_type": "llc",
        "company_age_years": 2.0,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 62000,
        "has_vc_or_accelerator": False,
        "team_size": 2,
        "tech_stack": ["web", "backend", "saas"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": False,
        "has_stripe_atlas": False,
        "current_perks": [],
        "priority_goals": ["cloud_infrastructure", "analytics_and_metrics"],
        "available_unlock_methods": ["self_apply"],
        "location": "california",
    },
    # 36 — Blockchain infra, pre-seed
    {
        "id": "CO-036",
        "name": "ValidatorNode.xyz",
        "entity_type": "llc",
        "company_age_years": 1.0,
        "has_deployed_product": True,
        "funding_stage": "pre_seed",
        "funding_raised_usd": 100000,
        "annual_revenue_usd": 15000,
        "has_vc_or_accelerator": False,
        "team_size": 2,
        "tech_stack": ["backend", "web"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": True,
        "has_stripe_atlas": False,
        "current_perks": ["mercury"],
        "priority_goals": ["cloud_infrastructure", "developer_tooling"],
        "available_unlock_methods": ["self_apply"],
        "location": "nevada",
    },
    # 37 — AI content platform, seed
    {
        "id": "CO-037",
        "name": "ContentForge AI",
        "entity_type": "c_corp",
        "company_age_years": 1.5,
        "has_deployed_product": True,
        "funding_stage": "seed",
        "funding_raised_usd": 1000000,
        "annual_revenue_usd": 120000,
        "has_vc_or_accelerator": False,
        "team_size": 6,
        "tech_stack": ["ai_ml", "saas", "web"],
        "has_brex": True,
        "has_ramp": False,
        "has_mercury": False,
        "has_stripe_atlas": False,
        "current_perks": ["brex", "openai_credits"],
        "priority_goals": ["ai_api_credits", "cloud_infrastructure"],
        "available_unlock_methods": ["self_apply", "brex_portal"],
        "location": "new_york",
    },
    # 38 — Mental health app, bootstrapped
    {
        "id": "CO-038",
        "name": "ClearMind Wellness",
        "entity_type": "llc",
        "company_age_years": 1.0,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 18000,
        "has_vc_or_accelerator": False,
        "team_size": 2,
        "tech_stack": ["mobile", "web", "saas"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": False,
        "has_stripe_atlas": False,
        "current_perks": [],
        "priority_goals": ["reduce_saas_costs", "analytics_and_metrics"],
        "available_unlock_methods": ["self_apply"],
        "location": "oregon",
    },
    # 39 — B2B data API, bootstrapped
    {
        "id": "CO-039",
        "name": "DataPulse API Services",
        "entity_type": "llc",
        "company_age_years": 2.0,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 90000,
        "has_vc_or_accelerator": False,
        "team_size": 2,
        "tech_stack": ["backend", "data_analytics", "saas"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": True,
        "has_stripe_atlas": False,
        "current_perks": ["mercury", "aws_activate"],
        "priority_goals": ["cloud_infrastructure", "analytics_and_metrics"],
        "available_unlock_methods": ["self_apply"],
        "location": "texas",
    },
    # 40 — Robotic process automation, bootstrapped
    {
        "id": "CO-040",
        "name": "AutoScript RPA",
        "entity_type": "llc",
        "company_age_years": 1.5,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 68000,
        "has_vc_or_accelerator": False,
        "team_size": 2,
        "tech_stack": ["backend", "ai_ml", "saas"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": True,
        "has_stripe_atlas": False,
        "current_perks": ["mercury"],
        "priority_goals": ["ai_api_credits", "cloud_infrastructure"],
        "available_unlock_methods": ["self_apply"],
        "location": "oregon",
    },
    # 41 — Event management SaaS, bootstrapped
    {
        "id": "CO-041",
        "name": "EventPilot Platform",
        "entity_type": "llc",
        "company_age_years": 2.5,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 88000,
        "has_vc_or_accelerator": False,
        "team_size": 3,
        "tech_stack": ["web", "saas", "backend"],
        "has_brex": False,
        "has_ramp": True,
        "has_mercury": False,
        "has_stripe_atlas": False,
        "current_perks": ["ramp", "hubspot"],
        "priority_goals": ["sales_and_crm", "analytics_and_metrics"],
        "available_unlock_methods": ["self_apply"],
        "location": "california",
    },
    # 42 — Insurance tech, seed
    {
        "id": "CO-042",
        "name": "PolicyAI InsurTech",
        "entity_type": "c_corp",
        "company_age_years": 2.0,
        "has_deployed_product": True,
        "funding_stage": "seed",
        "funding_raised_usd": 1800000,
        "annual_revenue_usd": 220000,
        "has_vc_or_accelerator": True,
        "accelerator_memberships": ["a16z"],
        "team_size": 12,
        "tech_stack": ["ai_ml", "backend", "data_analytics", "fintech"],
        "has_brex": True,
        "has_ramp": False,
        "has_mercury": False,
        "has_stripe_atlas": True,
        "current_perks": ["brex", "stripe_atlas", "aws_activate", "google_cloud"],
        "priority_goals": ["ai_api_credits", "identity_and_security"],
        "available_unlock_methods": ["self_apply", "brex_portal", "stripe_atlas"],
        "location": "new_york",
    },
    # 43 — Real-time translation SaaS, bootstrapped
    {
        "id": "CO-043",
        "name": "LinguaSync AI",
        "entity_type": "llc",
        "company_age_years": 1.0,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 32000,
        "has_vc_or_accelerator": False,
        "team_size": 2,
        "tech_stack": ["ai_ml", "web", "saas"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": True,
        "has_stripe_atlas": False,
        "current_perks": ["mercury"],
        "priority_goals": ["ai_api_credits", "cloud_infrastructure"],
        "available_unlock_methods": ["self_apply"],
        "location": "washington",
    },
    # 44 — No-code platform, pre-seed
    {
        "id": "CO-044",
        "name": "FlowBuilder No-Code",
        "entity_type": "llc",
        "company_age_years": 0.5,
        "has_deployed_product": True,
        "funding_stage": "pre_seed",
        "funding_raised_usd": 80000,
        "annual_revenue_usd": 8000,
        "has_vc_or_accelerator": False,
        "team_size": 2,
        "tech_stack": ["web", "saas", "frontend"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": False,
        "has_stripe_atlas": False,
        "current_perks": [],
        "priority_goals": ["developer_tooling", "cloud_infrastructure"],
        "available_unlock_methods": ["self_apply"],
        "location": "texas",
    },
    # 45 — Podcast / audio tech, bootstrapped
    {
        "id": "CO-045",
        "name": "SoundDeck Audio Platform",
        "entity_type": "llc",
        "company_age_years": 1.5,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 25000,
        "has_vc_or_accelerator": False,
        "team_size": 2,
        "tech_stack": ["web", "ai_ml", "saas"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": False,
        "has_stripe_atlas": False,
        "current_perks": [],
        "priority_goals": ["ai_api_credits", "reduce_saas_costs"],
        "available_unlock_methods": ["self_apply"],
        "location": "california",
    },
    # 46 — BI dashboard tool, bootstrapped, larger team
    {
        "id": "CO-046",
        "name": "MetricLens BI",
        "entity_type": "llc",
        "company_age_years": 3.5,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 250000,
        "has_vc_or_accelerator": False,
        "team_size": 8,
        "tech_stack": ["data_analytics", "saas", "web", "backend"],
        "has_brex": False,
        "has_ramp": True,
        "has_mercury": True,
        "has_stripe_atlas": False,
        "current_perks": ["ramp", "mercury", "datadog"],
        "priority_goals": ["analytics_and_metrics", "cloud_infrastructure"],
        "available_unlock_methods": ["self_apply"],
        "location": "florida",
    },
    # 47 — Telemedicine startup, pre-seed
    {
        "id": "CO-047",
        "name": "DocConnect Telehealth",
        "entity_type": "c_corp",
        "company_age_years": 1.0,
        "has_deployed_product": True,
        "funding_stage": "pre_seed",
        "funding_raised_usd": 350000,
        "annual_revenue_usd": 25000,
        "has_vc_or_accelerator": False,
        "team_size": 4,
        "tech_stack": ["web", "mobile", "backend", "saas"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": True,
        "has_stripe_atlas": False,
        "current_perks": ["mercury"],
        "priority_goals": ["cloud_infrastructure", "identity_and_security"],
        "available_unlock_methods": ["self_apply"],
        "location": "oregon",
    },
    # 48 — Supply chain visibility platform, seed
    {
        "id": "CO-048",
        "name": "ChainViz Supply Intelligence",
        "entity_type": "c_corp",
        "company_age_years": 2.0,
        "has_deployed_product": True,
        "funding_stage": "seed",
        "funding_raised_usd": 600000,
        "annual_revenue_usd": 75000,
        "has_vc_or_accelerator": False,
        "team_size": 5,
        "tech_stack": ["data_analytics", "ai_ml", "backend", "saas"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": True,
        "has_stripe_atlas": False,
        "current_perks": ["mercury"],
        "priority_goals": ["ai_api_credits", "analytics_and_metrics"],
        "available_unlock_methods": ["self_apply"],
        "location": "washington",
    },
    # 49 — Recruitment AI, bootstrapped, Oregon
    {
        "id": "CO-049",
        "name": "TalentPulse AI Recruiting",
        "entity_type": "llc",
        "company_age_years": 1.5,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 58000,
        "has_vc_or_accelerator": False,
        "team_size": 2,
        "tech_stack": ["ai_ml", "web", "saas"],
        "has_brex": False,
        "has_ramp": False,
        "has_mercury": True,
        "has_stripe_atlas": False,
        "current_perks": ["mercury"],
        "priority_goals": ["ai_api_credits", "sales_and_crm"],
        "available_unlock_methods": ["self_apply"],
        "location": "oregon",
    },
    # 50 — Home services marketplace, bootstrapped
    {
        "id": "CO-050",
        "name": "ProTasker Home Services",
        "entity_type": "llc",
        "company_age_years": 2.0,
        "has_deployed_product": True,
        "funding_stage": "bootstrapped",
        "funding_raised_usd": 0,
        "annual_revenue_usd": 102000,
        "has_vc_or_accelerator": False,
        "team_size": 3,
        "tech_stack": ["web", "mobile", "backend"],
        "has_brex": False,
        "has_ramp": True,
        "has_mercury": False,
        "has_stripe_atlas": False,
        "current_perks": ["ramp"],
        "priority_goals": ["reduce_saas_costs", "analytics_and_metrics"],
        "available_unlock_methods": ["self_apply"],
        "location": "texas",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Batch runner
# ─────────────────────────────────────────────────────────────────────────────

def run_batch(profiles):
    catalog = load_catalog()
    batch_results = []

    for profile in profiles:
        company_id = profile.get("id", "?")
        company_name = profile.get("name", "Unknown")
        result = run_matching(profile, catalog)
        batch_results.append({
            "id": company_id,
            "name": company_name,
            "funding_stage": profile.get("funding_stage"),
            "entity_type": profile.get("entity_type"),
            "team_size": profile.get("team_size"),
            "location": profile.get("location", "unknown"),
            "recommended_count": result["totals"]["recommended_count"],
            "ineligible_count": result["totals"]["ineligible_count"],
            "total_realistic_usd": result["totals"]["total_realistic_value_usd"],
            "total_max_usd": result["totals"]["total_max_value_usd"],
            "top_programs": [r["name"] for r in result["recommended"][:5]],
            "stacking_count": len(result["stacking_opportunities"]),
            "stacking_names": [s["stack_name"] for s in result["stacking_opportunities"]],
        })

    return batch_results


def format_batch_report(batch_results):
    lines = []
    lines.append("=" * 72)
    lines.append("  RUNWAY CREDITS — BATCH MATCHING ENGINE RUN")
    lines.append(f"  {len(batch_results)} company profiles | Run: {datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ')}")
    lines.append("=" * 72)

    total_realistic = sum(r["total_realistic_usd"] for r in batch_results)
    total_max = sum(r["total_max_usd"] for r in batch_results)
    avg_recommended = sum(r["recommended_count"] for r in batch_results) / len(batch_results)
    avg_realistic = total_realistic / len(batch_results)
    companies_over_100k = sum(1 for r in batch_results if r["total_realistic_usd"] >= 100000)
    companies_over_200k = sum(1 for r in batch_results if r["total_realistic_usd"] >= 200000)
    companies_over_300k = sum(1 for r in batch_results if r["total_realistic_usd"] >= 300000)

    lines.append("")
    lines.append("  AGGREGATE SUMMARY")
    lines.append(f"  {'─' * 60}")
    lines.append(f"  Companies run:              {len(batch_results)}")
    lines.append(f"  Avg programs recommended:   {avg_recommended:.1f}")
    lines.append(f"  Avg realistic value:        ${avg_realistic:,.0f}")
    lines.append(f"  Total realistic value:      ${total_realistic:,.0f}")
    lines.append(f"  Total max value:            ${total_max:,.0f}")
    lines.append(f"  Companies with >$100K:      {companies_over_100k} / {len(batch_results)}")
    lines.append(f"  Companies with >$200K:      {companies_over_200k} / {len(batch_results)}")
    lines.append(f"  Companies with >$300K:      {companies_over_300k} / {len(batch_results)}")

    # Sort by realistic value desc
    sorted_results = sorted(batch_results, key=lambda x: x["total_realistic_usd"], reverse=True)

    lines.append("")
    lines.append(f"  {'─' * 72}")
    lines.append("  RESULTS TABLE (sorted by realistic value)")
    lines.append(f"  {'─' * 72}")
    header = f"  {'ID':8} {'Company':35} {'Stage':14} {'Team':5} {'Rec':5} {'Realistic Value':>16}"
    lines.append(header)
    lines.append(f"  {'─' * 70}")

    for r in sorted_results:
        line = f"  {r['id']:8} {r['name'][:33]:35} {r['funding_stage']:14} {r['team_size']:>4}  {r['recommended_count']:>4}  ${r['total_realistic_usd']:>14,.0f}"
        lines.append(line)

    lines.append("")
    lines.append(f"  {'─' * 72}")
    lines.append("  TOP 10 COMPANIES BY VALUE")
    lines.append(f"  {'─' * 72}")
    for i, r in enumerate(sorted_results[:10], 1):
        lines.append(f"\n  {i:2}. {r['name']} ({r['id']})")
        lines.append(f"      Realistic: ${r['total_realistic_usd']:,.0f} | Max: ${r['total_max_usd']:,.0f}")
        lines.append(f"      Stage: {r['funding_stage']} | Team: {r['team_size']} | Location: {r['location']}")
        lines.append(f"      Programs: {r['recommended_count']} matched | Stacking: {r['stacking_count']} opportunities")
        if r["top_programs"]:
            lines.append(f"      Top picks: {', '.join(r['top_programs'][:3])}")

    # Bottom 5
    lines.append("")
    lines.append(f"  {'─' * 72}")
    lines.append("  LOWEST VALUE MATCHES (still positive)")
    lines.append(f"  {'─' * 72}")
    for r in sorted_results[-5:]:
        lines.append(f"  {r['id']:8} {r['name'][:33]:35} ${r['total_realistic_usd']:>10,.0f} ({r['recommended_count']} programs)")

    # Stacking breakdown
    stack_counts = {}
    for r in batch_results:
        for s in r["stacking_names"]:
            stack_counts[s] = stack_counts.get(s, 0) + 1

    if stack_counts:
        lines.append("")
        lines.append(f"  {'─' * 72}")
        lines.append("  STACKING OPPORTUNITIES (across all companies)")
        lines.append(f"  {'─' * 72}")
        for stack_name, count in sorted(stack_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {count:3} companies eligible: {stack_name}")

    lines.append("")
    lines.append("=" * 72)
    lines.append("  END OF BATCH REPORT")
    lines.append("=" * 72)
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Batch Matching Engine Runner")
    parser.add_argument("--output", "-o", help="Save JSON results to this file")
    parser.add_argument("--format", "-f", choices=["text", "json"], default="text")
    args = parser.parse_args()

    print(f"Running {len(BATCH_PROFILES)} profiles through matching engine...")
    batch_results = run_batch(BATCH_PROFILES)

    if args.format == "json":
        output = json.dumps(batch_results, indent=2)
    else:
        output = format_batch_report(batch_results)

    print(output)

    if args.output:
        with open(args.output, "w") as f:
            if args.format == "json":
                f.write(output)
            else:
                f.write(output)
        print(f"Results saved to {args.output}")

    return batch_results


if __name__ == "__main__":
    main()
