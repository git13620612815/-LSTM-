import re
from datetime import timedelta

from django.contrib.auth.models import Group, Permission, User
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.permissions import PERMISSION_CATALOG, PERMISSION_CODES, IsAdminRole, user_permissions, user_role
from apps.common.response import ok
from apps.records.models import PredictionTask
from apps.users.models import LoginLock, LoginLog, UserProfile

USERNAME_RE = re.compile(r"^[A-Za-z0-9]{4,20}$")
PASSWORD_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,32}$")


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def check_password_rule(value):
    if not PASSWORD_RE.match(value or ""):
        raise ValidationError("密码需为 8-32 位且同时包含字母和数字")
    return value


def ensure_profile(user, phone="", department=""):
    profile, _created = UserProfile.objects.get_or_create(
        user=user, defaults={"phone": phone or "", "department": department or ""}
    )
    return profile


def public_user(user):
    profile = ensure_profile(user)
    role = user_role(user)
    return {
        "id": user.id,
        "username": user.username,
        "phone": profile.phone,
        "department": profile.department,
        "role": role,
        "role_name": "管理员" if role == "admin" else "普通用户",
        "is_active": user.is_active,
        "must_change_password": profile.must_change_password,
        "permissions": user_permissions(user),
    }


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        confirm = request.data.get("confirm_password") or ""
        phone = (request.data.get("phone") or "").strip()
        if not USERNAME_RE.match(username):
            raise ValidationError("用户名需为 4-20 位字母或数字")
        check_password_rule(password)
        if password != confirm:
            raise ValidationError("两次输入的密码不一致")
        if phone and not re.match(r"^1\d{10}$", phone):
            raise ValidationError("手机号格式不正确")
        if User.objects.filter(username=username).exists():
            raise ValidationError("用户名已存在")
        user = User.objects.create_user(username=username, password=password)
        ensure_profile(user, phone=phone)
        user.groups.add(Group.objects.get(name="user"))
        return ok(public_user(user), status=201)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        now = timezone.now()
        lock, _created = LoginLock.objects.get_or_create(username=username or "-")
        if lock.locked_until and lock.locked_until > now:
            LoginLog.objects.create(username=username, ip=client_ip(request), result="locked")
            raise ValidationError("账户已锁定，请 15 分钟后再试")
        user = User.objects.filter(username=username).first()
        if user is None or not user.check_password(password):
            if lock.window_start is None or lock.window_start < now - timedelta(minutes=15):
                lock.failed_count = 0
                lock.window_start = now
            lock.failed_count += 1
            if lock.failed_count >= 5:
                lock.locked_until = now + timedelta(minutes=15)
            lock.save()
            LoginLog.objects.create(
                user=user, username=username, ip=client_ip(request), result="failed"
            )
            raise ValidationError("用户名或密码错误")
        if not user.is_active:
            LoginLog.objects.create(user=user, username=username, ip=client_ip(request), result="failed")
            raise ValidationError("账户已被禁用")
        lock.failed_count = 0
        lock.window_start = None
        lock.locked_until = None
        lock.save()
        LoginLog.objects.create(user=user, username=username, ip=client_ip(request), result="success")
        refresh = RefreshToken.for_user(user)
        data = public_user(user)
        data.update(access=str(refresh.access_token), refresh=str(refresh))
        return ok(data)


class RefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            token = RefreshToken(request.data.get("refresh"))
            return ok({"access": str(token.access_token)})
        except Exception:
            raise ValidationError("登录已过期，请重新登录")


class LogoutView(APIView):
    def post(self, request):
        try:
            token = RefreshToken(request.data.get("refresh"))
            token.blacklist()
        except Exception:
            raise ValidationError("退出失败，刷新令牌无效")
        return ok()


class MeView(APIView):
    def get(self, request):
        return ok(public_user(request.user))

    def put(self, request):
        profile = ensure_profile(request.user)
        phone = request.data.get("phone", profile.phone)
        phone = (phone or "").strip()
        if phone and not re.match(r"^1\d{10}$", phone):
            raise ValidationError("手机号格式不正确")
        profile.phone = phone
        profile.department = (request.data.get("department", profile.department) or "")[:64]
        profile.save()
        return ok(public_user(request.user))


class PasswordView(APIView):
    def post(self, request):
        old = request.data.get("old_password") or ""
        new = request.data.get("new_password") or ""
        if not request.user.check_password(old):
            raise ValidationError("原密码不正确")
        check_password_rule(new)
        if old == new:
            raise ValidationError("新密码不能与原密码相同")
        request.user.set_password(new)
        request.user.save()
        profile = ensure_profile(request.user)
        profile.must_change_password = False
        profile.save()
        return ok()


class LoginLogView(APIView):
    def get(self, request):
        logs = request.user.login_logs.all()[:20]
        return ok(
            [
                {
                    "id": item.id,
                    "ip": item.ip,
                    "result": item.result,
                    "created_at": item.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                }
                for item in logs
            ]
        )


def _set_role(user, role):
    if role not in {"admin", "user"}:
        raise ValidationError("角色只能是管理员或普通用户")
    user.groups.clear()
    user.groups.add(Group.objects.get(name=role))


class AdminUserListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        keyword = (request.query_params.get("q") or "").strip()
        users = User.objects.all().order_by("-id")
        if keyword:
            users = users.filter(username__icontains=keyword)
        return ok({"count": users.count(), "results": [public_user(user) for user in users]})

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        role = request.data.get("role") or "user"
        if not USERNAME_RE.match(username):
            raise ValidationError("用户名需为 4-20 位字母或数字")
        check_password_rule(password)
        if User.objects.filter(username=username).exists():
            raise ValidationError("用户名已存在")
        user = User.objects.create_user(username=username, password=password, is_active=True)
        profile = ensure_profile(
            user,
            phone=(request.data.get("phone") or "").strip(),
            department=(request.data.get("department") or "").strip(),
        )
        if profile.phone and not re.match(r"^1\d{10}$", profile.phone):
            user.delete()
            raise ValidationError("手机号格式不正确")
        _set_role(user, role)
        return ok(public_user(user), status=201)


class AdminUserDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def _user(self, pk):
        user = User.objects.filter(pk=pk).first()
        if user is None:
            raise ValidationError("用户不存在")
        return user

    def get(self, request, pk):
        return ok(public_user(self._user(pk)))

    def put(self, request, pk):
        user = self._user(pk)
        role = request.data.get("role", user_role(user))
        is_active = request.data.get("is_active", user.is_active)
        if user == request.user and role != "admin":
            raise ValidationError("不能取消自己的管理员角色")
        if user == request.user and not is_active:
            raise ValidationError("不能禁用自己")
        profile = ensure_profile(user)
        phone = (request.data.get("phone", profile.phone) or "").strip()
        if phone and not re.match(r"^1\d{10}$", phone):
            raise ValidationError("手机号格式不正确")
        profile.phone = phone
        profile.department = (request.data.get("department", profile.department) or "")[:64]
        profile.save()
        user.is_active = bool(is_active)
        user.save()
        _set_role(user, role)
        return ok(public_user(user))

    def delete(self, request, pk):
        user = self._user(pk)
        if user == request.user:
            raise ValidationError("不能删除自己")
        if PredictionTask.objects.filter(user=user).exists():
            user.is_active = False
            user.save()
            return ok({"deleted": False, "disabled": True})
        user.delete()
        return ok({"deleted": True, "disabled": False})


class ResetPasswordView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request, pk):
        user = User.objects.filter(pk=pk).first()
        if user is None:
            raise ValidationError("用户不存在")
        temp = f"Reset{user.id:04d}"
        user.set_password(temp)
        user.save()
        profile = ensure_profile(user)
        profile.must_change_password = True
        profile.save()
        return ok({"password": temp})


def _permission(code):
    app, codename = code.split(".")
    return Permission.objects.get(content_type__app_label=app, codename=codename)


class RoleListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        roles = []
        for code, name in (("admin", "管理员"), ("user", "普通用户")):
            group = Group.objects.get(name=code)
            owned = {f"{item.content_type.app_label}.{item.codename}" for item in group.permissions.all()}
            roles.append(
                {
                    "code": code,
                    "name": name,
                    "permissions": [item for item in PERMISSION_CODES if item in owned],
                }
            )
        return ok(
            {
                "roles": roles,
                "catalog": [{"code": code, "name": name} for code, name in PERMISSION_CATALOG],
            }
        )


class RoleDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def put(self, request, code):
        if code not in {"admin", "user"}:
            raise ValidationError("角色不存在")
        codes = request.data.get("permissions") or []
        unknown = [item for item in codes if item not in PERMISSION_CODES]
        if unknown:
            raise ValidationError("包含未知权限")
        if code == "admin" and "users.manage_role" not in codes:
            raise PermissionDenied("不能移除管理员的角色管理权限")
        group = Group.objects.get(name=code)
        group.permissions.set([_permission(item) for item in codes])
        return ok({"code": code, "permissions": codes})
