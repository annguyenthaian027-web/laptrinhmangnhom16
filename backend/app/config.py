"""Cấu hình đọc từ biến môi trường (khớp với .env.example)."""
import os

PIHOLE_URL = os.getenv("PIHOLE_URL", "http://pihole:80").rstrip("/")
PIHOLE_PASSWORD = os.getenv("PIHOLE_PASSWORD", "")
DATA_DIR = os.getenv("DATA_DIR", "./data")
