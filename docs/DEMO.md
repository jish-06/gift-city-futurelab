# FXNexus demo guide

## Local demo sign-in

The frontend opens on a sign-in page. The two configured local accounts are:

- **Maker:** `maker@fxnexus.local` / `Maker-Demo-2026!`
- **Checker:** `checker@fxnexus.local` / `Checker-Demo-2026!`

The credentials can be changed in `backend/.env` using `DEMO_MAKER_EMAIL`, `DEMO_MAKER_PASSWORD`, `DEMO_CHECKER_EMAIL` and `DEMO_CHECKER_PASSWORD`. Sessions are random bearer tokens stored in backend memory and expire after `DEMO_SESSION_HOURS`. A backend restart invalidates all sessions. This is prototype authentication, not production identity management.

## Recommended five-minute walkthrough

1. Sign in as Maker. Overview displays gross open invoice exposures and evidence-backed recommendations.
2. Transactions: record a partial customer receipt as converted into INR, retained in foreign currency, converted into another foreign currency (with a destination-units-per-source-unit rate), or unknown. Show that a receipt is not treated as if it disappeared.
3. Transactions: change an expected payment date. Hedge alignment displays maturity/roll-watch findings when the illustrative tolerance is exceeded.
4. Recommendations: inspect evidence, assumptions and calculation snapshot. Create a hedge-adjustment or roll-review proposal.
5. Submit the proposal to the checker queue. Sign out and sign in as Checker.
6. Approvals: complete the four source/hedge/maturity checks and approve internally. The maker cannot approve their own proposal.
7. Simulate the approved action. Explain that this is a local simulation, not a broker/bank order and it does not modify a real hedge.
8. Pipeline: demonstrate win-probability-weighted forecast exposure and 25/50/75% soft-planning coverage scenarios before an invoice exists. Change CRM probability/payment date through the event simulator; set the stage to CONTRACT_SIGNED / WON to move the pre-invoice planning amount to 100%, or LOST to exclude it.
9. Shadow balances: separate point-in-time cash snapshots from settlement movements, resolve unknown treatments, and carry a supported conversion into a different foreign currency into that destination-currency cash exposure without double counting the snapshots.
10. Netting demonstrates reciprocal entity positions; Liquidity stresses FX-linked receipts, payments, a margin call and available credit-line capacity; Working capital compares indicative hedge conversion with early discount / local-currency financing costs; Scenario lab and Accounting drafts demonstrate the remaining differentiators.
11. Connections shows the backend-only Zoho Books read-only connector and Twelve Data reference-rate adapter when configured, plus the CRM/bank/AI/execution boundaries.

## Sample scenario

The seeded USD invoice EXP-1042 originally represents USD 50,000 and has USD 35,000 outstanding. A USD 15,000 payment is seeded as retained in USD. The seed also includes a USD 50,000 forward contract and a USD 15,000 USD cash snapshot. The cash snapshot and payment ledger are deliberately displayed separately: they are different record types and must not be added together without reconciliation evidence.

The matching rule adds retained foreign-currency cash and supported cross-currency cash conversions back to compatible asset exposure for hedge matching, including when an invoice is fully settled. It is a demonstration rule, not a complete reconciliation across multiple bank accounts, cash pools, subsidiaries or all foreign-currency cash balances.

For a clean demo reset, stop the backend, delete `backend/fxnexus.db`, and restart the server to regenerate the sample data. Keep a copy of any local data you wish to preserve before deleting the database.
