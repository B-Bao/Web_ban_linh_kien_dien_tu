# PCShop — Website quản lý & bán linh kiện máy tính

Bài tập nhóm môn **Lập trình với Python** · Django + Django REST Framework + SQLite (đổi được sang PostgreSQL) · Bootstrap 5 + Chart.js.

## 1. Chạy dự án

Yêu cầu: Python 3.10+.

```bash
# Cách nhanh (tự tạo venv, cài thư viện, tạo DB, nạp dữ liệu mẫu, chạy server)
bash setup.sh        # Linux/macOS
setup.bat            # Windows

# Hoặc từng bước
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations accounts catalog orders
python manage.py migrate
python manage.py seed_data          # dữ liệu demo (thêm --reset để xóa và tạo lại)
python manage.py runserver
python manage.py test               # chạy unit test
```

> **Lần chạy đầu tiên** sinh ra các file `*/migrations/0001_initial.py`. Một người trong nhóm
> commit các file này lên Git, những người còn lại chỉ cần `migrate` (không `makemigrations` lại).

| Tài khoản | Mật khẩu | Vai trò |
|---|---|---|
| `admin` | `admin123` | Quản trị (vào `/manage/` và `/admin/`) |
| `khach` | `khach123` | Khách hàng (có sẵn vài đơn mẫu) |

Các địa chỉ chính: `/` trang chủ · `/products/` · `/cart/` · `/orders/` · `/manage/` dashboard · `/api/` REST API.

## 2. Cấu trúc

```
pcshop/        settings, urls gốc, utils (BootstrapFormMixin)
accounts/      User tùy biến (full_name, phone, address, role), đăng ký/đăng nhập/hồ sơ
catalog/       Category, Product (specifications JSON), Review; lọc sản phẩm (filters.py); seed_data
orders/        Order, OrderItem; cart.py (giỏ hàng session); services.py (NGHIỆP VỤ ĐẶT HÀNG); views
dashboard/     Khu quản trị: CRUD sản phẩm & danh mục, xử lý đơn, thống kê (stats.py)
api/           DRF: products, categories, check-stock, cart, dashboard stats
templates/ static/   Giao diện Bootstrap 5 + cart.js (Fetch API)
```

Luồng: `Request → urls → View / DRF APIView → services/Model (ORM) → DB → HTML / JSON`.
**Quy tắc: logic nghiệp vụ đặt trong `services.py`, `filters.py`, `cart.py`, `stats.py` — view chỉ nhận request và trả response.**

## 3. Quy tắc nghiệp vụ đã cài đặt

| Chủ đề | Quy tắc | Nơi cài đặt |
|---|---|---|
| Phân quyền | `role=admin` hoặc superuser ⇒ `is_staff=True`; `/manage/` và `/api/dashboard/*` chỉ cho staff | `accounts/models.py`, `dashboard/decorators.py` |
| Giỏ hàng | Lưu trong session; không cho thêm/sửa quá tồn kho; SL = 0 ⇒ xóa dòng; sản phẩm bị ẩn tự rơi khỏi giỏ | `orders/cart.py` |
| Đặt hàng | Phải đăng nhập; kiểm tra tồn kho lúc đặt; **trừ kho nguyên tử** (`UPDATE ... WHERE stock >= qty`) trong `transaction.atomic`; lỗi ở bất kỳ sản phẩm nào ⇒ rollback cả đơn; lưu snapshot tên & giá | `orders/services.create_order` |
| Trạng thái đơn | `Pending → Processing → Shipping → Completed`; được hủy khi `Pending`/`Processing`; không nhảy cóc, không sửa đơn đã kết thúc | `Order.TRANSITIONS`, `services.change_status` |
| Hủy đơn | Hủy ⇒ **hoàn lại tồn kho**; khách chỉ tự hủy đơn của mình khi còn `Pending` | `services.cancel_by_customer` |
| Thanh toán | COD hoặc Chuyển khoản (hiển thị thông tin ngân hàng ở chi tiết đơn, cấu hình trong `settings.BANK_TRANSFER_INFO`) | `orders/models.py`, `order_detail.html` |
| Đánh giá | Chỉ khách có đơn **Completed** chứa sản phẩm mới được đánh giá; 1–5 sao; mỗi người 1 đánh giá/sản phẩm (gửi lại = cập nhật) | `catalog/services.user_can_review` |
| Xóa sản phẩm | Sản phẩm đã nằm trong đơn ⇒ không xóa cứng, chuyển sang "ngừng bán" | `dashboard/views.product_delete` |
| Doanh thu | Chỉ tính đơn Completed, theo ngày tạo đơn; Top bán chạy theo số lượng | `dashboard/stats.py` |

## 4. REST API

| Method & URL | Mô tả |
|---|---|
| `GET /api/products/?category=cpu&brand=AMD&min_price=&max_price=&q=&in_stock=1&sort=price_asc` | Danh sách + lọc (phân trang) |
| `GET /api/products/<id>/`, `GET /api/categories/` | Chi tiết sản phẩm, danh mục |
| `GET /api/check-stock/?product_id=1&quantity=2` | Kiểm tra tồn kho realtime |
| `POST /api/cart/add/`, `POST /api/cart/update/` | JSON `{product_id, quantity}`; `quantity=0` ⇒ xóa; 400 nếu vượt tồn kho |
| `GET /api/dashboard/revenue/?days=30`, `GET /api/dashboard/top-products/?limit=5` | Dữ liệu biểu đồ (chỉ staff) |

## 5. Chuyển sang PostgreSQL

```bash
pip install psycopg2-binary
export DB_ENGINE=postgres DB_NAME=pcshop DB_USER=postgres DB_PASSWORD=... DB_HOST=localhost
python manage.py migrate
```
Khi triển khai thật: đặt `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS`.

## 6. Gợi ý việc tiếp theo cho thành viên backend

Xem `docs/TASKS.md`.
