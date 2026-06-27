from __future__ import annotations

import re

SECRET_FILTER_VERSION = "secret-v1"

SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bASIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[opusr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
)


def looks_like_secret(content: str) -> bool:
    return any(pattern.search(content) for pattern in SECRET_PATTERNS)
