from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.db import get_db
from app.core.auth import verify_password, get_password_hash, create_access_token
from app.core.security import get_current_user_context, AuthenticatedUserContext
from app.models.user import User
from app.schemas.auth import UserCreate, UserLogin, Token, UserResponse, UserWithDepartments, DepartmentOut

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Registers a new user account with a hashed password."""
    # Check if user already exists
    existing = await db.execute(select(User).where(User.email == user_in.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )

    # Hash the password and create user
    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
async def login_user(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """Verifies credentials and returns a signed JWT access token."""
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user account")

    access_token = create_access_token(subject=user.id)
    return Token(access_token=access_token)


@router.get("/me", response_model=UserWithDepartments)
async def read_current_user(
    auth_ctx: AuthenticatedUserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db)
):
    """Returns the authenticated user's profile and their authorized department list."""
    from app.models.user import Department, Membership

    # Fetch full department details
    dept_query = (
        select(Department)
        .join(Membership, Membership.department_id == Department.id)
        .where(Membership.user_id == auth_ctx.user.id)
    )
    res = await db.execute(dept_query)
    departments = res.scalars().all()

    return UserWithDepartments(
        id=auth_ctx.user.id,
        email=auth_ctx.user.email,
        full_name=auth_ctx.user.full_name,
        is_active=auth_ctx.user.is_active,
        created_at=auth_ctx.user.created_at,
        departments=[DepartmentOut.model_validate(d) for d in departments]
    )

