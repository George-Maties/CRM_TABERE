from django.contrib import admin

from .models import Note, Opportunity


class NoteInline(admin.TabularInline):
    model = Note
    extra = 0


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ["title", "contact", "status", "camp", "owner", "updated_at"]
    list_filter = ["status", "owner", "camp"]
    search_fields = ["title", "contact__name"]
    inlines = [NoteInline]
