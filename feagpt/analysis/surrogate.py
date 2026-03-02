"""
Surrogate modeling module for FeaGPT.

Builds lightweight surrogate models from FEA results
for rapid design space interpolation and prediction.

References:
    Rasmussen & Williams, Gaussian Processes for ML (MIT Press, 2006)
    Pedregosa et al., JMLR 12, 2825 (2011)
"""
import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SurrogateMetrics:
    """Surrogate model quality metrics."""
    model_type: str
    r2_score: float
    rmse: float
    max_error: float
    cv_r2_mean: float = 0.0
    cv_r2_std: float = 0.0
    n_training: int = 0
    n_features: int = 0


class SurrogateModeler:
    """
    Surrogate model builder for FEA design space interpolation.

    Supports GPR, Random Forest, and Polynomial regression.
    Auto-selects best model via cross-validation.
    """

    def __init__(self, model_type: str = "auto"):
        self.model_type = model_type
        self.model = None
        self.scaler_x = None
        self.scaler_y = None
        self.metrics: Optional[SurrogateMetrics] = None
        self.feature_names: List[str] = []

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[List[str]] = None,
    ) -> SurrogateMetrics:
        """
        Fit surrogate model to training data.

        Args:
            X: Feature matrix (n_samples, n_features)
            y: Target values (n_samples,)
            feature_names: Optional names for features

        Returns:
            SurrogateMetrics with model quality info
        """
        from sklearn.preprocessing import StandardScaler
        from sklearn.model_selection import cross_val_score

        self.feature_names = feature_names or [
            f"x{i}" for i in range(X.shape[1])
        ]

        # Scale inputs
        self.scaler_x = StandardScaler()
        self.scaler_y = StandardScaler()
        X_scaled = self.scaler_x.fit_transform(X)
        y_scaled = self.scaler_y.fit_transform(
            y.reshape(-1, 1)
        ).ravel()

        # Select model
        if self.model_type == "auto":
            self.model = self._auto_select(X_scaled, y_scaled)
        else:
            self.model = self._create_model(self.model_type)
            self.model.fit(X_scaled, y_scaled)

        # Cross-validation
        cv_scores = cross_val_score(
            self.model, X_scaled, y_scaled,
            cv=min(5, len(X)), scoring="r2"
        )

        # Compute metrics
        y_pred_scaled = self.model.predict(X_scaled)
        y_pred = self.scaler_y.inverse_transform(
            y_pred_scaled.reshape(-1, 1)
        ).ravel()

        residuals = y - y_pred
        self.metrics = SurrogateMetrics(
            model_type=type(self.model).__name__,
            r2_score=float(1 - np.sum(residuals**2) / np.sum(
                (y - np.mean(y))**2
            )),
            rmse=float(np.sqrt(np.mean(residuals**2))),
            max_error=float(np.max(np.abs(residuals))),
            cv_r2_mean=float(np.mean(cv_scores)),
            cv_r2_std=float(np.std(cv_scores)),
            n_training=len(X),
            n_features=X.shape[1],
        )

        logger.info(
            f"Surrogate fit: {self.metrics.model_type} "
            f"R2={self.metrics.r2_score:.4f} "
            f"CV={self.metrics.cv_r2_mean:.4f}"
        )
        return self.metrics

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict using fitted surrogate model."""
        if self.model is None:
            raise RuntimeError("Model not fitted. Call fit() first.")
        X_scaled = self.scaler_x.transform(X)
        y_scaled = self.model.predict(X_scaled)
        return self.scaler_y.inverse_transform(
            y_scaled.reshape(-1, 1)
        ).ravel()

    def _auto_select(
        self, X: np.ndarray, y: np.ndarray
    ):
        """Auto-select best model via cross-validation."""
        from sklearn.model_selection import cross_val_score

        candidates = {
            "rf": self._create_model("rf"),
            "poly": self._create_model("poly"),
        }

        # Add GPR only for small datasets
        if len(X) < 500:
            candidates["gpr"] = self._create_model("gpr")

        best_name = None
        best_score = -np.inf
        best_model = None

        for name, model in candidates.items():
            try:
                scores = cross_val_score(
                    model, X, y,
                    cv=min(5, len(X)), scoring="r2"
                )
                mean_score = np.mean(scores)
                logger.info(f"  {name}: CV R2 = {mean_score:.4f}")
                if mean_score > best_score:
                    best_score = mean_score
                    best_name = name
                    best_model = model
            except Exception as e:
                logger.warning(f"  {name} failed: {e}")

        logger.info(f"Selected: {best_name} (R2={best_score:.4f})")
        best_model.fit(X, y)
        return best_model

    def _create_model(self, model_type: str):
        """Create a model instance by type string."""
        if model_type == "rf":
            from sklearn.ensemble import RandomForestRegressor
            return RandomForestRegressor(
                n_estimators=100, random_state=42
            )
        elif model_type == "gpr":
            from sklearn.gaussian_process import (
                GaussianProcessRegressor
            )
            from sklearn.gaussian_process.kernels import (
                RBF, ConstantKernel
            )
            kernel = ConstantKernel() * RBF()
            return GaussianProcessRegressor(
                kernel=kernel, random_state=42
            )
        elif model_type == "poly":
            from sklearn.pipeline import make_pipeline
            from sklearn.preprocessing import PolynomialFeatures
            from sklearn.linear_model import Ridge
            return make_pipeline(
                PolynomialFeatures(degree=2),
                Ridge(alpha=1.0),
            )
        else:
            raise ValueError(f"Unknown model type: {model_type}")
