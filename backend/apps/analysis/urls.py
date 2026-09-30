from django.urls import path

from apps.analysis.views import DistributionView, OverviewView, ProfileView, SeriesView

urlpatterns = [
    path("<int:pk>/overview/", OverviewView.as_view()),
    path("<int:pk>/series/", SeriesView.as_view()),
    path("<int:pk>/distribution/", DistributionView.as_view()),
    path("<int:pk>/profile/", ProfileView.as_view()),
]
