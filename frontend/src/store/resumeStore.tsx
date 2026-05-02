"use client";

import { create } from "zustand";
import type {
  ContactInfo,
  EducationEntry,
  ExperienceEntry,
  ProjectEntry,
  CertificationEntry,
  AchievementEntry,
  OpenSourceEntry,
  PublicationEntry,
  VolunteeringEntry,
  LanguageEntry,
  ResumeData,
} from "@/types/resume";
import { EMPTY_RESUME, makeId } from "@/types/resume";

interface ResumeStore {
  resumeData: ResumeData;
  activeStep: number;
  completedSteps: number[];

  updateContact: (field: keyof ContactInfo, value: string) => void;
  setSummary: (summary: string) => void;

  addExperience: () => void;
  updateExperience: (id: string, field: keyof ExperienceEntry, value: any) => void;
  removeExperience: (id: string) => void;

  addEducation: () => void;
  updateEducation: (id: string, field: keyof EducationEntry, value: any) => void;
  removeEducation: (id: string) => void;

  addSkill: (skill: string) => void;
  removeSkill: (skill: string) => void;

  addProject: () => void;
  updateProject: (id: string, field: keyof ProjectEntry, value: any) => void;
  removeProject: (id: string) => void;

  addCertification: () => void;
  updateCertification: (id: string, field: keyof CertificationEntry, value: any) => void;
  removeCertification: (id: string) => void;

  addAchievement: () => void;
  updateAchievement: (id: string, field: keyof AchievementEntry, value: any) => void;
  removeAchievement: (id: string) => void;

  addOpenSource: () => void;
  updateOpenSource: (id: string, field: keyof OpenSourceEntry, value: any) => void;
  removeOpenSource: (id: string) => void;

  addVolunteering: () => void;
  updateVolunteering: (id: string, field: keyof VolunteeringEntry, value: any) => void;
  removeVolunteering: (id: string) => void;

  addLanguage: () => void;
  updateLanguage: (id: string, field: keyof LanguageEntry, value: any) => void;
  removeLanguage: (id: string) => void;

  importResumeData: (data: Partial<ResumeData>) => void;
  resetResume: () => void;

  setActiveStep: (step: number) => void;
  markStepComplete: (step: number) => void;
}

function migrateOldFormat(old: any): ResumeData {
  return {
    contact: {
      name: old?.name || "",
      jobTitle: old?.jobTitle || old?.targetRole || old?.title || "",
      email: old?.contact?.email || old?.email || "",
      phone: old?.contact?.phone || old?.phone || "",
      location: old?.contact?.location || old?.location || "",
      linkedin: old?.contact?.linkedinUrl || old?.linkedin || "",
      github: old?.contact?.githubUrl || old?.github || "",
      portfolio: old?.contact?.portfolioUrl || old?.portfolio || "",
    },
    summary: old?.summary || "",
    experience: Array.isArray(old?.experience)
      ? old.experience.map((e: any) =>
          typeof e === "string"
            ? { id: makeId(), title: "", company: "", startDate: "", endDate: "", current: false, location: "", description: e }
            : { id: e?.id || makeId(), title: e?.title || "", company: e?.company || "", startDate: e?.startDate || "", endDate: e?.endDate || "", current: !!e?.current, location: e?.location || "", description: e?.description || "" }
        )
      : [],
    education: Array.isArray(old?.education)
      ? old.education.map((e: any) =>
          typeof e === "string"
            ? { id: makeId(), degree: e, institution: "", field: "", startYear: "", endYear: "", grade: "" }
            : { id: e?.id || makeId(), degree: e?.degree || "", institution: e?.institution || "", field: e?.field || "", startYear: e?.startYear || e?.startDate || "", endYear: e?.endYear || e?.endDate || "", grade: e?.grade || "" }
        )
      : [],
    skills: Array.isArray(old?.skills) ? old.skills.filter((s: any) => typeof s === "string") : [],
    projects: Array.isArray(old?.projects)
      ? old.projects.map((p: any) =>
          typeof p === "string"
            ? { id: makeId(), name: p, description: "", techStack: [], github: "", demo: "" }
            : { id: p?.id || makeId(), name: p?.name || "", description: p?.description || "", techStack: Array.isArray(p?.techStack) ? p.techStack : [], github: p?.github || "", demo: p?.demo || "" }
        )
      : [],
    certifications: Array.isArray(old?.certifications)
      ? old.certifications.map((c: any) =>
          typeof c === "string"
            ? { id: makeId(), name: c, issuer: "", issuedDate: "", expiryDate: "", credentialID: "", credentialURL: "" }
            : { id: c?.id || makeId(), name: c?.name || "", issuer: c?.issuer || "", issuedDate: c?.issuedDate || "", expiryDate: c?.expiryDate || "", credentialID: c?.credentialID || "", credentialURL: c?.credentialURL || "" }
        )
      : [],
    achievements: Array.isArray(old?.achievements)
      ? old.achievements.map((a: any) =>
          typeof a === "string"
            ? { id: makeId(), title: a, description: "", date: "" }
            : { id: a?.id || makeId(), title: a?.title || "", description: a?.description || "", date: a?.date || "" }
        )
      : [],
    openSource: Array.isArray(old?.openSource)
      ? old.openSource.map((o: any) =>
          typeof o === "string"
            ? { id: makeId(), project: o, contribution: "", github: "" }
            : { id: o?.id || makeId(), project: o?.project || "", contribution: o?.contribution || "", github: o?.github || "" }
        )
      : [],
    publications: Array.isArray(old?.publications)
      ? old.publications.map((p: any) =>
          typeof p === "string"
            ? { id: makeId(), title: p, publisher: "", date: "", url: "" }
            : { id: p?.id || makeId(), title: p?.title || "", publisher: p?.publisher || "", date: p?.date || "", url: p?.url || "" }
        )
      : [],
    volunteering: Array.isArray(old?.volunteering)
      ? old.volunteering.map((v: any) =>
          typeof v === "string"
            ? { id: makeId(), role: v, organization: "", description: "", startDate: "", endDate: "" }
            : { id: v?.id || makeId(), role: v?.role || "", organization: v?.organization || "", description: v?.description || "", startDate: v?.startDate || "", endDate: v?.endDate || "" }
        )
      : [],
    languages: Array.isArray(old?.languages)
      ? old.languages.map((l: any) =>
          typeof l === "string"
            ? { id: makeId(), language: l, proficiency: "" }
            : { id: l?.id || makeId(), language: l?.language || "", proficiency: l?.proficiency || "" }
        )
      : [],
  };
}

function loadFromSession(): ResumeData {
  if (typeof window === "undefined") return { ...EMPTY_RESUME };
  try {
    const raw = sessionStorage.getItem("smartjob_resume");
    if (!raw) return { ...EMPTY_RESUME };
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object" && typeof parsed.name === "string" && !parsed.contact) {
      return migrateOldFormat(parsed);
    }
    // Merge with EMPTY_RESUME to ensure all new fields exist
    return {
      ...EMPTY_RESUME,
      ...parsed,
      contact: { ...EMPTY_RESUME.contact, ...(parsed.contact || {}) },
    };
  } catch {
    return { ...EMPTY_RESUME };
  }
}

function persist(data: ResumeData) {
  if (typeof window !== "undefined") {
    sessionStorage.setItem("smartjob_resume", JSON.stringify(data));
  }
}

function makeUpdater<T>(field: keyof ResumeData) {
  return (id: string, key: keyof T, value: any) =>
    (s: any) => {
      const updated = {
        ...s.resumeData,
        [field]: (s.resumeData[field] as any[]).map((e: any) => (e.id === id ? { ...e, [key]: value } : e)),
      };
      persist(updated);
      return { resumeData: updated };
    };
}

function makeRemover(field: keyof ResumeData) {
  return (id: string) =>
    (s: any) => {
      const updated = { ...s.resumeData, [field]: (s.resumeData[field] as any[]).filter((e: any) => e.id !== id) };
      persist(updated);
      return { resumeData: updated };
    };
}

export const useResumeStore = create<ResumeStore>((set, get) => ({
  resumeData: loadFromSession(),
  activeStep: 0,
  completedSteps: [],

  updateContact: (field, value) =>
    set((s) => {
      const updated = { ...s.resumeData, contact: { ...s.resumeData.contact, [field]: value } };
      persist(updated);
      return { resumeData: updated };
    }),

  setSummary: (summary) =>
    set((s) => {
      const updated = { ...s.resumeData, summary };
      persist(updated);
      return { resumeData: updated };
    }),

  // ── Experience ───────────────────────────────────────────────────────────────
  addExperience: () =>
    set((s) => {
      const newEntry: ExperienceEntry = { id: makeId(), title: "", company: "", startDate: "", endDate: "", current: false, location: "", description: "" };
      const updated = { ...s.resumeData, experience: [...s.resumeData.experience, newEntry] };
      persist(updated);
      return { resumeData: updated };
    }),
  updateExperience: (id, field, value) => set(makeUpdater<ExperienceEntry>("experience")(id, field, value)),
  removeExperience: (id) => set(makeRemover("experience")(id)),

  // ── Education ────────────────────────────────────────────────────────────────
  addEducation: () =>
    set((s) => {
      const newEntry: EducationEntry = { id: makeId(), degree: "", institution: "", field: "", startYear: "", endYear: "", grade: "" };
      const updated = { ...s.resumeData, education: [...s.resumeData.education, newEntry] };
      persist(updated);
      return { resumeData: updated };
    }),
  updateEducation: (id, field, value) => set(makeUpdater<EducationEntry>("education")(id, field, value)),
  removeEducation: (id) => set(makeRemover("education")(id)),

  // ── Skills ───────────────────────────────────────────────────────────────────
  addSkill: (skill) =>
    set((s) => {
      if (s.resumeData.skills.includes(skill)) return s;
      const updated = { ...s.resumeData, skills: [...s.resumeData.skills, skill] };
      persist(updated);
      return { resumeData: updated };
    }),
  removeSkill: (skill) =>
    set((s) => {
      const updated = { ...s.resumeData, skills: s.resumeData.skills.filter((sk) => sk !== skill) };
      persist(updated);
      return { resumeData: updated };
    }),

  // ── Projects ─────────────────────────────────────────────────────────────────
  addProject: () =>
    set((s) => {
      const newEntry: ProjectEntry = { id: makeId(), name: "", description: "", techStack: [], github: "", demo: "" };
      const updated = { ...s.resumeData, projects: [...s.resumeData.projects, newEntry] };
      persist(updated);
      return { resumeData: updated };
    }),
  updateProject: (id, field, value) => set(makeUpdater<ProjectEntry>("projects")(id, field, value)),
  removeProject: (id) => set(makeRemover("projects")(id)),

  // ── Certifications ───────────────────────────────────────────────────────────
  addCertification: () =>
    set((s) => {
      const newEntry: CertificationEntry = { id: makeId(), name: "", issuer: "", issuedDate: "", expiryDate: "", credentialID: "", credentialURL: "" };
      const updated = { ...s.resumeData, certifications: [...(s.resumeData.certifications || []), newEntry] };
      persist(updated);
      return { resumeData: updated };
    }),
  updateCertification: (id, field, value) => set(makeUpdater<CertificationEntry>("certifications")(id, field, value)),
  removeCertification: (id) => set(makeRemover("certifications")(id)),

  // ── Achievements ─────────────────────────────────────────────────────────────
  addAchievement: () =>
    set((s) => {
      const newEntry: AchievementEntry = { id: makeId(), title: "", description: "", date: "" };
      const updated = { ...s.resumeData, achievements: [...(s.resumeData.achievements || []), newEntry] };
      persist(updated);
      return { resumeData: updated };
    }),
  updateAchievement: (id, field, value) => set(makeUpdater<AchievementEntry>("achievements")(id, field, value)),
  removeAchievement: (id) => set(makeRemover("achievements")(id)),

  // ── Open Source ──────────────────────────────────────────────────────────────
  addOpenSource: () =>
    set((s) => {
      const newEntry: OpenSourceEntry = { id: makeId(), project: "", contribution: "", github: "" };
      const updated = { ...s.resumeData, openSource: [...(s.resumeData.openSource || []), newEntry] };
      persist(updated);
      return { resumeData: updated };
    }),
  updateOpenSource: (id, field, value) => set(makeUpdater<OpenSourceEntry>("openSource")(id, field, value)),
  removeOpenSource: (id) => set(makeRemover("openSource")(id)),

  // ── Volunteering ─────────────────────────────────────────────────────────────
  addVolunteering: () =>
    set((s) => {
      const newEntry: VolunteeringEntry = { id: makeId(), role: "", organization: "", description: "", startDate: "", endDate: "" };
      const updated = { ...s.resumeData, volunteering: [...(s.resumeData.volunteering || []), newEntry] };
      persist(updated);
      return { resumeData: updated };
    }),
  updateVolunteering: (id, field, value) => set(makeUpdater<VolunteeringEntry>("volunteering")(id, field, value)),
  removeVolunteering: (id) => set(makeRemover("volunteering")(id)),

  // ── Languages ────────────────────────────────────────────────────────────────
  addLanguage: () =>
    set((s) => {
      const newEntry: LanguageEntry = { id: makeId(), language: "", proficiency: "" };
      const updated = { ...s.resumeData, languages: [...(s.resumeData.languages || []), newEntry] };
      persist(updated);
      return { resumeData: updated };
    }),
  updateLanguage: (id, field, value) => set(makeUpdater<LanguageEntry>("languages")(id, field, value)),
  removeLanguage: (id) => set(makeRemover("languages")(id)),

  importResumeData: (data) =>
    set((s) => {
      // data is already V2 structured (from agent or parser) — spread directly, no migration needed
      const updated = {
        ...s.resumeData,
        ...data,
        contact: { ...EMPTY_RESUME.contact, ...s.resumeData.contact, ...(data.contact || {}) },
        certifications: data.certifications || s.resumeData.certifications || [],
        achievements: data.achievements || s.resumeData.achievements || [],
        openSource: data.openSource || s.resumeData.openSource || [],
        publications: data.publications || s.resumeData.publications || [],
        volunteering: data.volunteering || s.resumeData.volunteering || [],
        languages: data.languages || s.resumeData.languages || [],
      };
      persist(updated);
      return { resumeData: updated, completedSteps: [0, 1, 2, 3, 4, 5] };
    }),

  resetResume: () => {
    if (typeof window !== "undefined") {
      sessionStorage.removeItem("smartjob_resume");
      sessionStorage.removeItem("smartjob_jd_for_builder");
    }
    set({ resumeData: { ...EMPTY_RESUME }, activeStep: 0, completedSteps: [] });
  },

  setActiveStep: (step) => set({ activeStep: step }),
  markStepComplete: (step) => set((s) => ({ completedSteps: Array.from(new Set([...s.completedSteps, step])) })),
}));
