"""
Authentication endpoints for user login and registration.

Provides endpoints for user authentication, registration, and profile management.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
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
from app.core.rate_limit import limiter, RATE_LIMITS
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/login",
    response_model=TokenResponse,
    tags=["auth"],
    responses={
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
@limiter.limit(RATE_LIMITS["auth_login"])
async def login(
    request: Request,
    login_req: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
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
        logger.info(f"Login attempt for user: {login_req.username}")

        result = await login_user(db, login_req.username, login_req.password)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.info(f"User {login_req.username} logged in successfully")
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
    dependencies=[Depends(require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
@limiter.limit(RATE_LIMITS["auth_register"])
async def register(
    request: Request,
    register_req: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
) -> UserResponse:
    """
    Register a new user (Super Admin or Admin).

    Creates a new user account with role-based restrictions:
    - **Super Admin**: Can create any role (super_admin, admin, lecturer, student)
    - **Admin**: Can only create lecturer and student roles

    Args:
        request: User registration data.
        db: Database session.
        current_user: Current authenticated super admin or admin user.

    Returns:
        UserResponse with created user information.

    Raises:
        HTTPException: If username/email exists, validation fails, or insufficient permissions.
    """
    try:
        logger.info(f"Registration attempt for username: {register_req.username} by {current_user.username} (role: {current_user.role})")

        # Validate role
        try:
            requested_role = UserRole(register_req.role.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {register_req.role}. Must be: SUPER_ADMIN, ADMIN, LECTURER, or STUDENT (case-insensitive)",
            )

        # Validate role creation permissions
        if current_user.role == UserRole.SUPER_ADMIN:
            # Super Admin can create any role
            logger.info(f"Super Admin {current_user.username} creating user with role: {requested_role.value}")
        elif current_user.role == UserRole.ADMIN:
            # Admin can only create LECTURER and STUDENT
            if requested_role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
                logger.warning(
                    f"Admin {current_user.username} attempted to create {requested_role.value} user - DENIED"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin cannot create Super Admin or Admin users. Contact Super Admin for assistance.",
                )
            logger.info(f"Admin {current_user.username} creating user with role: {requested_role.value}")
        else:
            # Should not reach here due to dependency check, but defensive programming
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to create users",
            )

        role = requested_role

        # Create user
        user = await register_user(
            db=db,
            username=register_req.username,
            email=register_req.email,
            password=register_req.password,
            full_name=register_req.full_name,
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
