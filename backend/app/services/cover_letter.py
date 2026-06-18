"""
AutoApply — Cover Letter Generation Service

Generates personalized cover letters using Google Gemini,
tailored to the specific job, company, and candidate profile.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import google.generativeai as genai

from app.core.config import settings

logger = logging.getLogger(__name__)

COVER_LETTER_PROMPT = """
You are an expert cover letter writer. Write a compelling, personalized cover letter.

CANDIDATE PROFILE:
{profile}

TARGET JOB:
Title: {title}
Company: {company}
Description: {description}

GUIDELINES:
1. Open with a strong, specific hook — mention why this particular role/company excites you
2. Highlight 2-3 specific skills/projects from the candidate's background that directly relate
3. Show genuine interest in the company's mission or recent work
4. Keep it concise — 3-4 paragraphs, under 350 words
5. Use a professional but warm tone — not overly formal
6. End with a clear call to action
7. Do NOT use generic phrases like "I am writing to express my interest"
8. Do NOT include the date, addresses, or "Dear Hiring Manager" — just the body text

Write the cover letter now:
"""


async def generate_cover_letter(
    resume_structured: dict,
    job_title: str,
    job_company: str,
    job_description: str,
) -> str:
    """
    Generate a personalized cover letter.
    Returns the cover letter text.
    """
    if not settings.gemini_api_key:
        logger.warning("No Gemini API key, generating template cover letter")
        return generate_template_cover_letter(
            resume_structured, job_title, job_company
        )

    try:
        model = genai.GenerativeModel(settings.gemini_model)

        prompt = COVER_LETTER_PROMPT.format(
            profile=json.dumps(resume_structured, indent=2),
            title=job_title,
            company=job_company,
            description=job_description[:3000],
        )

        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.7,  # Slightly creative
            ),
        )

        cover_letter = response.text.strip()
        logger.info(f"Cover letter generated for {job_title} @ {job_company}")
        return cover_letter

    except Exception as e:
        logger.error(f"Cover letter generation failed: {e}")
        return generate_template_cover_letter(
            resume_structured, job_title, job_company
        )


def generate_template_cover_letter(
    profile: dict, job_title: str, company: str
) -> str:
    """Fallback template-based cover letter."""
    name = profile.get("name", "the candidate")
    skills = profile.get("skills", [])[:5]
    skills_text = ", ".join(skills) if skills else "various technical skills"

    projects = profile.get("projects", [])
    project_text = ""
    if projects:
        proj = projects[0]
        project_text = f"\n\nOne project I'm particularly proud of is {proj.get('name', 'a recent project')}, where I {proj.get('description', 'developed a significant solution')}."

    return f"""I am excited about the {job_title} position at {company}. With my background in {skills_text}, I believe I can make a meaningful contribution to your team.

Throughout my experience, I have developed strong expertise in areas directly relevant to this role. My technical skills include {skills_text}, which align closely with the requirements outlined in your job posting.{project_text}

I am particularly drawn to {company} because of the innovative work being done in this space. I am eager to bring my skills and enthusiasm to your team and contribute to the exciting challenges ahead.

I would welcome the opportunity to discuss how my background and skills can benefit {company}. Thank you for considering my application."""


async def save_cover_letter(
    resume_structured: dict,
    job_title: str,
    job_company: str,
    job_description: str,
) -> tuple[str, str]:
    """
    Generate and save a cover letter.
    Returns (cover_letter_text, file_path).
    """
    text = await generate_cover_letter(
        resume_structured, job_title, job_company, job_description
    )

    # Save as text file
    safe_company = "".join(c if c.isalnum() else "_" for c in job_company)
    timestamp = datetime.now().strftime("%Y%m%d")
    filename = f"cover_letter_{safe_company}_{timestamp}.txt"

    output_path = settings.generated_path / filename
    output_path.write_text(text, encoding="utf-8")

    logger.info(f"Cover letter saved: {output_path}")
    return text, str(output_path)
