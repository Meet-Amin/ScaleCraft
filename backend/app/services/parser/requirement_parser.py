import logging
import re
from collections.abc import Iterable

from app.schemas.requirement import (
    FunctionalRequirement,
    NonFunctionalRequirement,
    ParseRequirementRequest,
    ParseRequirementResponse,
    ParserMode,
    ProductDomain,
    RequirementPriority,
    StructuredRequirementSpec,
    TrafficExpectation,
)
from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class RequirementParser:
    def __init__(self, llm_provider: LLMProvider | None = None) -> None:
        self._llm_provider = llm_provider

    def parse(self, request: ParseRequirementRequest) -> ParseRequirementResponse:
        if self._llm_provider is not None:
            try:
                requirement = self._parse_with_llm(request.requirement_text)
                return ParseRequirementResponse(parser_mode=ParserMode.llm, requirement=requirement)
            except Exception as exc:  # pragma: no cover - fallback path
                logger.warning("LLM parsing failed, falling back to heuristics: %s", exc)

        requirement = self._heuristic_parse(request.requirement_text)
        return ParseRequirementResponse(parser_mode=ParserMode.heuristic, requirement=requirement)

    def _parse_with_llm(self, requirement_text: str) -> StructuredRequirementSpec:
        system_prompt = (
            "You convert natural-language product requirements into validated JSON. "
            "Return JSON only, no markdown. Prefer concrete assumptions over empty fields."
        )
        user_prompt = (
            "Extract a structured requirement spec from the following product request. "
            "Populate fields conservatively and avoid inventing technologies.\n\n"
            f"Requirement:\n{requirement_text}"
        )
        result = self._llm_provider.complete_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=StructuredRequirementSpec,
        )
        return StructuredRequirementSpec.model_validate(result)

    def _heuristic_parse(self, requirement_text: str) -> StructuredRequirementSpec:
        text = self._normalize_text(requirement_text)
        lowered = text.lower()

        traffic = self._extract_traffic(lowered)
        functional_requirements = self._extract_functional_requirements(text)
        non_functional_requirements = self._extract_non_functional_requirements(lowered, traffic)
        integrations = self._extract_keywords(lowered, self._integration_keywords())
        data_entities = self._extract_keywords(lowered, self._entity_keywords())
        assumptions = self._build_assumptions(lowered, traffic, functional_requirements)

        return StructuredRequirementSpec(
            product_name=self._extract_product_name(text),
            summary=text,
            domain=self._detect_domain(lowered),
            client_surfaces=self._detect_client_surfaces(lowered),
            functional_requirements=functional_requirements,
            non_functional_requirements=non_functional_requirements,
            integrations=integrations,
            data_entities=data_entities,
            traffic=traffic,
            availability_target=self._extract_availability_target(lowered),
            assumptions=assumptions,
        )

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text.strip())

    def _extract_product_name(self, text: str) -> str:
        quoted = re.search(r'"([^"]{2,80})"', text)
        if quoted:
            return quoted.group(1).strip()

        starter = re.search(
            r"(?:build|create|design|develop)\s+(?:an?|the)?\s*([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+){0,3})",
            text,
        )
        if starter:
            return starter.group(1).strip()

        noun_phrase = re.search(r"for\s+([A-Za-z][A-Za-z0-9\- ]{3,50})", text)
        if noun_phrase:
            candidate = noun_phrase.group(1).strip(" .,;")
            return candidate.title()

        return "ScaleCraft Project"

    def _detect_domain(self, lowered: str) -> ProductDomain:
        keyword_map: list[tuple[ProductDomain, tuple[str, ...]]] = [
            (ProductDomain.ecommerce, ("cart", "checkout", "product catalog", "inventory", "order")),
            (ProductDomain.fintech, ("payment", "wallet", "transaction", "bank", "ledger")),
            (ProductDomain.social, ("feed", "post", "comment", "like", "follow")),
            (ProductDomain.media, ("stream", "video", "audio", "media", "cdn")),
            (ProductDomain.logistics, ("delivery", "shipment", "driver", "tracking", "fleet")),
            (ProductDomain.healthcare, ("patient", "appointment", "ehr", "clinical", "provider")),
            (ProductDomain.ai_platform, ("ai", "model", "prompt", "inference", "agent")),
            (ProductDomain.saas, ("tenant", "dashboard", "workspace", "analytics", "subscription")),
        ]
        for domain, keywords in keyword_map:
            if any(keyword in lowered for keyword in keywords):
                return domain
        return ProductDomain.generic

    def _detect_client_surfaces(self, lowered: str) -> list[str]:
        surfaces: list[str] = []
        mapping = {
            "web": ("web", "browser", "portal"),
            "mobile": ("mobile", "ios", "android", "app"),
            "admin": ("admin", "operator", "backoffice"),
            "api": ("api", "public api", "partner"),
        }
        for surface, keywords in mapping.items():
            if any(keyword in lowered for keyword in keywords):
                surfaces.append(surface)
        return surfaces or ["web"]

    def _extract_functional_requirements(self, text: str) -> list[FunctionalRequirement]:
        sentences = [segment.strip(" .") for segment in re.split(r"[.!?;]", text) if segment.strip()]
        requirements: list[FunctionalRequirement] = []
        action_tokens = ("allow", "enable", "support", "provide", "users", "customers", "admins", "system")

        for sentence in sentences:
            lowered = sentence.lower()
            if not any(token in lowered for token in action_tokens):
                continue

            name = self._summarize_requirement_name(sentence)
            requirements.append(
                FunctionalRequirement(
                    name=name,
                    description=sentence,
                    priority=self._infer_priority(lowered),
                )
            )
            if len(requirements) >= 6:
                break

        if requirements:
            return requirements

        return [
            FunctionalRequirement(
                name="Core user workflow",
                description=text[:220],
                priority=RequirementPriority.high,
            )
        ]

    def _extract_non_functional_requirements(
        self,
        lowered: str,
        traffic: TrafficExpectation,
    ) -> list[NonFunctionalRequirement]:
        items: list[NonFunctionalRequirement] = []

        if any(keyword in lowered for keyword in ("latency", "fast", "performance", "p95", "responsive")):
            items.append(
                NonFunctionalRequirement(
                    category="performance",
                    description="Optimize for low latency and predictable response times under load.",
                    priority=RequirementPriority.high,
                )
            )

        if any(keyword in lowered for keyword in ("auth", "oauth", "secure", "security", "rbac", "permissions")):
            items.append(
                NonFunctionalRequirement(
                    category="security",
                    description="Protect user data with strong authentication, authorization, and transport security.",
                    priority=RequirementPriority.critical,
                )
            )

        if any(keyword in lowered for keyword in ("global", "multi-region", "99.9", "99.99", "ha", "high availability")):
            items.append(
                NonFunctionalRequirement(
                    category="availability",
                    description="Design for high availability across failure domains.",
                    priority=RequirementPriority.high,
                )
            )

        if traffic.peak_rps >= 500 or traffic.peak_concurrency >= 1_000:
            items.append(
                NonFunctionalRequirement(
                    category="scalability",
                    description="Sustain projected traffic growth without saturating shared dependencies.",
                    priority=RequirementPriority.high,
                )
            )

        items.append(
            NonFunctionalRequirement(
                category="observability",
                description="Capture metrics, logs, traces, and saturation signals for production operations.",
                priority=RequirementPriority.medium,
            )
        )
        return items

    def _extract_availability_target(self, lowered: str) -> str:
        match = re.search(r"(99(?:\.\d{1,2})?%)", lowered)
        if match:
            return match.group(1)
        if "mission critical" in lowered or "high availability" in lowered:
            return "99.95%"
        return "99.9%"

    def _extract_traffic(self, lowered: str) -> TrafficExpectation:
        baseline_rps = self._extract_integer(lowered, (r"(\d[\d,]*)\s*(?:rps|req/s|requests per second)",), default=50)
        peak_rps = self._extract_integer(
            lowered,
            (
                r"peak\s*(\d[\d,]*)\s*(?:rps|req/s|requests per second)",
                r"(\d[\d,]*)\s*(?:peak )?(?:rps|req/s|requests per second)",
            ),
            default=max(baseline_rps * 3, 150),
        )
        peak_concurrency = self._extract_integer(
            lowered,
            (r"(\d[\d,]*)\s*(?:concurrent users|concurrency|simultaneous users)",),
            default=max(peak_rps * 2, 200),
        )
        daily_active_users = self._extract_integer(
            lowered,
            (r"(\d[\d,]*)\s*(?:dau|daily active users)",),
            default=None,
        )

        if any(keyword in lowered for keyword in ("flash sale", "viral", "launch day", "spike")):
            peak_rps = max(peak_rps, baseline_rps * 5)
            peak_concurrency = max(peak_concurrency, peak_rps * 3)

        regions = ["us-east-1"]
        if any(keyword in lowered for keyword in ("global", "multi-region", "worldwide", "europe", "asia")):
            regions = ["us-east-1", "eu-west-1", "ap-southeast-1"]

        return TrafficExpectation(
            baseline_rps=baseline_rps,
            peak_rps=max(peak_rps, baseline_rps),
            peak_concurrency=max(peak_concurrency, peak_rps),
            daily_active_users=daily_active_users,
            regions=regions,
        )

    def _build_assumptions(
        self,
        lowered: str,
        traffic: TrafficExpectation,
        functional_requirements: Iterable[FunctionalRequirement],
    ) -> list[str]:
        assumptions: list[str] = []
        if "auth" not in lowered and "login" not in lowered:
            assumptions.append("Authentication is assumed for privileged or user-specific workflows.")
        if traffic.daily_active_users is None:
            assumptions.append("Daily active user volume was not specified and should be validated before capacity planning.")
        if not any("admin" in item.description.lower() for item in functional_requirements):
            assumptions.append("Operational tooling and admin workflows may require separate interfaces or role-based access.")
        return assumptions

    def _extract_keywords(self, lowered: str, keyword_map: dict[str, tuple[str, ...]]) -> list[str]:
        matches: list[str] = []
        for label, keywords in keyword_map.items():
            if any(keyword in lowered for keyword in keywords):
                matches.append(label)
        return matches

    def _integration_keywords(self) -> dict[str, tuple[str, ...]]:
        return {
            "Stripe": ("stripe", "payment gateway"),
            "SendGrid": ("sendgrid", "email"),
            "Twilio": ("twilio", "sms", "otp"),
            "Slack": ("slack",),
            "Segment": ("segment", "analytics"),
            "Salesforce": ("salesforce",),
            "OpenAI": ("openai", "gpt", "llm"),
        }

    def _entity_keywords(self) -> dict[str, tuple[str, ...]]:
        return {
            "users": ("user", "customer", "account", "profile"),
            "orders": ("order", "checkout", "purchase"),
            "products": ("product", "catalog", "inventory"),
            "payments": ("payment", "transaction", "invoice"),
            "content": ("content", "post", "feed", "media", "file"),
            "messages": ("message", "notification", "email", "sms"),
        }

    def _infer_priority(self, lowered_sentence: str) -> RequirementPriority:
        if any(token in lowered_sentence for token in ("must", "critical", "required")):
            return RequirementPriority.critical
        if any(token in lowered_sentence for token in ("should", "need", "important")):
            return RequirementPriority.high
        return RequirementPriority.medium

    def _summarize_requirement_name(self, sentence: str) -> str:
        cleaned = re.sub(r"^(users|customers|admins|the system)\s+", "", sentence.strip(), flags=re.IGNORECASE)
        words = cleaned.split()
        summary = " ".join(words[:6]).strip(" ,")
        return summary[:1].upper() + summary[1:] if summary else "Functional requirement"

    def _extract_integer(self, lowered: str, patterns: tuple[str, ...], default: int | None) -> int | None:
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if match:
                return int(match.group(1).replace(",", ""))
        return default
