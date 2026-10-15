from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalog.models import Category, Product
from orders.models import Order
from orders.services import OrderError, change_status

from . import stats
from .decorators import staff_required
from .forms import CategoryForm, ProductForm


@staff_required
def index(request):
    return render(request, "dashboard/index.html", stats.overview())


# ---------------- Sản phẩm (CRUD) ----------------
@staff_required
def product_list(request):
    qs = Product.objects.select_related("category")
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(brand__icontains=q))
    if category:
        qs = qs.filter(category__slug=category)
    page_obj = Paginator(qs, 20).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(
        request,
        "dashboard/product_list.html",
        {"page_obj": page_obj, "categories": Category.objects.all(), "q": q, "category": category, "querystring": params.urlencode()},
    )


@staff_required
def product_create(request):
    form = ProductForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        product = form.save()
        messages.success(request, f"Đã thêm “{product.name}”.")
        return redirect("dashboard:product_list")
    return render(request, "dashboard/product_form.html", {"form": form, "title": "Thêm linh kiện mới"})


@staff_required
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Đã cập nhật “{product.name}”.")
        return redirect("dashboard:product_list")
    return render(request, "dashboard/product_form.html", {"form": form, "title": f"Sửa: {product.name}", "product": product})


@staff_required
@require_POST
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    try:
        product.delete()
        messages.success(request, f"Đã xóa “{product.name}”.")
    except ProtectedError:
        # Sản phẩm đã có trong đơn hàng → không xóa cứng, chỉ ngừng bán để giữ lịch sử đơn
        product.is_active = False
        product.save(update_fields=["is_active", "updated_at"])
        messages.warning(request, f"“{product.name}” đã nằm trong đơn hàng nên chỉ được chuyển sang trạng thái ngừng bán.")
    return redirect("dashboard:product_list")


# ---------------- Đơn hàng ----------------
@staff_required
def order_list(request):
    qs = Order.objects.select_related("user")
    status = request.GET.get("status", "")
    q = request.GET.get("q", "").strip()
    if status in dict(Order.Status.choices):
        qs = qs.filter(status=status)
    if q:
        cond = Q(full_name__icontains=q) | Q(phone__icontains=q) | Q(user__username__icontains=q)
        if q.lstrip("#").isdigit():
            cond |= Q(pk=int(q.lstrip("#")))
        qs = qs.filter(cond)
    page_obj = Paginator(qs, 20).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(
        request,
        "dashboard/order_list.html",
        {"page_obj": page_obj, "statuses": Order.Status.choices, "status": status, "q": q, "querystring": params.urlencode()},
    )


@staff_required
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.select_related("user").prefetch_related("items__product"), pk=pk)
    if request.method == "POST":
        try:
            change_status(order, request.POST.get("status", ""))
            messages.success(request, f"Đã cập nhật trạng thái đơn #{order.pk}.")
        except OrderError as e:
            messages.error(request, str(e))
        return redirect("dashboard:order_detail", pk=pk)
    return render(request, "dashboard/order_detail.html", {"order": order})


# ---------------- Danh mục (CRUD) ----------------
@staff_required
def category_list(request):
    categories = Category.objects.annotate(product_count=Count("products"))
    return render(request, "dashboard/category_list.html", {"categories": categories})


@staff_required
def category_create(request):
    form = CategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        category = form.save()
        messages.success(request, f"Đã thêm danh mục “{category.name}”.")
        return redirect("dashboard:category_list")
    return render(request, "dashboard/category_form.html", {"form": form, "title": "Thêm danh mục"})


@staff_required
def category_update(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST or None, instance=category)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Đã cập nhật danh mục “{category.name}”.")
        return redirect("dashboard:category_list")
    return render(request, "dashboard/category_form.html", {"form": form, "title": f"Sửa danh mục: {category.name}"})


@staff_required
@require_POST
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    try:
        category.delete()
        messages.success(request, f"Đã xóa danh mục “{category.name}”.")
    except ProtectedError:
        messages.error(request, f"Không thể xóa “{category.name}” vì vẫn còn sản phẩm thuộc danh mục này.")
    return redirect("dashboard:category_list")
