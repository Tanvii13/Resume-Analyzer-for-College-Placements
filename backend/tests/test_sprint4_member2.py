import pytest
from app.services.opportunity_matcher import OpportunityMatcherService


# =====================================================================
# US-12 TESTS: Opportunity Relevance Ranking & Zero-Match Guidance
# =====================================================================

def test_opportunity_ranking_in_descending_order():
    matcher = OpportunityMatcherService()
    
    opportunities_pool = [
        {
            "id": "opp-1",
            "title": "Backend Intern",
            "company": "Company A",
            "required_skills": ["Python", "FastAPI"],
            "preferred_skills": ["PostgreSQL"],
        },
        {
            "id": "opp-2",
            "title": "Frontend Intern",
            "company": "Company B",
            "required_skills": ["React", "HTML5"],
            "preferred_skills": ["TypeScript"],
        },
        {
            "id": "opp-3",
            "title": "Fullstack Intern",
            "company": "Company C",
            "required_skills": ["Python", "React"],
            "preferred_skills": [],
        },
    ]

    # Student with strong backend skills
    student_skills = ["Python", "FastAPI", "PostgreSQL", "Git"]

    result = matcher.rank_opportunities_for_student(student_skills, opportunities_pool)

    ranked_cards = result["recommended_opportunities"]
    assert len(ranked_cards) == 3

    # Company A should rank #1 with highest percentage
    assert ranked_cards[0]["opportunity_id"] == "opp-1"
    assert ranked_cards[0]["match_percentage"] >= ranked_cards[1]["match_percentage"]
    assert ranked_cards[1]["match_percentage"] >= ranked_cards[2]["match_percentage"]
    assert ranked_cards[0]["relevance_tier"] == "High Fit"


def test_zero_match_fallback_guidance():
    matcher = OpportunityMatcherService()
    
    opportunities_pool = [
        {
            "id": "opp-1",
            "title": "Data Scientist",
            "company": "AI Labs",
            "required_skills": ["Python", "PyTorch", "TensorFlow"],
            "preferred_skills": ["Deep Learning"],
        }
    ]

    # Candidate with completely non-matching skills
    non_matching_skills = ["Graphic Design", "Video Editing"]

    result = matcher.rank_opportunities_for_student(
        resume_skills=non_matching_skills,
        opportunities_pool=opportunities_pool,
        min_threshold_pct=25.0
    )

    # US-12 AC 3: Should clearly inform user when no suitable opportunities are found
    assert result["has_suitable_matches"] is False
    assert result["matched_opportunities_count"] == 0
    assert result["guidance_message"] is not None
    assert "No placement opportunities currently match your profile" in result["guidance_message"]


# =====================================================================
# US-13 TESTS: Required vs Preferred Skills & Related Skill Affinity
# =====================================================================

def test_required_and_preferred_skill_separation():
    matcher = OpportunityMatcherService()
    
    opportunity = {
        "id": "opp-test",
        "title": "Software Trainee",
        "company": "Tech Corp",
        "required_skills": ["Python", "Docker"],
        "preferred_skills": ["FastAPI", "AWS"],
    }

    # Candidate has Python (Required) and FastAPI (Preferred)
    student_skills = ["Python", "FastAPI", "Git"]

    evaluation = matcher.evaluate_single_opportunity(student_skills, opportunity)
    breakdown = evaluation["skills_breakdown"]

    # US-13 AC 1 & 2: Required and Preferred must be separated
    assert "Python" in breakdown["matched_required"]
    assert "Docker" in breakdown["missing_required"]
    assert "FastAPI" in breakdown["matched_preferred"]
    assert "AWS" in breakdown["missing_preferred"]


def test_related_skill_affinity_partial_credit():
    matcher = OpportunityMatcherService()
    
    # Opportunity strictly requires PostgreSQL
    opportunity = {
        "id": "opp-db",
        "title": "Database Admin Intern",
        "company": "Cloud Data",
        "required_skills": ["PostgreSQL"],
        "preferred_skills": [],
    }

    # Candidate only knows MySQL (which is in related_skills for PostgreSQL)
    student_skills = ["MySQL"]

    evaluation = matcher.evaluate_single_opportunity(student_skills, opportunity)
    breakdown = evaluation["skills_breakdown"]

    # US-13 AC 3: Related skill should be credited rather than treated as completely missing
    assert len(breakdown["related_required"]) == 1
    assert "PostgreSQL (Alternative: MySQL)" in breakdown["related_required"][0]
    assert len(breakdown["missing_required"]) == 0
    # Related skill awards 50% credit
    assert evaluation["match_percentage"] == 50.0


def test_empty_student_skills_returns_clean_gaps():
    matcher = OpportunityMatcherService()
    
    opportunity = {
        "id": "opp-empty",
        "title": "Junior Developer",
        "company": "Startup",
        "required_skills": ["Python", "SQL"],
        "preferred_skills": ["Git"],
    }

    evaluation = matcher.evaluate_single_opportunity([], opportunity)
    
    assert evaluation["match_percentage"] == 0.0
    assert evaluation["relevance_tier"] == "Developing Fit"
    assert len(evaluation["skills_breakdown"]["missing_required"]) == 2
