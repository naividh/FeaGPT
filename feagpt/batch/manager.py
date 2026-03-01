"""
Parameter Space Generation (Equation 6).
Cartesian product expansion: P = prod_{i=1}^{n} range(p_min_i, p_max_i, delta_p_i)
"""

import itertools
import logging

logger = logging.getLogger(__name__)


class ParameterSpace:
    """Parameter space for parametric studies."""

        def __init__(self, parameters):
                    self.parameters = parameters

                        @classmethod
                            def from_spec(cls, param_spec):
                                    """Create from planning specification."""
                                            return cls(param_spec)

                                                def expand(self):
                                                        """Expand parameter space via Cartesian product (Equation 6)."""
                                                                param_names = []
                                                                        param_values = []

                                                                                for name, param in self.parameters.items():
                                                                                            param_names.append(name)
                                                                                                        if "values" in param:
                                                                                                                            param_values.append(param["values"])
                                                                                                                                        elif all(k in param for k in ["min", "max", "step"]):
                                                                                                                                                            import numpy as np
                                                                                                                                                                            vals = np.arange(param["min"], param["max"] + param["step"]/2, param["step"])
                                                                                                                                                                                            param_values.append([round(v, 4) for v in vals.tolist()])
                                                                                                                                                                                                        else:
                                                                                                                                                                                                                            param_values.append([param.get("default", 0)])

                                                                                                                                                                                                                                    # Cartesian product
                                                                                                                                                                                                                                            configurations = []
                                                                                                                                                                                                                                                    for combo in itertools.product(*param_values):
                                                                                                                                                                                                                                                                    config = dict(zip(param_names, combo))
                                                                                                                                                                                                                                                                                configurations.append(config)

                                                                                                                                                                                                                                                                                        logger.info(f"Parameter space: {len(configurations)} configurations "
                                                                                                                                                                                                                                                                                                           f"from {len(param_names)} parameters")
                                                                                                                                                                                                                                                                                                                   for name, vals in zip(param_names, param_values):
                                                                                                                                                                                                                                                                                                                                logger.info(f"  {name}: {len(vals)} values ({vals[0]} to {vals[-1]})")

                                                                                                                                                                                                                                                                                                                                        return configurations

                                                                                                                                                                                                                                                                                                                                            def __len__(self):
                                                                                                                                                                                                                                                                                                                                                        total = 1
                                                                                                                                                                                                                                                                                                                                                                for param in self.parameters.values():
                                                                                                                                                                                                                                                                                                                                                                            if "values" in param:
                                                                                                                                                                                                                                                                                                                                                                                                total *= len(param["values"])
                                                                                                                                                                                                                                                                                                                                                                                                        return total