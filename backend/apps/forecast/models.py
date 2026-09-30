from django.db import models


class ForecastPermission(models.Model):
    class Meta:
        default_permissions = ()
        permissions = [
            ("add_prediction", "发起预测"),
            ("view_all_record", "查看全部预测记录"),
        ]
