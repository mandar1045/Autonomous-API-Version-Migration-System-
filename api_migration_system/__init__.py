"""
Autonomous API Version Migration System with Formal Verification

This system automatically migrates code between API versions while generating
mathematical proof certificates that the migration preserves original behavior.
"""

__version__ = "0.1.0"
__author__ = "Autonomous Migration System"

from .core.api_diff_analyzer import APIDiffAnalyzer
from .core.semantic_mapper import SemanticMapper
from .core.transformation_engine import TransformationEngine

__all__ = [
    "APIDiffAnalyzer",
    "SemanticMapper", 
    "TransformationEngine"
]