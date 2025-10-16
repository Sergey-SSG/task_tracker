"""
Модели для трекера задач сотрудников.

Содержит модели Employee (Сотрудник) и Task (Задача)
с необходимыми связями и бизнес-логикой.
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Employee(models.Model):
    """
    Модель сотрудника.

    Attributes:
        full_name (str): ФИО сотрудника
        position (str): Должность сотрудника
        email (str): Электронная почта (опционально)
        hire_date (date): Дата приема на работу
        created_at (datetime): Дата создания записи
        updated_at (datetime): Дата последнего обновления
    """

    class PositionChoices(models.TextChoices):
        """Варианты должностей сотрудников."""

        JUNIOR = "junior", "Младший разработчик"
        MIDDLE = "middle", "Разработчик"
        SENIOR = "senior", "Старший разработчик"
        TEAM_LEAD = "team_lead", "Тимлид"
        MANAGER = "manager", "Менеджер"
        ANALYST = "analyst", "Аналитик"
        TESTER = "tester", "Тестировщик"

    full_name = models.CharField(
        max_length=200,
        verbose_name="ФИО сотрудника",
        help_text="Введите полное имя сотрудника",
    )
    position = models.CharField(
        max_length=50,
        choices=PositionChoices.choices,
        verbose_name="Должность",
        help_text="Выберите должность сотрудника",
    )
    email = models.EmailField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Электронная почта",
        help_text="Введите email сотрудника",
    )
    hire_date = models.DateField(
        default=timezone.now,
        verbose_name="Дата приема на работу",
        help_text="Укажите дату приема на работу",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Мета-класс для модели Employee."""

        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"
        ordering = ["full_name"]
        indexes = [
            models.Index(fields=["full_name"]),
            models.Index(fields=["position"]),
        ]

    def __str__(self):
        """Строковое представление сотрудника."""
        return f"{self.full_name} ({self.get_position_display()})"

    def clean(self):
        """Валидация данных сотрудника."""
        if len(self.full_name.split()) < 2:
            raise ValidationError(
                {"full_name": "ФИО должно содержать как минимум имя и фамилию"}
            )


class Task(models.Model):
    """
    Модель задачи.

    Attributes:
        name (str): Наименование задачи
        parent_task (Task): Родительская задача (опционально)
        assignee (Employee): Исполнитель задачи
        due_date (date): Срок выполнения
        status (str): Статус задачи
        description (str): Описание задачи (опционально)
        priority (str): Приоритет задачи
        created_at (datetime): Дата создания
        updated_at (datetime): Дата последнего обновления
    """

    class Status(models.TextChoices):
        """Статусы задач."""

        TODO = "todo", "К выполнению"
        IN_PROGRESS = "in_progress", "В работе"
        IN_REVIEW = "in_review", "На проверке"
        DONE = "done", "Выполнено"
        CANCELLED = "cancelled", "Отменено"

    class Priority(models.TextChoices):
        """Приоритеты задач."""

        LOW = "low", "Низкий"
        MEDIUM = "medium", "Средний"
        HIGH = "high", "Высокий"
        CRITICAL = "critical", "Критический"

    name = models.CharField(
        max_length=200,
        verbose_name="Наименование задачи",
        help_text="Введите название задачи",
    )
    parent_task = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="subtasks",
        blank=True,
        null=True,
        verbose_name="Родительская задача",
        help_text="Выберите родительскую задачу, если есть зависимость",
    )
    assignee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="Исполнитель",
        help_text="Выберите исполнителя задачи",
    )
    due_date = models.DateField(
        verbose_name="Срок выполнения", help_text="Укажите срок выполнения задачи"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
        verbose_name="Статус",
        help_text="Выберите статус задачи",
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Описание",
        help_text="Дополнительное описание задачи",
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name="Приоритет",
        help_text="Выберите приоритет задачи",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Мета-класс для модели Task."""

        verbose_name = "Задача"
        verbose_name_plural = "Задачи"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["assignee", "status"]),
        ]

    def __str__(self):
        """Строковое представление задачи."""
        return f"{self.name} ({self.get_status_display()})"

    def clean(self):
        """Валидация данных задачи."""
        if self.due_date and self.due_date < timezone.now().date():
            raise ValidationError(
                {"due_date": "Срок выполнения не может быть в прошлом"}
            )

        # Проверка циклических зависимостей
        if self.parent_task and self.parent_task.id == self.id:
            raise ValidationError(
                {"parent_task": "Задача не может быть родительской для самой себя"}
            )

    @property
    def is_overdue(self):
        """Просрочена ли задача."""
        if self.due_date and self.status not in [
            self.Status.DONE,
            self.Status.CANCELLED,
        ]:
            return self.due_date < timezone.now().date()
        return False

    @property
    def has_active_subtasks(self):
        """Есть ли активные подзадачи."""
        return self.subtasks.exclude(
            status__in=[self.Status.DONE, self.Status.CANCELLED]
        ).exists()
