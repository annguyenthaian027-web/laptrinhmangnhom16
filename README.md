# Minh họa DNS Sinkhole (Pi-hole)

Bài tập nhóm số 2: Minh họa giao thức bằng công cụ AI.

Demo tương tác mô phỏng cách một hệ thống **DNS Sinkhole** (như Pi-hole) chặn quảng cáo và tên miền độc hại ngay tại tầng DNS.

## 1. Giới thiệu

DNS là thành phần nền tảng của mọi kết nối Internet nhưng cũng bị lợi dụng để phát tán quảng cáo, theo dõi người dùng và làm kênh điều khiển (C2) cho mã độc. DNS Sinkhole chặn các tên miền này bằng cách trả về địa chỉ vô hiệu (`0.0.0.0`) thay vì IP thật, áp dụng cho mọi thiết bị trong mạng cùng lúc.

Demo là một file HTML duy nhất, trực quan hóa từng bước của một truy vấn DNS qua Pi-hole.

## 2. Chức năng

| STT | Chức năng | Mô tả |
|---|---|---|
| 1 | Gửi truy vấn DNS | Nhập hoặc chọn tên miền, bấm "Gửi truy vấn DNS" (hoặc Enter) |
| 2 | Hoạt ảnh luồng gói tin | Gói tin di chuyển giữa Máy khách, Pi-hole, DNS Upstream và Web Server, kèm lời giải thích từng bước |
| 3 | Chặn tên miền (Sinkhole) | Tên miền nằm trong blocklist sẽ nhận `0.0.0.0` và không kết nối được |
| 4 | Chuyển tiếp và Cache | Tên miền hợp lệ được forward lên upstream, kết quả lưu cache cho lần sau |
| 5 | Bật/tắt Pi-hole | So sánh hành vi khi có và không có lớp lọc DNS |
| 6 | Quản lý blocklist | Thêm tên miền mới hoặc xóa tên miền khỏi danh sách chặn |
| 7 | Query Log | Ghi giờ, tên miền, kết quả (Cho phép/Đã chặn) và IP trả về |
| 8 | Thống kê | Tổng truy vấn, số đã chặn, tỉ lệ chặn |

## 3. Yêu cầu hệ thống

- Máy tính hoặc điện thoại có trình duyệt hiện đại: Chrome, Edge, Firefox hoặc Safari (bản mới).
- Không cần cài đặt phần mềm, không cần Internet, không cần server.

## 4. Cách chạy

1. Tải file `dns_sinkhole_demo.html` về máy (hoặc clone repo: `git clone <link-repo>`).
2. Nhấp đúp vào file để mở bằng trình duyệt.
3. Nhập tên miền, bấm **Gửi truy vấn DNS** và theo dõi kết quả.

## 5. Cơ chế hoạt động

```
Máy khách ──(1) A? domain──▶ Pi-hole ──(2) kiểm tra blocklist
                                 │
              Có trong blocklist │ Không có
                   ▼             ▼
        (3a) trả 0.0.0.0    (3b) kiểm tra cache
        (kết thúc, bị chặn)     │ chưa có
                                ▼
                         (4) forward ▶ DNS Upstream (1.1.1.1 / 8.8.8.8)
                                │ nhận IP
                                ▼
                         (5) lưu cache, trả IP cho máy khách
                                ▼
                         (6) máy khách kết nối Web Server
```

## 6. Cấu trúc mã nguồn

| Thành phần | Vai trò |
|---|---|
| HTML/CSS | Giao diện, hỗ trợ chế độ sáng/tối |
| SVG | Sơ đồ 4 nút và gói tin chuyển động |
| JavaScript | Logic: `blocked` (Set blocklist), `cache`, `run()` (xử lý truy vấn), `mv()` (hoạt ảnh), `addLog()` (log và thống kê) |

## 7. Test case

| ID | Bước thực hiện | Kết quả mong đợi |
|---|---|---|
| TC01 | Pi-hole bật, truy vấn `google.com` | Kết quả "Cho phép", IP `142.250.66.14`, gói tin đi qua upstream |
| TC02 | Truy vấn `google.com` lần thứ hai | "Cho phép", lấy từ cache (không gọi upstream) |
| TC03 | Truy vấn `ads.doubleclick.net` | "Đã chặn", IP `0.0.0.0` |
| TC04 | Truy vấn `sub.ads.doubleclick.net` | "Đã chặn" (tên miền con của tên miền bị chặn) |
| TC05 | Tắt Pi-hole, truy vấn `ads.doubleclick.net` | "Cho phép (không lọc)", có IP bình thường |
| TC06 | Thêm `facebook.com` vào blocklist, truy vấn | "Đã chặn", IP `0.0.0.0` |
| TC07 | Xóa `ads.doubleclick.net` khỏi blocklist (nút ✕), truy vấn lại | "Cho phép" |
| TC08 | Để trống ô tên miền, bấm gửi | Không có phản ứng, không lỗi |
| TC09 | Gửi 1 truy vấn được phép và 1 truy vấn bị chặn | Tổng 2, Đã chặn 1, Tỉ lệ 50% |
| TC10 | Mở file trên máy khác và trình duyệt khác (Chrome, Edge, Firefox) | Hoạt động giống nhau |

## 8. Hạn chế và hướng phát triển

- Demo mô phỏng luồng xử lý, **không gửi gói tin DNS thật**; địa chỉ IP là IP giả.
- Blocklist chỉ gồm vài tên miền mẫu.
- Hướng phát triển: triển khai Pi-hole thật trên Raspberry Pi hoặc máy Linux, dùng blocklist cộng đồng, thêm DNS-over-HTTPS (DoH), hiển thị cấu trúc gói tin DNS (header, flags, RCODE).

## 9. Công cụ AI sử dụng

- Công cụ: *(Claude AI)*
- Vai trò: hỗ trợ rà lỗi sai và giải thích.

## 10. Thành viên nhóm

| Thành viên | MSSV | Nhiệm vụ |
|---|---|---|
| *Hoàng Như Quỳnh 2431540301* | | Nghiên cứu lý thuyết|
| *Nguyễn Thái An 2431540180* | | Xây dựng demo bằng , trình diễn demo |
| *Vũ Trung Kiên 2431540068* | | viết nội dung slide và nội dung báo cáo |

## 11. Tài liệu tham khảo

- IDC / EfficientIP, "Global DNS Threat Report" (2019-2023).
- eyeo, "2026 Ad Blocking Report".
- Pi-hole: https://pi-hole.net
