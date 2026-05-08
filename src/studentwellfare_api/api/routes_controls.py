from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from studentwellfare_api.database import get_db
from studentwellfare_api.models import AppRule, ExtraTimeRequest, InstallRequest, Student, User, WebsiteRule
from studentwellfare_api.schemas import (
    AppRuleResponse,
    AppRuleUpsert,
    ExtraTimeRequestCreate,
    ExtraTimeRequestResponse,
    ExtraTimeRequestReview,
    InstallRequestCreate,
    InstallRequestResponse,
    InstallRequestReview,
    WebsiteRuleResponse,
    WebsiteRuleUpsert,
)
from studentwellfare_api.services import (
    create_extra_time_request,
    create_install_request,
    replace_app_rules,
    replace_website_rules,
    review_extra_time_request,
    review_install_request,
    update_app_rule_record,
    update_website_rule_record,
)

router = APIRouter(tags=["controls"])


@router.put("/students/{student_id}/app-rules", response_model=list[AppRuleResponse])
def update_app_rules(
    student_id: str,
    payload: list[AppRuleUpsert],
    db: Session = Depends(get_db),
) -> list[AppRule]:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")
    return replace_app_rules(db, student_id=student_id, rules=payload)


@router.post("/students/{student_id}/app-rules", response_model=list[AppRuleResponse], status_code=status.HTTP_201_CREATED)
def create_app_rules(
    student_id: str,
    payload: list[AppRuleUpsert],
    db: Session = Depends(get_db),
) -> list[AppRule]:
    return update_app_rules(student_id=student_id, payload=payload, db=db)


@router.patch("/app-rules/{rule_id}", response_model=AppRuleResponse)
def patch_app_rule(rule_id: int, payload: AppRuleUpsert, db: Session = Depends(get_db)) -> AppRule:
    rule = db.get(AppRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App rule not found.")
    return update_app_rule_record(
        db,
        rule=rule,
        app_name=payload.app_name,
        package_name=payload.package_name,
        daily_limit_minutes=payload.daily_limit_minutes,
        is_blocked=payload.is_blocked,
    )


@router.put("/students/{student_id}/website-rules", response_model=list[WebsiteRuleResponse])
def update_website_rules(
    student_id: str,
    payload: list[WebsiteRuleUpsert],
    db: Session = Depends(get_db),
) -> list[WebsiteRule]:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")
    return replace_website_rules(db, student_id=student_id, rules=payload)


@router.post("/students/{student_id}/website-rules", response_model=list[WebsiteRuleResponse], status_code=status.HTTP_201_CREATED)
def create_website_rules(
    student_id: str,
    payload: list[WebsiteRuleUpsert],
    db: Session = Depends(get_db),
) -> list[WebsiteRule]:
    return update_website_rules(student_id=student_id, payload=payload, db=db)


@router.patch("/website-rules/{rule_id}", response_model=WebsiteRuleResponse)
def patch_website_rule(
    rule_id: int,
    payload: WebsiteRuleUpsert,
    db: Session = Depends(get_db),
) -> WebsiteRule:
    rule = db.get(WebsiteRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website rule not found.")
    return update_website_rule_record(
        db,
        rule=rule,
        domain=payload.domain,
        category=payload.category,
        rule_type=payload.rule_type,
    )


@router.get("/students/{student_id}/extra-time-requests", response_model=list[ExtraTimeRequestResponse])
def list_extra_time_requests(student_id: str, db: Session = Depends(get_db)) -> list[ExtraTimeRequest]:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    return db.scalars(
        select(ExtraTimeRequest)
        .where(ExtraTimeRequest.student_id == student_id)
        .order_by(desc(ExtraTimeRequest.created_at))
        .limit(50)
    ).all()


@router.post("/students/{student_id}/extra-time-requests", response_model=ExtraTimeRequestResponse)
def create_extra_time_request_endpoint(
    student_id: str,
    payload: ExtraTimeRequestCreate,
    db: Session = Depends(get_db),
) -> ExtraTimeRequest:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    return create_extra_time_request(
        db,
        student_id=student_id,
        device_id=payload.device_id,
        package_name=payload.package_name,
        requested_minutes=payload.requested_minutes,
        reason=payload.reason,
    )


@router.post("/extra-time/request", response_model=ExtraTimeRequestResponse, status_code=status.HTTP_201_CREATED)
def create_extra_time_request_alias(
    payload: ExtraTimeRequestCreate,
    student_id: str,
    db: Session = Depends(get_db),
) -> ExtraTimeRequest:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")
    return create_extra_time_request_endpoint(student_id=student_id, payload=payload, db=db)


@router.patch("/extra-time-requests/{request_id}", response_model=ExtraTimeRequestResponse)
def review_extra_time_request_endpoint(
    request_id: int,
    payload: ExtraTimeRequestReview,
    db: Session = Depends(get_db),
) -> ExtraTimeRequest:
    request_record = db.get(ExtraTimeRequest, request_id)
    if request_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extra time request not found.")

    user = db.get(User, payload.approved_by)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approver not found.")

    return review_extra_time_request(
        db,
        request_record=request_record,
        approved_by=user.id,
        status=payload.status,
    )


@router.post("/extra-time/{request_id}/approve", response_model=ExtraTimeRequestResponse)
def approve_extra_time_request(
    request_id: int,
    approved_by: str,
    db: Session = Depends(get_db),
) -> ExtraTimeRequest:
    return review_extra_time_request_endpoint(
        request_id=request_id,
        payload=ExtraTimeRequestReview(approved_by=approved_by, status="approved"),
        db=db,
    )


@router.post("/extra-time/{request_id}/reject", response_model=ExtraTimeRequestResponse)
def reject_extra_time_request(
    request_id: int,
    approved_by: str,
    db: Session = Depends(get_db),
) -> ExtraTimeRequest:
    return review_extra_time_request_endpoint(
        request_id=request_id,
        payload=ExtraTimeRequestReview(approved_by=approved_by, status="rejected"),
        db=db,
    )


@router.get("/students/{student_id}/install-requests", response_model=list[InstallRequestResponse])
def list_install_requests(student_id: str, db: Session = Depends(get_db)) -> list[InstallRequest]:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    return db.scalars(
        select(InstallRequest)
        .where(InstallRequest.student_id == student_id)
        .order_by(desc(InstallRequest.created_at))
        .limit(50)
    ).all()


@router.post("/students/{student_id}/install-requests", response_model=InstallRequestResponse, status_code=status.HTTP_201_CREATED)
def create_install_request_endpoint(
    student_id: str,
    payload: InstallRequestCreate,
    db: Session = Depends(get_db),
) -> InstallRequest:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    return create_install_request(
        db,
        student_id=student_id,
        device_id=payload.device_id,
        package_name=payload.package_name,
        app_name=payload.app_name,
        reason=payload.reason,
    )


@router.patch("/install-requests/{request_id}", response_model=InstallRequestResponse)
def review_install_request_endpoint(
    request_id: int,
    payload: InstallRequestReview,
    db: Session = Depends(get_db),
) -> InstallRequest:
    request_record = db.get(InstallRequest, request_id)
    if request_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Install request not found.")

    user = db.get(User, payload.approved_by)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approver not found.")

    return review_install_request(
        db,
        request_record=request_record,
        approved_by=user.id,
        status=payload.status,
    )
