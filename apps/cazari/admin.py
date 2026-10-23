from django.contrib import admin

from .models import Accommodation


@admin.register(Accommodation)
class AccommodationAdmin(admin.ModelAdmin):
    list_display = ["name", "city", "capacity", "contact_name", "phone"]
    search_fields = ["name", "city", "contact_name"]
