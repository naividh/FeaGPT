"""
Pytest configuration and shared fixtures for FeaGPT test suite.
"""
import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    d = tempfile.mkdtemp(prefix="feagpt_test_")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sample_spec():
    """Sample FEA specification for testing."""
    return {
        "material": {
            "name": "Al-7075-T6",
            "youngs_modulus": 71.7e9,
            "poissons_ratio": 0.33,
            "density": 2810,
            "yield_strength": 503e6,
        },
        "loads": [
            {
                "type": "force",
                "magnitude": 1000,
                "direction": "-Y",
                "location": "right edge",
            }
        ],
        "boundary_conditions": [
            {
                "type": "fixed",
                "location": "left edge",
                "constraints": ["X", "Y", "Z"],
            }
        ],
        "mesh": {
            "density": "fine",
            "element_type": "C3D10",
            "refinement_zones": [],
        },
        "analysis": {
            "type": "static",
            "solver": "CalculiX",
        },
        "geometry": {
            "type": "cantilever-beam",
            "length_mm": 200,
            "width_mm": 20,
            "height_mm": 20,
        },
    }


@pytest.fixture
def sample_results():
    """Sample FEA results for analysis testing."""
    import numpy as np
    np.random.seed(42)
    n = 50
    return {
        "max_von_mises_stress": np.random.uniform(200, 800, n).tolist(),
        "max_displacement": np.random.uniform(0.1, 5.0, n).tolist(),
        "mass": np.random.uniform(50, 200, n).tolist(),
    }


def pytest_collection_modifyitems(config, items):
    """Auto-mark tests based on dependencies."""
    for item in items:
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        if "batch" in item.nodeid or "slow" in item.nodeid:
            item.add_marker(pytest.mark.slow)
