from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AnalyticsViewSet, EmployeeViewSet, TaskViewSet

router = DefaultRouter()
router.register(r"employees", EmployeeViewSet)
router.register(r"tasks", TaskViewSet)
router.register(r"analytics", AnalyticsViewSet, basename="analytics")

urlpatterns = [
    path("", include(router.urls)),
]
