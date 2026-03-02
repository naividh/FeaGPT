"""
Multi-Objective Pareto Front Optimization for FeaGPT.
Identifies non-dominated solutions from parametric study results.
"""
import numpy as np
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


def is_dominated(point_a, point_b, minimize=True):
    """Check if point_a is dominated by point_b."""
    if minimize:
        return all(b <= a for a, b in zip(point_a, point_b)) and any(b < a for a, b in zip(point_a, point_b))
    return all(b >= a for a, b in zip(point_a, point_b)) and any(b > a for a, b in zip(point_a, point_b))


def find_pareto_front(objectives, minimize=None):
    """
    Find Pareto-optimal solutions via non-dominated sorting.
    Args:
        objectives: numpy array of shape (n_points, n_objectives)
        minimize: list of bool per objective (True=minimize, False=maximize).
                  Default: all minimized.
    Returns:
        List of indices of Pareto-optimal solutions.
    """
    objectives = np.array(objectives)
    n_points = objectives.shape[0]
    n_obj = objectives.shape[1]
    if minimize is None:
        minimize = [True] * n_obj
    # Flip objectives that should be maximized
    adjusted = objectives.copy()
    for j in range(n_obj):
        if not minimize[j]:
            adjusted[:, j] = -adjusted[:, j]
    pareto_mask = np.ones(n_points, dtype=bool)
    for i in range(n_points):
        if not pareto_mask[i]:
            continue
        for j in range(n_points):
            if i == j or not pareto_mask[j]:
                continue
            if all(adjusted[j, k] <= adjusted[i, k] for k in range(n_obj)) and \
               any(adjusted[j, k] < adjusted[i, k] for k in range(n_obj)):
                pareto_mask[i] = False
                break
    return list(np.where(pareto_mask)[0])


def crowding_distance(objectives, pareto_indices):
    """
    Compute crowding distance for Pareto front solutions.
    Larger distance = more isolated = more diverse.
    """
    objectives = np.array(objectives)
    front = objectives[pareto_indices]
    n_points = len(pareto_indices)
    n_obj = front.shape[1]
    if n_points <= 2:
        return [float("inf")] * n_points
    distances = np.zeros(n_points)
    for j in range(n_obj):
        sorted_idx = np.argsort(front[:, j])
        distances[sorted_idx[0]] = float("inf")
        distances[sorted_idx[-1]] = float("inf")
        obj_range = front[sorted_idx[-1], j] - front[sorted_idx[0], j]
        if obj_range < 1e-12:
            continue
        for k in range(1, n_points - 1):
            distances[sorted_idx[k]] += (
                front[sorted_idx[k + 1], j] - front[sorted_idx[k - 1], j]
            ) / obj_range
    return distances.tolist()


def find_balanced_solution(objectives, pareto_indices, weights=None):
    """
    Find the balanced (utopia-closest) solution on the Pareto front.
    Uses normalized Euclidean distance to utopia point.
    """
    objectives = np.array(objectives)
    front = objectives[pareto_indices]
    n_obj = front.shape[1]
    if weights is None:
        weights = np.ones(n_obj) / n_obj
    else:
        weights = np.array(weights)
    # Normalize each objective to [0, 1]
    mins = front.min(axis=0)
    maxs = front.max(axis=0)
    ranges = maxs - mins
    ranges[ranges < 1e-12] = 1.0
    normalized = (front - mins) / ranges
    # Utopia point is [0, 0, ...] after normalization
    distances = np.sqrt(np.sum(weights * normalized ** 2, axis=1))
    best_idx = np.argmin(distances)
    return pareto_indices[best_idx]


class ParetoAnalyzer:
    """Multi-objective Pareto optimization for FEA parametric studies."""

    def __init__(self):
        self.objectives_data = None
        self.pareto_indices = []
        self.crowding = []

    def analyze(self, objectives, objective_names=None, minimize=None):
        """
        Run full Pareto analysis on parametric study results.
        Args:
            objectives: array of shape (n_configs, n_objectives)
            objective_names: list of objective names
            minimize: list of bool per objective
        Returns:
            Dict with pareto_indices, balanced_solution, crowding, summary
        """
        objectives = np.array(objectives)
        n_configs, n_obj = objectives.shape
        if objective_names is None:
            objective_names = [f"obj_{i}" for i in range(n_obj)]
        self.objectives_data = objectives
        self.pareto_indices = find_pareto_front(objectives, minimize)
        self.crowding = crowding_distance(objectives, self.pareto_indices)
        balanced_idx = find_balanced_solution(objectives, self.pareto_indices)
        pareto_values = objectives[self.pareto_indices]
        return {
            "total_configs": n_configs,
            "pareto_count": len(self.pareto_indices),
            "pareto_pct": 100 * len(self.pareto_indices) / max(n_configs, 1),
            "pareto_indices": self.pareto_indices,
            "balanced_solution_index": balanced_idx,
            "balanced_solution_values": objectives[balanced_idx].tolist(),
            "pareto_range": {
                name: {"min": float(pareto_values[:, i].min()),
                       "max": float(pareto_values[:, i].max())}
                for i, name in enumerate(objective_names)
            },
            "crowding_distances": self.crowding,
        }
