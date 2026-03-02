"""Unit conversion utilities for FeaGPT.

Handles conversion between common engineering unit systems:
- SI (meters, Pascals, kilograms)
- mm-based (millimeters, MPa, tonnes)
- Imperial (inches, psi, pounds)
"""

from typing import Union

# Length conversion factors to meters
LENGTH_TO_M = {
    "m": 1.0, "mm": 1e-3, "cm": 1e-2, "km": 1e3,
    "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.344,
    "um": 1e-6, "nm": 1e-9,
}

# Stress/pressure conversion factors to Pascals
STRESS_TO_PA = {
    "Pa": 1.0, "kPa": 1e3, "MPa": 1e6, "GPa": 1e9,
    "psi": 6894.757, "ksi": 6894757.0, "bar": 1e5, "atm": 101325.0,
}

# Mass conversion factors to kilograms
MASS_TO_KG = {
    "kg": 1.0, "g": 1e-3, "mg": 1e-6, "tonne": 1e3, "t": 1e3,
    "lb": 0.453592, "oz": 0.0283495, "slug": 14.5939,
}

# Force conversion factors to Newtons
FORCE_TO_N = {
    "N": 1.0, "kN": 1e3, "MN": 1e6, "mN": 1e-3,
    "lbf": 4.44822, "kgf": 9.80665, "dyn": 1e-5,
}

# Density conversion factors to kg/m^3
DENSITY_TO_KGM3 = {
    "kg/m3": 1.0, "g/cm3": 1000.0, "kg/mm3": 1e9,
    "tonne/mm3": 1e12, "lb/in3": 27679.9, "lb/ft3": 16.0185,
}

# Temperature offsets (not simple multipliers)
TEMP_CONVERSIONS = {
    ("C", "K"): lambda t: t + 273.15,
    ("K", "C"): lambda t: t - 273.15,
    ("C", "F"): lambda t: t * 9/5 + 32,
    ("F", "C"): lambda t: (t - 32) * 5/9,
    ("K", "F"): lambda t: (t - 273.15) * 9/5 + 32,
    ("F", "K"): lambda t: (t - 32) * 5/9 + 273.15,
}

# Angle conversions
ANGLE_TO_RAD = {
    "rad": 1.0, "deg": 0.017453292519943295, "rev": 6.283185307179586,
}

# Angular velocity
ANGVEL_TO_RADS = {
    "rad/s": 1.0, "rpm": 0.10471975511965978, "deg/s": 0.017453292519943295,
}


def convert_length(value: float, from_unit: str, to_unit: str) -> float:
    """Convert between length units."""
    if from_unit not in LENGTH_TO_M:
        raise ValueError(f"Unknown length unit: {from_unit}")
    if to_unit not in LENGTH_TO_M:
        raise ValueError(f"Unknown length unit: {to_unit}")
    return value * LENGTH_TO_M[from_unit] / LENGTH_TO_M[to_unit]


def convert_stress(value: float, from_unit: str, to_unit: str) -> float:
    """Convert between stress/pressure units."""
    if from_unit not in STRESS_TO_PA:
        raise ValueError(f"Unknown stress unit: {from_unit}")
    if to_unit not in STRESS_TO_PA:
        raise ValueError(f"Unknown stress unit: {to_unit}")
    return value * STRESS_TO_PA[from_unit] / STRESS_TO_PA[to_unit]


def convert_mass(value: float, from_unit: str, to_unit: str) -> float:
    """Convert between mass units."""
    if from_unit not in MASS_TO_KG:
        raise ValueError(f"Unknown mass unit: {from_unit}")
    if to_unit not in MASS_TO_KG:
        raise ValueError(f"Unknown mass unit: {to_unit}")
    return value * MASS_TO_KG[from_unit] / MASS_TO_KG[to_unit]


def convert_force(value: float, from_unit: str, to_unit: str) -> float:
    """Convert between force units."""
    if from_unit not in FORCE_TO_N:
        raise ValueError(f"Unknown force unit: {from_unit}")
    if to_unit not in FORCE_TO_N:
        raise ValueError(f"Unknown force unit: {to_unit}")
    return value * FORCE_TO_N[from_unit] / FORCE_TO_N[to_unit]


def convert_density(value: float, from_unit: str, to_unit: str) -> float:
    """Convert between density units."""
    if from_unit not in DENSITY_TO_KGM3:
        raise ValueError(f"Unknown density unit: {from_unit}")
    if to_unit not in DENSITY_TO_KGM3:
        raise ValueError(f"Unknown density unit: {to_unit}")
    return value * DENSITY_TO_KGM3[from_unit] / DENSITY_TO_KGM3[to_unit]


def convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    """Convert between temperature units."""
    if from_unit == to_unit:
        return value
    key = (from_unit, to_unit)
    if key not in TEMP_CONVERSIONS:
        raise ValueError(f"Unknown temperature conversion: {from_unit} -> {to_unit}")
    return TEMP_CONVERSIONS[key](value)


def convert_angular_velocity(value: float, from_unit: str, to_unit: str) -> float:
    """Convert between angular velocity units (rpm, rad/s, deg/s)."""
    if from_unit not in ANGVEL_TO_RADS:
        raise ValueError(f"Unknown angular velocity unit: {from_unit}")
    if to_unit not in ANGVEL_TO_RADS:
        raise ValueError(f"Unknown angular velocity unit: {to_unit}")
    return value * ANGVEL_TO_RADS[from_unit] / ANGVEL_TO_RADS[to_unit]


def parse_unit_string(s: str) -> tuple:
    """Parse a value+unit string like '500 MPa' or '200mm'.

    Returns (value, unit) tuple.
    """
    s = s.strip()
    # Find where the number ends
    i = 0
    while i < len(s) and (s[i].isdigit() or s[i] in '.eE+-'):
        i += 1
    if i == 0:
        raise ValueError(f"Cannot parse unit string: {s}")
    value = float(s[:i])
    unit = s[i:].strip()
    return value, unit


def rpm_to_rad_s(rpm: float) -> float:
    """Convert RPM to radians per second."""
    return rpm * 0.10471975511965978


def rad_s_to_rpm(rad_s: float) -> float:
    """Convert radians per second to RPM."""
    return rad_s / 0.10471975511965978
