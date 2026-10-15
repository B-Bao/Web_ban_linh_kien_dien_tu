from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.filters import filter_products
from catalog.models import Category, Product
from dashboard import stats
from orders.cart import Cart, StockError

from .serializers import (
    CartItemSerializer,
    CategorySerializer,
    CheckStockQuerySerializer,
    ProductSerializer,
)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/categories/"""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = None


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/products/?category=cpu&brand=AMD&min_price=1000000&max_price=9000000
                      &q=ryzen&in_stock=1&sort=price_asc
    """

    serializer_class = ProductSerializer

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True).select_related("category")
        return filter_products(qs, self.request.query_params)


class CheckStockView(APIView):
    """GET /api/check-stock/?product_id=1&quantity=2 → kiểm tra tồn kho realtime."""

    permission_classes = [AllowAny]

    def get(self, request):
        s = CheckStockQuerySerializer(data=request.query_params)
        s.is_valid(raise_exception=True)
        pid, qty = s.validated_data["product_id"], s.validated_data["quantity"]
        product = Product.objects.filter(pk=pid, is_active=True).first()
        if product is None:
            return Response({"available": False, "stock": 0, "message": "Sản phẩm không tồn tại."}, status=404)
        available = product.stock >= qty
        if product.stock == 0:
            message = "Hết hàng."
        elif not available:
            message = f"Chỉ còn {product.stock} sản phẩm trong kho."
        else:
            message = "Còn hàng."
        return Response(
            {
                "product_id": product.pk,
                "name": product.name,
                "stock": product.stock,
                "requested": qty,
                "available": available,
                "message": message,
            }
        )


class _CartMutationView(APIView):
    permission_classes = [AllowAny]

    def mutate(self, cart, product_id, quantity):
        raise NotImplementedError

    def post(self, request):
        s = CartItemSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        cart = Cart(request)
        try:
            self.mutate(cart, s.validated_data["product_id"], s.validated_data["quantity"])
        except StockError as e:
            return Response({"ok": False, "message": e.message, "stock": e.stock, "cart": cart.summary()}, status=400)
        return Response({"ok": True, "cart": cart.summary()})


class CartAddView(_CartMutationView):
    """POST /api/cart/add/ {product_id, quantity}"""

    def mutate(self, cart, product_id, quantity):
        cart.add(product_id, max(1, quantity))


class CartUpdateView(_CartMutationView):
    """POST /api/cart/update/ {product_id, quantity}  (quantity=0 → xóa khỏi giỏ)"""

    def mutate(self, cart, product_id, quantity):
        cart.set(product_id, quantity)


class RevenueView(APIView):
    """GET /api/dashboard/revenue/?days=30 (chỉ staff)"""

    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            days = int(request.query_params.get("days", 30))
        except ValueError:
            days = 30
        return Response(stats.revenue_by_day(days))


class TopProductsView(APIView):
    """GET /api/dashboard/top-products/?limit=5 (chỉ staff)"""

    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            limit = max(1, min(int(request.query_params.get("limit", 5)), 20))
        except ValueError:
            limit = 5
        return Response(stats.top_products(limit))
