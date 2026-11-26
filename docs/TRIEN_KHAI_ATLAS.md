# Đưa SinkholeHome lên web với MongoDB Atlas

## Cần hiểu trước

- **Pi-hole là máy chủ DNS** (cổng 53), không phải ứng dụng web. Vercel, Netlify, Render, Railway, GitHub Pages **không chạy được** Pi-hole.
  Cần một máy chủ chạy Docker: VPS (Oracle Cloud Always Free, DigitalOcean, Vultr...) hoặc Raspberry Pi.
- **MongoDB Atlas là cơ sở dữ liệu**, không chạy được Pi-hole. Trong bản này Atlas lưu: hồ sơ chặn đang dùng và nhật ký thao tác (`GET /api/history`).
- Kiến trúc đề xuất: một VPS chạy `docker compose --profile app up -d --build`, backend trên VPS nối ra Atlas.

```
Trình duyệt ──HTTPS──▶ Caddy ──▶ Frontend ──▶ Backend ──▶ Pi-hole
                                                  └──────▶ MongoDB Atlas
```

## Bước 1. Tạo cơ sở dữ liệu Atlas

1. Đăng ký tại https://www.mongodb.com/cloud/atlas, tạo cluster **M0 (miễn phí)**, chọn vùng gần (Singapore).
2. **Database Access** → Add New Database User: đặt tên + mật khẩu (nên dùng mật khẩu chỉ gồm chữ và số để khỏi phải mã hóa URL).
3. **Network Access** → Add IP Address: nhập **IP public của VPS**. Tránh `0.0.0.0/0`.
4. **Database** → Connect → Drivers → copy chuỗi `mongodb+srv://...`, thay `<password>`.

## Bước 2. Chuẩn bị VPS

```bash
# Ubuntu 22.04+, đã cài Docker
git clone https://github.com/annguyenthaian027-web/laptrinhmangnhom16.git
cd laptrinhmangnhom16
cp .env.example .env
nano .env      # đặt PIHOLE_PASSWORD, MONGODB_URI
docker compose --profile app up -d --build
```

Nếu cổng 53 bị chiếm (systemd-resolved), xem mục "Lỗi thường gặp" trong `HUONG_DAN_TRIEN_KHAI.md`.
Compose hiện map DNS ra cổng 5353, nên **không mở cổng 53/5353 ra Internet**.

## Bước 3. Kiểm tra Atlas đã nối

```bash
curl http://localhost:3000/api/health
curl http://localhost:3000/api/history
# {"storage":"mongodb","events":[...]}   -> đã dùng Atlas
# {"storage":"file","events":[]}         -> MONGODB_URI chưa được nhận
```
Đổi hồ sơ trên bảng điều khiển rồi tải lại `/api/history`; trong Atlas sẽ thấy collection `history` và `state`.

## Bước 4. Tên miền + HTTPS + mật khẩu (bắt buộc nếu mở ra web)

Bảng điều khiển **chưa có đăng nhập**: ai vào được là tắt chặn hoặc sửa danh sách được. Khi công khai phải thêm khóa, ví dụ bằng Caddy:

```bash
sudo apt install -y caddy
caddy hash-password        # nhập mật khẩu, copy chuỗi băm
```
`/etc/caddy/Caddyfile`:
```
sinkhole.tenmiencuaban.com {
    basicauth {
        admin <chuoi-bam-vua-tao>
    }
    reverse_proxy localhost:3000
}
```
```bash
sudo systemctl reload caddy
```
Trỏ bản ghi DNS A của tên miền về IP VPS. Caddy tự cấp HTTPS. Nên đóng cổng 3000 và 8080 trên firewall, chỉ mở 80, 443, 22 (và 51820/udp nếu dùng VPN).

## Lưu ý bảo mật

- Không commit `.env` (đã có trong `.gitignore`). Nếu lỡ đưa chuỗi kết nối lên GitHub, đổi mật khẩu user Atlas ngay.
- Backend đang cho CORS `*`; khi công khai nên giới hạn về tên miền của bạn.
- Nếu Atlas lỗi, API trả `503 STORAGE_UNAVAILABLE`; Pi-hole vẫn chặn quảng cáo bình thường.
