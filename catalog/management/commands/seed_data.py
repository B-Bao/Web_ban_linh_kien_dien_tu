"""Tạo dữ liệu demo: python manage.py seed_data  (thêm --reset để xóa dữ liệu cũ)."""
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from catalog.models import Category, Product, Review
from orders.models import Order
from orders.services import OrderError, change_status, create_order

CATEGORIES = {
    "CPU": "Bộ vi xử lý Intel / AMD",
    "VGA": "Card đồ họa NVIDIA / AMD",
    "RAM": "Bộ nhớ trong DDR4 / DDR5",
    "SSD": "Ổ cứng thể rắn SATA / NVMe",
    "Mainboard": "Bo mạch chủ",
    "Nguồn (PSU)": "Nguồn máy tính",
}

# (danh mục, tên, hãng, giá, tồn kho, thông số)
PRODUCTS = [
    ("CPU", "AMD Ryzen 5 7600X", "AMD", 5490000, 25, {"Socket": "AM5", "Số nhân / luồng": "6 / 12", "Xung nhịp": "4.7 - 5.3 GHz", "TDP": "105W", "RAM hỗ trợ": "DDR5"}),
    ("CPU", "AMD Ryzen 7 7800X3D", "AMD", 11990000, 8, {"Socket": "AM5", "Số nhân / luồng": "8 / 16", "Cache": "96MB 3D V-Cache", "TDP": "120W", "RAM hỗ trợ": "DDR5"}),
    ("CPU", "Intel Core i5-13400F", "Intel", 5190000, 30, {"Socket": "LGA1700", "Số nhân / luồng": "10 / 16", "Xung nhịp": "2.5 - 4.6 GHz", "TDP": "65W", "RAM hỗ trợ": "DDR4 / DDR5"}),
    ("CPU", "Intel Core i7-14700K", "Intel", 10990000, 12, {"Socket": "LGA1700", "Số nhân / luồng": "20 / 28", "Xung nhịp": "3.4 - 5.6 GHz", "TDP": "125W", "RAM hỗ trợ": "DDR4 / DDR5"}),
    ("VGA", "NVIDIA GeForce RTX 4060 8GB", "ASUS", 8490000, 15, {"GPU": "RTX 4060", "VRAM": "8GB GDDR6", "Nguồn đề nghị": "550W", "Cổng nguồn": "1 x 8-pin"}),
    ("VGA", "NVIDIA GeForce RTX 4070 Super 12GB", "MSI", 16990000, 6, {"GPU": "RTX 4070 Super", "VRAM": "12GB GDDR6X", "Nguồn đề nghị": "650W", "Cổng nguồn": "1 x 16-pin"}),
    ("VGA", "AMD Radeon RX 7800 XT 16GB", "Gigabyte", 13490000, 0, {"GPU": "RX 7800 XT", "VRAM": "16GB GDDR6", "Nguồn đề nghị": "700W", "Cổng nguồn": "2 x 8-pin"}),
    ("RAM", "Corsair Vengeance 16GB (2x8GB) DDR5 5600", "Corsair", 1990000, 40, {"Dung lượng": "16GB (2x8GB)", "Chuẩn": "DDR5", "Bus": "5600 MHz", "Latency": "CL36"}),
    ("RAM", "Kingston Fury Beast 32GB (2x16GB) DDR4 3200", "Kingston", 2290000, 35, {"Dung lượng": "32GB (2x16GB)", "Chuẩn": "DDR4", "Bus": "3200 MHz", "Latency": "CL16"}),
    ("SSD", "Samsung 980 Pro 1TB NVMe", "Samsung", 2990000, 20, {"Dung lượng": "1TB", "Chuẩn": "M.2 NVMe PCIe 4.0", "Đọc / Ghi": "7000 / 5000 MB/s"}),
    ("SSD", "WD Blue SA510 500GB SATA", "Western Digital", 990000, 50, {"Dung lượng": "500GB", "Chuẩn": "SATA III 2.5\"", "Đọc / Ghi": "560 / 510 MB/s"}),
    ("Mainboard", "ASUS TUF Gaming B650-PLUS WiFi", "ASUS", 5290000, 10, {"Socket": "AM5", "Chipset": "B650", "RAM hỗ trợ": "DDR5", "Kích thước": "ATX"}),
    ("Mainboard", "MSI PRO B760M-A WiFi DDR4", "MSI", 3490000, 18, {"Socket": "LGA1700", "Chipset": "B760", "RAM hỗ trợ": "DDR4", "Kích thước": "mATX"}),
    ("Nguồn (PSU)", "Corsair RM750e 750W 80 Plus Gold", "Corsair", 2790000, 14, {"Công suất": "750W", "Chuẩn": "80 Plus Gold", "Modular": "Full modular"}),
    ("Nguồn (PSU)", "Cooler Master MWE 550W Bronze", "Cooler Master", 1290000, 3, {"Công suất": "550W", "Chuẩn": "80 Plus Bronze", "Modular": "Non-modular"}),
]


class Command(BaseCommand):
    help = "Tạo dữ liệu demo (danh mục, sản phẩm, tài khoản, đơn hàng mẫu)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Xóa đơn hàng, sản phẩm, danh mục demo trước khi tạo")

    @transaction.atomic
    def handle(self, *args, **opts):
        User = get_user_model()
        if opts["reset"]:
            Order.objects.all().delete()
            Review.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()

        cats = {}
        for name, desc in CATEGORIES.items():
            cats[name], _ = Category.objects.get_or_create(name=name, defaults={"description": desc})

        for cat, name, brand, price, stock, specs in PRODUCTS:
            Product.objects.update_or_create(
                name=name,
                defaults={"category": cats[cat], "brand": brand, "price": price, "stock": stock, "specifications": specs,
                          "description": f"{name} chính hãng, bảo hành 36 tháng."},
            )

        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@pcshop.local", "admin123", full_name="Quản trị viên")
        customer = User.objects.filter(username="khach").first()
        if customer is None:
            customer = User.objects.create_user(
                "khach", "khach@pcshop.local", "khach123",
                full_name="Nguyễn Văn Khách", phone="0912345678", address="12 Lê Lợi, Hà Nội",
            )

        if not Order.objects.exists():
            self._demo_orders(customer)

        self.stdout.write(self.style.SUCCESS(
            "Seed xong. Tài khoản: admin / admin123 (quản trị) • khach / khach123 (khách hàng)"
        ))

    def _demo_orders(self, customer):
        rng = random.Random(42)
        in_stock = list(Product.objects.filter(stock__gte=5, is_active=True))
        now = timezone.now()
        for i in range(12):
            chosen = rng.sample(in_stock, k=rng.randint(1, 3))
            items = {p.pk: rng.randint(1, 2) for p in chosen}
            try:
                order = create_order(
                    customer, items, full_name=customer.full_name, phone=customer.phone,
                    shipping_address=customer.address, payment_method=rng.choice(["cod", "bank"]),
                )
            except OrderError:
                continue  # hết hàng demo → bỏ qua đơn này
            # i < 9: hoàn thành, 9: đang giao, 10: đang xử lý, 11: chờ xác nhận
            flow = ["processing", "shipping", "completed"]
            steps = 3 if i < 9 else {9: 2, 10: 1, 11: 0}[i]
            for s in flow[:steps]:
                change_status(order, s)
            Order.objects.filter(pk=order.pk).update(created_at=now - timedelta(days=rng.randint(0, 25)))
            if i < 9:
                for item in order.items.all():
                    Review.objects.get_or_create(
                        product=item.product, user=customer,
                        defaults={"rating": rng.randint(4, 5), "comment": "Hàng chính hãng, giao nhanh."},
                    )
