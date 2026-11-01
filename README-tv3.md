# Danh sách chặn

Hệ thống **không** dùng file `.txt` thủ công. Danh sách chặn thật được khai báo trong
`backend/app/catalog.json` (các nguồn công khai: quảng cáo, mã độc, lừa đảo, cờ bạc, người lớn, mạng xã hội)
và được Pi-hole tải về khi áp dụng một hồ sơ chặn.

Muốn chặn thêm một tên miền riêng (ví dụ trang lừa đảo gặp ở Việt Nam), dùng mục
**"Danh sách tên miền riêng"** trên bảng điều khiển, hoặc gọi `POST /api/domains`.
