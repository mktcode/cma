from __future__ import annotations

import re
from email.utils import parseaddr

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DOMAIN_RE = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))*$")


class ValidationError(ValueError):
    """Raised when user input cannot be normalized safely."""


def normalize_email(value: str) -> str:
    parsed_name, parsed_email = parseaddr(value.strip())
    candidate = parsed_email or value.strip()
    candidate = candidate.lower()
    if parsed_name or not EMAIL_RE.match(candidate):
        raise ValidationError(f"invalid email address: {value}")
    return candidate


def normalize_domain(value: str) -> str:
    candidate = value.strip().lower().rstrip(".")
    if not DOMAIN_RE.match(candidate):
        raise ValidationError(f"invalid website domain: {value}")
    return candidate
