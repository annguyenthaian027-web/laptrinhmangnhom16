#!/usr/bin/env bash
# Cai dat SinkholeHome (Nhom 16) tren Linux / Raspberry Pi / VPS
# Dung: ./install.sh          (chay Pi-hole + Unbound)
#       ./install.sh --vpn    (them WireGuard)
#       ./install.sh --app    (them backend + frontend)
set -euo pipefail

cd "$(dirname "$0")"

PROFILES=()
for arg in "$@"; do
  case "$arg" in
    --vpn) PROFILES+=(--profile vpn) ;;
    --app) PROFILES+=(--profile app) ;;
    *) echo "Tham so khong hop le: $arg"; exit 1 ;;
  esac
done

echo "==> Kiem tra Docker..."
if ! command -v docker >/dev/null 2>&1; then
  echo "Chua co Docker. Dang cai bang script chinh thuc..."
  curl -fsSL https://get.docker.com | sh
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "Thieu Docker Compose plugin. Cai: sudo apt install docker-compose-plugin"
  exit 1
fi

echo "==> Tao file .env..."
if [ ! -f .env ]; then
  cp .env.example .env
  read -r -s -p "Nhap mat khau Pi-hole: " PASS
  echo
  if [ -n "$PASS" ]; then
    sed -i "s|^PIHOLE_PASSWORD=.*|PIHOLE_PASSWORD=${PASS}|" .env
  fi
  if [[ " ${PROFILES[*]:-} " == *" vpn "* ]]; then
    read -r -p "IP public hoac ten mien cua may nay: " HOST
    sed -i "s|^WG_HOST=.*|WG_HOST=${HOST}|" .env
    read -r -s -p "Nhap mat khau trang quan ly WireGuard: " WGPASS
    echo
    # wg-easy v14: tao hash bcrypt, trong .env phai doi $ thanh $$
    HASH=$(docker run --rm ghcr.io/wg-easy/wg-easy:14 wgpw "$WGPASS" | sed -E "s/^PASSWORD_HASH='(.*)'$/\1/" | sed 's/\$/$$/g')
    sed -i "s|^WG_PASSWORD_HASH=.*|WG_PASSWORD_HASH=${HASH}|" .env
  fi
else
  echo ".env da ton tai, giu nguyen."
fi

echo "==> Kiem tra cong 53..."
if ss -lntu 2>/dev/null | grep -qE ':53\s'; then
  echo "CANH BAO: cong 53 dang bi chiem (thuong la systemd-resolved)."
  echo "Xem docs/HUONG_DAN_TRIEN_KHAI.md muc 'Loi thuong gap' de xu ly."
fi

echo "==> Khoi dong..."
docker compose ${PROFILES[@]+"${PROFILES[@]}"} up -d

echo
WEBPORT=$(grep -E '^PIHOLE_WEB_PORT=' .env | cut -d= -f2)
echo "Xong! Giao dien Pi-hole: http://localhost:${WEBPORT}/admin"
