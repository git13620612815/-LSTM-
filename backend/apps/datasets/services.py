import csv
import io
import uuid
from datetime import datetime

import numpy as np
from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.datasets.models import DatasetColumn, DatasetStat, LoadDataset, LoadRecord

COLUMN_META = {
    "timestamp": ("时间", "datetime", True),
    "load_mw": ("负荷(MW)", "float", True),
    "temperature": ("气温", "float", False),
    "is_holiday": ("是否节假日", "int", False),
}
MAX_ROWS = 200000


def ensure_csv(upload):
    name = (upload.name or "").lower()
    if not name.endswith(".csv"):
        raise ValidationError("只允许上传 CSV 文件")
    content_type = getattr(upload, "content_type", "") or ""
    allowed = {"text/csv", "application/vnd.ms-excel", "application/octet-stream", "text/plain", ""}
    if content_type not in allowed:
        raise ValidationError("文件类型不正确")
    if upload.size > 10 * 1024 * 1024:
        raise ValidationError("文件不能超过 10MB")


def _parse_holiday(value):
    text = str(value).strip().lower()
    if text in {"", "nan", "none"}:
        return 0
    if text in {"1", "true", "yes", "y", "是"}:
        return 1
    if text in {"0", "false", "no", "n", "否"}:
        return 0
    raise ValueError("节假日取值无法识别")


def _parse_rows(raw):
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValidationError("CSV 必须使用 UTF-8 编码")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or "timestamp" not in reader.fieldnames or "load_mw" not in reader.fieldnames:
        raise ValidationError("CSV 必须包含 timestamp 和 load_mw 列")
    rows = list(reader)
    if not rows:
        raise ValidationError("文件没有数据行")
    if len(rows) > MAX_ROWS:
        raise ValidationError("行数不能超过 20000")
    errors = []
    parsed = []
    has_temp = "temperature" in reader.fieldnames
    has_holiday = "is_holiday" in reader.fieldnames
    for index, row in enumerate(rows, start=2):
        try:
            stamp = datetime.strptime(str(row.get("timestamp", "")).strip(), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                stamp = datetime.fromisoformat(str(row.get("timestamp", "")).strip())
            except ValueError:
                errors.append({"row": index, "message": "时间无法解析"})
                continue
        try:
            load = float(str(row.get("load_mw", "")).strip())
        except ValueError:
            errors.append({"row": index, "message": "负荷为空或不是数字"})
            continue
        if load < 0:
            errors.append({"row": index, "message": "负荷小于 0"})
            continue
        temperature = None
        if has_temp and str(row.get("temperature", "")).strip() not in {"", "nan"}:
            try:
                temperature = float(row["temperature"])
            except ValueError:
                errors.append({"row": index, "message": "气温不是数字"})
                continue
        try:
            holiday = _parse_holiday(row.get("is_holiday", 0)) if has_holiday else 0
        except ValueError as exc:
            errors.append({"row": index, "message": str(exc)})
            continue
        parsed.append(
            {"timestamp": stamp.replace(microsecond=0), "load_mw": load, "temperature": temperature, "is_holiday": holiday}
        )
    return parsed, errors, len(rows), has_temp, has_holiday


def import_csv(upload, name, description, user, dataset=None):
    ensure_csv(upload)
    raw = upload.read()
    parsed, errors, total, has_temp, has_holiday = _parse_rows(raw)
    if total and len(errors) / total > 0.05:
        preview = "；".join(f"第{item['row']}行{item['message']}" for item in errors[:8])
        raise ValidationError(f"错误行超过 5%，导入已回滚。{preview}")
    merged = {}
    for item in parsed:
        merged[item["timestamp"]] = item
    records = list(merged.values())
    if not records:
        raise ValidationError("没有可入库的有效数据")
    records.sort(key=lambda item: item["timestamp"])
    loads = np.array([item["load_mw"] for item in records], dtype=float)
    temps = [item["temperature"] for item in records]
    temp_missing = sum(value is None for value in temps) / len(records) if has_temp else 0
    missing_rate = len(errors) / total if total else 0
    with transaction.atomic():
        if dataset is None:
            dataset = LoadDataset.objects.create(
                name=name, description=description or "", uploaded_by=user, status="draft"
            )
        else:
            dataset.name = name or dataset.name
            if description is not None:
                dataset.description = description
            dataset.records.all().delete()
            dataset.columns.all().delete()
        dataset.source_file.save(f"{uuid.uuid4().hex}.csv", ContentFile(raw), save=False)
        dataset.sample_count = len(records)
        dataset.start_time = records[0]["timestamp"]
        dataset.end_time = records[-1]["timestamp"]
        dataset.save()
        LoadRecord.objects.bulk_create(
            [LoadRecord(dataset=dataset, **item) for item in records],
            batch_size=1000,
        )
        columns = [("timestamp", True), ("load_mw", True)]
        if has_temp:
            columns.append(("temperature", False))
        if has_holiday:
            columns.append(("is_holiday", False))
        DatasetColumn.objects.bulk_create(
            [
                DatasetColumn(
                    dataset=dataset,
                    name=field,
                    label=COLUMN_META[field][0],
                    dtype=COLUMN_META[field][1],
                    required=required,
                    order=order,
                )
                for order, (field, required) in enumerate(columns)
            ]
        )
        DatasetStat.objects.update_or_create(
            dataset=dataset,
            defaults={
                "mean": round(float(loads.mean()), 2),
                "std": round(float(loads.std(ddof=1)) if len(loads) > 1 else 0, 2),
                "minimum": round(float(loads.min()), 2),
                "maximum": round(float(loads.max()), 2),
                "missing_rate": round(float(missing_rate if not has_temp else temp_missing), 4),
            },
        )
    return dataset
