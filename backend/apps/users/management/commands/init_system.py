from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand

from apps.common.permissions import PERMISSION_CODES
from apps.users.models import UserProfile


class Command(BaseCommand):
    help = "初始化角色、权限和管理员账号"

    def handle(self, *args, **options):
        admin_group, _created = Group.objects.get_or_create(name="admin")
        user_group, _created = Group.objects.get_or_create(name="user")
        permissions = []
        for code in PERMISSION_CODES:
            app, codename = code.split(".")
            permissions.append(Permission.objects.get(content_type__app_label=app, codename=codename))
        admin_group.permissions.set(permissions)
        user_codes = {"datasets.view_dataset", "forecast.add_prediction"}
        user_group.permissions.set(
            [item for item in permissions if f"{item.content_type.app_label}.{item.codename}" in user_codes]
        )
        user, created = User.objects.get_or_create(username="admin", defaults={"is_active": True})
        if created:
            user.set_password("Admin12345")
            user.save()
        UserProfile.objects.get_or_create(user=user)
        user.groups.set([admin_group])
        self.stdout.write("管理员账号 admin / Admin12345")
