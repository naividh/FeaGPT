"""
Geometry Generator for FeaGPT.

Implements knowledge-augmented and novel synthesis modes (Eq. 2-3 in paper).
"""
import logging
import subprocess
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
        """Generate geometry from specification."""
        geo_spec = spec.get("geometry", {})
        geo_type = geo_spec.get("type", "unknown")
        output_path = output_dir / "geometry.step"

        if geo_type in self._generators:
            logger.info(f"Knowledge-augmented generation: {geo_type}")
            script = self._generators[geo_type](
                geo_spec, spec, output_path
            )
        else:
            logger.info(f"Novel synthesis mode for: {geo_type}")
            script = self._synthesize_novel(spec)

        self._execute_freecad_script(script, output_path)

        if not output_path.exists():
            raise FileNotFoundError(
                f"Geometry not generated: {output_path}"
            )

        logger.info(f"Geometry saved: {output_path}")
        return output_path

    def _generate_naca_wing(
        self, geo: Dict, spec: Dict, out_path: Path
    ) -> str:
        """Generate NACA wing geometry script."""
        code = geo.get("naca_code", "0012")
        chord = geo.get("chord_mm", 200.0)
        span = geo.get("span_mm", 200.0)
        m = int(code[0]) / 100.0
        p_val = int(code[1]) / 10.0
        t_max = int(code[2:]) / 100.0
        out_str = str(out_path)

        script_lines = [
            "import FreeCAD, Part, importerStep",
            "import numpy as np",
            "",
            'doc = FreeCAD.newDocument("NACAwing")',
            "",
            f"chord = {chord}",
            f"span = {span}",
            f"t_max = {t_max}",
            f"m = {m}",
            f"p = {p_val}",
            "",
            "n_pts = 100",
            "import numpy as np",
            "x_pts = (1 - np.cos(np.linspace(0, np.pi, n_pts))) / 2",
            "",
            "def naca_thickness(x):",
            "    return (t_max/0.2) * (0.2969*np.sqrt(x) - 0.1260*x - 0.3516*x**2 + 0.2843*x**3 - 0.1015*x**4)",
            "",
            "def naca_camber(x):",
            "    if p == 0: return 0.0",
            "    if x < p: return (m / p**2) * (2*p*x - x**2)",
            "    return (m / (1-p)**2) * ((1-2*p) + 2*p*x - x**2)",
            "",
            "upper_pts = []",
            "lower_pts = []",
            "for x in x_pts:",
            "    yc = naca_camber(x)",
            "    yt = naca_thickness(x)",
            "    upper_pts.append(FreeCAD.Vector(x*chord, (yc+yt)*chord, 0))",
            "    lower_pts.append(FreeCAD.Vector(x*chord, (yc-yt)*chord, 0))",
            "",
            "upper_wire = Part.makePolygon(upper_pts)",
            "lower_wire = Part.makePolygon(list(reversed(lower_pts)))",
            "profile_wire = Part.Wire([upper_wire, lower_wire])",
            "profile_face = Part.Face(profile_wire)",
            "shell_solid = profile_face.extrude(FreeCAD.Vector(0, 0, span))",
            "Part.show(shell_solid)",
            f'importerStep.export([doc.Objects[-1]], "{out_str}")',
        ]
        return "\n".join(script_lines)

    def _generate_cantilever_beam(
        self, geo: Dict, spec: Dict, out_path: Path
    ) -> str:
        """Generate cantilever beam geometry script."""
        length = geo.get("length_mm", 500)
        width = geo.get("width_mm", 50)
        height = geo.get("height_mm", 50)
        out_str = str(out_path)

        script_lines = [
            "import FreeCAD, Part, importerStep",
            'doc = FreeCAD.newDocument("beam")',
            f"beam = Part.makeBox({length}, {width}, {height})",
            "Part.show(beam)",
            f'importerStep.export([doc.Objects[-1]], "{out_str}")',
        ]
        return "\n".join(script_lines)

    def _generate_plate_with_hole(
        self, geo: Dict, spec: Dict, out_path: Path
    ) -> str:
        """Generate plate with hole geometry script."""
        length = geo.get("length_mm", 200)
        width = geo.get("width_mm", 100)
        thick = geo.get("thickness_mm", 10)
        diameter = geo.get("hole_diameter_mm", 30)
        out_str = str(out_path)

        script_lines = [
            "import FreeCAD, Part, importerStep",
            'doc = FreeCAD.newDocument("plate")',
            f"plate = Part.makeBox({length}, {width}, {thick},",
            f"    FreeCAD.Vector(-{length}/2, -{width}/2, 0))",
            f"hole = Part.makeCylinder({diameter}/2, {thick},",
            "    FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1))",
            "result = plate.cut(hole)",
            "Part.show(result)",
            f'importerStep.export([doc.Objects[-1]], "{out_str}")',
        ]
        return "\n".join(script_lines)

    def _synthesize_novel(self, spec: Dict) -> str:
        """Novel synthesis requires LLM integration."""
        raise NotImplementedError(
            "Novel synthesis requires LLM - configure Gemini API key"
        )

    def _execute_freecad_script(
        self, script: str, output_path: Path
    ):
        """Execute FreeCAD script to generate geometry."""
        script_file = output_path.parent / "generate_geometry.py"

        with open(script_file, "w") as f:
            f.write(script)

        try:
            fc_path = (
                self.config.geometry.freecad_path or "freecadcmd"
            )
            result = subprocess.run(
                [fc_path, str(script_file)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"FreeCAD failed: {result.stderr}"
                )
        except FileNotFoundError:
            raise RuntimeError(
                "FreeCAD not found. Install FreeCAD or set "
                "geometry.freecad_path in config."
            )
