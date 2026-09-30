from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=20, blank=True, default="")
    department = models.CharField(max_length=64, blank=True, default="")
    must_change_password = models.BooleanField(default=False)

    class Meta:
        default_permissions = ()
        permissions = [
            ("view_user", "查看用户"),
            ("add_user", "新增用户"),
            ("change_user", "修改用户"),
            ("delete_user", "删除用户"),
            ("manage_role", "管理角色"),
        ]


class LoginLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="login_logs"
    )
    username = models.CharField(max_length=150)
    ip = models.CharField(max_length=64, blank=True, default="")
    result = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class LoginLock(models.Model):
    username = models.CharField(max_length=150, unique=True)
    failed_count = models.IntegerField(default=0)
    window_start = models.DateTimeField(null=True, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True)
