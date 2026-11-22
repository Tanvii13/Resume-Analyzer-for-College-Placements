"""PostgreSQL persistence for job descriptions, match results and improvement logs."""
from uuid import UUID
from psycopg.types.json import Jsonb
from app.database import get_connection

class ResourceNotFoundError(Exception):
    pass

def _uuid(value):
    try:
        return UUID(str(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("Invalid UUID") from exc

def _array(value, field):
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    return value

def save_job_description(user_id, data):
    user_id = _uuid(user_id)
    title = str(data.get("title", "")).strip()
    description = str(data.get("description", "")).strip()
    if not title or not description:
        raise ValueError("title and description are required")
    required = _array(data.get("required_skills", []), "required_skills")
    optional = _array(data.get("optional_skills", []), "optional_skills")
    sql = """INSERT INTO job_descriptions
      (user_id,title,company,description,required_skills,optional_skills)
      VALUES (%s,%s,%s,%s,%s,%s) RETURNING id,title,company,description,
      required_skills,optional_skills,created_at"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,title,data.get("company"),description,
                              Jsonb(required),Jsonb(optional)))
            row = cur.fetchone()
    return _job_row(row)

def _job_row(row):
    keys = ("id","title","company","description","required_skills","optional_skills","created_at")
    result = dict(zip(keys, row))
    result["id"] = str(result["id"])
    return result

def get_job_description(job_id, user_id):
    sql = """SELECT id,title,company,description,required_skills,optional_skills,created_at
             FROM job_descriptions WHERE id=%s AND user_id=%s"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (_uuid(job_id),_uuid(user_id)))
            row = cur.fetchone()
    if row is None: raise ResourceNotFoundError("Job description not found")
    return _job_row(row)

def get_all_job_descriptions(user_id):
    sql = """SELECT id,title,company,description,required_skills,optional_skills,created_at
             FROM job_descriptions WHERE user_id=%s ORDER BY created_at DESC"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (_uuid(user_id),))
            rows = cur.fetchall()
    return [_job_row(row) for row in rows]

def save_match_result(resume_id, job_id, user_id, result):
    resume_id, job_id, user_id = _uuid(resume_id), _uuid(job_id), _uuid(user_id)
    sql = """INSERT INTO resume_jd_matches
      (resume_id,job_description_id,user_id,match_percentage,matched_skills,missing_skills,optional_skills_found)
      SELECT r.id,j.id,%s,%s,%s,%s,%s
      FROM resumes r JOIN job_descriptions j ON j.id=%s AND j.user_id=%s
      WHERE r.id=%s AND r.user_id=%s
      RETURNING id,match_percentage,matched_skills,missing_skills,optional_skills_found,created_at"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,result["match_percentage"],Jsonb(result["matched_skills"]),
                              Jsonb(result["missing_skills"]),Jsonb(result["optional_skills_found"]),
                              job_id,user_id,resume_id,user_id))
            row = cur.fetchone()
    if row is None: raise ResourceNotFoundError("Resume or job description not found for this user")
    return {"id":str(row[0]),"match_percentage":float(row[1]),"matched_skills":row[2],
            "missing_skills":row[3],"optional_skills_found":row[4],"created_at":row[5]}

def get_match_results(resume_id, user_id):
    sql = """SELECT m.id,m.job_description_id,m.match_percentage,m.matched_skills,
                    m.missing_skills,m.optional_skills_found,m.created_at
             FROM resume_jd_matches m JOIN resumes r ON r.id=m.resume_id
             WHERE m.resume_id=%s AND m.user_id=%s AND r.user_id=%s
             ORDER BY m.created_at DESC"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (_uuid(resume_id),_uuid(user_id),_uuid(user_id)))
            rows = cur.fetchall()
    return [{"id":str(r[0]),"job_description_id":str(r[1]),"match_percentage":float(r[2]),
             "matched_skills":r[3],"missing_skills":r[4],"optional_skills_found":r[5],
             "created_at":r[6]} for r in rows]

def save_improvement_log(resume_id, user_id, score_result, suggestions=None):
    sql = """INSERT INTO resume_improvement_logs
      (resume_id,user_id,overall_score,issues,suggestions)
      SELECT r.id,%s,%s,%s,%s FROM resumes r
      WHERE r.id=%s AND r.user_id=%s RETURNING id,created_at"""
    warnings = score_result.get("warnings", [])
    suggestions = suggestions if suggestions is not None else []
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (_uuid(user_id),score_result.get("overall_score"),
                              Jsonb(warnings),Jsonb(_array(suggestions,"suggestions")),
                              _uuid(resume_id),_uuid(user_id)))
            row = cur.fetchone()
    if row is None: raise ResourceNotFoundError("Resume not found for this user")
    return {"id":str(row[0]),"created_at":row[1]}

def get_improvement_logs(resume_id, user_id):
    sql = """SELECT l.id,l.overall_score,l.issues,l.suggestions,l.created_at
             FROM resume_improvement_logs l JOIN resumes r ON r.id=l.resume_id
             WHERE l.resume_id=%s AND l.user_id=%s AND r.user_id=%s
             ORDER BY l.created_at DESC"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (_uuid(resume_id),_uuid(user_id),_uuid(user_id)))
            rows = cur.fetchall()
    return [{"id":str(r[0]),"overall_score":float(r[1]) if r[1] is not None else None,
             "issues":r[2],"suggestions":r[3],"created_at":r[4]} for r in rows]
