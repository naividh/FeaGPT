"""
Configuration module for FeaGPT.

Defines all configuration dataclasses for the pipeline.
"""
import os
import yaml
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM (Gemini) configuration."""
    provider: str = "gemini"
    model: str = "gemini-2.0-flash"
    api_key: str = ""
    temperature: float = 0.1
    max_tokens: int = 4096
    timeout: int = 30


@dataclass
class GeometryConfig:
    """Geometry generation configuration."""
    freecad_path: Optional[str] = None
    output_format: str = "step"
    max_generation_time: int = 120
    validation_enabled: bool = True


@dataclass
class MeshConfig:
    """Meshing configuration."""
    default_density: str = "medium"
    default_element_type: str = "C3D10"
    gmsh_path: Optional[str] = None
    min_quality: float = 0.3
    max_aspect_ratio: float = 10.0
    refinement_enabled: bool = True


@dataclass
class SimulationConfig:
    """FEA simulation configuration."""
    solver: str = "CalculiX"
    calculix_path: str = "ccx"
    max_iterations: int = 1000
    convergence_tol: float = 1e-6
    timeout: int = 600
    num_threads: int = 1


@dataclass
class AnalysisConfig:
    """Post-processing analysis configuration."""
    fatigue_enabled: bool = True
    pareto_enabled: bool = True
    sensitivity_enabled: bool = True
    surrogate_enabled: bool = False
    safety_factor: float = 2.0


@dataclass
class BatchConfig:
    """Batch processing configuration."""
    max_workers: int = 4
    timeout_per_job: int = 1800
    checkpoint_interval: int = 10
    output_dir: str = "batch_results"


@dataclass
class KnowledgeBaseConfig:
    """Knowledge base configuration."""
    materials_path: str = "knowledge/materials.json"
    geometry_patterns_path: str = "knowledge/geometry_patterns.json"
    solver_configs_path: str = "knowledge/solver_configs.json"


@dataclass
class FeaGPTConfig:
    """Main configuration for the FeaGPT pipeline."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    geometry: GeometryConfig = field(default_factory=GeometryConfig)
    mesh: MeshConfig = field(default_factory=MeshConfig)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    batch: BatchConfig = field(default_factory=BatchConfig)
    knowledge_base: KnowledgeBaseConfig = field(
        default_factory=KnowledgeBaseConfig
    )

    workspace: str = "workspace"
    log_level: str = "INFO"
    debug: bool = False

    @classmethod
    def from_yaml(cls, path: str) -> "FeaGPTConfig":
        """Load configuration from YAML file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}

        config = cls()

        if "llm" in data:
            for k, v in data["llm"].items():
                if hasattr(config.llm, k):
                    setattr(config.llm, k, v)

        if "geometry" in data:
            for k, v in data["geometry"].items():
                if hasattr(config.geometry, k):
                    setattr(config.geometry, k, v)

        if "mesh" in data:
            for k, v in data["mesh"].items():
                if hasattr(config.mesh, k):
                    setattr(config.mesh, k, v)

        if "simulation" in data:
            for k, v in data["simulation"].items():
                if hasattr(config.simulation, k):
                    setattr(config.simulation, k, v)

        if "analysis" in data:
            for k, v in data["analysis"].items():
                if hasattr(config.analysis, k):
                    setattr(config.analysis, k, v)

        if "batch" in data:
            for k, v in data["batch"].items():
                if hasattr(config.batch, k):
                    setattr(config.batch, k, v)

        for key in ["workspace", "log_level", "debug"]:
            if key in data:
                setattr(config, key, data[key])

        # Override API key from environment
        env_key = os.environ.get("GEMINI_API_KEY")
        if env_key:
            config.llm.api_key = env_key

        return config

    def setup_logging(self):
        """Configure logging based on config."""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        )

    def validate(self) -> List[str]:
        """Validate configuration. Returns list of warnings."""
        warnings = []
        if not self.llm.api_key:
            warnings.append(
                "No LLM API key set. Set GEMINI_API_KEY env var."
            )
        if self.simulation.solver == "CalculiX":
            import shutil
            if not shutil.which(self.simulation.calculix_path):
                warnings.append(
                    f"CalculiX not found at: "
                    f"{self.simulation.calculix_path}"
                )
        return warnings
