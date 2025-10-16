"""
Тесты для представлений API.
"""

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import Employee, Task


class EmployeeAPITest(APITestCase):
    """Тесты для API сотрудников."""

    def setUp(self):
        """Настройка тестовых данных."""
        self.employee = Employee.objects.create(
            full_name="Сидоров Алексей Владимирович",
            position=Employee.PositionChoices.TEAM_LEAD,
            email="sidorov@example.com",
        )

        self.employee_data = {
            "full_name": "Козлова Мария Сергеевна",
            "position": Employee.PositionChoices.ANALYST,
            "email": "kozlova@example.com",
            "hire_date": "2023-01-15",
        }

    def test_create_employee(self):
        """Тест создания сотрудника через API."""
        url = reverse("employee-list")
        response = self.client.post(url, self.employee_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Employee.objects.count(), 2)
        self.assertEqual(response.data["full_name"], self.employee_data["full_name"])

    def test_get_employees_list(self):
        """Тест получения списка сотрудников."""
        url = reverse("employee-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_get_employee_detail(self):
        """Тест получения детальной информации о сотруднике."""
        url = reverse("employee-detail", args=[self.employee.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], self.employee.full_name)


class TaskAPITest(APITestCase):
    """Тесты для API задач."""

    def setUp(self):
        """Настройка тестовых данных."""
        self.employee = Employee.objects.create(
            full_name="Федоров Дмитрий Игоревич",
            position=Employee.PositionChoices.MIDDLE,
        )

        self.task = Task.objects.create(
            name="Тестовая задача",
            assignee=self.employee,
            due_date=timezone.now().date() + timedelta(days=14),
            status=Task.Status.IN_PROGRESS,
            priority=Task.Priority.MEDIUM,
        )

        self.task_data = {
            "name": "Новая задача",
            "assignee": self.employee.id,
            "due_date": (timezone.now().date() + timedelta(days=10)).isoformat(),
            "status": Task.Status.TODO,
            "priority": Task.Priority.HIGH,
        }

    def test_create_task(self):
        """Тест создания задачи через API."""
        url = reverse("task-list")
        response = self.client.post(url, self.task_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.count(), 2)
        self.assertEqual(response.data["name"], self.task_data["name"])

    def test_get_tasks_list(self):
        """Тест получения списка задач."""
        url = reverse("task-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)


class AnalyticsAPITest(APITestCase):
    """Тесты для аналитических эндпоинтов."""

    def setUp(self):
        """Настройка тестовых данных для аналитики."""
        self.employee1 = Employee.objects.create(
            full_name="Сотрудник 1", position=Employee.PositionChoices.MIDDLE
        )

        self.employee2 = Employee.objects.create(
            full_name="Сотрудник 2", position=Employee.PositionChoices.SENIOR
        )

        # Создаем задачи для тестирования аналитики
        self.parent_task = Task.objects.create(
            name="Родительская задача",
            assignee=self.employee1,
            due_date=timezone.now().date() + timedelta(days=30),
            status=Task.Status.TODO,
        )

        self.subtask = Task.objects.create(
            name="Подзадача в работе",
            parent_task=self.parent_task,
            assignee=self.employee2,
            due_date=timezone.now().date() + timedelta(days=15),
            status=Task.Status.IN_PROGRESS,
        )

    def test_busy_employees_endpoint(self):
        """Тест эндпоинта занятых сотрудников."""
        url = reverse("analytics-busy-employees")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # employee2 должен быть в списке, т.к. у него есть активная задача
        self.assertTrue(any(emp["full_name"] == "Сотрудник 2" for emp in response.data))

    def test_important_tasks_endpoint(self):
        """Тест эндпоинта важных задач."""
        url = reverse("analytics-important-tasks")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Родительская задача должна быть в списке важных
        self.assertTrue(
            any(
                task["Важная задача"] == "Родительская задача" for task in response.data
            )
        )
