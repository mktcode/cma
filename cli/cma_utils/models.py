from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WebsiteMapping:
    sender_email: str
    website_domain: str
