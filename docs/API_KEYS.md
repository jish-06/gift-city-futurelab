# FXNexus credentials and local demo sign-in

## Local Maker / Checker demo accounts

The app includes a login page and two demo roles. Configure these only in `backend/.env`:

```dotenv
DEMO_MAKER_EMAIL=maker@fxnexus.local
DEMO_MAKER_PASSWORD=Maker-Demo-2026!
DEMO_CHECKER_EMAIL=checker@fxnexus.local
DEMO_CHECKER_PASSWORD=Checker-Demo-2026!
DEMO_SESSION_HOURS=8
```

Change the sample passwords before sharing the project. These accounts and the in-memory bearer sessions are for local demonstration only; they are not production identity management.


## 1. Zoho Books (optional)

1. Open Zoho API Console and create a **Self Client** for a quick private prototype (a public multi-customer product should use a proper Server-based OAuth application and a real callback flow).
2. Request only read scopes: `ZohoBooks.invoices.READ,ZohoBooks.customerpayments.READ`.
3. In Self Client → Generate Code, create a temporary grant code for those scopes. Exchange it at your Zoho Accounts `/oauth/v2/token` endpoint using `grant_type=authorization_code`, `client_id`, `client_secret`, and `code`. Request offline access where supported so the response includes a refresh token. The grant code is short-lived; do not paste it into the app as the refresh token.
4. Put the returned `client_id`, `client_secret`, `refresh_token` and your Books `organization_id` into `backend/.env` as `ZOHO_CLIENT_ID`, `ZOHO_CLIENT_SECRET`, `ZOHO_REFRESH_TOKEN`, `ZOHO_ORGANIZATION_ID`.
5. For an India account, use `ZOHO_ACCOUNTS_URL=https://accounts.zoho.in` and `ZOHO_API_BASE_URL=https://www.zohoapis.in/books/v3`. Confirm the data centre from the OAuth response; do not assume all organisations use the India domain.
6. Test `GET http://localhost:8000/api/integrations/zoho/invoices` and `/payments`.

The current starter does not implement the browser redirect/callback route. It uses the refresh token you supply and refreshes short-lived access tokens server-side.

This starter refreshes access tokens server-side and makes read-only list calls. It does not yet map fetched Zoho objects into the local schema; verify field mappings, currencies, payment allocations and tenant ownership before enabling imports.

## 2. Twelve Data (optional)

Create an API key in your Twelve Data account and set `TWELVE_DATA_API_KEY`. Test `GET /api/integrations/fx-rate?symbol=USD/INR`. The returned rate is indicative reference data only. Do not use it as a bank executable forward quote or for trade pricing.

## 3. OpenAI API (optional)

Create an API key in the OpenAI developer platform and set `OPENAI_API_KEY` on the backend only. The MVP does not call the LLM yet; the intended use is plain-language explanation of already calculated facts. Never pass secrets or sensitive company data to an LLM without a data protection review. Financial computations remain deterministic.

## 4. Supabase PostgreSQL (optional)

Create a Supabase project. Copy the PostgreSQL connection string from Project → Connect and set `DATABASE_URL` to a SQLAlchemy-compatible URL. For example, replace the placeholders in:

`postgresql+psycopg://postgres.<project-ref>:<db-password>@<pooler-host>:6543/postgres`

Use a database password with URL-encoded special characters. The backend does not use Supabase client keys. If adding Supabase JS later, use a publishable key client-side with proper RLS; never expose a secret/service-role key in Vite variables.

## Never commit credentials

`.env` is ignored by Git. If a real key is accidentally committed, revoke/rotate it immediately; deleting it in a later commit is not sufficient.


### Zoho read-only connection test

The Connections page now tests OAuth independently of an organisation ID: it requests the accessible Zoho Books organisations using `ZohoBooks.settings.READ`. If an organisation is returned, copy its numeric `organization_id` into `ZOHO_ORGANIZATION_ID` in `backend/.env`, restart the backend, and run the test again. The test then retrieves invoice and customer-payment counts using `ZohoBooks.invoices.READ` and `ZohoBooks.customerpayments.READ`. It performs GET requests only; it does not create or modify Zoho records. If the account has no Zoho Books organisation, create a demo Books organisation in Zoho Books first; FXNexus cannot fetch invoices/payments without one.
