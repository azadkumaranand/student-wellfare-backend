from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from studentwellfare_api.database import get_db
from studentwellfare_api.models import User
from studentwellfare_api.schemas import (
    AuthLogoutRequest,
    AuthLoginRequest,
    AuthLoginResponse,
    AuthRefreshRequest,
    ParentPinVerifyRequest,
    ParentPinVerifyResponse,
)
from studentwellfare_api.services import (
    issue_user_session,
    refresh_user_session,
    revoke_user_session,
    verify_parent_pin,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


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
    db: Session = Depends(get_db),
) -> ParentPinVerifyResponse:
    from studentwellfare_api.models import Student
    
    user = None
    if payload.user_id:
        user = db.get(User, payload.user_id)
    elif payload.student_id:
        student = db.get(Student, payload.student_id)
        if student:
            user = student.parent
            
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    
    return ParentPinVerifyResponse(valid=verify_parent_pin(payload.pin, user.parent_pin_hash))
