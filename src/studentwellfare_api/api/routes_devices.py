from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from studentwellfare_api.database import get_db
from studentwellfare_api.models import Device
from studentwellfare_api.schemas import (
    HeartbeatRequest,
    HeartbeatResponse,
    UsageAppUploadRequest,
    UsageLogCreate,
    UsageLogResponse,
)
from studentwellfare_api.services import create_heartbeat, create_usage_logs

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("/{device_id}/heartbeat", response_model=HeartbeatResponse)
def device_heartbeat(
    device_id: str,
    payload: HeartbeatRequest,
    db: Session = Depends(get_db),
) -> HeartbeatResponse:
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")

    heartbeat = create_heartbeat(
        db,
        device=device,
        battery_level=payload.battery_level,
        permissions_status=payload.permissions_status.model_dump(),
        vpn_active=payload.vpn_active,
        accessibility_active=payload.accessibility_active,
    )

    return HeartbeatResponse(
        device_id=device.id,
        received_at=heartbeat.last_seen_at,
        protection_status=device.protection_status,
    )


@router.post("/{device_id}/usage-logs", response_model=list[UsageLogResponse])
def upload_usage_logs(
    device_id: str,
    payload: list[UsageLogCreate],
    db: Session = Depends(get_db),
) -> list[UsageLogResponse]:
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")

    return create_usage_logs(db, device=device, entries=payload)


@router.post("/usage/app", response_model=list[UsageLogResponse], status_code=status.HTTP_201_CREATED)
def upload_usage_logs_alias(
    payload: UsageAppUploadRequest,
    db: Session = Depends(get_db),
) -> list[UsageLogResponse]:
    device = db.get(Device, payload.device_id)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")
    return create_usage_logs(db, device=device, entries=payload.entries)
