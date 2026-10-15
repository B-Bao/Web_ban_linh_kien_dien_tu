from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User

EXTRA = ("Thông tin thêm", {"fields": ("full_name", "phone", "address", "role")})


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (EXTRA,)
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (EXTRA,)
    list_display = ("username", "email", "full_name", "role", "is_staff", "date_joined")
    list_filter = DjangoUserAdmin.list_filter + ("role",)
    search_fields = ("username", "email", "full_name", "phone")
