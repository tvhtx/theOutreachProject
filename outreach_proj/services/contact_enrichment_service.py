"""
Contact Enrichment Service - Bridge the contact acquisition gap.

This service provides a unified interface for multiple contact data providers,
allowing users to find and enrich contacts directly within the app.

Supported Providers:
- Apollo.io (recommended - has free tier)
- Hunter.io (email finder)
- RocketReach (emails + phones)
- Clearbit (company enrichment)
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import httpx


@dataclass
class EnrichedContact:
    """Unified contact data structure from any provider."""
    first_name: str
    last_name: str
    email: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    source: str = "manual"  # Which provider the data came from


class ContactEnrichmentProvider(ABC):
    """Abstract base class for contact enrichment providers."""
    
    @abstractmethod
    def search_contacts(
        self, 
        company: Optional[str] = None,
        job_title: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 25
    ) -> list[EnrichedContact]:
        """Search for contacts matching criteria."""
        pass
    
    @abstractmethod
    def enrich_contact(self, email: str) -> Optional[EnrichedContact]:
        """Enrich a single contact by email."""
        pass
    
    @abstractmethod
    def find_email(self, first_name: str, last_name: str, company_domain: str) -> Optional[str]:
        """Find email address for a person at a company."""
        pass


class ApolloProvider(ContactEnrichmentProvider):
    """
    Apollo.io integration - Best for prospecting.
    
    Free tier: 60 credits/month
    Paid: $49/mo for 2,400 credits
    
    API Docs: https://apolloio.github.io/apollo-api-docs/
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("APOLLO_API_KEY")
        self.base_url = "https://api.apollo.io/v1"
    
    def search_contacts(
        self, 
        company: Optional[str] = None,
        job_title: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 25
    ) -> list[EnrichedContact]:
        """Search Apollo's 270M+ contact database."""
        if not self.api_key:
            return []
        
        # Build search query
        payload = {
            "api_key": self.api_key,
            "per_page": min(limit, 100),
            "page": 1,
        }
        
        if company:
            payload["q_organization_name"] = company
        if job_title:
            payload["person_titles"] = [job_title]
        if location:
            payload["person_locations"] = [location]
        
        try:
            with httpx.Client(timeout=30) as client:
                response = client.post(
                    f"{self.base_url}/mixed_people/search",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                
                contacts = []
                for person in data.get("people", []):
                    contacts.append(EnrichedContact(
                        first_name=person.get("first_name", ""),
                        last_name=person.get("last_name", ""),
                        email=person.get("email"),
                        company=person.get("organization", {}).get("name"),
                        job_title=person.get("title"),
                        linkedin_url=person.get("linkedin_url"),
                        phone=person.get("phone_numbers", [{}])[0].get("raw_number") if person.get("phone_numbers") else None,
                        city=person.get("city"),
                        state=person.get("state"),
                        source="apollo"
                    ))
                return contacts
                
        except Exception as e:
            print(f"Apollo search error: {e}")
            return []
    
    def enrich_contact(self, email: str) -> Optional[EnrichedContact]:
        """Enrich a contact by email address."""
        if not self.api_key:
            return None
        
        try:
            with httpx.Client(timeout=30) as client:
                response = client.post(
                    f"{self.base_url}/people/match",
                    json={
                        "api_key": self.api_key,
                        "email": email
                    }
                )
                response.raise_for_status()
                person = response.json().get("person", {})
                
                if person:
                    return EnrichedContact(
                        first_name=person.get("first_name", ""),
                        last_name=person.get("last_name", ""),
                        email=email,
                        company=person.get("organization", {}).get("name"),
                        job_title=person.get("title"),
                        linkedin_url=person.get("linkedin_url"),
                        city=person.get("city"),
                        state=person.get("state"),
                        source="apollo"
                    )
        except Exception as e:
            print(f"Apollo enrich error: {e}")
        
        return None
    
    def find_email(self, first_name: str, last_name: str, company_domain: str) -> Optional[str]:
        """Find email using Apollo's email finder."""
        if not self.api_key:
            return None
        
        try:
            with httpx.Client(timeout=30) as client:
                response = client.post(
                    f"{self.base_url}/people/match",
                    json={
                        "api_key": self.api_key,
                        "first_name": first_name,
                        "last_name": last_name,
                        "organization_name": company_domain
                    }
                )
                response.raise_for_status()
                person = response.json().get("person", {})
                return person.get("email")
        except Exception as e:
            print(f"Apollo email finder error: {e}")
        
        return None


class HunterProvider(ContactEnrichmentProvider):
    """
    Hunter.io integration - Best for email finding.
    
    Free tier: 25 searches/month
    Paid: $49/mo for 500 searches
    
    API Docs: https://hunter.io/api-documentation/v2
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("HUNTER_API_KEY")
        self.base_url = "https://api.hunter.io/v2"
    
    def search_contacts(
        self, 
        company: Optional[str] = None,
        job_title: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 25
    ) -> list[EnrichedContact]:
        """Search for contacts at a domain."""
        if not self.api_key or not company:
            return []
        
        try:
            with httpx.Client(timeout=30) as client:
                response = client.get(
                    f"{self.base_url}/domain-search",
                    params={
                        "api_key": self.api_key,
                        "domain": company if "." in company else f"{company}.com",
                        "limit": limit
                    }
                )
                response.raise_for_status()
                data = response.json().get("data", {})
                
                contacts = []
                for email_data in data.get("emails", []):
                    contacts.append(EnrichedContact(
                        first_name=email_data.get("first_name", ""),
                        last_name=email_data.get("last_name", ""),
                        email=email_data.get("value"),
                        company=data.get("organization"),
                        job_title=email_data.get("position"),
                        linkedin_url=email_data.get("linkedin"),
                        phone=email_data.get("phone_number"),
                        source="hunter"
                    ))
                return contacts
                
        except Exception as e:
            print(f"Hunter search error: {e}")
            return []
    
    def enrich_contact(self, email: str) -> Optional[EnrichedContact]:
        """Get information about an email address."""
        if not self.api_key:
            return None
        
        try:
            with httpx.Client(timeout=30) as client:
                response = client.get(
                    f"{self.base_url}/email-finder",
                    params={
                        "api_key": self.api_key,
                        "email": email
                    }
                )
                response.raise_for_status()
                data = response.json().get("data", {})
                
                if data:
                    return EnrichedContact(
                        first_name=data.get("first_name", ""),
                        last_name=data.get("last_name", ""),
                        email=email,
                        company=data.get("company"),
                        job_title=data.get("position"),
                        linkedin_url=data.get("linkedin"),
                        source="hunter"
                    )
        except Exception as e:
            print(f"Hunter enrich error: {e}")
        
        return None
    
    def find_email(self, first_name: str, last_name: str, company_domain: str) -> Optional[str]:
        """Find email using Hunter's email finder."""
        if not self.api_key:
            return None
        
        try:
            with httpx.Client(timeout=30) as client:
                response = client.get(
                    f"{self.base_url}/email-finder",
                    params={
                        "api_key": self.api_key,
                        "first_name": first_name,
                        "last_name": last_name,
                        "domain": company_domain
                    }
                )
                response.raise_for_status()
                data = response.json().get("data", {})
                return data.get("email")
        except Exception as e:
            print(f"Hunter email finder error: {e}")
        
        return None


class ContactEnrichmentService:
    """
    Unified service that tries multiple providers.
    
    Falls back through providers to maximize hit rate.
    """
    
    def __init__(self):
        self.providers: list[ContactEnrichmentProvider] = []
        
        # Initialize available providers based on API keys
        if os.getenv("APOLLO_API_KEY"):
            self.providers.append(ApolloProvider())
        
        if os.getenv("HUNTER_API_KEY"):
            self.providers.append(HunterProvider())
    
    def is_configured(self) -> bool:
        """Check if any enrichment provider is configured."""
        return len(self.providers) > 0
    
    def get_available_providers(self) -> list[str]:
        """Get list of configured provider names."""
        return [p.__class__.__name__.replace("Provider", "") for p in self.providers]
    
    def search_contacts(
        self, 
        company: Optional[str] = None,
        job_title: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 25
    ) -> list[EnrichedContact]:
        """Search all configured providers for contacts."""
        all_contacts = []
        seen_emails = set()
        
        for provider in self.providers:
            try:
                contacts = provider.search_contacts(
                    company=company,
                    job_title=job_title,
                    location=location,
                    limit=limit
                )
                
                # Deduplicate by email
                for contact in contacts:
                    if contact.email and contact.email.lower() not in seen_emails:
                        seen_emails.add(contact.email.lower())
                        all_contacts.append(contact)
                
                # Stop if we have enough contacts
                if len(all_contacts) >= limit:
                    break
                    
            except Exception as e:
                print(f"Provider error: {e}")
                continue
        
        return all_contacts[:limit]
    
    def enrich_contact(self, email: str) -> Optional[EnrichedContact]:
        """Try to enrich a contact using all providers."""
        for provider in self.providers:
            try:
                result = provider.enrich_contact(email)
                if result:
                    return result
            except Exception:
                continue
        return None
    
    def find_email(self, first_name: str, last_name: str, company_domain: str) -> Optional[str]:
        """Try all providers to find an email address."""
        for provider in self.providers:
            try:
                email = provider.find_email(first_name, last_name, company_domain)
                if email:
                    return email
            except Exception:
                continue
        return None


# Singleton instance for easy access
enrichment_service = ContactEnrichmentService()
