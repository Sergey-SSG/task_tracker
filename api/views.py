"""
Представления для API трекера задач.

Содержит CRUD операции для сотрудников и задач,
а также специальные эндпоинты для бизнес-логики.
"""

from django.db.models import Count, OuterRef, Q, Subquery
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Employee, Task
from .serializers import (EmployeeSerializer, EmployeeTasksSerializer,
                          ImportantTaskSerializer, TaskSerializer)


class EmployeeViewSet(viewsets.ModelViewSet):
    """
    ViewSet для CRUD операций с сотрудниками.

    Предоставляет стандартные операции:
    - list: список всех сотрудников
    - retrieve: детальная информация о сотруднике
    - create: создание нового сотрудника
    - update: полное обновление сотрудника
    - partial_update: частичное обновление сотрудника
    - destroy: удаление сотрудника
    """

    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer

    def get_queryset(self):
        """
        Оптимизация запроса с аннотацией количества активных задач.

        Returns:
            QuerySet: Оптимизированный queryset сотрудников
        """
        return Employee.objects.annotate(
            active_tasks_count=Count(
                "tasks",
                filter=Q(
                    tasks__status__in=[Task.Status.IN_PROGRESS, Task.Status.IN_REVIEW]
                ),
            )
        ).order_by("full_name")

    def destroy(self, request, *args, **kwargs):
        """
        Удаление сотрудника с проверкой наличия активных задач.

        Args:
            request: HTTP запрос
            *args: Аргументы
            **kwargs: Ключевые аргументы

        Returns:
            Response: Ответ с результатом операции
        """
        employee = self.get_object()

        # Проверка наличия активных задач
        active_tasks = employee.tasks.exclude(
            status__in=[Task.Status.DONE, Task.Status.CANCELLED]
        ).exists()

        if active_tasks:
            return Response(
                {
                    "error": "Нельзя удалить сотрудника с активными задачами. "
                    "Переназначьте или завершите задачи сначала."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().destroy(request, *args, **kwargs)


class TaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet для CRUD операций с задачами.

    Предоставляет стандартные операции и дополнительную фильтрацию.
    """

    queryset = Task.objects.all()
    serializer_class = TaskSerializer

    def get_queryset(self):
        """
        Оптимизация запроса с выборкой связанных данных.

        Returns:
            QuerySet: Оптимизированный queryset задач
        """
        return Task.objects.select_related("assignee", "parent_task").prefetch_related(
            "subtasks"
        )

    def perform_create(self, serializer):
        """
        Создание задачи с дополнительной логикой.

        Args:
            serializer: Сериализатор задачи
        """
        serializer.save()

    def perform_update(self, serializer):
        """
        Обновление задачи с дополнительной логикой.

        Args:
            serializer: Сериализатор задачи
        """
        serializer.save()


class AnalyticsViewSet(viewsets.ViewSet):
    """
    ViewSet для аналитических эндпоинтов.

    Содержит специальные эндпоинты для бизнес-аналитики:
    - busy_employees: список занятых сотрудников
    - important_tasks: важные задачи с рекомендациями
    """

    @action(detail=False, methods=["get"])
    def busy_employees(self, request):
        """
        Эндпоинт для получения списка занятых сотрудников.

        Возвращает сотрудников, отсортированных по количеству активных задач.

        Args:
            request: HTTP запрос

        Returns:
            Response: Список сотрудников с их задачами
        """
        employees = (
            Employee.objects.annotate(
                active_tasks_count=Count(
                    "tasks",
                    filter=Q(
                        tasks__status__in=[
                            Task.Status.IN_PROGRESS,
                            Task.Status.IN_REVIEW,
                        ]
                    ),
                )
            )
            .filter(active_tasks_count__gt=0)
            .order_by("-active_tasks_count")
        )

        serializer = EmployeeTasksSerializer(employees, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def important_tasks(self, request):
        """
        Эндпоинт для получения важных задач.

        Находит задачи, которые:
        1. Не взяты в работу (status = 'todo')
        2. Имеют подзадачи, которые взяты в работу

        Также находит потенциальных исполнителей по критериям:
        - Наименее загруженный сотрудник
        - Сотрудник, выполняющий родительскую задачу (если у него не больше +2 задач)

        Args:
            request: HTTP запрос

        Returns:
            Response: Список важных задач с рекомендациями
        """
        # Подзапрос для подсчета активных задач у сотрудников
        active_tasks_count_subquery = (
            Task.objects.filter(
                assignee=OuterRef("pk"),
                status__in=[Task.Status.IN_PROGRESS, Task.Status.IN_REVIEW],
            )
            .values("assignee")
            .annotate(count=Count("id"))
            .values("count")[:1]
        )

        # Наименее загруженный сотрудник
        min_busy_employee = (
            Employee.objects.annotate(
                active_tasks_count=Subquery(active_tasks_count_subquery)
            )
            .exclude(active_tasks_count__isnull=True)
            .order_by("active_tasks_count")
            .first()
        )

        min_task_count = (
            min_busy_employee.active_tasks_count if min_busy_employee else 0
        )

        # Поиск важных задач
        important_tasks = Task.objects.filter(
            status=Task.Status.TODO,  # Не взяты в работу
            subtasks__status__in=[
                Task.Status.IN_PROGRESS,
                Task.Status.IN_REVIEW,
            ],  # Есть активные подзадачи
        ).distinct()

        result = []

        for task in important_tasks:
            potential_assignees = []

            # Критерий 1: Наименее загруженные сотрудники
            least_busy_employees = (
                Employee.objects.annotate(
                    active_tasks_count=Subquery(active_tasks_count_subquery)
                )
                .filter(
                    Q(active_tasks_count__isnull=True)
                    | Q(active_tasks_count__lte=min_task_count + 2)
                )
                .order_by("active_tasks_count")[:5]
            )

            # Критерий 2: Сотрудник, выполняющий родительскую задачу
            if task.parent_task and task.parent_task.assignee:
                parent_assignee = task.parent_task.assignee
                parent_assignee_tasks_count = Task.objects.filter(
                    assignee=parent_assignee,
                    status__in=[Task.Status.IN_PROGRESS, Task.Status.IN_REVIEW],
                ).count()

                if parent_assignee_tasks_count <= min_task_count + 2:
                    # Добавляем исполнителя родительской задачи в начало списка
                    potential_assignees.insert(
                        0,
                        {
                            "id": parent_assignee.id,
                            "full_name": parent_assignee.full_name,
                            "position": parent_assignee.position,
                            "active_tasks_count": parent_assignee_tasks_count,
                            "reason": "Исполнитель родительской задачи",
                        },
                    )

            # Добавляем наименее загруженных сотрудников
            for employee in least_busy_employees:
                if employee.id not in [emp["id"] for emp in potential_assignees]:
                    potential_assignees.append(
                        {
                            "id": employee.id,
                            "full_name": employee.full_name,
                            "position": employee.position,
                            "active_tasks_count": employee.active_tasks_count or 0,
                            "reason": "Наименее загруженный сотрудник",
                        }
                    )

            result.append(
                {
                    "task": {
                        "id": task.id,
                        "name": task.name,
                        "description": task.description,
                        "priority": task.get_priority_display(),
                    },
                    "due_date": task.due_date,
                    "potential_assignees": potential_assignees[
                        :3
                    ],  # Ограничиваем до 3 рекомендаций
                }
            )

        serializer = ImportantTaskSerializer(result, many=True)
        return Response(serializer.data)
