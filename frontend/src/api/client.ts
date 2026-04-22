import type {
  GenerateArchitectureResponse,
  ParseRequirementResponse,
  StructuredRequirementSpec,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

interface ApiErrorPayload {
  detail?: string | { msg?: string }[];
}

async function extractErrorMessage(response: Response): Promise<string> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    const payload = (await response.json()) as ApiErrorPayload;
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    if (Array.isArray(payload.detail)) {
      return payload.detail.map((item) => item.msg ?? "Validation error").join(", ");
    }
  }

  return (await response.text()) || `Request failed with status ${response.status}`;
}

async function apiPost<TResponse>(path: string, payload: object): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await extractErrorMessage(response));
  }

  return (await response.json()) as TResponse;
}

export const scaleCraftApi = {
  parse(requirementText: string): Promise<ParseRequirementResponse> {
    return apiPost<ParseRequirementResponse>("/parse", { requirement_text: requirementText });
  },
  architecture(requirement: StructuredRequirementSpec): Promise<GenerateArchitectureResponse> {
    return apiPost<GenerateArchitectureResponse>("/architecture", { requirement });
  },
};
