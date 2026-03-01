#!/bin/bash
# FeaGPT Local Development Setup Script
# Installs all dependencies for local development and testing.
#
# Supports: Ubuntu/Debian, macOS (with Homebrew)
# Usage: chmod +x deploy/setup_local.sh && ./deploy/setup_local.sh

set -euo pipefail

echo "========================================="
echo "  FeaGPT Local Setup"
echo "========================================="

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     PLATFORM=Linux;;
        Darwin*)    PLATFORM=Mac;;
            *)          echo "Unsupported OS: ${OS}"; exit 1;;
            esac
            echo "Platform: ${PLATFORM}"

            # Step 1: System dependencies
            echo ""
            echo "[1/5] Installing system dependencies..."
            if [ "${PLATFORM}" = "Linux" ]; then
                sudo apt-get update
                    sudo apt-get install -y \
                            python3.11 python3.11-venv python3.11-dev \
                                    gmsh \
                                            calculix-ccx \
                                                    freecad \
                                                            libglu1-mesa \
                                                                    git curl wget
                                                                    elif [ "${PLATFORM}" = "Mac" ]; then
                                                                        brew install python@3.11 gmsh
                                                                            # CalculiX via conda or manual build
                                                                                echo "NOTE: CalculiX on macOS - install via conda:"
                                                                                    echo "  conda install -c conda-forge calculix"
                                                                                        echo "NOTE: FreeCAD on macOS - download from freecad.org"
                                                                                        fi

                                                                                        # Step 2: Python virtual environment
                                                                                        echo ""
                                                                                        echo "[2/5] Setting up Python virtual environment..."
                                                                                        python3.11 -m venv .venv
                                                                                        source .venv/bin/activate
                                                                                        pip install --upgrade pip setuptools wheel

                                                                                        # Step 3: Python dependencies
                                                                                        echo ""
                                                                                        echo "[3/5] Installing Python dependencies..."
                                                                                        pip install -e ".[dev]"
                                                                                        pip install pytest pytest-cov flake8 black isort

                                                                                        # Step 4: Verify installations
                                                                                        echo ""
                                                                                        echo "[4/5] Verifying installations..."
                                                                                        echo -n "  Python: "; python --version
                                                                                        echo -n "  Gmsh: "; python -c "import gmsh; print(gmsh.__version__)" 2>/dev/null || echo "NOT FOUND"
                                                                                        echo -n "  CalculiX: "; ccx -v 2>&1 | head -1 || echo "NOT FOUND"
                                                                                        echo -n "  sentence-transformers: "; python -c "import sentence_transformers; print(sentence_transformers.__version__)" 2>/dev/null || echo "NOT FOUND"
                                                                                        echo -n "  numpy: "; python -c "import numpy; print(numpy.__version__)"
                                                                                        echo -n "  scipy: "; python -c "import scipy; print(scipy.__version__)"

                                                                                        # Step 5: Run tests
                                                                                        echo ""
                                                                                        echo "[5/5] Running tests..."
                                                                                        python -m pytest tests/ -v --tb=short 2>&1 | tail -20

                                                                                        echo ""
                                                                                        echo "========================================="
                                                                                        echo "  Setup Complete!"
                                                                                        echo "========================================="
                                                                                        echo ""
                                                                                        echo "Activate environment: source .venv/bin/activate"
                                                                                        echo "Run single analysis:  python main.py run 'Analyze a cantilever beam'"
                                                                                        echo "Run tests:           pytest tests/ -v"
                                                                                        echo "Run with Docker:     docker build -t feagpt . && docker run -it feagpt"
                                                                                        echo ""
                                                                                        echo "Set your Gemini API key:"
                                                                                        echo "  export GEMINI_API_KEY=your-key-here"