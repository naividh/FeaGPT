"""
Parameter space generation for FeaGPT batch processing.
Implements Equation (6): Cartesian product expansion.
"""
import itertools
import logging
from typing import Dict, List, Any

import numpy as np

logger = logging.getLogger(__name__)


class ParameterSpaceGenerator:
    """Generates parameter spaces from range specifications."""

    def __init__(self):
        self.parameters = {}

    def generate(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate all configurations from parameter spec.

        Args:
            spec: Dict mapping param names to range dicts
                  e.g. {"thickness": {"min": 1.0, "max": 2.0, "step": 0.5}}

        Returns:
            List of configuration dicts (Cartesian product)
        """
        if not spec:
            return [{}]

        parsed = self._parse_ranges(spec)
        self.parameters = parsed

        if not parsed:
            return [{}]

        names = list(parsed.keys())
        value_lists = [parsed[n] for n in names]

        configs = []
        for combo in itertools.product(*value_lists):
            config = dict(zip(names, combo))
            configs.append(config)

        logger.info(
            f"Generated {len(configs)} configurations "
            f"from {len(names)} parameters"
        )
        return configs

    def _parse_ranges(
        self, spec: Dict[str, Any]
    ) -> Dict[str, List]:
        """Parse parameter specs into value lists."""
        parsed = {}

        for name, param in spec.items():
            if isinstance(param, list):
                parsed[name] = param
            elif isinstance(param, dict):
                if "values" in param:
                    parsed[name] = param["values"]
                elif all(
                    k in param for k in ("min", "max", "step")
                ):
                    parsed[name] = self._generate_range(
                        param["min"],
                        param["max"],
                        param["step"],
                    )
                else:
                    val = param.get("value", param.get("default"))
                    if val is not None:
                        parsed[name] = [val]
            else:
                parsed[name] = [param]

        return parsed

    def _generate_range(
        self,
        min_val: float,
        max_val: float,
        step: float,
    ) -> List[float]:
        """Generate range of values with step."""
        vals = np.arange(
            min_val, max_val + step / 2, step
        )
        return [round(v, 6) for v in vals.tolist()]
