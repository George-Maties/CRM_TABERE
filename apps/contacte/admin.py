from django.contrib import admin

from .models import Contact


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ["name", "kind", "phone", "email", "assigned_to", "created_at"]
    list_filter = ["kind", "assigned_to"]
    search_fields = ["name", "phone", "email"]
