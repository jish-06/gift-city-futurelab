# Product scope and differentiation hypotheses

## Core product

FXNexus is a vendor-neutral, event-driven FX exposure operations overlay. It consumes events and records from accounting/ERP/CRM/bank/treasury sources, standardises transaction lifecycle data, recalculates exposures, reconciles hedge positions, and routes explainable recommendations through human approval.

## Gemini-proposed differentiators retained in this MVP

1. **Pre-invoice pipeline-triggered hedging:** CRM/pipeline deals, win probabilities, expected payment dates, probability-weighted scenario exposure and 25/50/75% soft-planning coverage bands. The internal CRM event simulator changes probability, amount, stage and expected payment date; CONTRACT_SIGNED / WON moves the planning factor to 100%, while LOST / CANCELLED is excluded. A signed pipeline order remains pre-invoice until the invoice is ingested. No auto-trade.
2. **Dynamic roll/adjustment engine:** payment date changes trigger maturity mismatch recommendations and a distinct roll/adjustment review proposal. The MVP never rolls or rebooks a real contract.
3. **Shadow balance and cross-currency settlement:** separate point-in-time cash snapshots from the settlement movement ledger; classify retained, INR-converted, foreign-currency-converted (with an explicit destination-units-per-source-unit rate), unknown and cross-currency-review treatments. Foreign currency held after conversion is represented as a destination-currency cash asset and can be matched to compatible hedge records, including after the source invoice is settled, while snapshots and movements are not added together. Operators can resolve uncertain treatment with an auditable event. No live GL/bank scanner yet.
4. **Intercompany netting:** reciprocal entity positions are grouped by currency and checked for both reciprocal entity direction and the demo seven-day timing window. This is economic netting only, not a legal settlement instruction.
5. **Liquidity/margin co-pilot:** simplified cash stress test includes a user-supplied margin call, FX shock, committed credit-line limit, drawn balance, undrawn capacity, utilisation and residual shortfall after available line capacity. It is not a derivative valuation, facility covenant or collateral model.
6. **Working capital vs hedge cost:** compares illustrative forward conversion value, early payment discount and financing cost. It is not an optimal financing recommendation.
7. **IFRS 9 / Ind AS 109 / ASC 815 documentation autopilot:** generates a draft designation memo and evidence checklist. No effectiveness conclusion, valuation, journal entry or compliance claim without supporting inputs and professional review.
8. **Headless overlay:** backend API, import routes and connector adapters are designed to sit on top of Zoho, Tally, NetSuite, SAP, CRM and bank systems, not replace them. Only the Zoho Books read-only fetch and Twelve Data rate adapter are partially wired in this MVP; other providers remain integration targets.
9. **Emerging-market corridor focus:** India exporter / USD-INR first; architecture keeps currency pair, entity and source fields explicit. Regulatory eligibility is not inferred from a currency pair.

## Differentiation claims to validate

Do not claim these workflows are unique or absent from incumbents without customer interviews and feature-level competitor verification. Test whether target exporters still manually reconcile ERP invoices, bank receipts, forward confirmations and revised shipment/payment dates despite existing software.

## Deliberately excluded from MVP execution

- Autonomous real FX derivatives execution, rollovers, cancellation or rebooking.
- Automatic bank account access without consent and authorised integration.
- Production CRM or bank connectors.
- Legally enforceable intercompany settlement.
- Production-grade margin valuation / collateral modelling.
- Certified hedge accounting.

## Authentication and role boundaries

The local UI has a sign-in page with separate Maker and Checker demo accounts. The backend issues random in-memory bearer sessions and enforces Maker-only proposal creation/submission and Checker-only approval/simulation, including same-user separation. Sessions expire and are invalidated on logout or backend restart. This is a local demo control only: use a managed identity provider, MFA, persistent revocable sessions and tenant-aware authorisation before external deployment.
