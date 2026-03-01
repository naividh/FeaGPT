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
            logger.warning("psutil not installed, using conservative estimate")
            return 4096  # 4GB default

    def get_cpu_count(self) -> int:
              """Get available CPU core count."""
              try:
                            import psutil
                            return psutil.cpu_count(logical=False) or os.cpu_count() or 4
except ImportError:
            return os.cpu_count() or 4

    def compute_optimal_batch_size(self) -> int:
              """
                      Compute optimal batch size using Equation (7):
                                  B_size = min(M_available / M_per_case, N_cores, B_max)
                                          """
              available_mb = self.get_available_memory_mb()
              n_cor
