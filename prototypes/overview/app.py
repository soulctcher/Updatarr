"""Throwaway Updatarr Overview prototype; never use as the production server."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent
from starlette.middleware.trustedhost import TrustedHostMiddleware


ROOT = Path(__file__).resolve().parent

app = FastAPI(
    title="Updatarr Overview Prototype",
    version="0.0.0-prototype",
    docs_url=None,
    redoc_url=None,
    openapi_url="/api/v1/openapi.json",
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["127.0.0.1", "localhost", "[::1]"],
)


SNAPSHOT = {
    "schema_version": 1,
    "prototype": True,
    "scan": {
        "state": "current",
        "completed_at": "Today, 18:42",
        "duration_seconds": 12.4,
    },
    "summary": {
        "updates_found": 12,
        "ready_to_review": 11,
        "system_updates": 8,
        "separate_updates": 4,
        "postponed": 3,
        "blocked": 1,
    },
    "update_sources": [
        {
            "id": "native",
            "name": "Arch + EndeavourOS",
            "state": "review",
            "updates_found": 8,
            "detail": "Updates together as one group",
        },
        {
            "id": "flatpak-user",
            "name": "Flatpak · user",
            "state": "healthy",
            "updates_found": 3,
            "detail": "3 updates that can run separately",
        },
        {
            "id": "firmware",
            "name": "Firmware",
            "state": "current",
            "updates_found": 0,
            "detail": "2 supported devices checked",
        },
        {
            "id": "aur",
            "name": "AUR",
            "state": "blocked",
            "updates_found": 1,
            "detail": "Needs system updates first",
        },
    ],
    "updates": [
        {
            "name": "linux",
            "source": "Core",
            "from": "7.2.10",
            "to": "7.2.11",
            "size": "132 MiB",
            "risk": "reboot",
            "status": "System update",
        },
        {
            "name": "mesa",
            "source": "Extra",
            "from": "26.2.1",
            "to": "26.2.2",
            "size": "18 MiB",
            "risk": "normal",
            "status": "System update",
        },
        {
            "name": "org.mozilla.firefox",
            "source": "Flathub · user",
            "from": "144.0",
            "to": "144.0.1",
            "size": "91 MiB",
            "risk": "normal",
            "status": "Updates separately",
        },
        {
            "name": "example-git",
            "source": "AUR",
            "from": "r418",
            "to": "r431",
            "size": "Unknown",
            "risk": "blocked",
            "status": "Waits for system update",
        },
    ],
    "plan_steps": [
        {"step": "Check", "state": "complete", "detail": "5 update sources"},
        {"step": "Review", "state": "active", "detail": "1 blocker"},
        {"step": "Confirm here", "state": "waiting", "detail": "On this computer"},
        {"step": "Allow access", "state": "waiting", "detail": "Admin updates only"},
        {"step": "Verify results", "state": "waiting", "detail": "Not started"},
    ],
}


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
    )
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(ROOT / "index.html")


@app.get("/assets/styles.css", include_in_schema=False)
async def styles() -> FileResponse:
    return FileResponse(ROOT / "styles.css", media_type="text/css")


@app.get("/assets/app.js", include_in_schema=False)
async def script() -> FileResponse:
    return FileResponse(ROOT / "app.js", media_type="text/javascript")


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/status")
async def status() -> dict:
    return SNAPSHOT


@app.get("/api/v1/events", response_class=EventSourceResponse)
async def events(request: Request):
    states = (
        ("checking", "Checking Flatpak · user", 68),
        ("checking", "Verifying update sources", 88),
        ("current", "Check complete · 11 ready to review", 100),
    )
    sequence = 0
    while not await request.is_disconnected():
        for state, message, progress in states:
            if await request.is_disconnected():
                return
            sequence += 1
            yield ServerSentEvent(
                event="scan-progress",
                id=str(sequence),
                retry=2_000,
                data={
                    "schema_version": 1,
                    "task_id": "prototype-scan",
                    "sequence": sequence,
                    "state": state,
                    "message": message,
                    "progress": progress,
                },
            )
            await asyncio.sleep(1.4)
        await asyncio.sleep(5)


if __name__ == "__main__":
    port = int(os.environ.get("UPDATARR_PROTOTYPE_PORT", "8787"))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
