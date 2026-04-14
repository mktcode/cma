from __future__ import annotations

from .models import WebsiteMapping
from .repository import MappingRepository
from .validators import normalize_domain, normalize_email


class MappingService:
    def __init__(self, repository: MappingRepository):
        self.repository = repository

    def initialize(self) -> None:
        self.repository.ensure_ready()

    def allow(self, sender_email: str, website_domain: str) -> WebsiteMapping:
        normalized_email = normalize_email(sender_email)
        normalized_domain = normalize_domain(website_domain)
        return self.repository.add_mapping(normalized_email, normalized_domain)

    def lookup(self, sender_email: str) -> list[WebsiteMapping]:
        normalized_email = normalize_email(sender_email)
        return self.repository.get_mappings(normalized_email)

    def list_mappings(self) -> list[WebsiteMapping]:
        return self.repository.list_mappings()

    def remove(self, sender_email: str, website_domain: str | None = None) -> bool:
        normalized_email = normalize_email(sender_email)
        normalized_domain = normalize_domain(website_domain) if website_domain is not None else None
        return self.repository.delete_mapping(normalized_email, normalized_domain)
