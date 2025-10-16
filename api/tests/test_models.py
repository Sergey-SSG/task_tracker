"""
Тесты для моделей приложения.
"""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from api.models import Employee, Task


class EmployeeModelTest(TestCase):
    """Тесты для модели Employee."""

    def setUp(self):
        """Настройка тестовых данных."""
        self.employee = Employee.objects.create(
            full_name="Иванов Иван Иванович",
            position=Employee.PositionChoices.MIDDLE,
            email="ivanov@example.com",
        )

    def test_employee_creation(self):
        """Тест создания сотрудника."""
        self.assertEqual(self.employee.full_name, "Иванов Иван Иванович")
        self.assertEqual(self.employee.position, Employee.PositionChoices.MIDDLE)
        self.assertTrue(self.employee.created_at)

    def test_employee_str_representation(self):
        """Тест строкового представления сотрудника."""
        expected_str = "Иванов Иван Иванович (Разработчик)"
        self.assertEqual(str(self.employee), expected_str)

    def test_employee_validation(self):
        """Тест валидации данных сотрудника."""
        # Тест неверного ФИО
        employee = Employee(full_name="Иван", position=Employee.PositionChoices.JUNIOR)

        with self.assertRaises(ValidationError):
            employee.full_clean()


class TaskModelTest(TestCase):
    """Тесты для модели Task."""

    def setUp(self):
        """Настройка тестовых данных."""
        self.employee = Employee.objects.create(
            full_name="Петров Петр Петрович", position=Employee.PositionChoices.SENIOR
        )

        self.task = Task.objects.create(
            name="Разработать новый функционал",
            assignee=self.employee,
            due_date=timezone.now().date() + timedelta(days=7),
            status=Task.Status.TODO,
            priority=Task.Priority.HIGH,
        )

    def test_task_creation(self):
        """Тест создания задачи."""
        self.assertEqual(self.task.name, "Разработать новый функционал")
        self.assertEqual(self.task.assignee, self.employee)
        self.assertEqual(self.task.status, Task.Status.TODO)

    def test_task_str_representation(self):
        """Тест строкового представления задачи."""
        expected_str = "Разработать новый функционал (К выполнению)"
        self.assertEqual(str(self.task), expected_str)

    def test_task_overdue_property(self):
        """Тест свойства просроченности задачи."""
        # Создаем просроченную задачу
        overdue_task = Task.objects.create(
            name="Просроченная задача",
            assignee=self.employee,
            due_date=timezone.now().date() - timedelta(days=1),
            status=Task.Status.IN_PROGRESS,
        )

        self.assertTrue(overdue_task.is_overdue)
        self.assertFalse(self.task.is_overdue)

    def test_task_validation(self):
        """Тест валидации данных задачи."""
        # Тест просроченной даты
        task = Task(
            name="Некорректная задача",
            assignee=self.employee,
            due_date=timezone.now().date() - timedelta(days=1),
            status=Task.Status.TODO,
        )

        with self.assertRaises(ValidationError):
            task.full_clean()
