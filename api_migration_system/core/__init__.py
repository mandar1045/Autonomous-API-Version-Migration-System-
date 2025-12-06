"""
Core module for the Autonomous API Version Migration System.
"""

from .api_diff_analyzer import APIDiffAnalyzer
from .semantic_mapper import SemanticMapper
from .transformation_engine import TransformationEngine

__all__ = [
    "APIDiffAnalyzer",
    "SemanticMapper",
    "TransformationEngine"
]