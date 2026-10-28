# Backend 

Backend FastAPI nối giao diện web với API Pi-hole v6, theo đúng `docs/api.md`.

## Cấu trúc

```
app/main.py       các endpoint /api/...
app/pihole.py     client gọi API Pi-hole v6 (đăng nhập, gọi lại khi hết phiên)
app/profiles.py   logic hồ sơ chặn (Gia đình / Trẻ em / Học tập)
app/catalog.json  danh mục nhóm chặn và danh sách tên miền (TV3 có thể bổ sung)
tests/            kiểm thử bằng Pi-hole giả
```

## Chạy

Qua Docker (cùng cả hệ thống): `docker compose --profile app up -d --build`

Chạy riêng để phát triển:

```bash
cd backend
pip install -r requirements.txt
PIHOLE_URL=http://localhost:80 PIHOLE_PASSWORD=mat-khau uvicorn app.main:app --reload --port 8080
```

Mở `http://localhost:8080/docs` để thử các endpoint.

## Kiểm thử

```bash
pytest -q
```

## Thay đổi so với docs/api.md v0.1

`POST /api/profiles/{id}/apply` trả về `listsAdded`, `listsRemoved`, `gravity` thay cho `domainsAdded`
(hồ sơ được áp dụng bằng cách thêm danh sách chặn vào Pi-hole nên không đếm được số tên miền ngay).
