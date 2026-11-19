from fastapi import FastAPI

from app.routers import auth, resumes
from app.routers.jobs import router as jobs_router
from app.routers.analysis import router as analysis_router

app = FastAPI(
    title="Resume Analyzer for College Placements",
    description="API for resume parsing, scoring and job matching",
    version="1.0.0",
)

# Existing routers
app.include_router(auth.router)
app.include_router(resumes.router)

# Sprint 3 routers
app.include_router(jobs_router)
app.include_router(analysis_router)


@app.get("/")
def root():
    return {
        "message": "Resume Analyzer API is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }