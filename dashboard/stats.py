"""Thống kê cho Dashboard. Doanh thu chỉ tính đơn đã HOÀN THÀNH (theo ngày tạo đơn)."""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count, DecimalField, F, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from catalog.models import Product
from orders.models import Order, OrderItem


def revenue_by_day(days=30):
    days = max(1, min(int(days), 365))
    end = timezone.localdate()
    start = end - timedelta(days=days - 1)
    rows = (
        Order.objects.filter(status=Order.Status.COMPLETED, created_at__date__gte=start, created_at__date__lte=end)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Sum("total_amount"), orders=Count("id"))
        .order_by("day")
    )
    by_day = {r["day"]: r for r in rows}
    labels, revenue, orders = [], [], []
    for i in range(days):
        d = start + timedelta(days=i)
        row = by_day.get(d)
        labels.append(d.strftime("%d/%m"))
        revenue.append(int(row["total"]) if row else 0)
        orders.append(row["orders"] if row else 0)
    return {"labels": labels, "revenue": revenue, "orders": orders}


def top_products(limit=5):
    rows = (
        OrderItem.objects.filter(order__status=Order.Status.COMPLETED)
        .values("product_id", "product_name")
        .annotate(
            total_quantity=Sum("quantity"),
            total_revenue=Sum(F("quantity") * F("price"), output_field=DecimalField(max_digits=16, decimal_places=0)),
        )
        .order_by("-total_quantity", "-total_revenue")[:limit]
    )
    return [
        {
            "product_id": r["product_id"],
            "name": r["product_name"],
            "quantity": r["total_quantity"],
            "revenue": int(r["total_revenue"] or 0),
        }
        for r in rows
    ]


def overview():
    status_counts = dict(Order.objects.order_by().values_list("status").annotate(c=Count("id")))
    total_revenue = (
        Order.objects.filter(status=Order.Status.COMPLETED).aggregate(t=Sum("total_amount"))["t"] or 0
    )
    return {
        "total_revenue": int(total_revenue),
        "status_counts": [(label, status_counts.get(value, 0), value) for value, label in Order.Status.choices],
        "total_orders": sum(status_counts.values()),
        "pending_orders": status_counts.get(Order.Status.PENDING, 0),
        "total_products": Product.objects.filter(is_active=True).count(),
        "total_customers": get_user_model().objects.filter(is_staff=False).count(),
        "low_stock": Product.objects.filter(is_active=True, stock__lte=settings.LOW_STOCK_THRESHOLD).order_by("stock")[:8],
    }
