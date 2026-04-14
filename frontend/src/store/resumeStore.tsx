"use client";

import { create } from "zustand";
import type {
  ContactInfo,
  EducationEntry,
  ExperienceEntry,
  ProjectEntry,
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

  importResumeData: (data: Partial<ResumeData>) => void;

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
      portfolio: old?.contact?.portfolioUrl || "",
    },
    summary: old?.summary || "",
    experience: Array.isArray(old?.experience)
      ? old.experience.map((e: any) =>
          typeof e === "string"
            ? {
                id: makeId(),
                title: "",
                company: "",
                startDate: "",
                endDate: "",
                current: false,
                location: "",
                description: e,
              }
            : {
                id: e?.id || makeId(),
                title: e?.title || "",
                company: e?.company || "",
                startDate: e?.startDate || "",
                endDate: e?.endDate || "",
                current: !!e?.current,
                location: e?.location || "",
                description: e?.description || "",
              }
        )
      : [],
    education: Array.isArray(old?.education)
      ? old.education.map((e: any) =>
          typeof e === "string"
            ? {
                id: makeId(),
                degree: e,
                institution: "",
                field: "",
                startYear: "",
                endYear: "",
                grade: "",
              }
            : {
                id: e?.id || makeId(),
                degree: e?.degree || "",
                institution: e?.institution || "",
                field: e?.field || "",
                startYear: e?.startYear || "",
                endYear: e?.endYear || "",
                grade: e?.grade || "",
              }
        )
      : [],
    skills: Array.isArray(old?.skills) ? old.skills.filter((s: any) => typeof s === "string") : [],
    projects: Array.isArray(old?.projects)
      ? old.projects.map((p: any) =>
          typeof p === "string"
            ? { id: makeId(), name: p, description: "", techStack: [], github: "", demo: "" }
            : {
                id: p?.id || makeId(),
                name: p?.name || "",
                description: p?.description || "",
                techStack: Array.isArray(p?.techStack) ? p.techStack : [],
                github: p?.github || "",
                demo: p?.demo || "",
              }
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
    return { ...EMPTY_RESUME, ...parsed };
  } catch {
    return { ...EMPTY_RESUME };
  }
}

function persist(data: ResumeData) {
  if (typeof window !== "undefined") {
    sessionStorage.setItem("smartjob_resume", JSON.stringify(data));
  }
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

  addExperience: () =>
    set((s) => {
      const newEntry: ExperienceEntry = {
        id: makeId(),
        title: "",
        company: "",
        startDate: "",
        endDate: "",
        current: false,
        location: "",
        description: "",
      };
      const updated = { ...s.resumeData, experience: [...s.resumeData.experience, newEntry] };
      persist(updated);
      return { resumeData: updated };
    }),

  updateExperience: (id, field, value) =>
    set((s) => {
      const updated = {
        ...s.resumeData,
        experience: s.resumeData.experience.map((e) => (e.id === id ? { ...e, [field]: value } : e)),
      };
      persist(updated);
      return { resumeData: updated };
    }),

  removeExperience: (id) =>
    set((s) => {
      const updated = { ...s.resumeData, experience: s.resumeData.experience.filter((e) => e.id !== id) };
      persist(updated);
      return { resumeData: updated };
    }),

  addEducation: () =>
    set((s) => {
      const newEntry: EducationEntry = {
        id: makeId(),
        degree: "",
        institution: "",
        field: "",
        startYear: "",
        endYear: "",
        grade: "",
      };
      const updated = { ...s.resumeData, education: [...s.resumeData.education, newEntry] };
      persist(updated);
      return { resumeData: updated };
    }),

  updateEducation: (id, field, value) =>
    set((s) => {
      const updated = {
        ...s.resumeData,
        education: s.resumeData.education.map((e) => (e.id === id ? { ...e, [field]: value } : e)),
      };
      persist(updated);
      return { resumeData: updated };
    }),

  removeEducation: (id) =>
    set((s) => {
      const updated = { ...s.resumeData, education: s.resumeData.education.filter((e) => e.id !== id) };
      persist(updated);
      return { resumeData: updated };
    }),

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

  addProject: () =>
    set((s) => {
      const newEntry: ProjectEntry = { id: makeId(), name: "", description: "", techStack: [], github: "", demo: "" };
      const updated = { ...s.resumeData, projects: [...s.resumeData.projects, newEntry] };
      persist(updated);
      return { resumeData: updated };
    }),

  updateProject: (id, field, value) =>
    set((s) => {
      const updated = {
        ...s.resumeData,
        projects: s.resumeData.projects.map((p) => (p.id === id ? { ...p, [field]: value } : p)),
      };
      persist(updated);
      return { resumeData: updated };
    }),

  removeProject: (id) =>
    set((s) => {
      const updated = { ...s.resumeData, projects: s.resumeData.projects.filter((p) => p.id !== id) };
      persist(updated);
      return { resumeData: updated };
    }),

  importResumeData: (data) =>
    set((s) => {
      const updated = {
        ...s.resumeData,
        ...data,
        contact: { ...s.resumeData.contact, ...(data.contact || {}) },
      };
      persist(updated);
      return { resumeData: updated, completedSteps: [0, 1, 2, 3, 4] };
    }),

  setActiveStep: (step) => set({ activeStep: step }),
  markStepComplete: (step) => set((s) => ({ completedSteps: Array.from(new Set([...s.completedSteps, step])) })),
}));
