from django import forms

from pcshop.utils import BootstrapFormMixin

from .models import Review


class ReviewForm(BootstrapFormMixin, forms.ModelForm):
    rating = forms.TypedChoiceField(
        label="Chấm điểm",
        coerce=int,
        choices=[(i, f"{i} sao") for i in range(5, 0, -1)],
    )

    class Meta:
        model = Review
        fields = ("rating", "comment")
        widgets = {"comment": forms.Textarea(attrs={"rows": 3})}
