"""
FastAPI routes for user management.

Provides REST API endpoints for user authentication:
- User registration
- User login (authentication)
- Get current user information
"""

from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError

from src.core.logging import get_logger
from src.modules.users.dependencies import get_user_repository

from .dependencies import CurrentUser
from .schemas import TokenResponse, UserCreate, UserLogin, UserResponse
from .utils import create_access_token, hash_password, verify_password

# Initialize logger
logger = get_logger("users.routes")

# Create router
router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=HTTPStatus.CREATED,
    summary="Register a new user",
    description="Create a new user account with email, password, and Telegram alias",
)
async def register_user(
    user_data: UserCreate,
    repo=Depends(get_user_repository),
) -> UserResponse:
    """
    Register a new user in the system.

    Args:
        user_data: User registration data (email, password, telegram_alias)
        session: Database session

    Returns:
        UserResponse: Created user information

    Raises:
        HTTPException 400: If email or telegram_alias already exists
        HTTPException 500: If database error occurs
    """
    logger.info(
        f"Registration attempt for email: {user_data.email}, "
        f"telegram: @{user_data.telegram_alias}"
    )

    try:
        # Hash the password
        hashed_password = hash_password(user_data.password)

        # Create user in database
        user = await repo.create_user(
            email=user_data.email,
            hashed_password=hashed_password,
            telegram_alias=user_data.telegram_alias,
        )

        logger.info(f"User registered successfully: {user.id} ({user.email})")

        return UserResponse.model_validate(user)

    except IntegrityError as e:
        logger.warning(f"Registration failed - duplicate data: {str(e)}")

        # Determine which field is duplicate
        error_msg = str(e)
        if "email" in error_msg.lower():
            detail = "Email already registered"
        elif "telegram_alias" in error_msg.lower():
            detail = "Telegram alias already registered"
        else:
            detail = "User with this data already exists"

        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=detail,
        )

    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Failed to register user",
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=HTTPStatus.OK,
    summary="User login",
    description="Authenticate user and receive JWT access token",
)
async def login_user(
    credentials: UserLogin,
    repo=Depends(get_user_repository),
) -> TokenResponse:
    """
    Authenticate user and return JWT access token.

    Args:
        credentials: User login credentials (email, password)
        repo: User repository

    Returns:
        TokenResponse: JWT access token

    Raises:
        HTTPException 401: If credentials are invalid
    """
    logger.info(f"Login attempt for email: {credentials.email}")

    # Get user by email
    user = await repo.get_user_by_email(credentials.email)

    # Verify user exists and password is correct
    if not user or not verify_password(credentials.password, user.hashed_password):
        logger.warning(f"Login failed for email: {credentials.email}")
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
    )

    logger.info(f"User logged in successfully: {user.id} ({user.email})")

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=HTTPStatus.OK,
    summary="Get current user",
    description="Get information about the currently authenticated user",
)
async def get_current_user_info(
    current_user: CurrentUser,
) -> UserResponse:
    """
    Get current authenticated user information.

    Args:
        current_user: Current authenticated user (from JWT token)

    Returns:
        UserResponse: Current user information
    """
    logger.info(f"User info requested: {current_user.id} ({current_user.email})")

    return UserResponse.model_validate(current_user)
