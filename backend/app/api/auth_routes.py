from __future__ import annotations

from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.auth.security import (
    get_password_hash,
    create_access_token,
    authenticate_user,
    get_current_user,
    require_roles,
)
from app.models.db_models import User
from app.models.dto import (
    UserCreate,
    UserResponse,
    Token,
)

router = APIRouter()


@router.post("/auth/register", response_model=UserResponse)
def register_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
):
    """
    Реєстрація нового користувача.

    Для спрощення диплома всі реєстрації отримують роль 'operator'.
    Першого адміна можна створити вручну в БД.
    """
    existing = (
        db.query(User)
        .filter(User.email == payload.email)
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Користувач із таким email вже існує",
        )

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=get_password_hash(payload.password),
        role="operator",
        is_active=True,
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Користувач із таким email вже існує",
        )
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не вдалося створити користувача",
        )

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post("/auth/login", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Логін. Повертає JWT-токен.
    """
    user = authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невірний email або пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=60),
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/auth/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_user),
):
    """
    Повертає дані поточного користувача.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )


@router.get("/auth/users", response_model=List[UserResponse])
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    """
    Список усіх користувачів (тільки для admin).
    """
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        UserResponse(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            is_active=u.is_active,
            created_at=u.created_at,
        )
        for u in users
    ]
