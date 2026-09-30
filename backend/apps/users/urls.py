from django.urls import path

from apps.users.views import LoginLogView, MeView, PasswordView

urlpatterns = [
    path("me/", MeView.as_view()),
    path("me/password/", PasswordView.as_view()),
    path("me/login-logs/", LoginLogView.as_view()),
]
