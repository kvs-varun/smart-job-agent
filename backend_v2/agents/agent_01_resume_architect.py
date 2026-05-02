"""
Agent 1 — Resume Architect Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Role: Elite ATS resume writer. Takes candidate's raw data and produces a
PROFESSIONALLY TRANSFORMED resume — dramatically better than the input.
Every bullet rewritten. Summary rebuilt. Skills prioritized.

Model: gemini-flash-latest (full reasoning for professional quality)
Runs: In PARALLEL with Agent 2 (Content Enhancer)
"""
import json
import logging
from typing import Any

from backend_v2.agents.tools.gemini_client import gemini_json

from backend_v2.agents.state import AgentState, AGENT_ARCHITECT, HEALTH_OK, HEALTH_FAILED
from backend_v2.agents.tools.kb_tools import infer_role, get_ats_keywords
from backend_v2.config import get_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the world's most aggressive resume transformation specialist — part senior recruiter,
part technical hiring manager, part personal branding strategist. You have reviewed 50,000+ resumes
and hired for companies ranging from TCS and Infosys to Razorpay, CRED, Google India, and Atlassian.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR PRIME DIRECTIVE: TRANSFORMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You do NOT reformat resumes. You do NOT copy-paste existing text.
You COMPLETELY REWRITE every single line from scratch.
The input is raw clay. Your output is a polished, professional masterpiece.

If you return ANY text that matches the original input word-for-word in a bullet, summary, or description — you have FAILED.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RECRUITER PSYCHOLOGY (6-SECOND SCAN)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Recruiters scan resumes in 6 seconds. In those 6 seconds they look for:
1. Job title match (does this person DO what we need?)
2. Company/institution credibility (project names, recognizable tech)
3. Numbers (metrics signal impact, not just effort)
4. Action verbs (signals ownership, not spectating)
5. Tech stack alignment (keywords matching JD)

Every word you write must serve one of these 5 signals.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BULLET REWRITING: THE STAR-IMPACT METHOD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Every bullet MUST follow this formula:
[Power Verb] + [What specifically you built/owned] + [With what technology] + [Scale or Impact or Result]

POWER VERBS ONLY (never use: worked, helped, did, was, assisted, participated, involved):
Built, Engineered, Architected, Designed, Developed, Implemented, Automated, Deployed,
Optimized, Reduced, Increased, Delivered, Led, Spearheaded, Launched, Shipped, Migrated,
Streamlined, Integrated, Scaled, Refactored, Secured, Mentored, Drove, Created, Established

QUANTIFICATION RULES:
- If resume says "multiple APIs" → write "5+ RESTful APIs"
- If resume says "improved performance" → write "reduced load time by 40%"
- If resume says "worked on team project" → write "collaborated in 4-person agile team"
- If resume says "deployed app" → write "deployed to production serving 200+ daily users"
- Use "3+ months", "8-week sprint", "50+ concurrent users", "99.8% uptime" where implied
- NEVER invent companies, degrees, or technologies not present in the input

TRANSFORMATION EXAMPLES (study these carefully):

❌ INPUT: "worked on GPS tracking app"
✅ OUTPUT: "Engineered real-time GPS tracking module using Flutter with persistent background
   execution, reducing location sync failures by 85% across unstable mobile networks"

❌ INPUT: "built a website for my college project"
✅ OUTPUT: "Developed full-stack college management portal using React and Node.js, enabling
   500+ students to access academic records and submit assignments through a single platform"

❌ INPUT: "helped with machine learning model for job matching"
✅ OUTPUT: "Built NLP-powered candidate-job matching engine using Python and scikit-learn,
   processing 50+ resume-JD pairs concurrently with 87% precision on held-out evaluation set"

❌ INPUT: "was responsible for backend"
✅ OUTPUT: "Architected RESTful backend API using FastAPI and PostgreSQL, handling 200+ daily
   active users with 99.8% uptime sustained across a 3-month production deployment"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUMMARY REWRITE: THE PITCH FORMULA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The summary is a SALES PITCH, not a job description of yourself.
Formula: [Seniority + Role Identity] with [Top Technical Strength]. [Best measurable achievement
from their actual work]. [Value proposition tailored to target role].

Example output:
"Results-driven Full Stack Developer with 2+ years of hands-on experience building production-grade
web and mobile applications using React, FastAPI, and Flutter. Delivered a GPS tracking platform
that reduced location sync failures by 85% and a job-matching engine achieving 87% NLP precision.
Seeking a backend engineering role where system design thinking and ownership culture drive impact."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SKILLS STRATEGY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Reorder skills: most relevant to TARGET ROLE come first
- Group logically: Languages → Frameworks → Databases → Tools/Cloud → Concepts
- Correct ALL capitalizations: python→Python, javascript→JavaScript, postgresql→PostgreSQL,
  github→GitHub, aws→AWS, react→React, nodejs→Node.js, fastapi→FastAPI, docker→Docker

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ATS ABSOLUTE RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. NEVER copy-paste original text — rewrite every line from scratch
2. NEVER fabricate experience, companies, schools, or certifications
3. You CAN quantify from context: "3+ projects", "5 APIs", "team of 4"
4. Dates in MMM YYYY format (e.g., "Jan 2023", "Aug 2024")
5. Every bullet starts with a capitalized Power Verb
6. No tables, no columns, no icons, no special characters in bullets
7. Return COMPLETE data — every experience, every project, every education entry

TEMPLATE SECTION ORDER:
- jakes: contact → education → skills → experience → projects
- harvard: contact → summary → education → experience → skills → projects
- ats_pro: contact → summary → skills → projects → experience → education

OUTPUT: Return ONLY valid JSON. Every line of output must be dramatically better than the input.
If you find yourself typing text from the input verbatim — STOP and rewrite it."""


async def run(state: AgentState) -> AgentState:
    """
    Agent 1 node function for LangGraph.
    Input: parsed_resume, job_description, selected_template, role_preference
    Output: tailored_resume, change_log
    """
    settings = get_settings()
    session_id = state.get("session_id", "unknown")
    logger.info(f"[Agent 1 — Architect] Starting | session={session_id}")

    try:
        parsed = state.get("parsed_resume") or {}
        if not isinstance(parsed, dict):
            parsed = {}

        # ── Defensive: ensure minimum usable structure ────────────────────────
        if not parsed.get("contact", {}).get("name") and not parsed.get("skills"):
            logger.warning("[Agent 1] parsed_resume is empty/minimal — attempting re-parse")
            raw_text = state.get("raw_resume_text", "")
            if raw_text:
                try:
                    from backend_v2.agents.tools.resume_tools import parse_resume_async
                    parsed = await parse_resume_async(raw_text) or parsed
                except Exception as exc:
                    logger.warning(f"[Agent 1] Re-parse failed: {exc}")
            if not parsed:
                parsed = {
                    "contact": {"name": "Candidate", "email": "", "phone": "",
                                "location": "", "linkedin": "", "github": "", "portfolio": "", "jobTitle": ""},
                    "summary": "", "skills": [], "experience": [], "projects": [], "education": [],
                    "certifications": [], "achievements": [], "openSource": [],
                    "publications": [], "volunteering": [], "languages": [],
                }

        jd_text = state.get("job_description", "")
        template = state.get("selected_template", "ats_pro")
        role_pref = state.get("role_preference", "")

        # ── Infer role and get ATS keywords ───────────────────────────────────
        skills_text = " ".join(str(s) for s in parsed.get("skills", []))
        role_key = role_pref or infer_role(jd_text or skills_text)
        ats_kw = get_ats_keywords(role_key)
        must_have = ats_kw.get("must_have", [])
        nice_to_have = ats_kw.get("nice_to_have", [])

        # ── Build rich context for LLM ────────────────────────────────────────
        contact = parsed.get("contact", {})
        name = contact.get("name", "Candidate")
        current_summary = parsed.get("summary", "")
        current_skills = parsed.get("skills", [])
        experience = parsed.get("experience", [])
        projects = parsed.get("projects", [])
        education = parsed.get("education", [])
        certifications = parsed.get("certifications", [])
        achievements = parsed.get("achievements", [])
        open_source = parsed.get("openSource", [])
        publications = parsed.get("publications", [])
        volunteering = parsed.get("volunteering", [])

        # Format experience for LLM context
        exp_context = []
        for exp in experience[:8]:
            if isinstance(exp, dict):
                exp_context.append(
                    f"  ROLE: {exp.get('title', 'N/A')} at {exp.get('company', 'N/A')} "
                    f"({exp.get('startDate', '')}–{exp.get('endDate', 'Present')})\n"
                    f"  CURRENT TEXT: {exp.get('description', '')[:500]}"
                )
            elif isinstance(exp, str):
                exp_context.append(f"  EXPERIENCE TEXT: {exp[:400]}")

        proj_context = []
        for proj in projects[:8]:
            if isinstance(proj, dict):
                tech = proj.get("techStack", [])
                tech_str = ", ".join(tech) if isinstance(tech, list) else str(tech)
                proj_context.append(
                    f"  PROJECT: {proj.get('name', 'N/A')}\n"
                    f"  TECH: {tech_str}\n"
                    f"  DESCRIPTION: {proj.get('description', '')[:400]}"
                )
            elif isinstance(proj, str):
                proj_context.append(f"  PROJECT TEXT: {proj[:300]}")

        edu_context = []
        for edu in education[:4]:
            if isinstance(edu, dict):
                edu_context.append(
                    f"  {edu.get('degree', '')} in {edu.get('field', '')} "
                    f"from {edu.get('institution', '')} | Grade: {edu.get('grade', '')} "
                    f"| {edu.get('startDate', '')}–{edu.get('endDate', '')}"
                )
            elif isinstance(edu, str):
                edu_context.append(f"  EDUCATION: {edu[:200]}")

        cert_context = []
        for cert in certifications[:10]:
            if isinstance(cert, dict):
                cert_context.append(
                    f"  {cert.get('name', '')} | {cert.get('issuer', '')} | {cert.get('issuedDate', '')}"
                )
            elif isinstance(cert, str):
                cert_context.append(f"  CERT: {cert}")

        ach_context = []
        for ach in achievements[:6]:
            if isinstance(ach, dict):
                ach_context.append(f"  {ach.get('title', '')} — {ach.get('description', '')} ({ach.get('date', '')})")
            elif isinstance(ach, str):
                ach_context.append(f"  {ach}")

        os_context = []
        for item in open_source[:5]:
            if isinstance(item, dict):
                os_context.append(f"  {item.get('project', '')} — {item.get('contribution', '')}")

        vol_context = []
        for vol in volunteering[:4]:
            if isinstance(vol, dict):
                vol_context.append(
                    f"  {vol.get('role', '')} at {vol.get('organization', '')} "
                    f"({vol.get('startDate', '')}–{vol.get('endDate', '')}): {vol.get('description', '')}"
                )

        user_prompt = f"""You are transforming {name}'s resume. This is NOT reformatting — it is a COMPLETE REWRITE.
Every bullet, every description, every summary line must be rewritten from scratch using the STAR-Impact method.
Think like a 30-year veteran recruiter who has hired for Google, Amazon, Razorpay, TCS, and Infosys.
Your output will be directly used in job applications — make it exceptional.

CANDIDATE: {name}
TARGET ROLE: {role_key}
TEMPLATE: {template}
MUST-HAVE KEYWORDS: {', '.join(must_have[:12])}
NICE-TO-HAVE: {', '.join(nice_to_have[:8])}
{f"JOB DESCRIPTION:{chr(10)}{jd_text[:800]}" if jd_text else ""}

════════════════════════════════════════════
RAW INPUT DATA — TRANSFORM EVERYTHING BELOW
════════════════════════════════════════════
⚠️ CRITICAL: Do NOT copy-paste ANY text from this section into the output.
Every line below is raw clay. Shape it into a masterpiece. Rewrite every word.

EXISTING SUMMARY (DO NOT USE THIS TEXT — it is provided only so you know what NOT to write):
<<< IGNORE: {(current_summary or "none")[:120]} >>>
Write a completely NEW summary below — zero words from above may appear in the output.

SKILLS ({len(current_skills)} raw — reorder by relevance, fix capitalizations):
{', '.join(str(s) for s in current_skills[:35])}

EXPERIENCE ({len(experience)} roles — rewrite EVERY bullet using Power Verb + What + Tech + Impact):
{chr(10).join(exp_context) or "(no experience — write strong bullets based on their tech stack context)"}

PROJECTS ({len(projects)} projects — rewrite EVERY description: problem → solution → scale):
{chr(10).join(proj_context) or "(no projects listed)"}

EDUCATION ({len(education)} entries — preserve facts, format properly):
{chr(10).join(edu_context) or "(no education listed)"}

CERTIFICATIONS ({len(certifications)} certs — preserve exactly, just clean formatting):
{chr(10).join(cert_context) or "(none — omit the certifications section if empty)"}

ACHIEVEMENTS & AWARDS ({len(achievements)} items):
{chr(10).join(ach_context) or "(none)"}

OPEN SOURCE CONTRIBUTIONS ({len(open_source)} items):
{chr(10).join(os_context) or "(none)"}

VOLUNTEERING ({len(volunteering)} items):
{chr(10).join(vol_context) or "(none)"}

════════════════════════════════════════════
30-YEAR RECRUITER TRANSFORMATION RULES
════════════════════════════════════════════

RULE 1 — SUMMARY (Most Important Section — WRITE FROM SCRATCH — 120-180 words):
The existing summary text shown above is FORBIDDEN from appearing in the output. Treat it as deleted.
Write a brand-new 5-sentence executive pitch using ONLY their actual skills, projects, and experience.

SENTENCE FORMULA:
• S1 — Role Identity: [Seniority/context] [role] with [X years / 'emerging' if fresher] background in [top 2-3 domains from their actual stack].
• S2 — Best Achievement: Name their strongest actual project — use the REAL project name + tech + realistic metric (e.g., "Engineered [Urban Traffic Optimization] using [ML + Scikit-learn], achieving [95% prediction accuracy] on [10K-sample] dataset").
• S3 — Second Achievement or Depth: Another project or a key technical capability they demonstrated.
• S4 — Breadth + Credibility: Their tech breadth (languages, frameworks) + one trust signal (cert, award, CGPA, hackathon, internship).
• S5 — Value Proposition: Forward-looking, JD-targeted, specific to {role_key}. Mirror JD language if provided.

TARGET LENGTH: 120–180 words. NOT 3 short sentences.
⚠️ "Passionate developer seeking opportunities" → REJECTED. Never write this.
⚠️ "Results-driven professional" → cliché, rejected.
GOOD EXAMPLE: "Emerging Data Scientist and BTech Computer Science graduate (2025) with hands-on expertise
in Python, Machine Learning, and NLP-driven systems. Engineered an Urban Traffic Optimization engine
using Scikit-learn and ensemble ML models, achieving 94% prediction accuracy across a 50K-record dataset
that reduced simulated traffic congestion by 30%. Developed a Keyword Extraction system using TF-IDF and
Python NLP pipelines, processing 1,000+ documents with 89% precision on unseen test data. Certified in
Web Development (Acadmor, 2023), Python AI (Google, 2025), and Sawit.AI Learnathon winner (GUVII, 2024),
demonstrating consistent upskilling across AI/ML domains. Seeking a data engineering or ML role at a
product company where model quality and data infrastructure drive real business outcomes."

RULE 2 — EXPERIENCE BULLETS:
Formula for EVERY single bullet: [Power Verb] + [Specific What] + [Using What Tech] + [Scale/Impact]
- Minimum 3 bullets per role, maximum 5
- Each bullet on its own line starting with •
- If the original says "worked on GPS app" → write "Engineered real-time GPS tracking system using Flutter with background execution, reducing location sync failures by 85%"
- If original has NO description → infer from job title + their tech stack what they likely did
- Every number is better than no number: "50+ users", "3 APIs", "8-week sprint", "team of 4"

RULE 3 — PROJECTS:
Each project = 2-3 rewritten bullets showing:
• What problem this solves and who benefits from it
• Key technical architecture decisions (not just "used React")
• Scale, impact, or complexity metric
Format: start description with "• " bullets

RULE 4 — CERTIFICATIONS:
Keep factual info (name, issuer, date) exactly as provided.
Do NOT rewrite cert names. Just ensure clean formatting.
Include all certifications provided — they are significant trust signals.

RULE 5 — ACHIEVEMENTS:
If candidate has hackathon wins, scholarships, dean's list, published papers → include them.
These are GOLD for differentiating candidates. Rewrite to maximize impact.

RULE 6 — SKILLS STRATEGY:
Order: Primary Language → Secondary Languages → Core Frameworks → Databases → Cloud/DevOps → Tools → Concepts
Fix every capitalization: python→Python, javascript→JavaScript, aws→AWS, react→React, etc.
Include ALL skills from the input — never drop any.

RULE 7 — COMPLETENESS:
Return ALL {len(experience)} experience entries. ALL {len(projects)} projects. ALL {len(education)} education entries.
Include certifications section only if certs exist.
Include achievements section only if achievements exist.
Include open source section only if open source contributions exist.

Return ONLY this JSON (complete, every section, no truncation):
{{
  "contact": {{
    "name": "{name}",
    "email": "{contact.get('email', '')}",
    "phone": "{contact.get('phone', '')}",
    "location": "{contact.get('location', '')}",
    "linkedin": "{contact.get('linkedin', '')}",
    "github": "{contact.get('github', '')}",
    "portfolio": "{contact.get('portfolio', '')}",
    "jobTitle": "Best-fit job title for target role (e.g., Senior Full-Stack Engineer)"
  }},
  "summary": "YOUR ORIGINAL COMPOSITION — zero words from existing summary. 5 sentences, 120-180 words: (1) Role identity + domains, (2) Best project name + tech + metric, (3) Second project or technical depth, (4) Breadth + one trust signal (cert/award/CGPA), (5) Value proposition for {role_key}.",
  "skills": ["Python", "React", "...all skills sorted by relevance..."],
  "experience": [
    {{
      "title": "Job Title",
      "company": "Company Name",
      "location": "City or Remote",
      "startDate": "MMM YYYY",
      "endDate": "MMM YYYY or Present",
      "description": "• Power Verb + What + Tech + Impact\\n• Power Verb + What + Tech + Impact\\n• Power Verb + What + Tech + Impact"
    }}
  ],
  "projects": [
    {{
      "name": "Project Name",
      "description": "• What problem it solves + who uses it\\n• Key technical choice + why\\n• Scale or impact metric",
      "techStack": ["Tech1", "Tech2", "Tech3"],
      "github": "github url if present",
      "demo": "demo url if present"
    }}
  ],
  "certifications": [
    {{
      "name": "Exact certification name",
      "issuer": "Issuing organization",
      "issuedDate": "MMM YYYY",
      "expiryDate": "MMM YYYY or empty",
      "credentialID": "ID if present",
      "credentialURL": "URL if present"
    }}
  ],
  "education": [
    {{
      "institution": "University Name",
      "degree": "B.Tech",
      "field": "Computer Science",
      "grade": "CGPA: X.X / 10.0",
      "startDate": "MMM YYYY",
      "endDate": "MMM YYYY"
    }}
  ],
  "achievements": [
    {{
      "title": "Achievement title",
      "description": "Rewritten impact statement",
      "date": "MMM YYYY"
    }}
  ],
  "openSource": [
    {{
      "project": "Project name",
      "contribution": "Rewritten contribution description with impact",
      "github": "URL if present"
    }}
  ],
  "volunteering": [
    {{
      "role": "Role",
      "organization": "Organization",
      "description": "Rewritten description",
      "startDate": "MMM YYYY",
      "endDate": "MMM YYYY or Present"
    }}
  ]
}}"""

        llm_result = await gemini_json(
            api_key=settings.gemini_api_key,
            model_name=settings.llm_model_fast,   # lite model — much faster JSON generation
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=4096,
            temperature=0.6,
            disable_thinking=True,
        )

        # Validate LLM returned a proper resume dict
        if llm_result.get("_parse_error") or not isinstance(llm_result.get("contact"), dict):
            logger.warning("[Agent 1] LLM returned invalid JSON — using parsed_resume as fallback")
            enhanced_resume = parsed
        else:
            enhanced_resume = llm_result
            # Preserve contact info that LLM might have lost
            if enhanced_resume.get("contact"):
                for field in ["email", "phone", "linkedin", "github", "location", "portfolio"]:
                    if not enhanced_resume["contact"].get(field) and contact.get(field):
                        enhanced_resume["contact"][field] = contact[field]
            # Preserve new sections from parsed if LLM omitted them
            for section in ["certifications", "achievements", "openSource", "publications", "volunteering", "languages"]:
                if not enhanced_resume.get(section) and parsed.get(section):
                    enhanced_resume[section] = parsed[section]
            # Ensure all new sections exist (at least as empty lists)
            for section in ["certifications", "achievements", "openSource", "publications", "volunteering", "languages"]:
                enhanced_resume.setdefault(section, [])

        logger.info(
            f"[Agent 1 — Architect] Complete | session={session_id} | template={template} | "
            f"skills={len(enhanced_resume.get('skills', []))} | "
            f"exp={len(enhanced_resume.get('experience', []))} | "
            f"proj={len(enhanced_resume.get('projects', []))} | "
            f"certs={len(enhanced_resume.get('certifications', []))}"
        )

        change_log = [{
            "agent": AGENT_ARCHITECT,
            "action": "full_resume_transformation",
            "model": settings.llm_model_heavy,
            "template": template,
            "role_key": role_key,
            "bullets_rewritten": sum(
                len(str(e.get("description", "")).split("\\n"))
                for e in enhanced_resume.get("experience", [])
                if isinstance(e, dict)
            ),
        }]

        health_map = dict(state.get("agent_health_map") or {})
        health_map[AGENT_ARCHITECT] = HEALTH_OK
        return {
            "tailored_resume": enhanced_resume,
            "change_log": change_log,
            "agent_health_map": health_map,
        }

    except Exception as exc:
        logger.error(f"[Agent 1 — Architect] FAILED: {exc}", exc_info=True)
        health_map = dict(state.get("agent_health_map") or {})
        health_map[AGENT_ARCHITECT] = HEALTH_FAILED
        return {
            "error": f"Agent 1 failed: {exc}",
            "tailored_resume": state.get("parsed_resume"),
            "agent_health_map": health_map,
        }
