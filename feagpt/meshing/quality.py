"""
Mesh quality analysis for FeaGPT.

Implements element quality metrics including aspect ratio,
Jacobian determinant, and connectivity checks (Eq. 8).
"""
import numpy as np
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class QualityReport:
    """Mesh quality assessment report."""
    total_elements: int = 0
    passed_elements: int = 0
    min_quality: float = 0.0
    mean_quality: float = 0.0
    max_aspect_ratio: float = 0.0
    mean_aspect_ratio: float = 0.0
    issues: List[str] = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []

    @property
    def pass_rate(self) -> float:
        if self.total_elements == 0:
            return 0.0
        return self.passed_elements / self.total_elements


class MeshQualityChecker:
    """
    Checks mesh quality using standard FEA metrics.

    Metrics: aspect ratio, Jacobian determinant,
    element connectivity validation.
    """

    def __init__(
        self,
        min_quality: float = 0.3,
        max_aspect_ratio: float = 10.0,
    ):
        self.min_quality = min_quality
        self.max_aspect_ratio = max_aspect_ratio

    def aspect_ratio(self, vertices: List[List[float]]) -> float:
        """
        Compute aspect ratio of an element.

        Args:
            vertices: List of [x, y, z] coordinates

        Returns:
            Aspect ratio (1.0 = ideal)
        """
        pts = np.array(vertices, dtype=float)
        n = len(pts)
        if n < 2:
            return 1.0

        # Compute all edge lengths
        edges = []
        for i in range(n):
            for j in range(i + 1, n):
                edge_len = np.linalg.norm(pts[i] - pts[j])
                edges.append(edge_len)

        if not edges or min(edges) == 0:
            return float("inf")

        return max(edges) / min(edges)

    def jacobian_quality(
        self, vertices: List[List[float]]
    ) -> float:
        """
        Compute Jacobian-based quality metric.

        Returns value between 0 (degenerate) and 1 (ideal).
        """
        pts = np.array(vertices, dtype=float)
        n = len(pts)

        if n == 3:
            # Triangle: area-based quality
            v1 = pts[1] - pts[0]
            v2 = pts[2] - pts[0]
            cross = np.cross(v1, v2)
            area = np.linalg.norm(cross) / 2.0
            # Compare to equilateral triangle
            edges = [
                np.linalg.norm(pts[1] - pts[0]),
                np.linalg.norm(pts[2] - pts[1]),
                np.linalg.norm(pts[0] - pts[2]),
            ]
            max_edge = max(edges)
            if max_edge == 0:
                return 0.0
            ideal_area = (np.sqrt(3) / 4) * max_edge**2
            return min(area / ideal_area, 1.0) if ideal_area > 0 else 0.0

        elif n == 4:
            # Tetrahedron: volume-based quality
            v1 = pts[1] - pts[0]
            v2 = pts[2] - pts[0]
            v3 = pts[3] - pts[0]
            vol = abs(np.dot(v1, np.cross(v2, v3))) / 6.0
            edges = []
            for i in range(4):
                for j in range(i + 1, 4):
                    edges.append(np.linalg.norm(pts[i] - pts[j]))
            max_edge = max(edges)
            if max_edge == 0:
                return 0.0
            ideal_vol = (max_edge**3) / (6.0 * np.sqrt(2))
            return min(vol / ideal_vol, 1.0) if ideal_vol > 0 else 0.0

        return 0.5  # default for unsupported element types

    def check_connectivity(
        self,
        elements: List[List[int]],
        n_nodes: int,
    ) -> Tuple[bool, List[str]]:
        """
        Validate mesh connectivity.

        Args:
            elements: List of element node index lists
            n_nodes: Total number of nodes

        Returns:
            (is_valid, list of issues)
        """
        issues = []
        referenced = set()

        for i, elem in enumerate(elements):
            for node_id in elem:
                if node_id < 0 or node_id >= n_nodes:
                    issues.append(
                        f"Element {i}: invalid node {node_id}"
                    )
                referenced.add(node_id)

            # Check for duplicate nodes in element
            if len(set(elem)) != len(elem):
                issues.append(
                    f"Element {i}: duplicate nodes"
                )

        # Check for orphan nodes
        orphans = set(range(n_nodes)) - referenced
        if orphans:
            issues.append(
                f"{len(orphans)} orphan nodes not in any element"
            )

        return len(issues) == 0, issues

    def full_check(
        self,
        nodes: np.ndarray,
        elements: List[List[int]],
    ) -> QualityReport:
        """
        Run complete mesh quality assessment.

        Args:
            nodes: Array of node coordinates (n_nodes, 3)
            elements: List of element connectivity lists

        Returns:
            QualityReport with detailed metrics
        """
        report = QualityReport(total_elements=len(elements))
        qualities = []
        aspect_ratios = []

        for elem_nodes in elements:
            verts = [nodes[nid].tolist() for nid in elem_nodes]

            ar = self.aspect_ratio(verts)
            aspect_ratios.append(ar)

            q = self.jacobian_quality(verts)
            qualities.append(q)

            if q >= self.min_quality and ar <= self.max_aspect_ratio:
                report.passed_elements += 1

        if qualities:
            report.min_quality = float(np.min(qualities))
            report.mean_quality = float(np.mean(qualities))

        if aspect_ratios:
            report.max_aspect_ratio = float(np.max(aspect_ratios))
            report.mean_aspect_ratio = float(np.mean(aspect_ratios))

        # Connectivity check
        is_valid, conn_issues = self.check_connectivity(
            elements, len(nodes)
        )
        report.issues.extend(conn_issues)

        if report.pass_rate < 0.95:
            report.issues.append(
                f"Low pass rate: {report.pass_rate:.1%}"
            )

        logger.info(
            f"Quality check: {report.pass_rate:.1%} pass, "
            f"mean AR={report.mean_aspect_ratio:.2f}"
        )
        return report
