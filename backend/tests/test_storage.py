"""Kiểm thử lớp lưu trữ bằng collection MongoDB giả (không cần Atlas)."""
from app import config, storage


class FakeCursor(list):
    def sort(self, key, direction):
        return FakeCursor(sorted(self, key=lambda d: d[key], reverse=direction < 0))

    def limit(self, n):
        return FakeCursor(self[:n])


class FakeCollection:
    def __init__(self):
        self.docs = []

    def find_one(self, flt):
        return next((d for d in self.docs if all(d.get(k) == v for k, v in flt.items())), None)

    def update_one(self, flt, update, upsert=False):
        doc = self.find_one(flt)
        if doc is None and upsert:
            doc = dict(flt)
            self.docs.append(doc)
        if doc is not None:
            doc.update(update["$set"])

    def insert_one(self, doc):
        self.docs.append(dict(doc))

    def find(self, flt, projection=None):
        return FakeCursor({k: v for k, v in d.items() if k != "_id"} for d in self.docs)


def test_file_mode(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(config, "MONGODB_URI", "")
    assert storage.get_active() is None
    storage.set_active("kids")
    assert storage.get_active() == "kids"
    assert storage.history() == []


def test_mongo_mode(monkeypatch):
    cols = {"state": FakeCollection(), "history": FakeCollection()}
    monkeypatch.setattr(config, "MONGODB_URI", "mongodb+srv://fake")
    monkeypatch.setattr(storage, "_col", lambda name: cols[name])
    assert storage.get_active() is None
    storage.set_active("study")
    storage.set_active("kids")
    assert storage.get_active() == "kids"
    storage.log_event("apply_profile", {"profile": "study"})
    storage.log_event("blocking", {"enabled": False})
    events = storage.history(10)
    assert [e["action"] for e in events] == ["blocking", "apply_profile"]
