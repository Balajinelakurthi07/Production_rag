import uuid
from typing import List
from dataclasses import dataclass
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.core.db import get_db
from app.core.auth import decode_access_token
from app.models.user import User, Membership

# OAuth2 scheme: Tells FastAPI to extract tokens from Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)


@dataclass
class AuthenticatedUserContext:
    """Carries the authenticated user and their authorized department boundaries."""
    user: User
    department_ids: List[uuid.UUID]


async def get_current_user_context(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> AuthenticatedUserContext:
    """
    Validates JWT and fetches the user's active department memberships directly from DB.
    Guarantees that access control boundaries can NEVER be bypassed by client prompts.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id_str: str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    # 1. Fetch user from DB
    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user account"
        )

    # 2. Fetch the user's authorized departments from the memberships table
    membership_query = select(Membership.department_id).where(Membership.user_id == user.id)
    dept_result = await db.execute(membership_query)
    allowed_department_ids = list(dept_result.scalars().all())

    return AuthenticatedUserContext(
        user=user,
        department_ids=allowed_department_ids
    )

