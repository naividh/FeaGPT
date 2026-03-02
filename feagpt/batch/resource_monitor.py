"""
Dynamic resource allocation for FeaGPT batch processing.
Implements Equation (7): Adaptive batch sizing based on available resources.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ResourceMonitor:
    """
    Monitors system resources and computes optimal batch sizes.
    Implements Equation (7):
        B_size = min(M_available / M_per_case, N_cores, B_max)
    """

    def __init__(self, memory_per_case_mb: int = 512, max_batch_size: int = 500):
        self.memory_per_case_mb = memory_per_case_mb
        self.max_batch_size = max_batch_size

    def get_available_memory_mb(self) -> float:
        """Get available system memory in MB."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            return mem.available / (1024 * 1024)
        except ImportError:
            logger.warning("psutil not available, estimating 8GB")
            return 8192.0

    def get_cpu_count(self) -> int:
        """Get available CPU core count."""
        try:
            return len(os.sched_getaffinity(0))
        except AttributeError:
            return os.cpu_count() or 4

    def compute_optimal_batch_size(self) -> int:
        """
        Compute optimal batch size using Equation (7):
        B_size = min(M_available / M_per_case, N_cores, B_max)
        """
        available_mb = self.get_available_memory_mb()
        memory_limited = int(available_mb / max(self.memory_per_case_mb, 1))
        cpu_limited = self.get_cpu_count()
        optimal = min(memory_limited, cpu_limited, self.max_batch_size)
        return max(optimal, 1)
