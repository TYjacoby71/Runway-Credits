# Developer / Startup Perks — Application Order Flowchart

_Last updated: 2026-04-07 | Synced with catalog v3 (26 programs)_

This document defines the optimal sequencing for applying to startup and developer perk programs, organized by effort, dependencies, and compounding value.

---

## Application Priority Matrix

```
STAGE 0 — APPLY IMMEDIATELY (Day 1, no dependencies)
─────────────────────────────────────────────────────
  ├── AWS Activate Founders ($1,000)
  │    └── URL: aws.amazon.com/activate → Founders tier
  ├── Google Cloud Spark ($2,000)
  │    └── URL: cloud.google.com/startup → Spark tier
  ├── Microsoft for Startups Founders Hub ($1,000 + M365 + GitHub Copilot)
  │    └── URL: startups.microsoft.com
  ├── Linear Startup Program (1yr free)
  │    └── URL: linear.app/startups (fastest approval)
  └── YC Startup School (free enrollment → partial deals)
       └── URL: startupschool.org

STAGE 1 — APPLY WITHIN FIRST WEEK (require account/entity setup)
──────────────────────────────────────────────────────────────────
  ├── Mercury Banking (free treasury account → Raise program)
  │    └── URL: mercury.com (need US entity + EIN)
  ├── Brex Business Account → unlock Anthropic, OpenAI, Notion, Figma, Carta perks
  │    └── URL: brex.com/startups (need US EIN + business entity)
  ├── Ramp Corporate Card (alternative/additive to Brex — different perk portal)
  │    └── URL: ramp.com (no personal guarantee; different partner perks than Brex)
  ├── Supabase Startup Program (1yr free Pro)
  │    └── URL: supabase.com/pricing → Startup Program (need first project)
  ├── Vercel Startup Program (1yr Pro)
  │    └── URL: vercel.com/pricing → startup apply (need first deployment)
  ├── Notion for Startups (6mo free Plus)
  │    └── URL: notion.so/startups (need company email domain)
  ├── JetBrains for Startups (All Products Pack, 1yr)
  │    └── URL: jetbrains.com/lp/startup-program (need GitHub or product URL)
  └── PostHog for Startups (1yr cloud credits via YC SUS portal)
       └── URL: posthog.com/startups or via startupschool.org deals

STAGE 2 — APPLY AFTER ENTITY FORMATION (if using Stripe Atlas)
───────────────────────────────────────────────────────────────
  └── Stripe Atlas ($500 one-time)
       └── Unlocks: AWS +$1K, GCP +$2K, HubSpot free, Gusto 6mo, Carta +$1.5K
       └── Note: do at incorporation for max compound; additive to Stage 0 applications
       └── URL: stripe.com/atlas

STAGE 3 — APPLY POST-SEED FUNDING (require funding proof)
───────────────────────────────────────────────────────────
  ├── AWS Activate Portfolio ($5K–$100K via VC/accelerator sponsor)
  │    └── Requires: VC/accelerator partner endorsement
  ├── Google Cloud Ignite ($10K–$200K via partner)
  │    └── Requires: GCP partner (Antler, YC, Techstars, etc.)
  ├── Microsoft for Startups Funded Startup ($25K–$150K)
  │    └── Requires: raised funding proof
  ├── HubSpot for Startups (90% off → 50% → 25%)
  │    └── Requires: accelerator/partner code
  └── YC Batch → full $500K deal package
       └── Requires: YC acceptance

STAGE 4 — ONGOING / RENEWAL (monitor and maintain)
─────────────────────────────────────────────────────
  ├── Renew cloud credits before expiry (track expiry dates)
  ├── Check Brex perks portal quarterly (new programs added)
  ├── Check Ramp perks portal quarterly (separate partner deals)
  ├── Upgrade AWS/GCP tiers as usage grows
  ├── JetBrains renewal: eligible for up to 3 years — re-apply annually
  └── Update catalog when any credit program changes pricing
```

---

## Decision Tree

```
Are you a legal entity (LLC or Corp)?
 ├── NO → Form entity first; Stripe Atlas is the fastest path ($500)
 └── YES ↓

Are you incorporated via Stripe Atlas?
 ├── NO → Apply Stage 0 immediately; Stage 1 within a week
 └── YES → Apply Stripe Atlas perks dashboard → then Stage 0–1

Do you have a VC or accelerator relationship?
 ├── NO → Stick to Stage 0–2; enroll in YC Startup School (free)
 └── YES → Pursue Stage 3 programs via sponsor; YC batch if applicable

Are you using AI/LLM APIs?
 ├── NO → Standard cloud credits sufficient (Stage 0–2)
 └── YES → Prioritize:
            1. Brex account (Anthropic + OpenAI credits fastest)
            2. Azure for Startups (Azure OpenAI access)
            3. Google Cloud Ignite (Vertex AI)
            4. Monitor anthropic.com/programs for direct credits

Is your primary stack frontend-heavy (JAMStack)?
 └── YES → Pair Vercel + Supabase startup credits (Stage 1) for zero-cost full-stack year
```

---

## Sequencing Recommendations by Company Profile

### Solo Founder, Pre-Revenue, No Entity Yet

1. Form entity (Stripe Atlas if US Delaware C-Corp — fastest)
2. Enroll YC Startup School (free, same day)
3. Apply Stage 0: AWS Activate Founders, GCP Spark, Microsoft Founders Hub
4. Open Brex account (after EIN received, ~1 week post-Atlas)
5. Apply Stage 1: Linear, Supabase, Vercel, Notion

**Expected total: ~$8,500–$15,000 in free credits within 2 weeks**

---

### Seed-Funded Startup ($500K–$2M raised)

1. Apply Stage 3 via VC intro: AWS Activate Portfolio, GCP Ignite
2. Apply HubSpot for Startups via accelerator
3. Maintain all Stage 0–2 active (don't cancel upon Stage 3 approval)
4. Push Stage 3 cloud tiers before Stage 0 credits expire

**Expected total: $50,000–$250,000 in cloud/SaaS credits over 18 months**

---

### AI-Native Product (any stage)

1. Brex account FIRST → Anthropic credits available immediately
2. Azure for Startups → Azure OpenAI Service access
3. GCP Spark → Vertex AI + Gemini API
4. Check `console.anthropic.com` for any direct-program credits
5. Monitor Brex portal quarterly for updated AI partner perks

---

## Expiry Tracking Checklist

| Program | Typical Expiry | Renewal Path |
|---------|---------------|--------------|
| AWS Activate Founders | 2 years | Cannot renew; transition to AWS Activate Portfolio |
| Google Cloud Spark | 12 months | Transition to Ignite (funding required) |
| Microsoft Founders Hub | 12 months | Apply for Funded Startup tier |
| Vercel Startup | 12 months | Re-apply or move to paid |
| Supabase Startup | 12 months | Re-apply or move to paid |
| Notion for Startups | 6 months free + 50% yr1 | Track billing date |
| Brex perks | Varies by perk | Review dashboard quarterly |
| Stripe Atlas perks | Varies | Check Atlas dashboard |

---

## Files in This Package

| File | Contents |
|------|---------|
| `dev-perk-catalog.md` | Full program entries with credit amounts, terms, requirements, stacking rules (26 programs as of Patrol #3) |
| `dev-perk-flowchart.md` | Application order and sequencing (this file) |

## Legacy Research (Authoritative Source)

| File | Contents |
|------|---------|
| `operations/runway/PROJECTS/CREDITS_INTEL_PACK/work/CREDITS-TRACKER.md` | Original program matrix (pre-catalog) |
| `operations/runway/PROJECTS/CREDITS_INTEL_PACK/work/PROGRAM-DEEP-DIVES.md` | Deep-dives: AWS, GCP, Stripe, Mercury, PostHog, Tier 2 |
| `operations/runway/PROJECTS/CREDITS_INTEL_PACK/work/ANALYTICS_AND_AD_ACCOUNT_INTEGRATIONS_REFERENCE_2026-03-17.md` | Integration blueprint: Plaid, Google Ads, Meta, Stripe, Mercury APIs |
| `operations/runway/NODE-RUNWAY-MISSION-BRIEFING.md` | Full mission charter + affiliate revenue strategy |
