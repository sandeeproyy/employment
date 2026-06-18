"""
AutoApply — Lever Job Source

Fetches jobs from Lever ATS public API.
API: https://api.lever.co/v0/postings/{company}
No authentication required for public postings.

Example companies: openai, figma, stripe, netflix
"""

import logging
import re
from datetime import datetime

import httpx

from app.sources.base import JobSource, RawJob, clean_html

logger = logging.getLogger(__name__)

LEVER_API = "https://api.lever.co/v0/postings/{company}"


class LeverSource(JobSource):
    name = "Lever"
    source_type = "lever"

    async def discover(self, config: dict) -> list[RawJob]:
        """
        Fetch jobs from a Lever company page.
        Config requires: {"company": "company-name"}
        """
        company = config.get("company", "")
        if not company:
            logger.warning("Lever: no company configured")
            return []

        jobs = []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                url = LEVER_API.format(company=company)
                response = await client.get(url)
                response.raise_for_status()

                raw_jobs = response.json()
                logger.info(f"Lever [{company}]: Found {len(raw_jobs)} jobs")

                for raw in raw_jobs:
                    try:
                        job = self._parse_job(raw, company)
                        if job:
                            jobs.append(job)
                    except Exception as e:
                        logger.error(f"Lever: Error parsing job: {e}")
                        continue

        except httpx.HTTPStatusError as e:
            logger.error(f"Lever [{company}]: HTTP {e.response.status_code}")
        except Exception as e:
            logger.error(f"Lever [{company}]: {e}")

        return jobs

    def _parse_job(self, raw: dict, company_slug: str) -> RawJob | None:
        """Parse a single Lever posting into RawJob."""
        title = raw.get("text", "").strip()
        if not title:
            return None

        # Location
        categories = raw.get("categories", {})
        location = categories.get("location", "")
        department = categories.get("department", "")
        team = categories.get("team", "")
        commitment = categories.get("commitment", "")  # Full-time, Part-time, etc.

        # Description from lists
        description_parts = []
        for section in raw.get("lists", []):
            section_text = section.get("text", "")
            content = section.get("content", "")
            content_clean = clean_html(content)
            if section_text:
                description_parts.append(f"{section_text}: {content_clean}")
            else:
                description_parts.append(content_clean)

        # Also include the main description
        main_desc = raw.get("descriptionPlain", "")
        if main_desc:
            description_parts.insert(0, main_desc)

        description = "\n\n".join(description_parts)

        # URLs
        source_url = raw.get("hostedUrl", "")
        apply_url = raw.get("applyUrl", source_url)

        # Timestamps
        created_at = raw.get("createdAt")
        discovered = datetime.utcnow()
        if created_at:
            try:
                discovered = datetime.fromtimestamp(created_at / 1000)
            except (ValueError, OSError):
                pass

        # Detect remote
        remote_allowed = "remote" in location.lower() if location else False

        # Job type from commitment
        job_type = ""
        if commitment:
            commitment_lower = commitment.lower()
            if "intern" in commitment_lower:
                job_type = "internship"
            elif "full" in commitment_lower:
                job_type = "full-time"
            elif "part" in commitment_lower:
                job_type = "part-time"
            elif "contract" in commitment_lower:
                job_type = "contract"

        # Extract skills
        skills = self._extract_skills(description)

        return RawJob(
            title=title,
            company=company_slug.replace("-", " ").title(),
            description=description[:5000],
            location=location,
            remote_allowed=remote_allowed,
            posted_at=discovered.strftime("%Y-%m-%d"),
            job_type=job_type,
            department=department or team,
            source="lever",
            source_url=source_url,
            apply_url=apply_url,
            skills_required=skills,
            discovered_at=discovered,
            raw_data={"lever_id": raw.get("id", ""), "company": company_slug},
        )

    def _extract_skills(self, description: str) -> list[str]:
        """Extract technical skills from description."""
        skill_keywords = [
            "Python", "Java", "C++", "JavaScript", "TypeScript", "Rust", "Go",
            "React", "Angular", "Vue", "Node.js", "Next.js",
            "AWS", "GCP", "Azure", "Docker", "Kubernetes",
            "PostgreSQL", "MongoDB", "Redis", "SQL",
            "TensorFlow", "PyTorch", "OpenCV", "ROS", "ROS2",
            "Machine Learning", "Deep Learning", "Computer Vision",
            "Git", "Linux", "REST API", "CI/CD",
        ]
        desc_lower = description.lower()
        return [s for s in skill_keywords if s.lower() in desc_lower][:20]
