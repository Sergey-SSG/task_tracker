from django.contrib import admin
from django.db.models import Count, Q
from .models import Employee, Task


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    """Админ-панель для сотрудников."""

    list_display = ["full_name", "position", "email", "hire_date", "active_tasks_count_display"]
    list_filter = ["position", "hire_date"]
    search_fields = ["full_name", "email"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("Основная информация", {"fields": ("full_name", "position", "email")}),
        ("Даты", {"fields": ("hire_date", "created_at", "updated_at")}),
    )

    def get_queryset(self, request):
        """Добавляем аннотацию для подсчёта активных задач."""
        return super().get_queryset(request).annotate(
            active_tasks_count_annotated=Count(
                'tasks',
                filter=Q(tasks__status__in=[Task.Status.IN_PROGRESS, Task.Status.IN_REVIEW])
            )
        )

    def active_tasks_count_display(self, obj):
        """Отображаем количество активных задач."""
        return obj.active_tasks_count_annotated
    active_tasks_count_display.short_description = 'Активные задачи'
    active_tasks_count_display.admin_order_field = 'active_tasks_count_annotated'  # позволяет сортировать по этому полю


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Админ-панель для задач."""

    list_display = [
        "name",
        "assignee",
        "status",
        "priority",
        "due_date",
        "is_overdue",
        "has_active_subtasks",
    ]
    list_filter = ["status", "priority", "due_date", "assignee"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at", "is_overdue", "has_active_subtasks"]
    raw_id_fields = ["parent_task", "assignee"]

    fieldsets = (
        ("Основная информация", {"fields": ("name", "description", "parent_task")}),
        ("Исполнение", {"fields": ("assignee", "due_date", "status", "priority")}),
        (
            "Системная информация",
            {
                "fields": (
                    "is_overdue",
                    "has_active_subtasks",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )