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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


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
        assert hasattr(cfg, "llm")
        assert hasattr(cfg, "simulation")


# ============================================================
# Test: Parameter Space Generation (Eq. 6)
# ============================================================
class TestParameterSpace:
    def test_cartesian_product(self):
        from feagpt.batch.parameter_space import ParameterSpaceGenerator
        gen = ParameterSpaceGenerator()
        configs = gen.generate({"length": [1, 2], "width": [3, 4]})
        assert len(configs) == 4

    def test_empty_space(self):
        from feagpt.batch.parameter_space import ParameterSpaceGenerator
        gen = ParameterSpaceGenerator()
        configs = gen.generate({})
        assert len(configs) == 1


# ============================================================
# Test: Fatigue Analysis (Eq. 2-4)
# ============================================================
class TestFatigue:
    def test_predict_life_basic(self):
        from feagpt.analysis.fatigue import FatigueAnalyzer
        fa = FatigueAnalyzer("Al-7075-T6")
        result = fa.predict_life(stress_amplitude=300e6)
        assert result.predicted_life > 0
        assert result.stress_amplitude == 300e6

    def test_higher_stress_fewer_cycles(self):
        from feagpt.analysis.fatigue import FatigueAnalyzer
        fa = FatigueAnalyzer("Al-7075-T6")
        r_low = fa.predict_life(200e6)
        r_high = fa.predict_life(400e6)
        assert r_low.predicted_life > r_high.predicted_life

    def test_miner_cumulative_damage(self):
        from feagpt.analysis.fatigue import FatigueAnalyzer
        fa = FatigueAnalyzer("Al-7075-T6")
        spectrum = [(300e6, 1000), (200e6, 5000)]
        result = fa.miner_cumulative_damage(spectrum)
        assert "total_damage" in result
        assert result["total_damage"] >= 0
        assert "failed" in result


# ============================================================
# Test: Pareto Front (Eq. 5)
# ============================================================
class TestPareto:
    def test_dominance_check(self):
        from feagpt.analysis.pareto import is_dominated
        a = [1.0, 2.0]
        b = [2.0, 3.0]
        assert is_dominated(b, a, minimize=True) is True
        assert is_dominated(a, b, minimize=True) is False

    def test_pareto_front_extraction(self):
        from feagpt.analysis.pareto import find_pareto_front
        points = np.array([
            [1.0, 5.0],
            [2.0, 3.0],
            [3.0, 1.0],
            [2.5, 4.0],
            [4.0, 2.0],
        ])
        front_indices = find_pareto_front(points)
        assert 0 in front_indices
        assert 1 in front_indices
        assert 2 in front_indices
        assert 3 not in front_indices

    def test_analyzer_class(self):
        from feagpt.analysis.pareto import ParetoAnalyzer
        pa = ParetoAnalyzer()
        points = np.array([[1.0, 5.0], [2.0, 3.0], [3.0, 1.0]])
        result = pa.analyze(points, objective_names=["stress", "weight"])
        assert "pareto_indices" in result


# ============================================================
# Test: Geometry Validators
# ============================================================
class TestValidators:
    def test_valid_geometry(self):
        from feagpt.geometry.validators import GeometryValidator
        v = GeometryValidator()
        result = v.validate({
            "type": "cantilever-beam",
            "length_mm": 100,
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
    def test_aspect_ratio_equilateral(self):
        from feagpt.meshing.quality import MeshQualityChecker
        mqc = MeshQualityChecker()
        tri = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.5, 0.866, 0.0]]
        ar = mqc.aspect_ratio(tri)
        assert ar >= 1.0
        assert ar < 1.5

    def test_full_check_returns_report(self):
        from feagpt.meshing.quality import MeshQualityChecker, QualityReport
        mqc = MeshQualityChecker()
        nodes = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.5, 0.866, 0.0],
            [0.5, 0.289, 0.816],
        ])
        elements = [[0, 1, 2], [0, 1, 3]]
        report = mqc.full_check(nodes, elements)
        assert isinstance(report, QualityReport)
        assert report.total_elements == 2


# ============================================================
# Test: Unit Conversions
# ============================================================
class TestUnits:
    def test_mm_to_m(self):
        from feagpt.utils.units import convert_length
        result = convert_length(1000.0, "mm", "m")
        assert abs(result - 1.0) < 1e-10

    def test_mpa_to_pa(self):
        from feagpt.utils.units import convert_stress
        result = convert_stress(1.0, "MPa", "Pa")
        assert abs(result - 1e6) < 1e-3

    def test_rpm_conversion(self):
        from feagpt.utils.units import rpm_to_rad_s, rad_s_to_rpm
        rads = rpm_to_rad_s(60.0)
        assert abs(rads - 2 * np.pi) < 1e-6
        back = rad_s_to_rpm(rads)
        assert abs(back - 60.0) < 1e-6


# ============================================================
# Test: File I/O
# ============================================================
class TestFileIO:
    def test_workspace_creation(self, temp_dir):
        from feagpt.utils.file_io import WorkspaceManager
        ws = WorkspaceManager(str(temp_dir))
        ws.setup()
        assert temp_dir.exists()

    def test_write_and_read(self, temp_dir):
        from feagpt.utils.file_io import WorkspaceManager
        ws = WorkspaceManager(str(temp_dir))
        ws.setup()
        ws.write_file("test.txt", "hello world")
        content = ws.read_file("test.txt")
        assert content == "hello world"


# ============================================================
# Test: Resource Monitor
# ============================================================
class TestResourceMonitor:
    def test_monitor_creation(self):
        from feagpt.batch.resource_monitor import ResourceMonitor
        rm = ResourceMonitor()
        assert rm is not None

    def test_optimal_batch_size(self):
        from feagpt.batch.resource_monitor import ResourceMonitor
        rm = ResourceMonitor(memory_per_case_mb=512, max_batch_size=100)
        size = rm.compute_optimal_batch_size()
        assert isinstance(size, int)
        assert size >= 1
        assert size <= 100


# ============================================================
# Test: Knowledge Base
# ============================================================
class TestKnowledgeBase:
    def test_fatigue_materials_data(self):
        from feagpt.analysis.fatigue import FATIGUE_MATERIALS
        assert "Al-7075-T6" in FATIGUE_MATERIALS
        mat = FATIGUE_MATERIALS["Al-7075-T6"]
        assert "fatigue_limit" in mat
        assert "ultimate_strength" in mat

    def test_unknown_material_fallback(self):
        from feagpt.analysis.fatigue import FatigueAnalyzer
        fa = FatigueAnalyzer("UnknownMaterial123")
        result = fa.predict_life(200e6)
        assert result.predicted_life > 0


# ============================================================
# Test: Pipeline
# ============================================================
class TestPipeline:
    def test_pipeline_creation(self):
        from feagpt.config import FeaGPTConfig
        from feagpt.pipeline import GMSAPipeline
        cfg = FeaGPTConfig()
        pipe = GMSAPipeline(cfg)
        assert pipe is not None

    def test_pipeline_has_run(self):
        from feagpt.config import FeaGPTConfig
        from feagpt.pipeline import GMSAPipeline
        cfg = FeaGPTConfig()
        pipe = GMSAPipeline(cfg)
        assert hasattr(pipe, "run")
