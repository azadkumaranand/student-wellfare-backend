from __future__ import annotations

import hashlib
import json
import secrets
import smtplib
import uuid
from datetime import datetime, timedelta
from email.message import EmailMessage
from urllib import error as urllib_error
from urllib import request as urllib_request

from sqlalchemy import desc, inspect, select, text
from sqlalchemy.orm import Session

from studentwellfare_api.database import engine
from studentwellfare_api.config import settings
from studentwellfare_api.models import (
    Alert,
    AppRule,
    Device,
    DeviceHeartbeat,
    ExtraTimeRequest,
    PairingCode,
    Student,
    UsageLog,
    User,
    UserSession,
    WebsiteRule,
)
from studentwellfare_api.schemas import (
    AppRuleUpsert,
    AuthLoginResponse,
    DashboardUsageCard,
    ExtraTimeRequestResponse,
    StudentCreateRequest,
    StudentDashboardResponse,
    StudentListItemResponse,
    StudentSummary,
    StudentUpdateRequest,
    UsagePackageSummary,
    UsageTodayResponse,
    UsageWeeklyDayResponse,
    UsageWeeklyResponse,
    UsageLogCreate,
    WebsiteRuleUpsert,
)


def now_utc() -> datetime:
    return datetime.utcnow()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def hash_parent_pin(pin: str) -> str:
    return hash_password(f"pin::{pin}")


def verify_parent_pin(pin: str, parent_pin_hash: str | None) -> bool:
    if not parent_pin_hash:
        return False
    return hash_parent_pin(pin) == parent_pin_hash


def generate_pairing_code() -> str:
    return f"SAFE-{secrets.randbelow(9000) + 1000}"


def issue_user_session(db: Session, *, user: User) -> AuthLoginResponse:
    session_record = UserSession(
        id=f"sess_{uuid.uuid4().hex[:16]}",
        user_id=user.id,
        refresh_token=secrets.token_urlsafe(32),
        is_revoked=False,
        created_at=now_utc(),
    )
    db.add(session_record)
    db.commit()

    return AuthLoginResponse(
        access_token=secrets.token_urlsafe(32),
        refresh_token=session_record.refresh_token,
        user_id=user.id,
        role=user.role,
        name=user.name,
    )


def refresh_user_session(db: Session, *, refresh_token: str) -> AuthLoginResponse | None:
    session_record = db.scalar(
        select(UserSession).where(UserSession.refresh_token == refresh_token, UserSession.is_revoked.is_(False))
    )
    if session_record is None:
        return None

    user = db.get(User, session_record.user_id)
    if user is None:
        return None

    session_record.is_revoked = True
    replacement = UserSession(
        id=f"sess_{uuid.uuid4().hex[:16]}",
        user_id=user.id,
        refresh_token=secrets.token_urlsafe(32),
        is_revoked=False,
        created_at=now_utc(),
    )
    db.add(replacement)
    db.commit()

    return AuthLoginResponse(
        access_token=secrets.token_urlsafe(32),
        refresh_token=replacement.refresh_token,
        user_id=user.id,
        role=user.role,
        name=user.name,
    )


def revoke_user_session(db: Session, *, refresh_token: str) -> bool:
    session_record = db.scalar(select(UserSession).where(UserSession.refresh_token == refresh_token))
    if session_record is None:
        return False

    session_record.is_revoked = True
    db.commit()
    return True


def seed_database(db: Session) -> None:
    parent = db.get(User, "parent_001")
    if parent is None:
        parent = User(
            id="parent_001",
            name=settings.seed_parent_name,
            email=settings.seed_parent_email,
            password_hash=hash_password(settings.seed_parent_password),
            parent_pin_hash=hash_parent_pin(settings.seed_parent_pin),
            role="parent",
            created_at=now_utc(),
        )
        db.add(parent)
    else:
        parent.name = settings.seed_parent_name
        parent.email = settings.seed_parent_email
        parent.password_hash = hash_password(settings.seed_parent_password)
        parent.parent_pin_hash = hash_parent_pin(settings.seed_parent_pin)
        parent.role = "parent"

    db.commit()


def get_student_summary(student: Student) -> StudentSummary:
    return StudentSummary(
        id=student.id,
        name=student.name,
        status=student.status,
        parent_id=student.parent_id,
    )


def list_students_with_status(db: Session) -> list[StudentListItemResponse]:
    students = db.scalars(select(Student).order_by(Student.created_at.asc())).all()
    items: list[StudentListItemResponse] = []
    for student in students:
        latest_device = db.scalar(
            select(Device)
            .where(Device.student_id == student.id)
            .order_by(desc(Device.last_seen_at), desc(Device.created_at))
            .limit(1)
        )
        alerts_count = db.query(Alert).filter(Alert.student_id == student.id).count()
        items.append(
            StudentListItemResponse(
                id=student.id,
                name=student.name,
                status=student.status,
                parent_id=student.parent_id,
                organization_id=student.organization_id,
                last_active_at=latest_device.last_seen_at if latest_device else None,
                protection_status=latest_device.protection_status if latest_device else None,
                alerts_count=alerts_count,
                created_at=student.created_at,
            )
        )
    return items


def create_student_record(db: Session, *, payload: StudentCreateRequest) -> Student:
    student = Student(
        id=f"stu_{uuid.uuid4().hex[:8]}",
        name=payload.name.strip(),
        parent_id=payload.parent_id,
        organization_id=payload.organization_id.strip(),
        status=payload.status.strip().upper(),
        created_at=now_utc(),
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


def update_student_record(db: Session, *, student: Student, payload: StudentUpdateRequest) -> Student:
    if payload.name is not None:
        student.name = payload.name.strip()
    if payload.parent_id is not None:
        student.parent_id = payload.parent_id
    if payload.organization_id is not None:
        student.organization_id = payload.organization_id.strip()
    if payload.status is not None:
        student.status = payload.status.strip().upper()
    db.commit()
    db.refresh(student)
    return student


def get_student_dashboard(db: Session, student: Student) -> StudentDashboardResponse:
    check_heartbeat_missing(db, student=student)
    latest_device = db.scalar(
        select(Device)
        .where(Device.student_id == student.id)
        .order_by(desc(Device.last_seen_at), desc(Device.created_at))
        .limit(1)
    )

    app_rules = db.scalars(
        select(AppRule).where(AppRule.student_id == student.id).order_by(AppRule.app_name.asc())
    ).all()

    social_usage = []
    usage_today = get_usage_summary_by_package(db, student_id=student.id)
    seed_usage_minutes = {
        "com.instagram.android": 12,
        "com.google.android.youtube": 18,
        "com.facebook.katana": 0,
    }
    for rule in app_rules:
        used_minutes = usage_today.get(rule.package_name, seed_usage_minutes.get(rule.package_name, 0))
        remaining_minutes = max(rule.daily_limit_minutes - used_minutes, 0)
        social_usage.append(
            DashboardUsageCard(
                app_name=rule.app_name,
                package_name=rule.package_name,
                daily_limit_minutes=rule.daily_limit_minutes,
                used_minutes=used_minutes,
                remaining_minutes=remaining_minutes,
                blocked=rule.is_blocked,
            )
        )

    website_rules = db.scalars(
        select(WebsiteRule).where(WebsiteRule.student_id == student.id)
    ).all()
    blocked_categories = sorted(
        {
            rule.category
            for rule in website_rules
            if rule.rule_type == "block"
        }
    )

    recent_alerts = db.scalars(
        select(Alert)
        .where(Alert.student_id == student.id)
        .order_by(desc(Alert.created_at))
        .limit(5)
    ).all()

    return StudentDashboardResponse(
        student=get_student_summary(student),
        device=latest_device,
        social_usage=social_usage,
        blocked_categories=blocked_categories,
        recent_alerts=recent_alerts,
        last_sync_at=latest_device.last_seen_at if latest_device else None,
    )


def create_heartbeat(
    db: Session,
    *,
    device: Device,
    battery_level: int | None,
    permissions_status: dict,
    vpn_active: bool,
    accessibility_active: bool,
) -> DeviceHeartbeat:
    seen_at = now_utc()
    heartbeat = DeviceHeartbeat(
        device_id=device.id,
        battery_level=battery_level,
        permissions_status_json=permissions_status,
        vpn_active=vpn_active,
        accessibility_active=accessibility_active,
        last_seen_at=seen_at,
    )
    device.last_seen_at = seen_at
    if all(permissions_status.values()):
        device.protection_status = "ACTIVE"
    else:
        device.protection_status = "SETUP_REQUIRED"

    db.add(heartbeat)
    db.commit()
    db.refresh(heartbeat)
    db.refresh(device)
    return heartbeat


def create_usage_logs(
    db: Session,
    *,
    device: Device,
    entries: list[UsageLogCreate],
) -> list[UsageLog]:
    created_at = now_utc()
    date_values = {entry.date for entry in entries}
    for date_value in date_values:
        db.query(UsageLog).filter(
            UsageLog.device_id == device.id,
            UsageLog.date == date_value,
        ).delete()

    records = [
        UsageLog(
            student_id=device.student_id,
            device_id=device.id,
            package_name=entry.package_name,
            usage_seconds=entry.usage_seconds,
            date=entry.date,
            created_at=created_at,
        )
        for entry in entries
    ]
    db.add_all(records)
    db.commit()
    return records


def create_alert(
    db: Session,
    *,
    student_id: str,
    device_id: str | None,
    event_type: str,
    severity: str,
    message: str,
    metadata_json: dict,
) -> Alert:
    alert = Alert(
        student_id=student_id,
        device_id=device_id,
        type=event_type,
        severity=severity,
        message=message,
        metadata_json=metadata_json,
        read_at=None,
        created_at=now_utc(),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    send_alert_notifications(db, alert=alert)
    return alert


def mark_alert_read(db: Session, *, alert: Alert) -> Alert:
    alert.read_at = now_utc()
    db.commit()
    db.refresh(alert)
    return alert


def get_usage_summary_by_package(db: Session, *, student_id: str) -> dict[str, int]:
    today = now_utc().date().isoformat()
    usage_logs = db.scalars(
        select(UsageLog).where(UsageLog.student_id == student_id, UsageLog.date == today)
    ).all()
    result: dict[str, int] = {}
    for log in usage_logs:
        result[log.package_name] = result.get(log.package_name, 0) + log.usage_seconds // 60
    return result


def get_usage_today_report(db: Session, *, student_id: str) -> UsageTodayResponse:
    date_value = now_utc().date().isoformat()
    package_map = get_usage_summary_by_package(db, student_id=student_id)
    return UsageTodayResponse(
        student_id=student_id,
        date=date_value,
        packages=[
            UsagePackageSummary(package_name=package_name, usage_minutes=usage_minutes)
            for package_name, usage_minutes in sorted(package_map.items())
        ],
    )


def get_usage_weekly_report(db: Session, *, student_id: str) -> UsageWeeklyResponse:
    today = now_utc().date()
    start_date = today - timedelta(days=6)
    usage_logs = db.scalars(
        select(UsageLog)
        .where(UsageLog.student_id == student_id)
        .where(UsageLog.date >= start_date.isoformat())
        .where(UsageLog.date <= today.isoformat())
        .order_by(UsageLog.date.asc(), UsageLog.package_name.asc())
    ).all()

    grouped: dict[str, dict[str, int]] = {}
    for log in usage_logs:
        by_package = grouped.setdefault(log.date, {})
        by_package[log.package_name] = by_package.get(log.package_name, 0) + log.usage_seconds // 60

    days = []
    for offset in range(7):
        date_value = (start_date + timedelta(days=offset)).isoformat()
        package_map = grouped.get(date_value, {})
        days.append(
            UsageWeeklyDayResponse(
                date=date_value,
                packages=[
                    UsagePackageSummary(package_name=package_name, usage_minutes=usage_minutes)
                    for package_name, usage_minutes in sorted(package_map.items())
                ],
            )
        )

    return UsageWeeklyResponse(student_id=student_id, days=days)


def check_heartbeat_missing(db: Session, *, student: Student) -> None:
    latest_device = db.scalar(
        select(Device)
        .where(Device.student_id == student.id)
        .order_by(desc(Device.last_seen_at), desc(Device.created_at))
        .limit(1)
    )
    if latest_device is None or latest_device.last_seen_at is None:
        return

    if now_utc() - latest_device.last_seen_at < timedelta(minutes=30):
        return

    existing_recent = db.scalar(
        select(Alert.id)
        .where(Alert.student_id == student.id, Alert.type == "APP_HEARTBEAT_MISSING")
        .order_by(desc(Alert.created_at))
        .limit(1)
    )
    if existing_recent:
        recent_alert = db.get(Alert, existing_recent)
        if recent_alert and now_utc() - recent_alert.created_at < timedelta(hours=6):
            return

    create_alert(
        db,
        student_id=student.id,
        device_id=latest_device.id,
        event_type="APP_HEARTBEAT_MISSING",
        severity="HIGH",
        message=f"Protection app may be disabled or removed. Last active: {latest_device.last_seen_at.isoformat()}",
        metadata_json={"lastSeenAt": latest_device.last_seen_at.isoformat()},
    )


def replace_app_rules(db: Session, *, student_id: str, rules: list[AppRuleUpsert]) -> list[AppRule]:
    db.query(AppRule).filter(AppRule.student_id == student_id).delete()
    created_at = now_utc()
    records = [
        AppRule(
            student_id=student_id,
            app_name=rule.app_name,
            package_name=rule.package_name,
            daily_limit_minutes=rule.daily_limit_minutes,
            is_blocked=rule.is_blocked,
            created_at=created_at,
            updated_at=created_at,
        )
        for rule in rules
    ]
    db.add_all(records)
    db.commit()
    return db.scalars(select(AppRule).where(AppRule.student_id == student_id)).all()


def update_app_rule_record(
    db: Session,
    *,
    rule: AppRule,
    app_name: str | None = None,
    package_name: str | None = None,
    daily_limit_minutes: int | None = None,
    is_blocked: bool | None = None,
) -> AppRule:
    if app_name is not None:
        rule.app_name = app_name
    if package_name is not None:
        rule.package_name = package_name
    if daily_limit_minutes is not None:
        rule.daily_limit_minutes = daily_limit_minutes
    if is_blocked is not None:
        rule.is_blocked = is_blocked
    rule.updated_at = now_utc()
    db.commit()
    db.refresh(rule)
    return rule


def replace_website_rules(
    db: Session,
    *,
    student_id: str,
    rules: list[WebsiteRuleUpsert],
) -> list[WebsiteRule]:
    db.query(WebsiteRule).filter(WebsiteRule.student_id == student_id).delete()
    created_at = now_utc()
    records = [
        WebsiteRule(
            student_id=student_id,
            domain=rule.domain.strip().lower(),
            category=rule.category.strip().lower(),
            rule_type=rule.rule_type,
            created_at=created_at,
        )
        for rule in rules
    ]
    db.add_all(records)
    db.commit()
    return db.scalars(select(WebsiteRule).where(WebsiteRule.student_id == student_id)).all()


def update_website_rule_record(
    db: Session,
    *,
    rule: WebsiteRule,
    domain: str | None = None,
    category: str | None = None,
    rule_type: str | None = None,
) -> WebsiteRule:
    if domain is not None:
        rule.domain = domain.strip().lower()
    if category is not None:
        rule.category = category.strip().lower()
    if rule_type is not None:
        rule.rule_type = rule_type
    db.commit()
    db.refresh(rule)
    return rule


def create_extra_time_request(
    db: Session,
    *,
    student_id: str,
    device_id: str | None,
    package_name: str,
    requested_minutes: int,
    reason: str,
) -> ExtraTimeRequest:
    request_record = ExtraTimeRequest(
        student_id=student_id,
        device_id=device_id,
        package_name=package_name,
        requested_minutes=requested_minutes,
        reason=reason,
        status="pending",
        approved_by=None,
        created_at=now_utc(),
    )
    db.add(request_record)
    db.commit()
    db.refresh(request_record)
    create_alert(
        db,
        student_id=student_id,
        device_id=device_id,
        event_type="EXTRA_TIME_REQUESTED",
        severity="MEDIUM",
        message=f"Student requested {requested_minutes} more minutes for {package_name}.",
        metadata_json={"requestId": request_record.id, "reason": reason},
    )
    return request_record


def review_extra_time_request(
    db: Session,
    *,
    request_record: ExtraTimeRequest,
    approved_by: str,
    status: str,
) -> ExtraTimeRequest:
    request_record.status = status
    request_record.approved_by = approved_by
    db.commit()
    db.refresh(request_record)

    create_alert(
        db,
        student_id=request_record.student_id,
        device_id=request_record.device_id,
        event_type="EXTRA_TIME_APPROVED" if status == "approved" else "EXTRA_TIME_REJECTED",
        severity="LOW" if status == "approved" else "MEDIUM",
        message=(
            f"Parent approved {request_record.requested_minutes} extra minutes for {request_record.package_name}."
            if status == "approved"
            else f"Parent rejected extra time for {request_record.package_name}."
        ),
        metadata_json={
            "requestId": request_record.id,
            "approvedBy": approved_by,
            "status": status,
        },
    )

    return request_record


def send_alert_notifications(db: Session, *, alert: Alert) -> None:
    student = db.get(Student, alert.student_id)
    if student is None:
        return

    parent = db.get(User, student.parent_id)
    if parent is None:
        return

    payload = {
        "studentId": alert.student_id,
        "deviceId": alert.device_id,
        "eventType": alert.type,
        "severity": alert.severity,
        "message": alert.message,
        "timestamp": alert.created_at.isoformat(),
    }

    if settings.alert_email_enabled:
        send_alert_email(parent_email=parent.email, parent_name=parent.name, payload=payload)

    if settings.fcm_enabled and settings.fcm_server_key:
        target_tokens = db.scalars(
            select(Device.fcm_token)
            .where(Device.student_id == alert.student_id)
            .where(Device.fcm_token.is_not(None))
        ).all()
        for token in target_tokens:
            send_fcm_notification(token=token, payload=payload)


def send_alert_email(*, parent_email: str, parent_name: str, payload: dict) -> None:
    if not settings.smtp_host or not parent_email:
        return

    message = EmailMessage()
    message["Subject"] = f"Studentwellfare alert: {payload['eventType']}"
    message["From"] = settings.alert_email_from
    message["To"] = parent_email
    message.set_content(
        "\n".join(
            [
                f"Hi {parent_name},",
                "",
                payload["message"],
                f"Severity: {payload['severity']}",
                f"Student: {payload['studentId']}",
                f"Device: {payload['deviceId'] or 'n/a'}",
                f"Time: {payload['timestamp']}",
            ]
        )
    )

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except OSError:
        return


def send_fcm_notification(*, token: str, payload: dict) -> None:
    if not token:
        return

    body = json.dumps(
        {
            "to": token,
            "priority": "high",
            "notification": {
                "title": f"{payload['eventType']} detected",
                "body": payload["message"],
            },
            "data": payload,
        }
    ).encode("utf-8")

    request = urllib_request.Request(
        "https://fcm.googleapis.com/fcm/send",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"key={settings.fcm_server_key}",
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(request, timeout=10):
            return
    except (urllib_error.URLError, OSError):
        return


def ensure_schema_compatibility() -> None:
    inspector = inspect(engine)
    if "alerts" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("alerts")}
    if "read_at" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE alerts ADD COLUMN read_at DATETIME"))

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "parent_pin_hash" not in user_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE users ADD COLUMN parent_pin_hash VARCHAR(128)"))
