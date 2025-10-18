"""
Celery задачи для приложения API.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import Task

logger = logging.getLogger(__name__)


@shared_task
def check_overdue_tasks():
    """
    Проверяет задачи, срок выполнения которых уже прошёл,
    и отправляет уведомления ответственным лицам.

    Запускается ежедневно через Celery Beat.
    """
    today = timezone.now().date()
    overdue_tasks = Task.objects.filter(
        due_date__lt=today,
        status__in=[
            Task.Status.TODO,
            Task.Status.IN_PROGRESS,
            Task.Status.IN_REVIEW,
        ],
    )

    notification_count = 0
    for task in overdue_tasks:
        send_task_overdue_notification.delay(task.id)
        notification_count += 1

    logger.info(
        f"Проверено {overdue_tasks.count()} просроченных задач. "
        f"Отправлено {notification_count} уведомлений."
    )
    return f"Проверено {overdue_tasks.count()} просроченных задач"


@shared_task
def send_task_overdue_notification(task_id):
    """
    Отправляет email-уведомление о просроченной задаче её исполнителю.

    Args:
        task_id (int): ID задачи.
    """
    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        logger.warning(
            f"Попытка отправить уведомление для несуществующей задачи ID={task_id}"
        )
        return

    # Проверяем, назначен ли исполнитель и есть ли у него email
    assignee = task.assignee
    if not assignee or not hasattr(assignee, "email") or not assignee.email:
        logger.warning(
            f"У задачи ID={task_id} нет исполнителя с email. Уведомление не отправлено."
        )
        return

    subject = f"Задача просрочена: {task.name}"
    message = (
        f'Задача "{task.name}" просрочена.\n\n'
        f'Исполнитель: {getattr(assignee, "full_name", assignee.email)}\n'
        f"Срок выполнения: {task.due_date}\n"
        f"Текущий статус: {task.get_status_display()}\n\n"
        f"Пожалуйста, примите меры."
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[assignee.email],
            fail_silently=False,
        )
        logger.info(
            f"Уведомление о просроченной задаче ID={task_id} отправлено на {assignee.email}"
        )
    except Exception as e:
        logger.error(f"Не удалось отправить email для задачи ID={task_id}: {e}")


@shared_task
def cleanup_old_tasks():
    """
    Удаляет старые завершённые задачи (старше 1 года).
    """
    cutoff_date = timezone.now() - timedelta(days=365)
    old_tasks = Task.objects.filter(
        status=Task.Status.DONE,
        updated_at__lt=cutoff_date,
    )

    count = old_tasks.count()
    if count > 0:
        old_tasks.delete()
        logger.info(f"Удалено {count} старых завершённых задач")
    else:
        logger.debug("Нет старых задач для удаления")

    return f"Удалено {count} старых задач"
