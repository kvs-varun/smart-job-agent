# Smart Job Agent (Phase-2 Hard-Ship)

Knowledge-augmented, human-in-the-loop **ATS Resume + Outreach assistant** for the **Indian IT fresher market**.

This is built for:

- **Final-year engineering students**
- **Recent CS graduates**
- **Bootcamp/self-taught candidates**

Output:

- A **one-page, ATS-friendly PDF** resume (selectable text, no columns/tables/images)
- A constrained, recruiter-friendly **cold email** (≤150 words)
- A constrained **LinkedIn message** (≤300 characters)

## Ethics & Safety (non-negotiable)

- Do **not** fabricate experience, dates, companies, or metrics.
- Missing skills must appear only as **Familiarity/Exposure** with honest wording.
- No scraping job sites, no CAPTCHA bypass, no credential harvesting.

**Disclaimer:** This tool helps with formatting and ethical tailoring. It does **not** guarantee interviews or job offers.

## Product Flow (4 steps)

1. **Upload Resume**
   - Upload PDF/DOCX **or** paste resume text (mutually exclusive enforced)
   - Paste job description (required)
2. **Check Job Match (Preview)**
   - Parse resume → analyze job match → ATS simulator
   - Show match %, ATS alignment, matched/missing skills, quality gate
   - **No PDF generated yet**
3. **Fix & Approve (Human-in-the-loop)**
   - Edit summary, skills, project bullets
   - Add missing skills only as **Familiarity/Exposure**
4. **Download & Apply (Finalize)**
   - Quality gate re-check
   - Generate one-page PDF to `backend/static/generated/`
   - Download button becomes available

## Architecture (high level)

```
Browser UI (templates/index.html)
  |  Step 1-4 UX + edits + copy buttons
  v
Flask API (backend/app.py)
  |  preview endpoints (no PDF)
  |  finalize endpoint (PDF from approved JSON only)
  |  outreach endpoint (mailto + Gmail link)
  v
Agent Pipeline (backend/agent_pipeline.py)
  | parse -> KB role inference -> job match -> ATS simulator -> safe corrections
  v
PDF Generator (backend/ats_resume_generator.py)
  | reportlab deterministic PDF
  v
Static downloads (backend/static/generated/*.pdf)
```

## Key Endpoints

- **Preview from pasted text**
  - `POST /agent/preview-resume-text`
  - body: `{ "resumeText": "...", "jobDescription": "...", "role_preference": "auto" }`

- **Preview from upload**
  - `POST /agent/preview-resume-upload` (multipart)
  - fields: `resumeFile`, `jobDescription`

- **Finalize PDF from user-approved JSON (no rewriting)**
  - `POST /agent/finalize-resume`
  - body: `{ "approved_resume_json": {...}, "job_analysis": {...} }`
  - returns: `{ download_url, pdf_path, quality_gate }`

- **Generate outreach**
  - `POST /agent/generate-cold-email`
  - body: `{ jobDescription, companyName, roleTitle, candidateName, recruiterEmail? }`
  - returns: `{ outreach, mailto, gmail_url }`

- **Analytics (token-protected)**
  - `GET /analytics/summary`
  - header: `X-Analytics-Token: $SMART_JOB_AGENT_ANALYTICS_TOKEN`

## Environment Variables

- `SMART_JOB_AGENT_ANALYTICS_TOKEN` (optional)
  - Enables auth for `/analytics/summary`
- `LLM_API_KEY` (optional)
  - LLM is optional; the system works without it.
- `DOCX2PDF_AVAILABLE=true` (optional / future)

## Run Locally (Windows)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python backend\app.py
```

Open:

- `http://127.0.0.1:5000/`

## Verification

### Automated acceptance (server must be running)

```powershell
python scripts\verify_acceptance.py
```

This checks:

- preview returns analysis
- finalize returns `download_url`
- download returns a real PDF (`%PDF`)
- outreach returns `mailto` and `gmail_url`

### Tests

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_tests.ps1
```

## Analytics Events

Recorded locally to: `backend/data/events.json`

- `generate_attempt`
- `preview_success` (if added)
- `user_edit_accepted`
- `final_pdf_generated`
- `outreach_generated`
- `pdf_download`

## Monetization hook (stub)

`backend/billing_stub.py` provides placeholder endpoints:

- `GET /billing/plans`
- `POST /billing/checkout`

Integrate Stripe/Razorpay later; do not store card data.

## Legal

- `docs/terms.md`
- `docs/privacy.md`
