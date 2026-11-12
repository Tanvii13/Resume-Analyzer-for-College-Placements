
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.analysis import router, get_current_user


app = FastAPI()
app.include_router(router)

client = TestClient(app)


@patch("app.routers.analysis.save_improvement_log")
@patch("app.routers.analysis.get_extraction")
def test_analyze_endpoint_returns_score(
    mock_extraction,
    mock_save
):
    app.dependency_overrides[get_current_user] = (
        lambda: {
            "id": "11111111-1111-1111-1111-111111111111"
        }
    )

    mock_extraction.return_value = {
        "skills": ["Python", "SQL"],
        "education": [{"degree": "B.Tech"}],
        "projects": [],
        "experience": []
    }

    mock_save.return_value = {
        "id": "log-1"
    }

    response = client.post(
        "/resumes/resume-1/analyze"
    )

    assert response.status_code == 200

    data = response.json()

    assert "overall_score" in data
    assert 0 <= data["overall_score"] <= 100

    app.dependency_overrides.clear()
