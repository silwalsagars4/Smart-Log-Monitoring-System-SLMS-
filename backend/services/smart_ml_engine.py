"""
Smart ML Engine — ensemble anomaly detection.
Features IsolationForest + LOF + OC-SVM and CUSUM drift detection.
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

from services.log_classifier import LogClassifier

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

class CUSUMDriftDetector:
    # ... (existing code remains same)
    def __init__(self, k=0.5, h=5.0):
        self.k = k
        self.h = h
        self._s_pos = 0.0
        self._s_neg = 0.0
        self._mean = None

    def update(self, score: float) -> bool:
        if self._mean is None:
            self._mean = score
            return False
        x = score - self._mean
        self._s_pos = max(0, self._s_pos + x - self.k)
        self._s_neg = max(0, self._s_neg - x - self.k)
        if self._s_pos > self.h or self._s_neg > self.h:
            self._s_pos = self._s_neg = 0.0
            return True
        return False

def _generate_bootstrap_data(n: int = 2000) -> np.ndarray:
    # ... (existing code remains same)
    rng = np.random.default_rng(42)
    return np.column_stack([
        rng.integers(0, 6, n).astype(float),
        rng.uniform(0, 0.1, n),
        rng.integers(1, 100, n).astype(float),
        rng.choice([200, 200, 200, 301, 302, 304, 404], n).astype(float),
        rng.integers(0, 2, n).astype(float),
        rng.integers(0, 2, n).astype(float),
        rng.integers(100, 5000, n).astype(float),
        rng.uniform(-1, 1, n),
        rng.integers(1, 10, n).astype(float),
        rng.integers(1, 50, n).astype(float),
        rng.integers(0, 2, n).astype(float),
        rng.uniform(0, 0.1, n),
        rng.integers(0, 2, n).astype(float),
        rng.integers(1, 3, n).astype(float),
        rng.integers(5, 200, n).astype(float),
        rng.integers(10, 500, n).astype(float),
        rng.uniform(0, 0.1, n),
        rng.integers(0, 24, n).astype(float),
        rng.integers(0, 7, n).astype(float),
        rng.integers(0, 2, n).astype(float),
        rng.uniform(2, 5, n),
        rng.integers(0, 2, n).astype(float),
        rng.integers(0, 2, n).astype(float),
        rng.integers(0, 5, n).astype(float),
        rng.integers(0, 2, n).astype(float),
        rng.integers(0, 3, n).astype(float),
    ])

class SmartMLEngine:
    def __init__(self):
        self._if_model = None
        self._lof_model = None
        self._svm_model = None
        self._scaler = StandardScaler()
        
        self._training_buffer = []
        self._last_train = 0
        self._model_dir = getattr(settings, "ML_MODEL_DIR", "/app/models")
        self._if_path = os.path.join(self._model_dir, "isolation_forest.pkl")
        self._lof_path = os.path.join(self._model_dir, "lof.pkl")
        self._svm_path = os.path.join(self._model_dir, "svm.pkl")
        self._scaler_path = os.path.join(self._model_dir, "scaler.pkl")
        
        self.supervised = LogClassifier(self._model_dir)
        self.drift_detector = CUSUMDriftDetector(k=0.5, h=5.0)
        self._load_or_bootstrap()

    def _load_or_bootstrap(self):
        try:
            if os.path.exists(self._if_path):
                self._if_model = joblib.load(self._if_path)
                self._lof_model = joblib.load(self._lof_path)
                self._svm_model = joblib.load(self._svm_path)
                self._scaler = joblib.load(self._scaler_path)
                logger.info("Loaded ensemble ML models")
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
            contamination="auto",
            max_samples="auto",
            max_features=0.8,
            random_state=42,
            n_jobs=-1,
        )
        self._if_model.fit(X_scaled)
        
        # 2. LOF
        self._lof_model = LocalOutlierFactor(
            n_neighbors=30,
            contamination="auto",
            novelty=True,
            n_jobs=-1,
        )
        self._lof_model.fit(X_scaled)
        
        # 3. SVM
        self._svm_model = OneClassSVM(
            kernel="rbf",
            nu=0.05,
            gamma="scale"
        )
        self._svm_model.fit(X_scaled)
        
        self._last_train = time.time()
        
        try:
            joblib.dump(self._if_model, self._if_path)
            joblib.dump(self._lof_model, self._lof_path)
            joblib.dump(self._svm_model, self._svm_path)
            joblib.dump(self._scaler, self._scaler_path)
            logger.info("Models trained and saved.")
        except Exception as exc:
            logger.warning("Could not save ML models: %s", exc)

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

    def predict(self, features: list[float], message: str = "") -> MLResult:
        if self._if_model is None:
            return MLResult(0.0, False, 0.0, 0.0, 0.0, "information", 0.0, 0.0, False)
            
        X = np.array(features).reshape(1, -1)
        X_scaled = self._scaler.transform(X)
        
        if_score = float(-self._if_model.score_samples(X_scaled)[0])
        lof_score = float(-self._lof_model.score_samples(X_scaled)[0])
        
        source_idx = features[0]
        svm_score = 0.0
        if source_idx in (0, 4, 5):
            svm_score = float(-self._svm_model.score_samples(X_scaled)[0])
            
        weights = [0.55, 0.30, 0.15]
        if svm_score == 0.0:
            weights = [0.70, 0.30, 0.0]
            
        final_anomaly_score = (weights[0] * if_score) + (weights[1] * lof_score) + (weights[2] * svm_score)
        
        drift = self.drift_detector.update(final_anomaly_score)
        if drift and len(self._training_buffer) >= 200:
            self.maybe_retrain()
            
        # 1. Improved Normalization: Use a Sigmoid-like scaling for anomaly scores
        # LOF scores > 1.5 are usually anomalies, but we want to map them smoothly.
        # IF scores > 0.5 are usually anomalies.
        # We'll use a modified tanh or sigmoid to keep scores in [0, 1] without pegging 1.0 too early.
        norm_score = float(1.0 / (1.0 + np.exp(-(final_anomaly_score - 1.0) * 2)))
        
        # Supervised Classification
        sup_result = self.supervised.predict(message)
        sup_sev = sup_result["top_severity"]
        sup_conf = sup_result["confidence"]
        
        # 2. Consensus: Deduct Information from Anomaly
        # If it's information, it shouldn't be an anomaly even if structurally new.
        is_anomaly = norm_score > 0.70
        
        # 3. Brute Force Detection (Structural)
        # features[10] is ip_fail_5m. If > 15 failures from same IP, upgrade to Disaster.
        ip_fail_5m = features[10]
        ip_fail_ratio = features[11]
        
        if ip_fail_5m > 15 and ip_fail_ratio > 0.8:
            sup_sev = "disaster"
            sup_conf = 0.99
            is_anomaly = True
            norm_score = 1.0 # Force max score for brute force
        
        if sup_sev == "information":
            if sup_conf > 0.60:
                is_anomaly = False # Force false for likely info
                norm_score *= 0.5   # Dampen score
            elif sup_conf > 0.40:
                is_anomaly = norm_score > 0.95 # very high bar
                norm_score *= 0.8

        
        return MLResult(
            score=round(norm_score, 4),
            is_anomaly=is_anomaly,
            if_score=round(if_score, 4),
            lof_score=round(lof_score, 4),
            svm_score=round(svm_score, 4),
            supervised_sev=sup_sev,
            supervised_conf=round(sup_conf, 4),
            confidence=round(max(norm_score, sup_conf), 4),
            drift_detected=drift
        )



# Singleton
_engine: Optional[SmartMLEngine] = None

def get_smart_ml_engine() -> SmartMLEngine:
    global _engine
    if _engine is None:
        _engine = SmartMLEngine()
    return _engine
