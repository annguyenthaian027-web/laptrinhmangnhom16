# Dự Án Hệ Thống Chặn Lọc Quảng Cáo & DNS (Pi-hole + Unbound)

Phần thi/Phân công của **Thành viên 3 (TV3)**: Phụ trách Frontend Dashboard, quản lý Blocklist và tài liệu hướng dẫn (QA)[cite: 1].

## 📂 Cấu trúc thư mục dự án
- `index.html`: Giao diện Dashboard quản trị (responsive, tiếng Việt, hỗ trợ bật/tắt bộ lọc)[cite: 1].
- `how-it-works.html`: Trang giải thích chi tiết cơ chế hoạt động phối hợp giữa DNS, Pi-hole và Unbound[cite: 1].
- `blocklists/`: Thư mục lưu trữ danh sách chặn[cite: 1].
  - `ads-block.txt`: Danh sách chặn tên miền quảng cáo[cite: 1].
  - `phishing-block.txt`: Danh sách chặn trang web lừa đảo, mã độc và cờ bạc tại Việt Nam[cite: 1].

## 📱 Hướng dẫn Kiểm thử (QA) & Cài đặt
TV3 đã thực hiện kịch bản kiểm thử trên các nền tảng[cite: 1]:
1. **Windows:** Cấu hình DNS thủ công trỏ về địa chỉ IP của hệ thống chặn lọc.
2. **Android / iOS:** Sử dụng cấu hình VPN hoặc WireGuard profile để mã hóa và định hướng phân giải DNS qua hệ thống nội bộ.

---
*Báo cáo hoàn thành nhiệm vụ TV3 của nhóm.*