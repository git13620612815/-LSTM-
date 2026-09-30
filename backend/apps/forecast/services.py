import uuid
from datetime import timedelta

import numpy as np
import pandas as pd
import torch
from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.forecast.runtime import get_runtime
from apps.records.models import PredictionPoint, PredictionTask
from ml.preprocess import WINDOW, assert_continuous, build_feature_matrix, inverse_load, parse_timestamp


def _require_runtime():
    runtime = get_runtime()
    if runtime["error"]:
        raise ValidationError(runtime["error"])
    return runtime


def points_to_frame(points):
    if len(points) != WINDOW:
        raise ValidationError("单次预测需要连续 24 个小时的历史负荷")
    rows = []
    for item in points:
        try:
            load = float(item["load_mw"])
        except (TypeError, ValueError, KeyError):
            raise ValidationError("负荷必须是大于等于 0 的数字")
        if load < 0:
            raise ValidationError("负荷不能小于 0")
        try:
            stamp = parse_timestamp(item["timestamp"])
        except ValueError as exc:
            raise ValidationError(str(exc))
        temperature = item.get("temperature")
        holiday = item.get("is_holiday", 0) or 0
        rows.append(
            {
                "timestamp": stamp,
                "load_mw": load,
                "temperature": None if temperature in (None, "") else float(temperature),
                "is_holiday": int(holiday),
            }
        )
    frame = pd.DataFrame(rows).sort_values("timestamp")
    try:
        assert_continuous(frame["timestamp"])
    except ValueError as exc:
        raise ValidationError(str(exc))
    return frame.reset_index(drop=True)


def _predict_window(frame, runtime):
    matrix, _loads = build_feature_matrix(frame, runtime["config"], runtime["scalers"])
    if matrix.shape[1] != runtime["config"]["input_size"]:
        raise ValidationError("特征维度与模型配置不一致")
    with torch.no_grad():
        value = runtime["model"](torch.tensor(matrix[-WINDOW:]).unsqueeze(0)).item()
    return inverse_load(value, runtime["scalers"]["load"])


def _history_payload(frame):
    payload = []
    for row in frame.itertuples(index=False):
        payload.append(
            {
                "timestamp": pd.Timestamp(row.timestamp).strftime("%Y-%m-%d %H:%M:%S"),
                "load_mw": round(float(row.load_mw), 2),
            }
        )
    return payload


def _save_task(user, mode, dataset, summary, status, error, metrics, points, upload_name=None, raw=None):
    with transaction.atomic():
        task = PredictionTask.objects.create(
            user=user,
            mode=mode,
            dataset=dataset,
            input_json=summary,
            status=status,
            error_message=error[:500],
            metrics_json=metrics or {},
        )
        if raw is not None:
            task.input_file.save(f"{uuid.uuid4().hex}.csv", ContentFile(raw), save=True)
        PredictionPoint.objects.bulk_create(
            [
                PredictionPoint(
                    task=task,
                    timestamp=item["timestamp"],
                    predicted_load=item["predicted_load"],
                    actual_load=item.get("actual_load"),
                    kind=item.get("kind", "point"),
                )
                for item in points
            ]
        )
    return task


def _fail(user, mode, dataset, summary, message, upload_name=None, raw=None):
    task = _save_task(user, mode, dataset, summary, "failed", message, {}, [], upload_name, raw)
    exc = ValidationError(message)
    exc.task_id = task.id
    raise exc


def predict_single(user, frame, dataset=None):
    summary = {
        "window": WINDOW,
        "start": pd.Timestamp(frame["timestamp"].iloc[0]).strftime("%Y-%m-%d %H:%M:%S"),
        "end": pd.Timestamp(frame["timestamp"].iloc[-1]).strftime("%Y-%m-%d %H:%M:%S"),
        "history": _history_payload(frame),
    }
    try:
        runtime = _require_runtime()
        predicted = _predict_window(frame, runtime)
    except ValidationError as exc:
        _fail(user, "single", dataset, summary, str(exc.detail if hasattr(exc, "detail") else exc))
    predicted_time = frame["timestamp"].iloc[-1] + timedelta(hours=1)
    task = _save_task(
        user,
        "single",
        dataset,
        summary,
        "success",
        "",
        {},
        [{"timestamp": predicted_time, "predicted_load": predicted, "actual_load": None, "kind": "point"}],
    )
    return {
        "task_id": task.id,
        "predicted_time": predicted_time.strftime("%Y-%m-%d %H:%M:%S"),
        "predicted_load": predicted,
        "history": summary["history"],
    }


def _score(pairs):
    if not pairs:
        return {}
    actual = np.array([item[0] for item in pairs], dtype=float)
    pred = np.array([item[1] for item in pairs], dtype=float)
    mae = float(np.mean(np.abs(pred - actual)))
    rmse = float(np.sqrt(np.mean((pred - actual) ** 2)))
    mask = actual != 0
    mape = float(np.mean(np.abs(pred[mask] - actual[mask]) / np.abs(actual[mask])) * 100) if mask.any() else None
    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "mape": None if mape is None else round(mape, 2),
    }


def predict_batch(user, frame, raw, filename):
    summary = {
        "filename": filename,
        "rows": int(len(frame)),
        "start": pd.Timestamp(frame["timestamp"].iloc[0]).strftime("%Y-%m-%d %H:%M:%S"),
        "end": pd.Timestamp(frame["timestamp"].iloc[-1]).strftime("%Y-%m-%d %H:%M:%S"),
    }
    try:
        if len(frame) > 20000:
            raise ValidationError("行数不能超过 20000")
        if len(frame) < WINDOW:
            raise ValidationError("至少需要 24 小时历史数据")
        assert_continuous(frame["timestamp"])
        runtime = _require_runtime()
    except (ValidationError, ValueError) as exc:
        message = exc.detail[0] if isinstance(getattr(exc, "detail", None), list) else str(getattr(exc, "detail", exc))
        _fail(user, "batch", None, summary, str(message), filename, raw)

    points = []
    pairs = []
    stamps = list(frame["timestamp"])
    loads = list(frame["load_mw"])
    for index in range(WINDOW, len(frame)):
        window = frame.iloc[index - WINDOW : index]
        predicted = _predict_window(window, runtime)
        actual = round(float(loads[index]), 2)
        points.append(
            {
                "timestamp": stamps[index].to_pydatetime() if hasattr(stamps[index], "to_pydatetime") else stamps[index],
                "predicted_load": predicted,
                "actual_load": actual,
                "kind": "point",
            }
        )
        pairs.append((actual, predicted))

    history = frame.iloc[-WINDOW:].copy()
    horizon = []
    cursor = history.copy()
    for _step in range(24):
        predicted = _predict_window(cursor, runtime)
        next_time = cursor["timestamp"].iloc[-1] + timedelta(hours=1)
        item = {
            "timestamp": next_time,
            "predicted_load": predicted,
            "actual_load": None,
            "kind": "horizon",
        }
        horizon.append(item)
        extra = {
            "timestamp": next_time,
            "load_mw": predicted,
            "temperature": np.nan,
            "is_holiday": 0,
        }
        cursor = pd.concat([cursor, pd.DataFrame([extra])], ignore_index=True).iloc[-WINDOW:]

    metrics = _score(pairs)
    task = _save_task(user, "batch", None, summary, "success", "", metrics, points + horizon, filename, raw)
    return {
        "task_id": task.id,
        "points": [
            {
                "timestamp": item["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                "predicted_load": item["predicted_load"],
                "actual_load": item["actual_load"],
            }
            for item in points
        ],
        "forecast_24h": [
            {
                "timestamp": item["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                "predicted_load": item["predicted_load"],
            }
            for item in horizon
        ],
        **metrics,
    }
