from app.schemas.architecture import ArchitectureSpec
from app.schemas.load_profile import LoadProfileSpec, LoadScenario, UserJourney, UserJourneyStep
from app.schemas.script import GeneratedScript, ScriptTarget


class LocustExporter:
    def export(self, architecture: ArchitectureSpec, load_profile: LoadProfileSpec) -> GeneratedScript:
        scenario = self._select_scenario(load_profile)
        journeys = scenario.user_journeys or self._fallback_journeys(scenario)
        task_methods = "\n\n".join(self._render_journey_task(journey, index) for index, journey in enumerate(journeys, start=1))
        worker_user_class = self._render_background_worker_class(scenario)
        load_shape = self._render_load_shape(scenario)
        architecture_comment = ", ".join(node.name for node in architecture.services[:4]) or "API Service"

        content = f'''from locust import HttpUser, LoadTestShape, between, task


# ScaleCraft generated Locust file.
# This file models weighted user journeys, pacing, and per-request assertions.
# Primary architecture components involved: {architecture_comment}.

class ScaleCraftUser(HttpUser):
    # Wait time provides pacing between user actions based on the generated think time.
    wait_time = between({max(0.1, scenario.think_time_seconds / 2):.1f}, {scenario.think_time_seconds + 0.5:.1f})

    def request_json(self, method: str, path: str, payload: dict | None = None, name: str | None = None) -> None:
        # Replace templated IDs with stable sample values so the file is runnable as-is.
        normalized_path = path.replace("{{id}}", "sample-123")
        normalized_path = normalized_path.replace("{{conversation_id}}", "conv-123")
        with self.client.request(method, normalized_path, json=payload, name=name or normalized_path, catch_response=True) as response:
            # Basic assertions fail the task on server errors or obvious latency regressions.
            if response.status_code >= 500:
                response.failure(f"Unexpected server error: {{response.status_code}}")
                return
            if response.elapsed.total_seconds() > 1.0:
                response.failure("Latency exceeded 1.0s budget")
                return
            response.success()

{task_methods}

{load_shape}
{worker_user_class}
'''
        return GeneratedScript(
            target=ScriptTarget.locust,
            file_name="locustfile.py",
            language="python",
            content=content,
            entrypoint_command="locust -f locustfile.py --host=http://localhost:8000",
        )

    def _select_scenario(self, load_profile: LoadProfileSpec) -> LoadScenario:
        return max(load_profile.scenarios, key=lambda item: item.peak_rps)

    def _render_journey_task(self, journey: UserJourney, index: int) -> str:
        body = [
            f"    @task({journey.percentage})",
            f"    def journey_{index}(self):",
            f"        # {journey.name}: weighted at {journey.percentage}% of modeled user traffic.",
        ]
        for step in journey.steps:
            payload = self._render_payload(step)
            body.append(
                f"        self.request_json('{step.method}', '{step.path}', payload={payload}, name='{step.name}')"
            )
        return "\n".join(body)

    def _render_background_worker_class(self, scenario: LoadScenario) -> str:
        if not scenario.background_worker_traffic:
            return ""

        lines = [
            "",
            "class BackgroundWorkerTriggerUser(HttpUser):",
            "    # This user approximates API calls that create asynchronous queue and worker pressure.",
            "    wait_time = between(1.0, 3.0)",
        ]
        for index, worker in enumerate(scenario.background_worker_traffic, start=1):
            path = worker.trigger_sources[0] if worker.trigger_sources else "/api/background-jobs"
            payload = self._render_worker_payload(worker.job_type)
            lines.extend(
                [
                    f"    @task({max(1, min(20, worker.peak_jobs_per_minute // max(worker.steady_jobs_per_minute or 1, 1)))})",
                    f"    def worker_trigger_{index}(self):",
                    f"        # {worker.name}: simulates job creation pressure for queue '{worker.queue_name}'.",
                    f"        with self.client.post('{path}', json={payload}, name='{worker.name}', catch_response=True) as response:",
                    "            if response.status_code >= 500:",
                    "                response.failure(f'Unexpected server error: {response.status_code}')",
                    "                return",
                    "            response.success()",
                ]
            )
        return "\n".join(lines)

    def _render_load_shape(self, scenario: LoadScenario) -> str:
        stages = scenario.ramp_up_stages or scenario.ramp_up
        stage_rows: list[str] = []
        elapsed = 0
        for stage in stages:
            elapsed += stage.duration_minutes * 60
            spawn_rate = max(1, stage.target_concurrency // max(stage.duration_minutes * 60, 1))
            stage_rows.append(
                f"        {{'duration': {elapsed}, 'users': {stage.target_concurrency}, 'spawn_rate': {spawn_rate}}},"
            )

        return "\n".join(
            [
                "class StagedLoadShape(LoadTestShape):",
                "    # Stage definitions mirror the generated ramp-up plan so Locust can ramp users over time.",
                "    stages = [",
                *stage_rows,
                "    ]",
                "",
                "    def tick(self):",
                "        run_time = self.get_run_time()",
                "        for stage in self.stages:",
                "            if run_time < stage['duration']:",
                "                return (stage['users'], stage['spawn_rate'])",
                "        return None",
            ]
        )

    def _render_payload(self, step: UserJourneyStep) -> str:
        normalized_path = step.path.lower()
        if step.method == "GET":
            return "None"
        if "checkout" in normalized_path:
            return "{'cart_id': 'cart-123', 'payment_token': 'tok_sample', 'confirm': True}"
        if "messages" in normalized_path:
            return "{'conversation_id': 'conv-123', 'body': 'Load test message from ScaleCraft'}"
        if "upload" in normalized_path:
            return "{'asset_id': 'asset-123', 'content_type': 'video/mp4', 'source': 'load-test'}"
        if "export" in normalized_path:
            return "{'report_id': 'report-123', 'format': 'csv'}"
        return "{'sample': True, 'source': 'scalecraft'}"

    def _render_worker_payload(self, job_type: str) -> str:
        return "{'job_type': '%s', 'source': 'scalecraft'}" % job_type

    def _fallback_journeys(self, scenario: LoadScenario) -> list[UserJourney]:
        request_mix = scenario.endpoint_request_mix or scenario.request_mix
        steps = [
            UserJourneyStep(
                name=item.name,
                method=item.method,
                path=item.path,
                description=item.name,
            )
            for item in request_mix
        ]
        return [UserJourney(name="Generated journey", persona="default", percentage=100, steps=steps)]
