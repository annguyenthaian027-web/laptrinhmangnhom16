# SinkholeHome: DNS Sinkhole chặn quảng cáo và mã độc trên nền Pi-hole

Bài tập nhóm 16, môn Lập trình mạng. SinkholeHome đóng gói Pi-hole thành một hệ thống cài bằng một lệnh,
có bảng điều khiển tiếng Việt để người không rành kỹ thuật vẫn dùng được.

## Tính năng

- Chặn quảng cáo, theo dõi, mã độc, lừa đảo ở tầng DNS cho mọi thiết bị dùng chung hệ thống.
- DNS đệ quy riêng tư bằng Unbound (không nhờ DNS bên thứ ba).
- Bảng điều khiển web: xem thống kê, bật/tắt chặn, tạm dừng 30 phút, chọn hồ sơ (Gia đình, Trẻ em, Học tập), quản lý danh sách tên miền riêng.
- Backend REST API (FastAPI) nối bảng điều khiển với API Pi-hole v6.
- VPN WireGuard (tùy chọn) để thiết bị bên ngoài mạng nhà vẫn đi qua hệ thống.

## Kiến trúc

```
Thiết bị ──DNS──▶ Pi-hole ──▶ Unbound
                    ▲
Trình duyệt ──▶ Frontend (nginx) ──/api──▶ Backend (FastAPI) ──REST──▶ Pi-hole
Thiết bị ngoài ──WireGuard──▶ Pi-hole
```

| Thư mục | Nội dung |
|---|---|
| `docker-compose.yml`, `.env.example` | Chạy cả hệ thống |
| `backend/` | API, logic hồ sơ chặn, test |
| `frontend/` | Bảng điều khiển và trang giải thích |
| `docs/api.md` | Tài liệu API |
| `blocklists/` | Ghi chú về nguồn danh sách chặn |
| `dns_sinkhole_demo.html` | Bản mô phỏng từ bài tập 2 |

## Cài đặt và chạy

Cần Docker Desktop (hoặc Docker Engine + Compose).

```bash
cp .env.example .env          # Windows: copy .env.example .env
# mở .env, đổi PIHOLE_PASSWORD
docker compose --profile app up -d --build
```

- Bảng điều khiển: http://localhost:3000
- Trang quản trị Pi-hole: http://localhost/admin
- Chỉ chạy Pi-hole và Unbound: `docker compose up -d`
- Thêm VPN: `docker compose --profile app --profile vpn up -d --build` (cần điền `WG_HOST`, `WG_PASSWORD_HASH` trong `.env`)

Nếu cổng 80/443 bị chiếm, đổi `PIHOLE_WEB_PORT` và `PIHOLE_WEB_HTTPS_PORT` trong `.env`.
Không mở cổng DNS (53) ra Internet công khai; dùng VPN khi cần truy cập từ ngoài.

## Kiểm thử backend

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate    # macOS/Linux: source .venv/bin/activate
pip install fastapi httpx pytest
python -m pytest -q
```

## Trạng thái kiểm thử

| Hạng mục | Kết quả |
|---|---|
| Backend: 5 test tự động với Pi-hole giả | Đạt (5/5) |
| Pi-hole + Unbound chạy thật bằng Docker | *Điền sau khi chạy, kèm ảnh chụp* |
| Backend nối Pi-hole thật | *Điền sau khi chạy* |
| Bảng điều khiển gọi backend thật | *Điền sau khi chạy* |
| Cấu hình DNS trên Windows / điện thoại | *Điền sau khi thử* |
| WireGuard | *Điền sau khi thử hoặc ghi "chưa thực hiện"* |

## Phân công

| Thành viên | Phần phụ trách |
|---|---|
| TV1 | Hạ tầng: Docker Compose, Unbound, WireGuard, triển khai |
| TV2 | Backend: API, hồ sơ chặn, test |
| TV3 | Bảng điều khiển, danh sách chặn, kiểm thử, tài liệu |

## Công cụ hỗ trợ

Nhóm có dùng công cụ AI để hỗ trợ viết mã và tài liệu; các thành viên tự rà soát, chạy thử và chỉnh sửa.

## Hạn chế và hướng phát triển

Chưa có đăng nhập cho bảng điều khiển (hệ thống nên chỉ chạy trong mạng nội bộ hoặc qua VPN), chưa có lịch chặn theo giờ,
chưa có danh sách riêng cho các trang lừa đảo và cờ bạc tại Việt Nam.
