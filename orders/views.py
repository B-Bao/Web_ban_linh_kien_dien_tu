from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from pcshop.utils import safe_redirect_target

from .cart import Cart, StockError
from .forms import CheckoutForm
from .models import Order
from .services import OrderError, cancel_by_customer, create_order


def cart_detail(request):
    cart = Cart(request)
    lines = cart.lines()
    return render(
        request,
        "orders/cart.html",
        {"lines": lines, "total": sum(l["subtotal"] for l in lines), "has_problem": any(not l["available"] for l in lines)},
    )


@require_POST
def cart_add(request):
    cart = Cart(request)
    try:
        cart.add(int(request.POST.get("product_id", 0)), int(request.POST.get("quantity", 1)))
        messages.success(request, "Đã thêm sản phẩm vào giỏ hàng.")
    except (ValueError, TypeError):
        messages.error(request, "Dữ liệu không hợp lệ.")
    except StockError as e:
        messages.error(request, e.message)
    return redirect(safe_redirect_target(request, "orders:cart"))


@require_POST
def cart_update(request):
    """Fallback không-JS: cập nhật số lượng 1 dòng."""
    cart = Cart(request)
    try:
        cart.set(int(request.POST.get("product_id", 0)), int(request.POST.get("quantity", 1)))
    except (ValueError, TypeError):
        messages.error(request, "Dữ liệu không hợp lệ.")
    except StockError as e:
        messages.error(request, e.message)
    return redirect("orders:cart")


@require_POST
def cart_remove(request):
    try:
        Cart(request).remove(int(request.POST.get("product_id", 0)))
    except (ValueError, TypeError):
        pass
    return redirect("orders:cart")


@login_required
def checkout(request):
    cart = Cart(request)
    lines = cart.lines()
    if not lines:
        messages.info(request, "Giỏ hàng của bạn đang trống.")
        return redirect("catalog:product_list")

    user = request.user
    form = CheckoutForm(
        request.POST or None,
        initial={"full_name": user.full_name, "phone": user.phone, "shipping_address": user.address},
    )
    if request.method == "POST" and form.is_valid():
        try:
            order = create_order(user, cart.raw(), **form.cleaned_data)
        except OrderError as e:
            messages.error(request, str(e))
            return redirect("orders:cart")
        cart.clear()
        messages.success(request, f"Đặt hàng thành công! Mã đơn của bạn là #{order.pk}.")
        return redirect("orders:detail", pk=order.pk)
    return render(
        request,
        "orders/checkout.html",
        {"form": form, "lines": lines, "total": sum(l["subtotal"] for l in lines)},
    )


@login_required
def order_list(request):
    qs = Order.objects.filter(user=request.user)
    page_obj = Paginator(qs, 10).get_page(request.GET.get("page"))
    return render(request, "orders/order_list.html", {"page_obj": page_obj})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related("items__product"), pk=pk, user=request.user)
    return render(
        request,
        "orders/order_detail.html",
        {"order": order, "bank": settings.BANK_TRANSFER_INFO},
    )


@login_required
@require_POST
def order_cancel(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    try:
        cancel_by_customer(order, request.user)
        messages.success(request, f"Đã hủy đơn #{order.pk}.")
    except OrderError as e:
        messages.error(request, str(e))
    return redirect("orders:detail", pk=pk)
