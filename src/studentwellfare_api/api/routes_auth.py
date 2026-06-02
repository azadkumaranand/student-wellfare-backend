from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from studentwellfare_api.api.deps import get_current_user
from studentwellfare_api.database import get_db
from studentwellfare_api.models import User
from studentwellfare_api.schemas import (
    AuthLogoutRequest,
    AuthLoginRequest,
    AuthLoginResponse,
    AuthRefreshRequest,
    AuthRegisterRequest,
    ParentPinUpdateRequest,
    ParentPinUpdateResponse,
    ParentPinVerifyRequest,
    ParentPinVerifyResponse,
)
from studentwellfare_api.services import (
    hash_parent_pin,
    hash_password,
    issue_user_session,
    refresh_user_session,
    revoke_user_session,
    verify_parent_pin,
    verify_password,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthLoginResponse, status_code=status.HTTP_201_CREATED)
def register(payload: AuthRegisterRequest, db: Session = Depends(get_db)) -> AuthLoginResponse:
    email = payload.email.strip().lower()
    if "@" not in email or "." not in email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Enter a valid email.")

    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        id=f"usr_{uuid.uuid4().hex[:12]}",
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        parent_pin_hash=None,
        role="parent",
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return issue_user_session(db, user=user)


@router.post("/login", response_model=AuthLoginResponse)
def login(payload: AuthLoginRequest, db: Session = Depends(get_db)) -> AuthLoginResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    return issue_user_session(db, user=user)


@router.post("/refresh", response_model=AuthLoginResponse)
def refresh(payload: AuthRefreshRequest, db: Session = Depends(get_db)) -> AuthLoginResponse:
    response = refresh_user_session(db, refresh_token=payload.refresh_token)
    if response is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is invalid.")
    return response


@router.post("/logout")
def logout(payload: AuthLogoutRequest, db: Session = Depends(get_db)) -> dict[str, bool]:
    return {"ok": revoke_user_session(db, refresh_token=payload.refresh_token)}


@router.post("/verify-parent-pin", response_model=ParentPinVerifyResponse)
def verify_parent_pin_endpoint(
    payload: ParentPinVerifyRequest,
    current_user: User = Depends(get_current_user),
) -> ParentPinVerifyResponse:
    return ParentPinVerifyResponse(valid=verify_parent_pin(payload.pin, current_user.parent_pin_hash))


@router.post("/set-parent-pin", response_model=ParentPinUpdateResponse)
def set_parent_pin_endpoint(
    payload: ParentPinUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ParentPinUpdateResponse:
    if not payload.new_pin.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PIN must contain only digits.",
        )

    current_user.parent_pin_hash = hash_parent_pin(payload.new_pin)
    db.commit()
    return ParentPinUpdateResponse(ok=True)
