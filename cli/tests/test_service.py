from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cma_utils.models import WebsiteMapping
from cma_utils.service import MappingService
from cma_utils.validators import ValidationError


class FakeRepository:
    def __init__(self):
        self.storage: dict[str, set[str]] = {}
        self.ready = False

    def ensure_ready(self) -> None:
        self.ready = True

    def add_mapping(self, sender_email: str, website_domain: str) -> WebsiteMapping:
        self.storage.setdefault(sender_email, set()).add(website_domain)
        return WebsiteMapping(sender_email=sender_email, website_domain=website_domain)

    def get_mappings(self, sender_email: str) -> list[WebsiteMapping]:
        return [
            WebsiteMapping(sender_email=sender_email, website_domain=domain)
            for domain in sorted(self.storage.get(sender_email, set()))
        ]

    def list_mappings(self) -> list[WebsiteMapping]:
        mappings: list[WebsiteMapping] = []
        for email, domains in sorted(self.storage.items()):
            for domain in sorted(domains):
                mappings.append(WebsiteMapping(sender_email=email, website_domain=domain))
        return mappings

    def delete_mapping(self, sender_email: str, website_domain: str | None = None) -> bool:
        domains = self.storage.get(sender_email)
        if not domains:
            return False
        if website_domain is None:
            del self.storage[sender_email]
            return True
        if website_domain not in domains:
            return False
        domains.remove(website_domain)
        if not domains:
            del self.storage[sender_email]
        return True


class MappingServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = FakeRepository()
        self.service = MappingService(self.repository)

    def test_allow_normalizes_inputs(self) -> None:
        mapping = self.service.allow(" Sales@Example.COM ", "WWW.Example.com.")
        self.assertEqual(mapping, WebsiteMapping("sales@example.com", "www.example.com"))

    def test_lookup_returns_all_domains_for_email(self) -> None:
        self.service.allow("owner@example.com", "alpha.example")
        self.service.allow("owner@example.com", "beta.example")
        self.assertEqual(
            self.service.lookup("owner@example.com"),
            [
                WebsiteMapping("owner@example.com", "alpha.example"),
                WebsiteMapping("owner@example.com", "beta.example"),
            ],
        )

    def test_remove_deletes_one_mapping_or_all(self) -> None:
        self.service.allow("hello@example.com", "alpha.example")
        self.service.allow("hello@example.com", "beta.example")
        self.assertTrue(self.service.remove("hello@example.com", "alpha.example"))
        self.assertEqual(self.service.lookup("hello@example.com"), [WebsiteMapping("hello@example.com", "beta.example")])
        self.assertTrue(self.service.remove("hello@example.com"))
        self.assertEqual(self.service.lookup("hello@example.com"), [])

    def test_allow_rejects_invalid_email(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.allow("not-an-email", "example.com")

    def test_allow_rejects_invalid_domain(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.allow("hello@example.com", "https://example.com")
