# Việc có thể làm tiếp (backend)

Khung và nghiệp vụ cốt lõi đã xong. Các hạng mục dưới đây là phần mở rộng, **chưa** có trong code:

- [ ] Tính tương thích linh kiện (Socket CPU ↔ Mainboard, DDR4/DDR5, công suất PSU) dựa trên `Product.specifications`.
- [ ] Phí vận chuyển / mã giảm giá trong `create_order`.
- [ ] Đồng bộ giỏ hàng session vào DB khi người dùng đăng nhập.
- [ ] Xác nhận thanh toán chuyển khoản (trường `paid_at` / trạng thái thanh toán).
- [ ] Gửi email xác nhận đơn (`django.core.mail`).
- [ ] Viết thêm test cho `dashboard/stats.py` và form sản phẩm.
- [ ] Phân quyền chi tiết hơn (nhân viên kho chỉ sửa tồn kho, v.v.).
- [ ] Triển khai: PostgreSQL, `collectstatic`, gunicorn + nginx.

Quy ước: nghiệp vụ mới đặt vào `services.py` của app tương ứng và có test trong `tests.py`.
