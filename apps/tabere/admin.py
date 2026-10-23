from django.contrib import admin

from .models import Camp, Child, Room, Task


class TaskInline(admin.TabularInline):
    model = Task
    extra = 0


@admin.register(Camp)
class CampAdmin(admin.ModelAdmin):
    list_display = ["name", "start_date", "end_date", "accommodation"]
    search_fields = ["name", "accommodation__name", "accommodation__city"]
    inlines = [TaskInline]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "assigned_to", "due_date", "done", "camp"]
    list_filter = ["done", "assigned_to"]


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ["name", "age", "city", "opportunity"]
    autocomplete_fields = ["opportunity"]
    search_fields = ["name", "opportunity__contact__name"]


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ["name", "capacity", "camp"]
    list_filter = ["camp"]
