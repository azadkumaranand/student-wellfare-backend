from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi import HTTPException

from studentwellfare_api.api.deps import get_current_user, get_owned_student
from studentwellfare_api.database import get_db
from studentwellfare_api.models import AppRule, Student, UsageLog, User, WebsiteRule
from studentwellfare_api.schemas import (
    RulesResponse,
    StudentCreateRequest,
    StudentDashboardResponse,
    StudentListItemResponse,
    StudentSummary,
    StudentUpdateRequest,
    UsageLogResponse,
    UsageTodayResponse,
    UsageWeeklyResponse,
)
from studentwellfare_api.services import (
    create_student_record,
    get_student_dashboard,
    get_student_summary,
    get_usage_today_report,
    get_usage_weekly_report,
    list_students_with_status,
    update_student_record,
)

router = APIRouter(prefix="/students", tags=["students"])


@router.get("", response_model=list[StudentListItemResponse])
def list_students(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[StudentListItemResponse]:
    return list_students_with_status(db, parent_id=current_user.id)


@router.post("", response_model=StudentSummary, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: StudentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StudentSummary:
    payload = payload.model_copy(update={"parent_id": current_user.id})
    student = create_student_record(db, payload=payload)
    return get_student_summary(student)


@router.patch("/{student_id}", response_model=StudentSummary)
def update_student(
    payload: StudentUpdateRequest,
    student: Student = Depends(get_owned_student),
    db: Session = Depends(get_db),
) -> StudentSummary:
    updated = update_student_record(db, student=student, payload=payload)
    return get_student_summary(updated)


# NOTE: these GET-by-id endpoints are called by the student device itself, which
# has no parent auth. They remain open; security comes from the fact that a
# student_id is only obtained via the pairing flow.
def _load_student_or_404(student_id: str, db: Session) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    return student


@router.get("/{student_id}/dashboard", response_model=StudentDashboardResponse)
def student_dashboard(
    student_id: str,
    db: Session = Depends(get_db),
) -> StudentDashboardResponse:
    return get_student_dashboard(db, _load_student_or_404(student_id, db))


@router.get("/{student_id}/rules", response_model=RulesResponse)
def student_rules(
    student_id: str,
    db: Session = Depends(get_db),
) -> RulesResponse:
    _load_student_or_404(student_id, db)
    app_rules = db.scalars(select(AppRule).where(AppRule.student_id == student_id)).all()
    website_rules = db.scalars(
        select(WebsiteRule).where(WebsiteRule.student_id == student_id)
    ).all()

    return RulesResponse(
        student_id=student_id,
        app_rules=app_rules,
        website_rules=website_rules,
    )


@router.get("/{student_id}/usage-logs", response_model=list[UsageLogResponse])
def student_usage_logs(
    student_id: str,
    db: Session = Depends(get_db),
) -> list[UsageLog]:
    _load_student_or_404(student_id, db)
    return db.scalars(
        select(UsageLog).where(UsageLog.student_id == student_id).order_by(UsageLog.created_at.desc()).limit(200)
    ).all()


@router.get("/{student_id}/usage/today", response_model=UsageTodayResponse)
def student_usage_today(
    student_id: str,
    db: Session = Depends(get_db),
) -> UsageTodayResponse:
    _load_student_or_404(student_id, db)
    return get_usage_today_report(db, student_id=student_id)


@router.get("/{student_id}/usage/weekly", response_model=UsageWeeklyResponse)
def student_usage_weekly(
    student_id: str,
    db: Session = Depends(get_db),
) -> UsageWeeklyResponse:
    _load_student_or_404(student_id, db)
    return get_usage_weekly_report(db, student_id=student_id)
