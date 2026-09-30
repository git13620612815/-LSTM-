import csv
import io

import pandas as pd
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.common.permissions import user_role
from apps.common.response import ok
from apps.datasets.models import LoadRecord
from apps.datasets.views import visible_datasets
from apps.forecast.runtime import get_runtime
from apps.forecast.services import _fail, points_to_frame, predict_batch, predict_single
from apps.records.models import PredictionTask
from ml.preprocess import WINDOW, assert_continuous


def _message(exc):
    detail = getattr(exc, "detail", exc)
    if isinstance(detail, list):
        return str(detail[0])
    return str(detail)


def task_queryset(user):
    if user.has_perm("forecast.view_all_record"):
        return PredictionTask.objects.select_related("user", "dataset")
    return PredictionTask.objects.select_related("user", "dataset").filter(user=user)


def filter_tasks(request, queryset):
    mode = request.query_params.get("mode")
    status = request.query_params.get("status")
    start = request.query_params.get("start")
    end = request.query_params.get("end")
    user_id = request.query_params.get("user_id")
    if mode:
        queryset = queryset.filter(mode=mode)
    if status:
        queryset = queryset.filter(status=status)
    if start:
        queryset = queryset.filter(created_at__gte=start)
    if end:
        queryset = queryset.filter(created_at__lte=end)
    if user_id and request.user.has_perm("forecast.view_all_record"):
        queryset = queryset.filter(user_id=user_id)
    return queryset


def task_brief(task):
    return {
        "id": task.id,
        "username": task.user.username,
        "mode": task.mode,
        "status": task.status,
        "dataset_name": task.dataset.name if task.dataset_id else "",
        "error_message": task.error_message,
        "metrics": task.metrics_json,
        "created_at": task.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    }


class ModelStatusView(APIView):
    def get(self, request):
        if not request.user.has_perm("forecast.add_prediction"):
            raise ValidationError("没有预测权限")
        runtime = get_runtime()
        config = runtime["config"] or {}
        return ok(
            {
                "ready": runtime["error"] is None,
                "message": runtime["error"] or "模型已就绪",
                "metrics": config.get("metrics"),
                "features": config.get("features") or [],
                "window": config.get("window") or WINDOW,
            }
        )


class SingleForecastView(APIView):
    def post(self, request):
        if not request.user.has_perm("forecast.add_prediction"):
            raise ValidationError("没有预测权限")
        dataset = None
        if request.data.get("points"):
            try:
                frame = points_to_frame(request.data.get("points"))
            except ValidationError as exc:
                _fail(request.user, "single", None, {"window": WINDOW}, _message(exc))
        else:
            dataset_id = request.data.get("dataset_id")
            end_time = request.data.get("end_time")
            if not dataset_id or not end_time:
                raise ValidationError("请提供 24 个历史点，或数据集与结束时刻")
            dataset = get_object_or_404(visible_datasets(request.user), pk=dataset_id, status="published")
            rows = list(
                LoadRecord.objects.filter(dataset=dataset, timestamp__lte=end_time)
                .order_by("-timestamp")
                .values("timestamp", "load_mw", "temperature", "is_holiday")[:WINDOW]
            )
            if len(rows) < WINDOW:
                _fail(request.user, "single", dataset, {"dataset_id": dataset.id, "end_time": end_time}, "截止时刻之前不足 24 小时数据")
            rows.reverse()
            end_text = str(end_time).replace("T", " ")[:19]
            if pd.Timestamp(rows[-1]["timestamp"]).strftime("%Y-%m-%d %H:%M:%S") != end_text:
                _fail(request.user, "single", dataset, {"dataset_id": dataset.id, "end_time": end_time}, "结束时刻在数据集中不存在")
            try:
                assert_continuous([item["timestamp"] for item in rows])
            except ValueError as exc:
                _fail(request.user, "single", dataset, {"dataset_id": dataset.id, "end_time": end_time}, str(exc))
            frame = pd.DataFrame(rows)
        return ok(predict_single(request.user, frame, dataset))


class BatchForecastView(APIView):
    def post(self, request):
        if not request.user.has_perm("forecast.add_prediction"):
            raise ValidationError("没有预测权限")
        upload = request.FILES.get("file")
        if upload is None:
            raise ValidationError("请上传 CSV 文件")
        if upload.size > 10 * 1024 * 1024:
            raise ValidationError("文件不能超过 10MB")
        if not (upload.name or "").lower().endswith(".csv"):
            raise ValidationError("只允许上传 CSV 文件")
        raw = upload.read()
        try:
            frame = pd.read_csv(io.BytesIO(raw))
        except Exception:
            raise ValidationError("CSV 无法解析")
        required = {"timestamp", "load_mw"}
        if not required.issubset(set(frame.columns)):
            raise ValidationError("CSV 必须包含 timestamp 和 load_mw 列")
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
        frame["load_mw"] = pd.to_numeric(frame["load_mw"], errors="coerce")
        if "temperature" not in frame.columns:
            frame["temperature"] = pd.NA
        if "is_holiday" not in frame.columns:
            frame["is_holiday"] = 0
        frame = frame.dropna(subset=["timestamp", "load_mw"])
        frame = frame[frame["load_mw"] >= 0]
        frame = frame.sort_values("timestamp").drop_duplicates("timestamp", keep="last")
        return ok(predict_batch(request.user, frame.reset_index(drop=True), raw, upload.name))


class TaskListView(APIView):
    def get(self, request):
        queryset = filter_tasks(request, task_queryset(request.user))
        try:
            page = max(int(request.query_params.get("page", 1)), 1)
            page_size = min(max(int(request.query_params.get("page_size", 10)), 1), 100)
        except ValueError:
            raise ValidationError("分页参数不正确")
        total = queryset.count()
        rows = queryset[(page - 1) * page_size : page * page_size]
        return ok({"count": total, "results": [task_brief(item) for item in rows]})


class TaskDetailView(APIView):
    def get(self, request, pk):
        task = get_object_or_404(task_queryset(request.user).prefetch_related("points"), pk=pk)
        points = [
            {
                "timestamp": item.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "predicted_load": item.predicted_load,
                "actual_load": item.actual_load,
                "kind": item.kind,
            }
            for item in task.points.all()
        ]
        return ok({**task_brief(task), "input": task.input_json, "points": points})


class TaskExportView(APIView):
    def get(self, request):
        queryset = filter_tasks(request, task_queryset(request.user)).prefetch_related("points")
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["任务ID", "用户", "模式", "状态", "预测时间", "预测负荷", "真实负荷", "创建时间", "错误信息"])
        for task in queryset:
            created = task.created_at.strftime("%Y-%m-%d %H:%M:%S")
            mode = "单次预测" if task.mode == "single" else "批量预测"
            status = "成功" if task.status == "success" else "失败"
            points = list(task.points.all())
            if not points:
                writer.writerow([task.id, task.user.username, mode, status, "", "", "", created, task.error_message])
                continue
            for point in points:
                writer.writerow(
                    [
                        task.id,
                        task.user.username,
                        mode,
                        status,
                        point.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        point.predicted_load,
                        "" if point.actual_load is None else point.actual_load,
                        created,
                        task.error_message,
                    ]
                )
        response = HttpResponse("\ufeff" + buffer.getvalue(), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="forecast_records.csv"'
        return response
