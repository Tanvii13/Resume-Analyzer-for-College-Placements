import time
from typing import Any, Dict, List

from app.schemas.pipeline_schemas import (
    FullPipelineResult,
    PilotBenchmarkSummaryDTO,
)
from app.services.pipeline_orchestrator import ResumePipelineOrchestrator


# 20 Diverse Synthetic Student Profiles across 5 Technical Placement Domains
PILOT_RESUME_CORPUS: List[Dict[str, Any]] = [
    # Domain 1: Backend Development (Candidates 1-4)
    {
        "id": "CANDIDATE-01",
        "domain": "Backend",
        "text": "Software Engineering Student. Skills: Python, FastAPI, PostgreSQL, Docker, Redis, Git, Linux. Built REST APIs.",
        "sections": {"Skills": "Python, FastAPI, PostgreSQL, Docker, Redis", "Experience": "Backend Intern building microservices."},
    },
    {
        "id": "CANDIDATE-02",
        "domain": "Backend",
        "text": "Computer Science undergrad. Proficient in Python, Django, MySQL, RabbitMQ, Docker, REST APIs, Unit Testing.",
        "sections": {"Skills": "Python, Django, MySQL, RabbitMQ", "Projects": "E-commerce order fulfillment service."},
    },
    {
        "id": "CANDIDATE-03",
        "domain": "Backend",
        "text": "Junior Developer. Skills: Java, Spring Boot, PostgreSQL, Kafka, Maven, Docker, AWS.",
        "sections": {"Skills": "Java, Spring Boot, Kafka, Docker", "Education": "B.Tech Computer Science."},
    },
    {
        "id": "CANDIDATE-04",
        "domain": "Backend",
        "text": "Student developer with experience in Python, Flask, MongoDB, Docker, Git, PyTest, GitHub Actions.",
        "sections": {"Skills": "Python, Flask, MongoDB, Docker", "Projects": "Student placement portal backend."},
    },

    # Domain 2: Full-Stack & Frontend (Candidates 5-8)
    {
        "id": "CANDIDATE-05",
        "domain": "Full-Stack",
        "text": "Full Stack enthusiast. Skills: JavaScript, TypeScript, React, Node.js, Express, TailwindCSS, MongoDB, GraphQL.",
        "sections": {"Skills": "JavaScript, TypeScript, React, Node.js", "Projects": "Real-time collaborative whiteboard."},
    },
    {
        "id": "CANDIDATE-06",
        "domain": "Full-Stack",
        "text": "Frontend Developer. Expertise in React, Next.js, Redux, CSS3, HTML5, Jest, Webpack, Figma.",
        "sections": {"Skills": "React, Next.js, Redux, HTML5, CSS3", "Experience": "Frontend developer at campus club."},
    },
    {
        "id": "CANDIDATE-07",
        "domain": "Full-Stack",
        "text": "Web developer. Skills: Vue.js, Node.js, Express, PostgreSQL, TailwindCSS, REST APIs, Git, Vite.",
        "sections": {"Skills": "Vue.js, Node.js, Express, TailwindCSS", "Projects": "Alumni tracking web portal."},
    },
    {
        "id": "CANDIDATE-08",
        "domain": "Full-Stack",
        "text": "Full Stack developer with Angular, TypeScript, Java, Spring Boot, MySQL, RxJS, Docker.",
        "sections": {"Skills": "Angular, TypeScript, Spring Boot, MySQL", "Projects": "Hospital appointment manager."},
    },

    # Domain 3: Cloud & DevOps (Candidates 9-12)
    {
        "id": "CANDIDATE-09",
        "domain": "DevOps",
        "text": "DevOps Engineer intern. Skills: AWS, Docker, Kubernetes, Terraform, GitHub Actions, Linux, Bash, Prometheus.",
        "sections": {"Skills": "AWS, Docker, Kubernetes, Terraform, Bash", "Projects": "Automated multi-region CI/CD deployment."},
    },
    {
        "id": "CANDIDATE-10",
        "domain": "DevOps",
        "text": "Cloud computing student. Proficient in Azure, Terraform, Docker, Ansible, Linux, Git, Jenkins, Python scripting.",
        "sections": {"Skills": "Azure, Terraform, Ansible, Jenkins", "Certifications": "Azure Fundamentals AZ-900."},
    },
    {
        "id": "CANDIDATE-11",
        "domain": "DevOps",
        "text": "Site reliability aspirant. Skills: Linux, Bash, Python, Docker, Grafana, ELK Stack, Nginx, CI/CD.",
        "sections": {"Skills": "Linux, Python, Docker, Grafana, Nginx", "Projects": "Server health telemetry dashboard."},
    },
    {
        "id": "CANDIDATE-12",
        "domain": "DevOps",
        "text": "Cloud infrastructure enthusiast. Skills: AWS EC2, S3, Docker, Kubernetes, Helm, GitLab CI, Python, Shell scripting.",
        "sections": {"Skills": "AWS, Docker, Kubernetes, Helm", "Education": "Information Technology."},
    },

    # Domain 4: Data Science & AI/ML (Candidates 13-16)
    {
        "id": "CANDIDATE-13",
        "domain": "Data/ML",
        "text": "Data Science student. Skills: Python, Pandas, NumPy, Scikit-Learn, PyTorch, SQL, Matplotlib, Data Cleaning.",
        "sections": {"Skills": "Python, Pandas, Scikit-Learn, PyTorch, SQL", "Projects": "Placement prediction using XGBoost."},
    },
    {
        "id": "CANDIDATE-14",
        "domain": "Data/ML",
        "text": "Machine Learning enthusiast. Proficient in Python, TensorFlow, Keras, OpenCV, NLP, HuggingFace, SQL.",
        "sections": {"Skills": "Python, TensorFlow, OpenCV, NLP", "Projects": "Automated medical document classifier."},
    },
    {
        "id": "CANDIDATE-15",
        "domain": "Data/ML",
        "text": "Data Analyst intern. Skills: Python, SQL, Tableau, PowerBI, Excel, Pandas, Statistical Analysis, A/B Testing.",
        "sections": {"Skills": "Python, SQL, Tableau, PowerBI, Excel", "Experience": "Analytics intern at fintech startup."},
    },
    {
        "id": "CANDIDATE-16",
        "domain": "Data/ML",
        "text": "Deep Learning researcher. Skills: Python, PyTorch, Transformers, LangChain, FAISS, Docker, Git, Linux.",
        "sections": {"Skills": "Python, PyTorch, LangChain, FAISS", "Projects": "Campus Q&A bot using RAG architecture."},
    },

    # Domain 5: Mobile Development (Candidates 17-20)
    {
        "id": "CANDIDATE-17",
        "domain": "Mobile",
        "text": "Mobile App Developer. Skills: Flutter, Dart, Firebase, REST APIs, Provider, SQLite, Git, Google Play Console.",
        "sections": {"Skills": "Flutter, Dart, Firebase, SQLite", "Projects": "Campus food ordering mobile app."},
    },
    {
        "id": "CANDIDATE-18",
        "domain": "Mobile",
        "text": "Android developer. Expertise in Kotlin, Android SDK, Jetpack Compose, Coroutines, Room DB, Retrofit, MVVM.",
        "sections": {"Skills": "Kotlin, Android SDK, Jetpack Compose, Retrofit", "Experience": "Android app contributor."},
    },
    {
        "id": "CANDIDATE-19",
        "domain": "Mobile",
        "text": "Cross-platform developer. Skills: React Native, JavaScript, TypeScript, Expo, Redux, Firebase, REST APIs.",
        "sections": {"Skills": "React Native, TypeScript, Expo, Firebase", "Projects": "Fitness tracking mobile application."},
    },
    {
        "id": "CANDIDATE-20",
        "domain": "Mobile",
        "text": "iOS app enthusiast. Proficient in Swift, SwiftUI, Combine, CoreData, Xcode, Git, REST APIs.",
        "sections": {"Skills": "Swift, SwiftUI, Combine, CoreData", "Education": "Computer Engineering."},
    },
]

# Standard Campus Placement Job Description for Matching Benchmark
STANDARD_PILOT_JD = """
Junior Software Engineer - Placement Drive
Requirements:
Proficiency in Python or Java or JavaScript.
Experience with REST APIs, SQL databases (PostgreSQL or MySQL), and Git.
Familiarity with Docker, Linux, or Cloud environments is preferred.
Strong problem-solving skills and teamwork.
"""


class PilotBenchmarkRunner:
    """Executes the comprehensive 20-resume pilot evaluation for Sprint 7."""

    def __init__(self, orchestrator: ResumePipelineOrchestrator):
        self.orchestrator = orchestrator

    def run_benchmark(self) -> Dict[str, Any]:
        results: List[FullPipelineResult] = []
        latencies: List[float] = []
        scores: List[float] = []
        stage_times: Dict[str, List[float]] = {
            "extraction": [],
            "scoring": [],
            "matching": [],
            "fairness": [],
        }

        start_all = time.perf_counter()

        for candidate in PILOT_RESUME_CORPUS:
            res = self.orchestrator.execute_full_pipeline(
                raw_text=candidate["text"],
                sections=candidate["sections"],
                jd_text=STANDARD_PILOT_JD,
                target_role=f"{candidate['domain']} Engineer",
            )
            results.append(res)
            latencies.append(res.total_duration_ms)
            scores.append(res.scoring.composite_score)

            for metric in res.execution_metrics:
                if metric.stage_name in stage_times:
                    stage_times[metric.stage_name].append(metric.duration_ms)

        total_wall_clock = round((time.perf_counter() - start_all) * 1000, 2)
        avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
        avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0

        stage_averages = {
            stg: round(sum(times) / len(times), 2) if times else 0.0
            for stg, times in stage_times.items()
        }

        all_fair = all(
            r.fairness.is_fair if r.fairness else True
            for r in results
        )
        all_advisory = all(r.is_advisory for r in results)

        summary = PilotBenchmarkSummaryDTO(
            total_resumes_tested=len(results),
            average_duration_ms=avg_latency,
            average_composite_score=avg_score,
            fairness_parity_maintained=all_fair and all_advisory,
            stage_latency_breakdown=stage_averages,
        )

        return {
            "status": "COMPLETED",
            "summary": summary.model_dump(),
            "wall_clock_ms": total_wall_clock,
            "individual_evaluations_count": len(results),
        }
