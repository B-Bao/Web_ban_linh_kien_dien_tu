from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .filters import filter_products
from .forms import ReviewForm
from .models import Category, Product, Review
from .services import user_can_review


def home(request):
    products = Product.objects.filter(is_active=True).select_related("category")
    context = {
        "categories": Category.objects.all(),
        "latest": products[:8],
        "bestsellers": products.filter(stock__gt=0).order_by("-stock")[:4],
    }
    return render(request, "catalog/home.html", context)


def product_list(request, slug=None):
    category = get_object_or_404(Category, slug=slug) if slug else None
    base = Product.objects.filter(is_active=True).select_related("category")
    if category:
        base = base.filter(category=category)

    brands = base.order_by("brand").values_list("brand", flat=True).distinct()

    params = request.GET.copy()
    products = filter_products(base, params)

    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    params.pop("page", None)
    context = {
        "category": category,
        "page_obj": page_obj,
        "brands": brands,
        "querystring": params.urlencode(),
        "sort_options": [
            ("newest", "Mới nhất"),
            ("price_asc", "Giá tăng dần"),
            ("price_desc", "Giá giảm dần"),
            ("name", "Tên A-Z"),
        ],
        "filters": request.GET,
    }
    return render(request, "catalog/product_list.html", context)


def product_detail(request, slug):
    product = get_object_or_404(Product.objects.select_related("category"), slug=slug, is_active=True)
    can_review = user_can_review(request.user, product)
    review_form = None
    if can_review:
        existing = Review.objects.filter(product=product, user=request.user).first()
        review_form = ReviewForm(instance=existing)
    context = {
        "product": product,
        "reviews": product.reviews.select_related("user"),
        "can_review": can_review,
        "review_form": review_form,
        "related": Product.objects.filter(category=product.category, is_active=True)
        .exclude(pk=product.pk)[:4],
    }
    return render(request, "catalog/product_detail.html", context)


@login_required
@require_POST
def review_submit(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    if not user_can_review(request.user, product):
        messages.error(request, "Bạn chỉ có thể đánh giá sản phẩm sau khi đơn hàng đã hoàn thành.")
        return redirect(product)
    existing = Review.objects.filter(product=product, user=request.user).first()
    form = ReviewForm(request.POST, instance=existing)
    if form.is_valid():
        review = form.save(commit=False)
        review.product = product
        review.user = request.user
        review.save()
        messages.success(request, "Cảm ơn bạn đã đánh giá sản phẩm!")
    else:
        messages.error(request, "Đánh giá không hợp lệ, vui lòng kiểm tra lại.")
    return redirect(product)
