import json
from pathlib import Path

import joblib
import torch

from ml.model import LoadLSTM

ARTIFACT_DIR = Path(__file__).resolve().parents[2] / "ml" / "artifacts"
RUNTIME = {"model": None, "scalers": None, "config": None, "error": "模型尚未加载"}


def load_runtime():
    try:
        config_path = ARTIFACT_DIR / "feature_config.json"
        weight_path = ARTIFACT_DIR / "lstm.pt"
        scaler_path = ARTIFACT_DIR / "scaler.pkl"
        if not (config_path.exists() and weight_path.exists() and scaler_path.exists()):
            raise FileNotFoundError("未找到模型文件，请先运行训练脚本")
        config = json.loads(config_path.read_text(encoding="utf-8"))
        model = LoadLSTM(config["input_size"])
        model.load_state_dict(torch.load(weight_path, map_location="cpu", weights_only=True))
        model.eval()
        RUNTIME.update(model=model, scalers=joblib.load(scaler_path), config=config, error=None)
    except Exception as exc:
        RUNTIME.update(model=None, scalers=None, config=None, error=str(exc))
    return RUNTIME


def get_runtime():
    if RUNTIME["model"] is None and RUNTIME["error"] in (None, "模型尚未加载"):
        return load_runtime()
    return RUNTIME
