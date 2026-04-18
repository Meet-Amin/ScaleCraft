from app.schemas.requirement import ParseRequirementRequest, ParserMode, ProductDomain
from app.services.parser.requirement_parser import RequirementParser


def test_parser_extracts_structured_requirement() -> None:
    parser = RequirementParser()
    response = parser.parse(
        ParseRequirementRequest(
            requirement_text=(
                "Build a global ecommerce platform where users can browse a product catalog, "
                "search inventory, checkout with Stripe, and receive email notifications. "
                "Support 400 rps baseline, peak 1800 rps, and 5000 concurrent users with 99.95% availability."
            )
        )
    )

    assert response.parser_mode == ParserMode.heuristic
    assert response.requirement.domain == ProductDomain.ecommerce
    assert response.requirement.traffic.peak_rps == 1800
    assert response.requirement.traffic.peak_concurrency == 5000
    assert "Stripe" in response.requirement.integrations
    assert response.requirement.availability_target == "99.95%"
