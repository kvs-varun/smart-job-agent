export type ResumeContact = {
  email?: string | null;
  phone?: string | null;
  location?: string | null;
  linkedinUrl?: string | null;
  githubUrl?: string | null;
  portfolioUrl?: string | null;
};

export type ResumeData = {
  name?: string | null;
  title?: string | null;
  contact?: ResumeContact;
  summary: string;
  skills: string[];
  projects: string[];
  education: string[];
  experience: string[];
  familiarity_exposure?: string[];
};

export type PreviewResponse = {
  message: string;
  resume_preview: {
    name?: string | null;
    contact?: ResumeContact;
    summary?: string;
    skills?: string[];
    projects?: string[];
    education?: string[];
    experience?: string[];
    familiarity_exposure?: string[] | null;
    parse_warnings?: string[];
  };
  analysis: {
    role_key?: string;
    role_confidence?: number;
    job_analysis?: {
      role_key?: string;
      job_skills?: string[];
      priority_skills?: string[];
      experience_req?: string | null;
    };
    scores?: {
      match_percentage?: number;
      ats_alignment_score?: number;
      matched_skills?: string[];
      missing_skills?: string[];
      recommendations?: string[];
    };
    quality_gate?: {
      passed?: boolean;
      ats_gate_score?: number;
      keyword_coverage?: number;
      issues?: string[];
      suggestions?: string[];
    };
    parse_warnings?: string[];
  };
};

export type FinalizeResponse = {
  message: string;
  download_url: string;
  pdf_path?: string;
  quality_gate?: {
    passed?: boolean;
    ats_gate_score?: number;
    keyword_coverage?: number;
    issues?: string[];
    suggestions?: string[];
  };
};
