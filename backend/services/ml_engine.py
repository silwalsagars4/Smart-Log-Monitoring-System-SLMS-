"""
Isolation Forest ML engine.
Trains on a bootstrap dataset, serialises model, and predicts anomaly scores.
Auto-retrains on a schedule.
"""

import asyncio
import logging
import os
import time
from typing import Optional

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Synthetic normal training data to bootstrap the model before real logs arrive.
_BOOTSTRAP_SAMPLES = 2000


def _generate_bootstrap_data(n: int = _BOOTSTRAP_SAMPLES) -> np.ndarray:
    rng = np.random.default_rng(42)
    return np.column_stack([
        rng.integers(0, 6, n).astype(float),     # source idx
        rng.choice([200, 200, 200, 301, 302, 304, 404], n).astype(float),  # status
        rng.integers(0, 2, n).astype(float),      # is_error
        rng.integers(1, 50, n).astype(float),     # ip_count (normal traffic)
        rng.integers(0, 2, n).astype(float),      # ip_fail (low failures)
        rng.integers(5, 200, n).astype(float),    # global_events
        rng.integers(0, 24, n).astype(float),     # hour
        rng.integers(100, 5000, n).astype(float), # bytes
    ])


class MLEngine:
    def __init__(self):
        self._model: Optional[IsolationForest] = None
        self._training_buffer: list[list[float]] = []
        self._last_train: float = 0
        self._model_path = settings.ML_MODEL_PATH
        self._load_or_bootstrap()

    def _load_or_bootstrap(self):
        if os.path.exists(self._model_path):
            try:
                self._model = joblib.load(self._model_path)
                logger.info("Loaded ML model from %s", self._model_path)
                return
            except Exception as exc:
                logger.warning("Failed to load model, retaining bootstrap: %s", exc)
        self._train(_generate_bootstrap_data())

    def _train(self, X: np.ndarray):
        model = IsolationForest(
            n_estimators=200,
            contamination=settings.ML_CONTAMINATION,
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X)
        self._model = model
        self._last_train = time.time()
        os.makedirs(os.path.dirname(self._model_path), exist_ok=True)
        try:
            joblib.dump(model, self._model_path)
            logger.info("Model trained on %d samples and saved.", len(X))
        except Exception as exc:
            logger.warning("Could not save ML model: %s", exc)

    def add_to_buffer(self, features: list[float]):
        self._training_buffer.append(features)

    def maybe_retrain(self):
        elapsed_h = (time.time() - self._last_train) / 3600
        if elapsed_h >= settings.ML_RETRAIN_INTERVAL_HOURS and len(self._training_buffer) >= 500:
            X_new = np.array(self._training_buffer[-10_000:])
            X_boot = _generate_bootstrap_data(500)
            X = np.vstack([X_boot, X_new])
            self._train(X)
            self._training_buffer.clear()

    def predict(self, features: list[float]) -> tuple[float, bool]:
        """Returns (anomaly_score, is_anomaly)."""
        if self._model is None:
            return 0.0, False
        X = np.array(features).reshape(1, -1)
        score = float(-self._model.score_samples(X)[0])  # higher = more anomalous
        label = self._model.predict(X)[0]  # -1 = anomaly, 1 = normal
        return round(score, 4), label == -1


# Singleton
_engine: Optional[MLEngine] = None


def get_ml_engine() -> MLEngine:
    global _engine
    if _engine is None:
        _engine = MLEngine()
    return _engine
