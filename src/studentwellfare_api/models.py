from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from studentwellfare_api.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_pin_hash: Mapped[str | None] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    students: Mapped[list["Student"]] = relationship(back_populates="parent")
    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user")


class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    parent_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(50), default="org_internal", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    parent: Mapped[User] = relationship(back_populates="students")
    devices: Mapped[list["Device"]] = relationship(back_populates="student")
    app_rules: Mapped[list["AppRule"]] = relationship(back_populates="student")
    website_rules: Mapped[list["WebsiteRule"]] = relationship(back_populates="student")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="student")
    extra_time_requests: Mapped[list["ExtraTimeRequest"]] = relationship(back_populates="student")
    usage_logs: Mapped[list["UsageLog"]] = relationship(back_populates="student")
    pairing_codes: Mapped[list["PairingCode"]] = relationship(back_populates="student")


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    device_name: Mapped[str] = mapped_column(String(120), nullable=False)
    android_id: Mapped[str | None] = mapped_column(String(255))
    fcm_token: Mapped[str | None] = mapped_column(String(255))
    app_version: Mapped[str | None] = mapped_column(String(50))
    protection_status: Mapped[str] = mapped_column(String(20), default="PENDING_SETUP", nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    student: Mapped[Student] = relationship(back_populates="devices")
    heartbeats: Mapped[list["DeviceHeartbeat"]] = relationship(back_populates="device")
    usage_logs: Mapped[list["UsageLog"]] = relationship(back_populates="device")


class AppRule(Base):
    __tablename__ = "app_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    app_name: Mapped[str] = mapped_column(String(120), nullable=False)
    package_name: Mapped[str] = mapped_column(String(255), nullable=False)
    daily_limit_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    student: Mapped[Student] = relationship(back_populates="app_rules")


class WebsiteRule(Base):
    __tablename__ = "website_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    student: Mapped[Student] = relationship(back_populates="website_rules")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    device_id: Mapped[str | None] = mapped_column(ForeignKey("devices.id"))
    type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    student: Mapped[Student] = relationship(back_populates="alerts")


class DeviceHeartbeat(Base):
    __tablename__ = "device_heartbeats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), nullable=False)
    battery_level: Mapped[int | None] = mapped_column(Integer)
    permissions_status_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    vpn_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    accessibility_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    device: Mapped[Device] = relationship(back_populates="heartbeats")


class ExtraTimeRequest(Base):
    __tablename__ = "extra_time_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    device_id: Mapped[str | None] = mapped_column(ForeignKey("devices.id"))
    package_name: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    student: Mapped[Student] = relationship(back_populates="extra_time_requests")


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), nullable=False)
    package_name: Mapped[str] = mapped_column(String(255), nullable=False)
    usage_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    student: Mapped[Student] = relationship(back_populates="usage_logs")
    device: Mapped[Device] = relationship(back_populates="usage_logs")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    refresh_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    user: Mapped[User] = relationship(back_populates="sessions")


class PairingCode(Base):
    __tablename__ = "pairing_codes"

    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    student: Mapped[Student] = relationship(back_populates="pairing_codes")
