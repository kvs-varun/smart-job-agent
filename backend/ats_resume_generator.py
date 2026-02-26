import os
from datetime import datetime
from typing import Dict, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


def _safe_filename(name: str) -> str:
    keep = []
    for ch in name:
        if ch.isalnum() or ch in ("-", "_"):
            keep.append(ch)
        else:
            keep.append("_")
    return "".join(keep)


def _wrap_text(c: canvas.Canvas, text: str, x: float, y: float, max_width: float, line_height: float) -> float:
    """Draw wrapped text and return the new y."""

    if not text:
        return y

    words = text.split()
    line = ""

    for w in words:
        candidate = (line + " " + w).strip()
        if c.stringWidth(candidate) <= max_width:
            line = candidate
        else:
            c.drawString(x, y, line)
            y -= line_height
            line = w

    if line:
        c.drawString(x, y, line)
        y -= line_height

    return y


def generate_ats_pdf(
    tailored_resume: Dict,
    output_dir: str,
    filename_prefix: str = "ats_resume",
    candidate_name: Optional[str] = None,
) -> str:
    """Generate a one-page, ATS-friendly PDF resume.

    Constraints:
    - Single column
    - No tables
    - No images
    - Uses simple headings + bullets

    Returns absolute file path.
    """

    os.makedirs(output_dir, exist_ok=True)

    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    name_part = _safe_filename(candidate_name or "candidate")
    file_name = f"{filename_prefix}_{name_part}_{stamp}.pdf"
    out_path = os.path.abspath(os.path.join(output_dir, file_name))

    # Register a common font if available; fall back to Helvetica.
    try:
        # Windows-friendly: Arial is common but not guaranteed.
        # We keep this safe; if font file isn't present, we just use Helvetica.
        pass
    except Exception:
        pass

    c = canvas.Canvas(out_path, pagesize=A4)
    width, height = A4

    left = 0.7 * inch
    right = 0.7 * inch
    top = 0.7 * inch
    bottom = 0.7 * inch

    x = left
    max_width = width - left - right

    y = height - top

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x, y, (candidate_name or "Your Name"))
    y -= 18

    c.setFont("Helvetica", 10)
    c.drawString(x, y, "Email: your.email@example.com | Phone: +91-XXXXXXXXXX | Location: India")
    y -= 16

    # Summary
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, "SUMMARY")
    y -= 14

    c.setFont("Helvetica", 10)
    y = _wrap_text(c, tailored_resume.get("summary", ""), x, y, max_width, 12)
    y -= 6

    # Skills
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, "SKILLS")
    y -= 14

    c.setFont("Helvetica", 10)
    skills: List[str] = tailored_resume.get("skills", []) or []
    skills_line = ", ".join(skills[:30])
    y = _wrap_text(c, skills_line, x, y, max_width, 12)
    y -= 6

    # Learning exposure (honest missing skills)
    learning: List[str] = tailored_resume.get("learning_exposure", []) or []
    if learning:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, "LEARNING (HONEST)")
        y -= 14

        c.setFont("Helvetica", 10)
        for ln in learning:
            y = _wrap_text(c, f"- {ln}", x, y, max_width, 12)
        y -= 6

    # Projects
    projects: List[str] = tailored_resume.get("projects", []) or []
    if projects:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, "PROJECTS")
        y -= 14

        c.setFont("Helvetica", 10)
        for p in projects[:5]:
            y = _wrap_text(c, f"- {p}", x, y, max_width, 12)
            if y < bottom + 80:
                break
        y -= 6

    # Experience (internships)
    exp: List[str] = tailored_resume.get("experience", []) or []
    if exp and y > bottom + 60:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, "EXPERIENCE / INTERNSHIPS")
        y -= 14

        c.setFont("Helvetica", 10)
        for e in exp[:4]:
            y = _wrap_text(c, f"- {e}", x, y, max_width, 12)
            if y < bottom + 60:
                break
        y -= 6

    # Education
    edu: List[str] = tailored_resume.get("education", []) or []
    if edu and y > bottom + 40:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, "EDUCATION")
        y -= 14

        c.setFont("Helvetica", 10)
        for e in edu[:3]:
            y = _wrap_text(c, f"- {e}", x, y, max_width, 12)
            if y < bottom + 30:
                break

    c.showPage()
    c.save()

    return out_path
