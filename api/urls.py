from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "api"

router = DefaultRouter()
router.register("products", views.ProductViewSet, basename="product")
router.register("categories", views.CategoryViewSet, basename="category")

urlpatterns = [
    path("check-stock/", views.CheckStockView.as_view(), name="check_stock"),
    path("cart/add/", views.CartAddView.as_view(), name="cart_add"),
    path("cart/update/", views.CartUpdateView.as_view(), name="cart_update"),
    path("dashboard/revenue/", views.RevenueView.as_view(), name="revenue"),
    path("dashboard/top-products/", views.TopProductsView.as_view(), name="top_products"),
] + router.urls
