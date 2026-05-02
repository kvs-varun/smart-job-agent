"""
Agent 2 — Content Enhancement Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Role: Linguistic quality engineer and ATS alignment checker.
Runs IN PARALLEL with Agent 1. Catches weak language, bad formatting,
missing keywords, and template alignment issues in real time.

Model: claude-sonnet-4-6 (parallel to Agent 1)
"""
import json
import logging
from typing import Any

from backend_v2.agents.tools.gemini_client import gemini_json

from backend_v2.agents.state import AgentState, AGENT_ENHANCER, HEALTH_OK, HEALTH_FAILED
from backend_v2.agents.tools.kb_tools import get_ats_keywords, infer_role
from backend_v2.config import get_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior resume quality editor and ATS compliance specialist.
You are the SECOND pass after the Resume Architect. Your job is to make the already-rewritten
resume even sharper — tightening language, maximizing ATS keyword density, and eliminating any
remaining weak phrasing that slipped through.

YOUR MANDATE:
1. ERADICATE WEAK VERBS: Any remaining "did", "worked on", "helped", "assisted", "participated",
   "was responsible for", "involved in" → replace with power verbs (Built, Engineered, Architected,
   Automated, Delivered, Optimized, Spearheaded, Led, Deployed, Implemented, Streamlined)

2. INJECT METRICS: If a bullet lacks numbers, add implied quantification:
   "built API" → "built 5-endpoint REST API"
   "improved performance" → "improved response time by 35%"
   "deployed app" → "deployed to cloud serving 100+ daily users"

3. FIX ALL CAPITALIZATIONS:
   python→Python, javascript→JavaScript, typescript→TypeScript, postgresql→PostgreSQL,
   mongodb→MongoDB, mysql→MySQL, github→GitHub, aws→AWS, gcp→GCP, docker→Docker,
   kubernetes→Kubernetes, react→React, nextjs→Next.js, nodejs→Node.js, fastapi→FastAPI

4. ATS KEYWORD DENSITY: Naturally weave role-critical keywords into bullets and summary.
   Do NOT keyword-stuff — integrate them into meaningful sentences.

5. REMOVE FIRST-PERSON: "I built" → "Built", "I developed" → "Developed", "My project" → "Project"

6. DATE FORMAT: ALL dates must be "MMM YYYY" (e.g., "Jan 2023", "Aug 2025")

7. PROFESSIONAL TONE: Remove informal language, casual phrasing, filler words ("basically",
   "various", "multiple things", "etc.", "and more")

8. SUMMARY PUNCH: If summary is weak or generic, rewrite it as a 2-3 sentence pitch that:
   - Opens with role identity + years/level
   - Names their best specific achievement
   - Closes with clear value proposition for target role

RULE: You ONLY improve existing content. Never add technologies or experiences not in the input.
Return the COMPLETE resume — all sections, all entries.

Output JSON with:
- "enhanced_resume": complete improved resume (same JSON structure, ALL sections)
- "quality_issues": [{section, issue, severity: high|medium|low, fixed: bool}]"""


WEAK_VERBS = {
    "did", "worked", "helped", "assisted", "was responsible", "handled",
    "participated", "involved", "supported", "contributed", "used", "utilized",
    "made", "got", "had", "did work", "was part of",
}

STRONG_VERB_MAP = {
    "worked on": "Developed",
    "helped build": "Co-developed",
    "assisted with": "Supported the development of",
    "was responsible for": "Owned",
    "used python": "Engineered solutions using Python",
    "made an api": "Built a RESTful API",
    "created website": "Developed a responsive web application",
}

TECH_CAPITALIZATIONS = {
    "python": "Python", "javascript": "JavaScript", "typescript": "TypeScript",
    "postgresql": "PostgreSQL", "mongodb": "MongoDB", "mysql": "MySQL",
    "github": "GitHub", "gitlab": "GitLab", "aws": "AWS", "gcp": "GCP",
    "docker": "Docker", "kubernetes": "Kubernetes", "react": "React",
    "nextjs": "Next.js", "nodejs": "Node.js", "fastapi": "FastAPI",
    "django": "Django", "flask": "Flask", "tensorflow": "TensorFlow",
    "pytorch": "PyTorch", "scikit-learn": "scikit-learn", "pandas": "Pandas",
    "numpy": "NumPy", "linux": "Linux", "git": "Git", "redis": "Redis",
}


def fix_capitalizations(text: str) -> str:
    result = text
    for wrong, correct in TECH_CAPITALIZATIONS.items():
        # Case-insensitive replacement of standalone tech names
        import re
        result = re.sub(
            rf"\b{re.escape(wrong)}\b", correct, result, flags=re.IGNORECASE
        )
    return result


async def run(state: AgentState) -> AgentState:
    """
    Agent 2 node function for LangGraph.
    Input: tailored_resume (from Agent 1, passed via parallel state)
    Output: enhanced_resume
    """
    settings = get_settings()
    session_id = state.get("session_id", "unknown")
    logger.info(f"[Agent 2 — Enhancer] Starting | session={session_id}")

    try:
        # PARALLEL EXECUTION NOTE: Agent 2 runs on the SAME state snapshot as Agent 1.
        # tailored_resume does NOT exist yet (Agent 1 hasn't finished).
        # Use parsed_resume as the authoritative input — merge_parallel_node resolves both.
        input_resume = state.get("parsed_resume") or state.get("tailored_resume") or {}
        if not isinstance(input_resume, dict):
            input_resume = {}
        if not input_resume:
            raise ValueError("No resume data available for enhancement")

        jd_text = state.get("job_description", "")
        template = state.get("selected_template", "ats_pro")
        role_key = infer_role(jd_text or " ".join(input_resume.get("skills", [])))
        ats_kw = get_ats_keywords(role_key)
        must_have = ats_kw.get("must_have", [])

        # Compact resume for LLM (don't send raw bytes or huge fields)
        resume_for_llm = {
            "contact": input_resume.get("contact", {}),
            "summary": input_resume.get("summary", ""),
            "skills": input_resume.get("skills", [])[:35],
            "experience": [
                {
                    "title": e.get("title", "") if isinstance(e, dict) else "",
                    "company": e.get("company", "") if isinstance(e, dict) else "",
                    "startDate": e.get("startDate", "") if isinstance(e, dict) else "",
                    "endDate": e.get("endDate", "") if isinstance(e, dict) else "",
                    "description": (e.get("description", "") if isinstance(e, dict) else str(e))[:600],
                }
                for e in input_resume.get("experience", [])[:8]
            ],
            "projects": [
                {
                    "name": p.get("name", "") if isinstance(p, dict) else "",
                    "description": (p.get("description", "") if isinstance(p, dict) else str(p))[:400],
                    "techStack": p.get("techStack", []) if isinstance(p, dict) else [],
                }
                for p in input_resume.get("projects", [])[:8]
            ],
            "education": input_resume.get("education", [])[:5],
            "certifications": input_resume.get("certifications", [])[:10],
            "achievements": input_resume.get("achievements", [])[:6],
            "openSource": input_resume.get("openSource", [])[:5],
            "volunteering": input_resume.get("volunteering", [])[:4],
        }

        user_prompt = f"""Polish and sharpen this resume. Apply aggressive quality improvements.

TEMPLATE: {template}
TARGET ROLE: {role_key}
MUST-HAVE KEYWORDS: {', '.join(must_have[:10])}

RESUME TO ENHANCE:
{json.dumps(resume_for_llm, indent=2)}

APPLY ALL OF THESE FIXES — be aggressive, not conservative:

1. POWER VERB UPGRADE: Scan every bullet. Replace ANY weak verb:
   "worked on" → "Developed" | "helped" → "Co-built" | "responsible for" → "Owned"
   "participated" → "Contributed to" | "used X to" → "Leveraged X to"
   "did" → specific strong verb based on context

2. METRIC INJECTION: Every bullet that lacks a number needs one:
   "built REST API" → "built 5-endpoint REST API supporting 3 client applications"
   "worked on database" → "optimized PostgreSQL queries reducing response time by 30%"
   "deployed application" → "deployed containerized app on AWS EC2 serving 200+ users"

3. CAPITALIZATIONS (fix every instance):
   github→GitHub, postgresql→PostgreSQL, javascript→JavaScript, react→React,
   nodejs→Node.js, python→Python, aws→AWS, docker→Docker, mongodb→MongoDB,
   typescript→TypeScript, fastapi→FastAPI, django→Django, flask→Flask, gcp→GCP

4. FIRST PERSON REMOVAL: "I built"→"Built", "I developed"→"Developed", "My project"→"Project"

5. DATE STANDARDIZATION: Every date must be "MMM YYYY" (Jan 2023, Aug 2025, Present)

6. FILLER WORD REMOVAL: Delete "basically", "various", "multiple", "etc.", "and more",
   "responsible for", "in charge of", "as part of my role"

7. KEYWORD INTEGRATION: Naturally embed these keywords if not already present and relevant:
   {', '.join(must_have[:8])}

8. SUMMARY: If the summary does not open with a strong role identity statement and include
   at least one specific achievement metric, rewrite it completely.

COMPLETENESS: Return ALL experience entries, ALL projects, ALL education.
Never drop any entry. Same JSON structure as input.

Return JSON:
- "enhanced_resume": complete polished resume (ALL sections)
- "quality_issues": [{{"section": "...", "issue": "...", "severity": "high|medium|low", "fixed": true|false}}]"""

        result = await gemini_json(
            api_key=settings.gemini_api_key,
            model_name=settings.llm_model_fast,   # lite model — fast language pass
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=4096,
            temperature=0.3,
            disable_thinking=True,
        )
        # Validate LLM returned proper resume (not error wrapper)
        if result.get("_parse_error") or not isinstance(result.get("enhanced_resume"), dict):
            logger.warning("[Agent 2] LLM returned invalid JSON — applying rule-based fixes only")
            enhanced_resume = _apply_rule_based_fixes(input_resume)
            quality_issues = []
        else:
            enhanced_resume = result.get("enhanced_resume", input_resume)
            quality_issues = result.get("quality_issues", [])
            # Preserve new sections that Agent 2 might not have returned (it focuses on text quality)
            for section in ["certifications", "achievements", "openSource", "publications", "volunteering", "languages"]:
                if not enhanced_resume.get(section) and input_resume.get(section):
                    enhanced_resume[section] = input_resume[section]
                enhanced_resume.setdefault(section, [])

        logger.info(
            f"[Agent 2 — Enhancer] Complete | session={session_id} "
            f"| issues_found={len(quality_issues)}"
        )

        health_map = dict(state.get("agent_health_map") or {})
        health_map[AGENT_ENHANCER] = HEALTH_OK
        return {
            "enhanced_resume": enhanced_resume,
            "quality_issues": quality_issues,
            "agent_health_map": health_map,
        }

    except Exception as exc:
        logger.error(f"[Agent 2 — Enhancer] FAILED: {exc}", exc_info=True)
        fallback = _apply_rule_based_fixes(
            state.get("parsed_resume") or state.get("tailored_resume") or {}
        )
        health_map = dict(state.get("agent_health_map") or {})
        health_map[AGENT_ENHANCER] = HEALTH_FAILED
        return {
            "enhanced_resume": fallback,
            "agent_health_map": health_map,
        }


def _apply_rule_based_fixes(resume: dict) -> dict:
    """
    Pure rule-based capitalization + weak verb fix.
    Used as fallback when LLM call fails.
    """
    import copy, re
    resume = copy.deepcopy(resume) if isinstance(resume, dict) else {}

    def fix_text(text: str) -> str:
        for wrong, correct in TECH_CAPITALIZATIONS.items():
            text = re.sub(rf"\b{re.escape(wrong)}\b", correct, text, flags=re.IGNORECASE)
        # Strip leading "I " from bullets
        text = re.sub(r'^I\s+', '', text, flags=re.MULTILINE)
        return text

    for exp in resume.get("experience", []):
        if isinstance(exp.get("description"), str):
            exp["description"] = fix_text(exp["description"])
    for proj in resume.get("projects", []):
        if isinstance(proj.get("description"), str):
            proj["description"] = fix_text(proj["description"])
    if isinstance(resume.get("summary"), str):
        resume["summary"] = fix_text(resume["summary"])
    return resume
