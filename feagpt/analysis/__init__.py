"""FeaGPT analysis package."""
from feagpt.analysis.analyzer import ResultsAnalyzer, FEAResults
from feagpt.analysis.fatigue import FatigueAnalyzer
from feagpt.analysis.pareto import ParetoAnalyzer

# Lazy imports for modules with heavy dependencies (pandas, scipy, sklearn)
# Use: from feagpt.analysis.sensitivity import SensitivityAnalyzer
# Use: from feagpt.analysis.surrogate import SurrogateModeler
