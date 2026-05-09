"""
Smart ML Engine — Enhanced Ensemble Anomaly Detection.

Improvements over v1:
  - RobustScaler instead of StandardScaler (resistant to log-data outliers)
  - AdaptiveWeightManager: learns which model is most accurate over time
  - EWMADriftDetector: combines CUSUM + EWMA for more sensitive drift detection
  - ScoreCalibrator: percentile-based normalization against live score distribution
  - TemporalContextTracker: per-source rolling statistics catch burst patterns
  - ModelAgreementVoter: consensus score based on model disagreement penalty
  - Smarter bootstrap data with injected anomaly patterns for better initial training
"""

import asyncio
import logging
import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Optional

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import RobustScaler   # v1 used StandardScaler — bad for outlier-heavy logs

from config import get_settings
from services.log_classifier import LogClassifier

logger = logging.getLogger(__name__)
settings = get_settings()


# ──────────────────────────────────────────────────────────────────────────────
# Data class
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class MLResult:
    score: float
    is_anomaly: bool
    if_score: float
    lof_score: float
    svm_score: float
    supervised_sev: str
    supervised_conf: float
    confidence: float
    drift_detected: bool
    # NEW fields
    model_agreement: float          # 0-1: how much the 3 models agreed
    temporal_boost: float           # extra score from burst/repeat detection
    calibrated_percentile: float    # where this score sits in recent distribution


# ──────────────────────────────────────────────────────────────────────────────
# Adaptive Weight Manager
# Tracks each model's "hit rate" on confirmed anomalies and adjusts weights.
# ──────────────────────────────────────────────────────────────────────────────

class AdaptiveWeightManager:
    """
    Maintains exponentially-weighted accuracy estimates for each sub-model.
    When a prediction is later confirmed (or contradicted) via feedback,
    call `record_feedback`. Without feedback the weights decay toward equal.
    """

    _BASE = np.array([0.55, 0.30, 0.15], dtype=float)   # IF, LOF, SVM
    _ALPHA = 0.05   # EMA decay for weight updates
    _MIN_W = 0.10   # floor so no model is ever silenced completely

    def __init__(self):
        self._scores = np.array([1.0, 1.0, 1.0], dtype=float)   # accuracy proxies

    def get_weights(self, svm_active: bool) -> np.ndarray:
        raw = self._BASE * self._scores
        if not svm_active:
            raw[2] = 0.0
        total = raw.sum()
        if total == 0:
            raw = self._BASE.copy()
            if not svm_active:
                raw[2] = 0.0
            total = raw.sum()
        weights = np.clip(raw / total, self._MIN_W, None)
        return weights / weights.sum()

    def record_feedback(self, model_idx: int, was_correct: bool):
        """Call when we get a ground-truth signal (e.g., analyst confirms anomaly)."""
        delta = self._ALPHA if was_correct else -self._ALPHA
        self._scores[model_idx] = float(np.clip(self._scores[model_idx] + delta, 0.1, 2.0))


# ──────────────────────────────────────────────────────────────────────────────
# EWMA + CUSUM Drift Detector
# v1 only used CUSUM. Adding EWMA makes detection faster on slow drift.
# ──────────────────────────────────────────────────────────────────────────────

class EWMADriftDetector:
    """
    Combines CUSUM (abrupt drift) with EWMA control chart (gradual drift).
    Triggers when EITHER method signals.
    """

    def __init__(self, k: float = 0.5, h: float = 5.0, ewma_lambda: float = 0.1, ewma_k: float = 3.0):
        # CUSUM params
        self._k = k
        self._h = h
        self._s_pos = 0.0
        self._s_neg = 0.0

        # EWMA params
        self._lam = ewma_lambda
        self._ewma_k = ewma_k
        self._ewma = None
        self._ewma_var = None
        self._n = 0

    def update(self, score: float) -> bool:
        # ── EWMA ──
        if self._ewma is None:
            self._ewma = score
            self._ewma_var = 0.01
            self._n = 1
            return False

        self._ewma = self._lam * score + (1 - self._lam) * self._ewma
        self._ewma_var = self._lam * (score - self._ewma) ** 2 + (1 - self._lam) * self._ewma_var
        self._n += 1

        sigma = max(np.sqrt(self._ewma_var), 1e-6)
        ewma_alarm = abs(self._ewma - score) > self._ewma_k * sigma and self._n > 30

        # ── CUSUM ──
        x = score - self._ewma   # mean-corrected
        self._s_pos = max(0, self._s_pos + x - self._k)
        self._s_neg = max(0, self._s_neg - x - self._k)
        cusum_alarm = self._s_pos > self._h or self._s_neg > self._h

        if cusum_alarm:
            self._s_pos = self._s_neg = 0.0

        return ewma_alarm or cusum_alarm


# ──────────────────────────────────────────────────────────────────────────────
# Score Calibrator
# Keeps a rolling window of recent scores and converts raw scores to percentiles.
# This gives meaningful 0-1 normalization that adapts to the data distribution.
# ──────────────────────────────────────────────────────────────────────────────

class ScoreCalibrator:
    """
    Maintains a fixed-size deque of recent anomaly scores.
    `calibrate(score)` returns the percentile rank in [0, 1] — much more
    meaningful than a fixed sigmoid that can saturate at extremes.
    """

    def __init__(self, window: int = 5000):
        self._window = window
        self._buffer: deque = deque(maxlen=window)

    def update(self, score: float):
        self._buffer.append(score)

    def calibrate(self, score: float) -> float:
        if len(self._buffer) < 50:
            # Fall back to sigmoid until we have enough data
            return float(1.0 / (1.0 + np.exp(-(score - 1.0) * 2)))
        arr = np.array(self._buffer)
        return float(np.mean(arr <= score))


# ──────────────────────────────────────────────────────────────────────────────
# Temporal Context Tracker
# Tracks per-source rolling windows to detect burst patterns.
# ──────────────────────────────────────────────────────────────────────────────

class TemporalContextTracker:
    """
    Maintains per-source (IP / container / service) sliding windows of:
      - anomaly scores
      - event counts
      - failure counts

    Returns a "temporal boost" — an extra score addend when a source is
    exhibiting burst activity that individual events wouldn't reveal.
    """

    def __init__(self, window_seconds: float = 300.0):
        self._window = window_seconds
        # source_key → deque of (timestamp, score, is_failure)
        self._history: defaultdict = defaultdict(lambda: deque(maxlen=500))

    def _prune(self, dq: deque, now: float):
        while dq and now - dq[0][0] > self._window:
            dq.popleft()

    def update_and_score(
        self,
        source_key: str,
        score: float,
        is_failure: bool,
    ) -> float:
        """
        Record this event and return a temporal boost in [0, 0.5].
        Boost is higher when:
          - many anomalies from same source in the window
          - high failure rate from same source
        """
        now = time.time()
        dq = self._history[source_key]
        self._prune(dq, now)
        dq.append((now, score, is_failure))

        if len(dq) < 3:
            return 0.0

        scores = np.array([e[1] for e in dq])
        failures = np.array([e[2] for e in dq])

        # Mean anomaly score in window (weighted toward recent events)
        weights = np.linspace(0.5, 1.0, len(scores))
        weighted_mean = float(np.average(scores, weights=weights))

        # Failure burst ratio
        fail_ratio = float(failures.mean())

        # Burst count penalty: the more events in a short window, the higher the boost
        density_boost = min(len(dq) / 50.0, 0.3)   # caps at 0.3

        boost = 0.5 * (0.6 * weighted_mean + 0.4 * fail_ratio) + density_boost
        return float(np.clip(boost, 0.0, 0.50))


# ──────────────────────────────────────────────────────────────────────────────
# Bootstrap Data Generator — now includes injected anomaly patterns
# ──────────────────────────────────────────────────────────────────────────────

def _generate_bootstrap_data(n: int = 2000) -> np.ndarray:
    """
    Generates realistic normal-traffic bootstrap data PLUS a small fraction
    of synthetic anomalies (OOM patterns, brute-force bursts, 5xx storms).
    This gives the models a better initial decision boundary.
    """
    rng = np.random.default_rng(42)
    n_normal = int(n * 0.92)
    n_anomaly = n - n_normal

    # ── Normal traffic ──
    normal = np.column_stack([
        rng.integers(0, 6, n_normal).astype(float),          # source_type
        rng.uniform(0, 0.08, n_normal),                        # error_rate (low)
        rng.integers(1, 80, n_normal).astype(float),           # response_time_ms
        rng.choice([200, 200, 200, 301, 302, 304, 404], n_normal).astype(float),
        rng.integers(0, 2, n_normal).astype(float),
        rng.integers(0, 2, n_normal).astype(float),
        rng.integers(100, 3000, n_normal).astype(float),       # payload_size
        rng.uniform(-0.5, 0.5, n_normal),                      # anomaly_signal (near 0)
        rng.integers(1, 8, n_normal).astype(float),
        rng.integers(1, 40, n_normal).astype(float),
        rng.integers(0, 3, n_normal).astype(float),            # ip_fail_5m (low)
        rng.uniform(0, 0.08, n_normal),                        # ip_fail_ratio
        rng.integers(0, 2, n_normal).astype(float),
        rng.integers(1, 3, n_normal).astype(float),
        rng.integers(5, 150, n_normal).astype(float),
        rng.integers(10, 400, n_normal).astype(float),
        rng.uniform(0, 0.08, n_normal),
        rng.integers(0, 24, n_normal).astype(float),
        rng.integers(0, 7, n_normal).astype(float),
        rng.integers(0, 2, n_normal).astype(float),
        rng.uniform(2, 4.5, n_normal),
        rng.integers(0, 2, n_normal).astype(float),
        rng.integers(0, 2, n_normal).astype(float),
        rng.integers(0, 3, n_normal).astype(float),
        rng.integers(0, 2, n_normal).astype(float),
        rng.integers(0, 3, n_normal).astype(float),
    ])

    # ── Synthetic anomalies (brute force, OOM, 5xx storms) ──
    anomaly = np.column_stack([
        rng.integers(0, 6, n_anomaly).astype(float),
        rng.uniform(0.6, 1.0, n_anomaly),                     # high error_rate
        rng.integers(5000, 30000, n_anomaly).astype(float),   # very slow responses
        rng.choice([500, 502, 503], n_anomaly).astype(float), # 5xx status
        rng.integers(0, 2, n_anomaly).astype(float),
        rng.integers(0, 2, n_anomaly).astype(float),
        rng.integers(50000, 200000, n_anomaly).astype(float), # huge payload
        rng.uniform(3, 10, n_anomaly),                        # high anomaly signal
        rng.integers(1, 8, n_anomaly).astype(float),
        rng.integers(1, 40, n_anomaly).astype(float),
        rng.integers(20, 100, n_anomaly).astype(float),       # high ip_fail_5m
        rng.uniform(0.7, 1.0, n_anomaly),                     # high ip_fail_ratio
        rng.integers(0, 2, n_anomaly).astype(float),
        rng.integers(1, 3, n_anomaly).astype(float),
        rng.integers(5, 150, n_anomaly).astype(float),
        rng.integers(10, 400, n_anomaly).astype(float),
        rng.uniform(0.5, 1.0, n_anomaly),
        rng.integers(0, 24, n_anomaly).astype(float),
        rng.integers(0, 7, n_anomaly).astype(float),
        rng.integers(0, 2, n_anomaly).astype(float),
        rng.uniform(6, 12, n_anomaly),                        # elevated signal
        rng.integers(0, 2, n_anomaly).astype(float),
        rng.integers(0, 2, n_anomaly).astype(float),
        rng.integers(0, 5, n_anomaly).astype(float),
        rng.integers(0, 2, n_anomaly).astype(float),
        rng.integers(0, 3, n_anomaly).astype(float),
    ])

    return np.vstack([normal, anomaly])


# ──────────────────────────────────────────────────────────────────────────────
# Main Engine
# ──────────────────────────────────────────────────────────────────────────────

class SmartMLEngine:

    def __init__(self):
        self._if_model = None
        self._lof_model = None
        self._svm_model = None
        self._scaler = RobustScaler()   # Upgraded from StandardScaler

        self._training_buffer: list = []
        self._last_train: float = 0.0
        self._model_dir = getattr(settings, "ML_MODEL_DIR", "/app/models")

        self._if_path    = os.path.join(self._model_dir, "isolation_forest.pkl")
        self._lof_path   = os.path.join(self._model_dir, "lof.pkl")
        self._svm_path   = os.path.join(self._model_dir, "svm.pkl")
        self._scaler_path = os.path.join(self._model_dir, "scaler.pkl")
        self._weights_path = os.path.join(self._model_dir, "adaptive_weights.pkl")

        self.supervised = LogClassifier(self._model_dir)
        self.drift_detector  = EWMADriftDetector(k=0.5, h=5.0, ewma_lambda=0.1, ewma_k=3.0)
        self.calibrator      = ScoreCalibrator(window=5000)
        self.temporal        = TemporalContextTracker(window_seconds=300.0)
        self.weight_manager  = AdaptiveWeightManager()

        self._load_or_bootstrap()

    # ── Model persistence ────────────────────────────────────────────────────

    def _load_or_bootstrap(self):
        try:
            if os.path.exists(self._if_path):
                self._if_model  = joblib.load(self._if_path)
                self._lof_model = joblib.load(self._lof_path)
                self._svm_model = joblib.load(self._svm_path)
                self._scaler    = joblib.load(self._scaler_path)
                if os.path.exists(self._weights_path):
                    self.weight_manager = joblib.load(self._weights_path)
                logger.info("Loaded ensemble ML models from disk.")
                return
        except Exception as exc:
            logger.warning("Failed to load models, bootstrapping: %s", exc)

        self._train(_generate_bootstrap_data())

    def _train(self, X: np.ndarray):
        os.makedirs(self._model_dir, exist_ok=True)

        self._scaler.fit(X)
        X_scaled = self._scaler.transform(X)

        # 1. Isolation Forest
        self._if_model = IsolationForest(
            n_estimators=400,
            contamination=0.05,          # explicit — "auto" was too permissive
            max_samples="auto",
            max_features=0.8,
            random_state=42,
            n_jobs=-1,
        )
        self._if_model.fit(X_scaled)

        # 2. LOF
        self._lof_model = LocalOutlierFactor(
            n_neighbors=30,
            contamination=0.05,
            novelty=True,
            n_jobs=-1,
        )
        self._lof_model.fit(X_scaled)

        # 3. OC-SVM — only on subset because it's slow on large data
        n_svm = min(len(X_scaled), 3000)
        idx = np.random.default_rng(42).choice(len(X_scaled), n_svm, replace=False)
        self._svm_model = OneClassSVM(kernel="rbf", nu=0.05, gamma="scale")
        self._svm_model.fit(X_scaled[idx])

        self._last_train = time.time()

        try:
            joblib.dump(self._if_model,      self._if_path)
            joblib.dump(self._lof_model,     self._lof_path)
            joblib.dump(self._svm_model,     self._svm_path)
            joblib.dump(self._scaler,        self._scaler_path)
            joblib.dump(self.weight_manager, self._weights_path)
            logger.info("Models trained and saved to %s", self._model_dir)
        except Exception as exc:
            logger.warning("Could not save ML models: %s", exc)

    # ── Training buffer ──────────────────────────────────────────────────────

    def add_to_buffer(self, features: list[float]):
        self._training_buffer.append(features)

    def maybe_retrain(self):
        elapsed_h = (time.time() - self._last_train) / 3600
        has_enough = len(self._training_buffer) >= 500
        if elapsed_h >= settings.ML_RETRAIN_INTERVAL_HOURS and has_enough:
            logger.info("Retraining ML models with %d samples.", len(self._training_buffer))
            X_new   = np.array(self._training_buffer[-10_000:])
            X_boot  = _generate_bootstrap_data(500)
            X       = np.vstack([X_boot, X_new])
            self._train(X)
            self._training_buffer.clear()

    # ── Model agreement voter ────────────────────────────────────────────────

    @staticmethod
    def _compute_agreement(scores: list[float]) -> float:
        """
        Returns 1.0 if all models agree (low variance), 0.0 if they strongly disagree.
        High disagreement → lower final confidence.
        """
        arr = np.array(scores)
        std = float(np.std(arr))
        # std of 0 → perfect agreement=1; std of 2 → agreement≈0
        return float(np.exp(-std))

    # ── Main predict ─────────────────────────────────────────────────────────

    def predict(
        self,
        features: list[float],
        message: str = "",
        source_key: str = "default",
    ) -> MLResult:

        if self._if_model is None:
            return MLResult(0.0, False, 0.0, 0.0, 0.0, "information", 0.0, 0.0, False, 1.0, 0.0, 0.0)

        X = np.array(features, dtype=float).reshape(1, -1)
        X_scaled = self._scaler.transform(X)

        # ── Raw sub-model scores ─────────────────────────────────────────────
        if_score  = float(-self._if_model.score_samples(X_scaled)[0])
        lof_score = float(-self._lof_model.score_samples(X_scaled)[0])

        source_idx = features[0]
        svm_active = source_idx in (0, 4, 5)
        svm_score  = float(-self._svm_model.score_samples(X_scaled)[0]) if svm_active else 0.0

        # ── Adaptive ensemble weighting ──────────────────────────────────────
        w = self.weight_manager.get_weights(svm_active)
        raw_scores = [if_score, lof_score, svm_score]
        final_raw = float(
            w[0] * if_score
            + w[1] * lof_score
            + w[2] * svm_score
        )

        # ── Model agreement ──────────────────────────────────────────────────
        active_scores = [if_score, lof_score] + ([svm_score] if svm_active else [])
        agreement = self._compute_agreement(active_scores)

        # ── Drift detection ──────────────────────────────────────────────────
        drift = self.drift_detector.update(final_raw)
        if drift and len(self._training_buffer) >= 200:
            logger.info("Drift detected — triggering retrain check.")
            self.maybe_retrain()

        # ── Calibrated percentile normalization ─────────────────────────────
        self.calibrator.update(final_raw)
        calibrated = self.calibrator.calibrate(final_raw)

        # Blend calibrated percentile with agreement penalty
        # Low agreement → less confident the score is meaningful
        norm_score = calibrated * (0.7 + 0.3 * agreement)

        # ── Temporal burst boost ─────────────────────────────────────────────
        ip_fail_5m    = features[10]
        ip_fail_ratio = features[11]
        is_failure    = ip_fail_5m > 0 or ip_fail_ratio > 0.3

        temporal_boost = self.temporal.update_and_score(source_key, norm_score, is_failure)

        # Apply boost (capped so it can't dominate alone)
        boosted_score = float(np.clip(norm_score + 0.4 * temporal_boost, 0.0, 1.0))

        # ── Supervised classification ────────────────────────────────────────
        sup_result = self.supervised.predict(message)
        sup_sev    = sup_result["top_severity"]
        sup_conf   = sup_result["confidence"]

        # ── Anomaly decision ─────────────────────────────────────────────────
        is_anomaly = boosted_score > 0.70

        # Hard brute-force override (structural, independent of ML)
        if ip_fail_5m > 15 and ip_fail_ratio > 0.8:
            sup_sev    = "disaster"
            sup_conf   = 0.99
            is_anomaly = True
            boosted_score = 1.0

        # Supervised text consensus dampening
        if sup_sev == "information":
            if sup_conf > 0.60:
                is_anomaly    = False
                boosted_score = boosted_score * 0.5
            elif sup_conf > 0.40:
                is_anomaly    = boosted_score > 0.95
                boosted_score = boosted_score * 0.8

        # Final confidence: blend of score + supervised confidence + agreement
        confidence = float(np.clip(
            0.5 * boosted_score + 0.35 * sup_conf + 0.15 * agreement,
            0.0, 1.0
        ))

        return MLResult(
            score                = round(boosted_score, 4),
            is_anomaly           = is_anomaly,
            if_score             = round(if_score, 4),
            lof_score            = round(lof_score, 4),
            svm_score            = round(svm_score, 4),
            supervised_sev       = sup_sev,
            supervised_conf      = round(sup_conf, 4),
            confidence           = round(confidence, 4),
            drift_detected       = drift,
            model_agreement      = round(agreement, 4),
            temporal_boost       = round(temporal_boost, 4),
            calibrated_percentile = round(calibrated, 4),
        )

    # ── Analyst feedback loop ─────────────────────────────────────────────────
    # Call this when a human analyst marks a prediction correct / incorrect.
    # It updates the adaptive weights so the best model gains influence over time.

    def record_analyst_feedback(self, model_idx: int, was_correct: bool):
        """
        model_idx: 0=IsolationForest, 1=LOF, 2=SVM
        was_correct: did that model's output match the analyst verdict?
        """
        self.weight_manager.record_feedback(model_idx, was_correct)
        # Persist updated weights immediately
        try:
            joblib.dump(self.weight_manager, self._weights_path)
        except Exception as exc:
            logger.warning("Could not persist adaptive weights: %s", exc)


# ── Singleton ─────────────────────────────────────────────────────────────────

_engine: Optional[SmartMLEngine] = None

def get_smart_ml_engine() -> SmartMLEngine:
    global _engine
    if _engine is None:
        _engine = SmartMLEngine()
    return _engine