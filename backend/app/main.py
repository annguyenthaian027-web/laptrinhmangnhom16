"""SinkholeHome backend: cầu nối giữa giao diện web và API Pi-hole v6.

Chạy thử:  uvicorn app.main:app --reload --port 8080
Tài liệu tự động của FastAPI: http://localhost:8080/docs
"""
import re
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import config, profiles
from .errors import ApiError
from .pihole import PiholeClient

DOMAIN_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
TYPES = ("allow", "deny")


class BlockingIn(BaseModel):
    enabled: bool
    timer: Optional[int] = Field(default=None, ge=1)


class DomainIn(BaseModel):
    domain: str
    type: str
    comment: str = ""


def _check_type(value: str) -> str:
    if value not in TYPES:
        raise ApiError(400, "INVALID_TYPE", "type phải là 'allow' hoặc 'deny'")
    return value


def _check_domain(value: str) -> str:
    domain = value.strip().lower()
    if not DOMAIN_RE.match(domain):
        raise ApiError(400, "INVALID_DOMAIN", "Tên miền không hợp lệ (ví dụ đúng: example.com, không có http://)")
    return domain


def create_app(pihole_client: PiholeClient | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.pihole = pihole_client or PiholeClient(config.PIHOLE_URL, config.PIHOLE_PASSWORD)
        yield
        await app.state.pihole.close()

    app = FastAPI(title="SinkholeHome API", version="0.1", lifespan=lifespan)

    # Mạng nội bộ/VPN; frontend thường đi qua proxy nên CORS chỉ để thuận tiện khi phát triển
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    @app.exception_handler(ApiError)
    async def api_error_handler(_: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status, content={"error": exc.message, "code": exc.code})

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(status_code=400, content={"error": "Dữ liệu gửi lên không hợp lệ", "code": "INVALID_REQUEST"})

    def pihole(request: Request) -> PiholeClient:
        return request.app.state.pihole

    # ---------- trạng thái và bật/tắt chặn ----------
    @app.get("/api/status")
    async def status(request: Request):
        return await pihole(request).get_blocking()

    @app.post("/api/blocking")
    async def blocking(body: BlockingIn, request: Request):
        return await pihole(request).set_blocking(body.enabled, body.timer)

    # ---------- thống kê ----------
    @app.get("/api/stats")
    async def stats(request: Request):
        data = await pihole(request).summary()
        queries = data.get("queries", {})
        return {
            "totalQueries": queries.get("total", 0),
            "blockedQueries": queries.get("blocked", 0),
            "blockedPercent": round(float(queries.get("percent_blocked", 0) or 0), 1),
            "domainsOnBlocklist": data.get("gravity", {}).get("domains_being_blocked", 0),
            "activeClients": data.get("clients", {}).get("active", 0),
        }

    @app.get("/api/top-blocked")
    async def top_blocked(request: Request, count: int = Query(10, ge=1, le=50)):
        items = await pihole(request).top_domains(True, count)
        return {"domains": [{"domain": i.get("domain"), "count": i.get("count", 0)} for i in items]}

    @app.get("/api/top-allowed")
    async def top_allowed(request: Request, count: int = Query(10, ge=1, le=50)):
        items = await pihole(request).top_domains(False, count)
        return {"domains": [{"domain": i.get("domain"), "count": i.get("count", 0)} for i in items]}

    # ---------- whitelist / blacklist ----------
    @app.get("/api/domains")
    async def list_domains(request: Request, type: str = "deny"):
        dtype = _check_type(type)
        items = await pihole(request).list_domains(dtype)
        return {
            "type": dtype,
            "domains": [{"domain": i.get("domain"), "comment": i.get("comment") or ""} for i in items],
        }

    @app.post("/api/domains", status_code=201)
    async def add_domain(body: DomainIn, request: Request):
        dtype = _check_type(body.type)
        domain = _check_domain(body.domain)
        client = pihole(request)
        if any(i.get("domain") == domain for i in await client.list_domains(dtype)):
            raise ApiError(409, "DOMAIN_EXISTS", f"{domain} đã có trong danh sách {dtype}")
        await client.add_domain(dtype, domain, body.comment)
        return {"domain": domain, "type": dtype, "comment": body.comment}

    @app.delete("/api/domains/{domain}")
    async def delete_domain(domain: str, request: Request, type: str = Query(...)):
        dtype = _check_type(type)
        name = _check_domain(domain)
        if not await pihole(request).delete_domain(dtype, name):
            raise ApiError(404, "DOMAIN_NOT_FOUND", f"{name} không có trong danh sách {dtype}")
        return {"deleted": name, "type": dtype}

    # ---------- hồ sơ chặn ----------
    @app.get("/api/profiles")
    async def get_profiles():
        return profiles.list_profiles()

    @app.post("/api/profiles/{profile_id}/apply")
    async def apply_profile(profile_id: str, request: Request, background: BackgroundTasks):
        client = pihole(request)
        result = await profiles.apply_profile(client, profile_id)
        changed = result["listsAdded"] or result["listsRemoved"]
        if changed:
            background.add_task(_run_gravity, client)  # chạy nền, không bắt giao diện chờ
        result["gravity"] = "updating" if changed else "unchanged"
        return result

    # ---------- sức khỏe hệ thống ----------
    @app.get("/api/health")
    async def health(request: Request):
        try:
            await pihole(request).get_blocking()
            ph = "ok"
        except ApiError:
            ph = "unreachable"
        return {"backend": "ok", "pihole": ph}

    return app


async def _run_gravity(client: PiholeClient) -> None:
    try:
        await client.run_gravity()
    except ApiError:
        pass  # lỗi cập nhật nền không làm hỏng phản hồi; Pi-hole sẽ tự cập nhật theo lịch


app = create_app()
