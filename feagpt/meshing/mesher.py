"""
Adaptive Mesh Generator for FeaGPT.
Implements Eqs. 4-5 (distance-based gradation) using Gmsh.
"""
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

MESH_LEVELS = {
    "ultra_fine": {"min_size": 0.2, "max_size": 1.0},
    "fine": {"min_size": 0.5, "max_size": 3.0},
    "medium": {"min_size": 2.0, "max_size": 8.0},
    "coarse": {"min_size": 5.0, "max_size": 20.0},
}


class AdaptiveMesher:
    """Gmsh-based adaptive mesh generation with physics-aware refinement."""

    def __init__(self, config):
        self.config = config
        self._gmsh = None

    def _init_gmsh(self):
        if self._gmsh is not None:
            return
        try:
            import gmsh
            self._gmsh = gmsh
            gmsh.initialize()
            gmsh.option.setNumber("General.Terminal", 0)
        except ImportError:
            raise RuntimeError("Gmsh not installed. Run: pip install gmsh")

    def mesh(self, geometry_path: Path, spec: Dict, output_dir: Path) -> Path:
        self._init_gmsh()
        gmsh = self._gmsh
        gmsh.clear()

        output_path = output_dir / "mesh.inp"
        mesh_spec = spec.get("mesh", {})
        level = mesh_spec.get("density", "fine")
        sizes = MESH_LEVELS.get(level, MESH_LEVELS["fine"])
        hmin = sizes["min_size"]
        hmax = sizes["max_size"]

        logger.info(f"Meshing with level={level}, hmin={hmin}, hmax={hmax}")

        # Import geometry
        gmsh.model.occ.importShapes(str(geometry_path))
        gmsh.model.occ.synchronize()

        # Set global mesh sizes
        gmsh.option.setNumber("Mesh.MeshSizeMin", hmin)
        gmsh.option.setNumber("Mesh.MeshSizeMax", hmax)
        gmsh.option.setNumber("Mesh.Algorithm3D", 1)  # Delaunay

        # Apply adaptive refinement based on spec
        refinement_zones = mesh_spec.get("refinement_zones", [])
        self._apply_refinement(refinement_zones, hmin, hmax)

        # Create physical groups from semantic locations
        self._create_physical_groups(spec)

        # Generate 3D mesh
        elem_type = mesh_spec.get("element_type", "C3D10")
        if "10" in elem_type or "tet" in elem_type.lower():
            gmsh.option.setNumber("Mesh.ElementOrder", 2)
        gmsh.model.mesh.generate(3)

        # Get mesh statistics
        node_tags, _, _ = gmsh.model.mesh.getNodes()
        elem_types, elem_tags, _ = gmsh.model.mesh.getElements(3)
        n_nodes = len(node_tags)
        n_elems = sum(len(t) for t in elem_tags)
        logger.info(f"Mesh generated: {n_nodes} nodes, {n_elems} elements")

        # Export to CalculiX INP format
        gmsh.write(str(output_path))
        gmsh.clear()

        logger.info(f"Mesh saved: {output_path}")
        return output_path

    def _apply_refinement(self, zones: List[str], hmin: float, hmax: float):
        gmsh = self._gmsh
        if not zones:
            return

        # Distance-based refinement (Eq. 4-5 in paper)
        field_id = 1
        for zone in zones:
            # Get surfaces matching zone description
            surfaces = gmsh.model.occ.getEntities(2)
            if not surfaces:
                continue

            # Apply distance field from all surfaces
            gmsh.model.mesh.field.add("Distance", field_id)
            surf_tags = [s[1] for s in surfaces[:3]]  # First 3 surfaces as refinement targets
            gmsh.model.mesh.field.setNumbers(field_id, "SurfacesList", surf_tags)

            # Threshold field (Eq. 5)
            field_id += 1
            dmin = 2 * hmin
            dmax = 10 * hmax
            gmsh.model.mesh.field.add("Threshold", field_id)
            gmsh.model.mesh.field.setNumber(field_id, "InField", field_id - 1)
            gmsh.model.mesh.field.setNumber(field_id, "SizeMin", hmin)
            gmsh.model.mesh.field.setNumber(field_id, "SizeMax", hmax)
            gmsh.model.mesh.field.setNumber(field_id, "DistMin", dmin)
            gmsh.model.mesh.field.setNumber(field_id, "DistMax", dmax)
            field_id += 1

        # Set the background field
        if field_id > 1:
            gmsh.model.mesh.field.add("Min", field_id)
            gmsh.model.mesh.field.setNumbers(field_id, "FieldsList", list(range(2, field_id, 2)))
            gmsh.model.mesh.field.setAsBackgroundMesh(field_id)

    def _create_physical_groups(self, spec: Dict):
        gmsh = self._gmsh
        bcs = spec.get("boundary_conditions", [])
        loads = spec.get("loads", [])
        volumes = gmsh.model.occ.getEntities(3)
        surfaces = gmsh.model.occ.getEntities(2)

        # Create Eall for all elements
        if volumes:
            gmsh.model.addPhysicalGroup(3, [v[1] for v in volumes], name="Eall")

        # Create surface groups for BCs and loads
        if surfaces:
            for i, bc in enumerate(bcs):
                loc = bc.get("location", f"bc_{i}").replace(" ", "_")
                # Assign first surface as BC
                if i < len(surfaces):
                    gmsh.model.addPhysicalGroup(2, [surfaces[i][1]], name=loc)

            for i, load in enumerate(loads):
                loc = load.get("location", f"load_{i}").replace(" ", "_")
                idx = len(bcs) + i
                if idx < len(surfaces):
                    gmsh.model.addPhysicalGroup(2, [surfaces[idx][1]], name=loc)
