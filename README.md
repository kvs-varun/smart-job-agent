# smart-job-agent
AI-powered agent to analyze resumes against job descriptions and suggest improvements

## What this project does

`smart-job-agent` is a **personal-use** AI-assisted backend that helps an Indian IT fresher:

- **Analyze** a job description against a resume
- **Identify** matched and missing skills + a match percentage
- **Tailor** the resume content ethically (no fake claims)
- **Generate** a one-page, ATS-friendly **PDF resume** (single-column, no tables/images)

This project is designed to be **portfolio-worthy** and **interview-explainable**: it uses simple, modular, rule-based logic (no hype, no illegal automation).

## Safety, ethics, and feasibility

- **No credential harvesting**
- **No CAPTCHA bypass**
- **No mass auto-apply**
- **No promises of “100% ATS pass”**

The tailoring is intentionally conservative:

- Missing skills are only included as **“Learning exposure / currently upskilling”**
- The system avoids skill inflation and encourages honest representation

## Backend architecture (Flask + modular Python)

The backend lives in `backend/`.

- `backend/app.py`
  - Flask app
  - Existing endpoint: `POST /agent/observe`
  - New endpoint: `POST /agent/generate-resume`

- `backend/agent_reasoner.py`
  - `extract_skills(text)`
  - `analyze_match(resume_text, job_text)`
  - `generate_resume_actions(analysis_result)`

- `backend/resume_parser.py`
  - `parse_resume_text(resume_text)`
  - Converts raw resume text to structured JSON with sections:
    - `summary`, `skills`, `projects`, `education`, `experience`

- `backend/resume_tailor.py`
  - `tailor_resume(structured_resume, analysis_result)`
  - Reorders skills to highlight matched ones
  - Adds missing skills only as “learning exposure”

- `backend/ats_resume_generator.py`
  - `generate_ats_pdf(tailored_resume, output_dir, ...)`
  - Produces ATS-friendly PDF via `reportlab`
  - Single-column, no images, no tables

- `backend/agent_controller.py`
  - `run_agent_pipeline(resume_text, job_description, output_dir)`
  - Orchestrates parsing -> analysis -> tailoring -> PDF generation

## API

### 1) Analyze only

`POST /agent/observe`

Request JSON:

```json
{
  "resumeText": "...",
  "jobDescription": "..."
}
```

Response JSON (example shape):

```json
{
  "message": "Agent analysis complete",
  "analysis": {
    "matched_skills": [],
    "missing_skills": [],
    "match_percentage": 0
  },
  "recommended_actions": []
}
```

### 2) Generate tailored ATS PDF

`POST /agent/generate-resume`

Request JSON:

```json
{
  "resumeText": "...",
  "jobDescription": "..."
}
```

Response JSON:

```json
{
  "message": "ATS resume generated",
  "match_percentage": 65,
  "missing_skills": ["docker"],
  "recommended_actions": ["..."],
  "pdf_path": "D:/smart-job-agent/backend/generated/ats_resume_candidate_20260226_123000.pdf"
}
```

## Setup (Windows)

1) Create a virtual environment

```bash
python -m venv .venv
.venv\\Scripts\\activate
```

2) Install dependencies

```bash
pip install -r requirements.txt
```

3) Run the backend

```bash
python backend/app.py
```

### Common PowerShell mistakes (quick fixes)

- If you typed `install flask reportlab`, use `pip install ...` instead.
- If your terminal is already inside `backend/`, run:

```bash
python app.py
```

The server runs on `http://127.0.0.1:5000`.

## How it helps in the Indian fresher market

- Emphasizes **projects**, **internships**, and **skill keywords** commonly screened on Naukri/LinkedIn-style ATS
- Keeps formatting ATS-friendly for PDF parsing
- Encourages targeted upskilling (missing skills list) without claiming experience

## How to explain in interviews

- **Problem**: Freshers struggle to map JD keywords to their actual project experience.
- **Approach**: A pipeline that parses resume text into sections, compares skill overlap, and generates an ATS-friendly PDF.
- **Key design choice**: Tailoring is **ethical** and **auditable** (simple rules, explicit “learning exposure”).
- **Tradeoffs**: Rule-based parsing is transparent but not perfect; can be improved with better section detection and a broader skill taxonomy.
