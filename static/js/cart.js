/* Xử lý bất đồng bộ với Fetch API: /api/check-stock/, /api/cart/update/ */
(function () {
  const meta = document.querySelector('meta[name="csrf-token"]');
  const csrf = meta ? meta.content : "";
  const fmt = (v) => new Intl.NumberFormat("vi-VN").format(v) + " ₫";

  async function postJSON(url, data) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
      body: JSON.stringify(data),
    });
    return { ok: res.ok, data: await res.json() };
  }

  function updateBadge(count) {
    const badge = document.getElementById("cart-badge");
    if (badge) badge.textContent = count;
  }

  function showAlert(msg) {
    const box = document.getElementById("cart-alert");
    if (!box) return;
    box.textContent = msg;
    box.classList.remove("d-none");
    setTimeout(() => box.classList.add("d-none"), 4000);
  }

  // ---- Trang giỏ hàng ----
  function applyCart(cart) {
    updateBadge(cart.count);
    const totalEl = document.getElementById("cart-total");
    if (totalEl) totalEl.textContent = fmt(cart.total);
    const present = new Set(cart.lines.map((l) => String(l.product_id)));
    document.querySelectorAll("tr[data-product-id]").forEach((row) => {
      const id = row.dataset.productId;
      if (!present.has(id)) { row.remove(); return; }
      const line = cart.lines.find((l) => String(l.product_id) === id);
      row.querySelector(".line-subtotal").textContent = fmt(line.subtotal);
      const input = row.querySelector(".cart-qty");
      input.value = line.quantity;
      input.dataset.prev = line.quantity;
      input.max = line.stock;
      row.classList.remove("table-warning");
    });
    if (cart.lines.length === 0) window.location.reload();
  }

  async function updateQty(productId, quantity, input) {
    const { ok, data } = await postJSON("/api/cart/update/", { product_id: Number(productId), quantity: Number(quantity) });
    if (!ok) {
      showAlert(data.message || "Không cập nhật được giỏ hàng.");
      if (input) input.value = input.dataset.prev;
      if (data.cart) updateBadge(data.cart.count);
      return;
    }
    applyCart(data.cart);
  }

  document.querySelectorAll(".cart-qty").forEach((input) => {
    input.dataset.prev = input.value;
    input.addEventListener("change", () => updateQty(input.dataset.productId, input.value, input));
  });
  document.querySelectorAll(".cart-remove-btn").forEach((btn) => {
    btn.addEventListener("click", () => updateQty(btn.dataset.productId, 0, null));
  });

  // ---- Trang chi tiết sản phẩm: kiểm tra tồn kho theo thời gian thực ----
  const stockInput = document.getElementById("detail-qty");
  if (stockInput) {
    const msg = document.getElementById("stock-msg");
    const btn = document.getElementById("add-btn");
    const check = async () => {
      const q = Math.max(1, parseInt(stockInput.value || "1", 10));
      const res = await fetch(`/api/check-stock/?product_id=${stockInput.dataset.productId}&quantity=${q}`);
      const data = await res.json();
      msg.textContent = data.message;
      msg.className = "small " + (data.available ? "text-success" : "text-danger");
      btn.disabled = !data.available;
    };
    stockInput.addEventListener("input", check);
  }
})();
