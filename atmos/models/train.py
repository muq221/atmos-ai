"""Train and evaluate the three Atmos AI models.

1. category   - flight category (VFR/MVFR/IFR/LIFR) 3 hours ahead      (classifier)
2. visibility - visibility in metres 3 hours ahead                     (regressor, log scale)
3. thunder    - probability of a thunderstorm in the next 3 hours      (classifier)

Split is by time, never random: train on Jan 2024 - Aug 2025, test on
Sep - Dec 2025, so the test set is genuinely "future" data.

    python -m atmos.models.train
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, brier_score_loss, confusion_matrix,
                             f1_score, mean_absolute_error, recall_score, roc_auc_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from atmos import config
from atmos.aviation.rules import CATEGORIES


def load_split():
    gold = pd.read_parquet(config.GOLD / "features.parquet")
    feats = json.loads((config.GOLD / "feature_list.json").read_text())
    gold = gold.dropna(subset=["y_category", "y_visibility_m", "y_thunder"])
    train = gold[(gold.time >= config.TRAIN_START) & (gold.time <= config.TRAIN_END)]
    test = gold[(gold.time >= config.TEST_START) & (gold.time <= config.TEST_END)]
    return train, test, feats


def _cat_metrics(y_true, y_pred) -> dict:
    return {
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "macro_f1": round(f1_score(y_true, y_pred, average="macro"), 4),
        "recall_ifr_or_worse": round(recall_score(np.isin(y_true, ["IFR", "LIFR"]), np.isin(y_pred, ["IFR", "LIFR"])), 4),
        "per_class_recall": {c: round(r, 4) for c, r in zip(CATEGORIES, recall_score(y_true, y_pred, labels=CATEGORIES, average=None, zero_division=0))},
    }


def train_category(train, test, feats) -> tuple[object, dict]:
    Xtr, ytr, Xte, yte = train[feats], train["y_category"], test[feats], test["y_category"]
    results = {"persistence (no model)": _cat_metrics(yte, test["flight_category"])}
    candidates = {
        "logistic_regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=600, class_weight="balanced")),
        "random_forest": RandomForestClassifier(n_estimators=250, min_samples_leaf=4, class_weight="balanced_subsample",
                                                n_jobs=-1, random_state=42),
        "gradient_boosting": HistGradientBoostingClassifier(max_iter=350, learning_rate=0.06, max_leaf_nodes=31,
                                                            class_weight="balanced", random_state=42),
    }
    fitted = {}
    for name, model in candidates.items():
        t0 = time.time()
        model.fit(Xtr, ytr)
        pred = model.predict(Xte)
        results[name] = _cat_metrics(yte, pred) | {"train_seconds": round(time.time() - t0, 1)}
        fitted[name] = model
        print(f"  category  {name:<22} acc={results[name]['accuracy']:.3f}  macroF1={results[name]['macro_f1']:.3f}")
    best = max(candidates, key=lambda k: results[k]["macro_f1"])
    cm = confusion_matrix(yte, fitted[best].predict(Xte), labels=CATEGORIES)
    return fitted[best], {"best_model": best, "comparison": results, "confusion_matrix": cm.tolist(), "labels": CATEGORIES}


def train_visibility(train, test, feats) -> tuple[object, dict]:
    model = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.06, random_state=42)
    model.fit(train[feats], np.log10(train["y_visibility_m"].clip(lower=10)))
    pred = 10 ** model.predict(test[feats])
    y = test["y_visibility_m"].to_numpy()
    low = y < 5000
    m = {
        "mae_m": round(mean_absolute_error(y, pred)),
        "mae_m_persistence": round(mean_absolute_error(y, test["visibility_m"])),
        "mae_m_when_below_5km": round(mean_absolute_error(y[low], pred[low])),
        "mae_m_when_below_5km_persistence": round(mean_absolute_error(y[low], test["visibility_m"].to_numpy()[low])),
    }
    print(f"  visibility MAE={m['mae_m']} m (persistence {m['mae_m_persistence']} m)")
    return model, m


def train_thunder(train, test, feats) -> tuple[object, dict]:
    model = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, random_state=42)
    model.fit(train[feats], train["y_thunder"].astype(int))
    p = model.predict_proba(test[feats])[:, 1]
    y = test["y_thunder"].astype(int)
    m = {
        "roc_auc": round(roc_auc_score(y, p), 4),
        "pr_auc": round(average_precision_score(y, p), 4),
        "brier": round(brier_score_loss(y, p), 4),
        "base_rate": round(float(y.mean()), 4),
    }
    print(f"  thunder   ROC-AUC={m['roc_auc']:.3f}  PR-AUC={m['pr_auc']:.3f}")
    return model, m


def main() -> None:
    train, test, feats = load_split()
    print(f"train rows={len(train):,}  test rows={len(test):,}  features={len(feats)}")
    config.MODEL_DIR.mkdir(parents=True, exist_ok=True)

    cat_model, cat_m = train_category(train, test, feats)
    vis_model, vis_m = train_visibility(train, test, feats)
    ts_model, ts_m = train_thunder(train, test, feats)

    importances = None
    if hasattr(cat_model, "feature_importances_"):
        importances = dict(sorted(zip(feats, cat_model.feature_importances_.round(4).tolist()), key=lambda kv: -kv[1])[:15])

    joblib.dump({"category": cat_model, "visibility": vis_model, "thunder": ts_model, "features": feats},
                config.MODEL_DIR / "atmos_models.joblib", compress=3)
    meta = {
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_source": config.DATA_SOURCE,
        "horizon_hours": config.FORECAST_HORIZON_H,
        "train_period": [config.TRAIN_START, config.TRAIN_END],
        "test_period": [config.TEST_START, config.TEST_END],
        "rows": {"train": len(train), "test": len(test)},
        "n_features": len(feats),
        "category": cat_m,
        "visibility": vis_m,
        "thunder": ts_m,
        "top_features_category": importances,
    }
    (config.MODEL_DIR / "metrics.json").write_text(json.dumps(meta, indent=2))
    print("saved -> models/atmos_models.joblib, models/metrics.json")


if __name__ == "__main__":
    main()
