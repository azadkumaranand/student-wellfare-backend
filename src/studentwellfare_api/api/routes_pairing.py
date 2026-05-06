from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from studentwellfare_api.database import get_db
from studentwellfare_api.models import AppRule, Device, PairingCode, Student, WebsiteRule
from studentwellfare_api.schemas import (
    DeviceRegisterRequest,
    DeviceResponse,
    PairingCodeCreateRequest,
    PairingCodeResponse,
    PairingVerifyRequest,
    PairingVerifyResponse,
    RulesResponse,
)
from studentwellfare_api.services import (
    generate_pairing_code,
    get_student_dashboard,
    get_student_summary,
    now_utc,
)

router = APIRouter(tags=["pairing"])


@router.post("/pairing/create-code", response_model=PairingCodeResponse)
def create_pairing_code(
    payload: PairingCodeCreateRequest,
    db: Session = Depends(get_db),
) -> PairingCodeResponse:
    student = db.get(Student, payload.student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    pairing_code = PairingCode(
        code=generate_pairing_code(),
        student_id=student.id,
        expires_at=now_utc() + timedelta(minutes=payload.expires_in_minutes),
        is_active=True,
        created_at=now_utc(),
    )
    db.add(pairing_code)
    db.commit()

    return PairingCodeResponse(
        student_id=student.id,
        pairing_code=pairing_code.code,
        expires_at=pairing_code.expires_at,
    )


@router.post("/pairing/verify-code", response_model=PairingVerifyResponse)
def verify_pairing_code(
    payload: PairingVerifyRequest,
    db: Session = Depends(get_db),
) -> PairingVerifyResponse:
    pairing = db.get(PairingCode, payload.pairing_code.strip().upper())
    if pairing is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pairing code is invalid. Please request a new one from your parent or admin.",
        )
    if not pairing.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This pairing code has already been used. Please ask your parent or admin for a new one.",
        )
    if pairing.expires_at < now_utc():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pairing code has expired. Please request a new one from your parent or admin.",
        )

    student = db.get(Student, pairing.student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    device = Device(
        id=f"device_{uuid.uuid4().hex[:12]}",
        student_id=student.id,
        device_name=payload.device_name,
        android_id=payload.android_id,
        fcm_token=payload.fcm_token,
        app_version=payload.app_version,
        protection_status="SETUP_REQUIRED",
        last_seen_at=now_utc(),
        created_at=now_utc(),
    )
    db.add(device)
    pairing.is_active = False
    db.commit()
    db.refresh(device)

    app_rules = db.scalars(select(AppRule).where(AppRule.student_id == student.id)).all()
    website_rules = db.scalars(
        select(WebsiteRule).where(WebsiteRule.student_id == student.id)
    ).all()

    return PairingVerifyResponse(
        student=get_student_summary(student),
        device=device,
        rules=RulesResponse(
            student_id=student.id,
            app_rules=app_rules,
            website_rules=website_rules,
        ),
        dashboard=get_student_dashboard(db, student),
    )


@router.post("/devices/register", response_model=DeviceResponse)
def register_device(
    payload: DeviceRegisterRequest,
    db: Session = Depends(get_db),
) -> DeviceResponse:
    student = db.get(Student, payload.student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    device = Device(
        id=f"device_{uuid.uuid4().hex[:12]}",
        student_id=student.id,
        device_name=payload.device_name,
        android_id=payload.android_id,
        fcm_token=payload.fcm_token,
        app_version=payload.app_version,
        protection_status="SETUP_REQUIRED",
        last_seen_at=now_utc(),
        created_at=now_utc(),
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device
