"""Same-origin FastAPI/React application boundary."""

from __future__ import annotations

from dataclasses import dataclass
import asyncio
import json
import os
from pathlib import Path
from secrets import token_urlsafe
import tempfile
import threading
from typing import AsyncIterator, Literal

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from .advisories import AdvisoryAdapter, AdvisoryService, ArchNewsAdapter, SimulatorAdvisoryAdapter
from .catalog import (
    CatalogAdapter, CatalogService, aur_build_preview,
    live_catalog_adapters, simulator_catalog_adapters,
)
from .domain import PlanState, PolicyKind, SourceState, UpdateRun, UpdateRunState, utc_now
from .execution import ProviderResultChecker, SimulatorExecutor, SimulatorResultChecker
from .events import EventHistory
from .history import (
    HistoryImportBatch,
    read_flatpak_history_report,
    read_pacman_history_report,
    simulator_history,
)
from .inventory import InventoryCoordinator
from .m4 import live_read_only_report, simulator_report
from .policy import PolicyError, apply_policies, check_update_selection, new_policy
from .planning import Planner, PlanningError
from .providers import live_adapters, simulator_adapters
from .providers.base import ProviderAdapter
from .providers.probes import LiveProbeClient
from .security import AuthenticationError, Session, SessionStore
from .storage import StateStore
from .tray_status import TrayStatusFile


SESSION_COOKIE = "updatarr_session"
API_VERSION = 1


class BoundedRequestBodyMiddleware:
    """Reject known-large bodies early and stop unknown streams at the limit."""

    def __init__(self, app, *, limit: int) -> None:  # type: ignore[no-untyped-def]
        self.app = app
        self.limit = limit

    async def __call__(self, scope, receive, send) -> None:  # type: ignore[no-untyped-def]
        if scope["type"] != "http" or scope["method"] in {"GET", "HEAD", "OPTIONS"}:
            await self.app(scope, receive, send)
            return
        headers = {name.lower(): value for name, value in scope.get("headers", [])}
        raw_length = headers.get(b"content-length")
        if raw_length:
            try:
                if int(raw_length) > self.limit:
                    await self._reject(scope, receive, send)
                    return
            except ValueError:
                await self._reject(scope, receive, send)
                return

        received = 0
        buffered: list[dict[str, object]] = []
        while True:
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.limit:
                    await self._reject(scope, receive, send)
                    return
                buffered.append(message)
                if not message.get("more_body", False):
                    break
            else:
                buffered.append(message)
                break

        async def limited_receive():  # type: ignore[no-untyped-def]
            if buffered:
                return buffered.pop(0)
            return await receive()

        await self.app(scope, limited_receive, send)

    @staticmethod
    async def _reject(scope, receive, send) -> None:  # type: ignore[no-untyped-def]
        response = JSONResponse({"detail": "This request is too large."}, status_code=413)
        await response(scope, receive, send)


@dataclass(frozen=True)
class AppConfig:
    password: str = "updatarr-demo"
    allowed_hosts: tuple[str, ...] = ("127.0.0.1", "localhost", "testserver")
    public_origin: str = "http://127.0.0.1:8788"
    url_base: str = ""
    secure_cookie: bool = False
    static_dir: Path | None = None
    session_ttl_seconds: int = 1800
    event_history_limit: int = 100
    max_request_body_bytes: int = 8192
    storage_path: Path | None = None
    provider_mode: str = "simulator"
    adapters: tuple[ProviderAdapter, ...] | None = None
    catalog_adapters: tuple[CatalogAdapter, ...] | None = None
    advisory_adapters: tuple[AdvisoryAdapter, ...] | None = None
    local_agent_token: str | None = None
    tray_status_path: Path | None = None
    trusted_proxy_peers: tuple[str, ...] = ()

    def normalized_base(self) -> str:
        if not self.url_base or self.url_base == "/":
            return ""
        return "/" + self.url_base.strip("/")


class LoginBody(BaseModel):
    password: str = Field(min_length=1, max_length=1024)


class PasswordBody(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=8, max_length=1024)


class AppearanceBody(BaseModel):
    theme: str = Field(min_length=1, max_length=64)


class PolicyBody(BaseModel):
    kind: Literal["turn_off_source", "postpone", "skip_version", "pause_software"]
    source_id: str = Field(min_length=1, max_length=64)
    scope: str = Field(min_length=1, max_length=64)
    software_id: str | None = Field(default=None, max_length=300)
    target_stable_id: str | None = Field(default=None, max_length=300)
    version: str | None = Field(default=None, max_length=300)
    expires_at: str | None = Field(default=None, max_length=64)
    reason: str | None = Field(default=None, max_length=500)


class SelectionBody(BaseModel):
    snapshot_id: str = Field(min_length=1, max_length=100)
    selected_stable_ids: list[str] = Field(max_length=500)


class ReviewPlanBody(BaseModel):
    digest: str = Field(min_length=64, max_length=64)


class SourceSettingBody(BaseModel):
    enabled: bool


THEME_IDS = {
    "system", "light", "dark", "amoled", "solarized-light", "solarized-dark",
    "github-light", "github-dark", "norse", "nord", "gruvbox-light", "gruvbox-dark",
    "dracula", "catppuccin-latte", "catppuccin-mocha", "sepia", "midnight", "high-contrast",
}


def create_app(config: AppConfig | None = None) -> FastAPI:
    config = config or AppConfig()
    base = config.normalized_base()
    storage_path = config.storage_path or Path(tempfile.mkdtemp(prefix="updatarr-m2-")) / "state.db"
    store = StateStore(storage_path)
    store.initialize()
    adapters = list(config.adapters) if config.adapters is not None else (
        live_adapters() if config.provider_mode == "live" else simulator_adapters()
    )
    store.recover_unfinished_runs(ProviderResultChecker(adapters).matches)
    sessions = SessionStore(
        config.password, ttl_seconds=config.session_ttl_seconds, repository=store
    )
    events = EventHistory(config.event_history_limit)
    events.restore(store.recent_events(config.event_history_limit))
    catalog_adapters = list(config.catalog_adapters) if config.catalog_adapters is not None else (
        live_catalog_adapters() if config.provider_mode == "live" else simulator_catalog_adapters()
    )
    catalog = CatalogService(catalog_adapters)
    advisory_adapters = list(config.advisory_adapters) if config.advisory_adapters is not None else (
        [ArchNewsAdapter()] if config.provider_mode == "live" else [SimulatorAdvisoryAdapter()]
    )
    advisories = AdvisoryService(advisory_adapters)
    tray_status_file = TrayStatusFile(config.tray_status_path) if config.tray_status_path else None

    def snapshot_status(snapshot) -> None:  # type: ignore[no-untyped-def]
        if tray_status_file is not None:
            try:
                tray_status_file.write({
                    "snapshot": {"snapshot_id": snapshot.snapshot_id, "completed_at": snapshot.completed_at},
                    "summary": snapshot.summary(),
                })
            except OSError:
                pass  # Tray display failure must not change the inventory result.

    inventory = InventoryCoordinator(adapters, store, events, snapshot_listener=snapshot_status)
    planner = Planner()
    simulator_executor = SimulatorExecutor()
    run_cancellations: dict[str, threading.Event] = {}
    run_tasks: set[asyncio.Task[None]] = set()
    app = FastAPI(title="Updatarr", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(BoundedRequestBodyMiddleware, limit=config.max_request_body_bytes)
    app.state.sessions = sessions
    app.state.events = events
    app.state.inventory = inventory
    app.state.catalog = catalog
    app.state.advisories = advisories
    app.state.store = store

    def saved_theme() -> str:
        theme = store.preference("administrator", "theme", "system")
        return theme if theme in THEME_IDS else "system"

    def effective_updates():  # type: ignore[no-untyped-def]
        snapshot = store.latest_snapshot()
        if snapshot is None:
            return None, ()
        return snapshot, apply_policies(snapshot.updates, store.policies())

    def saved_choice_counts(updates) -> dict[str, int]:  # type: ignore[no-untyped-def]
        return {
            "postponed": sum(update.state is SourceState.POSTPONED for update in updates),
            "skipped": sum(update.state is SourceState.SKIPPED for update in updates),
            "paused": sum(update.state is SourceState.PAUSED for update in updates),
        }

    def publish_tray_status(payload: dict[str, object]) -> None:
        if tray_status_file is not None:
            try:
                tray_status_file.write(payload)
            except OSError:
                pass  # The browser remains usable if the graphical session is absent.

    @app.middleware("http")
    async def security_boundary(request: Request, call_next):  # type: ignore[no-untyped-def]
        host = request.headers.get("host", "").split(":", 1)[0].lower()
        if host not in config.allowed_hosts:
            return JSONResponse({"detail": "Unknown host."}, status_code=400)
        forwarded = any(
            name == "forwarded" or name.startswith("x-forwarded-")
            for name in request.headers
        )
        peer = request.client.host if request.client else ""
        if forwarded and peer not in config.trusted_proxy_peers:
            return JSONResponse({"detail": "Forwarded headers are not trusted."}, status_code=400)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin != config.public_origin.rstrip("/"):
                return JSONResponse({"detail": "This request did not come from Updatarr."}, status_code=403)
        response = await call_next(request)
        response.headers.update(
            {
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
            }
        )
        return response

    def current_session(request: Request) -> Session:
        session = sessions.get(request.cookies.get(SESSION_COOKIE))
        if session is None:
            raise HTTPException(status_code=401, detail="Sign in is required.")
        return session

    def require_mutation(request: Request, csrf: str | None) -> Session:
        session = current_session(request)
        origin = request.headers.get("origin")
        if origin != config.public_origin.rstrip("/"):
            raise HTTPException(status_code=403, detail="This request did not come from Updatarr.")
        if not csrf or not __import__("hmac").compare_digest(csrf, session.csrf_token):
            raise HTTPException(status_code=403, detail="Refresh the page and try again.")
        return session

    def require_local_agent(request: Request, token: str | None) -> None:
        if request.client is None or request.client.host not in {"127.0.0.1", "testclient"}:
            raise HTTPException(status_code=403, detail="This action must come from the managed computer.")
        if config.local_agent_token is None or not token or not __import__("hmac").compare_digest(token, config.local_agent_token):
            raise HTTPException(status_code=403, detail="The confirmation tool on this computer did not approve this request.")

    def current_plan(plan_id: str):  # type: ignore[no-untyped-def]
        value = store.plan(plan_id)
        if value is None:
            raise HTTPException(status_code=404, detail="That update plan was not found.")
        return value

    def validate_plan(plan, state, *, require_executable: bool = True):  # type: ignore[no-untyped-def]
        result = planner.validate(
            plan, store.latest_snapshot(), store.policies(),
            require_executable=require_executable,
        )
        if not result.valid:
            if state in {
                PlanState.AWAITING_REVIEW, PlanState.AWAITING_LOCAL_CONFIRMATION,
                PlanState.AWAITING_AUTHORIZATION, PlanState.READY_FOR_EXECUTION,
            }:
                store.transition_plan(plan.plan_id, state, result.state, "plan_validation_failed",
                                      "updatarr", {"reason": result.message})
            raise HTTPException(status_code=409, detail=result.message)
        return result

    @app.get(f"{base}/healthz")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(f"{base}/api/v1/session")
    async def login(body: LoginBody, request: Request, response: Response) -> dict[str, str | int]:
        try:
            session = sessions.authenticate(body.password, request.client.host if request.client else "unknown")
        except AuthenticationError as error:
            store.record_audit("sign_in_failed", "unknown", {"reason": "credentials_not_accepted"})
            raise HTTPException(status_code=401, detail=str(error)) from None
        store.record_audit("signed_in", "administrator", {"session_rotated": True})
        response.set_cookie(
            SESSION_COOKIE,
            session.session_id,
            httponly=True,
            secure=config.secure_cookie,
            samesite="strict",
            path=base or "/",
            max_age=config.session_ttl_seconds,
        )
        return {
            "api_version": API_VERSION,
            "csrf_token": session.csrf_token,
            "expires_in": config.session_ttl_seconds,
            "theme": saved_theme(),
        }

    @app.get(f"{base}/api/v1/session")
    async def session_status(request: Request) -> dict[str, str | int]:
        session = current_session(request)
        return {
            "api_version": API_VERSION,
            "csrf_token": session.csrf_token,
            "expires_in": sessions.remaining_seconds(session),
            "theme": saved_theme(),
        }

    @app.delete(f"{base}/api/v1/session")
    async def logout(request: Request, response: Response, x_csrf_token: str | None = Header(None)) -> dict[str, bool]:
        session = require_mutation(request, x_csrf_token)
        sessions.revoke(session.session_id)
        store.record_audit("signed_out", "administrator", {})
        response.delete_cookie(SESSION_COOKIE, path=base or "/")
        return {"signed_out": True}

    @app.put(f"{base}/api/v1/session/password")
    async def change_password(body: PasswordBody, request: Request, response: Response, x_csrf_token: str | None = Header(None)) -> dict[str, str]:
        require_mutation(request, x_csrf_token)
        try:
            session = sessions.change_password(body.current_password, body.new_password)
        except AuthenticationError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None
        store.record_audit("password_changed", "administrator", {"sessions_revoked": True})
        response.set_cookie(SESSION_COOKIE, session.session_id, httponly=True, secure=config.secure_cookie, samesite="strict", path=base or "/", max_age=config.session_ttl_seconds)
        return {"csrf_token": session.csrf_token}

    @app.get(f"{base}/api/v1/overview")
    async def overview(request: Request) -> dict[str, object]:
        current_session(request)
        active = inventory.active
        snapshot, updates = effective_updates()
        if snapshot is None:
            payload = {
                "mode": "Read-only",
                "snapshot": None,
                "summary": {"updates_found": 0, "ready_to_review": 0, "blocked": 0,
                            "restart_needed": 0, "software_recorded": 0},
                "sources": [
                    {"source_id": adapter.source_id, "name": adapter.name, "scope": adapter.scope,
                     "state": "not_checked", "state_label": "Not checked", "message": "No check has completed yet.",
                     "software_count": 0, "update_count": 0}
                    for adapter in adapters
                ],
                "task": active.to_dict() if active else None,
                "saved_choices": {"postponed": 0, "skipped": 0, "paused": 0},
            }
            publish_tray_status(payload)
            return payload
        summary = snapshot.summary()
        summary["ready_to_review"] = sum(update.state is SourceState.READY_TO_REVIEW for update in updates)
        payload = {
            "mode": "Read-only" if config.provider_mode == "live" else "Safe preview",
            "snapshot": {"snapshot_id": snapshot.snapshot_id, "completed_at": snapshot.completed_at,
                         "generation": snapshot.generation},
            "summary": summary,
            "sources": [source.to_dict(include_software=False) for source in snapshot.sources],
            "task": active.to_dict() if active else None,
            "saved_choices": saved_choice_counts(updates),
        }
        publish_tray_status(payload)
        return payload

    @app.post(f"{base}/api/v1/checks")
    async def start_check(request: Request, x_csrf_token: str | None = Header(None)) -> JSONResponse:
        require_mutation(request, x_csrf_token)
        task, created = inventory.start()
        return JSONResponse({"task": task.to_dict(), "created": created}, status_code=202 if created else 200)

    @app.delete(f"{base}/api/v1/checks/active")
    async def cancel_check(request: Request, x_csrf_token: str | None = Header(None)) -> JSONResponse:
        require_mutation(request, x_csrf_token)
        cancelled = await inventory.cancel()
        return JSONResponse({"cancelled": cancelled}, status_code=202 if cancelled else 409)

    @app.get(f"{base}/api/v1/inventory")
    async def inventory_page(request: Request, limit: int = 100, offset: int = 0, q: str = "") -> dict[str, object]:
        current_session(request)
        if limit < 1 or limit > 500 or offset < 0 or len(q) > 200:
            raise HTTPException(status_code=400, detail="The software list request is not valid.")
        return store.inventory_page(limit=limit, offset=offset, query=q).to_dict()

    @app.get(f"{base}/api/v1/updates")
    async def updates(request: Request) -> dict[str, object]:
        current_session(request)
        snapshot, effective = effective_updates()
        return {
            "snapshot_id": snapshot.snapshot_id if snapshot else None,
            "items": [item.to_dict() for item in effective],
            "saved_choices": saved_choice_counts(effective),
        }

    @app.get(f"{base}/api/v1/safety-readiness")
    async def safety_readiness(request: Request) -> dict[str, object]:
        """Return M4 classification only; this read has no provider side effect."""
        current_session(request)
        return simulator_report() if config.provider_mode == "simulator" else live_read_only_report(store.latest_snapshot())

    @app.post(f"{base}/api/v1/update-selection/check")
    async def check_selection(body: SelectionBody, request: Request, x_csrf_token: str | None = Header(None)) -> dict[str, object]:
        require_mutation(request, x_csrf_token)
        snapshot, effective = effective_updates()
        if snapshot is None or body.snapshot_id != snapshot.snapshot_id:
            raise HTTPException(status_code=409, detail="The update information changed. Check for updates again.")
        try:
            decision = check_update_selection(effective, body.selected_stable_ids)
        except PolicyError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None
        store.record_audit(
            "update_selection_checked", "administrator",
            {"allowed": decision.allowed, "selected_count": decision.selected_count},
        )
        return decision.to_dict()

    @app.post(f"{base}/api/v1/plans", status_code=201)
    async def prepare_plan(body: SelectionBody, request: Request, x_csrf_token: str | None = Header(None)) -> dict[str, object]:
        require_mutation(request, x_csrf_token)
        snapshot, effective = effective_updates()
        if snapshot is None or body.snapshot_id != snapshot.snapshot_id:
            raise HTTPException(status_code=409, detail="The update information changed. Check for updates again.")
        try:
            plan = planner.prepare(snapshot, effective, body.selected_stable_ids, store.policies())
            store.save_plan(plan)
        except (PlanningError, PolicyError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from None
        store.record_audit("update_plan_prepared", "administrator", {"plan_id": plan.plan_id, "digest": plan.digest})
        return {"plan": plan.to_dict(PlanState.AWAITING_REVIEW)}

    @app.get(f"{base}/api/v1/plans/latest")
    async def read_latest_plan(request: Request) -> dict[str, object]:
        current_session(request)
        value = store.latest_plan()
        if value is not None and value[1] in {
            PlanState.AWAITING_REVIEW, PlanState.AWAITING_LOCAL_CONFIRMATION,
            PlanState.AWAITING_AUTHORIZATION, PlanState.READY_FOR_EXECUTION,
        }:
            result = planner.validate(
                value[0], store.latest_snapshot(), store.policies(), require_executable=False,
            )
            if not result.valid:
                value = (value[0], result.state)
        matching_run = None if value is None else store.run_for_plan(value[0].plan_id)
        return {"plan": None if value is None else value[0].to_dict(value[1]),
                "run": None if matching_run is None else matching_run.to_dict()}

    @app.post(f"{base}/api/v1/plans/{{plan_id}}/review")
    async def approve_plan(plan_id: str, body: ReviewPlanBody, request: Request,
                           x_csrf_token: str | None = Header(None)) -> dict[str, object]:
        require_mutation(request, x_csrf_token)
        plan, state = current_plan(plan_id)
        if not __import__("hmac").compare_digest(plan.digest, body.digest):
            raise HTTPException(status_code=409, detail="The update plan changed after it was reviewed. Prepare and review it again.")
        validate_plan(plan, state)
        if state is not PlanState.AWAITING_REVIEW:
            raise HTTPException(status_code=409, detail="This plan has already moved past review.")
        store.transition_plan(plan_id, state, PlanState.AWAITING_LOCAL_CONFIRMATION,
                              "review_approved", "administrator", {"digest": plan.digest})
        store.record_audit("update_plan_reviewed", "administrator", {"plan_id": plan_id, "digest": plan.digest})
        return {"plan": plan.to_dict(PlanState.AWAITING_LOCAL_CONFIRMATION)}

    @app.post(f"{base}/api/v1/local/plans/{{plan_id}}/confirm")
    async def confirm_plan_here(plan_id: str, request: Request,
                                x_updatarr_local_agent: str | None = Header(None)) -> dict[str, object]:
        require_local_agent(request, x_updatarr_local_agent)
        plan, state = current_plan(plan_id)
        validate_plan(plan, state)
        if state is not PlanState.AWAITING_LOCAL_CONFIRMATION:
            raise HTTPException(status_code=409, detail="This plan is not waiting for confirmation on this computer.")
        requested = PlanState.AWAITING_AUTHORIZATION if plan.requires_administrator else PlanState.READY_FOR_EXECUTION
        store.transition_plan(plan_id, state, requested, "confirmed_on_managed_computer", "local-agent",
                              {"digest": plan.digest, "uid": os.getuid(), "session_id": "simulator-local-agent"})
        return {"plan": plan.to_dict(requested)}

    @app.post(f"{base}/api/v1/local/plans/{{plan_id}}/reject")
    async def reject_plan_here(plan_id: str, request: Request,
                               x_updatarr_local_agent: str | None = Header(None)) -> dict[str, object]:
        require_local_agent(request, x_updatarr_local_agent)
        plan, state = current_plan(plan_id)
        if state is not PlanState.AWAITING_LOCAL_CONFIRMATION:
            raise HTTPException(status_code=409, detail="This plan is not waiting for a decision on this computer.")
        store.transition_plan(plan_id, state, PlanState.INVALIDATED,
                              "rejected_on_managed_computer", "local-agent", {"digest": plan.digest})
        return {"plan": plan.to_dict(PlanState.INVALIDATED)}

    @app.post(f"{base}/api/v1/local/plans/{{plan_id}}/authorize")
    async def record_simulated_authorization(plan_id: str, request: Request,
                                             x_updatarr_local_agent: str | None = Header(None)) -> dict[str, object]:
        require_local_agent(request, x_updatarr_local_agent)
        if config.provider_mode != "simulator":
            raise HTTPException(status_code=503, detail="The restricted system tool needed for administrator changes has not been installed or approved.")
        plan, state = current_plan(plan_id)
        validate_plan(plan, state)
        if state is not PlanState.AWAITING_AUTHORIZATION:
            raise HTTPException(status_code=409, detail="This plan is not waiting for administrator permission.")
        store.transition_plan(plan_id, state, PlanState.READY_FOR_EXECUTION,
                              "simulated_authorization_granted", "local-agent", {"digest": plan.digest})
        return {"plan": plan.to_dict(PlanState.READY_FOR_EXECUTION)}

    @app.post(f"{base}/api/v1/local/plans/{{plan_id}}/execute")
    async def execute_simulated_plan(plan_id: str, request: Request,
                                     x_updatarr_local_agent: str | None = Header(None)) -> dict[str, object]:
        require_local_agent(request, x_updatarr_local_agent)
        if config.provider_mode != "simulator":
            raise HTTPException(status_code=503, detail="Live installation needs its separate approval and is not enabled.")
        plan, state = current_plan(plan_id)
        validate_plan(plan, state)
        if state is not PlanState.READY_FOR_EXECUTION:
            raise HTTPException(status_code=409, detail="This plan is not ready to run.")
        created = UpdateRun(
            f"run-{token_urlsafe(12)}", plan.plan_id, plan.digest, UpdateRunState.CREATED,
            0, "The reviewed plan has been claimed.", utc_now(),
        )
        try:
            store.claim_plan_for_run(created)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from None
        running = store.transition_run(
            created.run_id, UpdateRunState.CREATED, UpdateRunState.RUNNING,
            progress=0, message="Simulation is starting.",
        )
        cancellation = threading.Event()
        run_cancellations[created.run_id] = cancellation

        async def finish_simulation() -> None:
            try:
                result, _run_steps = await asyncio.to_thread(
                    simulator_executor.execute, plan, SimulatorResultChecker(),
                    run_id=created.run_id, started_at=created.started_at,
                    cancel_requested=cancellation.is_set,
                    event_callback=lambda event: store.record_run_progress(created.run_id, event),
                )
                store.transition_run(
                    created.run_id, UpdateRunState.RUNNING, result.state,
                    progress=result.progress, message=result.message, finished_at=result.finished_at,
                )
                store.record_audit("simulated_update_run_completed", "local-agent",
                                   {"plan_id": plan_id, "run_id": result.run_id, "result": result.state.value})
            finally:
                run_cancellations.pop(created.run_id, None)

        task = asyncio.create_task(finish_simulation())
        run_tasks.add(task)
        task.add_done_callback(run_tasks.discard)
        return {"plan": plan.to_dict(PlanState.CONSUMED), "run": running.to_dict(), "steps": []}

    @app.post(f"{base}/api/v1/local/plans/{{plan_id}}/cancel")
    async def cancel_simulated_run(plan_id: str, request: Request,
                                   x_updatarr_local_agent: str | None = Header(None)) -> dict[str, object]:
        require_local_agent(request, x_updatarr_local_agent)
        run = store.run_for_plan(plan_id)
        cancellation = run_cancellations.get(run.run_id) if run else None
        if run is None or run.state is not UpdateRunState.RUNNING or cancellation is None:
            raise HTTPException(status_code=409, detail="There is no running simulation to stop.")
        cancellation.set()
        return {"cancel_requested": True, "message": "The simulation will stop at its next safe point."}

    @app.get(f"{base}/api/v1/catalog")
    async def search_catalog(
        request: Request,
        q: str = "",
        source_id: str | None = None,
        scope: str | None = None,
        limit: int = 40,
    ) -> dict[str, object]:
        current_session(request)
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=400, detail="Choose between 1 and 100 search results.")
        if not catalog.adapters:
            return {
                "items": [], "sources": [], "query": q, "total": 0,
                "message": "Live catalog search is not available in this build.",
            }
        try:
            page = await asyncio.to_thread(
                catalog.search, q, source_id=source_id, scope=scope, limit=limit,
                turned_off=store.turned_off_sources(),
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None
        return page.to_dict()

    @app.get(f"{base}/api/v1/advisories")
    async def read_advisories(request: Request, limit: int = 10) -> dict[str, object]:
        current_session(request)
        if limit < 1 or limit > 50:
            raise HTTPException(status_code=400, detail="Choose between 1 and 50 notices.")
        return await asyncio.to_thread(advisories.read, limit)

    @app.get(f"{base}/api/v1/catalog/aur/{{package}}/build-preview")
    async def read_aur_build_preview(package: str, request: Request) -> dict[str, object]:
        current_session(request)
        try:
            return await asyncio.to_thread(
                aur_build_preview, package, simulated=config.provider_mode == "simulator"
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None
        except (OSError, TimeoutError):
            raise HTTPException(
                status_code=503,
                detail="The AUR build file could not be checked. Try again later.",
            ) from None

    @app.get(f"{base}/api/v1/policies")
    async def policies(request: Request, include_inactive: bool = False) -> dict[str, object]:
        current_session(request)
        values = store.policies(include_inactive=include_inactive)
        return {"items": [policy.to_dict() for policy in values], "total": len(values)}

    @app.post(f"{base}/api/v1/policies", status_code=201)
    async def create_policy(body: PolicyBody, request: Request, x_csrf_token: str | None = Header(None)) -> dict[str, object]:
        require_mutation(request, x_csrf_token)
        known_sources = {(adapter.source_id, adapter.scope) for adapter in adapters}
        if (body.source_id, body.scope) not in known_sources:
            raise HTTPException(status_code=400, detail="Choose an update source shown by Updatarr.")
        if body.kind != "turn_off_source" and not (
            body.source_id == "native" and body.software_id == "system-update-group"
        ):
            if body.target_stable_id is None:
                raise HTTPException(status_code=400, detail="Choose the exact recorded software item.")
            snapshot = store.latest_snapshot()
            target = next(
                (
                    update for update in snapshot.updates
                    if update.stable_id == body.target_stable_id
                ),
                None,
            ) if snapshot else None
            if (
                target is None or target.source_id != body.source_id
                or target.scope != body.scope or target.software_id != body.software_id
                or (body.kind == "skip_version" and target.available_version != body.version)
            ):
                raise HTTPException(status_code=409, detail="The recorded software information changed. Check again.")
        try:
            policy = new_policy(
                kind=PolicyKind(body.kind), source_id=body.source_id, scope=body.scope,
                software_id=body.software_id, target_stable_id=body.target_stable_id,
                version=body.version,
                expires_at=body.expires_at, reason=body.reason,
            )
            store.create_policy(policy)
        except (PolicyError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from None
        store.record_audit(
            "saved_choice_added", "administrator",
            {"policy_id": policy.policy_id, "kind": policy.kind.value,
             "source_id": policy.source_id, "scope": policy.scope},
        )
        return {"policy": policy.to_dict()}

    @app.delete(f"{base}/api/v1/policies/{{policy_id}}")
    async def remove_policy(policy_id: str, request: Request, x_csrf_token: str | None = Header(None)) -> dict[str, object]:
        require_mutation(request, x_csrf_token)
        if len(policy_id) > 100:
            raise HTTPException(status_code=400, detail="That saved choice is not valid.")
        policy = store.remove_policy(policy_id)
        if policy is None:
            raise HTTPException(status_code=404, detail="That saved choice was not found.")
        store.record_audit("saved_choice_removed", "administrator", {"policy_id": policy_id})
        return {"policy": policy.to_dict()}

    @app.get(f"{base}/api/v1/settings/update-sources")
    async def update_source_settings(request: Request) -> dict[str, object]:
        current_session(request)
        disabled = store.turned_off_sources()
        return {"items": [
            {"source_id": adapter.source_id, "scope": adapter.scope, "name": adapter.name,
             "enabled": (adapter.source_id, adapter.scope) not in disabled}
            for adapter in adapters
        ]}

    @app.put(f"{base}/api/v1/settings/update-sources/{{source_id}}/{{scope}}")
    async def save_update_source_setting(
        source_id: str,
        scope: str,
        body: SourceSettingBody,
        request: Request,
        x_csrf_token: str | None = Header(None),
    ) -> dict[str, object]:
        require_mutation(request, x_csrf_token)
        known_sources = {(adapter.source_id, adapter.scope) for adapter in adapters}
        if (source_id, scope) not in known_sources:
            raise HTTPException(status_code=404, detail="That update source was not found.")
        existing = next(
            (policy for policy in store.policies()
             if policy.kind is PolicyKind.TURN_OFF_SOURCE
             and policy.source_id == source_id and policy.scope == scope),
            None,
        )
        if body.enabled and existing:
            store.remove_policy(existing.policy_id)
        elif not body.enabled and not existing:
            store.create_policy(new_policy(
                kind=PolicyKind.TURN_OFF_SOURCE, source_id=source_id, scope=scope,
                reason="Turned off in Settings",
            ))
        store.record_audit(
            "update_source_setting_changed", "administrator",
            {"source_id": source_id, "scope": scope, "enabled": body.enabled},
        )
        return {"source_id": source_id, "scope": scope, "enabled": body.enabled}

    @app.get(f"{base}/api/v1/history")
    async def history(request: Request, limit: int = 50, offset: int = 0) -> dict[str, object]:
        current_session(request)
        if limit < 1 or limit > 200 or offset < 0:
            raise HTTPException(status_code=400, detail="The history page request is not valid.")
        audit = store.audit_page(limit=limit, offset=offset)
        imported = store.external_history_page(limit=limit, offset=offset)
        return {
            **audit.to_dict(),
            "imported_items": imported.items,
            "imported_total": imported.total,
            "import_batches": store.history_import_batches(),
            "summary": store.history_summary(),
        }

    @app.post(f"{base}/api/v1/history/import")
    async def import_history(request: Request, x_csrf_token: str | None = Header(None)) -> dict[str, int]:
        require_mutation(request, x_csrf_token)
        try:
            if config.provider_mode == "simulator":
                events_to_import = simulator_history()
                batches = (HistoryImportBatch(
                    batch_id="simulated-pacman-history-v1", source_id="native", scope="system",
                    status="incomplete", requested_range="simulated example records",
                    first_position="1", last_position=str(len(events_to_import)),
                    record_count=len(events_to_import), skipped_count=0,
                    reason="This is partial simulated history for interface testing.",
                    observed_at=utc_now(),
                ),)
            else:
                pacman_path = Path("/var/log/pacman.log")
                pacman_events, pacman_batch, pacman_state = read_pacman_history_report(
                    pacman_path,
                    previous=store.history_source_state(str(pacman_path)),
                )
                flatpak_events, flatpak_batches = read_flatpak_history_report(LiveProbeClient())
                events_to_import = (*pacman_events, *flatpak_events)
                batches = (pacman_batch, *flatpak_batches)
        except OSError:
            raise HTTPException(
                status_code=503,
                detail="The system package history could not be read. The original log was not changed.",
            ) from None
        imported_count = store.import_history(events_to_import)
        batch_count = store.record_history_batches(batches)
        if config.provider_mode != "simulator":
            store.save_history_source_state(pacman_state)
        store.record_audit(
            "outside_history_imported", "administrator",
            {"read_only_source": True, "found": len(events_to_import), "added": imported_count},
        )
        return {"found": len(events_to_import), "added": imported_count, "batches_added": batch_count}

    @app.get(f"{base}/api/v1/settings/appearance")
    async def appearance(request: Request) -> dict[str, str]:
        current_session(request)
        return {"theme": saved_theme()}

    @app.put(f"{base}/api/v1/settings/appearance")
    async def save_appearance(body: AppearanceBody, request: Request, x_csrf_token: str | None = Header(None)) -> dict[str, str]:
        require_mutation(request, x_csrf_token)
        if body.theme not in THEME_IDS:
            raise HTTPException(status_code=400, detail="Choose one of the available themes.")
        store.set_preference("administrator", "theme", body.theme)
        store.record_audit("appearance_changed", "administrator", {"theme": body.theme})
        return {"theme": body.theme}

    @app.get(f"{base}/api/v1/settings/export")
    async def export_settings(request: Request) -> JSONResponse:
        """Export ordinary preferences only; credentials and runtime state stay out."""
        current_session(request)
        disabled = store.turned_off_sources()
        document = {
            "format": "updatarr-settings",
            "version": 1,
            "exported_at": utc_now(),
            "appearance": {"theme": saved_theme()},
            "update_sources": [
                {"source_id": adapter.source_id, "scope": adapter.scope,
                 "enabled": (adapter.source_id, adapter.scope) not in disabled}
                for adapter in adapters
            ],
            "saved_choices": [
                policy.to_dict() for policy in store.policies()
                if policy.kind is not PolicyKind.TURN_OFF_SOURCE
            ],
        }
        return JSONResponse(
            document,
            headers={"Content-Disposition": 'attachment; filename="updatarr-settings.json"'},
        )

    @app.get(f"{base}/api/v1/events")
    async def event_stream(request: Request, last_event_id: str | None = Header(None)) -> StreamingResponse:
        stream_session = current_session(request)
        try:
            cursor = int(last_event_id) if last_event_id is not None else None
        except ValueError:
            cursor = -1

        async def stream() -> AsyncIterator[bytes]:
            queue = events.subscribe()
            sent_id = cursor or 0
            try:
                reset, history = events.after(cursor)
                if reset:
                    payload = json.dumps({"reason": "Event history is no longer available. Refresh current state."}, separators=(",", ":"))
                    sent_id = events.latest_id
                    yield f"event: reset\nid: {sent_id}\ndata: {payload}\n\n".encode()
                for item in history:
                    payload = json.dumps(item.data, separators=(",", ":"))
                    sent_id = item.id
                    yield f"event: {item.kind}\nid: {item.id}\ndata: {payload}\n\n".encode()
                yield b": Updatarr event stream ready\nretry: 1500\n\n"
                while sessions.get(stream_session.session_id) and not await request.is_disconnected():
                    try:
                        item = await asyncio.wait_for(queue.get(), timeout=1)
                    except TimeoutError:
                        yield b": keepalive\n\n"
                        continue
                    if item.id <= sent_id:
                        continue
                    payload = json.dumps(item.data, separators=(",", ":"))
                    sent_id = item.id
                    yield f"event: {item.kind}\nid: {item.id}\ndata: {payload}\n\n".encode()
            finally:
                events.unsubscribe(queue)

        return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache, no-store"})

    static_dir = config.static_dir
    if static_dir and static_dir.is_dir():
        assets = static_dir / "assets"

        @app.get(f"{base}/assets/{{asset_path:path}}")
        async def static_asset(asset_path: str) -> FileResponse:
            target = (assets / asset_path).resolve()
            if assets.resolve() not in target.parents or not target.is_file():
                raise HTTPException(status_code=404)
            return FileResponse(target)

        @app.get(f"{base}/{{spa_path:path}}")
        async def spa(spa_path: str) -> FileResponse:
            if spa_path == "healthz" or spa_path.startswith("api/"):
                raise HTTPException(status_code=404)
            return FileResponse(static_dir / "index.html")

    return app
