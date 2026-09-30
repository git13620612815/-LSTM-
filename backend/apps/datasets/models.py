from django.conf import settings
from django.db import models


class DatasetPermission(models.Model):
    class Meta:
        default_permissions = ()
        permissions = [
            ("manage_dataset", "管理数据集"),
            ("view_dataset", "预览数据集"),
        ]


class LoadDataset(models.Model):
    STATUS_CHOICES = [
        ("draft", "草稿"),
        ("published", "已发布"),
        ("disabled", "已停用"),
    ]
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=500, blank=True, default="")
    source_file = models.FileField(upload_to="datasets/", blank=True)
    sample_count = models.IntegerField(default=0)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="draft")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="datasets"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class DatasetColumn(models.Model):
    dataset = models.ForeignKey(LoadDataset, on_delete=models.CASCADE, related_name="columns")
    name = models.CharField(max_length=64)
    label = models.CharField(max_length=64)
    dtype = models.CharField(max_length=32)
    required = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]


class DatasetStat(models.Model):
    dataset = models.OneToOneField(LoadDataset, on_delete=models.CASCADE, related_name="stat")
    mean = models.FloatField(default=0)
    std = models.FloatField(default=0)
    minimum = models.FloatField(default=0)
    maximum = models.FloatField(default=0)
    missing_rate = models.FloatField(default=0)


class LoadRecord(models.Model):
    dataset = models.ForeignKey(LoadDataset, on_delete=models.CASCADE, related_name="records")
    timestamp = models.DateTimeField()
    load_mw = models.FloatField()
    temperature = models.FloatField(null=True, blank=True)
    is_holiday = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["dataset", "timestamp"], name="uniq_dataset_timestamp"),
        ]
        ordering = ["timestamp"]
        indexes = [
            models.Index(fields=["dataset", "load_mw"]),
        ]
