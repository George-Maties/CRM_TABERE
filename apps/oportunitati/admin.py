from django.contrib import admin

from .models import Note, Opportunity, Task


class NoteInline(admin.TabularInline):
    model = Note
    extra = 0


class TaskInline(admin.TabularInline):
    model = Task
    extra = 0


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ["title", "contact", "status", "owner", "updated_at"]
    list_filter = ["status", "owner"]
    search_fields = ["title", "contact__name"]
    inlines = [NoteInline, TaskInline]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "assigned_to", "due_date", "done", "opportunity"]
    list_filter = ["done", "assigned_to"]
