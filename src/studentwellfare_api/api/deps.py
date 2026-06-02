from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from studentwellfare_api.database import get_db
from studentwellfare_api.models import Student, User, UserSession
from studentwellfare_api.services import now_utc


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header.",
        )

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty bearer token.",
        )

    session_record = db.scalar(
        select(UserSession).where(
            UserSession.access_token == token,
            UserSession.is_revoked.is_(False),
        )
    )
    if session_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is invalid or has been revoked.",
        )

    if session_record.access_token_expires_at and session_record.access_token_expires_at < now_utc():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please sign in again.",
        )

    user = db.get(User, session_record.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account no longer exists.",
        )
    return user


def get_owned_student(
    student_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Student:
    student = db.get(Student, student_id)
    if student is None or student.parent_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found.",
        )
    return student
