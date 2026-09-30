from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.common.permissions import IsAdminRole, user_role
from apps.common.response import ok
from apps.datasets.models import LoadDataset, LoadRecord
from apps.datasets.services import import_csv

ORDERING = {"timestamp", "-timestamp", "load_mw", "-load_mw"}


def visible_datasets(user):
    queryset = LoadDataset.objects.all()
    if user_role(user) != "admin":
        queryset = queryset.filter(status="published")
    return queryset


def dataset_payload(dataset):
    stat = getattr(dataset, "stat", None)
    return {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "sample_count": dataset.sample_count,
        "start_time": dataset.start_time.strftime("%Y-%m-%d %H:%M:%S") if dataset.start_time else None,
        "end_time": dataset.end_time.strftime("%Y-%m-%d %H:%M:%S") if dataset.end_time else None,
        "status": dataset.status,
        "created_at": dataset.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "columns": [
            {"name": item.name, "label": item.label, "dtype": item.dtype, "required": item.required}
            for item in dataset.columns.all()
        ],
        "stat": None
        if stat is None
        else {
            "mean": stat.mean,
            "std": stat.std,
            "minimum": stat.minimum,
            "maximum": stat.maximum,
            "missing_rate": stat.missing_rate,
        },
    }


class DatasetListView(APIView):
    def get(self, request):
        if not request.user.has_perm("datasets.view_dataset"):
            raise ValidationError("没有数据预览权限")
        queryset = visible_datasets(request.user)
        status = request.query_params.get("status")
        if status and user_role(request.user) == "admin":
            queryset = queryset.filter(status=status)
        results = [dataset_payload(item) for item in queryset.prefetch_related("columns")]
        return ok({"count": len(results), "results": results})


class DatasetDetailView(APIView):
    def get(self, request, pk):
        if not request.user.has_perm("datasets.view_dataset"):
            raise ValidationError("没有数据预览权限")
        dataset = get_object_or_404(visible_datasets(request.user).prefetch_related("columns"), pk=pk)
        return ok(dataset_payload(dataset))


class DatasetRecordView(APIView):
    def get(self, request, pk):
        if not request.user.has_perm("datasets.view_dataset"):
            raise ValidationError("没有数据预览权限")
        dataset = get_object_or_404(visible_datasets(request.user), pk=pk)
        ordering = request.query_params.get("ordering") or "timestamp"
        if ordering not in ORDERING:
            raise ValidationError("排序字段不支持")
        records = dataset.records.all()
        start = request.query_params.get("start")
        end = request.query_params.get("end")
        if start:
            records = records.filter(timestamp__gte=start)
        if end:
            records = records.filter(timestamp__lte=end)
        records = records.order_by(ordering)
        try:
            page = max(int(request.query_params.get("page", 1)), 1)
            page_size = min(max(int(request.query_params.get("page_size", 20)), 1), 100)
        except ValueError:
            raise ValidationError("分页参数不正确")
        total = records.count()
        start_index = (page - 1) * page_size
        rows = records[start_index : start_index + page_size]
        return ok(
            {
                "count": total,
                "results": [
                    {
                        "timestamp": item.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "load_mw": item.load_mw,
                        "temperature": item.temperature,
                        "is_holiday": item.is_holiday,
                    }
                    for item in rows
                ],
            }
        )


class DatasetUploadView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request):
        upload = request.FILES.get("file")
        name = (request.data.get("name") or "").strip()
        if upload is None:
            raise ValidationError("请上传 CSV 文件")
        if not name:
            raise ValidationError("请填写数据集名称")
        dataset = import_csv(upload, name, request.data.get("description") or "", request.user)
        return ok(dataset_payload(dataset), status=201)


class DatasetAdminDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def put(self, request, pk):
        dataset = get_object_or_404(LoadDataset, pk=pk)
        name = request.data.get("name")
        if name is not None:
            name = name.strip()
            if not name:
                raise ValidationError("数据集名称不能为空")
            dataset.name = name
        if "description" in request.data:
            dataset.description = request.data.get("description") or ""
        status = request.data.get("status")
        if status is not None:
            if status not in {"draft", "published", "disabled"}:
                raise ValidationError("状态不正确")
            if status == "published" and dataset.sample_count <= 0:
                raise ValidationError("没有样本，不能发布")
            dataset.status = status
        dataset.save()
        return ok(dataset_payload(LoadDataset.objects.prefetch_related("columns").get(pk=dataset.pk)))

    def delete(self, request, pk):
        dataset = get_object_or_404(LoadDataset, pk=pk)
        dataset.delete()
        return ok()


class DatasetTrainView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request, pk):
        import pandas as pd

        from apps.forecast.runtime import load_runtime
        from ml.train import train_dataframe

        dataset = get_object_or_404(LoadDataset, pk=pk)
        rows = list(dataset.records.values("timestamp", "load_mw", "temperature", "is_holiday"))
        if len(rows) <= 34:
            raise ValidationError("有效样本不足，至少需要连续 35 小时数据")
        try:
            score = train_dataframe(pd.DataFrame(rows))
        except ValueError as exc:
            raise ValidationError(str(exc))
        load_runtime()
        return ok(score)


class DatasetReimportView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request, pk):
        dataset = get_object_or_404(LoadDataset, pk=pk)
        upload = request.FILES.get("file")
        if upload is None:
            raise ValidationError("请上传 CSV 文件")
        import_csv(
            upload,
            (request.data.get("name") or dataset.name).strip(),
            request.data.get("description", dataset.description),
            request.user,
            dataset=dataset,
        )
        return ok(dataset_payload(LoadDataset.objects.prefetch_related("columns").get(pk=pk)))
