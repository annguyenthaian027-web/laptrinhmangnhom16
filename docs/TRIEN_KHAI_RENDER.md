# Đưa SinkholeHome lên Render

## Phải biết trước

Render chạy được **backend** và **frontend**, nhưng **không chạy được Pi-hole** (DNS server). Cần một VPS/Raspberry Pi chạy Pi-hole
(`docker compose up -d`), rồi backend trên Render gọi API Pi-hole qua Internet. Không có Pi-hole thì web lên được nhưng các nút báo lỗi 502.

Gói Render free ngủ sau 15 phút không dùng, lần mở đầu chậm khoảng 1 phút.

## Bước 1. Pi-hole trên VPS
```bash
cp .env.example .env     # đặt PIHOLE_PASSWORD mạnh, PIHOLE_WEB_PORT=8081
docker compose up -d
```
Mở firewall VPS cho cổng web Pi-hole (8081). **Không** mở cổng DNS (5353/53). Backend sẽ gọi `PIHOLE_URL=http://IP_VPS:8081`.
(Chưa có HTTPS nên mật khẩu đi dạng thường; tốt hơn là đặt Caddy/HTTPS trước Pi-hole.)

## Bước 2. MongoDB Atlas
Làm theo `TRIEN_KHAI_ATLAS.md` bước 1. Render free dùng IP ra ngoài thay đổi, nên Network Access phải cho `0.0.0.0/0`;
bù lại dùng mật khẩu user dài và ngẫu nhiên.

## Bước 3. Tạo dịch vụ trên Render
1. Đẩy code lên GitHub (có `render.yaml` ở thư mục gốc).
2. Render → New → **Blueprint** → chọn repo → Apply.
3. Điền các biến còn trống cho **sinkholehome-backend**: `PIHOLE_URL`, `PIHOLE_PASSWORD`, `MONGODB_URI`.
4. Chờ backend xong, copy URL của nó (dạng `https://sinkholehome-backend-xxxx.onrender.com`).
5. Với **sinkholehome-frontend** điền: `BACKEND_URL` = URL vừa copy (không có dấu `/` cuối), `BASIC_AUTH_PASS` = mật khẩu vào bảng điều khiển.
6. Deploy lại frontend, mở URL của frontend, đăng nhập `admin` + mật khẩu vừa đặt.

## Kiểm tra
- `https://<backend>/api/health` → `{"backend":"ok","pihole":"ok"}`
- `https://<backend>/api/history` → `"storage":"mongodb"`

## Lưu ý
- Backend có URL công khai và chưa có khóa riêng: ai biết URL backend gọi thẳng API được, bỏ qua mật khẩu của frontend.
  Muốn chặt hơn thì thêm kiểm tra khóa API ở backend.
- Không commit `.env`. Lộ mật khẩu thì đổi ngay.
