import pytest

from app.services.placement_analyzer import (
    PLACEMENT_CRITERIA,
    RUBRIC_VERSION,
    analyze_placement_readiness,
)


def test_analyzer_returns_all_six_criteria():
    result = analyze_placement_readiness({})

    assert len(result["results"]) == 6

    returned_ids = [
        item["criterion_id"] for item in result["results"]
    ]

    assert returned_ids == list(PLACEMENT_CRITERIA.keys())


def test_analyzer_returns_correct_metadata():
    result = analyze_placement_readiness({})

    assert result["rubric_version"] == RUBRIC_VERSION
    assert result["analysis_type"] == "placement_readiness"


def test_complete_resume_information_is_present():
    resume_data = {
        "academic_profile": {
            "degree": "B.Tech Computer Science",
            "cgpa": 8.7,
        },
        "technical_skills": ["Python", "C", "SQL"],
        "soft_skills": ["Communication", "Teamwork"],
        "projects": ["Resume Analyzer"],
        "experience": ["Software Development Intern"],
        "achievements": ["Hackathon Winner"],
    }

    result = analyze_placement_readiness(resume_data)

    assert all(
        item["status"] == "present"
        for item in result["results"]
    )


def test_missing_sections_are_not_assessable():
    result = analyze_placement_readiness({})

    assert all(
        item["status"] == "not_assessable"
        for item in result["results"]
    )


def test_explicitly_empty_sections_are_missing():
    resume_data = {
        criterion_id: []
        for criterion_id in PLACEMENT_CRITERIA
    }

    result = analyze_placement_readiness(resume_data)

    assert all(
        item["status"] == "missing"
        for item in result["results"]
    )


def test_whitespace_only_text_is_treated_as_empty():
    result = analyze_placement_readiness({
        "academic_profile": "   "
    })

    academic_result = result["results"][0]

    assert academic_result["status"] == "missing"
    assert academic_result["evidence"] == []


def test_numeric_evidence_is_preserved():
    result = analyze_placement_readiness({
        "academic_profile": {
            "degree": "B.Tech",
            "cgpa": 8.7,
        }
    })

    academic_result = result["results"][0]

    assert academic_result["status"] == "present"
    assert academic_result["evidence"] == ["B.Tech", "8.7"]


def test_nested_evidence_is_extracted():
    resume_data = {
        "projects": [
            {
                "name": "Resume Analyzer",
                "technologies": ["Python", "FastAPI"],
            }
        ]
    }

    result = analyze_placement_readiness(resume_data)

    project_result = result["results"][3]

    assert project_result["status"] == "present"
    assert project_result["evidence"] == [
        "Resume Analyzer",
        "Python",
        "FastAPI",
    ]


def test_missing_and_empty_sections_are_distinguished():
    resume_data = {
        "academic_profile": [],
    }

    result = analyze_placement_readiness(resume_data)

    assert result["results"][0]["status"] == "missing"
    assert result["results"][1]["status"] == "not_assessable"


def test_identical_input_produces_identical_output():
    resume_data = {
        "academic_profile": "B.Tech",
        "technical_skills": ["Python", "SQL"],
        "projects": ["Resume Analyzer"],
    }

    first_result = analyze_placement_readiness(resume_data)
    second_result = analyze_placement_readiness(resume_data)

    assert first_result == second_result


@pytest.mark.parametrize(
    "invalid_input",
    [
        None,
        "resume text",
        ["Python", "Java"],
        123,
    ],
)
def test_invalid_input_raises_type_error(invalid_input):
    with pytest.raises(TypeError):
        analyze_placement_readiness(invalid_input)


def test_each_result_contains_required_fields():
    result = analyze_placement_readiness({
        "projects": ["Resume Analyzer"]
    })

    required_fields = {
        "criterion_id",
        "criterion_name",
        "status",
        "evidence",
        "explanation",
    }

    for item in result["results"]:
        assert required_fields.issubset(item.keys())


def test_complete_project_details():
    resume_data = {
        "projects": [
            {
                "name": "Resume Analyzer",
                "description": "A resume analysis application.",
                "technologies": ["Python", "FastAPI"],
                "role": "Backend Developer",
                "outcome": "Implemented resume upload and authentication",
            }
        ]
    }

    result = analyze_placement_readiness(resume_data)
    assessment = result["results"][3]["detail_assessment"]

    assert assessment["status"] == "complete"
    assert assessment["entries"][0]["status"] == "complete"
    assert assessment["entries"][0]["missing_details"] == []


def test_partial_project_details():
    resume_data = {
        "projects": [
            {
                "name": "Resume Analyzer",
                "technologies": ["Python", "FastAPI"],
            }
        ]
    }

    result = analyze_placement_readiness(resume_data)
    assessment = result["results"][3]["detail_assessment"]

    assert assessment["status"] == "partial"
    assert assessment["entries"][0]["found_details"] == [
        "name",
        "technologies",
    ]
    assert assessment["entries"][0]["missing_details"] == [
        "description",
        "role",
        "outcome",
    ]


def test_project_with_no_structured_details_is_insufficient():
    resume_data = {
        "projects": [{}]
    }

    result = analyze_placement_readiness(resume_data)
    assessment = result["results"][3]["detail_assessment"]

    assert assessment["status"] == "insufficient"
    assert assessment["entries"][0]["missing_details"] == list(
        ("name", "description", "technologies", "role", "outcome")
    )


def test_complete_experience_details():
    resume_data = {
        "experience": [
            {
                "organization": "ABC Technologies",
                "role": "Software Intern",
                "responsibilities": "Developed backend APIs",
                "duration": "June 2026 - August 2026",
                "achievements": "Improved API response time",
            }
        ]
    }

    result = analyze_placement_readiness(resume_data)
    assessment = result["results"][4]["detail_assessment"]

    assert assessment["status"] == "complete"
    assert assessment["entries"][0]["missing_details"] == []


def test_partial_experience_details():
    resume_data = {
        "experience": [
            {
                "company": "ABC Technologies",
                "title": "Software Intern",
            }
        ]
    }

    result = analyze_placement_readiness(resume_data)
    assessment = result["results"][4]["detail_assessment"]

    assert assessment["status"] == "partial"
    assert assessment["entries"][0]["found_details"] == [
        "organization",
        "role",
    ]
    assert assessment["entries"][0]["missing_details"] == [
        "responsibilities",
        "duration",
        "achievements",
    ]


def test_multiple_projects_are_assessed_individually():
    resume_data = {
        "projects": [
            {
                "name": "Project One",
                "description": "First project",
                "technologies": ["Python"],
                "role": "Developer",
                "outcome": "Completed application",
            },
            {
                "name": "Project Two",
            },
        ]
    }

    result = analyze_placement_readiness(resume_data)
    assessment = result["results"][3]["detail_assessment"]

    assert assessment["status"] == "partial"
    assert assessment["entries"][0]["status"] == "complete"
    assert assessment["entries"][1]["status"] == "partial"


def test_empty_project_list_has_insufficient_detail_assessment():
    result = analyze_placement_readiness({
        "projects": []
    })

    project_result = result["results"][3]

    assert project_result["status"] == "missing"
    assert project_result["detail_assessment"]["status"] == "insufficient"
    assert project_result["detail_assessment"]["entries"] == []


def test_complete_academic_profile():
    resume_data = {
        "academic_profile": {
            "degree": "B.Tech",
            "field_of_study": "Computer Science",
            "institution": "DA-IICT",
            "graduation_year": 2027,
            "cgpa": 8.7,
        }
    }

    result = analyze_placement_readiness(resume_data)
    assessment = result["results"][0]["detail_assessment"]

    assert assessment["status"] == "complete"
    assert assessment["entries"][0]["missing_details"] == []


def test_partial_academic_profile():
    resume_data = {
        "academic_profile": {
            "degree": "B.Tech",
            "institution": "DA-IICT",
        }
    }

    result = analyze_placement_readiness(resume_data)
    assessment = result["results"][0]["detail_assessment"]

    assert assessment["status"] == "partial"
    assert assessment["entries"][0]["found_details"] == [
        "degree",
        "institution",
    ]
    assert assessment["entries"][0]["missing_details"] == [
        "field_of_study",
        "graduation_year",
    ]


def test_cgpa_is_optional_in_academic_assessment():
    resume_data = {
        "academic_profile": {
            "degree": "B.Tech",
            "field_of_study": "Computer Science",
            "institution": "DA-IICT",
            "graduation_year": 2027,
        }
    }

    result = analyze_placement_readiness(resume_data)
    assessment = result["results"][0]["detail_assessment"]

    assert assessment["status"] == "complete"
    assert "cgpa" not in assessment["entries"][0]["missing_details"]


def test_technical_skills_include_supporting_evidence():
    resume_data = {
        "technical_skills": [
            {"name": "Python", "evidence": "Used in Resume Analyzer project"},
            {"name": "SQL"},
        ]
    }

    result = analyze_placement_readiness(resume_data)
    assessment = result["results"][1]["skill_assessment"]

    assert assessment["status"] == "present"
    assert assessment["total_skills"] == 2
    assert assessment["skills_with_evidence"] == 1
    assert assessment["skills"][0]["evidence_status"] == "available"
    assert assessment["skills"][0]["supporting_evidence"] == [
        "Used in Resume Analyzer project"
    ]
    assert assessment["skills"][1]["evidence_status"] == "not_provided"
    assert assessment["skills"][1]["supporting_evidence"] == []


def test_soft_skills_include_supporting_evidence():
    resume_data = {
        "soft_skills": [
            {"name": "Teamwork", "evidence": "Collaborated in a six-member project team"},
            {"name": "Communication"},
        ]
    }

    result = analyze_placement_readiness(resume_data)
    assessment = result["results"][2]["skill_assessment"]

    assert assessment["status"] == "present"
    assert assessment["total_skills"] == 2
    assert assessment["skills_with_evidence"] == 1
    assert assessment["skills"][0]["evidence_status"] == "available"
    assert assessment["skills"][1]["evidence_status"] == "not_provided"
