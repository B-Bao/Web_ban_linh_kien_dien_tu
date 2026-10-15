"""Nghiệp vụ liên quan đến sản phẩm / đánh giá."""


def user_can_review(user, product):
    """Chỉ khách đã mua (có đơn HOÀN THÀNH chứa sản phẩm) mới được đánh giá."""
    if not user.is_authenticated:
        return False
    from orders.models import Order  # import muộn để tránh vòng lặp import

    return Order.objects.filter(
        user=user, status=Order.Status.COMPLETED, items__product=product
    ).exists()
