
# SinkholeHome: Tài liệu API (v0.1)

Tài liệu này là **hợp đồng** giữa Backend (TV2) và Frontend (TV3). Cả hai bên làm theo đúng tài liệu này. Muốn đổi endpoint hoặc cấu trúc JSON thì **báo cả nhóm và sửa file này trước**, rồi mới sửa code.

## 1. Quy ước chung

| Mục | Quy ước |
|---|---|
| Base URL | `http://<host>:<BACKEND_PORT>/api` (mặc định `BACKEND_PORT=8080`) |
| Định dạng | Request và response đều là JSON, `Content-Type: application/json` |
| Thời gian | ISO 8601, ví dụ `2026-10-28T09:30:00Z` |
| Frontend | **Chỉ gọi backend của nhóm**, không gọi thẳng Pi-hole |
| Mật khẩu Pi-hole | Chỉ nằm trong `.env` của backend (`PIHOLE_PASSWORD`), không lộ ra trình duyệt |
| Xác thực (MVP) | Chưa có đăng nhập; backend chỉ mở trong mạng nội bộ hoặc qua VPN. Có thể thêm sau |

### Định dạng lỗi (dùng cho mọi endpoint)

```json
{ "error": "Mô tả lỗi ngắn gọn bằng tiếng Việt", "code": "MA_LOI" }
```

| HTTP | Khi nào | Ví dụ `code` |
|---|---|---|
| 400 | Dữ liệu gửi lên sai | `INVALID_DOMAIN`, `INVALID_TYPE` |
| 404 | Không tìm thấy | `PROFILE_NOT_FOUND`, `DOMAIN_NOT_FOUND` |
| 409 | Trùng dữ liệu | `DOMAIN_EXISTS` |
| 502 | Backend không gọi được Pi-hole | `PIHOLE_UNREACHABLE` |
| 500 | Lỗi khác | `INTERNAL_ERROR` |

### Biến môi trường (khớp với `.env.example`)

```
PIHOLE_URL=http://pihole:80
PIHOLE_PASSWORD=doi-mat-khau-nay
BACKEND_PORT=8080
```

---

## 2. Trạng thái và bật/tắt chặn

### `GET /api/status`

Xem Pi-hole đang bật hay tắt chặn. *(Backend gọi `GET /dns/blocking` của Pi-hole.)*

Response 200:

```json
{
  "blocking": true,
  "timer": null
}
```

- `blocking`: `true` nếu đang chặn.
- `timer`: số giây còn lại trước khi tự bật lại, hoặc `null` nếu không có hẹn giờ.

### `POST /api/blocking`

Bật hoặc tắt chặn. Có thể tắt tạm bằng `timer` (giây). *(Backend gọi `POST /dns/blocking`.)*

Request:

```json
{ "enabled": false, "timer": 300 }
```

- `enabled` (bắt buộc): `true` hoặc `false`.
- `timer` (không bắt buộc): chỉ dùng khi `enabled=false`; tắt trong N giây rồi tự bật lại.

Response 200:

```json
{ "blocking": false, "timer": 300 }
```

---

## 3. Thống kê

### `GET /api/stats`

Thống kê tổng quan. *(Backend gọi `GET /stats/summary`.)*

Response 200:

```json
{
  "totalQueries": 1250,
  "blockedQueries": 310,
  "blockedPercent": 24.8,
  "domainsOnBlocklist": 180000,
  "activeClients": 4
}
```

### `GET /api/top-blocked?count=10`

Top tên miền bị chặn nhiều nhất. *(Backend gọi `GET /stats/top_domains?blocked=true&count=...`.)*

Query: `count` (mặc định 10, tối đa 50).

Response 200:

```json
{
  "domains": [
    { "domain": "ads.doubleclick.net", "count": 85 },
    { "domain": "tracker.example.com", "count": 42 }
  ]
}
```

### `GET /api/top-allowed?count=10`

Giống endpoint trên nhưng cho tên miền được phép. *(Backend gọi `GET /stats/top_domains?blocked=false&count=...`.)*

Response 200: cùng cấu trúc với `/api/top-blocked`.

---

## 4. Whitelist / Blacklist

`type` có hai giá trị: `allow` (whitelist) và `deny` (blacklist).

### `GET /api/domains?type=deny`

Xem danh sách theo loại. *(Backend gọi `GET /domains/deny/exact` hoặc `/domains/allow/exact`.)*

Response 200:

```json
{
  "type": "deny",
  "domains": [
    { "domain": "ads.doubleclick.net", "comment": "Quảng cáo" },
    { "domain": "bad-site.example", "comment": "" }
  ]
}
```

### `POST /api/domains`

Thêm một tên miền.

Request:

```json
{ "domain": "facebook.com", "type": "deny", "comment": "Chặn giờ học" }
```

- `domain` (bắt buộc): tên miền hợp lệ, không có `http://` và không có đường dẫn.
- `type` (bắt buộc): `allow` hoặc `deny`.
- `comment` (không bắt buộc).

Response 201:

```json
{ "domain": "facebook.com", "type": "deny", "comment": "Chặn giờ học" }
```

Lỗi: 400 `INVALID_DOMAIN`, 409 `DOMAIN_EXISTS`.

### `DELETE /api/domains/{domain}?type=deny`

Xóa một tên miền khỏi danh sách.

Response 200:

```json
{ "deleted": "facebook.com", "type": "deny" }
```

Lỗi: 404 `DOMAIN_NOT_FOUND`.

---

## 5. Hồ sơ chặn (Profiles)

Hồ sơ chặn là **logic riêng của nhóm**, không phải tính năng có sẵn của Pi-hole. Backend lưu hồ sơ trong file JSON hoặc SQLite, và nguồn danh sách tên miền nằm trong thư mục `/blocklists`.

Hồ sơ mặc định cho MVP:

| `id` | Tên | Ý nghĩa |
|---|---|---|
| `family` | Gia đình | Chặn quảng cáo, mã độc, lừa đảo |
| `kids` | Trẻ em | Như Gia đình, thêm chặn cờ bạc và nội dung người lớn |
| `study` | Học tập | Như Gia đình, thêm chặn mạng xã hội và game |

### `GET /api/profiles`

Response 200:

```json
{
  "active": "family",
  "profiles": [
    {
      "id": "family",
      "name": "Gia đình",
      "description": "Chặn quảng cáo, mã độc, lừa đảo",
      "categories": ["ads", "malware", "phishing"]
    },
    {
      "id": "kids",
      "name": "Trẻ em",
      "description": "Thêm chặn cờ bạc và nội dung người lớn",
      "categories": ["ads", "malware", "phishing", "gambling", "adult"]
    }
  ]
}
```

- `active`: `id` của hồ sơ đang áp dụng, hoặc `null` nếu chưa áp dụng.

### `POST /api/profiles/{id}/apply`

Áp dụng một hồ sơ (thêm các danh sách chặn tương ứng vào Pi-hole).

Response 200:

```json
{ "active": "kids", "domainsAdded": 1520 }
```

Lỗi: 404 `PROFILE_NOT_FOUND`, 502 `PIHOLE_UNREACHABLE`.

> Ghi chú cho TV2: có hai cách áp dụng hồ sơ, hoặc thêm từng tên miền qua `/domains/...`, hoặc thêm danh sách (adlist) qua endpoint quản lý danh sách của Pi-hole. Hãy kiểm tra `https://<pihole>/api/docs` trên bản Pi-hole đang chạy để chọn cách đúng với phiên bản đó.

---

## 6. Kiểm tra sức khỏe hệ thống

### `GET /api/health`

Dùng cho Docker healthcheck và để TV1 kiểm tra kết nối backend ↔ Pi-hole.

Response 200:

```json
{ "backend": "ok", "pihole": "ok" }
```

Nếu không gọi được Pi-hole, vẫn trả 200 với `"pihole": "unreachable"`.

---

## 7. Dữ liệu giả cho Frontend (TV3)

Frontend có thể dùng sẵn các JSON ở trên làm dữ liệu giả để làm giao diện trước khi backend xong. Khi backend sẵn sàng, chỉ cần đổi địa chỉ gọi API, không cần sửa cấu trúc dữ liệu.

## 8. Quy tắc thay đổi

1. Sửa file này trước khi sửa code.
2. Báo trong nhóm chat và ghi rõ vào mô tả Pull Request.
3. Chỉ **thêm** trường mới khi có thể; hạn chế đổi tên hoặc xóa trường đang dùng.
4. Mỗi lần đổi, tăng số phiên bản ở tiêu đề (v0.1 → v0.2).

## 9. Việc cần kiểm chứng trên Pi-hole thật (TV1 + TV2)

- [ ] Mở `https://<pihole>/api/docs` và đối chiếu từng endpoint "Backend gọi ..." ở trên.
- [ ] Xác nhận endpoint whitelist/blacklist (`/domains/allow|deny/exact`) hoạt động trên phiên bản đã cài.
- [ ] Xác nhận cách áp dụng hồ sơ chặn (thêm tên miền hay thêm danh sách).
- [ ] Ghi lại phiên bản Pi-hole đã dùng vào `README.md`.
