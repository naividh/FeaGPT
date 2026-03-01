"""
Parameter space generation for FeaGPT batch processing.
Implements Equation (6): Cartesian product expansion.
"""
import itertools
import logging

logger = logging.getLogger(__name__)


class ParameterSpaceGenerator:
      """Generates parameter spaces from range specifications."""

    def __init__(self):
              self.parameters = {}

    def parse_ranges(self, spec):
              """Parse parameter specs into value lists."""
              parsed = {}
              for name, param in spec.items():
                            if isinstance(param, list):
                                              parsed[name] = param
elif isinstance(param, dict):
                if "values" in param:
                                      parsed[name] = param["values"]
elif all(k in param for k in ("min", "max", "step")):
                      parsed[name] = self._generate_range(
                                                param["min"], param["max"], param["step"]
                      )
else:
                      parsed[name] = [param.get("value", param.get("default"))]
else:
                parsed[name] = [param]
          self.parameters = parsed
        return parsed

    def generate_configurations(self, parameters=None):
              """Generate all configs via Cartesian product (Eq. 6)."""
              params = parameters or self.parameters
              if not params:
                            return [{}]
                        names = list(params.keys())
        value_lists = [params[n] for n in names]
        configs = [
                      dict(zip(names, combo))
                      for combo in itertools.product(*value_lists)
        ]
        logger.info(f"Generated {len(configs)} configurations")
        return configs

    def get_total_count(self, parameters=None):
              """Get total config count without generating them."""
        params = parameters or self.parameters
        count = 1
        for vals in (params or {}).values():
                      count *= len(vals)
                  return count

    @staticmethod
    def _generate_range(min_val, max_val, step):
              """Generate range with float handling."""
        values = []
        current = min_val
        while current <= max_val + step * 0.01:
                      values.append(round(current, 10))
                      current += step
                  return values

    def filter_infeasible(self, configs, constraints=None):
              """Filter infeasible parameter combinations."""
        if not constraints:
                      return configs
                  feasible = [
                                c for c in configs
                                if all(check(c) for check in constraints.values())
                  ]
        removed = len(configs) - len(feasible)
        if removed > 0:
                      logger.info(f"Filtered {removed} infeasible configs")
                  return feasible
