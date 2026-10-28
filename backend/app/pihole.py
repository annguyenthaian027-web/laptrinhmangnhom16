"""Client gọi API Pi-hole v6.

Các endpoint dưới đây dựa trên API v6 (đường dẫn gốc /api, xác thực bằng session ID).
Cần đối chiếu với https://<pihole>/api/docs trên bản Pi-hole thật đang chạy.
"""
import asyncio
from urllib.parse import quote

import httpx

from .errors import ApiError


class PiholeClient:
    def __init__(self, base_url: str, password: str, transport: httpx.AsyncBaseTransport | None = None):
        self._password = password
        self._sid: str | None = None
        self._lock = asyncio.Lock()
        self._http = httpx.AsyncClient(base_url=f"{base_url}/api", timeout=10, transport=transport)

    # ---------- phiên đăng nhập ----------
    async def _login(self) -> None:
        try:
            resp = await self._http.post("/auth", json={"password": self._password})
        except httpx.RequestError as exc:
            raise ApiError(502, "PIHOLE_UNREACHABLE", "Không kết nối được tới Pi-hole") from exc
        try:
            session = resp.json().get("session", {})
        except ValueError:
            session = {}
        if not session.get("valid") or not session.get("sid"):
            raise ApiError(502, "PIHOLE_AUTH_FAILED", "Đăng nhập Pi-hole thất bại, kiểm tra PIHOLE_PASSWORD")
        self._sid = session["sid"]

    async def _ensure_sid(self) -> str:
        async with self._lock:
            if not self._sid:
                await self._login()
            return self._sid  # type: ignore[return-value]

    async def close(self) -> None:
        try:
            if self._sid:
                await self._http.delete("/auth", headers={"sid": self._sid})
        except httpx.RequestError:
            pass
        await self._http.aclose()

    # ---------- gọi API chung ----------
    async def request(self, method: str, path: str, *, params=None, json=None,
                      timeout: float | None = None, _retry: bool = True) -> httpx.Response:
        sid = await self._ensure_sid()
        try:
            resp = await self._http.request(
                method, path, params=params, json=json, headers={"sid": sid},
                timeout=timeout if timeout is not None else httpx.USE_CLIENT_DEFAULT,
            )
        except httpx.RequestError as exc:
            raise ApiError(502, "PIHOLE_UNREACHABLE", "Không kết nối được tới Pi-hole") from exc
        if resp.status_code == 401 and _retry:
            self._sid = None
            return await self.request(method, path, params=params, json=json, timeout=timeout, _retry=False)
        return resp

    @staticmethod
    def _fail(resp: httpx.Response) -> ApiError:
        message = f"Pi-hole trả về lỗi {resp.status_code}"
        try:
            message = resp.json()["error"]["message"] or message
        except (ValueError, KeyError, TypeError):
            pass
        return ApiError(502, "PIHOLE_ERROR", message)

    async def _json(self, method: str, path: str, ok=(200, 201), **kw) -> dict:
        resp = await self.request(method, path, **kw)
        if resp.status_code not in ok:
            raise self._fail(resp)
        try:
            return resp.json()
        except ValueError:
            return {}

    # ---------- chặn quảng cáo ----------
    async def get_blocking(self) -> dict:
        data = await self._json("GET", "/dns/blocking")
        return {"blocking": data.get("blocking") == "enabled", "timer": data.get("timer")}

    async def set_blocking(self, enabled: bool, timer: int | None) -> dict:
        body = {"blocking": enabled, "timer": None if enabled else timer}
        data = await self._json("POST", "/dns/blocking", json=body)
        return {"blocking": data.get("blocking") == "enabled", "timer": data.get("timer")}

    # ---------- thống kê ----------
    async def summary(self) -> dict:
        return await self._json("GET", "/stats/summary")

    async def top_domains(self, blocked: bool, count: int) -> list[dict]:
        data = await self._json("GET", "/stats/top_domains",
                                params={"blocked": str(blocked).lower(), "count": count})
        return data.get("domains", [])

    # ---------- whitelist / blacklist ----------
    async def list_domains(self, dtype: str) -> list[dict]:
        data = await self._json("GET", f"/domains/{dtype}/exact")
        return data.get("domains", [])

    async def add_domain(self, dtype: str, domain: str, comment: str) -> None:
        await self._json("POST", f"/domains/{dtype}/exact",
                         json={"domain": domain, "comment": comment, "groups": [0], "enabled": True})

    async def delete_domain(self, dtype: str, domain: str) -> bool:
        resp = await self.request("DELETE", f"/domains/{dtype}/exact/{quote(domain, safe='')}")
        if resp.status_code == 404:
            return False
        if resp.status_code not in (200, 204):
            raise self._fail(resp)
        return True

    # ---------- danh sách chặn (adlist) ----------
    async def list_adlists(self) -> list[dict]:
        data = await self._json("GET", "/lists")
        return data.get("lists", [])

    async def add_adlist(self, address: str, comment: str) -> None:
        await self._json("POST", "/lists", params={"type": "block"},
                         json={"address": address, "comment": comment, "groups": [0], "enabled": True})

    async def delete_adlist(self, address: str) -> None:
        resp = await self.request("DELETE", f"/lists/{quote(address, safe='')}", params={"type": "block"})
        if resp.status_code not in (200, 204, 404):
            raise self._fail(resp)

    async def run_gravity(self) -> None:
        """Cập nhật gravity để Pi-hole tải các danh sách mới (mất vài chục giây)."""
        resp = await self.request("POST", "/action/gravity", timeout=300)
        if resp.status_code not in (200, 201, 204):
            raise self._fail(resp)
