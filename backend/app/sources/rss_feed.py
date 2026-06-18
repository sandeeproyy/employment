"""
AutoApply — RSS Feed Job Source

Generic RSS/Atom feed parser for job boards and company blogs
that publish job listings via feeds.
"""

import logging
import re
from datetime import datetime

import feedparser
import httpx

from app.sources.base import JobSource, RawJob, clean_html

logger = logging.getLogger(__name__)


class RSSFeedSource(JobSource):
    name = "RSS Feed"
    source_type = "rss"

    async def discover(self, config: dict) -> list[RawJob]:
        """
        Fetch jobs from an RSS/Atom feed.
        Config requires: {"url": "https://...feed.xml", "company": "Company Name"}
        """
        feed_url = config.get("url", "")
        company = config.get("company", "Unknown")

        if not feed_url:
            logger.warning("RSS: no feed URL configured")
            return []

        jobs = []
        try:
            # Fetch feed content
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(feed_url)
                response.raise_for_status()
                content = response.text

            # Parse feed
            feed = feedparser.parse(content)
            entries = feed.get("entries", [])

            logger.info(f"RSS [{company}]: Found {len(entries)} entries")

            for entry in entries:
                try:
                    job = self._parse_entry(entry, company, feed_url)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.error(f"RSS: Error parsing entry: {e}")
                    continue

        except Exception as e:
            logger.error(f"RSS [{feed_url}]: {e}")

        return jobs

    def _parse_entry(self, entry: dict, company: str, feed_url: str) -> RawJob | None:
        """Parse a single feed entry into a RawJob."""
        title = entry.get("title", "").strip()
        if not title:
            return None

        # Description
        description = ""
        if entry.get("summary"):
            description = entry["summary"]
        elif entry.get("content"):
            description = entry["content"][0].get("value", "")

        description = clean_html(description)

        # URL
        source_url = entry.get("link", feed_url)

        # Published date
        discovered = datetime.utcnow()
        if entry.get("published_parsed"):
            try:
                import time
                discovered = datetime.fromtimestamp(
                    time.mktime(entry["published_parsed"])
                )
            except (ValueError, OSError):
                pass

        # Tags/categories
        tags = [tag.get("term", "") for tag in entry.get("tags", [])]
        location = ""
        for tag in tags:
            if any(geo in tag.lower() for geo in ["remote", "onsite", "hybrid"]):
                location = tag
                break

        remote_allowed = "remote" in (location + title + description).lower()

        return RawJob(
            title=title,
            company=company,
            description=description[:5000],
            location=location,
            remote_allowed=remote_allowed,
            posted_at=discovered.strftime("%Y-%m-%d"),
            source="rss",
            source_url=source_url,
            apply_url=source_url,
            discovered_at=discovered,
            raw_data={"feed_url": feed_url, "tags": tags},
        )
