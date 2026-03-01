"""
FeaGPT: End-to-End Agentic AI for Finite Element Analysis

A natural language-driven framework that automates the complete FEA workflow
from geometry creation through mesh generation, simulation, to result analysis.
"""

__version__ = "0.1.0"
__author__ = "FeaGPT Team"

from feagpt.pipeline import GMSAPipeline
from feagpt.config import FeaGPTConfig

__all__ = ["GMSAPipeline", "FeaGPTConfig"]
