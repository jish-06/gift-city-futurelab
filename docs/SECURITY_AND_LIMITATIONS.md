# Security, regulatory and model limitations

- Local demo now has environment-configured Maker/Checker sign-in and an in-memory bearer-session guard. It is not production identity management. Do not expose this deployment publicly with real data.
- Add OIDC/Supabase Auth, MFA, RBAC, tenant isolation and row-level security before production.
- Encrypt OAuth refresh tokens at rest and rotate credentials. Keep API secrets server-side.
- Verify webhook signatures and use an idempotent inbox/outbox pattern in production.
- Use authoritative bank-confirmed contract details; never infer an executed hedge from an indicative quote.
- Hedge compatibility requires product type, direction, currency pair, entity, underlying item, amount, maturity, settlement and legal eligibility checks. MVP rules are intentionally simplified.
- Cash snapshots and payment movements are kept in separate ledgers. A foreign-currency conversion is only carried into destination-currency exposure when an explicit positive destination-units-per-source-unit rate is supplied; bank advice/account evidence must be verified before operational use.
- Intercompany netting is not automatically legally enforceable. Obtain legal/tax review and verify jurisdictional restrictions.
- RBI/IFSCA rules can change. The application does not determine whether a derivative or account is permitted. Obtain qualified compliance advice for the entity, product, currency pair and transaction.
- IFRS 9 / Ind AS 109 / ASC 815 documentation requires contemporaneous designation, eligible instruments/items, risk management objective, economic relationship, hedge ratio, credit risk assessment, valuation and disclosures. The draft memo is not a compliance opinion.
- Margin/collateral models require actual derivative valuation, CSAs, thresholds, minimum transfer amounts, netting sets and collateral haircuts. The MVP uses user-supplied scenario values only.
- FX reference data may be delayed, limited or subject to licensing. It is not a trade quote.

## Local demo authentication added in this build

The app now requires sign-in before any `/api/*` route except health and login. A Maker account can create and submit proposals; a distinct Checker account can approve/reject/request changes and run the simulation. The backend checks that the checker is not the same email as the requesting maker. Bearer sessions use random tokens and an in-memory expiry registry. Sessions do not survive a backend restart and are not shared across multiple backend workers. This is only a local demonstration guardrail, not a production authentication system. Use an identity provider, MFA, persistent session management, account lifecycle controls, RBAC/tenant isolation and security review before external use.

The sample Maker/Checker credentials in `.env.example` are public demo defaults. Change them in `backend/.env` before sharing the project. Do not commit `.env`.
