"""
AutoApply — Resume Tailoring Service

Takes the user's structured resume + a specific job description,
and generates a tailored resume emphasizing relevant skills and projects.
Outputs HTML that can be converted to PDF via WeasyPrint.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import google.generativeai as genai

from app.core.config import settings

logger = logging.getLogger(__name__)

TAILORING_PROMPT = """
You are a resume optimization expert. Given a candidate's resume data and a target job,
reorder and emphasize the resume content to maximize relevance for this specific role.

RESUME DATA:
{resume}

TARGET JOB:
Title: {title}
Company: {company}
Description: {description}

Instructions:
1. Reorder skills: Put the most relevant skills for THIS job first
2. Reorder projects: Put the most relevant projects first
3. Reorder experience: Put the most relevant experience first
4. For each project/experience, emphasize aspects relevant to this job
5. Keep ALL content — do not remove anything, just reorder and re-emphasize

Return ONLY valid JSON (no markdown, no code fences):
{{
    "name": "candidate name",
    "email": "email",
    "links": {{}},
    "summary": "A 2-sentence tailored professional summary for this specific role",
    "skills": ["most relevant first", "..."],
    "experience": [
        {{
            "company": "...",
            "title": "...",
            "duration": "...",
            "highlights": ["rewritten to emphasize relevant aspects"]
        }}
    ],
    "projects": [
        {{
            "name": "...",
            "description": "rewritten to emphasize relevant aspects",
            "technologies": ["..."]
        }}
    ],
    "education": [
        {{
            "institution": "...",
            "degree": "...",
            "field": "...",
            "year": "...",
            "gpa": "..."
        }}
    ]
}}
"""


RESUME_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
    @page {{ size: A4; margin: 1.5cm; }}
    body {{
        font-family: 'Helvetica Neue', Arial, sans-serif;
        font-size: 10pt;
        line-height: 1.4;
        color: #1a1a1a;
        margin: 0;
        padding: 0;
    }}
    .header {{
        text-align: center;
        margin-bottom: 12px;
        border-bottom: 2px solid #2563eb;
        padding-bottom: 8px;
    }}
    .header h1 {{
        margin: 0;
        font-size: 18pt;
        color: #1e293b;
        letter-spacing: 0.5px;
    }}
    .header .contact {{
        font-size: 9pt;
        color: #475569;
        margin-top: 4px;
    }}
    .header .contact a {{
        color: #2563eb;
        text-decoration: none;
    }}
    .section {{
        margin-bottom: 10px;
    }}
    .section h2 {{
        font-size: 11pt;
        color: #2563eb;
        text-transform: uppercase;
        letter-spacing: 1px;
        border-bottom: 1px solid #cbd5e1;
        padding-bottom: 3px;
        margin: 8px 0 6px 0;
    }}
    .summary {{
        font-size: 9.5pt;
        color: #334155;
        font-style: italic;
        margin-bottom: 8px;
    }}
    .skills {{
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
    }}
    .skill-tag {{
        background: #eff6ff;
        color: #1d4ed8;
        padding: 2px 8px;
        border-radius: 3px;
        font-size: 9pt;
    }}
    .entry {{
        margin-bottom: 8px;
    }}
    .entry-header {{
        display: flex;
        justify-content: space-between;
        align-items: baseline;
    }}
    .entry-header .title {{
        font-weight: 700;
        font-size: 10pt;
    }}
    .entry-header .duration {{
        font-size: 9pt;
        color: #64748b;
    }}
    .entry .org {{
        color: #475569;
        font-size: 9.5pt;
    }}
    .entry ul {{
        margin: 3px 0;
        padding-left: 18px;
    }}
    .entry li {{
        font-size: 9.5pt;
        margin-bottom: 2px;
    }}
    .tech-stack {{
        font-size: 8.5pt;
        color: #64748b;
        margin-top: 2px;
    }}
</style>
</head>
<body>
    <div class="header">
        <h1>{name}</h1>
        <div class="contact">
            {email}
            {links_html}
        </div>
    </div>

    {summary_html}

    <div class="section">
        <h2>Skills</h2>
        <div class="skills">
            {skills_html}
        </div>
    </div>

    {experience_html}

    {projects_html}

    {education_html}
</body>
</html>
"""


async def tailor_resume(
    resume_structured: dict,
    job_title: str,
    job_company: str,
    job_description: str,
) -> tuple[dict, str]:
    """
    Tailor a resume for a specific job.
    Returns (tailored_data, html_content).
    """
    if settings.gemini_api_key:
        try:
            tailored = await tailor_with_ai(
                resume_structured, job_title, job_company, job_description
            )
        except Exception as e:
            logger.error(f"AI tailoring failed: {e}, using basic reorder")
            tailored = basic_tailor(resume_structured, job_description)
    else:
        tailored = basic_tailor(resume_structured, job_description)

    html = render_resume_html(tailored)
    return tailored, html


async def tailor_with_ai(
    resume: dict, title: str, company: str, description: str
) -> dict:
    """Use Gemini to intelligently reorder and re-emphasize resume content."""
    model = genai.GenerativeModel(settings.gemini_model)

    prompt = TAILORING_PROMPT.format(
        resume=json.dumps(resume, indent=2),
        title=title,
        company=company,
        description=description[:3000],
    )

    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            temperature=0.3,
            response_mime_type="application/json",
        ),
    )

    return json.loads(response.text)


def basic_tailor(resume: dict, job_description: str) -> dict:
    """Basic tailoring: reorder skills by relevance (keyword matching)."""
    desc_lower = job_description.lower()
    skills = resume.get("skills", [])

    # Sort skills by whether they appear in the job description
    relevant = [s for s in skills if s.lower() in desc_lower]
    other = [s for s in skills if s.lower() not in desc_lower]

    tailored = {**resume, "skills": relevant + other}
    return tailored


def render_resume_html(data: dict) -> str:
    """Render tailored resume data as HTML with strict escaping."""
    import html
    
    def esc(val) -> str:
        if val is None:
            return ""
        return html.escape(str(val))

    # Links
    links = data.get("links", {})
    links_parts = []
    for key, url in links.items():
        if url:
            # Escape the url attribute and the key text
            links_parts.append(f' | <a href="{html.escape(url)}">{esc(key.capitalize())}</a>')
    links_html = "".join(links_parts)

    # Summary
    summary = data.get("summary", "")
    summary_html = f'<p class="summary">{esc(summary)}</p>' if summary else ""

    # Skills
    skills = data.get("skills", [])
    skills_html = "".join(f'<span class="skill-tag">{esc(s)}</span>' for s in skills)

    # Experience
    experience = data.get("experience", [])
    exp_parts = []
    if experience:
        exp_parts.append('<div class="section"><h2>Experience</h2>')
        for exp in experience:
            exp_parts.append('<div class="entry">')
            exp_parts.append('<div class="entry-header">')
            exp_parts.append(f'<span class="title">{esc(exp.get("title", ""))}</span>')
            exp_parts.append(f'<span class="duration">{esc(exp.get("duration", ""))}</span>')
            exp_parts.append('</div>')
            exp_parts.append(f'<div class="org">{esc(exp.get("company", ""))}</div>')
            highlights = exp.get("highlights", [])
            if isinstance(highlights, list) and highlights:
                exp_parts.append("<ul>")
                for h in highlights:
                    exp_parts.append(f"<li>{esc(h)}</li>")
                exp_parts.append("</ul>")
            elif exp.get("description"):
                exp_parts.append(f"<p>{esc(exp['description'])}</p>")
            techs = exp.get("technologies", [])
            if techs:
                exp_parts.append(f'<div class="tech-stack">Tech: {", ".join(esc(t) for t in techs)}</div>')
            exp_parts.append('</div>')
        exp_parts.append('</div>')
    experience_html = "\n".join(exp_parts)

    # Projects
    projects = data.get("projects", [])
    proj_parts = []
    if projects:
        proj_parts.append('<div class="section"><h2>Projects</h2>')
        for proj in projects:
            proj_parts.append('<div class="entry">')
            proj_parts.append(f'<div class="entry-header"><span class="title">{esc(proj.get("name", ""))}</span></div>')
            desc = proj.get("description", "")
            if desc:
                proj_parts.append(f"<p>{esc(desc)}</p>")
            techs = proj.get("technologies", [])
            if techs:
                proj_parts.append(f'<div class="tech-stack">Tech: {", ".join(esc(t) for t in techs)}</div>')
            proj_parts.append('</div>')
        proj_parts.append('</div>')
    projects_html = "\n".join(proj_parts)

    # Education
    education = data.get("education", [])
    edu_parts = []
    if education:
        edu_parts.append('<div class="section"><h2>Education</h2>')
        for edu in education:
            edu_parts.append('<div class="entry">')
            degree = f'{edu.get("degree", "")} in {edu.get("field", "")}'.strip(" in ")
            # Construct escaped degree in field safely
            field_text = f" in {esc(edu.get('field', ''))}" if edu.get("field") else ""
            degree_html = f'{esc(edu.get("degree", ""))}{field_text}'
            edu_parts.append(f'<div class="entry-header"><span class="title">{degree_html}</span>')
            edu_parts.append(f'<span class="duration">{esc(edu.get("year", ""))}</span></div>')
            edu_parts.append(f'<div class="org">{esc(edu.get("institution", ""))}</div>')
            gpa = edu.get("gpa")
            if gpa:
                edu_parts.append(f"<p>GPA: {esc(gpa)}</p>")
            edu_parts.append('</div>')
        edu_parts.append('</div>')
    education_html = "\n".join(edu_parts)

    return RESUME_HTML_TEMPLATE.format(
        name=esc(data.get("name", "")),
        email=esc(data.get("email", "")),
        links_html=links_html,
        summary_html=summary_html,
        skills_html=skills_html,
        experience_html=experience_html,
        projects_html=projects_html,
        education_html=education_html,
    )


def render_resume_latex(data: dict) -> str:
    """Render tailored resume data as clean, compilable LaTeX."""
    def esc(text) -> str:
        if text is None:
            return ""
        text = str(text)
        # Characters to escape: & % $ # _ { } ~ ^ \
        # Order is important! Backslash first.
        replacements = [
            ("\\", "\\textbackslash{}"),
            ("&", "\\&"),
            ("%", "\\%"),
            ("$", "\\$"),
            ("#", "\\#"),
            ("_", "\\_"),
            ("{", "\\{"),
            ("}", "\\}"),
            ("~", "\\textasciitilde{}"),
            ("^", "\\textasciicircum{}"),
        ]
        for orig, rep in replacements:
            text = text.replace(orig, rep)
        return text

    # Header section
    name = esc(data.get("name", ""))
    email = esc(data.get("email", ""))
    
    links = data.get("links", {})
    links_parts = []
    if email:
        links_parts.append("\\href{mailto:" + email + "}{" + email + "}")
    for key, url in links.items():
        if url:
            escaped_url = url.replace("%", "\\%").replace("&", "\\&").replace("#", "\\#").replace("_", "\\_")
            links_parts.append("\\href{" + escaped_url + "}{" + esc(key.capitalize()) + "}")
    
    links_str = " | ".join(links_parts)

    latex = [
        "\\documentclass[10pt,letterpaper]{article}",
        "\\usepackage[utf8]{inputenc}",
        "\\usepackage[margin=0.75in]{geometry}",
        "\\usepackage[hidelinks]{hyperref}",
        "\\usepackage{enumitem}",
        "\\pagestyle{empty}",
        "",
        "\\begin{document}",
        "",
        "\\begin{center}",
        "    {\\LARGE \\textbf{" + name + "}} \\\\",
        "    \\vspace{4pt}",
        "    \\small " + links_str,
        "\\end{center}",
        "\\vspace{-8pt}",
        "\\hrule",
        "\\vspace{8pt}",
    ]

    # Summary
    summary = data.get("summary", "")
    if summary:
        latex.extend([
            esc(summary),
            "\\vspace{8pt}",
        ])

    # Skills
    skills = data.get("skills", [])
    if skills:
        skills_str = ", ".join(esc(s) for s in skills)
        latex.extend([
            "\\noindent",
            "\\textbf{\\large Skills} \\\\",
            "\\vspace{-6pt}",
            "\\hrule",
            "\\vspace{4pt}",
            skills_str,
            "\\vspace{8pt}",
        ])

    # Experience
    experience = data.get("experience", [])
    if experience:
        latex.extend([
            "\\noindent",
            "\\textbf{\\large Experience} \\\\",
            "\\vspace{-6pt}",
            "\\hrule",
            "\\vspace{6pt}",
        ])
        for exp in experience:
            company = esc(exp.get("company", ""))
            title = esc(exp.get("title", ""))
            duration = esc(exp.get("duration", ""))
            
            latex.extend([
                "\\noindent",
                "\\textbf{" + title + "} \\hfill \\textit{" + duration + "} \\\\",
                "\\textit{" + company + "} \\\\",
                "\\vspace{-4pt}",
            ])
            
            highlights = exp.get("highlights", [])
            if isinstance(highlights, list) and highlights:
                latex.append("\\begin{itemize}[leftmargin=*, noitemsep, topsep=2pt, parsep=1pt]")
                for h in highlights:
                    latex.append("    \\item " + esc(h))
                latex.append("\\end{itemize}")
            elif exp.get("description"):
                latex.append(esc(exp["description"]))
                
            techs = exp.get("technologies", [])
            if techs:
                techs_str = ", ".join(esc(t) for t in techs)
                latex.append("\\noindent\\small\\textbf{Technologies:} " + techs_str + " \\\\")
            
            latex.append("\\vspace{4pt}")

    # Projects
    projects = data.get("projects", [])
    if projects:
        latex.extend([
            "\\noindent",
            "\\textbf{\\large Projects} \\\\",
            "\\vspace{-6pt}",
            "\\hrule",
            "\\vspace{6pt}",
        ])
        for proj in projects:
            proj_name = esc(proj.get("name", ""))
            desc = esc(proj.get("description", ""))
            techs = proj.get("technologies", [])
            
            latex.extend([
                "\\noindent",
                "\\textbf{" + proj_name + "} \\\\",
                "\\vspace{-4pt}",
            ])
            if desc:
                latex.append(desc + " \\\\")
            if techs:
                techs_str = ", ".join(esc(t) for t in techs)
                latex.append("\\noindent\\small\\textbf{Technologies:} " + techs_str + " \\\\")
            
            latex.append("\\vspace{4pt}")

    # Education
    education = data.get("education", [])
    if education:
        latex.extend([
            "\\noindent",
            "\\textbf{\\large Education} \\\\",
            "\\vspace{-6pt}",
            "\\hrule",
            "\\vspace{6pt}",
        ])
        for edu in education:
            institution = esc(edu.get("institution", ""))
            degree = esc(edu.get("degree", ""))
            field = esc(edu.get("field", ""))
            year = esc(edu.get("year", ""))
            gpa = esc(edu.get("gpa", ""))
            
            field_text = " in " + field if field else ""
            degree_str = degree + field_text
            
            latex.extend([
                "\\noindent",
                "\\textbf{" + degree_str + "} \\hfill \\textit{" + year + "} \\\\",
                "\\textit{" + institution + "} \\\\",
                "\\vspace{-4pt}",
            ])
            if gpa:
                latex.append("GPA: " + gpa + " \\\\")
            latex.append("\\vspace{4pt}")

    latex.append("\\end{document}")
    return "\n".join(latex)


async def save_tailored_resume(
    resume_structured: dict,
    job_title: str,
    job_company: str,
    job_description: str,
) -> str:
    """
    Generate and save a tailored resume PDF/HTML.
    Returns the file path.
    """
    tailored_data, html_content = await tailor_resume(
        resume_structured, job_title, job_company, job_description
    )

    # Generate filename
    safe_company = "".join(c if c.isalnum() else "_" for c in job_company)
    timestamp = datetime.now().strftime("%Y%m%d")
    filename = f"resume_{safe_company}_{timestamp}.html"

    # Save HTML (PDF conversion via WeasyPrint can be added)
    output_path = settings.generated_path / filename
    output_path.write_text(html_content, encoding="utf-8")

    # Save LaTeX version
    latex_content = render_resume_latex(tailored_data)
    latex_path = output_path.with_suffix(".tex")
    latex_path.write_text(latex_content, encoding="utf-8")

    logger.info(f"Tailored resume HTML saved: {output_path}")
    logger.info(f"Tailored resume LaTeX saved: {latex_path}")
    return str(output_path)
