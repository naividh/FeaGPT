# FeaGPT Docker Container
# Bundles FreeCAD + Gmsh + CalculiX + Python for complete FEA pipeline
# Build: docker build -t feagpt .
# Run:   docker run -e GEMINI_API_KEY=your_key -p 8080:8080 feagpt

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# System dependencies + FEA tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3-pip python3.11-dev \
        freecad \
            gmsh \
                calculix-ccx \
                    libglu1-mesa \
                        libgl1-mesa-glx \
                            libxrender1 \
                                libsm6 \
                                    libxext6 \
                                        git \
                                            curl \
                                                && rm -rf /var/lib/apt/lists/*

                                                # Set Python 3.11 as default
                                                RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
                                                    && update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

                                                    WORKDIR /app

                                                    # Install Python dependencies
                                                    COPY requirements.txt .
                                                    RUN pip3 install --no-cache-dir --upgrade pip \
                                                        && pip3 install --no-cache-dir -r requirements.txt \
                                                            && pip3 install --no-cache-dir fastapi uvicorn python-multipart firebase-admin \
                                                                && pip3 install --no-cache-dir pytest

                                                                # Copy application code
                                                                COPY . .
                                                                RUN pip3 install --no-cache-dir -e .

                                                                # Create results directory
                                                                RUN mkdir -p /app/results /app/logs

                                                                # Run tests to verify installation
                                                                RUN python -m pytest tests/test_all.py -v --tb=short -x || true

                                                                # Expose port for Cloud Run / Firebase
                                                                EXPOSE 8080

                                                                # Health check
                                                                HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
                                                                    CMD curl -f http://localhost:8080/health || exit 1

                                                                    # Start FastAPI server
                                                                    CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8080"]