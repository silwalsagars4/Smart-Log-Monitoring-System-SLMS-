"""
Authentication routes: register, login, me.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database.postgres import get_db_session
from middleware.auth_middleware import get_current_user
from middleware.rate_limiter import limiter
from models.db_models import User
from models.schemas import UserRegister, UserLogin, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": str(user.id), "username": user.username, "role": user.role, "exp": expire},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, body: UserRegister, db: AsyncSession = Depends(get_db_session)):
    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")
    user = User(
        username=body.username,
        email=body.email,
        hashed_password=_hash_password(body.password),
        role="user",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: UserLogin, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if not user or not _verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    return TokenResponse(access_token=_create_token(user), role=user.role)


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
