"""Lưu trạng thái ứng dụng: MongoDB Atlas nếu có MONGODB_URI, ngược lại dùng file JSON.

Lưu hai thứ:
  - hồ sơ chặn đang dùng (collection "state", một document id="active")
  - nhật ký thao tác (collection "history"): đổi hồ sơ, bật/tắt chặn...

Các hàm ở đây là đồng bộ (pymongo); gọi qua asyncio.to_thread trong code async.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .errors import ApiError

_client = None


def use_mongo() -> bool:
    return bool(config.MONGODB_URI)


def _col(name: str):
    """Trả về collection MongoDB (tạo kết nối một lần, dùng lại)."""
    global _client
    if _client is None:
        from pymongo import MongoClient  # import muộn để chạy không cần pymongo khi dùng file

        _client = MongoClient(config.MONGODB_URI, serverSelectionTimeoutMS=5000)
    return _client[config.MONGODB_DB][name]


def _mongo_error() -> ApiError:
    return ApiError(503, "STORAGE_UNAVAILABLE", "Không kết nối được MongoDB Atlas, kiểm tra MONGODB_URI và Network Access")


def _state_path() -> Path:
    return Path(config.DATA_DIR) / "state.json"


def get_active() -> str | None:
    if use_mongo():
        try:
            doc = _col("state").find_one({"_id": "active"})
        except Exception as exc:  # PyMongoError và lỗi DNS/TLS
            raise _mongo_error() from exc
        return doc.get("profile") if doc else None
    try:
        return json.loads(_state_path().read_text(encoding="utf-8")).get("active")
    except (OSError, ValueError):
        return None


def set_active(profile_id: str) -> None:
    if use_mongo():
        try:
            _col("state").update_one({"_id": "active"}, {"$set": {"profile": profile_id}}, upsert=True)
        except Exception as exc:
            raise _mongo_error() from exc
        return
    path = _state_path()
    os.makedirs(path.parent, exist_ok=True)
    path.write_text(json.dumps({"active": profile_id}), encoding="utf-8")


def log_event(action: str, detail: dict | None = None) -> None:
    """Ghi nhật ký. Chỉ có tác dụng khi dùng MongoDB; lỗi ghi nhật ký không làm hỏng yêu cầu."""
    if not use_mongo():
        return
    try:
        _col("history").insert_one(
            {"time": datetime.now(timezone.utc), "action": action, "detail": detail or {}}
        )
    except Exception:
        pass


def history(limit: int = 20) -> list[dict]:
    if not use_mongo():
        return []
    try:
        rows = _col("history").find({}, {"_id": 0}).sort("time", -1).limit(limit)
        return [
            {"time": r["time"].isoformat(), "action": r["action"], "detail": r.get("detail", {})}
            for r in rows
        ]
    except Exception as exc:
        raise _mongo_error() from exc
