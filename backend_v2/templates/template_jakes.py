"""
Jake's Resume Template — PDF Renderer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The most widely used tech resume format globally. Single-column, LaTeX-inspired.
UPPERCASE section headers + horizontal rules. Skills before experience.
~65% of successful FAANG India / top startup applications use this format.

ATS Compatibility: 99% (Workday, Taleo, Greenhouse, iCIMS, Naukri)
Best for: Software engineers, backend/frontend, data scientists at product companies.
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether
)
from reportlab.lib import colors


# ─── Typography ───────────────────────────────────────────────────────────────
FONT_NAME = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
NAME_SIZE = 20
SECTION_SIZE = 10.5
BODY_SIZE = 9.5
CONTACT_SIZE = 9
LINE_SPACING = 13
PAGE_MARGIN = 0.55 * inch


def _styles():
    base = getSampleStyleSheet()
    return {
        "name": ParagraphStyle(
            "name", fontName=FONT_BOLD, fontSize=NAME_SIZE,
            alignment=TA_CENTER, spaceAfter=2,
        ),
        "contact": ParagraphStyle(
            "contact", fontName=FONT_NAME, fontSize=CONTACT_SIZE,
            alignment=TA_CENTER, spaceAfter=4,
        ),
        "section_header": ParagraphStyle(
            "section_header", fontName=FONT_BOLD, fontSize=SECTION_SIZE,
            spaceAfter=2, spaceBefore=6, textColor=colors.black,
        ),
        "body": ParagraphStyle(
            "body", fontName=FONT_NAME, fontSize=BODY_SIZE,
            leading=LINE_SPACING, spaceAfter=1,
        ),
        "bullet": ParagraphStyle(
            "bullet", fontName=FONT_NAME, fontSize=BODY_SIZE,
            leading=LINE_SPACING, spaceAfter=1, leftIndent=12, bulletIndent=2,
        ),
        "bold_inline": ParagraphStyle(
            "bold_inline", fontName=FONT_BOLD, fontSize=BODY_SIZE,
            leading=LINE_SPACING, spaceAfter=0,
        ),
        "skills_label": ParagraphStyle(
            "skills_label", fontName=FONT_BOLD, fontSize=BODY_SIZE,
            leading=LINE_SPACING, spaceAfter=1,
        ),
    }


def generate_pdf(resume: dict[str, Any], settings=None) -> tuple[Path, str]:
    """Generate Jake's Resume PDF. Returns (path, download_url)."""
    if settings is None:
        from backend_v2.config import get_settings
        settings = get_settings()

    output_dir = settings.generated_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    contact = resume.get("contact", {})
    name = contact.get("name", "Candidate").strip()
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"jakes_{safe_name}_{timestamp}.pdf"
    output_path = output_dir / filename

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=LETTER,
        leftMargin=PAGE_MARGIN, rightMargin=PAGE_MARGIN,
        topMargin=PAGE_MARGIN, bottomMargin=PAGE_MARGIN,
    )

    styles = _styles()
    story = []

    # ── NAME ──────────────────────────────────────────────────────────────────
    story.append(Paragraph(name.upper(), styles["name"]))

    # ── CONTACT LINE ─────────────────────────────────────────────────────────
    contact_parts = [
        p for p in [
            contact.get("phone"), contact.get("email"),
            contact.get("linkedin"), contact.get("github"),
            contact.get("location"),
        ] if p
    ]
    if contact_parts:
        story.append(Paragraph(" | ".join(contact_parts), styles["contact"]))

    story.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceAfter=4))

    # ── EDUCATION ─────────────────────────────────────────────────────────────
    education = resume.get("education", [])
    if education:
        story.append(Paragraph("EDUCATION", styles["section_header"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.black, spaceAfter=3))
        for edu in education:
            inst = edu.get("institution", "")
            degree = edu.get("degree", "")
            field = edu.get("field", "")
            start_y = edu.get("startYear", "")
            end_y = edu.get("endYear", "")
            grade = edu.get("grade", "")
            date_str = f"{start_y}–{end_y}" if start_y and end_y else end_y or start_y
            degree_str = f"{degree} in {field}" if field else degree
            story.append(Paragraph(
                f"<b>{inst}</b> — {degree_str} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {date_str}",
                styles["body"],
            ))
            if grade:
                story.append(Paragraph(f"CGPA / Grade: {grade}", styles["body"]))

    # ── SKILLS ────────────────────────────────────────────────────────────────
    skills = resume.get("skills", [])
    if skills:
        story.append(Spacer(1, 4))
        story.append(Paragraph("SKILLS", styles["section_header"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.black, spaceAfter=3))

        # Group skills into categories (Languages / Frameworks / Tools) heuristically
        language_kws = {"python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "kotlin", "dart", "r", "scala", "c"}
        framework_kws = {"react", "angular", "vue", "django", "flask", "fastapi", "spring", "express", "nextjs", "next.js", "laravel", "flutter"}
        tool_kws = {"docker", "kubernetes", "git", "aws", "gcp", "azure", "postgresql", "mysql", "mongodb", "redis", "kafka", "jenkins", "github", "linux"}

        skill_list = [str(s).strip() for s in skills if s]
        languages = [s for s in skill_list if s.lower() in language_kws]
        frameworks = [s for s in skill_list if s.lower() in framework_kws]
        tools = [s for s in skill_list if s.lower() in tool_kws]
        others = [s for s in skill_list if s not in languages + frameworks + tools]

        categories = []
        if languages:
            categories.append(("Languages", languages))
        if frameworks:
            categories.append(("Frameworks", frameworks))
        if tools:
            categories.append(("Tools", tools))
        if others:
            categories.append(("Other", others))

        if not categories:
            categories = [("Technical Skills", skill_list)]

        for label, cat_skills in categories:
            story.append(Paragraph(
                f"<b>{label}:</b> {', '.join(cat_skills)}",
                styles["body"],
            ))

    # ── EXPERIENCE ────────────────────────────────────────────────────────────
    experience = resume.get("experience", [])
    if experience:
        story.append(Spacer(1, 4))
        story.append(Paragraph("EXPERIENCE", styles["section_header"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.black, spaceAfter=3))

        for exp in experience:
            title = exp.get("title", "")
            company = exp.get("company", "")
            start = exp.get("startDate", "")
            end = "Present" if exp.get("current") else exp.get("endDate", "")
            location = exp.get("location", "")
            date_str = f"{start} – {end}" if start else end

            story.append(Paragraph(
                f"<b>{title}</b> — {company} &nbsp; | &nbsp; {date_str}",
                styles["body"],
            ))
            if location:
                story.append(Paragraph(location, styles["body"]))

            desc = exp.get("description", "")
            for bullet in [b.strip() for b in desc.split("\n") if b.strip()]:
                bullet = bullet.lstrip("•-– ")
                story.append(Paragraph(f"• {bullet}", styles["bullet"]))

    # ── PROJECTS ─────────────────────────────────────────────────────────────
    projects = resume.get("projects", [])
    if projects:
        story.append(Spacer(1, 4))
        story.append(Paragraph("PROJECTS", styles["section_header"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.black, spaceAfter=3))

        for proj in projects[:4]:
            pname = proj.get("name", "")
            tech = proj.get("techStack", [])
            tech_str = ", ".join(tech) if isinstance(tech, list) else str(tech)
            github = proj.get("github", "")
            desc = proj.get("description", "")

            header = f"<b>{pname}</b>"
            if tech_str:
                header += f" | <i>{tech_str}</i>"
            if github:
                header += f" | {github}"
            story.append(Paragraph(header, styles["body"]))

            if desc:
                for bullet in [b.strip() for b in desc.split("\n") if b.strip()]:
                    bullet = bullet.lstrip("•-– ")
                    story.append(Paragraph(f"• {bullet}", styles["bullet"]))

    doc.build(story)
    download_url = f"/v2/agent/download/{filename}"
    return output_path, download_url
