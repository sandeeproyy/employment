"""
AutoApply — Chatbot API Routes

Conversational assistant for guiding users through setting up their job search preferences
and updating the preferences database dynamically.
"""

import json
import logging
import re
import google.generativeai as genai
from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import verify_api_token
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import UserProfile
from app.models.preference import UserPreference

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chatbot", tags=["Chatbot"])

# Configure genai key
if settings.gemini_api_key:
    genai.configure(api_key=settings.gemini_api_key)


class ChatMessage(BaseModel):
    role: str  # 'user', 'assistant', 'system'
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    response: str
    preference_update: dict | None = None
    suggested_replies: list[str] | None = None


SYSTEM_PROMPT = """You are a highly professional AI Career Advisor and Executive Search Assistant. The candidate has uploaded a resume, and your mandate is to conversationally construct and refine their precise job/internship targeting preferences.

User Profile (Extracted from Resume):
- Name: {name}
- Email: {email}
- Resume Skills: {skills}

Current Preferences in Database:
- Job Types: {job_types}
- Domains: {domains}
- Experience Level: {experience_level}
- Locations: {locations}
- Target Companies: {target_companies}
- Minimum Match Score: {min_match_score}

Your Instructions:
1. Maintain a highly professional, polite, and executive-level tone. Avoid overly casual language.
2. Conduct a structured, step-by-step onboarding flow. Ask exactly ONE targeted question at a time to complete their preferences in order:
   - Step 1: Job Types. If not set, ask if they want full-time, internship, etc. and provide suggested replies like ["Internship", "Full-time", "Both"].
   - Step 2: Domains. Suggest 3-4 domains based on their resume skills (e.g., ["Software Development", "Machine Learning", "Robotics"]) and ask which they prefer.
   - Step 3: Experience Level. Ask for their level and suggest: ["Student", "Entry Level", "Mid Level", "Senior"].
   - Step 4: Locations. Ask for their preferred locations and suggest options like ["Remote", "India", "United States", "Singapore"].
3. Focus strictly on aligning searches to their actual skill set (as parsed from the resume) and target parameters.
4. When the user specifies any location or role preferences, you must parse and map them to the database schema.
5. Do not suggest or configure irrelevant job boards or default companies (e.g. Cloudflare/Figma) unless the user explicitly requests them. Only build job discovery sources that match their target keywords and locations.

If the user mentions new preferences, output them in the 'preference_update' field of the JSON. Only update fields when the user explicitly provides, clarifies, or refines them.
Locations should be parsed as a list of dicts: {{"country": str, "state": str | None, "city": str | None, "remote_allowed": bool}}.
Job types should be a list containing any of: ["internship", "full-time", "research", "contract", "part-time"].
Domains should be a list containing strings representing fields of interest (e.g. "robotics", "computer_vision", "software_development", "machine_learning", "web_development").
Experience level should be: "student", "graduate", "entry_level", "mid_level", or "senior".
Minimum Match Score should be an integer between 0 and 100.

You MUST return a JSON object with this exact schema:
{{
  "response": "Your professional, executive response to the user.",
  "preference_update": {{ ... }}, // optional, include only if you detected preference changes in the user's latest input
  "suggested_replies": ["Option 1", "Option 2", ...] // optional, list of 2-4 simple, short button labels to guide the user's choice for the current question. Keep them very short (1-3 words).
}}
Do not include markdown code fences (like ```json), return raw JSON only.
"""


# ---------- Fallback keyword-based preference parser ----------
LOCATION_KEYWORDS = {
    "india": {"country": "India"},
    "bangalore": {"country": "India", "city": "Bangalore"},
    "bengaluru": {"country": "India", "city": "Bengaluru"},
    "delhi": {"country": "India", "city": "Delhi"},
    "noida": {"country": "India", "city": "Noida"},
    "gurgaon": {"country": "India", "city": "Gurgaon"},
    "gurugram": {"country": "India", "city": "Gurugram"},
    "mumbai": {"country": "India", "city": "Mumbai"},
    "hyderabad": {"country": "India", "city": "Hyderabad"},
    "chennai": {"country": "India", "city": "Chennai"},
    "pune": {"country": "India", "city": "Pune"},
    "united states": {"country": "United States"},
    "usa": {"country": "United States"},
    "us": {"country": "United States"},
    "san francisco": {"country": "United States", "city": "San Francisco"},
    "new york": {"country": "United States", "city": "New York"},
    "seattle": {"country": "United States", "city": "Seattle"},
    "boston": {"country": "United States", "city": "Boston"},
    "united kingdom": {"country": "United Kingdom"},
    "uk": {"country": "United Kingdom"},
    "london": {"country": "United Kingdom", "city": "London"},
    "singapore": {"country": "Singapore"},
    "germany": {"country": "Germany"},
    "berlin": {"country": "Germany", "city": "Berlin"},
    "munich": {"country": "Germany", "city": "Munich"},
    "canada": {"country": "Canada"},
    "toronto": {"country": "Canada", "city": "Toronto"},
    "vancouver": {"country": "Canada", "city": "Vancouver"},
    "remote": {"country": "Remote", "remote_allowed": True},
}

JOB_TYPE_KEYWORDS = {
    "internship": "internship",
    "intern": "internship",
    "full-time": "full-time",
    "full time": "full-time",
    "fulltime": "full-time",
    "part-time": "part-time",
    "part time": "part-time",
    "contract": "contract",
    "research": "research",
}

DOMAIN_KEYWORDS = {
    "robotics": "robotics",
    "machine learning": "machine_learning",
    "ml": "machine_learning",
    "ai": "machine_learning",
    "deep learning": "deep_learning",
    "dl": "deep_learning",
    "computer vision": "computer_vision",
    "cv": "computer_vision",
    "nlp": "natural_language_processing",
    "natural language processing": "natural_language_processing",
    "web development": "web_development",
    "web dev": "web_development",
    "frontend": "frontend_development",
    "frontend dev": "frontend_development",
    "backend": "backend_development",
    "backend dev": "backend_development",
    "full stack": "full_stack_development",
    "fullstack": "full_stack_development",
    "data science": "data_science",
    "data engineering": "data_engineering",
    "devops": "devops",
    "cloud": "cloud_computing",
    "cloud computing": "cloud_computing",
    "embedded": "embedded_systems",
    "embedded systems": "embedded_systems",
    "software": "software_development",
    "software engineering": "software_development",
    "software dev": "software_development",
    "software development": "software_development",
    "autonomous vehicles": "autonomous_vehicles",
    "self driving": "autonomous_vehicles",
    "autonomous driving": "autonomous_vehicles",
    "embodied ai": "embodied_ai",
    "embodied": "embodied_ai",
    "mechanical": "mechanical_design",
    "mechanical design": "mechanical_design",
}


def _parse_preferences_from_text(text: str) -> dict | None:
    """Fallback: parse user preferences from plain text using keyword matching."""
    text_lower = text.lower()
    update = {}

    # Parse locations
    locations = []
    for kw, loc in LOCATION_KEYWORDS.items():
        if kw in text_lower:
            entry = {"country": loc.get("country", ""), "state": None, "city": loc.get("city"), "remote_allowed": loc.get("remote_allowed", False)}
            if entry not in locations:
                locations.append(entry)
    if locations:
        update["locations"] = locations

    # Parse job types
    job_types = []
    for kw, jt in JOB_TYPE_KEYWORDS.items():
        if kw in text_lower and jt not in job_types:
            job_types.append(jt)
    if job_types:
        update["job_types"] = job_types

    # Parse domains
    domains = []
    for kw, domain in DOMAIN_KEYWORDS.items():
        if kw in text_lower and domain not in domains:
            domains.append(domain)
    if domains:
        update["domains"] = domains

    # Parse min match score
    score_match = re.search(r'(?:min(?:imum)?|match)\s*(?:score|match)?\s*(?:to|of|at|=|:)?\s*(\d{1,3})', text_lower)
    if score_match:
        score = int(score_match.group(1))
        if 0 <= score <= 100:
            update["min_match_score"] = score

    # Parse experience level
    for level in ["student", "graduate", "entry_level", "entry level", "mid_level", "mid level", "senior"]:
        if level in text_lower:
            update["experience_level"] = level.replace(" ", "_")
            break

    return update if update else None


def _build_fallback_response(update: dict | None, user_msg: str) -> str:
    """Build a helpful assistant response when Gemini is unavailable."""
    if not update:
        return (
            "I am ready to configure your job search parameters. "
            "You can specify requirements such as job titles, target locations, "
            "domains of interest, and employment types (internships or full-time)."
        )

    parts = ["Preferences updated successfully:"]
    if "locations" in update:
        locs = [l.get("city") or l.get("country") for l in update["locations"]]
        parts.append(f"- Locations: {', '.join(locs)}")
    if "job_types" in update:
        parts.append(f"- Job Types: {', '.join(update['job_types'])}")
    if "domains" in update:
        parts.append(f"- Domains: {', '.join(d.replace('_', ' ') for d in update['domains'])}")
    if "min_match_score" in update:
        parts.append(f"- Minimum Match Score: {update['min_match_score']}%")
    if "experience_level" in update:
        parts.append(f"- Experience Level: {update['experience_level']}")
    return "\n".join(parts)

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user_token: str = Depends(verify_api_token),
):
    """Handle chat interaction and update preferences based on LLM output."""

    # 1. Fetch Profile & Preferences scoped to user
    profile_result = await db.execute(select(UserProfile).where(UserProfile.user_token == user_token))
    profile = profile_result.scalar_one_or_none()

    pref_result = await db.execute(select(UserPreference).where(UserPreference.user_token == user_token))
    pref = pref_result.scalar_one_or_none()
    if not pref:
        pref = UserPreference(user_token=user_token)
        db.add(pref)
        await db.commit()
        await db.refresh(pref)

    # Get latest user message for fallback parsing
    latest_user_msg = ""
    for msg in reversed(payload.messages):
        if msg.role == "user":
            latest_user_msg = msg.content
            break

    # --- Try Gemini first ---
    chatbot_msg = None
    upd = None
    gemini_failed = False

    if settings.gemini_api_key:
        # Formulate context variables
        name = profile.name if profile else "Guest"
        email = profile.email if profile else ""
        skills = ", ".join(profile.resume_structured.get("skills", [])) if (profile and profile.resume_structured) else "None uploaded yet"

        job_types = pref.job_types
        domains = pref.domains
        experience_level = pref.experience_level
        locations = json.dumps(pref.locations)
        target_companies = ", ".join(pref.target_companies)
        min_match_score = pref.min_match_score

        sys_instruction = SYSTEM_PROMPT.format(
            name=name,
            email=email,
            skills=skills,
            job_types=job_types,
            domains=domains,
            experience_level=experience_level,
            locations=locations,
            target_companies=target_companies,
            min_match_score=min_match_score,
        )

        formatted_prompt = f"System Instructions:\n{sys_instruction}\n\nChat History:\n"
        for msg in payload.messages:
            formatted_prompt += f"{msg.role.upper()}: {msg.content}\n"
        formatted_prompt += "\nASSISTANT (JSON response):"

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

        gemini_failed = True
        for model_name in models_to_try:
            try:
                logger.info(f"Attempting chatbot generation with Gemini model: {model_name}")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(
                    formatted_prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=0.3,
                        response_mime_type="application/json",
                    ),
                )

                parsed = json.loads(response.text)
                chatbot_msg = parsed.get("response", "How can I help you with your job search today?")
                upd = parsed.get("preference_update")
                suggested = parsed.get("suggested_replies") or []
                gemini_failed = False
                break

            except Exception as e:
                err_msg = str(e).lower()
                logger.warning(f"Gemini API call failed for model {model_name}: {e}")
                if any(k in err_msg for k in ["429", "quota", "exhausted", "limit", "400", "401", "403", "api_key", "api key", "invalid", "permission"]):
                    logger.error("Gemini API quota exceeded or key invalid. Breaking model retry loop.")
                    break
                continue
    else:
        gemini_failed = True

    # --- Fallback: keyword-based preference extraction ---
    suggested = []
    if gemini_failed:
        upd = _parse_preferences_from_text(latest_user_msg)
        chatbot_msg = _build_fallback_response(upd, latest_user_msg)
        # Generate fallback quick response suggestion chips
        if not upd:
            suggested = ["Internship", "Full-time", "Remote", "India"]
        else:
            if "job_types" not in upd:
                suggested.extend(["Internship", "Full-time"])
            if "locations" not in upd:
                suggested.extend(["Remote", "India", "United States"])
            if "domains" not in upd:
                suggested.extend(["Machine Learning", "Software Development", "Robotics"])
            suggested = list(dict.fromkeys(suggested))[:4] # deduplicate and limit

    # 4. Save Preference Updates to DB
    if upd:
        if "job_types" in upd:
            pref.job_types = upd["job_types"]
        if "domains" in upd:
            pref.domains = upd["domains"]
        if "experience_level" in upd:
            pref.experience_level = upd["experience_level"]
        if "locations" in upd:
            pref.locations = upd["locations"]
        if "target_companies" in upd:
            pref.target_companies = upd["target_companies"]
        if "min_match_score" in upd:
            pref.min_match_score = int(upd["min_match_score"])

        # Generate default scraper source configurations dynamically
        if "domains" in upd or "locations" in upd or "job_types" in upd:
            new_sources = []
            loc_names = [l.get("country") or l.get("city") for l in pref.locations if l.get("country") or l.get("city")]
            if not loc_names:
                loc_names = ["India"]

            domains_list = pref.domains or ["software_development"]
            job_types_list = pref.job_types or ["internship", "full-time"]

            for loc in loc_names[:2]:
                for domain in domains_list[:3]:
                    clean_domain = domain.replace("_", " ")
                    for jt in job_types_list:
                        if jt in ["internship", "full-time"]:
                            new_sources.append({
                                "type": "linkedin",
                                "keywords": f"{clean_domain} {jt}" if jt == "internship" else clean_domain,
                                "location": loc,
                                "job_type": jt,
                                "interval_minutes": 30,
                                "enabled": True,
                                "label": f"LinkedIn {clean_domain.title()} {jt.title()} {loc.title()}",
                            })

            pref.job_sources = new_sources

        await db.commit()
        logger.info("Chatbot updated preferences dynamically in DB.")
        # Auto-trigger job discovery/scoring pipeline if resume is uploaded and preferences are fully set
        from app.services.pipeline_trigger import auto_trigger_pipeline_if_ready
        await auto_trigger_pipeline_if_ready(db, user_token)

    # 5. Query matching jobs and append recommendations
    wants_jobs = any(kw in latest_user_msg.lower() for kw in ["job", "match", "recommend", "show", "find", "best", "what are", "list"])
    threshold = pref.min_match_score or 70
    from app.models.job import Job
    jobs_result = await db.execute(
        select(Job)
        .where((Job.match_score >= threshold) & (Job.user_token == user_token))
        .order_by(Job.match_score.desc())
        .limit(3)
    )
    matching_jobs = jobs_result.scalars().all()

    if matching_jobs and wants_jobs:
        chatbot_msg += "\n\nTop matching jobs for your preferences:\n"
        for idx, job in enumerate(matching_jobs):
            url_text = f" [[Apply]({job.apply_url})]" if job.apply_url else ""
            posted_text = f" (Posted: {job.posted_at})" if job.posted_at else ""
            chatbot_msg += f"• **{job.title}** at *{job.company}* — **{round(job.match_score)}% match**{posted_text}{url_text}\n"
        chatbot_msg += "\nNavigate to ~/jobs in the sidebar to view all matching listings!"
    elif wants_jobs:
        chatbot_msg += "\n\nNo matching jobs currently found in the database. You can run a discovery scan to search for new listings."

    return ChatResponse(response=chatbot_msg, preference_update=upd, suggested_replies=suggested)
