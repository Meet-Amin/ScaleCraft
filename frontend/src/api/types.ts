export type ProductDomain =
  | "ecommerce"
  | "saas"
  | "social"
  | "fintech"
  | "media"
  | "logistics"
  | "healthcare"
  | "ai_platform"
  | "generic";

export type ParserMode = "llm" | "heuristic";
export type ComponentKind =
  | "load_balancer"
  | "service"
  | "worker"
  | "database"
  | "cache"
  | "queue"
  | "object_storage"
  | "cdn"
  | "search"
  | "external_api"
  | "observability";
export type TrafficPattern = "steady" | "spiky" | "bursty" | "diurnal";
export type LoadScenarioType =
  | "generic"
  | "chat_app"
  | "ecommerce_flash_sale"
  | "video_platform"
  | "saas_dashboard";
export type ScriptTarget = "k6" | "locust";
export type RiskSeverity = "critical" | "high" | "medium" | "low";

export interface FunctionalRequirement {
  name: string;
  description: string;
  priority: string;
}

export interface NonFunctionalRequirement {
  category: string;
  description: string;
  priority: string;
}

export interface TrafficExpectation {
  baseline_rps: number;
  peak_rps: number;
  peak_concurrency: number;
  daily_active_users: number | null;
  regions: string[];
}

export interface StructuredRequirementSpec {
  product_name: string;
  summary: string;
  domain: ProductDomain;
  client_surfaces: string[];
  functional_requirements: FunctionalRequirement[];
  non_functional_requirements: NonFunctionalRequirement[];
  integrations: string[];
  data_entities: string[];
  traffic: TrafficExpectation;
  availability_target: string;
  assumptions: string[];
}

export interface ParseRequirementResponse {
  parser_mode: ParserMode;
  requirement: StructuredRequirementSpec;
}

export interface ArchitectureNode {
  id: string;
  name: string;
  kind: ComponentKind;
  technology: string;
  description: string;
  responsibilities: string[];
  scaling_notes: string[];
  stateful: boolean;
}

export interface ArchitectureEdge {
  source: string;
  target: string;
  interaction: string;
  protocol: string;
  critical_path: boolean;
}

export interface ArchitectureGraphNode {
  id: string;
  label: string;
  kind: ComponentKind;
  technology: string;
  attributes: Record<string, unknown>;
}

export interface ArchitectureGraphEdge {
  id: string;
  source: string;
  target: string;
  interaction: string;
  protocol: string;
  critical_path: boolean;
}

export interface ArchitectureGraphJson {
  directed: boolean;
  multigraph: boolean;
  nodes: ArchitectureGraphNode[];
  edges: ArchitectureGraphEdge[];
}

export interface ArchitectureSpec {
  overview: string;
  nodes: ArchitectureNode[];
  edges: ArchitectureEdge[];
  services: ArchitectureNode[];
  databases: ArchitectureNode[];
  cache: ArchitectureNode[];
  queues: ArchitectureNode[];
  storage: ArchitectureNode[];
  observability: ArchitectureNode[];
  availability_strategy: string[];
  scaling_strategy: string[];
  failover_strategy: string[];
  data_strategy: string[];
  scaling_notes: string[];
  graph_json: ArchitectureGraphJson;
  explanation: string;
  assumptions: string[];
}

export interface GenerateArchitectureResponse {
  architecture: ArchitectureSpec;
}

export interface RequestMixItem {
  name: string;
  method: string;
  path: string;
  percentage: number;
}

export interface RampStage {
  duration_minutes: number;
  target_rps: number;
  target_concurrency: number;
}

export interface TrafficWindow {
  rps: number;
  requests_per_minute: number;
  description: string;
}

export interface ConcurrencyLevels {
  baseline_users: number;
  target_users: number;
  peak_users: number;
  background_workers: number;
}

export interface SpikeProfile {
  name: string;
  peak_multiplier: number;
  duration_minutes: number;
  recovery_minutes: number;
}

export interface SpikeTraffic {
  name: string;
  trigger: string;
  peak_rps: number;
  peak_concurrency: number;
  duration_minutes: number;
  recovery_minutes: number;
}

export interface UserJourneyStep {
  name: string;
  method: string;
  path: string;
  description: string;
}

export interface UserJourney {
  name: string;
  persona: string;
  percentage: number;
  steps: UserJourneyStep[];
}

export interface BackgroundWorkerTraffic {
  name: string;
  queue_name: string;
  job_type: string;
  steady_jobs_per_minute: number;
  peak_jobs_per_minute: number;
  trigger_sources: string[];
}

export interface LoadScenario {
  name: string;
  description: string;
  scenario_type: LoadScenarioType;
  traffic_pattern: TrafficPattern;
  duration_minutes: number;
  steady_state_rps: number;
  peak_rps: number;
  concurrency: number;
  think_time_seconds: number;
  baseline_traffic: TrafficWindow;
  spike_traffic: SpikeTraffic | null;
  concurrency_levels: ConcurrencyLevels;
  request_mix: RequestMixItem[];
  endpoint_request_mix: RequestMixItem[];
  ramp_up: RampStage[];
  ramp_up_stages: RampStage[];
  spikes: SpikeProfile[];
  user_journeys: UserJourney[];
  background_worker_traffic: BackgroundWorkerTraffic[];
  assumptions: string[];
}

export interface LoadProfileSpec {
  objective: string;
  scenarios: LoadScenario[];
  kpis: string[];
  global_assumptions: string[];
}

export interface GenerateLoadProfileResponse {
  load_profile: LoadProfileSpec;
}

export interface GeneratedScript {
  target: ScriptTarget;
  file_name: string;
  language: string;
  content: string;
  entrypoint_command: string;
}

export interface GenerateScriptResponse {
  script: GeneratedScript;
}

export interface RiskItem {
  title: string;
  severity: RiskSeverity;
  category: string;
  explanation: string;
  recommendation: string;
  description: string;
  affected_components: string[];
  rationale: string;
  recommendations: string[];
}

export interface RiskReport {
  summary: string;
  top_risks: RiskItem[];
  scaling_actions: string[];
  resilience_gaps: string[];
  assumptions: string[];
}

export interface AnalyzeRisksResponse {
  report: RiskReport;
}
