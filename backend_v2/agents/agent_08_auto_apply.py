"""
Agent 8 — Auto-Apply Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━
Role: Fully automated job application engine. Searches LinkedIn and Naukri for
matching jobs, filters by relevance (>= 70% match), tailors resume per JD, and
submits applications via Playwright browser automation.

ACTIVATION GATE: Only runs if resume_score >= apply_score_threshold (default 7.0/10)

Model: claude-haiku-4-5 (routing decisions; Playwright does the actual application)
"""
import asyncio
import logging
from typing import Any
from pathlib import Path

from backend_v2.agents.state import AgentState, AGENT_AUTO_APPLY, HEALTH_OK, HEALTH_FAILED
from backend_v2.config import get_settings

logger = logging.getLogger(__name__)

MIN_MATCH_SCORE = 0.70        # 70% match required to apply
MAX_APPLICATIONS_PER_RUN = 10 # safety cap per session
SCREENSHOTS_DIR = Path("backend_v2/screenshots")


async def run(state: AgentState) -> AgentState:
    """
    Agent 8 node function.
    Input: final_resume, auto_apply_preferences, resume_score
    Output: auto_apply_results[]
    """
    settings = get_settings()
    session_id = state.get("session_id", "unknown")

    # ── Activation gate ───────────────────────────────────────────────────────
    if not state.get("auto_apply_enabled", False):
        logger.info(f"[Agent 8 — Auto-Apply] Skipped — not enabled | session={session_id}")
        return {**state, "current_agent": AGENT_AUTO_APPLY}

    resume_score = state.get("resume_score") or 0
    threshold = state.get("apply_score_threshold", settings.apply_score_threshold)

    if resume_score < threshold:
        logger.info(
            f"[Agent 8 — Auto-Apply] Gate blocked — score {resume_score:.1f} < {threshold} | session={session_id}"
        )
        return {
            **state,
            "auto_apply_results": [{
                "status": "blocked",
                "reason": f"Resume score {resume_score:.1f}/10 below threshold {threshold}/10. "
                          f"Improve your resume to score ≥ {threshold} to unlock auto-apply.",
                "score": resume_score,
                "threshold": threshold,
            }],
            "current_agent": AGENT_AUTO_APPLY,
            "agent_health_map": {**state.get("agent_health_map", {}), AGENT_AUTO_APPLY: HEALTH_OK},
        }

    logger.info(f"[Agent 8 — Auto-Apply] Starting | session={session_id} | score={resume_score:.1f}")

    try:
        prefs = state.get("auto_apply_preferences") or {}
        resume = state.get("final_resume") or state.get("parsed_resume", {})
        contact = resume.get("contact", {})

        platforms = prefs.get("platforms", ["linkedin", "naukri"])
        keywords = _extract_search_keywords(resume, prefs)
        location = prefs.get("location", "India")
        max_apps = min(prefs.get("max_applications", 5), MAX_APPLICATIONS_PER_RUN)

        results = []
        applied_count = 0

        for platform in platforms:
            if applied_count >= max_apps:
                break

            # ── Search ────────────────────────────────────────────────────────
            jobs = await _search_jobs(platform, keywords, location, settings)

            # ── Filter by match score ─────────────────────────────────────────
            filtered = await _filter_jobs(jobs, resume, max_apps - applied_count)

            logger.info(
                f"[Agent 8] Platform={platform} | found={len(jobs)} | filtered={len(filtered)}"
            )

            # ── Apply ─────────────────────────────────────────────────────────
            for job in filtered:
                result = await _apply_to_job(platform, job, resume, contact, settings)
                results.append(result)
                applied_count += 1

                # Log to database
                await _log_application(session_id, resume, job, result, platform)

                if applied_count >= max_apps:
                    break

                # Polite delay between applications to avoid rate limiting
                await asyncio.sleep(3)

        logger.info(
            f"[Agent 8 — Auto-Apply] Complete | session={session_id} "
            f"| applied={applied_count} | results={len(results)}"
        )

        return {
            **state,
            "auto_apply_results": results,
            "current_agent": AGENT_AUTO_APPLY,
            "agent_health_map": {
                **state.get("agent_health_map", {}),
                AGENT_AUTO_APPLY: HEALTH_OK,
            },
        }

    except Exception as exc:
        logger.error(f"[Agent 8 — Auto-Apply] FAILED: {exc}")
        return {
            **state,
            "auto_apply_results": [{"status": "failed", "error": str(exc)}],
            "current_agent": AGENT_AUTO_APPLY,
            "agent_health_map": {
                **state.get("agent_health_map", {}),
                AGENT_AUTO_APPLY: HEALTH_FAILED,
            },
        }


async def _search_jobs(
    platform: str, keywords: list[str], location: str, settings
) -> list[dict[str, Any]]:
    """Search for jobs on LinkedIn or Naukri using Playwright."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("[Agent 8] Playwright not installed — using mock results")
        return []

    jobs = []
    search_query = " ".join(keywords[:3])

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        try:
            if platform == "linkedin":
                jobs = await _scrape_linkedin(page, search_query, location, settings)
            elif platform == "naukri":
                jobs = await _scrape_naukri(page, search_query, location)
        except Exception as exc:
            logger.error(f"[Agent 8] Search failed on {platform}: {exc}")
        finally:
            await browser.close()

    return jobs


async def _scrape_linkedin(page, query: str, location: str, settings) -> list[dict]:
    """Scrape LinkedIn job listings (Easy Apply only)."""
    jobs = []
    try:
        # Login to LinkedIn
        await page.goto("https://www.linkedin.com/login")
        await page.fill("#username", settings.linkedin_email)
        await page.fill("#password", settings.linkedin_password)
        await page.click('[type="submit"]')
        await page.wait_for_timeout(3000)

        # Search for jobs with Easy Apply filter
        search_url = (
            f"https://www.linkedin.com/jobs/search/?keywords={query.replace(' ', '%20')}"
            f"&location={location.replace(' ', '%20')}&f_AL=true&f_E=1,2"  # f_AL=Easy Apply, f_E=Entry level
        )
        await page.goto(search_url)
        await page.wait_for_timeout(2000)

        job_cards = await page.query_selector_all(".job-card-container")
        for card in job_cards[:20]:
            try:
                title = await card.query_selector(".job-card-list__title")
                company = await card.query_selector(".job-card-container__company-name")
                link = await card.query_selector("a.job-card-container__link")

                if title and company and link:
                    jobs.append({
                        "title": await title.inner_text(),
                        "company": await company.inner_text(),
                        "url": await link.get_attribute("href"),
                        "platform": "linkedin",
                        "easy_apply": True,
                    })
            except Exception:
                continue
    except Exception as exc:
        logger.error(f"[Agent 8] LinkedIn scrape error: {exc}")

    return jobs


async def _scrape_naukri(page, query: str, location: str) -> list[dict]:
    """Scrape Naukri.com job listings."""
    jobs = []
    try:
        search_url = (
            f"https://www.naukri.com/{query.replace(' ', '-')}-jobs-in-{location.lower().replace(' ', '-')}"
            f"?experience=0"
        )
        await page.goto(search_url)
        await page.wait_for_timeout(2000)

        job_cards = await page.query_selector_all(".jobTuple")
        for card in job_cards[:20]:
            try:
                title = await card.query_selector(".title")
                company = await card.query_selector(".subTitle")
                link = await card.query_selector("a.title")

                if title and company and link:
                    jobs.append({
                        "title": await title.inner_text(),
                        "company": await company.inner_text(),
                        "url": await link.get_attribute("href"),
                        "platform": "naukri",
                        "easy_apply": True,
                    })
            except Exception:
                continue
    except Exception as exc:
        logger.error(f"[Agent 8] Naukri scrape error: {exc}")

    return jobs


async def _filter_jobs(
    jobs: list[dict], resume: dict, max_count: int
) -> list[dict]:
    """Filter jobs by match score. Only apply to jobs with >= 70% match."""
    if not jobs:
        return []

    from backend_v2.agents.tools.resume_tools import analyze_job_async, compute_match_scores_async
    from backend_v2.agents.tools.kb_tools import infer_role

    scored_jobs = []
    for job in jobs:
        try:
            jd_text = job.get("description", job.get("title", ""))
            role_key = infer_role(jd_text)
            job_analysis = await analyze_job_async(jd_text, role_key)
            scores = await compute_match_scores_async(resume, job_analysis)
            match = scores.get("overall_score", 0)
            if match >= MIN_MATCH_SCORE:
                job["match_score"] = match
                scored_jobs.append(job)
        except Exception:
            continue

    # Sort by match score, take top N
    scored_jobs.sort(key=lambda j: j.get("match_score", 0), reverse=True)
    return scored_jobs[:max_count]


async def _apply_to_job(
    platform: str, job: dict, resume: dict, contact: dict, settings
) -> dict[str, Any]:
    """Apply to a single job using Playwright. Returns result dict."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {"job": job, "status": "skipped", "reason": "playwright_not_installed"}

    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            if platform == "linkedin":
                success = await _apply_linkedin_easy_apply(page, job["url"], resume, contact, settings)
            else:
                success = await _apply_naukri_quick_apply(page, job["url"], resume, contact, settings)

            return {
                "job_title": job.get("title"),
                "company": job.get("company"),
                "url": job.get("url"),
                "platform": platform,
                "match_score": job.get("match_score", 0),
                "status": "submitted" if success else "failed",
            }

        except Exception as exc:
            screenshot_path = str(SCREENSHOTS_DIR / f"error_{platform}_{int(asyncio.get_event_loop().time())}.png")
            try:
                await page.screenshot(path=screenshot_path)
            except Exception:
                screenshot_path = None

            return {
                "job_title": job.get("title"),
                "company": job.get("company"),
                "url": job.get("url"),
                "platform": platform,
                "status": "failed",
                "error": str(exc),
                "screenshot_path": screenshot_path,
            }
        finally:
            await browser.close()


async def _apply_linkedin_easy_apply(page, job_url: str, resume: dict, contact: dict, settings) -> bool:
    """Submit LinkedIn Easy Apply."""
    await page.goto("https://www.linkedin.com/login")
    await page.fill("#username", settings.linkedin_email)
    await page.fill("#password", settings.linkedin_password)
    await page.click('[type="submit"]')
    await page.wait_for_timeout(3000)

    await page.goto(job_url)
    await page.wait_for_timeout(2000)

    # Click Easy Apply button
    easy_apply_btn = await page.query_selector(".jobs-apply-button")
    if not easy_apply_btn:
        return False

    await easy_apply_btn.click()
    await page.wait_for_timeout(1500)

    # Fill contact info if prompted
    phone_field = await page.query_selector('input[id*="phoneNumber"]')
    if phone_field:
        await phone_field.fill(contact.get("phone", ""))

    # Navigate through Easy Apply steps
    for _ in range(5):
        next_btn = await page.query_selector('[aria-label="Continue to next step"]')
        submit_btn = await page.query_selector('[aria-label="Submit application"]')

        if submit_btn:
            await submit_btn.click()
            await page.wait_for_timeout(2000)
            return True
        elif next_btn:
            await next_btn.click()
            await page.wait_for_timeout(1500)
        else:
            break

    return False


async def _apply_naukri_quick_apply(page, job_url: str, resume: dict, contact: dict, settings) -> bool:
    """Submit Naukri Quick Apply."""
    await page.goto(job_url)
    await page.wait_for_timeout(2000)

    apply_btn = await page.query_selector(".apply-button")
    if not apply_btn:
        return False

    await apply_btn.click()
    await page.wait_for_timeout(2000)

    # Naukri requires login for application
    email_field = await page.query_selector("#usernameField")
    if email_field:
        await email_field.fill(settings.naukri_email)
        password_field = await page.query_selector("#passwordField")
        if password_field:
            await password_field.fill(settings.naukri_password)
            login_btn = await page.query_selector("[data-ga-track='Login-Button']")
            if login_btn:
                await login_btn.click()
                await page.wait_for_timeout(2000)

    # Submit if apply button still present after login
    submit_btn = await page.query_selector(".chatbot_drawer .apply-button")
    if submit_btn:
        await submit_btn.click()
        await page.wait_for_timeout(2000)
        return True

    return False


def _extract_search_keywords(resume: dict, prefs: dict) -> list[str]:
    """Extract the best job search keywords from resume and preferences."""
    keywords = []

    # Use preferred roles if specified
    target_roles = prefs.get("target_roles", [])
    if target_roles:
        keywords.extend(target_roles[:2])

    # Fall back to job title from contact
    contact = resume.get("contact", {})
    if contact.get("jobTitle"):
        keywords.append(contact["jobTitle"])

    # Add top skills
    skills = resume.get("skills", [])
    if isinstance(skills, list):
        keywords.extend(str(s) for s in skills[:3])

    return list(dict.fromkeys(keywords))[:4]  # dedupe, max 4


async def _log_application(
    session_id: str, resume: dict, job: dict, result: dict, platform: str
):
    """Persist auto-apply result to PostgreSQL."""
    try:
        from backend_v2.database import get_connection
        import json
        async with get_connection() as conn:
            await conn.execute("""
                INSERT INTO auto_apply_log
                (session_id, platform, job_title, company, job_url, match_score, status, error_detail, screenshot_path)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
                session_id, platform,
                job.get("title"), job.get("company"), job.get("url"),
                job.get("match_score", 0),
                result.get("status", "unknown"),
                result.get("error"),
                result.get("screenshot_path"),
            )

            # Also add to applications tracker if submitted
            if result.get("status") == "submitted":
                await conn.execute("""
                    INSERT INTO applications (session_id, company, role, job_url, status, source)
                    VALUES ($1, $2, $3, $4, 'applied', 'auto_apply')
                """, session_id, job.get("company", ""), job.get("title", ""), job.get("url", ""))

    except Exception as exc:
        logger.error(f"[Agent 8] Failed to log application: {exc}")
