"""
FEA Results Analyzer for FeaGPT.

Post-processes CalculiX output files (.frd, .dat) to extract
stress, displacement, and other field data.
"""
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FEAResults:
    """Container for FEA simulation results."""
    max_von_mises_stress: float = 0.0
    max_displacement: float = 0.0
    max_principal_stress: float = 0.0
    min_principal_stress: float = 0.0
    strain_energy: float = 0.0
    mass: float = 0.0
    node_count: int = 0
    element_count: int = 0
    converged: bool = False
    stress_field: Optional[np.ndarray] = None
    displacement_field: Optional[np.ndarray] = None

    def safety_factor(self, yield_strength: float) -> float:
        """Compute safety factor against yield."""
        if self.max_von_mises_stress <= 0:
            return float("inf")
        return yield_strength / self.max_von_mises_stress

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding large arrays)."""
        return {
            "max_von_mises_stress": self.max_von_mises_stress,
            "max_displacement": self.max_displacement,
            "max_principal_stress": self.max_principal_stress,
            "min_principal_stress": self.min_principal_stress,
            "strain_energy": self.strain_energy,
            "mass": self.mass,
            "node_count": self.node_count,
            "element_count": self.element_count,
            "converged": self.converged,
        }


class ResultsAnalyzer:
    """
    Analyzes FEA output files from CalculiX.

    Parses .frd (field data) and .dat (summary) files
    to extract key engineering metrics.
    """

    def __init__(self, config=None):
        self.config = config
        self.results: Optional[FEAResults] = None

    def analyze(self, output_dir: Path) -> FEAResults:
        """
        Analyze all result files in the output directory.

        Args:
            output_dir: Directory containing CalculiX output

        Returns:
            FEAResults with extracted metrics
        """
        self.results = FEAResults()

        dat_files = list(output_dir.glob("*.dat"))
        frd_files = list(output_dir.glob("*.frd"))

        if dat_files:
            self._parse_dat(dat_files[0])
        if frd_files:
            self._parse_frd(frd_files[0])

        logger.info(
            f"Analysis complete: "
            f"max stress={self.results.max_von_mises_stress:.2f}, "
            f"max disp={self.results.max_displacement:.6f}"
        )
        return self.results

    def _parse_dat(self, path: Path):
        """Parse CalculiX .dat summary file."""
        try:
            text = path.read_text()

            # Extract strain energy
            se_match = re.search(
                r"total\s+strain\s+energy\s*=\s*([\d.eE+-]+)",
                text, re.IGNORECASE,
            )
            if se_match:
                self.results.strain_energy = float(se_match.group(1))

            # Extract mass
            mass_match = re.search(
                r"total\s+mass\s*=\s*([\d.eE+-]+)",
                text, re.IGNORECASE,
            )
            if mass_match:
                self.results.mass = float(mass_match.group(1))

            self.results.converged = (
                "convergence" in text.lower()
                or "total" in text.lower()
            )

        except Exception as e:
            logger.error(f"Error parsing .dat: {e}")

    def _parse_frd(self, path: Path):
        """Parse CalculiX .frd field results file."""
        try:
            text = path.read_text()
            stress_values = []
            disp_values = []

            lines = text.split("\n")
            in_stress = False
            in_disp = False

            for line in lines:
                if "STRESS" in line:
                    in_stress = True
                    in_disp = False
                    continue
                elif "DISP" in line:
                    in_disp = True
                    in_stress = False
                    continue
                elif line.startswith(" -3"):
                    in_stress = False
                    in_disp = False

                if in_stress and line.startswith(" -1"):
                    parts = line.split()
                    if len(parts) >= 7:
                        try:
                            sx = float(parts[3])
                            sy = float(parts[4])
                            sz = float(parts[5])
                            sxy = float(parts[6])
                            von_mises = np.sqrt(
                                0.5 * (
                                    (sx - sy)**2
                                    + (sy - sz)**2
                                    + (sz - sx)**2
                                    + 6 * sxy**2
                                )
                            )
                            stress_values.append(von_mises)
                        except (ValueError, IndexError):
                            pass

                if in_disp and line.startswith(" -1"):
                    parts = line.split()
                    if len(parts) >= 6:
                        try:
                            dx = float(parts[3])
                            dy = float(parts[4])
                            dz = float(parts[5])
                            mag = np.sqrt(dx**2 + dy**2 + dz**2)
                            disp_values.append(mag)
                        except (ValueError, IndexError):
                            pass

            if stress_values:
                arr = np.array(stress_values)
                self.results.max_von_mises_stress = float(np.max(arr))
                self.results.stress_field = arr

            if disp_values:
                arr = np.array(disp_values)
                self.results.max_displacement = float(np.max(arr))
                self.results.displacement_field = arr

        except Exception as e:
            logger.error(f"Error parsing .frd: {e}")

    def generate_report(self) -> str:
        """Generate a human-readable analysis report."""
        if self.results is None:
            return "No results available."

        r = self.results
        lines = [
            "=== FeaGPT Analysis Report ===",
            f"Max Von Mises Stress: {r.max_von_mises_stress:.2f} Pa",
            f"Max Displacement: {r.max_displacement:.6f} m",
            f"Strain Energy: {r.strain_energy:.4f} J",
            f"Mass: {r.mass:.4f} kg",
            f"Converged: {r.converged}",
        ]
        return "\n".join(lines)
