"""
Analysis Planner for FeaGPT.
Implements Algorithm 1: NL description -> structured FEA specification (JSON).
Uses LLM (Gemini 2.5 Pro) with RAG from knowledge base.
"""
import json
import re
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Default material database for rule-based fallback
DEFAULT_MATERIALS = {
    "al-7075-t6": {"name": "Al-7075-T6", "youngs_modulus": 71.7e9, "poissons_ratio": 0.33, "density": 2810, "yield_strength": 503e6, "fatigue_limit": 160e6},
    "al-6061-t6": {"name": "Al-6061-T6", "youngs_modulus": 68.9e9, "poissons_ratio": 0.33, "density": 2700, "yield_strength": 276e6},
    "steel-4340": {"name": "Steel-AISI-4340", "youngs_modulus": 205e9, "poissons_ratio": 0.29, "density": 7850, "yield_strength": 862e6},
    "ti-6al-4v": {"name": "Ti-6Al-4V", "youngs_modulus": 113.8e9, "poissons_ratio": 0.342, "density": 4430, "yield_strength": 880e6},
    "inconel-718": {"name": "Inconel-718", "youngs_modulus": 200e9, "poissons_ratio": 0.3, "density": 8190, "yield_strength": 1034e6},
    "al-c355": {"name": "Al-C355", "youngs_modulus": 75e9, "poissons_ratio": 0.3, "density": 2650, "yield_strength": 250e6},
}


class AnalysisPlanner:
    """
    Transforms natural language descriptions into structured FEA specifications.
    Supports both LLM-based planning (Gemini) and rule-based fallback.
    """

    def __init__(self, config):
        self.config = config
        self._llm = None
        self._kb = None
        self._init_llm()

    def _init_llm(self):
        try:
            import google.generativeai as genai
            api_key = self.config.llm.api_key
            if api_key:
                genai.configure(api_key=api_key)
                self._llm = genai.GenerativeModel(self.config.llm.model)
                logger.info(f"LLM initialized: {self.config.llm.model}")
            else:
                logger.warning("No API key - using rule-based planning")
        except ImportError:
            logger.warning("google-generativeai not installed - using rule-based planning")

    def plan(self, description: str) -> Dict[str, Any]:
        """
        Parse NL description into structured FEA specification.
        Tries LLM first, falls back to rule-based extraction.
        """
        logger.info(f"Planning analysis for: {description[:100]}...")

        if self._llm:
            try:
                return self._plan_with_llm(description)
            except Exception as e:
                logger.warning(f"LLM planning failed ({e}), falling back to rule-based")

        return self._plan_rule_based(description)

    def _plan_with_llm(self, description: str) -> Dict[str, Any]:
        """Use Gemini to generate structured specification."""
        from feagpt.planning.prompts import ANALYSIS_PLANNING_PROMPT

        # Retrieve relevant knowledge
        material_context = self._retrieve_materials(description)
        solver_context = ""

        prompt = ANALYSIS_PLANNING_PROMPT.format(
            description=description,
            material_context=json.dumps(material_context, indent=2),
            solver_context=solver_context,
        )

        response = self._llm.generate_content(prompt)
        text = response.text

        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            spec = json.loads(json_match.group())
            logger.info("LLM planning successful")
            return spec

        raise ValueError("No valid JSON in LLM response")

    def _plan_rule_based(self, description: str) -> Dict[str, Any]:
        """Rule-based fallback: extract specs using regex and heuristics."""
        desc_lower = description.lower()
        spec = {
            "material": self._extract_material(desc_lower),
            "loads": self._extract_loads(description),
            "boundary_conditions": self._extract_bcs(description),
            "mesh": {"density": self._extract_mesh_level(desc_lower), "element_type": "C3D10"},
            "analysis": {"type": "static", "solver": "CalculiX"},
            "geometry": self._extract_geometry(description),
            "parameters": self._extract_parameters(description),
            "data_analysis": self._extract_analysis_objectives(desc_lower),
        }
        logger.info(f"Rule-based planning complete: {spec['geometry'].get('type', 'unknown')} geometry")
        return spec

    def _extract_material(self, desc: str) -> Dict:
        for key, mat in DEFAULT_MATERIALS.items():
            if key.replace("-", " ") in desc or key.replace("-", "") in desc:
                return mat
        if "aerospace" in desc or "aircraft" in desc or "wing" in desc:
            return DEFAULT_MATERIALS["al-7075-t6"]
        if "turbo" in desc or "turbine" in desc:
            return DEFAULT_MATERIALS["inconel-718"]
        if "steel" in desc:
            return DEFAULT_MATERIALS["steel-4340"]
        return DEFAULT_MATERIALS["al-7075-t6"]

    def _extract_loads(self, desc: str) -> List[Dict]:
        loads = []
        # Match patterns like "500N", "500 N", "1000 Pa"
        force_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:N|kN|MN)\b', desc, re.I)
        for val in force_matches:
            loads.append({"type": "force", "magnitude": float(val), "direction": "-Y", "location": "top edge"})
        pressure_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:Pa|kPa|MPa)\b', desc, re.I)
        for val in pressure_matches:
            loads.append({"type": "pressure", "magnitude": float(val), "location": "top surface"})
        if "centrifugal" in desc.lower() or "rpm" in desc.lower():
            rpm_match = re.search(r'(\d[\d,]*)\s*RPM', desc, re.I)
            rpm = float(rpm_match.group(1).replace(",", "")) if rpm_match else 10000
            loads.append({"type": "centrifugal", "rpm": rpm})
        if "aerodynamic" in desc.lower():
            loads.append({"type": "pressure", "magnitude": 5000, "location": "lower surface", "distribution": "aerodynamic"})
        if not loads:
            loads.append({"type": "force", "magnitude": 1000, "direction": "-Y", "location": "right edge"})
        return loads

    def _extract_bcs(self, desc: str) -> List[Dict]:
        bcs = []
        if any(w in desc.lower() for w in ["cantilever", "fixed", "clamp"]):
            bcs.append({"type": "fixed", "location": "left edge", "constraints": ["X", "Y", "Z"]})
        elif "wing" in desc.lower():
            bcs.append({"type": "fixed", "location": "wing root", "constraints": ["X", "Y", "Z"]})
        elif "cyclic" in desc.lower():
            bcs.append({"type": "cyclic_symmetry", "location": "sector boundaries"})
        else:
            bcs.append({"type": "fixed", "location": "left edge", "constraints": ["X", "Y", "Z"]})
        return bcs

    def _extract_mesh_level(self, desc: str) -> str:
        if "ultra" in desc and "fine" in desc:
            return "ultra_fine"
        if "fine" in desc:
            return "fine"
        if "coarse" in desc:
            return "coarse"
        return "fine"

    def _extract_geometry(self, desc: str) -> Dict:
        geo = {"type": "unknown"}
        naca_match = re.search(r'NACA\s*(\d{4})', desc, re.I)
        if naca_match:
            geo["type"] = "naca_wing"
            geo["naca_code"] = naca_match.group(1)
        chord = re.search(r'(\d+(?:\.\d+)?)\s*mm\s*chord', desc, re.I)
        if chord:
            geo["chord_mm"] = float(chord.group(1))
        span = re.search(r'(\d+(?:\.\d+)?)\s*mm\s*span', desc, re.I)
        if span:
            geo["span_mm"] = float(span.group(1))
        spars = re.search(r'(\d+)\s*spar', desc, re.I)
        if spars:
            geo["num_spars"] = int(spars.group(1))
        ribs = re.search(r'(\d+)\s*rib', desc, re.I)
        if ribs:
            geo["num_ribs"] = int(ribs.group(1))
        if "cantilever" in desc.lower() or "beam" in desc.lower():
            geo["type"] = "cantilever_beam"
        if "plate" in desc.lower() and "hole" in desc.lower():
            geo["type"] = "plate_with_hole"
        if "turbo" in desc.lower() and "compressor" in desc.lower():
            geo["type"] = "turbocharger_compressor"
        if "turbo" in desc.lower() and "turbine" in desc.lower():
            geo["type"] = "turbocharger_turbine"
        return geo

    def _extract_parameters(self, desc: str) -> Dict:
        params = {}
        range_pattern = r'(\w[\w\s]*)\s*(?:from|between)\s*(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*(?:mm|cm|m)?(?:\s*(?:in|,)?\s*(?:step|increment)\s*(\d+(?:\.\d+)?))?'
        matches = re.findall(range_pattern, desc, re.I)
        for name, min_val, max_val, step in matches:
            name = name.strip().lower().replace(" ", "_")
            step = float(step) if step else (float(max_val) - float(min_val)) / 5
            params[name] = {"min": float(min_val), "max": float(max_val), "step": step}
        return params

    def _extract_analysis_objectives(self, desc: str) -> Dict:
        objectives = []
        if "optim" in desc:
            objectives.extend(["minimize stress", "minimize weight"])
        if "fatigue" in desc:
            objectives.append("fatigue_life")
        if "sensitiv" in desc:
            objectives.append("sensitivity")
        return {"objectives": objectives, "metrics": ["von_mises_stress", "displacement", "mass"]}

    def _retrieve_materials(self, description: str) -> Dict:
        desc_lower = description.lower()
        for key, mat in DEFAULT_MATERIALS.items():
            if key.replace("-", " ") in desc_lower or key.replace("-", "") in desc_lower:
                return mat
        if "aerospace" in desc_lower:
            return DEFAULT_MATERIALS["al-7075-t6"]
        return {}
