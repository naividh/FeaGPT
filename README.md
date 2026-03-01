# FeaGPT

**An End-to-End Agentic AI for Finite Element Analysis**

FeaGPT is a natural language-driven framework that automates the complete FEA workflow from geometry creation through mesh generation, simulation, and result analysis. It transforms engineering specifications into validated computational results without manual intervention.

Based on the research paper: *"FeaGPT: an End-to-End agentic-AI for Finite Element Analysis"* (arXiv:2510.21993)

## Features

- **Natural Language Interface**: Describe your analysis in plain English
- **GMSA Pipeline**: Geometry -> Mesh -> Simulation -> Analysis, fully automated
- **Knowledge-Augmented Generation**: Leverages validated engineering patterns (NACA airfoils, standard components)
- **Adaptive Meshing**: Physics-aware mesh refinement using Gmsh
- **CalculiX Integration**: Automatic solver configuration and result extraction
- **Parametric Studies**: Batch processing of hundreds of configurations
- **Multi-Objective Analysis**: Pareto optimization, sensitivity analysis, S-N fatigue assessment

## Architecture

```
Natural Language Input
        |
          [Analysis Planner] --- Knowledge Base (RAG)
                  |
                    [Geometry Generator] --- FreeCAD
                            |
                              [Adaptive Mesher] --- Gmsh
                                      |
                                        [FEA Simulator] --- CalculiX
                                                |
                                                  [Data Analyzer] --- Pareto / Sensitivity / Fatigue
                                                          |
                                                            Engineering Insights
                                                            ```

                                                            ## Quick Start

                                                            ### Installation

                                                            ```bash
                                                            # Clone the repository
                                                            git clone https://github.com/naividh/FeaGPT.git
                                                            cd FeaGPT

                                                            # Install dependencies
                                                            pip install -r requirements.txt

                                                            # Install the package
                                                            pip install -e .
                                                            ```

                                                            ### Prerequisites

                                                            - Python >= 3.10
                                                            - FreeCAD (for geometry generation)
                                                            - Gmsh >= 4.11 (included via pip)
                                                            - CalculiX >= 2.20 (for FEA solver)
                                                            - Gemini API key (for LLM planning)

                                                            ### Usage

                                                            ```bash
                                                            # Set your Gemini API key
                                                            export GEMINI_API_KEY="your-api-key-here"

                                                            # Run a single analysis
                                                            feagpt run "Analyze a cantilever beam, 500mm long, 50mm square cross-section, steel, with 1000N downward force at the free end"

                                                            # Interactive mode
                                                            feagpt interactive

                                                            # Parametric study
                                                            feagpt run "Analyze a NACA4412 wing structure for aerospace application. Wing dimensions: 200mm chord, 200mm span. Vary the shell thickness from 1.0 to 2.0mm in 0.5mm steps, spar width from 1.0 to 2.0mm in 0.2mm steps."
                                                            ```

                                                            ### Python API

                                                            ```python
                                                            from feagpt import GMSAPipeline, FeaGPTConfig

                                                            config = FeaGPTConfig("config.yaml")
                                                            pipeline = GMSAPipeline(config)

                                                            result = pipeline.run(
                                                                "Analyze a plate with a 30mm central hole under tensile loading. "
                                                                    "Plate dimensions: 200x100x10mm, aluminum 6061-T6."
                                                                    )

                                                                    print(f"Max stress: {result.analysis_data['max_von_mises_stress']:.1f} Pa")
                                                                    print(f"Safety factor: {result.analysis_data['safety_factor']:.2f}")
                                                                    ```

                                                                    ## Project Structure

                                                                    ```
                                                                    feagpt/
                                                                      __init__.py          # Package initialization
                                                                        config.py            # Configuration management
                                                                          pipeline.py          # GMSA pipeline orchestrator
                                                                            planning/            # NL analysis planning + knowledge base
                                                                              geometry/            # Geometry generation (NACA, plates, beams)
                                                                                meshing/             # Adaptive mesh generation (Gmsh)
                                                                                  simulation/          # CalculiX FEA integration
                                                                                    analysis/            # Data analysis (Pareto, sensitivity, fatigue)
                                                                                      batch/               # Batch processing + parameter space
                                                                                      ```

                                                                                      ## Key Algorithms

                                                                                      - **Equation (1)**: Cosine similarity for knowledge base retrieval
                                                                                      - **Equation (2)**: Strategy selection (knowledge-augmented vs novel synthesis)
                                                                                      - **Equation (3)**: NACA 4-digit thickness distribution
                                                                                      - **Equations (4-5)**: Distance-based adaptive mesh gradation
                                                                                      - **Equation (6)**: Cartesian product parameter space expansion
                                                                                      - **Equation (7)**: Dynamic resource allocation for batch processing

                                                                                      ## License

                                                                                      MIT License - see [LICENSE](LICENSE) for details.

                                                                                      ## Citation

                                                                                      ```bibtex
                                                                                      @article{qi2025feagpt,
                                                                                        title={FeaGPT: an End-to-End agentic-AI for Finite Element Analysis},
                                                                                          author={Qi, Yupeng and Xu, Ran and Chu, Xu},
                                                                                            journal={arXiv preprint arXiv:2510.21993},
                                                                                              year={2025}
                                                                                              }
                                                                                              ```