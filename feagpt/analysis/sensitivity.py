"""
Parameter sensitivity analysis module for FeaGPT.

Implements correlation-based sensitivity analysis to rank
parameter influence on performance metrics.
Reference: Saltelli et al., Global Sensitivity Analysis (2008)
"""
import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class SensitivityResult:
    """Container for sensitivity analysis results."""
    parameter_name: str
    metric_name: str
    pearson_r: float
    pearson_p: float
    spearman_rho: float
    spearman_p: float
    rank: int = 0

    @property
    def is_significant(self) -> bool:
        """Check if correlation is statistically significant (p < 0.05)."""
        return self.pearson_p < 0.05

    @property
    def strength(self) -> str:
        """Categorize correlation strength."""
        r = abs(self.pearson_r)
        if r > 0.7:
            return "strong"
        elif r > 0.4:
            return "moderate"
        elif r > 0.2:
            return "weak"
        return "negligible"


class SensitivityAnalyzer:
    """
    Sensitivity analyzer for FEA parameter studies.

    Computes Pearson and Spearman correlations between
    design parameters and output metrics.
    """

    def __init__(self):
        self.results: List[SensitivityResult] = []

    def analyze(
        self,
        parameters: Dict[str, List[float]],
        metrics: Dict[str, List[float]],
    ) -> List[SensitivityResult]:
        """
        Run sensitivity analysis.

        Args:
            parameters: Dict mapping param names to value lists
            metrics: Dict mapping metric names to value lists

        Returns:
            List of SensitivityResult sorted by influence
        """
        self.results = []

        for param_name, param_values in parameters.items():
            param_arr = np.array(param_values)
            for metric_name, metric_values in metrics.items():
                metric_arr = np.array(metric_values)

                if len(param_arr) != len(metric_arr):
                    logger.warning(
                        f"Length mismatch: {param_name} ({len(param_arr)}) "
                        f"vs {metric_name} ({len(metric_arr)})"
                    )
                    continue

                if np.std(param_arr) == 0 or np.std(metric_arr) == 0:
                    pr, pp = 0.0, 1.0
                    sr, sp = 0.0, 1.0
                else:
                    pr, pp = stats.pearsonr(param_arr, metric_arr)
                    sr, sp = stats.spearmanr(param_arr, metric_arr)

                self.results.append(SensitivityResult(
                    parameter_name=param_name,
                    metric_name=metric_name,
                    pearson_r=float(pr),
                    pearson_p=float(pp),
                    spearman_rho=float(sr),
                    spearman_p=float(sp),
                ))

        # Rank by absolute Pearson correlation
        self.results.sort(key=lambda r: abs(r.pearson_r), reverse=True)
        for i, result in enumerate(self.results):
            result.rank = i + 1

        return self.results

    def get_top_parameters(
        self,
        metric_name: str,
        n: int = 5,
    ) -> List[SensitivityResult]:
        """Get top N most influential parameters for a metric."""
        filtered = [
            r for r in self.results
            if r.metric_name == metric_name
        ]
        filtered.sort(key=lambda r: abs(r.pearson_r), reverse=True)
        return filtered[:n]

    def to_dataframe(self) -> pd.DataFrame:
        """Convert results to a pandas DataFrame."""
        records = []
        for r in self.results:
            records.append({
                "parameter": r.parameter_name,
                "metric": r.metric_name,
                "pearson_r": r.pearson_r,
                "pearson_p": r.pearson_p,
                "spearman_rho": r.spearman_rho,
                "spearman_p": r.spearman_p,
                "rank": r.rank,
                "strength": r.strength,
                "significant": r.is_significant,
            })
        return pd.DataFrame(records)
