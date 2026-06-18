"""
AutoApply — Greenhouse Job Source

Fetches jobs from Greenhouse ATS public API.
API: https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs
No authentication required for public job boards.

Example board tokens: tesla, figma, stripe, cloudflare, databricks
"""

import logging
from datetime import datetime

import httpx

from app.sources.base import JobSource, RawJob, clean_html

logger = logging.getLogger(__name__)

GREENHOUSE_API = "https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
GREENHOUSE_JOB_DETAIL = "https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}"


class GreenhouseSource(JobSource):
    name = "Greenhouse"
    source_type = "greenhouse"

    async def discover(self, config: dict) -> list[RawJob]:
        """
        Fetch jobs from a Greenhouse board.
        Config requires: {"board_token": "company-name"}
        """
        board_token = config.get("board_token", "")
        if not board_token:
            logger.warning("Greenhouse: no board_token configured")
            return []

        jobs = []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Fetch job listing
                url = GREENHOUSE_API.format(board_token=board_token)
                response = await client.get(url, params={"content": "true"})
                response.raise_for_status()

                data = response.json()
                raw_jobs = data.get("jobs", [])

                logger.info(f"Greenhouse [{board_token}]: Found {len(raw_jobs)} jobs")

                for raw in raw_jobs:
                    try:
                        job = self._parse_job(raw, board_token)
                        if job:
                            jobs.append(job)
                    except Exception as e:
                        logger.error(f"Greenhouse: Error parsing job: {e}")
                        continue

        except httpx.HTTPStatusError as e:
            logger.error(f"Greenhouse [{board_token}]: HTTP {e.response.status_code}")
        except Exception as e:
            logger.error(f"Greenhouse [{board_token}]: {e}")

        return jobs

    def _parse_job(self, raw: dict, board_token: str) -> RawJob | None:
        """Parse a single Greenhouse job response into RawJob."""
        title = raw.get("title", "").strip()
        if not title:
            return None

        # Location
        location_obj = raw.get("location", {})
        location = location_obj.get("name", "") if isinstance(location_obj, dict) else str(location_obj)

        # Description (HTML content)
        content = raw.get("content", "")
        description = clean_html(content)

        # Departments
        departments = raw.get("departments", [])
        department = departments[0].get("name", "") if departments else ""

        # Job ID for URL
        job_id = raw.get("id", "")
        source_url = f"https://boards.greenhouse.io/{board_token}/jobs/{job_id}"
        apply_url = raw.get("absolute_url", source_url)

        # Detect remote
        remote_allowed = "remote" in location.lower() if location else False

        # Extract skills from description (basic keyword extraction)
        skills = self._extract_skills_from_description(description)

        return RawJob(
            title=title,
            company=board_token.replace("-", " ").title(),
            description=description[:5000],  # Limit size
            location=location,
            remote_allowed=remote_allowed,
            posted_at="recently",
            department=department,
            source="greenhouse",
            source_url=source_url,
            apply_url=apply_url,
            skills_required=skills,
            discovered_at=datetime.utcnow(),
            raw_data={"greenhouse_id": job_id, "board_token": board_token},
        )

    def _extract_skills_from_description(self, description: str) -> list[str]:
        """Extract common technical skills mentioned in the description."""
        skill_keywords = [
            "Python", "Java", "C++", "C#", "JavaScript", "TypeScript", "Rust", "Go",
            "React", "Angular", "Vue", "Next.js", "Node.js",
            "AWS", "GCP", "Azure", "Docker", "Kubernetes",
            "PostgreSQL", "MySQL", "MongoDB", "Redis",
            "TensorFlow", "PyTorch", "OpenCV", "ROS", "ROS2",
            "SLAM", "Gazebo", "MoveIt", "CAD", "SolidWorks",
            "Machine Learning", "Deep Learning", "Computer Vision", "NLP",
            "Git", "CI/CD", "Linux", "REST API", "GraphQL",
            "Figma", "SQL", "NoSQL", "Spark", "Kafka",
        ]
        desc_lower = description.lower()
        found = []
        for skill in skill_keywords:
            if skill.lower() in desc_lower:
                found.append(skill)
        return found[:20]  # Cap at 20 skills
