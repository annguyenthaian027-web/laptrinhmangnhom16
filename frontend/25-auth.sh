#!/bin/sh
# Tạo cấu hình đăng nhập cơ bản cho nginx. Không đặt BASIC_AUTH_PASS thì không khóa (chạy nội bộ).
set -e
if [ -n "$BASIC_AUTH_PASS" ]; then
  printf '%s:%s\n' "${BASIC_AUTH_USER:-admin}" "$(openssl passwd -apr1 "$BASIC_AUTH_PASS")" > /etc/nginx/.htpasswd
  printf 'auth_basic "SinkholeHome";\nauth_basic_user_file /etc/nginx/.htpasswd;\n' > /etc/nginx/auth.conf
else
  echo 'auth_basic off;' > /etc/nginx/auth.conf
fi
