# FXNexus — Event-driven FX exposure & treasury workflow MVP

FXNexus is a working, local-first prototype for exporters and mid-market businesses managing foreign-currency receivables, payables, cash balances and hedge records.

It demonstrates a **headless treasury overlay**: ingest business events, maintain transaction state, calculate exposures, reconcile hedge records, surface actionable recommendations, and route proposals through maker-checker approval. It also includes the wider challenge differentiators as explicit, demoable modules: pre-invoice pipeline scenarios, dynamic roll/adjustment planning, shadow-balance detection, intercompany netting, liquidity/margin stress tests, working-capital-vs-hedge-cost comparison, and draft hedge-accounting documentation.

> **Important prototype boundary:** FXNexus does not execute real derivatives, send trade instructions to a bank, make legal/accounting determinations, or provide investment advice. The execution adapter is simulation-only. Recommendations are decision support and require qualified review. Accounting outputs are drafts requiring professional validation.

## Quick start (Windows PowerShell)

Requirements: Python 3.11+ and Node.js 22.12+ (the project pins Vite 8.3.8).

```powershell
# 1. Backend — no PowerShell script activation is required
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# 2. Frontend — open a second terminal
cd frontend
npm.cmd install
Copy-Item .env.example .env
npm.cmd run dev
```

Open http://localhost:5173. API docs: http://localhost:8000/docs. The frontend starts at the FXNexus sign-in page.

**Local demo accounts** (also listed on the sign-in screen):
- Maker: `maker@fxnexus.local` / `Maker-Demo-2026!`
- Checker: `checker@fxnexus.local` / `Checker-Demo-2026!`

Change these in `backend/.env` before sharing the project. This is a local prototype login, not production identity management. Sessions are held in backend memory and expire after the configured period.

The backend creates a local SQLite database and seeds a demo company on first start. No third-party API keys are required for the seeded demo.

## Demo flow

1. Open **Overview** and inspect current exposures and alerts.
2. Open **Transactions**. Use the event simulator to record a partial payment and choose whether it was converted to INR or retained in USD.
3. Open **Recommendations**. Inspect the generated evidence-backed mismatch.
4. As Maker, create an action proposal and submit it for approval.
5. Sign out, sign in as Checker, verify all four controls, and approve internally. The separate simulation never changes a real hedge or sends a bank order.
6. Explore **Pipeline** soft-planning bands, **Hedge alignment** roll watch, **Shadow balances**, **Netting**, **Liquidity**, **Working capital**, **Scenario lab**, and **Accounting drafts**.
7. Open **Connections** to test the Zoho read-only fetch and Twelve Data reference-rate adapter when you have configured credentials.

## Architecture

- Frontend: React + TypeScript + Vite + Lucide icons; chart is rendered with a responsive CSS/SVG-free bar layout so it does not depend on chart-container measurement.
- Backend: Python + FastAPI + Pydantic + SQLAlchemy.
- Storage: SQLite by default; PostgreSQL/Supabase via `DATABASE_URL`.
- Money: Python `Decimal` and SQL `NUMERIC`/decimal strings. Avoid JS floating point for financial calculations; frontend displays backend-calculated strings.
- Integrations: Zoho Books read-only list-fetch scaffold and Twelve Data reference-rate adapter. OpenAI has a server-side key placeholder only; an LLM is not invoked. CRM and bank providers are not live-connected. Deterministic demo data works without credentials.

## Environment variables and keys

See `backend/.env.example` and `frontend/.env.example`.

### Required to run locally

None. The sample-data mode works with no credentials.

### Optional integrations

| Variable | Obtain it from | Used for |
|---|---|---|
| `ZOHO_CLIENT_ID` | Zoho API Console → create Server-based application | OAuth client ID |
| `ZOHO_CLIENT_SECRET` | Same Zoho application | OAuth client secret |
| `ZOHO_REFRESH_TOKEN` | OAuth consent flow with `access_type=offline` and scopes below | Server-side token refresh |
| `ZOHO_ORGANIZATION_ID` | Zoho Books organization settings / API response | Selects the Books organisation |
| `ZOHO_ACCOUNTS_URL` | Use `https://accounts.zoho.in` for India DC | OAuth token endpoint base |
| `ZOHO_API_BASE_URL` | Use `https://www.zohoapis.in/books/v3` for India DC | Books API base |
| `TWELVE_DATA_API_KEY` | Twelve Data dashboard | Indicative FX reference rates; not executable quotes |
| `OPENAI_API_KEY` | OpenAI API platform | Optional narrative explanation only; never calculations or trade decisions |
| `OPENAI_MODEL` | Model available to your API project | Optional explanation model (default in code is configurable) |
| `DATABASE_URL` | Supabase project → Connect → Transaction pooler/connection string | Optional hosted PostgreSQL |

Zoho scopes for this read-only prototype:
`ZohoBooks.invoices.READ,ZohoBooks.customerpayments.READ`

The backend currently expects an OAuth refresh token (use Zoho Self Client to generate a grant code, exchange it for a refresh token, then paste the refresh token into `.env`). The `ZOHO_REDIRECT_URI` setting is reserved for a future full server-based OAuth callback flow; no callback route is implemented in this starter. Never put Zoho client secrets, refresh tokens, OpenAI keys, Twelve Data keys, or Supabase secret keys in frontend variables. Do not commit `.env` files.

### Supabase note

The MVP uses SQLAlchemy directly. If using Supabase PostgreSQL, set `DATABASE_URL` to the PostgreSQL connection string (prefer the pooler for hosted deployments), e.g. `postgresql+psycopg://postgres.<project-ref>:<password>@<pooler-host>:6543/postgres`. The app does not need Supabase browser keys for its current architecture. If you later add Supabase Auth/client access, use a publishable key in the browser and keep any secret key server-only.

## What is implemented vs scaffolded

| Capability | Status |
|---|---|
| Invoice/payment/hedge demo data | Working |
| Event ingestion and idempotency | Working; includes invoice-date and mapped CRM-deal update event types |
| Exposure recalculation and hedge mismatch detection | Working MVP rules |
| Recommendations, evidence, action proposals | Working |
| Maker-checker approvals and stale snapshot protection | Working local demo workflow with separate Maker/Checker logins; not production identity management |
| Simulated hedge adjustment / roll proposal | Working maker-checker proposal and local simulation; no external order or real contract mutation |
| Pipeline probability scenarios | Working model with 25/50/75% soft-planning coverage bands; signed/won stages move to 100% firm pre-invoice planning, lost/cancelled deals are excluded; not an automated trade |
| FX/payment-delay/invoice-change scenario lab | Working illustrative USD/INR scenario endpoint and UI |
| India-first corridor orientation | INR base model and currency-pair-aware records; no regulatory eligibility determination |
| Shadow-balance / settlement reconciliation | Working demo ledger separates cash snapshots from payment movements, resolves retained/INR-converted/foreign-cross-converted/unknown treatments, carries supported foreign-currency conversions into destination-currency cash exposure using an explicit conversion rate, and flags unresolved records; no live GL/bank statement scanner |
| Intercompany netting | Working illustrative calculation; requires reciprocal entity positions and a seven-day demo timing window |
| Liquidity and margin stress test | Working simplified calculator with FX-linked receipts, payments, margin call, committed credit-line limit, drawn amount, undrawn capacity, utilisation and post-facility shortfall; cash snapshot is an initial input |
| Working-capital vs hedge-cost comparison | Working illustrative calculator |
| Ind AS 109 / IFRS 9 / ASC 815 draft memo | Template draft only; not a compliance opinion or journal-entry generator |
| Zoho Books invoice/payment retrieval | OAuth refresh + read-only API fetch scaffold; fetched objects are not yet mapped/imported into local tables |
| Twelve Data | Reference-rate adapter scaffold |
| CRM / ERP connector targets | Headless integration design for Zoho, Tally, NetSuite, SAP, HubSpot and Salesforce; only Zoho Books read-only retrieval is scaffolded, CRM provider OAuth/webhooks and ERP imports are not connected |
| OANDA / IBKR | Not integrated; intentionally no broker execution |
| Bank APIs / AA / Setu | Not integrated; use explicit synthetic/imported cash snapshots and settlement events |

## Tests

```bash
cd backend
pytest
```

## Authentication notes

The sign-in page uses two local demo accounts with environment-configured credentials. The backend issues expiring in-memory bearer sessions and enforces Maker-only proposal submission and Checker-only approval/simulation. This is useful for a local prototype walkthrough, but it is not a substitute for OIDC/Supabase Auth, MFA, persistent session revocation, multi-tenant role-based authorisation or production security review.

## Production hardening still required

Before real company use: proper identity provider and MFA; tenant-level PostgreSQL row security; encrypted OAuth token vault; signed webhook verification; background queue/outbox; full audit immutability/WORM export; robust FX instrument eligibility and legal-entity rules; bank/custodian integrations; professional review of regulatory/accounting logic; security review and penetration testing. The demo auth uses configurable environment-based Maker/Checker accounts and in-memory tokens for local demonstration only.

### v0.3 usability fixes
The audit trail now presents readable event summaries and keeps raw payloads behind an expandable technical-details section. Recommendation details show the financial calculation inputs/outputs separately from the SHA-256 trace identifier. Accounting drafts download as PDF files. The Connections page can test Zoho OAuth and discover accessible Books organisations before an organisation ID is configured; see `docs/API_KEYS.md` for required read-only scopes.
