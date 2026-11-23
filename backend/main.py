
from fastapi import FastAPI

from app.routers.auth import router as auth_router
from app.routers.resumes import router as resumes_router

from app.routers.health import router as health_router
from app.routers.admin_audit import router as admin_audit_router
from app.routers.resume_insights import router as resume_insights_router
from app.routers.officer import router as officer_router
from app.routers.admin import router as admin_router
from app.routers.governance import router as governance_router
app = FastAPI(
    title="Resume Analyzer API",
    description="Backend API for the Resume Analyzer for College Placements project.",
    version="0.1.0",
)

app.include_router(auth_router)
app.include_router(resumes_router)

app.include_router(health_router)
app.include_router(admin_audit_router)
app.include_router(resume_insights_router)
app.include_router(officer_router)
app.include_router(admin_router)
app.include_router(governance_router)

@app.get("/")
def root():
    return {
        "message": "Resume Analyzer API is running",
        "status": "success",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "resume-analyzer-backend",
    }
