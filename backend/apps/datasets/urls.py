from django.urls import path

from apps.datasets.views import DatasetDetailView, DatasetListView, DatasetRecordView

urlpatterns = [
    path("", DatasetListView.as_view()),
    path("<int:pk>/", DatasetDetailView.as_view()),
    path("<int:pk>/records/", DatasetRecordView.as_view()),
]
