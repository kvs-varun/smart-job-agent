def extract_skills(text):
    """
    Extract skills from text using a simple rule-based approach.
    """
    known_skills = [
        "python",
        "flutter",
        "firebase",
        "sql",
        "rest",
        "flask",
        "react",
        "docker",
        "aws"
    ]

    text = text.lower()
    found_skills = []

    for skill in known_skills:
        if skill in text:
            found_skills.append(skill)

    return found_skills


def analyze_match(resume_text, job_text):
    """
    Compare resume and job description and calculate match details.
    """

    resume_skills = extract_skills(resume_text)
    job_skills = extract_skills(job_text)

    matched_skills = list(set(resume_skills) & set(job_skills))
    missing_skills = list(set(job_skills) - set(resume_skills))

    if len(job_skills) == 0:
        match_percentage = 0
    else:
        match_percentage = int((len(matched_skills) / len(job_skills)) * 100)

    return {
        "resume_skills": resume_skills,
        "job_skills": job_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "match_percentage": match_percentage
    }


def generate_resume_actions(analysis_result):
    """
    Decide how the resume should be improved based on analysis.
    """

    matched = analysis_result.get("matched_skills", [])
    missing = analysis_result.get("missing_skills", [])
    match_percentage = analysis_result.get("match_percentage", 0)

    actions = []

    if match_percentage < 40:
        actions.append(
            "Low match score. Resume needs significant tailoring for this role."
        )
    elif match_percentage < 70:
        actions.append(
            "Moderate match. Resume can be improved by emphasizing relevant skills."
        )
    else:
        actions.append(
            "Good match. Resume is already well aligned with the job."
        )

    if matched:
        actions.append(
            f"Highlight these skills more prominently: {', '.join(matched)}"
        )

    if missing:
        actions.append(
            f"Consider adding or learning these skills: {', '.join(missing)}"
        )

    return actions
