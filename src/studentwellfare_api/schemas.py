from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuthLoginRequest(BaseModel):
    email: str
    password: str


class AuthLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    role: str
    name: str


class AuthRefreshRequest(BaseModel):
    refresh_token: str


class AuthLogoutRequest(BaseModel):
    refresh_token: str


class AuthRegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=128)


class ParentPinVerifyRequest(BaseModel):
    user_id: str | None = None
    student_id: str | None = None
    pin: str = Field(min_length=4, max_length=12)


class ParentPinVerifyResponse(BaseModel):
    valid: bool


class ParentPinUpdateRequest(BaseModel):
    user_id: str
    current_pin: str | None = None
    new_pin: str = Field(min_length=4, max_length=12)


class ParentPinUpdateResponse(BaseModel):
    ok: bool


class PairingCodeCreateRequest(BaseModel):
    student_id: str
    expires_in_minutes: int = Field(default=30, ge=5, le=1440)


class PairingCodeResponse(BaseModel):
    student_id: str
    pairing_code: str
    expires_at: datetime


class PairingVerifyRequest(BaseModel):
    pairing_code: str
    device_name: str
    android_id: str | None = None
    app_version: str | None = "0.1.0"
    fcm_token: str | None = None


class DeviceRegisterRequest(BaseModel):
    student_id: str
    device_name: str
    android_id: str | None = None
    app_version: str | None = None
    fcm_token: str | None = None


class PermissionStatus(BaseModel):
    usage_access: bool = False
    accessibility: bool = False
    overlay: bool = False
    vpn: bool = False
    device_admin: bool = False
    notifications: bool = False


class HeartbeatRequest(BaseModel):
    battery_level: int | None = Field(default=None, ge=0, le=100)
    permissions_status: PermissionStatus = Field(default_factory=PermissionStatus)
    vpn_active: bool = False
    accessibility_active: bool = False


class UsageLogCreate(BaseModel):
    package_name: str
    usage_seconds: int = Field(ge=0)
    date: str


class UsageLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: str
    device_id: str
    package_name: str
    usage_seconds: int
    date: str
    created_at: datetime


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    student_id: str
    device_name: str
    android_id: str | None
    app_version: str | None
    protection_status: str
    last_seen_at: datetime | None
    created_at: datetime


class AppRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    app_name: str
    package_name: str
    daily_limit_minutes: int
    is_blocked: bool


class WebsiteRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    domain: str
    category: str
    rule_type: str


class AppRuleUpsert(BaseModel):
    app_name: str
    package_name: str
    daily_limit_minutes: int = Field(ge=0, le=1440)
    is_blocked: bool = False


class WebsiteRuleUpsert(BaseModel):
    domain: str
    category: str
    rule_type: str = Field(pattern="^(block|allow)$")


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    severity: str
    message: str
    metadata_json: dict[str, Any]
    read_at: datetime | None
    created_at: datetime


class AlertCreateRequest(BaseModel):
    student_id: str
    device_id: str | None = None
    type: str
    severity: str
    message: str
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ExtraTimeRequestCreate(BaseModel):
    device_id: str | None = None
    package_name: str
    requested_minutes: int = Field(ge=5, le=240)
    reason: str = Field(min_length=3, max_length=500)


class ExtraTimeRequestReview(BaseModel):
    approved_by: str
    status: str = Field(pattern="^(approved|rejected)$")


class ExtraTimeRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: str
    device_id: str | None
    package_name: str
    requested_minutes: int
    reason: str
    status: str
    approved_by: str | None
    created_at: datetime


class InstallRequestCreate(BaseModel):
    device_id: str | None = None
    package_name: str
    app_name: str
    reason: str = Field(min_length=3, max_length=500)


class InstallRequestReview(BaseModel):
    approved_by: str
    status: str = Field(pattern="^(approved|rejected)$")


class InstallRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: str
    device_id: str | None
    package_name: str
    app_name: str
    reason: str
    status: str
    approved_by: str | None
    created_at: datetime


class StudentSummary(BaseModel):
    id: str
    name: str
    status: str
    parent_id: str


class StudentCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    parent_id: str | None = None  # ignored — server fills from auth token
    organization_id: str = Field(default="org_internal", min_length=2, max_length=50)
    status: str = Field(default="ACTIVE", min_length=3, max_length=20)


class StudentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    parent_id: str | None = None
    organization_id: str | None = Field(default=None, min_length=2, max_length=50)
    status: str | None = Field(default=None, min_length=3, max_length=20)


class StudentListItemResponse(BaseModel):
    id: str
    name: str
    status: str
    parent_id: str
    organization_id: str
    last_active_at: datetime | None
    protection_status: str | None
    alerts_count: int
    created_at: datetime


class UsageAppUploadRequest(BaseModel):
    device_id: str
    entries: list[UsageLogCreate]


class UsagePackageSummary(BaseModel):
    package_name: str
    usage_minutes: int


class UsageTodayResponse(BaseModel):
    student_id: str
    date: str
    packages: list[UsagePackageSummary]


class UsageWeeklyDayResponse(BaseModel):
    date: str
    packages: list[UsagePackageSummary]


class UsageWeeklyResponse(BaseModel):
    student_id: str
    days: list[UsageWeeklyDayResponse]


class DashboardUsageCard(BaseModel):
    app_name: str
    package_name: str
    daily_limit_minutes: int
    used_minutes: int
    remaining_minutes: int
    blocked: bool


class StudentDashboardResponse(BaseModel):
    student: StudentSummary
    device: DeviceResponse | None
    social_usage: list[DashboardUsageCard]
    blocked_categories: list[str]
    recent_alerts: list[AlertResponse]
    last_sync_at: datetime | None


class RulesResponse(BaseModel):
    student_id: str
    app_rules: list[AppRuleResponse]
    website_rules: list[WebsiteRuleResponse]


class PairingVerifyResponse(BaseModel):
    student: StudentSummary
    device: DeviceResponse
    rules: RulesResponse
    dashboard: StudentDashboardResponse


class HeartbeatResponse(BaseModel):
    device_id: str
    received_at: datetime
    protection_status: str
