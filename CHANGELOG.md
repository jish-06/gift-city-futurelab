# Changelog

## 0.2.0 — November 18, 2026

- Added a local Maker / Checker sign-in page and backend-enforced role boundaries.
- Fixed page scrolling with independent workspace and sidebar scroll containers.
- Replaced the chart-library responsive container with an in-layout CSS bar chart to avoid blank chart space when the parent has no measured height.
- Added the Shadow balances page with separate cash snapshots and settlement movements, including retained and cross-currency-converted cash treatments.
- Added event-driven CRM pipeline updates, signed / won firm pre-invoice treatment, lost-deal exclusion and soft planning bands.
- Added a dynamic hedge maturity / roll watch with a review proposal path; no real rollover is performed.
- Tightened intercompany netting to require reciprocal entity records and a seven-day demo timing window.
- Extended liquidity stress to show margin-call effects, undrawn credit capacity, facility utilisation and shortfall after available credit.
- Kept working-capital comparisons, accounting draft memos, scenario analysis, Zoho Books read-only retrieval and Twelve Data reference-rate support.
- Moved Vite and the React Vite plugin into `devDependencies`; the Picomatch advisory may still appear in the full development audit until an upstream fix is available.
- Added regression coverage for signed / lost pipeline stages and credit-line liquidity calculations.

## Prototype boundary

CRM, bank, GL, ERP vendors beyond the Zoho Books read-only fetch, LLM explanations, and real derivative execution are not live integrations in this build. Authentication is local demo authentication, not production identity management. All financial actions are simulations or review proposals.

## v0.3.0 — usability and connector diagnostics
- Replaced raw audit JSON in the default table view with human-readable event summaries; full source payload remains available under Technical details.
- Replaced the misleading recommendation snapshot display with the actual exposure/hedge/mismatch figures and assumptions. The SHA-256 value is now correctly labelled as a technical trace reference.
- Accounting draft generation now stores an audit event and downloads a formatted PDF memo instead of opening a browser alert.
- Added Zoho Books read-only connection diagnostics that can validate OAuth and discover accessible organisations before an organisation ID is configured. When an organisation is selected, the test also checks invoice and customer-payment reads.
- Added ReportLab to backend requirements for PDF generation.
- CRM and bank connectors remain extension points, not live integrations; Twelve Data remains an indicative read-only reference-rate adapter.
