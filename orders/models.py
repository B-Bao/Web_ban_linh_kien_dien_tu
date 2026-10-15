from django.conf import settings
from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Chờ xác nhận"
        PROCESSING = "processing", "Đang xử lý"
        SHIPPING = "shipping", "Đang giao"
        COMPLETED = "completed", "Hoàn thành"
        CANCELLED = "cancelled", "Đã hủy"

    class PaymentMethod(models.TextChoices):
        COD = "cod", "Thanh toán khi nhận hàng (COD)"
        BANK = "bank", "Chuyển khoản ngân hàng"

    # Luồng trạng thái hợp lệ: Pending → Processing → Shipping → Completed
    # Có thể hủy khi đang Pending hoặc Processing (hoàn lại tồn kho).
    TRANSITIONS = {
        "pending": ["processing", "cancelled"],
        "processing": ["shipping", "cancelled"],
        "shipping": ["completed"],
        "completed": [],
        "cancelled": [],
    }

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    full_name = models.CharField("Người nhận", max_length=150)
    phone = models.CharField("SĐT", max_length=20)
    shipping_address = models.CharField("Địa chỉ giao hàng", max_length=255)
    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.COD)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    total_amount = models.DecimalField("Tổng tiền", max_digits=14, decimal_places=0, default=0)
    note = models.TextField("Ghi chú", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "Đơn hàng"
        verbose_name_plural = "Đơn hàng"

    def can_transition_to(self, new_status):
        return new_status in self.TRANSITIONS.get(self.status, [])

    @property
    def next_statuses(self):
        """Danh sách (value, label) các trạng thái có thể chuyển tới."""
        labels = dict(self.Status.choices)
        return [(s, labels[s]) for s in self.TRANSITIONS.get(self.status, [])]

    @property
    def can_cancel_by_customer(self):
        # Khách chỉ được tự hủy khi shop chưa xác nhận đơn
        return self.status == self.Status.PENDING

    def __str__(self):
        return f"Đơn #{self.pk}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, related_name="order_items")
    product_name = models.CharField(max_length=200)  # snapshot tên tại thời điểm mua
    quantity = models.PositiveIntegerField()
    price = models.DecimalField("Đơn giá", max_digits=12, decimal_places=0)  # snapshot giá

    @property
    def subtotal(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.product_name} x{self.quantity}"
