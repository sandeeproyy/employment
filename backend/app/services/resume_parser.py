"""
AutoApply — Resume Parser Service

Extracts structured data from a resume PDF using:
1. PyMuPDF → Markdown extraction
2. Google Gemini → Structured JSON parsing

Fallback: regex-based extraction if AI call fails.
"""

import json
import logging
import re
from pathlib import Path

import fitz  # PyMuPDF
import google.generativeai as genai

from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure Gemini
if settings.gemini_api_key:
    genai.configure(api_key=settings.gemini_api_key)


RESUME_EXTRACTION_PROMPT = """
You are a resume parser. Extract structured data from the following resume text.

Return ONLY valid JSON with this exact structure (no markdown, no code fences):
{
    "name": "Full Name",
    "email": "email@example.com",
    "skills": ["skill1", "skill2"],
    "projects": [
        {
            "name": "Project Name",
            "description": "Brief description",
            "technologies": ["tech1", "tech2"],
            "highlights": ["key achievement"]
        }
    ],
    "education": [
        {
            "institution": "University Name",
            "degree": "Degree Name",
            "field": "Field of Study",
            "year": "2024",
            "gpa": "3.8"
        }
    ],
    "experience": [
        {
            "company": "Company Name",
            "title": "Job Title",
            "duration": "Jan 2024 - Present",
            "description": "What you did",
            "technologies": ["tech1"]
        }
    ],
    "interests": ["interest1", "interest2"],
    "certifications": ["cert1"],
    "links": {
        "github": "",
        "linkedin": "",
        "portfolio": ""
    }
}

Resume text:
"""


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF file using PyMuPDF."""
    doc = fitz.open(pdf_path)
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text("text"))
    doc.close()
    return "\n".join(text_parts)


def extract_markdown_from_pdf(pdf_path: str) -> str:
    """Extract PDF content as Markdown for better LLM parsing."""
    doc = fitz.open(pdf_path)
    md_parts = []
    for page in doc:
        # Get text with layout preservation
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block.get("type") == 0:  # Text block
                for line in block.get("lines", []):
                    line_text = ""
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text:
                            # Detect headers by font size
                            font_size = span.get("size", 12)
                            if font_size > 14:
                                line_text += f"## {text} "
                            elif font_size > 12:
                                line_text += f"### {text} "
                            else:
                                line_text += text + " "
                    if line_text.strip():
                        md_parts.append(line_text.strip())
    doc.close()
    return "\n".join(md_parts)


async def parse_resume_with_ai(text: str) -> dict:
    """
    Parse resume text using Google Gemini to extract structured data.
    Attempts multiple models in sequence to mitigate rate/quota limits.
    Returns a dictionary with skills, projects, education, experience, interests.
    """
    if not settings.gemini_api_key:
        logger.warning("No Gemini API key configured, falling back to regex parsing")
        return parse_resume_with_regex(text)

    # List of models to try in sequence to handle potential quota / rate limit errors
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
            logger.info(f"Attempting resume parsing with Gemini model: {model_name}")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                RESUME_EXTRACTION_PROMPT + text,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )

            result = json.loads(response.text)
            logger.info(f"AI parsing successful with model {model_name}: {len(result.get('skills', []))} skills extracted")
            return result

        except Exception as e:
            logger.warning(f"AI parsing failed for model {model_name}: {e}")
            continue

    logger.error("All Gemini models failed for resume parsing. Falling back to regex.")
    return parse_resume_with_regex(text)


def extract_name(text: str) -> str:
    """Heuristic name extractor: scan first 5 lines for capitalized candidate name."""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    header_keywords = {"resume", "cv", "curriculum", "vitae", "contact", "email", "phone", "profile", "summary", "skills", "experience", "education", "projects"}
    for line in lines[:5]:
        cleaned = re.sub(r'[^a-zA-Z\s]', '', line).strip()
        words = cleaned.split()
        if 1 <= len(words) <= 4:
            if any(w.lower() in header_keywords for w in words):
                continue
            if all(w[0].isupper() for w in words if w):
                return cleaned
    return "Candidate"


def extract_education(text: str) -> list:
    """Heuristic education section extractor using regex matching."""
    education_entries = []
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    start_idx = -1
    for idx, line in enumerate(lines):
        if re.search(r'(?i)^\s*(?:academic|educational)?\s*education\s*:?\s*$', line) or re.search(r'(?i)^\s*academic\s+profile\s*:?\s*$', line):
            start_idx = idx
            break
    
    if start_idx != -1:
        edu_lines = []
        section_headers = ["experience", "work", "projects", "skills", "interests", "languages", "certifications", "achievements", "links"]
        for line in lines[start_idx + 1:]:
            if any(re.search(r'(?i)^\s*' + h, line) for h in section_headers):
                break
            edu_lines.append(line)
        
        current_entry = {}
        for line in edu_lines:
            inst_match = re.search(r'(?i)(?:university|college|institute|school|iit|nit|iiit|bits|academy|university\s+of\s+[a-zA-Z\s]+)', line)
            degree_match = re.search(r'(?i)(b\.?tech|b\.?e\.?|m\.?tech|b\.?s\.?|m\.?s\.?|ph\.?d|bachelor|master|diploma|graduate)', line)
            year_match = re.findall(r'\b(20\d{2})\b', line)
            
            if inst_match:
                if current_entry and "institution" in current_entry:
                    education_entries.append(current_entry)
                    current_entry = {}
                current_entry["institution"] = line
            if degree_match:
                current_entry["degree"] = degree_match.group(1).title()
                field_match = re.search(r'(?i)(?:in|of)\s+([a-zA-Z\s]+?)(?:\s+from|\s+at|\s+in|\s*\(|$)', line)
                if field_match:
                    current_entry["field"] = field_match.group(1).strip()
            if year_match:
                current_entry["year"] = year_match[-1]
        
        if current_entry:
            education_entries.append(current_entry)
            
    if not education_entries and start_idx != -1:
        for line in edu_lines:
            if line.strip():
                education_entries.append({
                    "institution": line,
                    "degree": "Degree",
                    "field": "Study Field",
                    "year": "2026"
                })
                break
                
    return education_entries


def extract_experience(text: str) -> list:
    """Heuristic experience section extractor."""
    experience_entries = []
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    start_idx = -1
    for idx, line in enumerate(lines):
        if re.search(r'(?i)^\s*(?:work|professional|employment|job)?\s*experience\s*:?\s*$', line) or re.search(r'(?i)^\s*employment\s+history\s*:?\s*$', line):
            start_idx = idx
            break
            
    if start_idx != -1:
        exp_lines = []
        section_headers = ["education", "projects", "skills", "interests", "languages", "certifications", "achievements", "links"]
        for line in lines[start_idx + 1:]:
            if any(re.search(r'(?i)^\s*' + h, line) for h in section_headers):
                break
            exp_lines.append(line)
            
        current_entry = {}
        for line in exp_lines:
            title_match = re.search(r'(?i)(engineer|developer|analyst|intern|manager|programmer|architect|consultant|designer|lead|scientist|specialist)', line)
            duration_match = re.search(r'(?i)\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december)\s*\d{4}\s*(?:-|to|–)\s*(?:present|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december)\s*\d{4}\b)', line)
            
            if title_match:
                if current_entry and "title" in current_entry:
                    experience_entries.append(current_entry)
                    current_entry = {}
                current_entry["title"] = line
            if duration_match:
                current_entry["duration"] = duration_match.group(0)
                
            if current_entry and "title" in current_entry and line != current_entry["title"]:
                desc = current_entry.get("description", "")
                if len(desc) < 500:
                    current_entry["description"] = (desc + "\n" + line).strip()
                    
        if current_entry:
            experience_entries.append(current_entry)
            
    return experience_entries


def extract_projects(text: str) -> list:
    """Heuristic projects section extractor."""
    projects_entries = []
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    start_idx = -1
    for idx, line in enumerate(lines):
        if re.search(r'(?i)^\s*(?:academic|personal|key)?\s*projects\s*:?\s*$', line) or re.search(r'(?i)^\s*key\s+projects\s*:?\s*$', line):
            start_idx = idx
            break
            
    if start_idx != -1:
        proj_lines = []
        section_headers = ["education", "experience", "work", "skills", "interests", "languages", "certifications", "achievements", "links"]
        for line in lines[start_idx + 1:]:
            if any(re.search(r'(?i)^\s*' + h, line) for h in section_headers):
                break
            proj_lines.append(line)
            
        current_entry = {}
        for line in proj_lines:
            words = line.split()
            if 1 <= len(words) <= 5 and not line.startswith("•") and not line.startswith("-"):
                if current_entry and "name" in current_entry:
                    projects_entries.append(current_entry)
                    current_entry = {}
                current_entry["name"] = line
                current_entry["description"] = ""
            elif current_entry and "name" in current_entry:
                current_entry["description"] = (current_entry.get("description", "") + " " + line).strip()
                
        if current_entry:
            projects_entries.append(current_entry)
            
    return projects_entries


def parse_resume_with_regex(text: str) -> dict:
    """
    Fallback regex-based resume parser with heuristic section matchers.
    Extracts name, email, skills, education, experience, and projects.
    """
    result = {
        "name": extract_name(text),
        "email": "",
        "skills": [],
        "projects": extract_projects(text),
        "education": extract_education(text),
        "experience": extract_experience(text),
        "interests": [],
        "certifications": [],
        "links": {},
    }

    # Extract email
    email_pattern = r'[\w.+-]+@[\w-]+\.[\w.-]+'
    emails = re.findall(email_pattern, text)
    if emails:
        result["email"] = emails[0]

    # Extract skills
    common_skills = [
        "Python", "Java", "C++", "C", "JavaScript", "TypeScript", "Rust", "Go",
        "React", "Next.js", "Node.js", "FastAPI", "Django", "Flask",
        "TensorFlow", "PyTorch", "OpenCV", "ROS", "ROS2", "SLAM",
        "Docker", "Kubernetes", "AWS", "GCP", "Azure",
        "PostgreSQL", "MongoDB", "Redis", "SQL",
        "Git", "Linux", "MATLAB", "Simulink",
        "CAD", "SolidWorks", "AutoCAD", "Fusion 360",
        "Arduino", "Raspberry Pi", "PCB Design",
        "Machine Learning", "Deep Learning", "Computer Vision",
        "Natural Language Processing", "NLP",
        "Reinforcement Learning", "Robotics",
        "3D Printing", "Laser Cutting",
    ]
    text_lower = text.lower()
    for skill in common_skills:
        if skill.lower() in text_lower:
            result["skills"].append(skill)

    # Extract links
    github_match = re.search(r'github\.com/[\w-]+', text, re.IGNORECASE)
    if github_match:
        result["links"]["github"] = f"https://{github_match.group()}"

    linkedin_match = re.search(r'linkedin\.com/in/[\w-]+', text, re.IGNORECASE)
    if linkedin_match:
        result["links"]["linkedin"] = f"https://{linkedin_match.group()}"

    logger.info(f"Regex parsing fallback complete: {len(result['skills'])} skills found")
    return result


async def parse_resume(pdf_path: str) -> tuple[str, dict]:
    """
    Main entry point: extracts text from PDF, then parses with AI.
    Returns (raw_text, structured_data).
    """
    raw_text = extract_text_from_pdf(pdf_path)

    try:
        md_text = extract_markdown_from_pdf(pdf_path)
        parse_text = md_text if len(md_text) > len(raw_text) * 0.5 else raw_text
    except Exception:
        parse_text = raw_text

    structured = await parse_resume_with_ai(parse_text)

    return raw_text, structured
