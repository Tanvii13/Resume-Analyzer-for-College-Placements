from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt import InvalidTokenError
from pydantic import BaseModel, Field
import psycopg

from app.database import get_connection
from app.services.auth_service import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    email: str
    role: str


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest):
    full_name = request.full_name.strip()
    email = request.email.strip().lower()
    password = request.password

    if len(full_name) < 2:
        raise HTTPException(status_code=422, detail="Full name must contain at least 2 characters")

    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise HTTPException(status_code=422, detail="A valid email address is required")

    password_hashed = hash_password(password)

    try:
        with get_connection() as conn:
            with conn.transaction():
                user = conn.execute(
                    """
                    INSERT INTO users (full_name, email, password_hash)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (email) DO NOTHING
                    RETURNING id, email, is_active
                    """,
                    (full_name, email, password_hashed),
                ).fetchone()

                if user is None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="An account with this email already exists",
                    )

                role = conn.execute(
                    "SELECT id FROM roles WHERE name = %s",
                    ("student",),
                ).fetchone()

                if role is None:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="The student role is not configured",
                    )

                conn.execute(
                    """
                    INSERT INTO user_roles (user_id, role_id)
                    VALUES (%s, %s)
                    """,
                    (user[0], role[0]),
                )

    except psycopg.Error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create the account",
        )

    return UserResponse(email=user[1], role="student")


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    email = form_data.username.strip().lower()

    try:
        with get_connection() as conn:
            user = conn.execute(
                """
                SELECT u.id, u.email, u.password_hash, u.is_active
                FROM users AS u
                WHERE u.email = %s
                """,
                (email,),
            ).fetchone()

    except psycopg.Error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to access the user database",
        )

    if (
        user is None
        or not user[3]
        or not verify_password(form_data.password, user[2])
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=user[1])
    return {"access_token": token, "token_type": "bearer"}


def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    try:
        payload = decode_access_token(token)
        email = payload.get("sub")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        with get_connection() as conn:
            user = conn.execute(
                """
                SELECT u.email, u.is_active, r.name
                FROM users AS u
                JOIN user_roles AS ur ON ur.user_id = u.id
                JOIN roles AS r ON r.id = ur.role_id
                WHERE u.email = %s
                ORDER BY CASE r.name
                    WHEN 'admin' THEN 1
                    WHEN 'placement_officer' THEN 2
                    ELSE 3
                END
                LIMIT 1
                """,
                (email,),
            ).fetchone()

    except psycopg.Error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to access the user database",
        )

    if user is None or not user[1]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserResponse(email=user[0], role=user[2])


@router.get("/me", response_model=UserResponse)
def read_current_user(
    current_user: UserResponse = Depends(get_current_user),
):
    return current_user
