import json

from app.schemas.architecture import ArchitectureSpec
from app.schemas.load_profile import LoadProfileSpec, LoadScenario, UserJourney, UserJourneyStep
from app.schemas.script import GeneratedScript, ScriptTarget


class K6Exporter:
    def export(self, architecture: ArchitectureSpec, load_profile: LoadProfileSpec) -> GeneratedScript:
        scenario = self._select_scenario(load_profile)
        stages = self._render_stages(scenario)
        journeys = self._render_journeys(scenario)
        worker_comments = self._render_worker_comments(scenario)
        supported_components = ", ".join(node.name for node in architecture.services[:4]) or "API service"

        content = f"""import http from 'k6/http';
import {{ check, sleep }} from 'k6';

// ScaleCraft generated k6 script.
// This file models ramping user traffic, weighted user journeys, pacing, and health checks.
// Primary architecture components involved: {supported_components}.

export const options = {{
  // Ramping virtual users approximates the load profile's user growth across the test window.
  stages: [
{stages}
  ],
  thresholds: {{
    // Core assertions for error rate and latency.
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<1000'],
  }},
}};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const THINK_TIME_SECONDS = {scenario.think_time_seconds};

// Weighted user journeys derived from the generated load profile.
const JOURNEYS = {journeys};

// Background worker traffic notes:
{worker_comments}

function materializePath(pathTemplate) {{
  return pathTemplate
    .replaceAll('{{id}}', 'sample-123')
    .replaceAll('{{conversation_id}}', 'conv-123')
    .replaceAll('{{report_id}}', 'report-123');
}}

function buildPayload(path, method) {{
  if (method === 'GET') {{
    return null;
  }}

  const normalizedPath = materializePath(path);
  if (normalizedPath.includes('checkout')) {{
    return JSON.stringify({{ cart_id: 'cart-123', payment_token: 'tok_sample', confirm: true }});
  }}
  if (normalizedPath.includes('messages')) {{
    return JSON.stringify({{ conversation_id: 'conv-123', body: 'Load test message from ScaleCraft' }});
  }}
  if (normalizedPath.includes('upload')) {{
    return JSON.stringify({{ asset_id: 'asset-123', content_type: 'video/mp4', source: 'load-test' }});
  }}
  if (normalizedPath.includes('export')) {{
    return JSON.stringify({{ report_id: 'report-123', format: 'csv' }});
  }}
  return JSON.stringify({{ sample: true, source: 'scalecraft' }});
}}

function requestStep(step) {{
  const path = materializePath(step.path);
  const payload = buildPayload(step.path, step.method);
  const params = {{ headers: {{ 'Content-Type': 'application/json' }} }};
  const response = step.method === 'GET'
    ? http.get(`${{BASE_URL}}${{path}}`, params)
    : http.request(step.method, `${{BASE_URL}}${{path}}`, payload, params);

  // Assertions validate both correctness and basic latency expectations per request.
  check(response, {{
    'status under 500': (r) => r.status < 500,
    'latency under 1000ms': (r) => r.timings.duration < 1000,
  }});

  // Pacing prevents unrealistically tight loops and keeps behavior closer to the modeled think time.
  sleep(Math.max(0.2, THINK_TIME_SECONDS / Math.max(stepCount(step.journey), 1)));
}}

function stepCount(journeyName) {{
  const journey = JOURNEYS.find((item) => item.name === journeyName);
  return journey ? journey.steps.length : 1;
}}

function pickJourney() {{
  const choice = Math.random() * 100;
  let cumulative = 0;
  for (const journey of JOURNEYS) {{
    cumulative += journey.percentage;
    if (choice <= cumulative) {{
      return journey;
    }}
  }}
  return JOURNEYS[0];
}}

export default function () {{
  // Each VU executes one weighted journey per iteration.
  const journey = pickJourney();
  for (const step of journey.steps) {{
    requestStep({{ ...step, journey: journey.name }});
  }}
}}
"""
        return GeneratedScript(
            target=ScriptTarget.k6,
            file_name="scalecraft_load_test.js",
            language="javascript",
            content=content,
            entrypoint_command="k6 run -e BASE_URL=http://localhost:8000 scalecraft_load_test.js",
        )

    def _select_scenario(self, load_profile: LoadProfileSpec) -> LoadScenario:
        return max(load_profile.scenarios, key=lambda item: item.peak_rps)

    def _render_stages(self, scenario: LoadScenario) -> str:
        stages = scenario.ramp_up_stages or scenario.ramp_up
        return "\n".join(
            f"    {{ duration: '{stage.duration_minutes}m', target: {stage.target_concurrency} }},"
            for stage in stages
        )

    def _render_journeys(self, scenario: LoadScenario) -> str:
        journeys = scenario.user_journeys or self._fallback_journeys(scenario)
        payload = [
            {
                "name": journey.name,
                "percentage": journey.percentage,
                "steps": [
                    {
                        "name": step.name,
                        "method": step.method,
                        "path": step.path,
                    }
                    for step in journey.steps
                ],
            }
            for journey in journeys
        ]
        return json.dumps(payload, indent=2)

    def _render_worker_comments(self, scenario: LoadScenario) -> str:
        if not scenario.background_worker_traffic:
            return "// No explicit background worker load was modeled for this scenario."
        return "\n".join(
            f"// - {worker.name}: {worker.steady_jobs_per_minute} steady jobs/min, {worker.peak_jobs_per_minute} peak jobs/min via {', '.join(worker.trigger_sources) or worker.queue_name}."
            for worker in scenario.background_worker_traffic
        )

    def _fallback_journeys(self, scenario: LoadScenario) -> list[UserJourney]:
        request_mix = scenario.endpoint_request_mix or scenario.request_mix
        return [
            UserJourney(
                name="Generated journey",
                persona="default",
                percentage=100,
                steps=[
                    UserJourneyStep(
                        name=item.name,
                        method=item.method,
                        path=item.path,
                        description=item.name,
                    )
                    for item in request_mix
                ],
            )
        ]
