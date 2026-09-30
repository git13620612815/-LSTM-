import json
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

WINDOW = 24
BASE_FEATURES = ["load_mw", "hour", "weekday", "is_holiday"]
ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"


def generate_series(days=120, start="2023-01-01"):
    rng = np.random.default_rng(42)
    index = pd.date_range(start, periods=days * 24, freq="h")
    hour = index.hour.to_numpy()
    dow = index.dayofweek.to_numpy()
    daily = 90 * np.sin((hour - 7) / 24 * 2 * np.pi)
    weekly = 30 * np.cos(dow / 7 * 2 * np.pi)
    weekend = np.where(dow >= 5, -40, 0)
    holiday = ((index.month == 1) & (index.day == 1)).astype(int)
    load = 520 + daily + weekly + weekend - holiday * 50 + rng.normal(0, 8, len(index))
    temp = 8 + 10 * np.sin((hour - 15) / 24 * 2 * np.pi) + rng.normal(0, 0.4, len(index))
    temp[rng.random(len(index)) < 0.05] = np.nan
    return pd.DataFrame(
        {
            "timestamp": index.strftime("%Y-%m-%d %H:%M:%S"),
            "load_mw": np.round(load, 2),
            "temperature": np.round(temp, 2),
            "is_holiday": holiday,
        }
    )


def parse_timestamp(value):
    text = str(value).strip()
    if not text or text.lower() == "nan":
        raise ValueError("时间为空")
    ts = pd.to_datetime(text, errors="coerce")
    if pd.isna(ts):
        raise ValueError("时间无法解析")
    return pd.Timestamp(ts).to_pydatetime().replace(tzinfo=None, microsecond=0)


def assert_continuous(timestamps):
    stamps = list(timestamps)
    if len(stamps) < 2:
        return
    for prev, curr in zip(stamps, stamps[1:]):
        if curr - prev != timedelta(hours=1):
            raise ValueError("时间不连续，相邻点间隔必须为 1 小时")


def _as_frame(rows):
    frame = pd.DataFrame(rows)
    if "timestamp" not in frame.columns or "load_mw" not in frame.columns:
        raise ValueError("缺少 timestamp 或 load_mw 列")
    frame["timestamp"] = frame["timestamp"].map(parse_timestamp)
    frame["load_mw"] = pd.to_numeric(frame["load_mw"], errors="coerce")
    if "temperature" in frame.columns:
        frame["temperature"] = pd.to_numeric(frame["temperature"], errors="coerce")
    else:
        frame["temperature"] = np.nan
    if "is_holiday" not in frame.columns:
        frame["is_holiday"] = 0
    frame["is_holiday"] = pd.to_numeric(frame["is_holiday"], errors="coerce").fillna(0).astype(int)
    frame = frame.sort_values("timestamp").drop_duplicates("timestamp", keep="last")
    return frame.reset_index(drop=True)


def clean_for_training(frame):
    data = frame.copy()
    data = data.set_index("timestamp").sort_index()
    full_index = pd.date_range(data.index.min(), data.index.max(), freq="h")
    data = data.reindex(full_index)
    data.index.name = "timestamp"
    data["load_mw"] = data["load_mw"].interpolate(method="time", limit=3)
    data = data.dropna(subset=["load_mw"])
    if "temperature" not in data.columns:
        data["temperature"] = np.nan
    missing_rate = float(data["temperature"].isna().mean()) if len(data) else 1
    use_temperature = missing_rate < 0.2 and data["temperature"].notna().any()
    if use_temperature:
        data["temperature"] = data["temperature"].interpolate(method="time")
        data["temperature"] = data["temperature"].bfill().ffill()
    if "is_holiday" not in data.columns:
        data["is_holiday"] = 0
    data["is_holiday"] = data["is_holiday"].fillna(0).astype(int)
    data = data.reset_index()
    if len(data) <= WINDOW + 10:
        raise ValueError("有效样本不足，无法训练")
    split = int(len(data) * 0.8)
    low = float(np.quantile(data["load_mw"].iloc[:split], 0.01))
    high = float(np.quantile(data["load_mw"].iloc[:split], 0.99))
    data["load_mw"] = data["load_mw"].clip(low, high)
    return data, use_temperature, low, high, split


def fit_scalers(data, use_temperature, split):
    load_scaler = MinMaxScaler()
    load_scaler.fit(data["load_mw"].iloc[:split].to_numpy().reshape(-1, 1))
    temp_scaler = None
    if use_temperature:
        temp_scaler = MinMaxScaler()
        temp_scaler.fit(data["temperature"].iloc[:split].to_numpy().reshape(-1, 1))
    return {"load": load_scaler, "temperature": temp_scaler}


def feature_names(use_temperature):
    names = list(BASE_FEATURES)
    if use_temperature:
        names.append("temperature")
    return names


def transform_loads(values, scaler, low, high):
    clipped = np.clip(np.asarray(values, dtype=float), low, high).reshape(-1, 1)
    return scaler.transform(clipped).reshape(-1)


def build_feature_matrix(frame, config, scalers):
    loads = transform_loads(frame["load_mw"].to_numpy(), scalers["load"], config["load_q_low"], config["load_q_high"])
    stamps = pd.to_datetime(frame["timestamp"])
    columns = {
        "load_mw": loads,
        "hour": stamps.dt.hour.to_numpy() / 23.0,
        "weekday": stamps.dt.dayofweek.to_numpy() / 6.0,
        "is_holiday": frame["is_holiday"].fillna(0).to_numpy(dtype=float),
    }
    if config["use_temperature"]:
        temp = frame["temperature"].to_numpy(dtype=float) if "temperature" in frame.columns else np.full(len(frame), np.nan)
        known = ~np.isnan(temp)
        scaled = np.zeros(len(frame), dtype=float)
        if known.any():
            scaled[known] = scalers["temperature"].transform(temp[known].reshape(-1, 1)).reshape(-1)
        columns["temperature"] = scaled
    matrix = np.column_stack([columns[name] for name in config["features"]]).astype(np.float32)
    return matrix, loads.astype(np.float32)


def make_windows(frame, config, scalers):
    matrix, loads = build_feature_matrix(frame, config, scalers)
    stamps = list(pd.to_datetime(frame["timestamp"]))
    xs, ys, times = [], [], []
    for index in range(WINDOW, len(frame)):
        xs.append(matrix[index - WINDOW : index])
        ys.append(loads[index])
        times.append(stamps[index].to_pydatetime().replace(tzinfo=None))
    return np.stack(xs), np.asarray(ys, dtype=np.float32), times


def inverse_load(value, scaler):
    restored = float(scaler.inverse_transform(np.array([[value]], dtype=float))[0, 0])
    return round(max(restored, 0), 2)


def save_config(path, config):
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def load_config(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
