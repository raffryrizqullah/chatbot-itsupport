"""
Authentication endpoints for user login and registration.

Provides endpoints for user authentication, registration, and profile management.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models import User, UserRole
from app.models.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    ErrorResponse,
)
from app.services.auth import login_user, register_user
from app.core.dependencies import get_current_active_user, require_role
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/login",
    response_model=TokenResponse,
    tags=["auth"],
    responses={
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """
    Login with username and password.

    Returns JWT access token on successful authentication.

    Args:
        request: Login credentials (username and password).
        db: Database session.

    Returns:
        TokenResponse with access token and user information.

    Raises:
        HTTPException: If credentials are invalid.
    """
    try:
        logger.info(f"Login attempt for user: {request.username}")

        result = await login_user(db, request.username, request.password)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.info(f"User {request.username} logged in successfully")
        return TokenResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        msg = f"Login failed: {str(e)}"
        logger.error(msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=msg,
        )


@router.post(
    "/register",
    response_model=UserResponse,
    tags=["auth"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> UserResponse:
    """
    Register a new user (Admin only).

    Creates a new user account. Only accessible by admin users.

    Args:
        request: User registration data.
        db: Database session.
        current_user: Current authenticated admin user.

    Returns:
        UserResponse with created user information.

    Raises:
        HTTPException: If username/email exists or validation fails.
    """
    try:
        logger.info(f"Registration attempt for username: {request.username}")

        # Validate role
        try:
            role = UserRole(request.role.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {request.role}. Must be: admin, lecturer, or student",
            )

        # Create user
        user = await register_user(
            db=db,
            username=request.username,
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            role=role,
        )

        logger.info(f"User {user.username} registered successfully by admin {current_user.username}")

        return UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        msg = f"Registration failed: {str(e)}"
        logger.error(msg)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )


@router.get(
    "/me",
    response_model=UserResponse,
    tags=["auth"],
    responses={
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """
    Get current authenticated user information.

    Requires valid JWT token in Authorization header.

    Args:
        current_user: Current authenticated user.

    Returns:
        UserResponse with user information.

    Raises:
        HTTPException: If not authenticated.
    """
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )
