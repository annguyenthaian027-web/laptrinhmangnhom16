"""Cấu hình đọc từ biến môi trường (khớp với .env.example)."""
import os

PIHOLE_URL = os.getenv("PIHOLE_URL", "http://pihole:80").rstrip("/")
PIHOLE_PASSWORD = os.getenv("PIHOLE_PASSWORD", "")
DATA_DIR = os.getenv("DATA_DIR", "./data")

# MongoDB Atlas (tùy chọn). Để trống thì backend lưu trạng thái vào file như cũ.
MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DB = os.getenv("MONGODB_DB", "sinkholehome")
