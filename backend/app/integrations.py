import httpx
from .config import settings

class IntegrationNotConfigured(Exception): pass

async def zoho_access_token():
    if not all([settings.zoho_client_id, settings.zoho_client_secret, settings.zoho_refresh_token]):
        raise IntegrationNotConfigured("Set ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET and ZOHO_REFRESH_TOKEN in backend/.env")
    async with httpx.AsyncClient(timeout=20) as client:
        r=await client.post(f"{settings.zoho_accounts_url}/oauth/v2/token", params={
            "refresh_token":settings.zoho_refresh_token,
            "client_id":settings.zoho_client_id,
            "client_secret":settings.zoho_client_secret,
            "grant_type":"refresh_token"
        })
        r.raise_for_status(); data=r.json()
        if "access_token" not in data: raise RuntimeError(f"Zoho token response did not contain access_token: {data}")
        return data["access_token"]

async def zoho_get(path, params=None, require_organization=True):
    if require_organization and not settings.zoho_organization_id:
        raise IntegrationNotConfigured("Set ZOHO_ORGANIZATION_ID in backend/.env after selecting a Zoho Books organization")
    token=await zoho_access_token()
    query={**({"organization_id":settings.zoho_organization_id} if settings.zoho_organization_id else {}), **(params or {})}
    async with httpx.AsyncClient(timeout=30) as client:
        r=await client.get(f"{settings.zoho_api_base_url}{path}", params=query, headers={"Authorization":f"Zoho-oauthtoken {token}"})
        r.raise_for_status(); return r.json()

async def fetch_zoho_organizations():
    return await zoho_get("/organizations", {"per_page":100}, require_organization=False)

async def fetch_zoho_invoices():
    return await zoho_get("/invoices", {"per_page":100, "filter_by":"Status.Unpaid"})

async def fetch_zoho_customer_payments():
    return await zoho_get("/customerpayments", {"per_page":100})

async def fetch_twelve_data_rate(symbol="USD/INR"):
    if not settings.twelve_data_api_key: raise IntegrationNotConfigured("Set TWELVE_DATA_API_KEY in backend/.env")
    async with httpx.AsyncClient(timeout=20) as client:
        r=await client.get(f"{settings.twelve_data_base_url}/exchange_rate",params={"symbol":symbol,"apikey":settings.twelve_data_api_key})
        r.raise_for_status(); return r.json()
