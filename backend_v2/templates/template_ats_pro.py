"""
ATS Pro Template — PDF Renderer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pixel-accurate ReportLab translation of ATSMinimal.tsx (React live preview).
Every section, ordering, font size, spacing, and bullet style is kept in sync.

Section order  (matches ATSMinimal.tsx exactly):
  1. Header: Name / Job Title / Contact
  2. PROFESSIONAL SUMMARY
  3. TECHNICAL SKILLS  (single dot-separated line)
  4. PROFESSIONAL EXPERIENCE
  5. PROJECTS
  6. EDUCATION
  7. CERTIFICATIONS
  8. ACHIEVEMENTS & AWARDS
  9. OPEN SOURCE CONTRIBUTIONS
 10. VOLUNTEERING & COMMUNITY
 11. LANGUAGES

ATS Compatibility: 99 %
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle,
)
from reportlab.lib import colors

# ── Typography — exactly mirrors frontend ATSMinimal.tsx fonts ────────────────
FONT_SERIF      = "Times-Roman"
FONT_BOLD       = "Times-Bold"
FONT_ITALIC     = "Times-Italic"
FONT_BOLD_ITALIC = "Times-BoldItalic"

# ── Colour palette — mirrors C {} in ATSMinimal.tsx ───────────────────────────
C_NAME    = colors.HexColor("#0F1923")   # near-black
C_TITLE   = colors.HexColor("#374151")   # charcoal
C_CONTACT = colors.HexColor("#4B5563")   # medium gray
C_SECTION = colors.HexColor("#0F1923")   # same as name
C_BODY    = colors.HexColor("#1F2937")   # dark charcoal
C_RULE    = colors.HexColor("#9CA3AF")   # light gray divider

PAGE_MARGIN = 0.60 * inch


# ── Style factory (keeps identical sizes to the TSX) ─────────────────────────

def _styles() -> dict:
    return {
        "name": ParagraphStyle(
            "name",
            fontName=FONT_BOLD, fontSize=20, leading=26,
            alignment=TA_CENTER, textColor=C_NAME,
            spaceBefore=0, spaceAfter=2,
        ),
        "job_title": ParagraphStyle(
            "job_title",
            fontName=FONT_ITALIC, fontSize=10.5, leading=14,
            alignment=TA_CENTER, textColor=C_TITLE,
            spaceBefore=0, spaceAfter=3,
        ),
        "contact": ParagraphStyle(
            "contact",
            fontName=FONT_SERIF, fontSize=9.5, leading=12,
            alignment=TA_CENTER, textColor=C_CONTACT,
            spaceBefore=0, spaceAfter=5,
        ),
        # ── Section header — uppercase, same weight as TSX h2 ──────────────
        "section_head": ParagraphStyle(
            "section_head",
            fontName=FONT_BOLD, fontSize=10.5, leading=13,
            textColor=C_SECTION, spaceBefore=7, spaceAfter=1,
        ),
        # ── Role / Project title (bold, 10.5 pt) ────────────────────────────
        "entry_title": ParagraphStyle(
            "entry_title",
            fontName=FONT_BOLD, fontSize=10.5, leading=13,
            textColor=C_SECTION, spaceBefore=0, spaceAfter=0,
        ),
        # ── Sub-line (italic, 9.5 pt) — location, tech stack ───────────────
        "subline": ParagraphStyle(
            "subline",
            fontName=FONT_ITALIC, fontSize=9.5, leading=12,
            textColor=C_CONTACT, spaceBefore=0, spaceAfter=1,
        ),
        # ── Body text (10 pt) — summary, single-para descriptions ──────────
        "body": ParagraphStyle(
            "body",
            fontName=FONT_SERIF, fontSize=10, leading=14,
            textColor=C_BODY, spaceBefore=0, spaceAfter=1,
            alignment=TA_JUSTIFY,
        ),
        # ── Bullet line (10 pt, left-indented) ─────────────────────────────
        "bullet": ParagraphStyle(
            "bullet",
            fontName=FONT_SERIF, fontSize=10, leading=13.5,
            textColor=C_BODY, spaceBefore=0, spaceAfter=0,
            leftIndent=10, firstLineIndent=-10,
        ),
        # ── Small auxiliary text (9.5 pt) — grade, cert date, etc. ─────────
        "small": ParagraphStyle(
            "small",
            fontName=FONT_SERIF, fontSize=9.5, leading=12,
            textColor=C_CONTACT, spaceBefore=0, spaceAfter=1,
        ),
        # ── Skills single-line body ─────────────────────────────────────────
        "skills_line": ParagraphStyle(
            "skills_line",
            fontName=FONT_SERIF, fontSize=10, leading=14.5,
            textColor=C_BODY, spaceBefore=0, spaceAfter=1,
        ),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _rule(after: float = 3) -> HRFlowable:
    return HRFlowable(
        width="100%", thickness=0.75, color=C_RULE,
        spaceBefore=0, spaceAfter=after,
    )


def _section(title: str, story: list, styles: dict) -> None:
    """Append uppercase section header + thin rule to story."""
    story.append(Paragraph(title.upper(), styles["section_head"]))
    story.append(_rule(after=4))


def _two_col(left_para: Paragraph, right_para: Paragraph, avail_w: float) -> Table:
    """
    Two-column row: left is bold entry title, right is date/link (right-aligned).
    Mirrors the flex justify-between layout in ATSMinimal.tsx.
    """
    date_w = 1.1 * inch          # enough for "MMM YYYY – Present"
    name_w = avail_w - date_w
    t = Table([[left_para, right_para]], colWidths=[name_w, date_w])
    t.setStyle(TableStyle([
        ("VALIGN",    (0, 0), (-1, -1), "BOTTOM"),
        ("ALIGN",     (1, 0), (1, 0),  "RIGHT"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
    ]))
    return t


def _desc_bullets(desc: str, styles: dict) -> list:
    """
    Parse description the same way as ATSMinimal.tsx:
      - Split on \\n, strip, drop blanks
      - If any line starts with a bullet char → strip prefix, re-add •
      - Multiple lines without bullet prefix → treat each as a bullet
      - Single line (no break) → body paragraph, no bullet
    """
    lines = [l.strip() for l in (desc or "").split("\n") if l.strip()]
    if not lines:
        return []

    has_bullets = any(re.match(r"^[•\-–*]", l) for l in lines)

    if len(lines) == 1 and not has_bullets:
        return [Paragraph(lines[0], styles["body"])]

    out = []
    for line in lines:
        text = re.sub(r"^[•\-–*]\s*", "", line)
        out.append(Paragraph(f"•  {text}", styles["bullet"]))
    return out


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_pdf(resume: dict[str, Any], settings=None) -> tuple[Path, str]:
    """
    Generate an ATS Pro PDF that exactly matches the ATSMinimal.tsx live preview.
    Returns (output_path, download_url).
    """
    if settings is None:
        from backend_v2.config import get_settings
        settings = get_settings()

    output_dir = settings.generated_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    contact = resume.get("contact", {})
    name = contact.get("name", "Candidate").strip()
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ats_pro_{safe_name}_{ts}.pdf"
    output_path = output_dir / filename

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=LETTER,
        leftMargin=PAGE_MARGIN, rightMargin=PAGE_MARGIN,
        topMargin=PAGE_MARGIN, bottomMargin=PAGE_MARGIN,
    )

    avail_w = LETTER[0] - 2 * PAGE_MARGIN
    styles  = _styles()
    story   = []

    # ── 1. HEADER ─────────────────────────────────────────────────────────────
    story.append(Paragraph(name, styles["name"]))

    job_title = contact.get("jobTitle", "")
    if job_title:
        story.append(Paragraph(job_title, styles["job_title"]))

    contact_parts = [p for p in [
        contact.get("email"), contact.get("phone"), contact.get("location"),
        contact.get("linkedin"), contact.get("github"), contact.get("portfolio"),
    ] if p]
    if contact_parts:
        story.append(Paragraph("  |  ".join(contact_parts), styles["contact"]))

    story.append(_rule(after=7))

    # ── 2. PROFESSIONAL SUMMARY ───────────────────────────────────────────────
    summary = resume.get("summary", "")
    if summary:
        _section("Professional Summary", story, styles)
        story.append(Paragraph(summary, styles["body"]))
        story.append(Spacer(1, 4))

    # ── 3. TECHNICAL SKILLS — single dot-separated line ────────────────────────
    skills = [str(s).strip() for s in resume.get("skills", []) if s]
    if skills:
        _section("Technical Skills", story, styles)
        story.append(Paragraph("  ·  ".join(skills), styles["skills_line"]))
        story.append(Spacer(1, 4))

    # ── 4. PROFESSIONAL EXPERIENCE ────────────────────────────────────────────
    experience = resume.get("experience", [])
    if experience:
        _section("Professional Experience", story, styles)
        for i, exp in enumerate(experience):
            title_str   = exp.get("title", "")
            company_str = exp.get("company", "")
            start       = exp.get("startDate", "")
            end         = "Present" if exp.get("current") else exp.get("endDate", "")
            date_str    = " – ".join(filter(None, [start, end]))
            location    = exp.get("location", "")
            desc        = exp.get("description", "")

            # "Title — Company" left, date right (two-column)
            heading = f"{title_str}" + (f" — {company_str}" if company_str else "")
            left_p  = Paragraph(f"<b>{heading}</b>", styles["entry_title"])
            right_p = Paragraph(date_str, styles["small"])
            story.append(_two_col(left_p, right_p, avail_w))

            if location:
                story.append(Paragraph(f"<i>{location}</i>", styles["subline"]))

            story.extend(_desc_bullets(desc, styles))

            # Gap between entries (not after last)
            if i < len(experience) - 1:
                story.append(Spacer(1, 5))

        story.append(Spacer(1, 4))

    # ── 5. PROJECTS ───────────────────────────────────────────────────────────
    projects = resume.get("projects", [])
    if projects:
        _section("Projects", story, styles)
        for i, proj in enumerate(projects):
            pname   = proj.get("name", "Untitled Project")
            tech    = proj.get("techStack", [])
            github  = proj.get("github", "")
            demo    = proj.get("demo", "")
            desc    = proj.get("description", "")

            tech_str    = "  ·  ".join(t for t in tech[:6] if t) if isinstance(tech, list) else ""
            github_disp = github.replace("https://", "").replace("http://", "") if github else ""
            demo_disp   = demo.replace("https://", "").replace("http://", "")   if demo   else ""

            # Row 1: project name (left) + github (right)
            left_p  = Paragraph(f"<b>{pname}</b>", styles["entry_title"])
            right_p = Paragraph(github_disp, styles["small"])
            story.append(_two_col(left_p, right_p, avail_w))

            # Row 2: Tech stack + demo (only if present)
            sub_parts = []
            if tech_str:
                sub_parts.append(f"<i>Tech:</i> {tech_str}")
            if demo_disp:
                sub_parts.append(f"<i>Demo:</i> {demo_disp}")
            if sub_parts:
                story.append(Paragraph("  |  ".join(sub_parts), styles["subline"]))

            # Row 3: description bullets
            story.extend(_desc_bullets(desc, styles))

            if i < len(projects) - 1:
                story.append(Spacer(1, 5))

        story.append(Spacer(1, 4))

    # ── 6. EDUCATION ──────────────────────────────────────────────────────────
    education = resume.get("education", [])
    if education:
        _section("Education", story, styles)
        for i, edu in enumerate(education):
            degree  = edu.get("degree", "")
            field   = edu.get("field", "")
            inst    = edu.get("institution", "")
            start_y = edu.get("startYear", "")
            end_y   = edu.get("endYear", "")
            grade   = edu.get("grade", "")

            degree_str = " ".join(filter(None, [degree, f"in {field}" if field else ""]))
            date_str   = " – ".join(filter(None, [start_y, end_y]))

            # "Degree in Field" left, year right
            left_p  = Paragraph(f"<b>{degree_str}</b>", styles["entry_title"])
            right_p = Paragraph(date_str, styles["small"])
            story.append(_two_col(left_p, right_p, avail_w))

            if inst:
                story.append(Paragraph(inst, styles["body"]))
            if grade:
                story.append(Paragraph(grade, styles["small"]))

            if i < len(education) - 1:
                story.append(Spacer(1, 4))

        story.append(Spacer(1, 4))

    # ── 7. CERTIFICATIONS ─────────────────────────────────────────────────────
    certs = resume.get("certifications", [])
    if certs:
        _section("Certifications", story, styles)
        for i, cert in enumerate(certs):
            cert_name = cert.get("name", "")
            issuer    = cert.get("issuer", "")
            issued    = cert.get("issuedDate", "")
            expiry    = cert.get("expiryDate", "")
            date_str  = issued + (f" – {expiry}" if expiry else "")

            label = cert_name + (f" — {issuer}" if issuer else "")
            left_p  = Paragraph(f"<b>{cert_name}</b>" + (f" — {issuer}" if issuer else ""), styles["body"])
            right_p = Paragraph(date_str, styles["small"])
            story.append(_two_col(left_p, right_p, avail_w))

            if i < len(certs) - 1:
                story.append(Spacer(1, 2))

        story.append(Spacer(1, 4))

    # ── 8. ACHIEVEMENTS & AWARDS ──────────────────────────────────────────────
    achievements = resume.get("achievements", [])
    if achievements:
        _section("Achievements & Awards", story, styles)
        for i, ach in enumerate(achievements):
            title = ach.get("title", "")
            desc  = ach.get("description", "")
            date  = ach.get("date", "")

            label_text = f"<b>{title}</b>" + (f" — {desc}" if desc else "")
            left_p  = Paragraph(label_text, styles["body"])
            right_p = Paragraph(date, styles["small"])
            story.append(_two_col(left_p, right_p, avail_w))

            if i < len(achievements) - 1:
                story.append(Spacer(1, 2))

        story.append(Spacer(1, 4))

    # ── 9. OPEN SOURCE ────────────────────────────────────────────────────────
    open_source = resume.get("openSource", [])
    if open_source:
        _section("Open Source Contributions", story, styles)
        for i, os_entry in enumerate(open_source):
            proj  = os_entry.get("project", "")
            gh    = os_entry.get("github", "").replace("https://", "")
            contrib = os_entry.get("contribution", "")

            label_text = f"<b>{proj}</b>" + (f"  {gh}" if gh else "")
            story.append(Paragraph(label_text, styles["body"]))
            if contrib:
                story.append(Paragraph(contrib, styles["small"]))

            if i < len(open_source) - 1:
                story.append(Spacer(1, 3))

        story.append(Spacer(1, 4))

    # ── 10. VOLUNTEERING & COMMUNITY ──────────────────────────────────────────
    volunteering = resume.get("volunteering", [])
    if volunteering:
        _section("Volunteering & Community", story, styles)
        for i, vol in enumerate(volunteering):
            role  = vol.get("role", "")
            org   = vol.get("organization", "")
            start = vol.get("startDate", "")
            end   = vol.get("endDate", "")
            desc  = vol.get("description", "")
            date_str = " – ".join(filter(None, [start, end]))

            heading = role + (f" — {org}" if org else "")
            left_p  = Paragraph(f"<b>{heading}</b>", styles["entry_title"])
            right_p = Paragraph(date_str, styles["small"])
            story.append(_two_col(left_p, right_p, avail_w))

            if desc:
                story.append(Paragraph(desc, styles["small"]))

            if i < len(volunteering) - 1:
                story.append(Spacer(1, 3))

        story.append(Spacer(1, 4))

    # ── 11. LANGUAGES ─────────────────────────────────────────────────────────
    languages = resume.get("languages", [])
    if languages:
        _section("Languages", story, styles)
        lang_parts = [
            f"{l.get('language', '')} ({l.get('proficiency', '')})" if l.get("proficiency")
            else l.get("language", "")
            for l in languages
        ]
        story.append(Paragraph("  ·  ".join(lang_parts), styles["skills_line"]))

    # ── Build ──────────────────────────────────────────────────────────────────
    doc.build(story)
    download_url = f"/v2/agent/download/{filename}"
    return output_path, download_url
