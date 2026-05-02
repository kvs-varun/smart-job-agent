"""
Harvard Chronological Resume Template — PDF Renderer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Classic professional format. Left-aligned, formal, objective first, education prominent.
Preferred by traditional Indian IT companies (TCS, Infosys, Wipro) and PSUs.
Works best on older ATS systems (common at large service companies).

ATS Compatibility: 98% (Workday, SAP SuccessFactors, PeopleSoft, Naukri older systems)
Best for: Service companies, PSU applications, formal corporate roles, campus drives.
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib import colors

FONT_NAME = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
PAGE_MARGIN = 0.75 * inch


def _styles():
    return {
        "name": ParagraphStyle(
            "name", fontName=FONT_BOLD, fontSize=18,
            alignment=TA_LEFT, spaceAfter=2,
        ),
        "contact": ParagraphStyle(
            "contact", fontName=FONT_NAME, fontSize=9,
            alignment=TA_LEFT, spaceAfter=6, textColor=colors.HexColor("#333333"),
        ),
        "section_header": ParagraphStyle(
            "section_header", fontName=FONT_BOLD, fontSize=11,
            spaceAfter=3, spaceBefore=8, textColor=colors.black,
            borderPad=2,
        ),
        "body": ParagraphStyle(
            "body", fontName=FONT_NAME, fontSize=9.5,
            leading=13, spaceAfter=2, alignment=TA_JUSTIFY,
        ),
        "bullet": ParagraphStyle(
            "bullet", fontName=FONT_NAME, fontSize=9.5,
            leading=13, spaceAfter=1, leftIndent=14, bulletIndent=2,
        ),
        "objective": ParagraphStyle(
            "objective", fontName=FONT_NAME, fontSize=9.5,
            leading=14, spaceAfter=2, alignment=TA_JUSTIFY,
            textColor=colors.HexColor("#222222"),
        ),
    }


def generate_pdf(resume: dict[str, Any], settings=None) -> tuple[Path, str]:
    """Generate Harvard Chronological PDF. Returns (path, download_url)."""
    if settings is None:
        from backend_v2.config import get_settings
        settings = get_settings()

    output_dir = settings.generated_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    contact = resume.get("contact", {})
    name = contact.get("name", "Candidate").strip()
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"harvard_{safe_name}_{timestamp}.pdf"
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
    story.append(Paragraph(name, styles["name"]))

    # ── CONTACT ──────────────────────────────────────────────────────────────
    contact_parts = [
        p for p in [
            contact.get("phone"), contact.get("email"),
            contact.get("location"),
            contact.get("linkedin"), contact.get("github"),
        ] if p
    ]
    story.append(Paragraph("  ·  ".join(contact_parts), styles["contact"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.black, spaceAfter=6))

    # ── OBJECTIVE / SUMMARY ───────────────────────────────────────────────────
    summary = resume.get("summary", "")
    if summary:
        story.append(Paragraph("OBJECTIVE / PROFESSIONAL SUMMARY", styles["section_header"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#666666"), spaceAfter=4))
        story.append(Paragraph(summary, styles["objective"]))

    # ── EDUCATION (prominent in Harvard format) ───────────────────────────────
    education = resume.get("education", [])
    if education:
        story.append(Paragraph("EDUCATION", styles["section_header"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#666666"), spaceAfter=4))

        for edu in education:
            inst = edu.get("institution", "")
            degree = edu.get("degree", "")
            field = edu.get("field", "")
            start_y = edu.get("startYear", "")
            end_y = edu.get("endYear", "")
            grade = edu.get("grade", "")
            location = edu.get("location", "India")

            degree_str = f"{degree} in {field}" if field else degree
            date_str = f"{start_y}–{end_y}" if start_y and end_y else end_y or start_y

            story.append(Paragraph(
                f"<b>{inst}</b>  {location}  {date_str}",
                styles["body"],
            ))
            story.append(Paragraph(degree_str, styles["body"]))
            if grade:
                story.append(Paragraph(f"GPA / CGPA: {grade}  |  Relevant Coursework: Data Structures, DBMS, Operating Systems", styles["bullet"]))

    # ── PROFESSIONAL EXPERIENCE ───────────────────────────────────────────────
    experience = resume.get("experience", [])
    if experience:
        story.append(Paragraph("PROFESSIONAL EXPERIENCE", styles["section_header"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#666666"), spaceAfter=4))

        for exp in experience:
            title = exp.get("title", "")
            company = exp.get("company", "")
            start = exp.get("startDate", "")
            end = "Present" if exp.get("current") else exp.get("endDate", "")
            location = exp.get("location", "")
            date_str = f"{start}–{end}" if start else end

            story.append(Paragraph(
                f"<b>{company}</b>  {location}  {date_str}",
                styles["body"],
            ))
            story.append(Paragraph(title, styles["body"]))

            desc = exp.get("description", "")
            for bullet in [b.strip() for b in desc.split("\n") if b.strip()]:
                bullet = bullet.lstrip("•-– ")
                story.append(Paragraph(f"• {bullet}", styles["bullet"]))
            story.append(Spacer(1, 3))

    # ── TECHNICAL SKILLS ─────────────────────────────────────────────────────
    skills = resume.get("skills", [])
    if skills:
        story.append(Paragraph("TECHNICAL SKILLS", styles["section_header"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#666666"), spaceAfter=4))

        skill_list = [str(s).strip() for s in skills if s]
        # Flat bullet list for Harvard format (simple, readable)
        for i in range(0, len(skill_list), 5):
            batch = skill_list[i:i+5]
            story.append(Paragraph("• " + "  •  ".join(batch), styles["bullet"]))

    # ── PROJECTS & ACHIEVEMENTS ───────────────────────────────────────────────
    projects = resume.get("projects", [])
    if projects:
        story.append(Paragraph("PROJECTS & ACHIEVEMENTS", styles["section_header"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#666666"), spaceAfter=4))

        for proj in projects[:4]:
            pname = proj.get("name", "")
            tech = proj.get("techStack", [])
            tech_str = ", ".join(tech) if isinstance(tech, list) else str(tech)
            github = proj.get("github", "")
            desc = proj.get("description", "")
            year = proj.get("year", "")

            header = f"<b>{pname}</b>"
            if year:
                header += f" ({year})"
            story.append(Paragraph(header, styles["body"]))
            if tech_str:
                story.append(Paragraph(f"Technologies: {tech_str}", styles["bullet"]))
            if desc:
                first_line = desc.split("\n")[0].strip().lstrip("•-– ")
                story.append(Paragraph(f"• {first_line}", styles["bullet"]))
            if github:
                story.append(Paragraph(f"• Repository: {github}", styles["bullet"]))
            story.append(Spacer(1, 2))

    doc.build(story)
    download_url = f"/v2/agent/download/{filename}"
    return output_path, download_url
