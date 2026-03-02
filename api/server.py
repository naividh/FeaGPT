"""
FeaGPT FastAPI Server
Serves FeaGPT as a REST API for Google Cloud Run / Firebase Hosting.

Endpoints:
    POST /analyze      - Submit NL description for FEA analysis
    POST /batch        - Submit parametric study
    GET  /status/{id}  - Check job status
    GET  /results/{id} - Download results
    GET  /health       - Health check
"""

import os
import uuid
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ================================================================
# Pydantic Models
# ================================================================
class AnalyzeRequest(BaseModel):
    description: str = Field(..., description="Natural language engineering description")
    output_dir: Optional[str] = None
    config_overrides: Optional[dict] = None


class BatchRequest(BaseModel):
    description: str = Field(..., description="Natural language engineering description")
    parameter_space: dict = Field(default_factory=dict, description="Parameter ranges")
    output_dir: Optional[str] = None


class JobStatus(BaseModel):
    id: str
    status: str
    created_at: str
    updated_at: Optional[str] = None
    progress: float = 0.0
    result: Optional[dict] = None
    error: Optional[str] = None


# ================================================================
# Application Setup
# ================================================================
app = FastAPI(
    title="FeaGPT API",
    description="End-to-End Agentic AI for Finite Element Analysis",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store (replace with Redis/Firestore in production)
_jobs: dict = {}


def _get_pipeline():
    """Lazy-load the pipeline to avoid heavy imports at module level."""
    from feagpt.config import FeaGPTConfig
    from feagpt.pipeline import GMSAPipeline
    config = FeaGPTConfig()
    pipeline = GMSAPipeline(config)
    pipeline.initialize()
    return pipeline


# ================================================================
# Routes
# ================================================================
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/analyze")
async def analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """Submit a single FEA analysis from natural language description."""
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "id": job_id,
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "description": request.description,
    }
    background_tasks.add_task(_run_analysis, job_id, request)
    return {"job_id": job_id, "status": "queued"}


async def _run_analysis(job_id: str, request: AnalyzeRequest):
    """Execute analysis in background."""
    try:
        _jobs[job_id]["status"] = "running"
        _jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()

        pipeline = _get_pipeline()
        output_dir = request.output_dir or "results/%s" % job_id
        result = await asyncio.to_thread(
            pipeline.run, request.description, output_dir=output_dir
        )

        _jobs[job_id]["status"] = "completed" if result.success else "failed"
        _jobs[job_id]["result"] = result.to_dict()
        _jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()

    except Exception as e:
        logger.error("Analysis failed for job %s: %s", job_id, e)
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)
        _jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()


@app.post("/batch")
async def batch(request: BatchRequest, background_tasks: BackgroundTasks):
    """Submit a parametric batch study."""
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "id": job_id,
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "type": "batch",
        "description": request.description,
        "parameter_space": request.parameter_space,
    }
    background_tasks.add_task(_run_batch, job_id, request)
    return {"job_id": job_id, "status": "queued"}


async def _run_batch(job_id: str, request: BatchRequest):
    """Execute batch study in background."""
    try:
        _jobs[job_id]["status"] = "running"
        _jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()

        pipeline = _get_pipeline()
        output_dir = request.output_dir or "results/batch_%s" % job_id
        results = await asyncio.to_thread(
            pipeline.run_batch, request.description, output_dir=output_dir
        )

        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["result"] = {
            "total": len(results),
            "successful": sum(1 for r in results if r.success),
            "results": [r.to_dict() for r in results],
        }
        _jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()

    except Exception as e:
        logger.error("Batch failed for job %s: %s", job_id, e)
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)
        _jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    """Check job status."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = _jobs[job_id]
    return JobStatus(
        id=job["id"],
        status=job["status"],
        created_at=job["created_at"],
        updated_at=job.get("updated_at"),
        result=job.get("result"),
        error=job.get("error"),
    )


@app.get("/results/{job_id}")
async def get_results(job_id: str):
    """Download results for a completed job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = _jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not yet completed")
    return JSONResponse(content=job.get("result", {}))
