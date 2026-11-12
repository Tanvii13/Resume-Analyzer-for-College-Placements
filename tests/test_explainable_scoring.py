
from app.services.scoring_service import score_resume


def test_score_is_within_range():
    result = score_resume({
        "skills": ["Python"],
        "education": [{"degree": "B.Tech"}]
    })

    assert 0 <= result["overall_score"] <= 100


def test_each_category_has_explanation():
    result = score_resume({})

    categories = [
        "skills",
        "education",
        "projects",
        "experience",
        "completeness"
    ]

    for category in categories:
        assert "reason" in result["category_scores"][category]
        assert "score" in result["category_scores"][category]
        assert "maximum" in result["category_scores"][category]


def test_incomplete_extraction_adds_warning():
    result = score_resume({
        "extraction_complete": False
    })

    assert any(
        "incomplete" in warning.lower()
        for warning in result["warnings"]
    )
