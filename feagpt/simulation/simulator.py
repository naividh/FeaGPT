"""
FEA Simulation module for FeaGPT.

Manages CalculiX solver execution, input file generation,
and result collection.
"""
import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class FEASimulator:
    """
    Runs FEA simulations using CalculiX solver.

    Handles input deck generation, solver invocation,
    and output file management.
    """

    def __init__(self, config):
        self.config = config
        self.solver_path = config.simulation.calculix_path
        self.timeout = config.simulation.timeout

    def run(
        self,
        input_file: Path,
        output_dir: Path,
    ) -> Dict[str, Any]:
        """
        Execute FEA simulation.

        Args:
            input_file: Path to CalculiX input deck (.inp)
            output_dir: Directory for output files

        Returns:
            Dict with status, timing, and output paths
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        job_name = input_file.stem

        logger.info(f"Starting simulation: {job_name}")
        start_time = time.time()

        try:
            result = subprocess.run(
                [self.solver_path, "-i", str(input_file)],
                cwd=str(output_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            elapsed = time.time() - start_time

            # Check for output files
            frd_file = output_dir / f"{job_name}.frd"
            dat_file = output_dir / f"{job_name}.dat"

            success = result.returncode == 0 and frd_file.exists()

            if success:
                logger.info(
                    f"Simulation complete in {elapsed:.1f}s"
                )
            else:
                logger.error(
                    f"Simulation failed: {result.stderr[:500]}"
                )

            return {
                "success": success,
                "elapsed_seconds": elapsed,
                "returncode": result.returncode,
                "frd_file": str(frd_file) if frd_file.exists() else None,
                "dat_file": str(dat_file) if dat_file.exists() else None,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except subprocess.TimeoutExpired:
            logger.error(
                f"Simulation timed out after {self.timeout}s"
            )
            return {
                "success": False,
                "elapsed_seconds": self.timeout,
                "error": "timeout",
            }
        except FileNotFoundError:
            logger.error(
                f"Solver not found: {self.solver_path}"
            )
            return {
                "success": False,
                "error": "solver_not_found",
            }

    def generate_input_deck(
        self,
        spec: Dict[str, Any],
        mesh_file: Path,
        output_path: Path,
    ) -> Path:
        """
        Generate CalculiX input deck from specification.

        Args:
            spec: FEA specification dict
            mesh_file: Path to mesh file
            output_path: Where to write the .inp file

        Returns:
            Path to generated input deck
        """
        lines = []
        lines.append("** FeaGPT Generated Input Deck")
        lines.append(f"** Generated for: {spec.get('geometry', {}).get('type', 'unknown')}")
        lines.append("")

        # Include mesh
        lines.append(f"*INCLUDE, INPUT={mesh_file.name}")
        lines.append("")

        # Material definition
        mat = spec.get("material", {})
        mat_name = mat.get("name", "Material1")
        E = mat.get("youngs_modulus", 210e9)
        nu = mat.get("poissons_ratio", 0.3)
        rho = mat.get("density", 7850)

        lines.append(f"*MATERIAL, NAME={mat_name}")
        lines.append("*ELASTIC")
        lines.append(f"{E}, {nu}")
        lines.append("*DENSITY")
        lines.append(f"{rho}")
        lines.append("")

        # Section assignment
        lines.append(f"*SOLID SECTION, ELSET=EALL, MATERIAL={mat_name}")
        lines.append("")

        # Boundary conditions
        for bc in spec.get("boundary_conditions", []):
            bc_type = bc.get("type", "fixed")
            if bc_type == "fixed":
                lines.append("*BOUNDARY")
                lines.append("NFIX, 1, 3, 0.0")
        lines.append("")

        # Loads
        lines.append("*STEP")
        lines.append("*STATIC")
        for load in spec.get("loads", []):
            load_type = load.get("type", "force")
            mag = load.get("magnitude", 0)
            direction = load.get("direction", "-Y")

            dof_map = {
                "X": 1, "-X": 1,
                "Y": 2, "-Y": 2,
                "Z": 3, "-Z": 3,
            }
            dof = dof_map.get(direction, 2)
            sign = -1 if direction.startswith("-") else 1

            if load_type == "force":
                lines.append("*CLOAD")
                lines.append(f"NLOAD, {dof}, {sign * mag}")
            elif load_type == "pressure":
                lines.append("*DLOAD")
                lines.append(f"ELOAD, P, {mag}")
        lines.append("")

        # Output requests
        lines.append("*NODE FILE")
        lines.append("U")
        lines.append("*EL FILE")
        lines.append("S, E")
        lines.append("*END STEP")

        output_path.write_text("\n".join(lines))
        logger.info(f"Input deck written: {output_path}")
        return output_path

    def check_solver(self) -> bool:
        """Check if CalculiX solver is available."""
        try:
            result = subprocess.run(
                [self.solver_path, "-v"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
