"""
FeaGPT Batch Worker
Standalone worker process for executing FEA simulations from a job queue.
Used in docker-compose deployment with Redis as the message broker.

Usage: python -m feagpt.batch.worker
"""
import os
import sys
import json
import time
import logging
import signal
from pathlib import Path

logger = logging.getLogger(__name__)

_shutdown = False


def signal_handler(signum, frame):
    global _shutdown
    logger.info("Received signal %s, shutting down gracefully...", signum)
    _shutdown = True


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


class BatchWorker:
    """Worker that pulls simulation jobs from Redis and executes them."""

    def __init__(self):
        self.redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        self.redis_client = None
        self.config = None
        self.pipeline = None

    def initialize(self):
        """Initialize worker with Redis connection and pipeline."""
        try:
            import redis
            self.redis_client = redis.from_url(self.redis_url)
            self.redis_client.ping()
            logger.info("Connected to Redis at %s", self.redis_url)
        except Exception as e:
            logger.error("Failed to connect to Redis: %s", e)
            raise

        from feagpt.config import FeaGPTConfig
        from feagpt.pipeline import GMSAPipeline
        self.config = FeaGPTConfig()
        self.pipeline = GMSAPipeline(self.config)
        self.pipeline.initialize()
        logger.info("Pipeline initialized")

    def run(self):
        """Main worker loop - pull and execute jobs."""
        logger.info("Starting batch worker loop...")

        while not _shutdown:
            try:
                result = self.redis_client.brpop("feagpt:jobs", timeout=5)
                if result is None:
                    continue

                _, job_data = result
                job = json.loads(job_data)
                job_id = job.get("id", "unknown")

                logger.info("Processing job %s", job_id)
                self._update_status(job_id, "running")

                try:
                    description = job.get("description", "")
                    output_dir = job.get("output_dir", "results/job_%s" % job_id)
                    pipe_result = self.pipeline.run(description, output_dir=output_dir)

                    self._update_status(job_id, "completed", {
                        "success": pipe_result.success,
                        "results": pipe_result.to_dict(),
                    })
                    logger.info("Job %s completed: success=%s", job_id, pipe_result.success)

                except Exception as e:
                    logger.error("Job %s failed: %s", job_id, e)
                    self._update_status(job_id, "failed", {"error": str(e)})

            except Exception as e:
                if not _shutdown:
                    logger.error("Worker error: %s", e)
                    time.sleep(1)

        logger.info("Worker shut down gracefully")

    def _update_status(self, job_id, status, data=None):
        """Update job status in Redis."""
        status_data = {"status": status, "updated_at": time.time()}
        if data:
            status_data.update(data)
        try:
            self.redis_client.set(
                "feagpt:status:%s" % job_id,
                json.dumps(status_data),
                ex=86400,
            )
        except Exception as e:
            logger.warning("Failed to update status for %s: %s", job_id, e)


def main():
    """Entry point for batch worker."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    worker = BatchWorker()
    worker.initialize()
    worker.run()


if __name__ == "__main__":
    main()
