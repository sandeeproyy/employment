import logging
import re
from datetime import datetime
from bs4 import BeautifulSoup
import httpx

from app.sources.base import JobSource, RawJob, clean_html

logger = logging.getLogger(__name__)

LINKEDIN_SEARCH_API = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

class LinkedInSource(JobSource):
    name = "LinkedIn"
    source_type = "linkedin"

    async def discover(self, config: dict) -> list[RawJob]:
        """
        Scrape public job postings from LinkedIn guest API.
        Config requires: {"keywords": "robotics", "location": "India"}
        Can optionally contain: {"job_type": "internship" | "full-time"}
        """
        keywords = config.get("keywords", "robotics")
        location = config.get("location", "India")
        source_job_type = config.get("job_type")
        
        jt_map = {
            "internship": "I",
            "full-time": "F",
        }
        
        jobs = []
        try:
            async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
                params = {
                    "keywords": keywords,
                    "location": location,
                    "start": 0
                }
                if source_job_type and source_job_type in jt_map:
                    params["f_JT"] = jt_map[source_job_type]
                
                # Fetch job listings HTML
                response = await client.get(LINKEDIN_SEARCH_API, params=params)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "html.parser")
                items = soup.find_all("li")
                logger.info(f"LinkedIn [{keywords} - {location}]: Found {len(items)} listings")
                
                for item in items[:15]:  # Limit to top 15 listings per discovery run to keep it fast
                    try:
                        # Extract basic info
                        link_el = item.find("a", class_="base-card__full-link")
                        if not link_el:
                            continue
                        
                        source_url = link_el["href"]
                        # Clean link (remove tracking parameters)
                        if "?" in source_url:
                            source_url = source_url.split("?")[0]
                        
                        title_el = item.find("h3", class_="base-search-card__title")
                        title = title_el.text.strip() if title_el else "Unknown Job"
                        
                        company_el = item.find("h4", class_="base-search-card__subtitle")
                        company = company_el.text.strip() if company_el else "Unknown Company"
                        
                        location_el = item.find("span", class_="job-search-card__location")
                        job_location = location_el.text.strip() if location_el else location
                        
                        # Extract when posted
                        time_el = item.find("time")
                        posted_at = time_el.text.strip() if time_el else "recently"
                        posted_at = re.sub(r'\s+', ' ', posted_at)
                        
                        # Fetch full description page
                        description = f"Job listing for {title} at {company} in {job_location}."
                        try:
                            detail_res = await client.get(source_url)
                            if detail_res.status_code == 200:
                                detail_soup = BeautifulSoup(detail_res.text, "html.parser")
                                desc_el = detail_soup.find("div", class_="show-more-less-html__markup")
                                if not desc_el:
                                    desc_el = detail_soup.find("section", class_="description")
                                if not desc_el:
                                    desc_el = detail_soup.find("div", class_="description__text")
                                
                                if desc_el:
                                    description = clean_html(str(desc_el))
                        except Exception as detail_err:
                            logger.warning(f"LinkedIn details fetch failed: {detail_err}")
                        
                        # Skills extraction
                        skills = self._extract_skills_from_description(description)
                        
                        remote_allowed = any(kw in (job_location + title + description).lower() for kw in ["remote", "work from home", "wfh"])
                        
                        # Default job type to internship if title contains intern/internship or if we requested internships
                        job_type = "full-time"
                        if source_job_type == "internship" or any(kw in title.lower() for kw in ["intern", "internship", "trainee"]):
                            job_type = "internship"
                        
                        jobs.append(RawJob(
                            title=title,
                            company=company,
                            description=description[:5000],
                            location=job_location,
                            remote_allowed=remote_allowed,
                            posted_at=posted_at,
                            job_type=job_type,
                            source="linkedin",
                            source_url=source_url,
                            apply_url=source_url,
                            skills_required=skills,
                            discovered_at=datetime.utcnow(),
                            raw_data={"keywords": keywords, "location": location}
                        ))
                    except Exception as parse_err:
                        logger.error(f"LinkedIn item parse error: {parse_err}")
                        continue
        except Exception as e:
            logger.error(f"LinkedIn discovery failed: {e}")
            
        return jobs

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
