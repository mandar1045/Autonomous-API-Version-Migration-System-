# API Migration System
"""
Autonomous API Version Migration System
"""

from .core.api_diff_analyzer import APIDiffAnalyzer, APIEntity, APIDiff, ChangeType
from .core.transformation_engine import TransformationEngine

__version__ = "1.0.0"
__all__ = [
    'APIDiffAnalyzer',
    'APIEntity',
    'APIDiff',
    'ChangeType',
    'TransformationEngine'
]