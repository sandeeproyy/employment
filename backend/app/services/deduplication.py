"""
AutoApply — Job Deduplication Service

Prevents storing the same job multiple times when found from different sources.
Uses a canonical ID (hash of normalized company + title + location)
plus fuzzy matching for near-duplicates.
"""

import hashlib
import logging
import re

from thefuzz import fuzz

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """Normalize text for comparison: lowercase, strip, remove extra spaces."""
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    # Remove common suffixes/prefixes
    text = re.sub(r'\b(inc|llc|ltd|corp|co|pvt)\b\.?', '', text)
    return text.strip()


def generate_canonical_id(company: str, title: str, location: str = "") -> str:
    """
    Generate a unique canonical ID for a job listing.
    Hash of normalized (company + title + location).
    """
    normalized = f"{normalize_text(company)}|{normalize_text(title)}|{normalize_text(location)}"
    return hashlib.sha256(normalized.encode()).hexdigest()[:32]


def is_duplicate(
    new_title: str,
    new_company: str,
    existing_title: str,
    existing_company: str,
    threshold: int = 85,
) -> bool:
    """
    Check if two job listings are likely duplicates using fuzzy matching.
    Returns True if the similarity score exceeds the threshold.
    """
    company_score = fuzz.ratio(
        normalize_text(new_company),
        normalize_text(existing_company)
    )
    title_score = fuzz.ratio(
        normalize_text(new_title),
        normalize_text(existing_title)
    )

    # Both company and title must be similar
    combined_score = (company_score * 0.4) + (title_score * 0.6)

    if combined_score >= threshold:
        logger.debug(
            f"Duplicate detected: '{new_title}' @ '{new_company}' "
            f"≈ '{existing_title}' @ '{existing_company}' "
            f"(score: {combined_score:.0f})"
        )
        return True

    return False


def merge_source_urls(existing_urls: list[str], new_url: str) -> list[str]:
    """Merge a new source URL into existing URL list (no duplicates)."""
    if new_url and new_url not in existing_urls:
        existing_urls.append(new_url)
    return existing_urls
