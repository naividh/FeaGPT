"""
GMSA Pipeline Orchestrator for FeaGPT.
Coordinates the complete Geometry-Mesh-Simulation-Analysis workflow.
"""
import logging
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from feagpt.config import FeaGPTConfig

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Container for pipeline execution results."""
    success: bool = False
    stage: str = ""
    spec: Dict[str, Any] = field(default_factory=dict)
    geometry_path: Optional[str] = None
    mesh_path: Optional[str] = None
    results_path: Optional[str] = None
    results_data: Dict[str, Any] = field(default_factory=dict)
    analysis_data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    timing: Dict[str, float] = field(default_factory=dict)

    def to_dict(self):
        return {
            "success": self.success,
            "stage": self.stage,
            "geometry_path": self.geometry_path,
            "mesh_path": self.mesh_path,
            "results_path": self.results_path,
            "results_data": self.results_data,
            "analysis_data": self.analysis_data,
            "errors": self.errors,
            "timing": self.timing,
        }


class GMSAPipeline:
    """
    Main GMSA pipeline orchestrator.

    Implements the 5-stage pipeline from the paper:
    1. Engineering Analysis Planning (NL -> structured JSON)
    2. Geometry Generation (JSON -> STEP file)
    3. Adaptive Mesh Generation (STEP -> INP mesh)
    4. FEA Simulation (INP -> FRD results)
    5. Result Analysis (FRD -> insights)
    """

    def __init__(self, config: Optional[FeaGPTConfig] = None):
        self.config = config or FeaGPTConfig()
        self._planner = None
        self._geometry_gen = None
        self._mesher = None
        self._simulator = None
        self._analyzer = None
        self._initialized = False

    def initialize(self):
        """Lazy initialization of all pipeline modules."""
        if self._initialized:
            return

        logger.info("Initializing GMSA pipeline modules...")

        try:
            from feagpt.planning.planner import AnalysisPlanner
            self._planner = AnalysisPlanner(self.config)
            logger.info("Planning module initialized")
        except ImportError as e:
            logger.warning(f"Planning module not available: {e}")

        try:
            from feagpt.geometry.generator import GeometryGenerator
            self._geometry_gen = GeometryGenerator(self.config)
            logger.info("Geometry module initialized")
        except ImportError as e:
            logger.warning(f"Geometry module not available: {e}")

        try:
            from feagpt.meshing.mesher import AdaptiveMesher
            self._mesher = AdaptiveMesher(self.config)
            logger.info("Meshing module initialized")
        except ImportError as e:
            logger.warning(f"Meshing module not available: {e}")

        try:
            from feagpt.simulation.simulator import FEASimulator
            self._simulator = FEASimulator(self.config)
            logger.info("Simulation module initialized")
        except ImportError as e:
            logger.warning(f"Simulation module not available: {e}")

        try:
            from feagpt.analysis.analyzer import ResultAnalyzer
            self._analyzer = ResultAnalyzer(self.config)
            logger.info("Analysis module initialized")
        except ImportError as e:
            logger.warning(f"Analysis module not available: {e}")

        self._initialized = True
        logger.info("GMSA pipeline initialization complete")

    def run(self, description: str, output_dir: Optional[str] = None) -> PipelineResult:
        """
        Execute the complete GMSA pipeline from natural language description.

        Args:
            description: Natural language engineering specification
            output_dir: Directory for output files (default: config.output.directory)

        Returns:
            PipelineResult with all outputs and timing data
        """
        self.initialize()
        result = PipelineResult()
        out = Path(output_dir or self.config.output.directory)
        out.mkdir(parents=True, exist_ok=True)

        # Stage 1: Planning
        result.stage = "planning"
        t0 = time.time()
        logger.info("Stage 1/5: Engineering Analysis Planning")
        try:
            spec = self._run_planning(description)
            result.spec = spec
            result.timing["planning"] = time.time() - t0
            logger.info(f"Planning complete in {result.timing['planning']:.2f}s")
        except Exception as e:
            result.errors.append(f"Planning failed: {e}")
            logger.error(f"Planning failed: {e}")
            return result

        # Check if parametric study
        is_parametric = "parameters" in spec and spec["parameters"]

        # Stage 2: Geometry Generation
        result.stage = "geometry"
        t0 = time.time()
        logger.info("Stage 2/5: Geometry Generation")
        try:
            geo_path = self._run_geometry(spec, out)
            result.geometry_path = str(geo_path)
            result.timing["geometry"] = time.time() - t0
            logger.info(f"Geometry complete in {result.timing['geometry']:.2f}s")
        except Exception as e:
            result.errors.append(f"Geometry generation failed: {e}")
            logger.error(f"Geometry generation failed: {e}")
            return result

        # Stage 3: Mesh Generation
        result.stage = "meshing"
        t0 = time.time()
        logger.info("Stage 3/5: Adaptive Mesh Generation")
        try:
            mesh_path = self._run_meshing(geo_path, spec, out)
            result.mesh_path = str(mesh_path)
            result.timing["meshing"] = time.time() - t0
            logger.info(f"Meshing complete in {result.timing['meshing']:.2f}s")
        except Exception as e:
            result.errors.append(f"Mesh generation failed: {e}")
            logger.error(f"Mesh generation failed: {e}")
            return result

        # Stage 4: FEA Simulation
        result.stage = "simulation"
        t0 = time.time()
        logger.info("Stage 4/5: FEA Simulation")
        try:
            sim_results = self._run_simulation(mesh_path, spec, out)
            result.results_path = sim_results.get("frd_path")
            result.results_data = sim_results
            result.timing["simulation"] = time.time() - t0
            logger.info(f"Simulation complete in {result.timing['simulation']:.2f}s")
        except Exception as e:
            result.errors.append(f"Simulation failed: {e}")
            logger.error(f"Simulation failed: {e}")
            return result

        # Stage 5: Result Analysis (optional, for parametric or optimization)
        if is_parametric or spec.get("data_analysis", {}).get("objectives"):
            result.stage = "analysis"
            t0 = time.time()
            logger.info("Stage 5/5: Result Analysis")
            try:
                analysis = self._run_analysis(sim_results, spec)
                result.analysis_data = analysis
                result.timing["analysis"] = time.time() - t0
                logger.info(f"Analysis complete in {result.timing['analysis']:.2f}s")
            except Exception as e:
                result.errors.append(f"Analysis failed: {e}")
                logger.error(f"Analysis failed: {e}")

        result.success = True
        result.stage = "complete"
        total = sum(result.timing.values())
        logger.info(f"Pipeline complete in {total:.2f}s total")

        # Save results
        results_file = out / "results.json"
        with open(results_file, "w") as f:
            json.dump(result.to_dict(), f, indent=2, default=str)

        return result

    def run_batch(self, description: str, output_dir: Optional[str] = None) -> List[PipelineResult]:
        """
        Execute batch parametric study from natural language description.
        """
        self.initialize()
        out = Path(output_dir or self.config.output.directory)
        out.mkdir(parents=True, exist_ok=True)

        # Plan
        spec = self._run_planning(description)

        # Generate parameter space
        if "parameters" not in spec or not spec["parameters"]:
            logger.info("No parametric study detected, running single configuration")
            return [self.run(description, output_dir)]

        from feagpt.batch.parameter_space import ParameterSpaceGenerator
        ps_gen = ParameterSpaceGenerator()
        configs = ps_gen.generate(spec["parameters"])
        logger.info(f"Generated {len(configs)} parameter configurations")

        # Execute batch
        from feagpt.batch.manager import BatchManager
        manager = BatchManager(self.config)
        results = manager.execute(
            base_spec=spec,
            configurations=configs,
            pipeline=self,
            output_dir=out,
        )

        return results

    def _run_planning(self, description: str) -> Dict[str, Any]:
        """Stage 1: Parse NL description into structured FEA specification."""
        if self._planner is None:
            raise RuntimeError("Planning module not initialized")
        return self._planner.plan(description)

    def _run_geometry(self, spec: Dict, output_dir: Path) -> Path:
        """Stage 2: Generate geometry from specification."""
        if self._geometry_gen is None:
            raise RuntimeError("Geometry module not initialized")
        return self._geometry_gen.generate(spec, output_dir)

    def _run_meshing(self, geometry_path: Path, spec: Dict, output_dir: Path) -> Path:
        """Stage 3: Generate adaptive mesh."""
        if self._mesher is None:
            raise RuntimeError("Meshing module not initialized")
        return self._mesher.mesh(geometry_path, spec, output_dir)

    def _run_simulation(self, mesh_path: Path, spec: Dict, output_dir: Path) -> Dict:
        """Stage 4: Configure and run CalculiX FEA."""
        if self._simulator is None:
            raise RuntimeError("Simulation module not initialized")
        return self._simulator.run(mesh_path, spec, output_dir)

    def _run_analysis(self, sim_results: Dict, spec: Dict) -> Dict:
        """Stage 5: Analyze results based on objectives."""
        if self._analyzer is None:
            raise RuntimeError("Analysis module not initialized")
        return self._analyzer.analyze(sim_results, spec)
