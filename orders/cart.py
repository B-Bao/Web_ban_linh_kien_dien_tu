"""Giỏ hàng lưu trong session: {"<product_id>": quantity}."""
from catalog.models import Product

CART_SESSION_KEY = "cart"


class StockError(Exception):
    """Số lượng yêu cầu vượt quá tồn kho / sản phẩm không khả dụng."""

    def __init__(self, message, stock=None):
        super().__init__(message)
        self.message = message
        self.stock = stock


class Cart:
    def __init__(self, request):
        self.session = request.session
        self._data = dict(self.session.get(CART_SESSION_KEY, {}))

    def _save(self):
        self.session[CART_SESSION_KEY] = self._data
        self.session.modified = True

    # --- thao tác ---------------------------------------------------------
    def add(self, product_id, quantity=1):
        current = self._data.get(str(product_id), 0)
        self.set(product_id, current + int(quantity))

    def set(self, product_id, quantity):
        quantity = int(quantity)
        if quantity <= 0:
            self.remove(product_id)
            return
        product = Product.objects.filter(pk=product_id, is_active=True).first()
        if product is None:
            raise StockError("Sản phẩm không tồn tại hoặc đã ngừng bán.", stock=0)
        if product.stock <= 0:
            raise StockError(f"“{product.name}” đã hết hàng.", stock=0)
        if quantity > product.stock:
            raise StockError(
                f"“{product.name}” chỉ còn {product.stock} sản phẩm trong kho.", stock=product.stock
            )
        self._data[str(product_id)] = quantity
        self._save()

    def remove(self, product_id):
        if self._data.pop(str(product_id), None) is not None:
            self._save()

    def clear(self):
        self._data = {}
        self._save()

    # --- đọc dữ liệu ------------------------------------------------------
    def raw(self):
        """{product_id(int): quantity(int)} - dùng khi tạo đơn."""
        return {int(k): int(v) for k, v in self._data.items()}

    def lines(self):
        ids = list(self.raw())
        products = Product.objects.in_bulk(ids)
        lines, dirty = [], False
        for pid, qty in self.raw().items():
            product = products.get(pid)
            if product is None or not product.is_active:
                self._data.pop(str(pid), None)  # sản phẩm đã bị xóa/ngừng bán
                dirty = True
                continue
            lines.append(
                {
                    "product": product,
                    "quantity": qty,
                    "subtotal": product.price * qty,
                    "available": product.stock >= qty,
                }
            )
        if dirty:
            self._save()
        return lines

    @property
    def count(self):
        return sum(self.raw().values())

    def total(self):
        return sum(line["subtotal"] for line in self.lines())

    def summary(self):
        lines = self.lines()
        return {
            "count": sum(l["quantity"] for l in lines),
            "total": int(sum(l["subtotal"] for l in lines)),
            "lines": [
                {
                    "product_id": l["product"].pk,
                    "quantity": l["quantity"],
                    "subtotal": int(l["subtotal"]),
                    "stock": l["product"].stock,
                }
                for l in lines
            ],
        }
