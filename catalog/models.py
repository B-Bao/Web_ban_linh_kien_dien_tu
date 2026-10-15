from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg
from django.templatetags.static import static
from django.urls import reverse
from django.utils.text import slugify


def unique_slug(model, value, instance=None):
    """Sinh slug không dấu, không trùng trong bảng của model."""
    value = (value or "").replace("đ", "d").replace("Đ", "D")
    base = slugify(value) or "item"
    slug, i = base, 2
    qs = model.objects.all()
    if instance is not None and instance.pk:
        qs = qs.exclude(pk=instance.pk)
    while qs.filter(slug=slug).exists():
        slug = f"{base}-{i}"
        i += 1
    return slug


class Category(models.Model):
    name = models.CharField("Tên danh mục", max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField("Mô tả", blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Danh mục"
        verbose_name_plural = "Danh mục"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(Category, self.name, self)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:category", kwargs={"slug": self.slug})

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products", verbose_name="Danh mục")
    name = models.CharField("Tên linh kiện", max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    brand = models.CharField("Thương hiệu", max_length=100, db_index=True)
    price = models.DecimalField("Giá (VNĐ)", max_digits=12, decimal_places=0, validators=[MinValueValidator(0)])
    stock = models.PositiveIntegerField("Tồn kho", default=0)
    # Thông số kỹ thuật dạng {"Socket": "AM5", "Số nhân": "8", ...}
    specifications = models.JSONField("Thông số kỹ thuật", default=dict, blank=True)
    description = models.TextField("Mô tả", blank=True)
    image = models.ImageField("Ảnh", upload_to="products/", blank=True)
    image_url = models.URLField("Ảnh (URL)", blank=True, help_text="Dùng khi không upload file ảnh")
    is_active = models.BooleanField("Đang bán", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "Linh kiện"
        verbose_name_plural = "Linh kiện"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(Product, self.name, self)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:product_detail", kwargs={"slug": self.slug})

    @property
    def image_src(self):
        if self.image:
            return self.image.url
        if self.image_url:
            return self.image_url
        return static("img/no-image.svg")

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def average_rating(self):
        avg = self.reviews.aggregate(a=Avg("rating"))["a"]
        return round(avg, 1) if avg else 0

    @property
    def review_count(self):
        return self.reviews.count()

    def __str__(self):
        return self.name


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(
        "Số sao", validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField("Nhận xét", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["product", "user"], name="one_review_per_user_product"),
        ]
        verbose_name = "Đánh giá"
        verbose_name_plural = "Đánh giá"

    def __str__(self):
        return f"{self.user} - {self.product} ({self.rating}★)"
