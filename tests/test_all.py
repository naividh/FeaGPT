"""
Comprehensive test suite for FeaGPT.
Tests all pure-Python modules without external FEA dependencies.
Run with: python -m pytest tests/test_all.py -v
"""
import pytest
import numpy as np
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ============================================================
# Test: Configuration
# ============================================================
class TestConfig:
    def test_config_loads(self):
        from feagpt.config import FeaGPTConfig
        cfg = FeaGPTConfig()
        assert cfg is not None

    def test_config_has_defaults(self):
        from feagpt.config import FeaGPTConfig
        cfg = FeaGPTConfig()
        assert hasattr(cfg, 'llm')
        assert hasattr(cfg, 'simulation')


# ============================================================
# Test: Parameter Space Generation (Eq. 6)
# ============================================================
class TestParameterSpace:
    def test_cartesian_product(self):
        from feagpt.batch.parameter_space import ParameterSpaceGenerator
        gen = ParameterSpaceGenerator()
        spec = {
            "shell_thickness": {"min": 1.0, "max": 2.0, "step": 0.5},
            "spar_width": {"min": 1.0, "max": 2.0, "step": 1.0},
        }
        configs = gen.generate(spec)
        assert len(configs) == 3 * 2  # 3 x 2 = 6

    def test_empty_spec(self):
        from feagpt.batch.parameter_space import ParameterSpaceGenerator
        gen = ParameterSpaceGenerator()
        configs = gen.generate({})
        assert len(configs) == 1  # single empty config


# ============================================================
# Test: Fatigue Analysis (Eq. 2-4)
# ============================================================
class TestFatigue:
    def test_basquin_relation(self):
        from feagpt.analysis.fatigue import FatigueAnalyzer
        fa = FatigueAnalyzer()
        cycles = fa.basquin_cycles(
            stress_amplitude=300e6,
            fatigue_strength_coeff=900e6,
            fatigue_exponent=-0.1
        )
        assert cycles > 0
        assert isinstance(cycles, float)

    def test_higher_stress_fewer_cycles(self):
        from feagpt.analysis.fatigue import FatigueAnalyzer
        fa = FatigueAnalyzer()
        c_low = fa.basquin_cycles(200e6, 900e6, -0.1)
        c_high = fa.basquin_cycles(400e6, 900e6, -0.1)
        assert c_low > c_high

    def test_miner_rule(self):
        from feagpt.analysis.fatigue import FatigueAnalyzer
        fa = FatigueAnalyzer()
        blocks = [
            {"cycles": 1000, "cycles_to_failure": 10000},
            {"cycles": 2000, "cycles_to_failure": 50000},
        ]
        damage = fa.miners_rule(blocks)
        expected = 1000 / 10000 + 2000 / 50000
        assert abs(damage - expected) < 1e-10


# ============================================================
# Test: Pareto Front (Eq. 5)
# ============================================================
class TestPareto:
    def test_dominance_check(self):
        from feagpt.analysis.pareto import ParetoAnalyzer
        pa = ParetoAnalyzer()
        a = [1.0, 2.0]
        b = [2.0, 3.0]
        assert pa.dominates(a, b) is True
        assert pa.dominates(b, a) is False

    def test_pareto_front_extraction(self):
        from feagpt.analysis.pareto import ParetoAnalyzer
        pa = ParetoAnalyzer()
        points = [
            [1.0, 5.0],
            [2.0, 3.0],
            [3.0, 1.0],
            [2.5, 4.0],  # dominated
            [4.0, 2.0],  # dominated
        ]
        front = pa.find_pareto_front(points)
        assert len(front) == 3
        dominated = [2.5, 4.0]
        assert dominated not in front

    def test_single_point(self):
        from feagpt.analysis.pareto import ParetoAnalyzer
        pa = ParetoAnalyzer()
        front = pa.find_pareto_front([[1.0, 2.0]])
        assert len(front) == 1


# ============================================================
# Test: Geometry Validators
# ============================================================
class TestValidators:
    def test_beam_dimensions_valid(self):
        from feagpt.geometry.validators import GeometryValidator
        v = GeometryValidator()
        result = v.validate({
            "type": "cantilever-beam",
            "length_mm": 200,
            "width_mm": 20,
            "height_mm": 20,
        })
        assert result["valid"] is True

    def test_negative_dimension_rejected(self):
        from feagpt.geometry.validators import GeometryValidator
        v = GeometryValidator()
        result = v.validate({
            "type": "cantilever-beam",
            "length_mm": -10,
            "width_mm": 20,
            "height_mm": 20,
        })
        assert result["valid"] is False

    def test_missing_type_rejected(self):
        from feagpt.geometry.validators import GeometryValidator
        v = GeometryValidator()
        result = v.validate({"length_mm": 100})
        assert result["valid"] is False


# ============================================================
# Test: Mesh Quality (Eq. 8)
# ============================================================
class TestMeshQuality:
    def test_aspect_ratio(self):
        from feagpt.meshing.quality import MeshQualityChecker
        mqc = MeshQualityChecker()
        ratio = mqc.aspect_ratio(
            [[0, 0, 0], [10, 0, 0], [5, 1, 0]]
        )
        assert ratio > 1.0

    def test_perfect_element(self):
        from feagpt.meshing.quality import MeshQualityChecker
        mqc = MeshQualityChecker()
        # Equilateral triangle
        h = np.sqrt(3) / 2
        ratio = mqc.aspect_ratio(
            [[0, 0, 0], [1, 0, 0], [0.5, h, 0]]
        )
        assert abs(ratio - 1.0) < 0.2


# ============================================================
# Test: Unit Conversions
# ============================================================
class TestUnits:
    def test_mm_to_m(self):
        from feagpt.utils.units import UnitConverter
        uc = UnitConverter()
        assert abs(uc.convert(1000, "mm", "m") - 1.0) < 1e-10

    def test_mpa_to_pa(self):
        from feagpt.utils.units import UnitConverter
        uc = UnitConverter()
        assert abs(uc.convert(1, "MPa", "Pa") - 1e6) < 1e-3

    def test_identity_conversion(self):
        from feagpt.utils.units import UnitConverter
        uc = UnitConverter()
        assert abs(uc.convert(42, "mm", "mm") - 42.0) < 1e-10


# ============================================================
# Test: File I/O
# ============================================================
class TestFileIO:
    def test_workspace_creation(self, temp_dir):
        from feagpt.utils.file_io import WorkspaceManager
        ws = WorkspaceManager(str(temp_dir))
        ws.setup()
        assert (temp_dir / "input").exists()
        assert (temp_dir / "output").exists()

    def test_write_and_read(self, temp_dir):
        from feagpt.utils.file_io import WorkspaceManager
        ws = WorkspaceManager(str(temp_dir))
        ws.setup()
        test_data = "test content"
        ws.write_file("input/test.txt", test_data)
        content = ws.read_file("input/test.txt")
        assert content == test_data


# ============================================================
# Test: Resource Monitor
# ============================================================
class TestResourceMonitor:
    def test_monitor_creation(self):
        from feagpt.utils.resource_monitor import ResourceMonitor
        rm = ResourceMonitor()
        assert rm is not None

    def test_get_usage(self):
        from feagpt.utils.resource_monitor import ResourceMonitor
        rm = ResourceMonitor()
        usage = rm.get_usage()
        assert "cpu_percent" in usage
        assert "memory_percent" in usage


# ============================================================
# Test: Knowledge Base
# ============================================================
class TestKnowledgeBase:
    def test_material_lookup(self):
        from feagpt.planning.knowledge_base import KnowledgeBase
        kb = KnowledgeBase()
        kb.initialize()
        mat = kb.get_material("Al-7075-T6")
        assert mat is not None
        assert "youngs_modulus" in mat

    def test_unknown_material(self):
        from feagpt.planning.knowledge_base import KnowledgeBase
        kb = KnowledgeBase()
        kb.initialize()
        mat = kb.get_material("UnknownMaterial123")
        assert mat is None


# ============================================================
# Test: Pipeline
# ============================================================
class TestPipeline:
    def test_pipeline_creation(self):
        from feagpt.config import FeaGPTConfig
        from feagpt.pipeline import FeaGPTPipeline
        cfg = FeaGPTConfig()
        pipe = FeaGPTPipeline(cfg)
        assert pipe is not None

    def test_pipeline_has_stages(self):
        from feagpt.config import FeaGPTConfig
        from feagpt.pipeline import FeaGPTPipeline
        cfg = FeaGPTConfig()
        pipe = FeaGPTPipeline(cfg)
        assert hasattr(pipe, 'run') or hasattr(pipe, 'execute')
