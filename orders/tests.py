from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Product, Review
from catalog.services import user_can_review

from .cart import Cart, StockError
from .models import Order
from .services import OrderError, cancel_by_customer, change_status, create_order

User = get_user_model()
SHIP = dict(full_name="A", phone="0912345678", shipping_address="Hà Nội", payment_method="cod")


class BaseCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u1", "u1@x.com", "pass12345")
        self.other = User.objects.create_user("u2", "u2@x.com", "pass12345")
        self.cat = Category.objects.create(name="CPU")
        self.p1 = Product.objects.create(category=self.cat, name="Ryzen 5", brand="AMD", price=5000000, stock=10)
        self.p2 = Product.objects.create(category=self.cat, name="Core i5", brand="Intel", price=4000000, stock=2)


class OrderServiceTests(BaseCase):
    def test_create_order_decrements_stock_and_snapshots_price(self):
        order = create_order(self.user, {self.p1.pk: 3, self.p2.pk: 1}, **SHIP)
        self.p1.refresh_from_db(); self.p2.refresh_from_db()
        self.assertEqual((self.p1.stock, self.p2.stock), (7, 1))
        self.assertEqual(order.total_amount, 3 * 5000000 + 4000000)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.p1.price = 1
        self.p1.save()
        self.assertEqual(order.items.get(product=self.p1).price, 5000000)

    def test_insufficient_stock_rolls_back_everything(self):
        with self.assertRaises(OrderError):
            create_order(self.user, {self.p1.pk: 1, self.p2.pk: 5}, **SHIP)
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 10)
        self.assertEqual(Order.objects.count(), 0)

    def test_status_flow(self):
        order = create_order(self.user, {self.p1.pk: 1}, **SHIP)
        with self.assertRaises(OrderError):
            change_status(order, Order.Status.COMPLETED)  # không được nhảy cóc
        for s in ("processing", "shipping", "completed"):
            order = change_status(order, s)
        self.assertEqual(order.status, "completed")
        with self.assertRaises(OrderError):
            change_status(order, "cancelled")

    def test_cancel_restores_stock(self):
        order = create_order(self.user, {self.p1.pk: 4}, **SHIP)
        change_status(order, "cancelled")
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 10)

    def test_customer_cancel_rules(self):
        order = create_order(self.user, {self.p1.pk: 1}, **SHIP)
        with self.assertRaises(OrderError):
            cancel_by_customer(order, self.other)
        change_status(order, "processing")
        with self.assertRaises(OrderError):
            cancel_by_customer(order, self.user)


class CartTests(BaseCase):
    def _cart(self):
        self.client.get(reverse("catalog:home"))  # tạo session
        from django.http import HttpRequest
        req = HttpRequest(); req.session = self.client.session
        return Cart(req)

    def test_cannot_exceed_stock(self):
        cart = self._cart()
        cart.add(self.p2.pk, 2)
        with self.assertRaises(StockError):
            cart.add(self.p2.pk, 1)

    def test_set_zero_removes(self):
        cart = self._cart()
        cart.add(self.p1.pk, 1)
        cart.set(self.p1.pk, 0)
        self.assertEqual(cart.count, 0)


class ReviewTests(BaseCase):
    def test_only_completed_buyers_can_review(self):
        self.assertFalse(user_can_review(self.user, self.p1))
        order = create_order(self.user, {self.p1.pk: 1}, **SHIP)
        self.assertFalse(user_can_review(self.user, self.p1))
        for s in ("processing", "shipping", "completed"):
            change_status(order, s)
        self.assertTrue(user_can_review(self.user, self.p1))
        self.assertFalse(user_can_review(self.other, self.p1))

    def test_review_view_updates_existing(self):
        order = create_order(self.user, {self.p1.pk: 1}, **SHIP)
        for s in ("processing", "shipping", "completed"):
            change_status(order, s)
        self.client.login(username="u1", password="pass12345")
        url = reverse("catalog:review_submit", args=[self.p1.slug])
        self.client.post(url, {"rating": 5, "comment": "ok"})
        self.client.post(url, {"rating": 3, "comment": "sửa"})
        self.assertEqual(Review.objects.filter(product=self.p1).count(), 1)
        self.assertEqual(Review.objects.get(product=self.p1).rating, 3)


class ApiAndViewTests(BaseCase):
    def test_check_stock_api(self):
        r = self.client.get("/api/check-stock/", {"product_id": self.p2.pk, "quantity": 5})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["available"])
        r = self.client.get("/api/check-stock/", {"product_id": self.p1.pk, "quantity": 1})
        self.assertTrue(r.json()["available"])

    def test_cart_update_api(self):
        r = self.client.post("/api/cart/update/", {"product_id": self.p2.pk, "quantity": 99}, content_type="application/json")
        self.assertEqual(r.status_code, 400)
        r = self.client.post("/api/cart/update/", {"product_id": self.p1.pk, "quantity": 2}, content_type="application/json")
        self.assertEqual(r.json()["cart"]["count"], 2)

    def test_product_filter_api(self):
        r = self.client.get("/api/products/", {"brand": "AMD", "max_price": 6000000})
        self.assertEqual([p["name"] for p in r.json()["results"]], ["Ryzen 5"])

    def test_dashboard_requires_staff(self):
        self.assertEqual(self.client.get("/manage/").status_code, 302)
        self.client.login(username="u1", password="pass12345")
        self.assertEqual(self.client.get("/manage/").status_code, 403)
        self.assertEqual(self.client.get("/api/dashboard/revenue/").status_code, 403)
        admin = User.objects.create_user("boss", "b@x.com", "pass12345", role="admin")
        self.client.force_login(admin)
        self.assertEqual(self.client.get("/manage/").status_code, 200)
        self.assertEqual(self.client.get("/api/dashboard/revenue/?days=7").status_code, 200)

    def test_checkout_flow(self):
        self.client.login(username="u1", password="pass12345")
        self.client.post(reverse("orders:cart_add"), {"product_id": self.p1.pk, "quantity": 2})
        r = self.client.post(reverse("orders:checkout"), {**SHIP, "note": ""})
        order = Order.objects.get()
        self.assertRedirects(r, reverse("orders:detail", args=[order.pk]))
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 8)

    def test_pages_render(self):
        for url in ("/", "/products/", f"/category/{self.cat.slug}/", f"/products/{self.p1.slug}/", "/cart/", "/accounts/login/", "/accounts/register/"):
            self.assertEqual(self.client.get(url).status_code, 200, url)
