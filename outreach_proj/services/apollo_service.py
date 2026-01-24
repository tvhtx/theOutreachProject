"""
Apollo.io Contact Discovery Service

Provides direct integration with Apollo's API to find and enrich contacts
directly within the Resonate app - eliminating the need for separate subscriptions.

Apollo Free Tier: 60 credits/month
Apollo Basic: $49/mo for 2,400 credits

API Docs: https://apolloio.github.io/apollo-api-docs/
"""

import os
from dataclasses import dataclass, asdict
from typing import Optional
import httpx


# Get Apollo API key from environment
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "")


@dataclass
class ApolloContact:
    """Contact data structure from Apollo.io"""
    first_name: str
    last_name: str
    email: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    headline: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    company_website: Optional[str] = None
    company_size: Optional[str] = None
    industry: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


class ApolloService:
    """
    Apollo.io API Integration Service
    
    Provides contact search, enrichment, and email finding capabilities.
    """
    
    BASE_URL = "https://api.apollo.io/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or APOLLO_API_KEY
        self._client = None
    
    @property
    def is_configured(self) -> bool:
        """Check if Apollo is configured with a valid API key."""
        return bool(self.api_key and len(self.api_key) > 10)
    
    def _get_client(self) -> httpx.Client:
        if not self._client:
            self._client = httpx.Client(timeout=30.0)
        return self._client
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make an authenticated request to Apollo API."""
        if not self.is_configured:
            raise ValueError("Apollo API key not configured. Set APOLLO_API_KEY environment variable.")
        
        # Use headers for API key (as per Apollo's deprecation notice)
        headers = kwargs.pop("headers", {})
        headers["x-api-key"] = self.api_key
        headers["Content-Type"] = "application/json"
        
        url = f"{self.BASE_URL}/{endpoint}"
        client = self._get_client()
        
        response = client.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        
        return response.json()
    
    def search_people(
        self,
        company_name: Optional[str] = None,
        job_titles: Optional[list[str]] = None,
        person_locations: Optional[list[str]] = None,
        company_locations: Optional[list[str]] = None,
        industries: Optional[list[str]] = None,
        company_sizes: Optional[list[str]] = None,
        seniority_levels: Optional[list[str]] = None,
        limit: int = 25,
        page: int = 1,
    ) -> tuple[list[ApolloContact], int]:
        """
        Search Apollo's database for people matching criteria.
        
        Uses the new 2-step API flow (as of late 2025):
        1. mixed_people/api_search - Get IDs and partial data
        2. people/bulk_match - Get full enriched data (uses credits)
        
        Args:
            company_name: Company name to search within
            job_titles: List of job titles (e.g., ["Software Engineer", "Data Scientist"])
            person_locations: List of locations (e.g., ["New York", "California"])
            company_locations: Company HQ locations
            industries: Industry filters
            company_sizes: Company size ranges (e.g., ["11-50", "51-200"])
            seniority_levels: Seniority filters (e.g., ["senior", "manager", "director"])
            limit: Max results per page (1-100)
            page: Page number
            
        Returns:
            Tuple of (list of contacts, total count)
        """
        payload = {
            "per_page": min(limit, 100),
            "page": page,
        }
        
        # Add filters
        if company_name:
            payload["q_organization_name"] = company_name
        
        if job_titles:
            payload["person_titles"] = job_titles
        
        if person_locations:
            payload["person_locations"] = person_locations
        
        if company_locations:
            payload["organization_locations"] = company_locations
        
        if industries:
            payload["organization_industry_tag_ids"] = industries
        
        if company_sizes:
            # Apollo uses ranges like "1,10" for 1-10 employees
            size_map = {
                "1-10": "1,10",
                "11-50": "11,50",
                "51-200": "51,200",
                "201-500": "201,500",
                "501-1000": "501,1000",
                "1001-5000": "1001,5000",
                "5001-10000": "5001,10000",
                "10001+": "10001,1000000"
            }
            payload["organization_num_employees_ranges"] = [
                size_map.get(s, s) for s in company_sizes
            ]
        
        if seniority_levels:
            payload["person_seniorities"] = seniority_levels
        
        try:
            # Step 1: Use new api_search endpoint (returns IDs and basic data)
            data = self._make_request("POST", "mixed_people/api_search", json=payload)
            
            contacts = []
            people_data = data.get("people", [])
            
            # Extract person IDs for bulk enrichment
            person_ids = [p.get("id") for p in people_data if p.get("id")]
            
            # Step 2: If we have IDs, get full enriched data via bulk_match
            if person_ids:
                try:
                    enrich_payload = {"ids": person_ids[:limit]}
                    enrich_data = self._make_request("POST", "people/bulk_match", json=enrich_payload)
                    # Use enriched data if available
                    enriched_people = enrich_data.get("people", [])
                    if enriched_people:
                        people_data = enriched_people
                except Exception as e:
                    # Fall back to basic data from api_search if bulk_match fails
                    print(f"[Apollo] bulk_match failed, using basic data: {e}")
            
            for person in people_data:
                org = person.get("organization", {}) or {}
                phone_numbers = person.get("phone_numbers", []) or []
                
                contacts.append(ApolloContact(
                    first_name=person.get("first_name", ""),
                    last_name=person.get("last_name", ""),
                    email=person.get("email"),
                    company=org.get("name"),
                    job_title=person.get("title"),
                    linkedin_url=person.get("linkedin_url"),
                    phone=phone_numbers[0].get("raw_number") if phone_numbers else None,
                    city=person.get("city"),
                    state=person.get("state"),
                    country=person.get("country"),
                    headline=person.get("headline"),
                    company_linkedin_url=org.get("linkedin_url"),
                    company_website=org.get("website_url"),
                    company_size=org.get("estimated_num_employees"),
                    industry=org.get("industry"),
                ))
            
            total = data.get("pagination", {}).get("total_entries", len(contacts))
            return contacts, total
            
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.text
            except:
                pass
            print(f"[Apollo] Search error {e.response.status_code}: {error_detail}")
            
            if e.response.status_code == 422:
                # Validation error - return empty results
                return [], 0
            raise
    
    def enrich_person(
        self,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        company_name: Optional[str] = None,
        linkedin_url: Optional[str] = None,
    ) -> Optional[ApolloContact]:
        """
        Enrich a person's data using available information.
        
        Provide at least one of:
        - email
        - first_name + last_name + company_name
        - linkedin_url
        """
        payload = {}
        
        if email:
            payload["email"] = email
        if first_name:
            payload["first_name"] = first_name
        if last_name:
            payload["last_name"] = last_name
        if company_name:
            payload["organization_name"] = company_name
        if linkedin_url:
            payload["linkedin_url"] = linkedin_url
        
        if not payload:
            return None
        
        try:
            data = self._make_request("POST", "people/match", json=payload)
            person = data.get("person", {})
            
            if not person:
                return None
            
            org = person.get("organization", {}) or {}
            phone_numbers = person.get("phone_numbers", []) or []
            
            return ApolloContact(
                first_name=person.get("first_name", ""),
                last_name=person.get("last_name", ""),
                email=person.get("email"),
                company=org.get("name"),
                job_title=person.get("title"),
                linkedin_url=person.get("linkedin_url"),
                phone=phone_numbers[0].get("raw_number") if phone_numbers else None,
                city=person.get("city"),
                state=person.get("state"),
                country=person.get("country"),
                headline=person.get("headline"),
                company_linkedin_url=org.get("linkedin_url"),
                company_website=org.get("website_url"),
                company_size=org.get("estimated_num_employees"),
                industry=org.get("industry"),
            )
            
        except httpx.HTTPStatusError:
            return None
    
    def find_email(
        self,
        first_name: str,
        last_name: str,
        company_domain: str,
    ) -> Optional[str]:
        """
        Find a person's email address given their name and company.
        
        Args:
            first_name: Person's first name
            last_name: Person's last name  
            company_domain: Company domain (e.g., "google.com") or company name
        """
        result = self.enrich_person(
            first_name=first_name,
            last_name=last_name,
            company_name=company_domain,
        )
        
        return result.email if result else None
    
    def search_organizations(
        self,
        name: Optional[str] = None,
        domains: Optional[list[str]] = None,
        locations: Optional[list[str]] = None,
        industries: Optional[list[str]] = None,
        sizes: Optional[list[str]] = None,
        limit: int = 25,
        page: int = 1,
    ) -> list[dict]:
        """
        Search for organizations/companies.
        
        Returns company data including employee count, industry, etc.
        """
        payload = {
            "per_page": min(limit, 100),
            "page": page,
        }
        
        if name:
            payload["q_organization_name"] = name
        if domains:
            payload["organization_domains"] = domains
        if locations:
            payload["organization_locations"] = locations
        
        try:
            data = self._make_request("POST", "mixed_companies/search", json=payload)
            
            organizations = []
            for org in data.get("organizations", []):
                organizations.append({
                    "name": org.get("name"),
                    "website": org.get("website_url"),
                    "linkedin_url": org.get("linkedin_url"),
                    "industry": org.get("industry"),
                    "employee_count": org.get("estimated_num_employees"),
                    "city": org.get("city"),
                    "state": org.get("state"),
                    "country": org.get("country"),
                    "founded_year": org.get("founded_year"),
                    "keywords": org.get("keywords", []),
                })
            
            return organizations
            
        except httpx.HTTPStatusError:
            return []
    
    def get_credits_info(self) -> dict:
        """Get current API credit usage (if available)."""
        # Apollo doesn't have a public endpoint for this
        # but we can return configuration status
        return {
            "configured": self.is_configured,
            "api_key_preview": f"{self.api_key[:8]}..." if self.api_key else None,
        }


# Singleton instance
apollo_service = ApolloService()


def get_apollo_service(api_key: Optional[str] = None) -> ApolloService:
    """Get Apollo service instance."""
    if api_key:
        return ApolloService(api_key)
    return apollo_service
