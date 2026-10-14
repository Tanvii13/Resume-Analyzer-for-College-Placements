from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.routers.auth import router as auth_router
from app.routers.resumes import router as resumes_router
from app.services.resume_parser import ResumeParsingError

app = FastAPI(
    title="Resume Analyzer API",
    description="Backend API for the Resume Analyzer for College Placements project.",
    version="0.1.0",
)


@app.exception_handler(ResumeParsingError)
async def resume_parsing_exception_handler(request: Request, exc: ResumeParsingError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.message,
            "error_code": exc.error_code,
        },
    )


app.include_router(auth_router)
app.include_router(resumes_router)


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
