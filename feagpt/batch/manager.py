"""
Batch processing manager for FeaGPT.

Orchestrates parallel execution of parametric FEA studies.
"""
import logging
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class BatchManager:
    """
    Manages batch execution of parametric FEA studies.

    Coordinates workers, tracks progress, handles checkpointing.
    """

    def __init__(self, config):
        self.config = config
        self.max_workers = config.batch.max_workers
        self.timeout = config.batch.timeout_per_job
        self.checkpoint_interval = config.batch.checkpoint_interval
        self.output_dir = Path(config.batch.output_dir)
        self.results: List[Dict[str, Any]] = []
        self.failed: List[Dict[str, Any]] = []

    def run(
        self,
        configs: List[Dict[str, Any]],
        pipeline=None,
    ) -> List[Dict[str, Any]]:
        """
        Execute batch of FEA configurations.

        Args:
            configs: List of parameter configurations
            pipeline: FeaGPTPipeline instance

        Returns:
            List of result dicts
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        total = len(configs)
        logger.info(
            f"Starting batch: {total} configs, "
            f"{self.max_workers} workers"
        )

        start_time = time.time()
        completed = 0

        with ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            futures = {}
            for i, cfg in enumerate(configs):
                future = executor.submit(
                    self._run_single, i, cfg, pipeline
                )
                futures[future] = i

            for future in as_completed(futures):
                idx = futures[future]
                try:
                    result = future.result(timeout=self.timeout)
                    self.results.append(result)
                    completed += 1
                except Exception as e:
                    logger.error(f"Config {idx} failed: {e}")
                    self.failed.append({
                        "index": idx,
                        "config": configs[idx],
                        "error": str(e),
                    })

                # Checkpoint
                if completed % self.checkpoint_interval == 0:
                    self._save_checkpoint()
                    logger.info(
                        f"Progress: {completed}/{total} "
                        f"({completed/total:.0%})"
                    )

        elapsed = time.time() - start_time
        logger.info(
            f"Batch complete: {completed}/{total} in "
            f"{elapsed:.1f}s ({len(self.failed)} failed)"
        )

        self._save_results()
        return self.results

    def _run_single(
        self,
        index: int,
        config: Dict[str, Any],
        pipeline=None,
    ) -> Dict[str, Any]:
        """Run a single configuration."""
        job_dir = self.output_dir / f"job_{index:04d}"
        job_dir.mkdir(parents=True, exist_ok=True)

        result = {
            "index": index,
            "config": config,
            "status": "pending",
        }

        try:
            if pipeline is not None:
                output = pipeline.execute(config, job_dir)
                result["output"] = output
                result["status"] = "success"
            else:
                result["status"] = "skipped"
                result["message"] = "No pipeline provided"
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)

        # Save individual result
        result_file = job_dir / "result.json"
        with open(result_file, "w") as f:
            json.dump(result, f, indent=2, default=str)

        return result

    def _save_checkpoint(self):
        """Save checkpoint of current results."""
        ckpt_file = self.output_dir / "checkpoint.json"
        with open(ckpt_file, "w") as f:
            json.dump({
                "completed": len(self.results),
                "failed": len(self.failed),
                "results": self.results,
            }, f, indent=2, default=str)

    def _save_results(self):
        """Save final results summary."""
        summary_file = self.output_dir / "summary.json"
        with open(summary_file, "w") as f:
            json.dump({
                "total": len(self.results) + len(self.failed),
                "completed": len(self.results),
                "failed": len(self.failed),
                "results": self.results,
                "failures": self.failed,
            }, f, indent=2, default=str)
        logger.info(f"Results saved: {summary_file}")

    def load_checkpoint(self) -> Optional[Dict]:
        """Load checkpoint if it exists."""
        ckpt_file = self.output_dir / "checkpoint.json"
        if ckpt_file.exists():
            with open(ckpt_file, "r") as f:
                return json.load(f)
        return None
