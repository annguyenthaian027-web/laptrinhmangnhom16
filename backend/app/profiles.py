"""Logic hồ sơ chặn: đọc catalog.json, lưu hồ sơ đang dùng, áp dụng vào Pi-hole."""
import json
import os
from pathlib import Path

from . import config
from .errors import ApiError
from .pihole import PiholeClient

MANAGED_PREFIX = "SinkholeHome"  # đánh dấu các danh sách do ứng dụng quản lý, để thay đổi khi đổi hồ sơ

_CATALOG_PATH = Path(__file__).parent / "catalog.json"


def load_catalog() -> dict:
    with open(_CATALOG_PATH, encoding="utf-8") as f:
        return json.load(f)


def _state_path() -> Path:
    return Path(config.DATA_DIR) / "state.json"


def get_active() -> str | None:
    try:
        return json.loads(_state_path().read_text(encoding="utf-8")).get("active")
    except (OSError, ValueError):
        return None


def set_active(profile_id: str) -> None:
    path = _state_path()
    os.makedirs(path.parent, exist_ok=True)
    path.write_text(json.dumps({"active": profile_id}), encoding="utf-8")


def list_profiles() -> dict:
    catalog = load_catalog()
    return {
        "active": get_active(),
        "profiles": [
            {"id": p["id"], "name": p["name"], "description": p["description"], "categories": p["categories"]}
            for p in catalog["profiles"]
        ],
    }


def find_profile(profile_id: str) -> dict:
    for p in load_catalog()["profiles"]:
        if p["id"] == profile_id:
            return p
    raise ApiError(404, "PROFILE_NOT_FOUND", f"Không có hồ sơ '{profile_id}'")


async def apply_profile(client: PiholeClient, profile_id: str) -> dict:
    """Thêm các danh sách chặn của hồ sơ, gỡ các danh sách cũ do ứng dụng quản lý."""
    profile = find_profile(profile_id)
    catalog = load_catalog()

    desired: dict[str, str] = {}  # địa chỉ danh sách -> ghi chú
    for cat in profile["categories"]:
        for url in catalog["categories"][cat]["urls"]:
            desired[url] = f"{MANAGED_PREFIX}:{cat}"

    existing = await client.list_adlists()
    existing_addresses = {item["address"] for item in existing}
    managed = [item["address"] for item in existing if str(item.get("comment") or "").startswith(MANAGED_PREFIX)]

    removed = 0
    for address in managed:
        if address not in desired:
            await client.delete_adlist(address)
            removed += 1

    added = 0
    for address, comment in desired.items():
        if address not in existing_addresses:
            await client.add_adlist(address, comment)
            added += 1

    set_active(profile_id)
    return {"active": profile_id, "listsAdded": added, "listsRemoved": removed}
