from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Product
from orders.models import Order
from orders.services import change_status, create_order

from . import stats

User = get_user_model()
SHIP = dict(full_name="A", phone="0912345678", shipping_address="Hà Nội", payment_method="cod")


class DashboardBase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("boss", "b@x.com", "pass12345", role="admin")
        self.customer = User.objects.create_user("c1", "c@x.com", "pass12345")
        self.cat = Category.objects.create(name="CPU")
        self.p1 = Product.objects.create(category=self.cat, name="Ryzen 5", brand="AMD", price=5000000, stock=20)
        self.p2 = Product.objects.create(category=self.cat, name="Core i5", brand="Intel", price=4000000, stock=20)
        self.client.force_login(self.admin)

    def complete(self, items):
        order = create_order(self.customer, items, **SHIP)
        for s in ("processing", "shipping", "completed"):
            order = change_status(order, s)
        return order


class StatsTests(DashboardBase):
    def test_revenue_counts_only_completed_orders(self):
        self.complete({self.p1.pk: 2})                       # 10.000.000
        create_order(self.customer, {self.p2.pk: 1}, **SHIP)  # pending: không tính
        data = stats.revenue_by_day(7)
        self.assertEqual(len(data["labels"]), 7)
        self.assertEqual(sum(data["revenue"]), 10000000)
        self.assertEqual(stats.overview()["total_revenue"], 10000000)

    def test_top_products_sorted_by_quantity(self):
        self.complete({self.p1.pk: 1, self.p2.pk: 3})
        top = stats.top_products(5)
        self.assertEqual(top[0]["name"], "Core i5")
        self.assertEqual(top[0]["quantity"], 3)
        self.assertEqual(top[0]["revenue"], 12000000)


class CategoryCrudTests(DashboardBase):
    def test_create_update_delete(self):
        self.client.post(reverse("dashboard:category_create"), {"name": "Đồ họa", "description": ""})
        cat = Category.objects.get(name="Đồ họa")
        self.assertEqual(cat.slug, "do-hoa")
        self.client.post(reverse("dashboard:category_update", args=[cat.pk]), {"name": "VGA", "description": "x"})
        cat.refresh_from_db()
        self.assertEqual(cat.name, "VGA")
        self.client.post(reverse("dashboard:category_delete", args=[cat.pk]))
        self.assertFalse(Category.objects.filter(pk=cat.pk).exists())

    def test_cannot_delete_category_with_products(self):
        self.client.post(reverse("dashboard:category_delete", args=[self.cat.pk]))
        self.assertTrue(Category.objects.filter(pk=self.cat.pk).exists())

    def test_customer_cannot_access(self):
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse("dashboard:category_list")).status_code, 403)


class ProductAndOrderCrudTests(DashboardBase):
    def test_product_create_parses_specs(self):
        r = self.client.post(reverse("dashboard:product_create"), {
            "category": self.cat.pk, "name": "Ryzen 7", "brand": "AMD", "price": 8000000, "stock": 5,
            "specs_text": "Socket: AM5\nTDP: 105W", "description": "", "image_url": "", "is_active": "on",
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Product.objects.get(name="Ryzen 7").specifications, {"Socket": "AM5", "TDP": "105W"})

    def test_product_specs_invalid_line(self):
        r = self.client.post(reverse("dashboard:product_create"), {
            "category": self.cat.pk, "name": "X", "brand": "B", "price": 1, "stock": 1,
            "specs_text": "khong co dau hai cham", "description": "", "image_url": "",
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Product.objects.filter(name="X").exists())

    def test_delete_product_in_order_only_deactivates(self):
        self.complete({self.p1.pk: 1})
        self.client.post(reverse("dashboard:product_delete", args=[self.p1.pk]))
        self.p1.refresh_from_db()
        self.assertFalse(self.p1.is_active)

    def test_admin_changes_order_status_and_invalid_jump_is_rejected(self):
        order = create_order(self.customer, {self.p1.pk: 2}, **SHIP)
        url = reverse("dashboard:order_detail", args=[order.pk])
        self.client.post(url, {"status": "completed"})  # nhảy cóc → bị từ chối
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)
        self.client.post(url, {"status": "cancelled"})
        order.refresh_from_db(); self.p1.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual(self.p1.stock, 20)  # đã hoàn kho
