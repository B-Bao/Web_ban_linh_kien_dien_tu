from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

phone_validator = RegexValidator(
    regex=r"^(0|\+84)\d{9,10}$",
    message="Số điện thoại không hợp lệ (ví dụ: 0912345678).",
)


class User(AbstractUser):
    """User tùy biến: thêm họ tên, SĐT, địa chỉ và phân quyền theo role."""

    class Role(models.TextChoices):
        CUSTOMER = "customer", "Khách hàng"
        ADMIN = "admin", "Quản trị"

    full_name = models.CharField("Họ và tên", max_length=150, blank=True)
    phone = models.CharField("Số điện thoại", max_length=20, blank=True, validators=[phone_validator])
    address = models.CharField("Địa chỉ", max_length=255, blank=True)
    role = models.CharField("Vai trò", max_length=20, choices=Role.choices, default=Role.CUSTOMER)

    def save(self, *args, **kwargs):
        # Quy tắc: superuser luôn là admin; role admin tự động có quyền vào khu quản trị
        if self.is_superuser:
            self.role = self.Role.ADMIN
        if self.role == self.Role.ADMIN:
            self.is_staff = True
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return self.full_name or self.username

    def __str__(self):
        return self.display_name
