import re
from typing import Dict, List


def _clean_lines(text: str) -> List[str]:
    if not text:
        return []

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln]
    return lines


def _find_section_indices(lines: List[str], headings: List[str]) -> Dict[int, str]:
    idx_to_heading: Dict[int, str] = {}
    for i, ln in enumerate(lines):
        normalized = re.sub(r"[^a-z ]", "", ln.lower()).strip()
        for h in headings:
            if normalized == h:
                idx_to_heading[i] = h
                break
    return idx_to_heading


def parse_resume_text(resume_text: str) -> Dict:
    """Convert raw resume text into a structured JSON-like dict.

    This is intentionally rule-based and beginner-readable. It is not a full NLP parser.

    Output sections:
    - summary (str)
    - skills (list[str])
    - projects (list[str])
    - education (list[str])
    - experience (list[str])

    Heuristics are tuned for common Indian fresher resumes:
    - Headings like "Summary", "Skills", "Projects", "Education", "Experience", "Internship".
    - Bullet-ish lines starting with -, *, , .
    """

    lines = _clean_lines(resume_text)

    headings = [
        "summary",
        "professional summary",
        "objective",
        "skills",
        "technical skills",
        "projects",
        "personal projects",
        "internship",
        "internships",
        "experience",
        "work experience",
        "education",
        "certifications",
        "achievements",
    ]

    idx_to_heading = _find_section_indices(lines, headings)

    # If we can't detect headings, fall back to a simple structure.
    if not idx_to_heading:
        return {
            "summary": " ".join(lines[:3]).strip(),
            "skills": [],
            "projects": lines[3:10],
            "education": [],
            "experience": [],
            "raw": resume_text,
        }

    sorted_indices = sorted(idx_to_heading.keys())

    def slice_section(start_idx: int, end_idx: int) -> List[str]:
        chunk = lines[start_idx + 1 : end_idx]
        return chunk

    sections: Dict[str, List[str]] = {"summary": [], "skills": [], "projects": [], "education": [], "experience": []}

    for pos, start in enumerate(sorted_indices):
        heading = idx_to_heading[start]
        end = sorted_indices[pos + 1] if (pos + 1) < len(sorted_indices) else len(lines)
        chunk = slice_section(start, end)

        if heading in ("summary", "professional summary", "objective"):
            sections["summary"].extend(chunk)
        elif heading in ("skills", "technical skills"):
            sections["skills"].extend(chunk)
        elif heading in ("projects", "personal projects"):
            sections["projects"].extend(chunk)
        elif heading in ("education",):
            sections["education"].extend(chunk)
        elif heading in ("experience", "work experience", "internship", "internships"):
            sections["experience"].extend(chunk)
        else:
            # Ignore other headings for now.
            pass

    summary = " ".join(sections["summary"]).strip()

    # Skills parsing: split comma/pipe separated lines, keep short tokens.
    skill_tokens: List[str] = []
    for ln in sections["skills"]:
        for tok in re.split(r"[,|/]+", ln):
            tok = tok.strip(" -*")
            if not tok:
                continue
            # Avoid extremely long sentences.
            if len(tok) > 40:
                continue
            skill_tokens.append(tok)

    # De-duplicate while keeping order.
    seen = set()
    skills: List[str] = []
    for s in skill_tokens:
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        skills.append(s)

    def normalize_bullets(items: List[str]) -> List[str]:
        out: List[str] = []
        for ln in items:
            ln = re.sub(r"^[-*]+\s*", "", ln).strip()
            if ln:
                out.append(ln)
        return out

    structured = {
        "summary": summary,
        "skills": skills,
        "projects": normalize_bullets(sections["projects"]),
        "education": normalize_bullets(sections["education"]),
        "experience": normalize_bullets(sections["experience"]),
        "raw": resume_text,
    }

    return structured


def parse_resume_text_to_json(text: str) -> Dict:
    """Parse resume text into a conservative structured JSON.

    Keys:
    - name (str|None)
    - contact: {email, phone}
    - summary (str)
    - skills (list[str])
    - projects (list[str])
    - education (list[str])
    - experience (list[str])
    - parse_warnings (list[str])
    """

    warnings: List[str] = []
    raw = text or ""

    email_match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", raw, flags=re.I)
    phone_match = re.search(r"(\+91[\s-]?)?[6-9]\d{9}", raw)

    # Very conservative name guess: first non-empty line that isn't an email/phone.
    lines = _clean_lines(raw)
    name = None
    for ln in lines[:5]:
        if email_match and email_match.group(0).lower() in ln.lower():
            continue
        if phone_match and phone_match.group(0) in ln:
            continue
        if len(ln.split()) <= 5 and len(ln) <= 40:
            name = ln.strip()
            break

    structured = parse_resume_text(raw)
    summary = structured.get("summary", "")
    if not summary:
        warnings.append("Summary section not detected; using fallback summary.")

    if not structured.get("skills"):
        warnings.append("Skills section not detected. Consider adding a SKILLS section.")

    return {
        "name": name,
        "contact": {
            "email": email_match.group(0) if email_match else None,
            "phone": phone_match.group(0) if phone_match else None,
        },
        "summary": summary,
        "skills": structured.get("skills", []),
        "projects": structured.get("projects", []),
        "education": structured.get("education", []),
        "experience": structured.get("experience", []),
        "parse_warnings": warnings,
        "raw": raw,
    }
