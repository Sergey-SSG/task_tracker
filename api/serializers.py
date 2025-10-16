"""
Сериализаторы для API трекера задач.

Содержит сериализаторы для моделей Employee и Task
с валидацией и преобразованием данных.
"""

from django.utils import timezone
from rest_framework import serializers

from .models import Employee, Task


class EmployeeSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Employee.

    Включает вычисляемое поле количества активных задач.
    """

    active_tasks_count = serializers.ReadOnlyField()

    class Meta:
        model = Employee
        fields = [
            "id",
            "full_name",
            "position",
            "email",
            "hire_date",
            "active_tasks_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_full_name(self, value):
        """Валидация ФИО сотрудника."""
        if len(value.strip()) < 5:
            raise serializers.ValidationError(
                "ФИО должно содержать не менее 5 символов"
            )
        return value

    def validate_hire_date(self, value):
        """Валидация даты приема на работу."""
        if value > timezone.now().date():
            raise serializers.ValidationError(
                "Дата приема на работу не может быть в будущем"
            )
        return value


class TaskSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Task.

    Включает вычисляемые поля и расширенную информацию.
    """

    assignee_name = serializers.CharField(source="assignee.full_name", read_only=True)
    parent_task_name = serializers.CharField(source="parent_task.name", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    has_active_subtasks = serializers.BooleanField(read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "name",
            "parent_task",
            "parent_task_name",
            "assignee",
            "assignee_name",
            "due_date",
            "status",
            "description",
            "priority",
            "is_overdue",
            "has_active_subtasks",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "is_overdue",
            "has_active_subtasks",
        ]

    def validate_due_date(self, value):
        """Валидация срока выполнения задачи."""
        if value < timezone.now().date():
            raise serializers.ValidationError("Срок выполнения не может быть в прошлом")
        return value

    def validate(self, data):
        """Комплексная валидация данных задачи."""
        # Проверка, что родительская задача не является самой задачей
        parent_task = data.get("parent_task")
        if parent_task and self.instance and parent_task.id == self.instance.id:
            raise serializers.ValidationError(
                {"parent_task": "Задача не может быть родительской для самой себя"}
            )

        return data


class EmployeeTasksSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отображения сотрудника с его задачами.

    Используется в специальных эндпоинтах.
    """

    tasks = TaskSerializer(many=True, read_only=True)
    active_tasks_count = serializers.ReadOnlyField()

    class Meta:
        model = Employee
        fields = ["id", "full_name", "position", "active_tasks_count", "tasks"]


class ImportantTaskSerializer(serializers.Serializer):
    """
    Сериализатор для важных задач с рекомендациями по исполнителям.

    Используется в специальном эндпоинте важных задач.
    """

    task = serializers.DictField()
    due_date = serializers.DateField()
    potential_assignees = serializers.ListField(child=serializers.DictField())

    def to_representation(self, instance):
        """Преобразование данных для ответа API."""
        return {
            "Важная задача": instance["task"]["name"],
            "Срок": instance["due_date"],
            "ФИО сотрудника": [
                emp["full_name"] for emp in instance["potential_assignees"]
            ],
        }
