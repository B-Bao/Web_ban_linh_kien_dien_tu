"""
Nghiệp vụ đặt hàng - toàn bộ quy tắc quan trọng nằm ở đây (không nằm trong view).

1. create_order(): kiểm tra tồn kho, trừ kho nguyên tử, snapshot giá/tên sản phẩm.
2. change_status(): chỉ cho phép chuyển trạng thái theo Order.TRANSITIONS,
   hủy đơn thì hoàn lại tồn kho.
3. cancel_by_customer(): khách chỉ hủy được đơn của mình khi còn Pending.
"""
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from catalog.models import Product

from .models import Order, OrderItem


class OrderError(Exception):
    pass


@transaction.atomic
def create_order(user, items, *, full_name, phone, shipping_address, payment_method, note=""):
    """items: {product_id: quantity}. Raise OrderError nếu không hợp lệ."""
    if not items:
        raise OrderError("Giỏ hàng đang trống.")
    if payment_method not in dict(Order.PaymentMethod.choices):
        raise OrderError("Phương thức thanh toán không hợp lệ.")

    products = Product.objects.in_bulk(list(items))
    order = Order.objects.create(
        user=user,
        full_name=full_name,
        phone=phone,
        shipping_address=shipping_address,
        payment_method=payment_method,
        note=note,
    )
    total = 0
    for pid, qty in items.items():
        product = products.get(pid)
        if qty <= 0:
            raise OrderError("Số lượng sản phẩm không hợp lệ.")
        if product is None or not product.is_active:
            raise OrderError("Có sản phẩm trong giỏ không còn được bán.")
        # Trừ kho có điều kiện (an toàn khi nhiều người mua cùng lúc):
        # chỉ cập nhật nếu stock >= qty, ngược lại 0 dòng bị ảnh hưởng.
        updated = Product.objects.filter(pk=pid, stock__gte=qty).update(
            stock=F("stock") - qty, updated_at=timezone.now()
        )
        if not updated:
            product.refresh_from_db()
            raise OrderError(f"“{product.name}” chỉ còn {product.stock} sản phẩm, không đủ số lượng bạn chọn.")
        OrderItem.objects.create(
            order=order, product=product, product_name=product.name, quantity=qty, price=product.price
        )
        total += product.price * qty
    order.total_amount = total
    order.save(update_fields=["total_amount", "updated_at"])
    return order  # nếu có OrderError ở trên, transaction.atomic sẽ rollback toàn bộ


def _restock(order):
    for item in order.items.all():
        Product.objects.filter(pk=item.product_id).update(
            stock=F("stock") + item.quantity, updated_at=timezone.now()
        )


@transaction.atomic
def change_status(order, new_status):
    order = Order.objects.select_for_update().get(pk=order.pk)
    if not order.can_transition_to(new_status):
        labels = dict(Order.Status.choices)
        raise OrderError(
            f"Không thể chuyển đơn từ “{labels.get(order.status)}” sang “{labels.get(new_status, new_status)}”."
        )
    if new_status == Order.Status.CANCELLED:
        _restock(order)
    order.status = new_status
    order.save(update_fields=["status", "updated_at"])
    return order


def cancel_by_customer(order, user):
    if order.user_id != user.id:
        raise OrderError("Bạn không có quyền hủy đơn hàng này.")
    if not order.can_cancel_by_customer:
        raise OrderError("Đơn hàng đã được xử lý, không thể tự hủy. Vui lòng liên hệ cửa hàng.")
    return change_status(order, Order.Status.CANCELLED)
