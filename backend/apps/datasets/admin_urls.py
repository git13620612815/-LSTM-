from django.urls import path

from apps.datasets.views import DatasetAdminDetailView, DatasetReimportView, DatasetTrainView, DatasetUploadView

urlpatterns = [
    path("datasets/upload/", DatasetUploadView.as_view()),
    path("datasets/<int:pk>/train/", DatasetTrainView.as_view()),
    path("datasets/<int:pk>/", DatasetAdminDetailView.as_view()),
    path("datasets/<int:pk>/reimport/", DatasetReimportView.as_view()),
]
