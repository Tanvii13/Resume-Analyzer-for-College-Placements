"""
Shared fixtures for NLP module tests.
"""

import pytest


@pytest.fixture
def sample_resume_text() -> str:
    """Standard synthetic college placement resume text."""
    return """Aarav Sharma
aarav.sharma@dau.ac.in | +91 98250 12345 | Ahmedabad, India
linkedin.com/in/aarav-sharma-cs | github.com/aaravsharma

EDUCATION
Degree | Institution | Year | CGPA
B.Tech in ICT | DA-IICT | 2021 - 2025 | 8.74 / 10
Class XII (CBSE) | Delhi Public School | 2021 | 94.6%

TECHNICAL SKILLS
• Programming Languages: Python, C++, C#, Java, JavaScript, TypeScript, SQL
• Frameworks & Libraries: FastAPI, React.js, Node.js, Vue.js, ASP.NET, .NET Core
• Cloud & DevOps: Docker, Kubernetes, CI/CD, Git, GitHub Actions, Linux
• Core CS: Data Structures & Algorithms, DBMS, Operating Systems, TCP/IP, Computer Networks

EXPERIENCE
Software Engineering Intern
Credence Analytics | May 2024 – July 2024
• Developed scalable REST APIs using FastAPI and PostgreSQL handling 50k
  daily requests with async connection pooling.
• Implemented automated CI/CD pipelines with GitHub Actions reducing build
  times by 30%.
• Integrated Redis caching for session management and token verification.

PROJECTS
College Placement Portal & Resume Analyzer
• Architected full-stack resume analysis platform using FastAPI, Python 3.11,
  and PostgreSQL database for college placements.
• Integrated C++ text-matching utility and Vue.js interactive dashboard.
• Repository: https://github.com/Tanvii13/Resume-Analyzer-for-College-Placements
"""
