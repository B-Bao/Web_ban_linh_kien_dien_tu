from django import forms

from catalog.models import Category, Product
from pcshop.utils import BootstrapFormMixin


class ProductForm(BootstrapFormMixin, forms.ModelForm):
    specs_text = forms.CharField(
        label="Thông số kỹ thuật",
        required=False,
        widget=forms.Textarea(attrs={"rows": 8, "placeholder": "Socket: AM5\nSố nhân / luồng: 8 / 16\nTDP: 105W"}),
        help_text="Mỗi dòng một thông số theo dạng <code>Tên: Giá trị</code>.",
    )

    class Meta:
        model = Product
        fields = ["category", "name", "brand", "price", "stock", "description", "image", "image_url", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    field_order = ["category", "name", "brand", "price", "stock", "specs_text", "description", "image", "image_url", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.specifications:
            self.initial["specs_text"] = "\n".join(f"{k}: {v}" for k, v in self.instance.specifications.items())

    def clean_specs_text(self):
        specs = {}
        for n, line in enumerate(self.cleaned_data.get("specs_text", "").splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            if ":" not in line:
                raise forms.ValidationError(f"Dòng {n} thiếu dấu “:” (định dạng đúng: Tên: Giá trị).")
            key, value = line.split(":", 1)
            if not key.strip() or not value.strip():
                raise forms.ValidationError(f"Dòng {n} thiếu tên hoặc giá trị.")
            specs[key.strip()] = value.strip()
        return specs

    def save(self, commit=True):
        self.instance.specifications = self.cleaned_data["specs_text"]
        return super().save(commit=commit)


class CategoryForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}
