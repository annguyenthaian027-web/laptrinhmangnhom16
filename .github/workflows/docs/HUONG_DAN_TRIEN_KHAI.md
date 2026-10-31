# Hướng dẫn triển khai SinkholeHome (TV1)

Hệ thống gồm: **Pi-hole** (DNS sinkhole chặn quảng cáo), **Unbound** (DNS đệ quy riêng) và **WireGuard** qua `wg-easy` (VPN, có giao diện web tạo mã QR cho điện thoại).

Docker Compose chia thành 3 nhóm chạy:

| Lệnh | Chạy gì |
|---|---|
| `docker compose up -d` | Pi-hole + Unbound |
| `docker compose --profile vpn up -d` | Thêm WireGuard |
| `docker compose --profile app up -d --build` | Thêm backend + frontend |

## 0. Chuẩn bị chung

- Máy Linux (Ubuntu/Debian/Raspberry Pi OS) hoặc Windows có Docker Desktop.
- Cổng dùng: `53/tcp+udp` (DNS), `80`/`443` hoặc cổng đã đổi trong `.env` (web Pi-hole), `51820/udp` (WireGuard), `51821/tcp` (giao diện quản lý WireGuard).

## 1. Cài nhanh

Linux / Raspberry Pi / VPS:

```bash
git clone https://github.com/annguyenthaian027-web/laptrinhmangnhom16.git
cd laptrinhmangnhom16
chmod +x install.sh
./install.sh --vpn
```

Bỏ `--vpn` nếu chỉ cần Pi-hole + Unbound. Thêm `--app` để chạy cả backend và frontend.

Windows (PowerShell, quyền Administrator):

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1 -Vpn
```

Script sẽ hỏi mật khẩu Pi-hole, địa chỉ IP public (nếu dùng VPN) và mật khẩu trang quản lý WireGuard, rồi tự tạo file `.env`.

Kiểm tra: `docker compose ps`, các container phải ở trạng thái `Up`.
Vào `http://<ip-may>:<PIHOLE_WEB_PORT>/admin` và đăng nhập bằng mật khẩu Pi-hole.

## 2. Triển khai trên VPS

1. Thuê VPS Ubuntu 22.04 trở lên, mở firewall `51820/udp` và `22/tcp`.
2. Không mở cổng 53 ra Internet (dễ bị lợi dụng tấn công khuếch đại DDoS). Điện thoại dùng DNS qua VPN là đủ.
3. Đặt `WG_HOST` trong `.env` là IP public của VPS.
4. Chạy `./install.sh --vpn`.
5. Hạn chế mở cổng `51821` (trang quản lý WireGuard), chỉ truy cập khi cần hoặc qua SSH tunnel.

## 3. Triển khai trên Raspberry Pi

1. Cài Raspberry Pi OS Lite 64-bit, bật SSH, đặt IP tĩnh (hoặc cấp IP cố định trong router).
2. Chạy `./install.sh --vpn`.
3. Trên router, port-forward `51820/udp` về IP của Pi để dùng VPN từ ngoài nhà.
4. Nhà không có IP public cố định thì dùng DDNS (DuckDNS, No-IP) và điền vào `WG_HOST`.

## 4. Dùng cho cả mạng nhà qua router

1. Vào trang quản trị router (thường `192.168.1.1`).
2. Ở mục DHCP/LAN, đặt DNS server bằng IP của máy chạy SinkholeHome.
3. Kết nối lại Wi-Fi trên thiết bị (hoặc `ipconfig /renew` trên Windows).
4. Router không cho đổi DNS thì đổi thủ công từng thiết bị (mục 6).

## 5. WireGuard và mã QR cho điện thoại

1. Mở `http://<WG_HOST>:51821`, đăng nhập bằng mật khẩu WireGuard đã đặt.
2. Bấm **New Client**, đặt tên (ví dụ `phone`), bấm **Create**.
3. Bấm biểu tượng mã QR bên cạnh client.
4. Trên điện thoại cài app WireGuard, bấm dấu `+`, chọn quét mã QR, quét mã vừa hiện, bật công tắc.
5. Thiết bị VPN tự dùng Pi-hole (172.20.0.2) làm DNS. Mở thử một trang có quảng cáo để kiểm tra.

Laptop: bấm biểu tượng tải file `.conf` rồi import vào app WireGuard.

Lưu ý: không đưa file `.env` và thư mục `data/` lên GitHub (đã có trong `.gitignore`).

## 6. Cài DNS thủ công trên từng thiết bị (không dùng VPN)

| Thiết bị | Cách làm |
|---|---|
| Windows | Cài đặt, Mạng, Wi-Fi, Thuộc tính, Gán máy chủ DNS, Thủ công, IPv4, nhập IP máy chạy Pi-hole |
| Android | Cài đặt, Wi-Fi, giữ tên mạng, Sửa, IP: Tĩnh, DNS 1 = IP Pi-hole |
| iOS | Cài đặt, Wi-Fi, biểu tượng (i), Cấu hình DNS, Thủ công, thêm IP Pi-hole và xóa DNS cũ |

## 7. Lỗi thường gặp

**Cổng 53 bị chiếm (Ubuntu), do systemd-resolved:**

```bash
sudo sed -i 's/#DNSStubListener=yes/DNSStubListener=no/' /etc/systemd/resolved.conf
sudo systemctl restart systemd-resolved
docker compose up -d
```

**Cổng 80/443 bị chiếm:** đổi `PIHOLE_WEB_PORT` và `PIHOLE_WEB_HTTPS_PORT` trong `.env` (ví dụ 8081 và 8443).

**Không có mạng sau khi bật VPN:** kiểm tra đã mở `51820/udp` và `WG_HOST` đúng.

**Pi-hole không healthy:** xem `docker compose logs pihole`.

**Cập nhật:** `docker compose pull && docker compose up -d`.

## 8. CI/CD

Workflow `.github/workflows/ci.yml` chạy mỗi lần push, gồm 3 bước:
1. `lint`: yamllint cho compose và workflow, shellcheck cho `install.sh`.
2. `build`: kiểm tra cú pháp compose ở mọi profile, build backend/frontend nếu có Dockerfile.
3. `test-compose`: khởi động Pi-hole + Unbound, thử phân giải DNS và mở trang web Pi-hole.

## 9. Đối chiếu với tài liệu API

- Backend gọi Pi-hole qua `PIHOLE_URL=http://pihole:80` (tên service trong mạng Docker).
- Phiên bản Pi-hole đã dùng: chạy `docker exec pihole pihole -v` và ghi vào README.
