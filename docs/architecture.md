# Smart Job Agent – Architecture

## Goal

Analyze a candidate's resume against a job description and identify skill gaps.

## Agent Loop

1. Observe:
   - Resume text
   - Job description text
2. Reason:
   - Compare required skills vs existing skills
3. Decide:
   - What gaps matter most
4. Act:
   - Suggest learning actions
5. Remember:
   - Store past analyses and progress

## Current Status

- Backend server initialized
- Health endpoint verified
- Ready to ingest inputs
