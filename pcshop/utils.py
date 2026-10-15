"""Tiện ích dùng chung."""
from django import forms
from django.utils.http import url_has_allowed_host_and_scheme


class BootstrapFormMixin:
    """Tự động gắn class Bootstrap 5 cho các widget của form."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(widget, forms.RadioSelect):
                continue
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                css = "form-select"
            else:
                css = "form-control"
            widget.attrs["class"] = (widget.attrs.get("class", "") + " " + css).strip()


def safe_redirect_target(request, default):
    """Trả về URL 'next' hợp lệ (cùng host) hoặc default."""
    target = request.POST.get("next") or request.META.get("HTTP_REFERER")
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return target
    return default
