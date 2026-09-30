import numpy as np
import pandas as pd
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from apps.common.response import ok
from apps.datasets.views import visible_datasets

WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def load_frame(user, pk):
    if not user.has_perm("datasets.view_dataset"):
        raise ValidationError("没有数据预览权限")
    dataset = get_object_or_404(visible_datasets(user), pk=pk)
    rows = list(dataset.records.values_list("timestamp", "load_mw"))
    frame = pd.DataFrame(rows, columns=["timestamp", "load_mw"])
    if not frame.empty:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    return frame


class OverviewView(APIView):
    def get(self, request, pk):
        frame = load_frame(request.user, pk)
        if frame.empty:
            return ok({"mean": 0, "minimum": 0, "maximum": 0, "std": 0, "labels": [], "values": []})
        monthly = frame.groupby(frame["timestamp"].dt.to_period("M")).size()
        return ok(
            {
                "mean": round(float(frame["load_mw"].mean()), 2),
                "minimum": round(float(frame["load_mw"].min()), 2),
                "maximum": round(float(frame["load_mw"].max()), 2),
                "std": round(float(frame["load_mw"].std(ddof=1)) if len(frame) > 1 else 0, 2),
                "labels": [str(item) for item in monthly.index],
                "values": [int(item) for item in monthly.values],
            }
        )


class SeriesView(APIView):
    def get(self, request, pk):
        frame = load_frame(request.user, pk)
        granularity = request.query_params.get("granularity") or "day"
        aggregated = False
        if frame.empty:
            return ok({"labels": [], "values": [], "aggregated": False})
        if granularity == "hour" and len(frame) > 2000:
            granularity = "day"
            aggregated = True
        if granularity == "hour":
            grouped = frame.groupby(frame["timestamp"].dt.floor("h"))["load_mw"].mean()
            labels = [item.strftime("%Y-%m-%d %H:%M") for item in grouped.index]
        else:
            grouped = frame.groupby(frame["timestamp"].dt.floor("D"))["load_mw"].mean()
            labels = [item.strftime("%Y-%m-%d") for item in grouped.index]
        return ok(
            {
                "labels": labels,
                "values": [round(float(item), 2) for item in grouped.values],
                "aggregated": aggregated,
            }
        )


class DistributionView(APIView):
    def get(self, request, pk):
        frame = load_frame(request.user, pk)
        if frame.empty:
            return ok({"labels": [], "values": []})
        try:
            bins = int(request.query_params.get("bins", 10))
        except ValueError:
            bins = 10
        bins = min(max(bins, 5), 20)
        counts, edges = np.histogram(frame["load_mw"], bins=bins)
        labels = [f"{edges[i]:.0f}-{edges[i + 1]:.0f}" for i in range(len(counts))]
        return ok({"labels": labels, "values": [int(item) for item in counts]})


class ProfileView(APIView):
    def get(self, request, pk):
        frame = load_frame(request.user, pk)
        if frame.empty:
            return ok({"weekday": {"labels": WEEKDAYS, "values": []}, "hour": {"labels": [], "values": []}})
        by_week = frame.groupby(frame["timestamp"].dt.dayofweek)["load_mw"].mean()
        by_hour = frame.groupby(frame["timestamp"].dt.hour)["load_mw"].mean()
        return ok(
            {
                "weekday": {
                    "labels": WEEKDAYS,
                    "values": [round(float(by_week.get(i, 0)), 2) for i in range(7)],
                },
                "hour": {
                    "labels": [f"{i:02d}:00" for i in range(24)],
                    "values": [round(float(by_hour.get(i, 0)), 2) for i in range(24)],
                },
            }
        )
