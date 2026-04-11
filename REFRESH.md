# Perk Catalog Refresh Protocol

## Overview

The Intel Pack catalog (`perk-engine/data/programs.json`) is a curated, quality-first dataset.
Current size: **201 programs** (as of April 2026). Ceiling target: ~400–500 high-value programs.

**Philosophy:** Signal over noise. We track real credits with meaningful value ($50+), not every
free-tier SaaS plan. Each entry must have a verifiable application URL and realistic credit value.

---

## Monthly Patrol Run (~1 hour)

**Who:** CMO agent (discovery sweep)
**Frequency:** First week of each month
**Goal:** Net-new programs only — do not re-scrape existing entries

### Steps

1. **Check provider newsletters & changelogs**
   - AWS Activate blog (`aws.amazon.com/blogs/startups`)
   - Google for Startups updates
   - Microsoft for Startups announcements
   - Stripe Atlas newsletter
   - YC blog (new batch perks)

2. **Check AI/integration bonuses** (fast-moving category)
   - Netlify + AI integration credits
   - Vercel AI SDK promotions
   - Supabase AI tier bonuses
   - Any `partner.anthropic.com` or `openai.com/startups` updates

3. **Check accelerator new cohort announcements**
   - New VC firms with portfolio perks
   - New accelerator batch perks (Techstars, 500, etc.)

4. **Deduplicate** — search `programs.json` for provider name before adding.

5. **Add new entries** using the schema below.

---

## Quarterly Deep Dive (~4 hours)

**Who:** CTO agent
**Frequency:** Quarterly (Jan, Apr, Jul, Oct)
**Goal:** Verify existing entries still active, update amounts/terms, prune dead programs

### Steps

1. Sample 20% of entries (random), verify URLs still resolve and programs still active
2. Flag any with `approval_time_days` changed significantly
3. Update `credit_min_usd`/`credit_max_usd`/`realistic_credit_usd` if terms changed
4. Remove entries where program is confirmed discontinued
5. Commit with message: `data: quarterly refresh Q[N] YYYY`

---

## Adding a New Entry (Schema)

```json
{
  "id": "provider_program_name",
  "name": "Full Program Name",
  "provider": "Provider Company",
  "category": "cloud_infrastructure|developer_tools|ai_ml|payments|devops|communication|other",
  "credit_min_usd": 0,
  "credit_max_usd": 0,
  "realistic_credit_usd": 0,
  "duration_months": 12,
  "tiers": [
    {
      "name": "Tier Name",
      "credit_usd": 0,
      "requires_sponsor": false
    }
  ],
  "eligibility": {
    "max_company_age_years": null,
    "max_funding_usd": null,
    "max_arr_usd": null,
    "funding_stages_eligible": ["bootstrapped", "pre_seed", "seed"],
    "entity_types": ["any"],
    "requires_deployed_product": false,
    "requires_partner_sponsor": false,
    "tech_focus": null
  },
  "application_url": "https://...",
  "approval_time_days": 7,
  "unlock_methods": ["self_apply"],
  "sequence_priority": 2,
  "stacking": {
    "conflicts_with": [],
    "stacks_well_with": [],
    "notes": null
  },
  "tags": [],
  "notes": "One-sentence description.",
  "prerequisites": [],
  "enhances_via": [],
  "unlocks": []
}
```

### Quality Bar
- `realistic_credit_usd` must be ≥ $50
- `application_url` must be live and verifiable
- `notes` must be a single clear sentence
- Do not add programs you cannot verify exist

---

## Monthly Buyer Email

After each patrol run, send a digest email to Intel Pack buyers:

**Subject:** "Intel Pack Update: [N] new credits added this month"
**Body:** List new programs with realistic credit values and application URLs.
**Framing:** Value-first — "We found $X in new credits worth tracking."

This keeps the $49 one-time purchase feeling like ongoing value without requiring a subscription.

---

## Versioning

- Tag each significant data update: `git tag data-refresh-YYYY-MM`
- Keep `programs.json` as the source of truth
- The markdown catalog (`work/dev-perk-catalog.md`) is a human-readable snapshot — reconcile quarterly
