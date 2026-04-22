import { useState } from "react";

import { scaleCraftApi } from "../api/client";
import type { ArchitectureSpec, ParseRequirementResponse } from "../api/types";

export type PipelineStep = "parse" | "architecture";
export type PipelineStepState = "idle" | "loading" | "success" | "error";

export interface PipelineStatus {
  parse: PipelineStepState;
  architecture: PipelineStepState;
}

export interface StepErrors {
  parse: string | null;
  architecture: string | null;
}

interface ScaleCraftState {
  error: string | null;
  parseResult: ParseRequirementResponse | null;
  architecture: ArchitectureSpec | null;
  pipelineStatus: PipelineStatus;
  stepErrors: StepErrors;
}

const initialPipelineStatus: PipelineStatus = {
  parse: "idle",
  architecture: "idle",
};

const initialStepErrors: StepErrors = {
  parse: null,
  architecture: null,
};

const initialState: ScaleCraftState = {
  error: null,
  parseResult: null,
  architecture: null,
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
        }),
        stepErrors: updateStepErrors(current.stepErrors, {
          parse: null,
          architecture: null,
        }),
      }));

      const architectureResult = await scaleCraftApi.architecture(requirement);

      setState((current) => ({
        ...current,
        architecture: architectureResult.architecture,
        error: null,
        pipelineStatus: updatePipelineStatus(current.pipelineStatus, {
          architecture: "success",
        }),
        stepErrors: updateStepErrors(current.stepErrors, {
          architecture: null,
        }),
      }));
    } catch (error) {
      setState((current) => ({
        ...current,
        error: error instanceof Error ? error.message : "Unexpected error",
        pipelineStatus: updatePipelineStatus(current.pipelineStatus, {
          parse: current.pipelineStatus.parse === "loading" ? "error" : current.pipelineStatus.parse,
          architecture:
            current.pipelineStatus.architecture === "loading" ? "error" : current.pipelineStatus.architecture,
        }),
        stepErrors: updateStepErrors(current.stepErrors, {
          parse: current.pipelineStatus.parse === "loading" ? error instanceof Error ? error.message : "Failed to parse requirement" : null,
          architecture:
            current.pipelineStatus.architecture === "loading"
              ? error instanceof Error
                ? error.message
                : "Failed to generate architecture"
              : null,
        }),
      }));
    }
  }

  return {
    ...state,
    isLoading: anyStepLoading(state.pipelineStatus),
    activeStepLabel: activeStepLabel(state.pipelineStatus),
    runAnalysis,
  };
}
