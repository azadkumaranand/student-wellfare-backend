from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from studentwellfare_api.api.routes_auth import router as auth_router
from studentwellfare_api.api.routes_alerts import router as alerts_router
from studentwellfare_api.api.routes_controls import router as controls_router
from studentwellfare_api.api.routes_devices import router as devices_router
from studentwellfare_api.api.routes_health import router as health_router
from studentwellfare_api.api.routes_pairing import router as pairing_router
from studentwellfare_api.api.routes_students import router as students_router
from studentwellfare_api.config import settings
from studentwellfare_api.database import Base, SessionLocal, engine
from studentwellfare_api.services import ensure_schema_compatibility, seed_database

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    summary="Backend foundation for the student safety mobile app MVP.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility()
    with SessionLocal() as session:
        seed_database(session)


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(alerts_router)
app.include_router(controls_router)
app.include_router(pairing_router)
app.include_router(students_router)
app.include_router(devices_router)
