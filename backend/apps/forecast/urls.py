from django.urls import path

from apps.forecast.views import (
    BatchForecastView,
    ModelStatusView,
    SingleForecastView,
    TaskDetailView,
    TaskExportView,
    TaskListView,
)

urlpatterns = [
    path("model/", ModelStatusView.as_view()),
    path("single/", SingleForecastView.as_view()),
    path("batch/", BatchForecastView.as_view()),
    path("tasks/export/", TaskExportView.as_view()),
    path("tasks/", TaskListView.as_view()),
    path("tasks/<int:pk>/", TaskDetailView.as_view()),
]
