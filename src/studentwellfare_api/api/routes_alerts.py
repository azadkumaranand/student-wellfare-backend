from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from studentwellfare_api.database import get_db
from studentwellfare_api.models import Alert, Student
from studentwellfare_api.schemas import AlertCreateRequest, AlertResponse
from studentwellfare_api.services import create_alert, mark_alert_read

router = APIRouter(tags=["alerts"])


@router.post("/alerts", response_model=AlertResponse)
def create_alert_endpoint(
    payload: AlertCreateRequest,
    db: Session = Depends(get_db),
) -> AlertResponse:
    student = db.get(Student, payload.student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    return create_alert(
        db,
        student_id=payload.student_id,
        device_id=payload.device_id,
        event_type=payload.type,
        severity=payload.severity,
        message=payload.message,
        metadata_json=payload.metadata_json,
    )


@router.get("/students/{student_id}/alerts", response_model=list[AlertResponse])
def list_student_alerts(student_id: str, db: Session = Depends(get_db)) -> list[AlertResponse]:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    return db.scalars(
        select(Alert).where(Alert.student_id == student_id).order_by(desc(Alert.created_at)).limit(50)
    ).all()


@router.patch("/alerts/{alert_id}/read", response_model=AlertResponse)
def mark_alert_read_endpoint(alert_id: int, db: Session = Depends(get_db)) -> AlertResponse:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")

    if alert.read_at is not None:
        return alert

    return mark_alert_read(db, alert=alert)
