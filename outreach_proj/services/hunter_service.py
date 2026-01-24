"""
Hunter.io Contact Discovery Service

Provides email finding and domain search capabilities via Hunter.io API.
Free tier: 25 searches/month, 50 email verifications/month.

API Docs: https://hunter.io/api-documentation/v2
"""

import os
from dataclasses import dataclass, asdict
from typing import Optional
import httpx


# Get Hunter API key from environment
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")


@dataclass
class HunterContact:
    """Contact data structure from Hunter.io"""
    first_name: str
    last_name: str
    email: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None  # Called 'position' in Hunter
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    confidence: Optional[int] = None  # Email confidence score 0-100
    
    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


class HunterService:
    """
    Hunter.io API Integration Service
    
    Provides domain search and email finder capabilities.
    """
    
    BASE_URL = "https://api.hunter.io/v2"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or HUNTER_API_KEY
        self._client = None
    
    @property
    def is_configured(self) -> bool:
        """Check if Hunter is configured with a valid API key."""
        return bool(self.api_key and len(self.api_key) > 10)
    
    def _get_client(self) -> httpx.Client:
        if not self._client:
            self._client = httpx.Client(timeout=30.0)
        return self._client
    
    def _make_request(self, method: str, endpoint: str, params: dict = None) -> dict:
        """Make an authenticated request to Hunter API."""
        if not self.is_configured:
            raise ValueError("Hunter API key not configured. Set HUNTER_API_KEY environment variable.")
        
        if params is None:
            params = {}
        params["api_key"] = self.api_key
        
        url = f"{self.BASE_URL}/{endpoint}"
        client = self._get_client()
        
        response = client.request(method, url, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def domain_search(
        self,
        domain: str,
        company: Optional[str] = None,
        department: Optional[str] = None,
        seniority: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[HunterContact], int]:
        """
        Search for email addresses associated with a domain.
        
        Args:
            domain: Company domain (e.g., "google.com")
            company: Company name (optional, for filtering)
            department: Department filter (e.g., "engineering", "sales", "marketing")
            seniority: Seniority filter (e.g., "junior", "senior", "executive")
            limit: Max results (1-100)
            offset: Pagination offset
            
        Returns:
            Tuple of (list of contacts, total count)
        """
        params = {
            "domain": domain,
            "limit": min(limit, 100),
            "offset": offset,
        }
        
        if department:
            params["department"] = department
        if seniority:
            params["seniority"] = seniority
        
        try:
            data = self._make_request("GET", "domain-search", params=params)
            
            contacts = []
            domain_data = data.get("data", {})
            company_name = company or domain_data.get("organization") or domain
            
            for email_data in domain_data.get("emails", []):
                contacts.append(HunterContact(
                    first_name=email_data.get("first_name", ""),
                    last_name=email_data.get("last_name", ""),
                    email=email_data.get("value"),
                    company=company_name,
                    job_title=email_data.get("position"),
                    linkedin_url=email_data.get("linkedin"),
                    phone=email_data.get("phone_number"),
                    department=email_data.get("department"),
                    confidence=email_data.get("confidence"),
                ))
            
            # Get total from meta
            meta = data.get("meta", {})
            total = meta.get("results", len(contacts))
            
            return contacts, total
            
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_json = e.response.json()
                error_detail = error_json.get("errors", [{}])[0].get("details", str(e))
            except:
                error_detail = str(e)
            print(f"[Hunter] Domain search error {e.response.status_code}: {error_detail}")
            
            if e.response.status_code == 429:
                raise ValueError("Hunter API rate limit exceeded. Free tier: 25 searches/month.")
            raise
    
    def find_email(
        self,
        first_name: str,
        last_name: str,
        domain: str,
        company: Optional[str] = None,
    ) -> Optional[HunterContact]:
        """
        Find a specific person's email address.
        
        Args:
            first_name: Person's first name
            last_name: Person's last name
            domain: Company domain (e.g., "google.com")
            company: Company name (optional)
            
        Returns:
            HunterContact with email if found, None otherwise
        """
        params = {
            "first_name": first_name,
            "last_name": last_name,
            "domain": domain,
        }
        
        try:
            data = self._make_request("GET", "email-finder", params=params)
            
            email_data = data.get("data", {})
            
            if not email_data.get("email"):
                return None
            
            return HunterContact(
                first_name=email_data.get("first_name", first_name),
                last_name=email_data.get("last_name", last_name),
                email=email_data.get("email"),
                company=company or email_data.get("company") or domain,
                job_title=email_data.get("position"),
                linkedin_url=email_data.get("linkedin"),
                confidence=email_data.get("score"),
            )
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    def verify_email(self, email: str) -> dict:
        """
        Verify if an email address is valid and deliverable.
        
        Args:
            email: Email address to verify
            
        Returns:
            Dict with verification status and details
        """
        params = {"email": email}
        
        try:
            data = self._make_request("GET", "email-verifier", params=params)
            
            result = data.get("data", {})
            return {
                "email": result.get("email"),
                "status": result.get("status"),  # valid, invalid, unknown
                "score": result.get("score"),
                "regexp": result.get("regexp"),
                "disposable": result.get("disposable"),
                "webmail": result.get("webmail"),
                "accept_all": result.get("accept_all"),
            }
            
        except httpx.HTTPStatusError as e:
            return {"email": email, "status": "error", "error": str(e)}
    
    def get_account_info(self) -> dict:
        """Get current API usage and limits."""
        try:
            data = self._make_request("GET", "account")
            
            account = data.get("data", {})
            requests = account.get("requests", {})
            
            return {
                "configured": True,
                "email": account.get("email"),
                "plan": account.get("plan_name"),
                "searches_used": requests.get("searches", {}).get("used", 0),
                "searches_available": requests.get("searches", {}).get("available", 0),
                "verifications_used": requests.get("verifications", {}).get("used", 0),
                "verifications_available": requests.get("verifications", {}).get("available", 0),
            }
        except Exception as e:
            return {
                "configured": self.is_configured,
                "error": str(e),
            }


# Singleton instance
hunter_service = HunterService()


def get_hunter_service(api_key: Optional[str] = None) -> HunterService:
    """Get Hunter service instance."""
    if api_key:
        return HunterService(api_key)
    return hunter_service
