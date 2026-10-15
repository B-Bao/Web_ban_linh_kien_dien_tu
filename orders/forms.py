from django import forms

from accounts.models import phone_validator
from pcshop.utils import BootstrapFormMixin

from .models import Order


class CheckoutForm(BootstrapFormMixin, forms.Form):
    full_name = forms.CharField(label="Họ tên người nhận", max_length=150)
    phone = forms.CharField(label="Số điện thoại", max_length=20, validators=[phone_validator])
    shipping_address = forms.CharField(label="Địa chỉ giao hàng", max_length=255)
    payment_method = forms.ChoiceField(
        label="Phương thức thanh toán",
        choices=Order.PaymentMethod.choices,
        widget=forms.RadioSelect,
        initial=Order.PaymentMethod.COD,
    )
    note = forms.CharField(label="Ghi chú", required=False, widget=forms.Textarea(attrs={"rows": 2}))
