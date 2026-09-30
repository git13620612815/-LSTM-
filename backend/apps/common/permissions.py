from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

ROLE_NAMES = {"admin": "管理员", "user": "普通用户"}

PERMISSION_CATALOG = [
    ("users.view_user", "查看用户"),
    ("users.add_user", "新增用户"),
    ("users.change_user", "修改用户"),
    ("users.delete_user", "删除用户"),
    ("users.manage_role", "管理角色"),
    ("datasets.manage_dataset", "管理数据集"),
    ("datasets.view_dataset", "预览数据集"),
    ("forecast.view_all_record", "查看全部预测记录"),
    ("forecast.add_prediction", "发起预测"),
]
PERMISSION_CODES = [code for code, _ in PERMISSION_CATALOG]


class IsAdminRole(BasePermission):
    message = "需要管理员角色"

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.groups.filter(name="admin").exists())


class MustChangePassword(BasePermission):
    message = "请先修改密码"

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return True
        path = request.path
        if path.startswith("/api/auth/"):
            return True
        profile = getattr(user, "profile", None)
        if not profile or not profile.must_change_password:
            return True
        if path == "/api/users/me/" and request.method == "GET":
            return True
        if path == "/api/users/me/password/" and request.method == "POST":
            return True
        raise PermissionDenied(self.message)


def user_role(user):
    if user.groups.filter(name="admin").exists():
        return "admin"
    return "user"


def user_permissions(user):
    owned = set()
    for code in PERMISSION_CODES:
        if user.has_perm(code):
            owned.add(code)
    return [code for code in PERMISSION_CODES if code in owned]
