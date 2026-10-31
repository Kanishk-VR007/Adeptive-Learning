from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user (Student or Teacher)"
)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account with a designated role (STUDENT or TEACHER).
    """
    existing_user = UserService.get_by_email(db, user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email address already exists."
        )
    return UserService.create(db, user_in)


@router.post(
    "/login",
    response_model=Token,
    summary="Login to obtain JWT access token (OAuth2 form compatible)"
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token login, accepts `username` (email) and `password`.
    Used by Swagger UI 'Authorize' button and standard form clients.
    """
    user = UserService.authenticate(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is inactive."
        )

    access_token = create_access_token(
        subject=user.id,
        extra_claims={"role": user.role.value, "email": user.email}
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post(
    "/login/json",
    response_model=Token,
    summary="Login using a JSON request body"
)
def login_json(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Authenticate using application/json body (email and password).
    """
    user = UserService.authenticate(db, email=credentials.email, password=credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is inactive."
        )

    access_token = create_access_token(
        subject=user.id,
        extra_claims={"role": user.role.value, "email": user.email}
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile"
)
def read_current_user(current_user: User = Depends(get_current_user)):
    """
    Fetch profile information and role permissions for the currently authenticated user.
    """
    return current_user
