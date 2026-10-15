from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "product_name", "quantity", "price")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "total_amount", "payment_method", "status", "created_at")
    list_filter = ("status", "payment_method")
    search_fields = ("id", "user__username", "full_name", "phone")
    inlines = [OrderItemInline]
    # Đổi trạng thái phải qua trang quản trị của shop (có kiểm tra luồng + hoàn kho)
    readonly_fields = ("status", "total_amount", "user")
