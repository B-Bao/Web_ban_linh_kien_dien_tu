"""Logic lọc/sắp xếp sản phẩm dùng chung cho trang web và REST API."""
from decimal import Decimal, InvalidOperation

from django.db.models import Q

SORT_OPTIONS = {
    "newest": ("-created_at", "-id"),
    "price_asc": ("price", "id"),
    "price_desc": ("-price", "-id"),
    "name": ("name",),
}


def _to_decimal(value):
    try:
        d = Decimal(str(value).strip())
        return d if d >= 0 else None
    except (InvalidOperation, ValueError, AttributeError):
        return None


def filter_products(qs, params):
    """params: dict-like (request.GET hoặc request.query_params)."""
    q = (params.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(brand__icontains=q))

    category = (params.get("category") or "").strip()
    if category:
        qs = qs.filter(category__slug=category)

    brand = (params.get("brand") or "").strip()
    if brand:
        qs = qs.filter(brand__iexact=brand)

    min_price = _to_decimal(params.get("min_price", ""))
    if min_price is not None:
        qs = qs.filter(price__gte=min_price)
    max_price = _to_decimal(params.get("max_price", ""))
    if max_price is not None:
        qs = qs.filter(price__lte=max_price)

    if params.get("in_stock") in ("1", "true", "on"):
        qs = qs.filter(stock__gt=0)

    return qs.order_by(*SORT_OPTIONS.get(params.get("sort"), SORT_OPTIONS["newest"]))
