import express from "express";

const router = express.Router();

/**
 * Agent Observation Endpoint
 * Accepts resume and job description text
 */
router.post("/observe", (req, res) => {
  const { resumeText, jobDescription } = req.body;

  if (!resumeText || !jobDescription) {
    return res.status(400).json({
      error: "resumeText and jobDescription are required"
    });
  }

  return res.json({
    message: "Observation received",
    resumeLength: resumeText.length,
    jobDescriptionLength: jobDescription.length
  });
});

export default router;