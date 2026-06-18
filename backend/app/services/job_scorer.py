"""
AutoApply — Job Scoring Service

Scores job relevance against user profile using weighted factors:
- Skills Match:      40%
- Project Relevance: 25%
- Education Match:   15%
- Location Match:    10%
- Career Goal Match: 10%

Uses Google Gemini for intelligent matching.
"""

import json
import logging
from typing import Any

import google.generativeai as genai

from app.core.config import settings

logger = logging.getLogger(__name__)

SCORING_PROMPT = """
You are a job matching engine. Score how well this candidate matches the job.

CANDIDATE PROFILE:
{profile}

JOB LISTING:
Title: {title}
Company: {company}
Description: {description}
Required Skills: {required_skills}
Location: {location}
Job Type: {job_type}

USER PREFERENCES:
Preferred Domains: {domains}
Preferred Job Types: {job_types}
Experience Level: {experience_level}
Preferred Locations: {locations}
Target Companies: {target_companies}

EXPERIENCE MISMATCH PENALTY RULE:
Check the required experience level of the job listing (e.g., "Senior", "Lead", "Staff", "Manager", "Principal", "Director", "VP", "Architect", or "3+ years of experience", "5+ years of experience") against the candidate's profile/preferences (e.g., they are a student, intern, or entry_level and have NO professional full-time experience).
If the job requires a senior/experienced professional but the candidate is a student/intern/entry_level, you MUST penalize the score heavily.
For this mismatch, set the projects, education, and career_goals points to 0 or very low, and cap the total match score below 40.

CRITICALITY RULE:
BE EXTREMELY CRITICAL AND CONSERVATIVE. If a candidate lacks the core technical qualifications, or if the job does not match their career interests (Preferred Domains) and experience level (student/intern), penalize the score heavily. Do not give the benefit of the doubt. If the job description requires skills or experience they do not have, subtract points aggressively. We only want high scores for jobs the candidate is genuinely qualified for and interested in.

Score the match on these factors (as percentages of maximum possible):
- skills (max 40 points): How many required skills does the candidate have?
- projects (max 25 points): How relevant are the candidate's projects?
- education (max 15 points): Is the candidate's education relevant?
- location (max 10 points): Does the location match preferences? Remote = full score if allowed.
- career_goals (max 10 points): Does this align with the candidate's domains/interests?

Also identify:
- matched_skills: Skills the candidate HAS that the job requires
- missing_skills: Skills the job requires that the candidate LACKS

Return ONLY valid JSON (no markdown, no code fences):
{{
    "skills": <0-40>,
    "projects": <0-25>,
    "education": <0-15>,
    "location": <0-10>,
    "career_goals": <0-10>,
    "total": <0-100>,
    "matched_skills": ["skill1", "skill2"],
    "missing_skills": ["skill3"],
    "reason": "One sentence explaining the score"
}}
"""


async def score_job(
    profile: dict,
    job_title: str,
    job_company: str,
    job_description: str,
    job_skills: list[str],
    job_location: str,
    job_type: str,
    preferences: dict,
) -> dict:
    """
    Score a job listing against the user's profile and preferences.
    Returns a match breakdown dictionary.
    """
    if not settings.gemini_api_key:
        logger.warning("No Gemini API key, using basic scoring")
        return basic_score(
            profile=profile,
            job_title=job_title,
            job_company=job_company,
            job_description=job_description,
            job_skills=job_skills,
            job_location=job_location,
            job_type=job_type,
            preferences=preferences,
        )

    prompt = SCORING_PROMPT.format(
        profile=json.dumps(profile, indent=2),
        title=job_title,
        company=job_company,
        description=job_description[:3000],  # Limit description length
        required_skills=", ".join(job_skills) if job_skills else "Not specified",
        location=job_location,
        job_type=job_type,
        domains=", ".join(preferences.get("domains", [])),
        job_types=", ".join(preferences.get("job_types", [])),
        experience_level=preferences.get("experience_level", ""),
        locations=json.dumps(preferences.get("locations", [])),
        target_companies=", ".join(preferences.get("target_companies", [])),
    )

    models_to_try = [
        settings.gemini_model,
        "gemini-2.0-flash",
        "gemini-2.5-flash",
        "gemini-2.0-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.1-flash-lite",
    ]
    seen = set()
    models_to_try = [x for x in models_to_try if not (x in seen or seen.add(x))]

    for model_name in models_to_try:
        try:
            logger.info(f"Attempting job scoring with Gemini model: {model_name}")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )

            result = json.loads(response.text)

            # Validate and clamp scores
            result["skills"] = min(max(float(result.get("skills", 0)), 0), 40)
            result["projects"] = min(max(float(result.get("projects", 0)), 0), 25)
            result["education"] = min(max(float(result.get("education", 0)), 0), 15)
            result["location"] = min(max(float(result.get("location", 0)), 0), 10)
            result["career_goals"] = min(max(float(result.get("career_goals", 0)), 0), 10)
            result["total"] = (
                result["skills"]
                + result["projects"]
                + result["education"]
                + result["location"]
                + result["career_goals"]
            )

            logger.info(f"AI scoring successful with model {model_name}: {job_title} @ {job_company} = {result['total']}/100")
            return result

        except Exception as e:
            logger.warning(f"AI scoring failed for model {model_name}: {e}")
            continue

    logger.error("All Gemini models failed for job scoring. Falling back to basic scoring.")
    return basic_score(
        profile=profile,
        job_title=job_title,
        job_company=job_company,
        job_description=job_description,
        job_skills=job_skills,
        job_location=job_location,
        job_type=job_type,
        preferences=preferences,
    )


def basic_score(
    profile: dict,
    job_title: str,
    job_company: str,
    job_description: str,
    job_skills: list[str],
    job_location: str,
    job_type: str,
    preferences: dict,
) -> dict:
    """
    Fallback basic scoring using strict keyword and constraint matching.
    Designed to prevent score inflation and provide high-fidelity matching.
    """
    title_lower = job_title.lower() if job_title else ""
    desc_lower = job_description.lower() if job_description else ""

    # Check experience level mismatch:
    # If the job title suggests senior level (Senior, Lead, Staff, Principal, Manager, Architect, etc.),
    # and the candidate's preferences or profile indicates entry/intern level, apply heavy penalty.
    senior_keywords = ["senior", "sr.", "sr ", "staff", "principal", "lead", "manager", "director", "architect", "head", "vp"]
    is_senior_job = any(kw in title_lower for kw in senior_keywords)

    # Candidate profile check (Sandeep Roy has B.Tech 2027, so is entry/intern)
    is_entry_candidate = True
    pref_exp = (preferences.get("experience_level") or "").lower()
    if pref_exp in ("mid_level", "senior"):
        is_entry_candidate = False

    # Domain match check (e.g. robotics, computer_vision, web_development, etc.)
    domains = [d.lower().replace("_", " ") for d in preferences.get("domains", [])]
    domain_matched = any(d in title_lower or d in desc_lower for d in domains) if domains else True

    # Skills match (40%)
    user_skills = set(s.lower() for s in profile.get("skills", []))
    required_skills = set(s.lower() for s in job_skills)

    if required_skills:
        skill_overlap = user_skills & required_skills
        skills_score = (len(skill_overlap) / len(required_skills)) * 40
        matched = list(skill_overlap)
        missing = list(required_skills - user_skills)
    else:
        # No skills listed explicitly, look for candidate skills inside description
        matched_in_desc = [s for s in user_skills if s in desc_lower]
        matched = matched_in_desc
        skills_score = min(len(matched_in_desc) * 4.0, 40.0)
        missing = []

    # Location match (10%)
    location_lower = job_location.lower() if job_location else ""
    user_locations = preferences.get("locations", [])
    location_score = 0
    for loc in user_locations:
        if loc.get("remote_allowed") and "remote" in location_lower:
            location_score = 10
            break
        country = (loc.get("country") or "").lower()
        city = (loc.get("city") or "").lower()
        if country and country in location_lower:
            location_score = 7
        if city and city in location_lower:
            location_score = 10
            break

    # Projects match (25%)
    projects_score = 0
    candidate_projects = profile.get("projects", [])
    if candidate_projects:
        for p in candidate_projects:
            proj_techs = [t.lower() for t in p.get("technologies", [])]
            tech_matched = any(t in desc_lower for t in proj_techs)
            name_matched = p.get("name", "").lower() in desc_lower
            if tech_matched or name_matched:
                projects_score = min(projects_score + 10, 25)
        if not projects_score and matched:
            projects_score = 5

    # Education match (15%)
    education_score = 0
    candidate_edu = profile.get("education", [])
    if candidate_edu:
        for edu in candidate_edu:
            field = edu.get("field", "").lower()
            if field and field in desc_lower:
                education_score = 15
                break
            elif "engineer" in field or "computer" in field or "robotics" in field or "technology" in field:
                if "engineer" in title_lower or "tech" in title_lower or "developer" in title_lower:
                    education_score = 10
        if not education_score:
            education_score = 5

    # Career goal match (10%)
    career_score = 10 if domain_matched else 0

    reason_msg = f"Basic scoring: {len(matched)} skills matched."

    # Experience penalty: Cap total score if there's a mismatch
    if is_senior_job and is_entry_candidate:
        projects_score = 0
        education_score = 0
        career_score = 0
        skills_score = min(skills_score, 5.0)
        location_score = min(location_score, 5.0)
        reason_msg += " | Heavily penalized due to senior experience level mismatch with entry/intern profile"
    elif not domain_matched:
        projects_score = 0
        education_score = 0
        career_score = 0
        skills_score = min(skills_score, 5.0)
        location_score = min(location_score, 5.0)
        reason_msg += " | Penalized due to domain mismatch (does not align with preferred domains)"
    elif not matched:
        projects_score = 0
        education_score = 0
        career_score = 0
        location_score = min(location_score, 5.0)
        reason_msg += " | Zero skills matched from candidate resume"

    total = skills_score + projects_score + education_score + location_score + career_score

    # Apply strict cap if mismatch is present
    if not domain_matched:
        total = min(total, 15.0)
    if is_senior_job and is_entry_candidate:
        total = min(total, 10.0)
    if not matched:
        total = min(total, 5.0)

    return {
        "skills": round(skills_score, 1),
        "projects": projects_score,
        "education": education_score,
        "location": location_score,
        "career_goals": career_score,
        "total": round(total, 1),
        "matched_skills": matched,
        "missing_skills": missing,
        "reason": reason_msg,
    }
