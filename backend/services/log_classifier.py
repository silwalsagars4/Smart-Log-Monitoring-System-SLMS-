"""
Supervised Log Classifier.
Uses TF-IDF + SGD (Logistic Regression) for fast incremental text classification.
"""

import os
import logging
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)

# Severity mapping for internal ML labels
# 0: Information, 1: Warning, 2: High, 3: Disaster
SEV_MAP = {
    "information": 0,
    "warning": 1,
    "high": 2,
    "disaster": 3
}
INV_MAP = {v: k for k, v in SEV_MAP.items()}

class LogClassifier:
    def __init__(self, model_dir: str):
        self.model_dir = model_dir
        self.pipeline_path = os.path.join(model_dir, "supervised_pipeline.pkl")
        self._pipeline = None
        self._is_trained = False
        
        self._load_or_init()

    def _load_or_init(self):
        try:
            if os.path.exists(self.pipeline_path):
                self._pipeline = joblib.load(self.pipeline_path)
                self._is_trained = True
                logger.info("Loaded supervised log classifier")
                return
        except Exception as exc:
            logger.warning("Failed to load supervised model: %s", exc)

        # Initialize fresh pipeline
        self._pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                ngram_range=(1, 3), 
                max_features=5000,
                stop_words='english',
                lowercase=True
            )),
            ('clf', SGDClassifier(
                loss='log_loss',  # provides probabilities
                penalty='l2',
                alpha=1e-4,
                random_state=42,
                max_iter=1000,
                tol=1e-3
            ))
        ])
        
        # Bootstrap training
        self._bootstrap()

    def _bootstrap(self):
        """Pre-train with common patterns to avoid zero-start."""
        data = [
            ("GET /index.html 200", "information"),
            ("healthcheck ok", "information"),
            ("Connection accepted from 127.0.0.1", "information"),
            ("User logged in successfully", "information"),
            ("File uploaded: image.png", "information"),
            
            ("connection timeout", "warning"),
            ("deprecated api used", "warning"),
            ("slow query detected", "warning"),
            ("disk usage at 80%", "warning"),
            ("retry attempt 3", "warning"),
            
            ("Failed password for admin", "high"),
            ("Access denied for user 'dbadmin'", "high"),
            ("404 Not Found for /admin/config", "high"),
            ("Segmentation fault in process", "high"),
            ("Uncaught exception in app.py", "high"),
            
            ("Failed password for root", "disaster"),
            ("OOMKilled: container died", "disaster"),
            ("Kernel panic - not syncing", "disaster"),
            ("No space left on device", "disaster"),
            ("Database corruption detected", "disaster"),
            ("Filesystem read-only", "disaster"),
            ("service stopped", "disaster"),
            ("server restarted", "disaster"),
        ]

        
        X = [d[0] for d in data]
        y = [SEV_MAP[d[1]] for d in data]
        
        # We need at least one of each class for some models, 
        # but SGD with partial_fit or fit works fine here.
        self._pipeline.fit(X, y)
        self._is_trained = True
        self.save()
        logger.info("Supervised model bootstrapped with %d samples", len(data))

    def save(self):
        try:
            os.makedirs(self.model_dir, exist_ok=True)
            joblib.dump(self._pipeline, self.pipeline_path)
        except Exception as exc:
            logger.error("Could not save supervised model: %s", exc)

    def predict(self, message: str) -> dict:
        """Returns probabilities for each severity level."""
        if not self._is_trained:
            return {sev: 0.0 for sev in SEV_MAP}
            
        probs = self._pipeline.predict_proba([message])[0]
        result = {}
        for i, prob in enumerate(probs):
            label = INV_MAP.get(i, "unknown")
            result[label] = float(prob)
            
        # Get top prediction
        top_idx = np.argmax(probs)
        result["top_severity"] = INV_MAP[top_idx]
        result["confidence"] = float(probs[top_idx])
        
        return result

    def partial_fit(self, messages: list[str], labels: list[str]):
        """Incremental learning."""
        if not messages:
            return
            
        y = [SEV_MAP.get(l, 0) for l in labels]
        
        # SGDClassifier supports partial_fit, but Pipeline doesn't directly
        # for all steps. We'll just use fit for now as the dataset is small,
        # or we could re-fit on a larger buffer.
        # For simplicity in this version, we'll re-fit on the combined set if buffer is large.
        self._pipeline.fit(messages, y)
        self._is_trained = True
        self.save()
