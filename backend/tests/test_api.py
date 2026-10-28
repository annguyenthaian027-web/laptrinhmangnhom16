"""Kiểm thử backend bằng một Pi-hole giả (không cần Docker).

Chạy:  cd backend && pip install -r requirements.txt && pytest -q
"""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import create_app
from app.pihole import PiholeClient


class FakePihole:
    """Mô phỏng các endpoint Pi-hole v6 mà backend dùng."""

    def __init__(self):
        self.blocking = "enabled"
        self.timer = None
        self.domains = {"allow": [], "deny": [{"domain": "ads.example.com", "comment": "test"}]}
        self.lists = []
        self.gravity_runs = 0
        self.down = False

    def handler(self, request: httpx.Request) -> httpx.Response:
        if self.down:
            raise httpx.ConnectError("down")
        path = request.url.path.removeprefix("/api")
        method = request.method
        body = json.loads(request.content) if request.content else {}

        if path == "/auth" and method == "POST":
            return httpx.Response(200, json={"session": {"valid": True, "sid": "abc"}})
        if path == "/auth" and method == "DELETE":
            return httpx.Response(204)
        if request.headers.get("sid") != "abc":
            return httpx.Response(401, json={"error": {"message": "unauthorized"}})

        if path == "/dns/blocking" and method == "GET":
            return httpx.Response(200, json={"blocking": self.blocking, "timer": self.timer})
        if path == "/dns/blocking" and method == "POST":
            self.blocking = "enabled" if body["blocking"] else "disabled"
            self.timer = body.get("timer")
            return httpx.Response(200, json={"blocking": self.blocking, "timer": self.timer})
        if path == "/stats/summary":
            return httpx.Response(200, json={
                "queries": {"total": 100, "blocked": 25, "percent_blocked": 25.04},
                "clients": {"active": 3},
                "gravity": {"domains_being_blocked": 1234},
            })
        if path == "/stats/top_domains":
            return httpx.Response(200, json={"domains": [{"domain": "a.com", "count": 5}]})

        if path.startswith("/domains/"):
            parts = path.split("/")  # ['', 'domains', type, 'exact', (domain)]
            dtype = parts[2]
            if method == "GET":
                return httpx.Response(200, json={"domains": self.domains[dtype]})
            if method == "POST":
                self.domains[dtype].append({"domain": body["domain"], "comment": body.get("comment", "")})
                return httpx.Response(201, json={})
            if method == "DELETE":
                name = parts[4]
                before = len(self.domains[dtype])
                self.domains[dtype] = [d for d in self.domains[dtype] if d["domain"] != name]
                return httpx.Response(204 if len(self.domains[dtype]) < before else 404)

        if path == "/lists" and method == "GET":
            return httpx.Response(200, json={"lists": self.lists})
        if path == "/lists" and method == "POST":
            self.lists.append({"address": body["address"], "comment": body["comment"]})
            return httpx.Response(201, json={})
        if path.startswith("/lists/") and method == "DELETE":
            from urllib.parse import unquote
            address = unquote(path.removeprefix("/lists/"))
            self.lists = [x for x in self.lists if x["address"] != address]
            return httpx.Response(204)
        if path == "/action/gravity":
            self.gravity_runs += 1
            return httpx.Response(200, text="done")
        return httpx.Response(404, json={"error": {"message": "not found"}})


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    fake = FakePihole()
    client = PiholeClient("http://pihole", "pw", transport=httpx.MockTransport(fake.handler))
    with TestClient(create_app(client)) as api:
        yield api, fake


def test_status_and_blocking(env):
    api, _ = env
    assert api.get("/api/status").json() == {"blocking": True, "timer": None}
    r = api.post("/api/blocking", json={"enabled": False, "timer": 300})
    assert r.status_code == 200 and r.json() == {"blocking": False, "timer": 300}
    assert api.post("/api/blocking", json={"enabled": "x"}).status_code == 400


def test_stats(env):
    api, _ = env
    assert api.get("/api/stats").json() == {
        "totalQueries": 100, "blockedQueries": 25, "blockedPercent": 25.0,
        "domainsOnBlocklist": 1234, "activeClients": 3,
    }
    assert api.get("/api/top-blocked?count=5").json()["domains"][0] == {"domain": "a.com", "count": 5}
    assert api.get("/api/top-allowed").status_code == 200
    assert api.get("/api/top-blocked?count=999").status_code == 400


def test_domains_crud(env):
    api, _ = env
    assert api.get("/api/domains?type=deny").json()["domains"][0]["domain"] == "ads.example.com"
    r = api.post("/api/domains", json={"domain": "Facebook.com", "type": "deny", "comment": "học"})
    assert r.status_code == 201 and r.json()["domain"] == "facebook.com"
    assert api.post("/api/domains", json={"domain": "facebook.com", "type": "deny"}).status_code == 409
    assert api.post("/api/domains", json={"domain": "http://x.com", "type": "deny"}).json()["code"] == "INVALID_DOMAIN"
    assert api.post("/api/domains", json={"domain": "x.com", "type": "zzz"}).json()["code"] == "INVALID_TYPE"
    assert api.delete("/api/domains/facebook.com?type=deny").json() == {"deleted": "facebook.com", "type": "deny"}
    assert api.delete("/api/domains/facebook.com?type=deny").status_code == 404


def test_profiles(env):
    api, fake = env
    body = api.get("/api/profiles").json()
    assert body["active"] is None and {p["id"] for p in body["profiles"]} == {"family", "kids", "study"}

    r = api.post("/api/profiles/kids/apply")
    assert r.status_code == 200 and r.json()["active"] == "kids" and r.json()["listsAdded"] >= 5
    assert fake.gravity_runs == 1
    kids_lists = len(fake.lists)

    # đổi sang hồ sơ khác: gỡ danh sách không còn dùng, thêm danh sách mới
    r = api.post("/api/profiles/family/apply")
    assert r.json()["listsRemoved"] >= 1
    assert len(fake.lists) < kids_lists
    assert api.get("/api/profiles").json()["active"] == "family"

    # áp dụng lại cùng hồ sơ: không có gì thay đổi
    assert api.post("/api/profiles/family/apply").json()["gravity"] == "unchanged"
    assert api.post("/api/profiles/nope/apply").status_code == 404


def test_health_and_pihole_down(env):
    api, fake = env
    assert api.get("/api/health").json() == {"backend": "ok", "pihole": "ok"}
    fake.down = True
    assert api.get("/api/health").json() == {"backend": "ok", "pihole": "unreachable"}
    r = api.get("/api/status")
    assert r.status_code == 502 and r.json()["code"] == "PIHOLE_UNREACHABLE"
