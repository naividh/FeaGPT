"""
Geometry validation for FeaGPT.

Three-layer validation: syntax, physics, and manufacturability.
"""
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

KNOWN_TYPES = [
    "cantilever-beam", "cantilever_beam",
    "naca_wing", "naca-wing",
    "plate_with_hole", "plate-with-hole",
    "bracket", "I-beam", "tube",
]


class GeometryValidator:
    """
    Validates geometry specifications with 3-layer checking.

    Layer 1: Syntax (required fields, types)
    Layer 2: Physics (positive dimensions, reasonable ranges)
    Layer 3: Manufacturability (min thickness, aspect ratios)
    """

    def __init__(self):
        self.min_dimension_mm = 0.1
        self.max_dimension_mm = 10000.0
        self.max_aspect_ratio = 100.0

    def validate(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a geometry specification.

        Returns:
            {"valid": bool, "errors": [...], "warnings": [...]}
        """
        errors = []
        warnings = []

        # Layer 1: Syntax
        syntax_errors = self._check_syntax(spec)
        errors.extend(syntax_errors)

        # Layer 2: Physics
        if not syntax_errors:
            physics_errors = self._check_physics(spec)
            errors.extend(physics_errors)

        # Layer 3: Manufacturability
        if not errors:
            mfg_warnings = self._check_manufacturability(spec)
            warnings.extend(mfg_warnings)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def _check_syntax(self, spec: Dict) -> List[str]:
        """Layer 1: Check required fields and types."""
        errors = []

        if "type" not in spec:
            errors.append("Missing required field: type")
            return errors

        geo_type = spec["type"]
        if geo_type not in KNOWN_TYPES:
            errors.append(f"Unknown geometry type: {geo_type}")

        # Check dimension fields exist
        dim_fields = [
            k for k in spec.keys()
            if k.endswith("_mm") or k.endswith("_m")
        ]
        if not dim_fields and geo_type in KNOWN_TYPES:
            errors.append("No dimension fields found")

        return errors

    def _check_physics(self, spec: Dict) -> List[str]:
        """Layer 2: Check physical validity."""
        errors = []

        for key, val in spec.items():
            if not key.endswith("_mm") and not key.endswith("_m"):
                continue

            if not isinstance(val, (int, float)):
                errors.append(f"{key} must be numeric, got {type(val)}")
                continue

            if val <= 0:
                errors.append(f"{key} must be positive, got {val}")
            elif val < self.min_dimension_mm:
                errors.append(
                    f"{key}={val} below minimum {self.min_dimension_mm}mm"
                )
            elif val > self.max_dimension_mm:
                errors.append(
                    f"{key}={val} exceeds maximum {self.max_dimension_mm}mm"
                )

        return errors

    def _check_manufacturability(self, spec: Dict) -> List[str]:
        """Layer 3: Check manufacturability constraints."""
        warnings = []

        dims = {
            k: v for k, v in spec.items()
            if isinstance(v, (int, float))
            and (k.endswith("_mm") or k.endswith("_m"))
            and v > 0
        }

        if len(dims) >= 2:
            values = list(dims.values())
            ratio = max(values) / min(values)
            if ratio > self.max_aspect_ratio:
                warnings.append(
                    f"High aspect ratio ({ratio:.1f}:1) "
                    f"may cause mesh quality issues"
                )

        # Check for thin walls
        for key, val in dims.items():
            if "thickness" in key and val < 0.5:
                warnings.append(
                    f"{key}={val}mm is very thin for manufacturing"
                )

        return warnings


def validate_script(script: str) -> Tuple[bool, List[str]]:
    """
    Validate a FreeCAD Python script for safety.

    Checks for forbidden operations (file deletion, network).
    """
    errors = []

    forbidden = [
        "os.remove", "shutil.rmtree", "os.system",
        "subprocess.call", "exec(", "eval(",
        "import socket", "import requests",
        "__import__",
    ]

    for term in forbidden:
        if term in script:
            errors.append(f"Forbidden operation: {term}")

    required = ["FreeCAD", "Part"]
    for term in required:
        if term not in script:
            errors.append(f"Missing required import: {term}")

    return len(errors) == 0, errors
