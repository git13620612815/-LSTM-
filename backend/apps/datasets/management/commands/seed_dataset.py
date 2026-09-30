from pathlib import Path

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand

from apps.datasets.services import import_csv


class Command(BaseCommand):
    help = "把训练样本导入为已发布数据集"

    def handle(self, *args, **options):
        path = Path(__file__).resolve().parents[4] / "ml" / "artifacts" / "sample_load.csv"
        if not path.exists():
            self.stderr.write("请先运行 python -m ml.train")
            return
        admin = User.objects.filter(username="admin").first()
        upload = SimpleUploadedFile("sample_load.csv", path.read_bytes(), content_type="text/csv")
        dataset = import_csv(upload, "示例小时负荷", "训练脚本生成的 120 天小时负荷", admin)
        dataset.status = "published"
        dataset.save(update_fields=["status"])
        self.stdout.write(f"已发布数据集 {dataset.id}，样本 {dataset.sample_count}")
