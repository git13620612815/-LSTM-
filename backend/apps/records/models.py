from django.conf import settings
from django.db import models


class PredictionTask(models.Model):
    MODE_CHOICES = [("single", "单次预测"), ("batch", "批量预测")]
    STATUS_CHOICES = [("success", "成功"), ("failed", "失败")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="prediction_tasks")
    mode = models.CharField(max_length=16, choices=MODE_CHOICES)
    dataset = models.ForeignKey(
        "datasets.LoadDataset", null=True, blank=True, on_delete=models.SET_NULL, related_name="prediction_tasks"
    )
    input_json = models.JSONField(default=dict, blank=True)
    input_file = models.FileField(upload_to="forecasts/", blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES)
    error_message = models.CharField(max_length=500, blank=True, default="")
    metrics_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class PredictionPoint(models.Model):
    task = models.ForeignKey(PredictionTask, on_delete=models.CASCADE, related_name="points")
    timestamp = models.DateTimeField()
    predicted_load = models.FloatField()
    actual_load = models.FloatField(null=True, blank=True)
    kind = models.CharField(max_length=16, default="point")

    class Meta:
        ordering = ["timestamp", "id"]
