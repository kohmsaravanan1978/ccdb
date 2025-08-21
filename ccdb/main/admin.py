from django.contrib import admin

from main.models import LogEntry


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    model = LogEntry
    list_display = ["created", "log_level", "origin", "text"]
    search_fields = ["origin", "text"]
    list_editable = []
    list_filter = ["created", "log_level"]
    readonly_fields = [f.name for f in LogEntry._meta.fields]

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
