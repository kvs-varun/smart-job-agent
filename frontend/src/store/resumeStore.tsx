"use client";

import React, { createContext, useContext, useMemo, useReducer } from "react";
import type { ResumeData } from "@/types/resume";

export type BuilderStep = 1 | 2 | 3 | 4;

export type BuilderState = {
  step: BuilderStep;
  resumeSource: "text" | "upload";
  busy: boolean;
  error: string | null;

  resumeText: string;
  jobDescription: string;

  previewReady: boolean;
  approved: boolean;
  pdfReady: boolean;

  resumeData: ResumeData;
  jobAnalysis: Record<string, unknown> | null;
  downloadUrl: string | null;

  matchPct: number | null;
  atsAlignmentScore: number | null;
  matchedSkills: string[];
  missingSkills: string[];
  gatePassed: boolean | null;
  gateScore: number | null;
  gateCoverage: number | null;
  gateSuggestions: string[];
};

type Action =
  | { type: "setStep"; step: BuilderStep }
  | { type: "setBusy"; busy: boolean }
  | { type: "setError"; error: string | null }
  | { type: "setResumeSource"; resumeSource: BuilderState["resumeSource"] }
  | { type: "setResumeText"; resumeText: string }
  | { type: "setJobDescription"; jobDescription: string }
  | { type: "setResumeData"; resumeData: ResumeData }
  | {
      type: "setPreview";
      payload: {
        previewReady: boolean;
        jobAnalysis: Record<string, unknown> | null;
        matchPct: number | null;
        atsAlignmentScore: number | null;
        matchedSkills: string[];
        missingSkills: string[];
        gatePassed: boolean | null;
        gateScore: number | null;
        gateCoverage: number | null;
        gateSuggestions: string[];
      };
    }
  | { type: "setFinalize"; payload: { pdfReady: boolean; downloadUrl: string | null } }
  | { type: "resetAfterInputChange" };

export const initialResumeData: ResumeData = {
  name: null,
  title: null,
  contact: {},
  summary: "",
  skills: [],
  projects: [],
  education: [],
  experience: [],
  familiarity_exposure: [],
};

export const initialBuilderState: BuilderState = {
  step: 1,
  resumeSource: "text",
  busy: false,
  error: null,

  resumeText: "",
  jobDescription: "",

  previewReady: false,
  approved: false,
  pdfReady: false,

  resumeData: initialResumeData,
  jobAnalysis: null,
  downloadUrl: null,

  matchPct: null,
  atsAlignmentScore: null,
  matchedSkills: [],
  missingSkills: [],
  gatePassed: null,
  gateScore: null,
  gateCoverage: null,
  gateSuggestions: [],
};

function reducer(state: BuilderState, action: Action): BuilderState {
  switch (action.type) {
    case "setStep":
      return { ...state, step: action.step };
    case "setBusy":
      return { ...state, busy: action.busy };
    case "setError":
      return { ...state, error: action.error };
    case "setResumeSource":
      return { ...state, resumeSource: action.resumeSource, error: null };
    case "setResumeText":
      return { ...state, resumeText: action.resumeText };
    case "setJobDescription":
      return { ...state, jobDescription: action.jobDescription };
    case "setResumeData":
      return { ...state, resumeData: action.resumeData };
    case "setPreview":
      return {
        ...state,
        previewReady: action.payload.previewReady,
        approved: false,
        pdfReady: false,
        downloadUrl: null,
        jobAnalysis: action.payload.jobAnalysis,
        matchPct: action.payload.matchPct,
        atsAlignmentScore: action.payload.atsAlignmentScore,
        matchedSkills: action.payload.matchedSkills,
        missingSkills: action.payload.missingSkills,
        gatePassed: action.payload.gatePassed,
        gateScore: action.payload.gateScore,
        gateCoverage: action.payload.gateCoverage,
        gateSuggestions: action.payload.gateSuggestions,
      };
    case "setFinalize":
      return {
        ...state,
        approved: true,
        pdfReady: action.payload.pdfReady,
        downloadUrl: action.payload.downloadUrl,
      };
    case "resetAfterInputChange":
      return {
        ...state,
        error: null,
        previewReady: false,
        approved: false,
        pdfReady: false,
        downloadUrl: null,
        jobAnalysis: null,
        matchPct: null,
        atsAlignmentScore: null,
        matchedSkills: [],
        missingSkills: [],
        gatePassed: null,
        gateScore: null,
        gateCoverage: null,
        gateSuggestions: [],
        step: 1,
      };
    default:
      return state;
  }
}

const Ctx = createContext<{
  state: BuilderState;
  dispatch: React.Dispatch<Action>;
} | null>(null);

export function ResumeStoreProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialBuilderState);
  const value = useMemo(() => ({ state, dispatch }), [state]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useResumeStore() {
  const ctx = useContext(Ctx);
  if (!ctx) {
    throw new Error("useResumeStore must be used within ResumeStoreProvider");
  }
  return ctx;
}
