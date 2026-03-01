"""
Geometry Generator for FeaGPT.
Implements knowledge-augmented and novel synthesis modes (Eq. 2-3 in paper).
"""
import logging
import math
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class GeometryGenerator:
    """Generates CAD geometry from structured specifications."""

    def __init__(self, config):
        self.config = config
        self._generators = {
            "naca_wing": self._generate_naca_wing,
            "cantilever_beam": self._generate_cantilever_beam,
            "plate_with_hole": self._generate_plate_with_hole,
        }

    def generate(self, spec: Dict[str, Any], output_dir: Path) -> Path:
        geo_spec = spec.get("geometry", {})
        geo_type = geo_spec.get("type", "unknown")
        output_path = output_dir / "geometry.step"

        if geo_type in self._generators:
            logger.info(f"Knowledge-augmented generation: {geo_type}")
            script = self._generators[geo_type](geo_spec, spec)
        else:
            logger.info(f"Novel synthesis mode for: {geo_type}")
            script = self._synthesize_novel(spec)

        # Validate and execute
        from feagpt.geometry.validators import validate_script
        is_valid, errors = validate_script(script)
        if not is_valid:
            raise ValueError(f"Script validation failed: {errors}")

        self._execute_freecad_script(script, output_path)
        if not output_path.exists():
            raise FileNotFoundError(f"Geometry not generated: {output_path}")
        logger.info(f"Geometry saved: {output_path}")
        return output_path

    def _generate_naca_wing(self, geo: Dict, spec: Dict) -> str:
        code = geo.get("naca_code", "0012")
        chord = geo.get("chord_mm", 200.0)
        span = geo.get("span_mm", 200.0)
        shell_t = geo.get("shell_thickness_mm", 1.5)
        spar_w = geo.get("spar_width_mm", 1.5)
        rib_t = geo.get("rib_thickness_mm", 1.5)
        n_spars = geo.get("num_spars", 2)
        n_ribs = geo.get("num_ribs", 2)

        # NACA 4-digit params
        m = int(code[0]) / 100.0  # max camber
        p = int(code[1]) / 10.0   # camber position
        t_max = int(code[2:]) / 100.0  # max thickness

        return f'''import FreeCAD, Part, importerStep
import numpy as np

doc = FreeCAD.newDocument("NACAwing")

# NACA {code} profile - Eq. 3 in paper
def naca_thickness(x, t={t_max}):
    return (t/0.2) * (0.2969*np.sqrt(x) - 0.1260*x - 0.3516*x**2 + 0.2843*x**3 - 0.1015*x**4)

def naca_camber(x, m={m}, p={p}):
    if p == 0:
        return 0.0
    if x < p:
        return (m / p**2) * (2*p*x - x**2)
    return (m / (1-p)**2) * ((1-2*p) + 2*p*x - x**2)

chord = {chord}
span = {span}
n_pts = 100
x_pts = (1 - np.cos(np.linspace(0, np.pi, n_pts))) / 2

upper_pts = []
lower_pts = []
for x in x_pts:
    yc = naca_camber(x)
    yt = naca_thickness(x)
    upper_pts.append(FreeCAD.Vector(x*chord, (yc+yt)*chord, 0))
    lower_pts.append(FreeCAD.Vector(x*chord, (yc-yt)*chord, 0))

upper_wire = Part.makePolygon(upper_pts)
lower_wire = Part.makePolygon(list(reversed(lower_pts)))
profile_wire = Part.Wire([upper_wire, lower_wire])
profile_face = Part.Face(profile_wire)

# Extrude shell
shell_solid = profile_face.extrude(FreeCAD.Vector(0, 0, span))

# Hollow out
inner_face = profile_face.copy()
inner_face.scale({1-shell_t*2/chord})
inner_solid = inner_face.extrude(FreeCAD.Vector(0, 0, span))
wing = shell_solid.cut(inner_solid)

# Add spars
for i in range({n_spars}):
    pos = chord * (0.25 + 0.4 * i / max({n_spars}-1, 1))
    spar_box = Part.makeBox({spar_w}, chord*{t_max}*2, span, FreeCAD.Vector(pos-{spar_w}/2, -chord*{t_max}, 0))
    spar = spar_box.common(shell_solid)
    wing = wing.fuse(spar)

# Add ribs
for i in range({n_ribs}):
    pos = span * (i+1) / ({n_ribs}+1)
    rib_box = Part.makeBox(chord, chord*{t_max}*2, {rib_t}, FreeCAD.Vector(0, -chord*{t_max}, pos-{rib_t}/2))
    rib = rib_box.common(shell_solid)
    wing = wing.fuse(rib)

Part.show(wing)
importerStep.export([doc.Objects[-1]], "{output_dir}/geometry.step")
'''

    def _generate_cantilever_beam(self, geo: Dict, spec: Dict) -> str:
        l = geo.get("length_mm", 500)
        w = geo.get("width_mm", 50)
        h = geo.get("height_mm", 50)
        return f'''import FreeCAD, Part, importerStep
doc = FreeCAD.newDocument("beam")
beam = Part.makeBox({l}, {w}, {h})
Part.show(beam)
importerStep.export([doc.Objects[-1]], "{spec.get('_output_path', 'geometry.step')}")
'''

    def _generate_plate_with_hole(self, geo: Dict, spec: Dict) -> str:
        l = geo.get("length_mm", 200)
        w = geo.get("width_mm", 100)
        t = geo.get("thickness_mm", 10)
        d = geo.get("hole_diameter_mm", 30)
        return f'''import FreeCAD, Part, importerStep
doc = FreeCAD.newDocument("plate")
plate = Part.makeBox({l}, {w}, {t}, FreeCAD.Vector(-{l}/2, -{w}/2, 0))
hole = Part.makeCylinder({d}/2, {t}, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1))
result = plate.cut(hole)
Part.show(result)
importerStep.export([doc.Objects[-1]], "{spec.get('_output_path', 'geometry.step')}")
'''

    def _synthesize_novel(self, spec: Dict) -> str:
        raise NotImplementedError("Novel synthesis requires LLM - configure Gemini API key")

    def _execute_freecad_script(self, script: str, output_path: Path):
        script_file = output_path.parent / "generate_geometry.py"
        # Replace placeholder path
        script = script.replace("geometry.step", str(output_path))
        with open(script_file, "w") as f:
            f.write(script)
        try:
            fc_path = self.config.geometry.freecad_path or "freecadcmd"
            result = subprocess.run([fc_path, str(script_file)], capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                raise RuntimeError(f"FreeCAD failed: {result.stderr}")
        except FileNotFoundError:
            raise RuntimeError("FreeCAD not found. Install FreeCAD or set geometry.freecad_path in config.")
