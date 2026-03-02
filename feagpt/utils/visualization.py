"""Result visualization utilities for FeaGPT."""
import logging
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.tri as tri
    import numpy as np
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    logger.warning("matplotlib not installed. Visualization disabled.")


class FEAVisualizer:
    """Visualization of FEA results including stress fields, deformations, and analysis plots."""

    def __init__(self, output_dir: str = "results", dpi: int = 300, fmt: str = "png"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.dpi = dpi
        self.fmt = fmt

    def plot_stress_field(self, nodes: np.ndarray, elements: np.ndarray,
                          stress: np.ndarray, title: str = "Von Mises Stress",
                          filename: str = "stress_field") -> Optional[str]:
        """Plot 2D stress contour from FEA results."""
        if not HAS_MPL:
            logger.warning("Cannot plot: matplotlib not available")
            return None

        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        x, y = nodes[:, 0], nodes[:, 1]

        # Create triangulation from element connectivity
        if elements.shape[1] >= 3:
            triang = tri.Triangulation(x, y, elements[:, :3])
            tcf = ax.tricontourf(triang, stress, levels=20, cmap='jet')
            ax.tricontour(triang, stress, levels=20, colors='k', linewidths=0.3, alpha=0.3)
            plt.colorbar(tcf, ax=ax, label='Stress [MPa]', shrink=0.8)

        ax.set_xlabel('X [mm]')
        ax.set_ylabel('Y [mm]')
        ax.set_title(title)
        ax.set_aspect('equal')

        path = self.output_dir / f"{filename}.{self.fmt}"
        fig.savefig(path, dpi=self.dpi, bbox_inches='tight')
        plt.close(fig)
        logger.info(f"Stress field saved to {path}")
        return str(path)

    def plot_deformation(self, nodes: np.ndarray, displacements: np.ndarray,
                         scale: float = 10.0, title: str = "Deformed Shape",
                         filename: str = "deformation") -> Optional[str]:
        """Plot original and deformed shape overlay."""
        if not HAS_MPL:
            return None

        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        x, y = nodes[:, 0], nodes[:, 1]
        dx, dy = displacements[:, 0], displacements[:, 1]

        ax.scatter(x, y, c='blue', s=1, alpha=0.3, label='Original')
        ax.scatter(x + scale * dx, y + scale * dy, c='red', s=1, alpha=0.5,
                   label=f'Deformed ({scale}x)')

        ax.set_xlabel('X [mm]')
        ax.set_ylabel('Y [mm]')
        ax.set_title(title)
        ax.set_aspect('equal')
        ax.legend()

        path = self.output_dir / f"{filename}.{self.fmt}"
        fig.savefig(path, dpi=self.dpi, bbox_inches='tight')
        plt.close(fig)
        logger.info(f"Deformation plot saved to {path}")
        return str(path)

    def plot_convergence(self, iterations: List[int], residuals: List[float],
                         title: str = "Solver Convergence",
                         filename: str = "convergence") -> Optional[str]:
        """Plot solver convergence history."""
        if not HAS_MPL:
            return None

        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        ax.semilogy(iterations, residuals, 'b-o', markersize=4)
        ax.set_xlabel('Iteration')
        ax.set_ylabel('Residual')
        ax.set_title(title)
        ax.grid(True, alpha=0.3)

        path = self.output_dir / f"{filename}.{self.fmt}"
        fig.savefig(path, dpi=self.dpi, bbox_inches='tight')
        plt.close(fig)
        return str(path)

    def plot_mesh(self, nodes: np.ndarray, elements: np.ndarray,
                  title: str = "Finite Element Mesh",
                  filename: str = "mesh") -> Optional[str]:
        """Plot the finite element mesh wireframe."""
        if not HAS_MPL:
            return None

        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        x, y = nodes[:, 0], nodes[:, 1]

        if elements.shape[1] >= 3:
            triang = tri.Triangulation(x, y, elements[:, :3])
            ax.triplot(triang, 'k-', linewidth=0.3, alpha=0.5)

        ax.set_xlabel('X [mm]')
        ax.set_ylabel('Y [mm]')
        ax.set_title(title)
        ax.set_aspect('equal')

        path = self.output_dir / f"{filename}.{self.fmt}"
        fig.savefig(path, dpi=self.dpi, bbox_inches='tight')
        plt.close(fig)
        return str(path)

    def plot_parameter_sweep(self, param_values: List[float], metric_values: List[float],
                              param_name: str = "Parameter", metric_name: str = "Metric",
                              filename: str = "sweep") -> Optional[str]:
        """Plot parameter sweep results."""
        if not HAS_MPL:
            return None

        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        ax.plot(param_values, metric_values, 'b-o', markersize=5)
        ax.set_xlabel(param_name)
        ax.set_ylabel(metric_name)
        ax.set_title(f'{metric_name} vs {param_name}')
        ax.grid(True, alpha=0.3)

        path = self.output_dir / f"{filename}.{self.fmt}"
        fig.savefig(path, dpi=self.dpi, bbox_inches='tight')
        plt.close(fig)
        return str(path)
