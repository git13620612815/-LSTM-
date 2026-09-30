import argparse
import json
import sys
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.model import LoadLSTM
from ml.preprocess import (
    ARTIFACT_DIR,
    clean_for_training,
    feature_names,
    fit_scalers,
    generate_series,
    make_windows,
)

RUN_DIR = Path(__file__).resolve().parent / "runs" / "train"


def metrics(pred, actual):
    pred = np.asarray(pred, dtype=float)
    actual = np.asarray(actual, dtype=float)
    mae = float(np.mean(np.abs(pred - actual)))
    rmse = float(np.sqrt(np.mean((pred - actual) ** 2)))
    mask = actual != 0
    mape = float(np.mean(np.abs(pred[mask] - actual[mask]) / np.abs(actual[mask])) * 100) if mask.any() else None
    return {"mae": round(mae, 4), "rmse": round(rmse, 4), "mape": None if mape is None else round(mape, 4)}


def save_charts(history, times, actual, pred, score):
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
    plt.rcParams["axes.unicode_minus"] = False
    pd.DataFrame(history).to_csv(RUN_DIR / "results.csv", index=False)

    epochs = [item["epoch"] for item in history]
    plt.figure(figsize=(8, 4.5))
    plt.plot(epochs, [item["train_mse"] for item in history], label="训练损失")
    plt.plot(epochs, [item["val_mse"] for item in history], label="验证损失")
    plt.xlabel("轮次")
    plt.ylabel("MSE")
    plt.title("训练与验证损失")
    plt.legend()
    plt.tight_layout()
    plt.savefig(RUN_DIR / "loss_curve.png", dpi=120)
    plt.close()

    show = min(24 * 14, len(actual))
    stamps = pd.to_datetime(times[-show:])
    plt.figure(figsize=(10, 4.5))
    plt.plot(stamps, actual[-show:], label="真实负荷", linewidth=1.2)
    plt.plot(stamps, pred[-show:], label="预测负荷", linewidth=1.2)
    plt.xlabel("时间")
    plt.ylabel("负荷(MW)")
    plt.title(f"验证集末尾 {show // 24} 天  MAE {score['mae']}  MAPE {score['mape']}%")
    plt.legend()
    plt.tight_layout()
    plt.savefig(RUN_DIR / "pred_vs_actual.png", dpi=120)
    plt.close()

    plt.figure(figsize=(5.5, 5.5))
    plt.scatter(actual, pred, s=6, alpha=0.25)
    low = min(float(np.min(actual)), float(np.min(pred)))
    high = max(float(np.max(actual)), float(np.max(pred)))
    plt.plot([low, high], [low, high], color="#c0392b", linewidth=1)
    plt.xlabel("真实负荷(MW)")
    plt.ylabel("预测负荷(MW)")
    plt.title("验证集预测值与真实值")
    plt.tight_layout()
    plt.savefig(RUN_DIR / "pred_scatter.png", dpi=120)
    plt.close()


def train_dataframe(frame):
    torch.manual_seed(42)
    np.random.seed(42)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    data = frame.copy()
    data["timestamp"] = pd.to_datetime(data["timestamp"])
    data, use_temperature, low, high, split = clean_for_training(data)
    scalers = fit_scalers(data, use_temperature, split)
    config = {
        "window": 24,
        "features": feature_names(use_temperature),
        "use_temperature": bool(use_temperature),
        "input_size": len(feature_names(use_temperature)),
        "load_q_low": low,
        "load_q_high": high,
        "temp_fill": 0.0,
    }
    xs, ys, times = make_windows(data, config, scalers)
    cut = int(len(xs) * 0.8)
    train_x, val_x = xs[:cut], xs[cut:]
    train_y, val_y = ys[:cut], ys[cut:]
    val_times = times[cut:]

    model = LoadLSTM(config["input_size"])
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.MSELoss()
    loader = DataLoader(
        TensorDataset(torch.tensor(train_x), torch.tensor(train_y).unsqueeze(1)),
        batch_size=64,
        shuffle=True,
    )
    best_state = None
    best_loss = float("inf")
    patience = 0
    history = []
    for epoch in range(1, 51):
        model.train()
        total_loss = 0.0
        total_count = 0
        for batch_x, batch_y in loader:
            optimizer.zero_grad()
            loss = loss_fn(model(batch_x), batch_y)
            loss.backward()
            optimizer.step()
            total_loss += float(loss) * len(batch_x)
            total_count += len(batch_x)
        model.eval()
        with torch.no_grad():
            val_loss = float(loss_fn(model(torch.tensor(val_x)), torch.tensor(val_y).unsqueeze(1)))
        train_loss = total_loss / total_count
        history.append({"epoch": epoch, "train_mse": round(train_loss, 6), "val_mse": round(val_loss, 6)})
        print(f"epoch {epoch} train_mse {train_loss:.6f} val_mse {val_loss:.6f}", flush=True)
        if val_loss + 1e-6 < best_loss:
            best_loss = val_loss
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            patience = 0
        else:
            patience += 1
            if patience >= 8:
                print("early stop")
                break
    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        pred_scaled = model(torch.tensor(val_x)).numpy().reshape(-1)
    restored_pred = scalers["load"].inverse_transform(pred_scaled.reshape(-1, 1)).reshape(-1)
    restored_actual = scalers["load"].inverse_transform(val_y.reshape(-1, 1)).reshape(-1)
    score = metrics(restored_pred, restored_actual)
    save_charts(history, val_times, restored_actual, restored_pred, score)
    config["metrics"] = score
    torch.save(model.state_dict(), ARTIFACT_DIR / "lstm.pt")
    joblib.dump(scalers, ARTIFACT_DIR / "scaler.pkl")
    (ARTIFACT_DIR / "feature_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print("MAE", score["mae"], "RMSE", score["rmse"], "MAPE", score["mape"])
    return score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", help="用于训练的负荷 CSV，需包含 timestamp 和 load_mw")
    args = parser.parse_args()
    if args.csv:
        frame = pd.read_csv(args.csv)
    else:
        frame = generate_series()
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        frame.to_csv(ARTIFACT_DIR / "sample_load.csv", index=False)
    train_dataframe(frame)


if __name__ == "__main__":
    main()
