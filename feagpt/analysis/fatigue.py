"""
S-N Curve Fatigue Life Assessment for FeaGPT.
Uses Basquin equation and Miner's cumulative damage theory.
"""
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


FATIGUE_MATERIALS = {
    "Al-7075-T6": {
        "fatigue_limit": 160e6,
        "ultimate_strength": 572e6,
        "basquin_b": -0.122,
        "basquin_sf": 1090e6,
        "endurance_cycles": 1e7,
    },
    "Al-6061-T6": {
        "fatigue_limit": 96.5e6,
        "ultimate_strength": 310e6,
        "basquin_b": -0.115,
        "basquin_sf": 585e6,
        "endurance_cycles": 1e7,
    },
    "Steel-AISI-4340": {
        "fatigue_limit": 400e6,
        "ultimate_strength": 1000e6,
        "basquin_b": -0.089,
        "basquin_sf": 1560e6,
        "endurance_cycles": 1e7,
    },
    "Ti-6Al-4V": {
        "fatigue_limit": 510e6,
        "ultimate_strength": 950e6,
        "basquin_b": -0.095,
        "basquin_sf": 1400e6,
        "endurance_cycles": 1e7,
    },
}


@dataclass
class FatigueResult:
    """Result of fatigue life assessment."""
    stress_amplitude: float = 0.0
    mean_stress: float = 0.0
    r_ratio: float = 0.0
    predicted_life: float = 0.0
    category: str = "unknown"
    safety_factor: float = 0.0
    damage_per_cycle: float = 0.0


class FatigueAnalyzer:
    """S-N curve fatigue life assessment with Basquin and Miner."""

    def __init__(self, material_name="Al-7075-T6"):
        self.material_name = material_name
        if material_name in FATIGUE_MATERIALS:
            self.material = FATIGUE_MATERIALS[material_name]
        else:
            logger.warning("Material %s not found, using Al-7075-T6", material_name)
            self.material = FATIGUE_MATERIALS["Al-7075-T6"]

    def predict_life(self, stress_amplitude, r_ratio=0.0):
        """Predict fatigue life using Basquin equation."""
        result = FatigueResult()
        result.stress_amplitude = stress_amplitude
        result.r_ratio = r_ratio
        fatigue_limit = self.material["fatigue_limit"]
        sf = self.material["basquin_sf"]
        b = self.material["basquin_b"]
        if r_ratio != -1:
            sigma_max = 2 * stress_amplitude / (1 - r_ratio)
            sigma_min = r_ratio * sigma_max
            result.mean_stress = (sigma_max + sigma_min) / 2.0
            su = self.material["ultimate_strength"]
            if result.mean_stress > 0:
                corrected_amp = stress_amplitude / (1 - result.mean_stress / su)
            else:
                corrected_amp = stress_amplitude
        else:
            corrected_amp = stress_amplitude
            result.mean_stress = 0.0
        if corrected_amp <= fatigue_limit:
            result.category = "infinite_life"
            result.predicted_life = float("inf")
            result.safety_factor = fatigue_limit / max(corrected_amp, 1e-10)
            result.damage_per_cycle = 0.0
        else:
            try:
                n_cycles = 0.5 * (corrected_amp / sf) ** (1.0 / b)
                n_cycles = max(n_cycles, 1.0)
            except (OverflowError, ZeroDivisionError):
                n_cycles = 1.0
            result.predicted_life = n_cycles
            result.damage_per_cycle = 1.0 / n_cycles
            result.safety_factor = fatigue_limit / max(corrected_amp, 1e-10)
            if n_cycles > 1e6:
                result.category = "high_cycle"
            elif n_cycles > 1e3:
                result.category = "finite_life"
            else:
                result.category = "low_cycle_critical"
        return result

    def miner_cumulative_damage(self, load_spectrum, r_ratio=0.0):
        """Miner linear cumulative damage: D = sum(n_i / N_i)."""
        total_damage = 0.0
        step_damages = []
        critical_step = -1
        max_step_damage = 0.0
        for i, (amp, n_applied) in enumerate(load_spectrum):
            res = self.predict_life(amp, r_ratio)
            if res.predicted_life == float("inf"):
                step_damage = 0.0
            else:
                step_damage = n_applied / res.predicted_life
            total_damage += step_damage
            step_damages.append(step_damage)
            if step_damage > max_step_damage:
                max_step_damage = step_damage
                critical_step = i
        return {
            "total_damage": total_damage,
            "remaining_life_fraction": max(1.0 - total_damage, 0.0),
            "failed": total_damage >= 1.0,
            "step_damages": step_damages,
            "critical_step": critical_step,
        }

    def analyze_batch(self, stress_amplitudes, r_ratio=0.0):
        """Analyze batch of configurations from parametric study."""
        results = []
        cats = {"infinite_life": 0, "high_cycle": 0, "finite_life": 0, "low_cycle_critical": 0}
        for amp in stress_amplitudes:
            res = self.predict_life(amp, r_ratio)
            results.append(res)
            cats[res.category] = cats.get(res.category, 0) + 1
        finite_lives = [r.predicted_life for r in results if r.predicted_life < 1e15]
        return {
            "total_configs": len(stress_amplitudes),
            "categories": cats,
            "infinite_life_pct": 100 * cats["infinite_life"] / max(len(stress_amplitudes), 1),
            "critical_pct": 100 * cats["low_cycle_critical"] / max(len(stress_amplitudes), 1),
            "median_finite_life": float(np.median(finite_lives)) if finite_lives else None,
            "results": results,
        }

    def generate_sn_curve(self, n_points=100):
        """Generate S-N curve data points for plotting."""
        sf = self.material["basquin_sf"]
        b = self.material["basquin_b"]
        fl = self.material["fatigue_limit"]
        log_n = np.linspace(1, 8, n_points)
        n_vals = 10 ** log_n
        stress_vals = sf * (2 * n_vals) ** b
        stress_vals = np.maximum(stress_vals, fl)
        return n_vals, stress_vals
