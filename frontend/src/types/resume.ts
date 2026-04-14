export const makeId = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;

export interface ContactInfo {
  name: string;
  jobTitle: string;
  email: string;
  phone: string;
  location: string;
  linkedin: string;
  github: string;
  portfolio: string;
}

export interface ExperienceEntry {
  id: string;
  title: string;
  company: string;
  startDate: string;
  endDate: string;
  current: boolean;
  location: string;
  description: string;
}

export interface EducationEntry {
  id: string;
  degree: string;
  institution: string;
  field: string;
  startYear: string;
  endYear: string;
  grade: string;
}

export interface ProjectEntry {
  id: string;
  name: string;
  description: string;
  techStack: string[];
  github: string;
  demo: string;
}

export interface ResumeData {
  contact: ContactInfo;
  summary: string;
  experience: ExperienceEntry[];
  education: EducationEntry[];
  skills: string[];
  projects: ProjectEntry[];
}

export const EMPTY_CONTACT: ContactInfo = {
  name: "",
  jobTitle: "",
  email: "",
  phone: "",
  location: "",
  linkedin: "",
  github: "",
  portfolio: "",
};

export const EMPTY_RESUME: ResumeData = {
  contact: { ...EMPTY_CONTACT },
  summary: "",
  experience: [],
  education: [],
  skills: [],
  projects: [],
};

export type PreviewResponse = {
  message: string;
  resume_preview: {
    name?: string | null;
    contact?: {
      email?: string | null;
      phone?: string | null;
      location?: string | null;
      linkedinUrl?: string | null;
      githubUrl?: string | null;
      portfolioUrl?: string | null;
    };
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
