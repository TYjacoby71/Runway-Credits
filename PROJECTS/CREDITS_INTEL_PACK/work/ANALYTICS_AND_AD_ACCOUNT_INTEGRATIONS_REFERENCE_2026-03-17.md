# NODE: RUNWAY — Analytics, Ad Account, and Verification Integration Reference

**Source type:** Engineer note relayed by Commander Jacob on 2026-03-17
**Purpose:** Capture a practical integration blueprint for what Node: Runway / Clawbot should request or connect when automating startup-perk discovery, verification, application support, and credit deployment.
**Status:** Reference only — not yet verified against every provider's live API terms.

---

## Core Architectural Model

The note separates the system into three layers:

1. **Verification / Proof-of-Life layer**
   - prove the business is legitimate
   - reduce fraud flags
   - pre-fill applications accurately

2. **Action / Target layer**
   - connect to the ad accounts and partner platforms where credits/perks are discovered or applied

3. **Value / Reporting layer**
   - internal dashboard showing secured credits, application status, and next-best actions

This is a strong design frame for Node: Runway.

---

## 1. Verification / Proof-of-Life Integrations

### Plaid API
**Purpose**
- Connect a real business bank account securely.

**Why it matters**
- Strong legitimacy signal for perk providers.
- Can support verification that the business is funded and operational.
- Especially useful if Mercury or another business banking rail is already active.

**Operational use for Runway**
- confirm existence of business banking
- support application trust signals
- potentially fast-track higher-confidence applications

### Secretary of State (SoS) APIs or equivalent state-business registry access
**Purpose**
- Verify LLC / corporation registration details.

**Why it matters**
- Many startup programs ask for incorporation date, legal name, status, and entity type.
- Programmatic retrieval reduces application errors.

**Operational use for Runway**
- legal entity validation
- formation-date lookup
- official business-status verification
- possible fallback to web automation/scraping if state APIs are weak

### Domain registrar / DNS ownership integrations
**Targets mentioned**
- GoDaddy
- Namecheap
- Cloudflare

**Purpose**
- Verify that the startup owns and controls its domain.

**Why it matters**
- Domain ownership is a legitimacy signal.
- Helps validate business email + operating footprint.

**Operational use for Runway**
- verify active company domain
- confirm DNS / registrar control
- support application trust scoring

---

## 2. Action / Target Integrations

### Google Ads API
**Purpose**
- Access the user's Google Ads environment and apply / manage ad-credit workflows where possible.

**Why it matters**
- Many startup perk paths eventually lead to Google ad credits.

**Operational use for Runway**
- verify account existence and readiness
- identify promo / billing / eligibility surfaces
- assist with promotion redemption workflows
- support future spend/credit tracking

### Meta Marketing API
**Purpose**
- Access Facebook / Instagram ad account structures for applied credits and related promotions.

**Why it matters**
- Meta credits or ad-partner offers may be part of startup perk stacks.

**Operational use for Runway**
- verify ad account presence
- identify promotion redemption surfaces
- support account readiness for perk activation

### Stripe API
**Purpose**
- Access startup/perks ecosystem signals and account legitimacy details.

**Why it matters**
- Stripe is both a target platform and a discovery source for startup offers.

**Operational use for Runway**
- confirm live payments infrastructure
- discover Stripe-partner perk surfaces
- support business-legitimacy scoring

### Mercury API / integration surfaces
**Purpose**
- Access business banking/perks ecosystem and structured offer discovery.

**Why it matters**
- Mercury can act as a Golden Key platform for downstream perks.

**Operational use for Runway**
- verify account status
- discover available perks
- use as part of proof-of-life stack

---

## 3. Reporting / Value Layer

### Internal Runway dashboard
**Purpose**
- Node: Runway should function as the analytics layer for this system, not merely feed another analytics tool.

**Suggested dashboard outputs**
- **Total Credits Secured**
- **Monthly Burn Reduction**
- **Application Status Tracker**
- **Next Recommended Perk**
- **Expiration / burn-down tracking**

**Operational implication**
- For Runway, analytics is not primarily GA4-style web analytics.
- Analytics means operational visibility into runway captured, pending applications, expiration risk, and next actions.

---

## Priority Interpretation for Node: Runway

### Highest-value integrations to pursue first
1. **Mercury**
2. **Stripe**
3. **Plaid**
4. **Google Ads**
5. **Meta Marketing API**
6. **Secretary of State / business registry lookup path**
7. **Domain registrar / DNS verification path**

### Why this order
- Mercury + Stripe + Plaid strengthen legitimacy and perk discovery
- Google Ads + Meta create direct action surfaces for ad-credit benefits
- SoS + domain verification strengthen automation reliability for applications

---

## Important caution
This note is architecturally useful, but some claims still need live verification before doctrine is locked:
- whether a given provider truly exposes the needed API surface
- whether promo-code redemption is actually automatable via official API
- whether Stripe/Mercury expose startup-perk inventory through official APIs vs dashboard/manual flows
- where scraping would violate terms or create fragility

Use this file as a **planning reference**, not as fully confirmed platform truth.
