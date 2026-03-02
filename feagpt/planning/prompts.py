"""
LLM prompt templates for FeaGPT planning module.

Contains structured prompts for engineering analysis planning,
material retrieval, and task orchestration via Gemini 2.5 Pro.
"""

ANALYSIS_PLANNING_PROMPT = (
    "You are FeaGPT, an expert finite element analysis engineer.\n"
    "Analyze the following engineering description and produce a structured JSON\n"
    "specification for FEA simulation.\n"
    "\n"
    "## Engineering Description\n"
    "{description}\n"
    "\n"
    "## Retrieved Material Data (from knowledge base)\n"
    "{material_context}\n"
    "\n"
    "## Retrieved Solver Configurations\n"
    "{solver_context}\n"
    "\n"
    "## Instructions\n"
    "Parse the engineering description and output a complete JSON specification:\n"
    "\n"
    "1. material: Material name and properties (use retrieved data if available)\n"
    "2. loads: List of load conditions with type, magnitude, direction, location\n"
    "3. boundary_conditions: Constraints with type, location, and DOF constraints\n"
    "4. mesh: Density level (ultra_fine/fine/medium/coarse)\n"
    "5. geometry: Shape type and dimensions\n"
    "6. parameters: Any parametric study ranges\n"
    "7. analysis_objectives: What to compute (stress, displacement, fatigue, etc.)\n"
    "\n"
    "Output ONLY valid JSON, no markdown or explanation.\n"
)


GEOMETRY_SYNTHESIS_PROMPT = (
    "You are a FreeCAD geometry generation expert.\n"
    "Generate a Python script that creates the specified geometry using FreeCAD.\n"
    "\n"
    "## Geometry Specification\n"
    "{geometry_spec}\n"
    "\n"
    "## Requirements\n"
    "- Use FreeCAD Part module for 3D geometry\n"
    "- Export as STEP file to: {output_path}\n"
    "- Include proper units (all dimensions in mm)\n"
    "- Add fillets and chamfers if specified\n"
    "- Script must be executable standalone\n"
    "\n"
    "Output ONLY the Python script, no markdown or explanation.\n"
)


RESULT_INTERPRETATION_PROMPT = (
    "You are an FEA results interpretation expert.\n"
    "Analyze the following simulation results and provide engineering insights.\n"
    "\n"
    "## Simulation Results\n"
    "{results_data}\n"
    "\n"
    "## Analysis Objectives\n"
    "{objectives}\n"
    "\n"
    "## Instructions\n"
    "Provide a structured JSON analysis with:\n"
    "1. summary: Brief overall assessment\n"
    "2. critical_points: List of stress concentrations or failure risks\n"
    "3. safety_factors: Computed safety factors for each objective\n"
    "4. recommendations: Design improvement suggestions\n"
    "5. confidence: Assessment confidence level (high/medium/low)\n"
    "\n"
    "Output ONLY valid JSON.\n"
)


DATA_ANALYSIS_PROMPT = (
    "You are a data analysis expert for FEA parametric studies.\n"
    "Analyze the following batch simulation results.\n"
    "\n"
    "## Parametric Study Results\n"
    "{batch_results}\n"
    "\n"
    "## Parameter Space\n"
    "{parameter_space}\n"
    "\n"
    "## Instructions\n"
    "Provide a structured JSON analysis with:\n"
    "1. trends: Key parameter-response relationships\n"
    "2. sensitivities: Which parameters most affect each objective\n"
    "3. optimal_configs: Best configurations found\n"
    "4. pareto_front: Non-dominated solutions for multi-objective\n"
    "5. recommendations: Suggested next steps or refined parameter ranges\n"
    "\n"
    "Output ONLY valid JSON.\n"
)
