import { useState } from "react";

import { scaleCraftApi } from "../api/client";
import type {
  ArchitectureSpec,
  GeneratedScript,
  LoadProfileSpec,
  ParseRequirementResponse,
  RiskReport,
} from "../api/types";

export type PipelineStep = "parse" | "architecture" | "loadProfile" | "scripts" | "risks";
export type PipelineStepState = "idle" | "loading" | "success" | "error";

export interface PipelineStatus {
  parse: PipelineStepState;
  architecture: PipelineStepState;
  loadProfile: PipelineStepState;
  scripts: PipelineStepState;
  risks: PipelineStepState;
}

export interface StepErrors {
  parse: string | null;
  architecture: string | null;
  loadProfile: string | null;
  scripts: string | null;
  risks: string | null;
}

interface ScaleCraftState {
  error: string | null;
  parseResult: ParseRequirementResponse | null;
  architecture: ArchitectureSpec | null;
  loadProfile: LoadProfileSpec | null;
  scripts: GeneratedScript[];
  riskReport: RiskReport | null;
  pipelineStatus: PipelineStatus;
  stepErrors: StepErrors;
}

const initialPipelineStatus: PipelineStatus = {
  parse: "idle",
  architecture: "idle",
  loadProfile: "idle",
  scripts: "idle",
  risks: "idle",
};

const initialStepErrors: StepErrors = {
  parse: null,
  architecture: null,
  loadProfile: null,
  scripts: null,
  risks: null,
};

const initialState: ScaleCraftState = {
  error: null,
  parseResult: null,
  architecture: null,
  loadProfile: null,
  scripts: [],
  riskReport: null,
  pipelineStatus: initialPipelineStatus,
  stepErrors: initialStepErrors,
};

function updatePipelineStatus(current: PipelineStatus, updates: Partial<PipelineStatus>): PipelineStatus {
  return { ...current, ...updates };
}

function updateStepErrors(current: StepErrors, updates: Partial<StepErrors>): StepErrors {
  return { ...current, ...updates };
}

function activeStepLabel(pipelineStatus: PipelineStatus): string | null {
  if (pipelineStatus.parse === "loading") {
    return "Parsing requirement";
  }
  if (pipelineStatus.architecture === "loading") {
    return "Generating architecture";
  }
  if (pipelineStatus.loadProfile === "loading") {
    return "Building load profile";
  }
  if (pipelineStatus.scripts === "loading") {
    return "Exporting test scripts";
  }
  if (pipelineStatus.risks === "loading") {
    return "Analyzing scaling risks";
  }
  return null;
}

function anyStepLoading(pipelineStatus: PipelineStatus): boolean {
  return Object.values(pipelineStatus).includes("loading");
}

export function useScaleCraft() {
  const [state, setState] = useState<ScaleCraftState>(initialState);

  async function runAnalysis(requirementText: string): Promise<void> {
    setState({
      ...initialState,
      pipelineStatus: updatePipelineStatus(initialPipelineStatus, { parse: "loading" }),
    });

    try {
      const parseResult = await scaleCraftApi.parse(requirementText);
      const requirement = parseResult.requirement;
      setState((current) => ({
        ...current,
        parseResult,
        error: null,
        pipelineStatus: updatePipelineStatus(current.pipelineStatus, {
          parse: "success",
          architecture: "loading",
          loadProfile: "loading",
        }),
        stepErrors: updateStepErrors(current.stepErrors, {
          parse: null,
          architecture: null,
          loadProfile: null,
        }),
      }));

      const [architectureResult, loadProfileResult] = await Promise.allSettled([
        scaleCraftApi.architecture(requirement),
        scaleCraftApi.loadProfile(requirement),
      ]);

      const architecture = architectureResult.status === "fulfilled" ? architectureResult.value.architecture : null;
      const loadProfile = loadProfileResult.status === "fulfilled" ? loadProfileResult.value.load_profile : null;

      setState((current) => ({
        ...current,
        architecture,
        loadProfile,
        error:
          architectureResult.status === "rejected" || loadProfileResult.status === "rejected"
            ? "Some panels could not be generated. Use the refresh actions to retry individual outputs."
            : null,
        pipelineStatus: updatePipelineStatus(current.pipelineStatus, {
          architecture: architectureResult.status === "fulfilled" ? "success" : "error",
          loadProfile: loadProfileResult.status === "fulfilled" ? "success" : "error",
          scripts: architecture && loadProfile ? "loading" : "idle",
          risks: architecture && loadProfile ? "loading" : "idle",
        }),
        stepErrors: updateStepErrors(current.stepErrors, {
          architecture:
            architectureResult.status === "rejected"
              ? architectureResult.reason instanceof Error
                ? architectureResult.reason.message
                : "Failed to generate architecture"
              : null,
          loadProfile:
            loadProfileResult.status === "rejected"
              ? loadProfileResult.reason instanceof Error
                ? loadProfileResult.reason.message
                : "Failed to generate load profile"
              : null,
        }),
      }));

      if (!architecture || !loadProfile) {
        return;
      }

      const [k6Result, locustResult, risksResult] = await Promise.allSettled([
        scaleCraftApi.generateScript(architecture, loadProfile, "k6"),
        scaleCraftApi.generateScript(architecture, loadProfile, "locust"),
        scaleCraftApi.analyzeRisks(requirement, architecture, loadProfile),
      ]);

      const scripts = [
        k6Result.status === "fulfilled" ? k6Result.value.script : null,
        locustResult.status === "fulfilled" ? locustResult.value.script : null,
      ].filter((item): item is GeneratedScript => item !== null);

      setState((current) => ({
        ...current,
        scripts,
        riskReport: risksResult.status === "fulfilled" ? risksResult.value.report : current.riskReport,
        error:
          k6Result.status === "rejected" || locustResult.status === "rejected" || risksResult.status === "rejected"
            ? "Some downstream outputs failed. Retry the scripts or risks panels individually."
            : current.error,
        pipelineStatus: updatePipelineStatus(current.pipelineStatus, {
          scripts: scripts.length === 2 ? "success" : scripts.length > 0 ? "error" : "error",
          risks: risksResult.status === "fulfilled" ? "success" : "error",
        }),
        stepErrors: updateStepErrors(current.stepErrors, {
          scripts:
            k6Result.status === "rejected" || locustResult.status === "rejected"
              ? "Failed to generate one or more script exports."
              : null,
          risks:
            risksResult.status === "rejected"
              ? risksResult.reason instanceof Error
                ? risksResult.reason.message
                : "Failed to analyze risks"
              : null,
        }),
      }));
    } catch (error) {
      setState((current) => ({
        ...current,
        error: error instanceof Error ? error.message : "Unexpected error",
        pipelineStatus: updatePipelineStatus(current.pipelineStatus, {
          parse: current.pipelineStatus.parse === "loading" ? "error" : current.pipelineStatus.parse,
        }),
        stepErrors: updateStepErrors(current.stepErrors, {
          parse: error instanceof Error ? error.message : "Failed to parse requirement",
        }),
      }));
    }
  }

  async function refreshParse(requirementText: string): Promise<void> {
    setState((current) => ({
      ...current,
      error: null,
      pipelineStatus: updatePipelineStatus(current.pipelineStatus, { parse: "loading" }),
      stepErrors: updateStepErrors(current.stepErrors, { parse: null }),
    }));

    try {
      const parseResult = await scaleCraftApi.parse(requirementText);
      setState((current) => ({
        ...current,
        parseResult,
        pipelineStatus: updatePipelineStatus(current.pipelineStatus, { parse: "success" }),
      }));
    } catch (error) {
      setState((current) => ({
        ...current,
        error: error instanceof Error ? error.message : "Unexpected error",
        pipelineStatus: updatePipelineStatus(current.pipelineStatus, { parse: "error" }),
        stepErrors: updateStepErrors(current.stepErrors, {
          parse: error instanceof Error ? error.message : "Failed to parse requirement",
        }),
      }));
    }
  }

  async function refreshArchitecture(): Promise<void> {
    if (!state.parseResult) {
      return;
    }

    setState((current) => ({
      ...current,
      error: null,
      pipelineStatus: updatePipelineStatus(current.pipelineStatus, { architecture: "loading" }),
      stepErrors: updateStepErrors(current.stepErrors, { architecture: null }),
    }));

    try {
      const response = await scaleCraftApi.architecture(state.parseResult.requirement);
      setState((current) => ({
        ...current,
        architecture: response.architecture,
        pipelineStatus: updatePipelineStatus(current.pipelineStatus, { architecture: "success" }),
      }));
    } catch (error) {
      setState((current) => ({
        ...current,
        error: error instanceof Error ? error.message : "Unexpected error",
        pipelineStatus: updatePipelineStatus(current.pipelineStatus, { architecture: "error" }),
        stepErrors: updateStepErrors(current.stepErrors, {
          architecture: error instanceof Error ? error.message : "Failed to generate architecture",
        }),
      }));
    }
  }

  async function refreshLoadProfile(): Promise<void> {
    if (!state.parseResult) {
      return;
    }

    setState((current) => ({
      ...current,
      error: null,
      pipelineStatus: updatePipelineStatus(current.pipelineStatus, { loadProfile: "loading" }),
      stepErrors: updateStepErrors(current.stepErrors, { loadProfile: null }),
    }));

    try {
      const response = await scaleCraftApi.loadProfile(state.parseResult.requirement);
      setState((current) => ({
        ...current,
        loadProfile: response.load_profile,
        pipelineStatus: updatePipelineStatus(current.pipelineStatus, { loadProfile: "success" }),
      }));
    } catch (error) {
      setState((current) => ({
        ...current,
        error: error instanceof Error ? error.message : "Unexpected error",
        pipelineStatus: updatePipelineStatus(current.pipelineStatus, { loadProfile: "error" }),
        stepErrors: updateStepErrors(current.stepErrors, {
          loadProfile: error instanceof Error ? error.message : "Failed to generate load profile",
        }),
      }));
    }
  }

  async function refreshScripts(): Promise<void> {
    if (!state.architecture || !state.loadProfile) {
      return;
    }

    setState((current) => ({
      ...current,
      error: null,
      pipelineStatus: updatePipelineStatus(current.pipelineStatus, { scripts: "loading" }),
      stepErrors: updateStepErrors(current.stepErrors, { scripts: null }),
    }));

    const [k6Result, locustResult] = await Promise.allSettled([
      scaleCraftApi.generateScript(state.architecture, state.loadProfile, "k6"),
      scaleCraftApi.generateScript(state.architecture, state.loadProfile, "locust"),
    ]);

    const scripts = [
      k6Result.status === "fulfilled" ? k6Result.value.script : null,
      locustResult.status === "fulfilled" ? locustResult.value.script : null,
    ].filter((item): item is GeneratedScript => item !== null);

    setState((current) => ({
      ...current,
      scripts,
      error:
        k6Result.status === "rejected" || locustResult.status === "rejected"
          ? "Failed to generate one or more scripts."
          : null,
      pipelineStatus: updatePipelineStatus(current.pipelineStatus, {
        scripts: scripts.length === 2 ? "success" : "error",
      }),
      stepErrors: updateStepErrors(current.stepErrors, {
        scripts:
          k6Result.status === "rejected" || locustResult.status === "rejected"
            ? "Failed to generate one or more script exports."
            : null,
      }),
    }));
  }

  async function refreshRisks(): Promise<void> {
    if (!state.parseResult || !state.architecture || !state.loadProfile) {
      return;
    }

    setState((current) => ({
      ...current,
      error: null,
      pipelineStatus: updatePipelineStatus(current.pipelineStatus, { risks: "loading" }),
      stepErrors: updateStepErrors(current.stepErrors, { risks: null }),
    }));

    try {
      const response = await scaleCraftApi.analyzeRisks(
        state.parseResult.requirement,
        state.architecture,
        state.loadProfile,
      );
      setState((current) => ({
        ...current,
        riskReport: response.report,
        pipelineStatus: updatePipelineStatus(current.pipelineStatus, { risks: "success" }),
      }));
    } catch (error) {
      setState((current) => ({
        ...current,
        error: error instanceof Error ? error.message : "Unexpected error",
        pipelineStatus: updatePipelineStatus(current.pipelineStatus, { risks: "error" }),
        stepErrors: updateStepErrors(current.stepErrors, {
          risks: error instanceof Error ? error.message : "Failed to analyze risks",
        }),
      }));
    }
  }

  return {
    ...state,
    isLoading: anyStepLoading(state.pipelineStatus),
    activeStepLabel: activeStepLabel(state.pipelineStatus),
    refreshArchitecture,
    refreshLoadProfile,
    refreshParse,
    refreshRisks,
    refreshScripts,
    runAnalysis,
  };
}
