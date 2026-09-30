from django.urls import path

from apps.users.views import AdminUserDetailView, AdminUserListView, ResetPasswordView, RoleDetailView, RoleListView

urlpatterns = [
    path("users/", AdminUserListView.as_view()),
    path("users/<int:pk>/", AdminUserDetailView.as_view()),
    path("users/<int:pk>/reset-password/", ResetPasswordView.as_view()),
    path("roles/", RoleListView.as_view()),
    path("roles/<str:code>/", RoleDetailView.as_view()),
]
