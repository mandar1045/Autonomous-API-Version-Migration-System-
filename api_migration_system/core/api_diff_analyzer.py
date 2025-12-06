"""
API Diff Analyzer - Module 1

Analyzes Python code to detect API changes between versions using AST parsing.
Generates structured representations of API signatures and identifies modifications.
"""

import ast
import astunparse
import re
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Types of API changes that can be detected."""
    PARAMETER_ADDED = "parameter_added"
    PARAMETER_REMOVED = "parameter_removed"
    PARAMETER_RENAMED = "parameter_renamed"
    PARAMETER_TYPE_CHANGED = "parameter_type_changed"
    RETURN_TYPE_CHANGED = "return_type_changed"
    METHOD_DEPRECATED = "method_deprecated"
    SIGNATURE_CHANGED = "signature_changed"


@dataclass
class APIEntity:
    """Represents an API entity (function, method, class)."""
    name: str
    module: str
    signature: Dict[str, Any]
    docstring: Optional[str] = None
    source_location: Optional[str] = None
    ast_node: Optional[ast.AST] = None
    
    def __hash__(self):
        return hash((self.name, self.module))


@dataclass
class APIDiff:
    """Represents a detected difference between two API versions."""
    change_type: ChangeType
    old_entity: Optional[APIEntity] = None
    new_entity: Optional[APIEntity] = None
    description: str = ""
    confidence: float = 1.0
    impact_analysis: Dict[str, Any] = field(default_factory=dict)


class APIDiffAnalyzer:
    """
    Advanced API diff analyzer that uses AST parsing to detect structural changes.
    
    This is the foundational component that enables automated API migration by:
    1. Parsing Python code into AST representations
    2. Extracting API signatures and metadata
    3. Comparing versions to identify changes
    4. Generating structured diff information
    """
    
    def __init__(self, include_builtin_apis: bool = False):
        """
        Initialize the API Diff Analyzer.
        
        Args:
            include_builtin_apis: Whether to analyze builtin library APIs
        """
        self.include_builtin_apis = include_builtin_apis
        self.builtin_modules = {'requests', 'json', 'os', 'sys', 're', 'datetime'}
        
    def analyze_file(self, file_path: str, target_module: Optional[str] = None) -> List[APIEntity]:
        """
        Analyze a Python file to extract API entities.
        
        Args:
            file_path: Path to the Python file to analyze
            target_module: Specific module to focus on (e.g., 'requests')
            
        Returns:
            List of APIEntity objects found in the file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            return self.analyze_source_code(source_code, target_module)
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return []
    
    def analyze_source_code(self, source_code: str, target_module: Optional[str] = None) -> List[APIEntity]:
        """
        Analyze Python source code to extract API entities.
        
        Args:
            source_code: Python source code to analyze
            target_module: Specific module to focus on
            
        Returns:
            List of APIEntity objects found in the source
        """
        try:
            tree = ast.parse(source_code)
            entities = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    entity = self._extract_function_entity(node, source_code)
                    if self._should_include_entity(entity, target_module):
                        entities.append(entity)
                elif isinstance(node, ast.ClassDef):
                    for child in node.body:
                        if isinstance(child, ast.FunctionDef):
                            method_entity = self._extract_method_entity(child, node.name, source_code)
                            if self._should_include_entity(method_entity, target_module):
                                entities.append(method_entity)
            
            return entities
        except Exception as e:
            logger.error(f"Error parsing source code: {e}")
            return []
    
    def compare_versions(self, old_entities: List[APIEntity], new_entities: List[APIEntity]) -> List[APIDiff]:
        """
        Compare two sets of API entities to detect changes.
        
        Args:
            old_entities: API entities from the old version
            new_entities: API entities from the new version
            
        Returns:
            List of detected differences
        """
        old_dict = {self._entity_key(entity): entity for entity in old_entities}
        new_dict = {self._entity_key(entity): entity for entity in new_entities}
        
        diffs = []
        
        # Find removed/added entities
        for key in old_dict:
            if key not in new_dict:
                diffs.append(APIDiff(
                    change_type=ChangeType.METHOD_DEPRECATED,
                    old_entity=old_dict[key],
                    description=f"API entity {key} was removed or deprecated"
                ))
        
        for key in new_dict:
            if key not in old_dict:
                # Check if it's a new API or renamed version
                similar_key = self._find_similar_entity(key, old_dict)
                if similar_key:
                    diffs.append(APIDiff(
                        change_type=ChangeType.PARAMETER_RENAMED,
                        old_entity=old_dict[similar_key],
                        new_entity=new_dict[key],
                        description=f"API entity renamed from {similar_key} to {key}"
                    ))
                else:
                    diffs.append(APIDiff(
                        change_type=ChangeType.SIGNATURE_CHANGED,
                        new_entity=new_dict[key],
                        description=f"New API entity {key} was added"
                    ))
        
        # Find modified entities
        for key in old_dict:
            if key in new_dict:
                old_entity = old_dict[key]
                new_entity = new_dict[key]
                signature_diff = self._compare_signatures(old_entity, new_entity)
                if signature_diff:
                    diffs.append(APIDiff(
                        change_type=ChangeType.SIGNATURE_CHANGED,
                        old_entity=old_entity,
                        new_entity=new_entity,
                        description=f"Signature changed for {key}",
                        impact_analysis=signature_diff
                    ))
        
        return diffs
    
    def extract_api_usage(self, source_code: str, target_module: str) -> List[Dict[str, Any]]:
        """
        Extract API usage patterns from source code.
        
        Args:
            source_code: Python source code to analyze
            target_module: Module to analyze usage for (e.g., 'requests')
            
        Returns:
            List of API usage patterns found
        """
        try:
            tree = ast.parse(source_code)
            usages = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    usage = self._extract_call_usage(node, source_code, target_module)
                    if usage:
                        usages.append(usage)
            
            return usages
        except Exception as e:
            logger.error(f"Error extracting API usage: {e}")
            return []
    
    def _extract_function_entity(self, node: ast.FunctionDef, source_code: str) -> APIEntity:
        """Extract function entity from AST node."""
        signature = self._extract_signature(node)
        
        return APIEntity(
            name=node.name,
            module="__main__",  # Will be set by caller if needed
            signature=signature,
            docstring=ast.get_docstring(node),
            source_location=self._get_source_location(node, source_code),
            ast_node=node
        )
    
    def _extract_method_entity(self, node: ast.FunctionDef, class_name: str, source_code: str) -> APIEntity:
        """Extract method entity from AST node."""
        signature = self._extract_signature(node)
        
        return APIEntity(
            name=f"{class_name}.{node.name}",
            module="__main__",  # Will be set by caller if needed
            signature=signature,
            docstring=ast.get_docstring(node),
            source_location=self._get_source_location(node, source_code),
            ast_node=node
        )
    
    def _extract_signature(self, node: ast.FunctionDef) -> Dict[str, Any]:
        """Extract function/method signature information."""
        signature = {
            'args': [],
            'defaults': [],
            'vararg': None,
            'kwarg': None,
            'returns': None,
            'is_async': isinstance(node, ast.AsyncFunctionDef)
        }
        
        # Extract positional arguments
        for arg in node.args.args:
            signature['args'].append({
                'name': arg.arg,
                'annotation': ast.unparse(arg.annotation) if arg.annotation else None
            })
        
        # Extract default values
        for default in node.args.defaults:
            signature['defaults'].append(ast.unparse(default))
        
        # Extract vararg and kwarg
        if node.args.vararg:
            signature['vararg'] = {
                'name': node.args.vararg.arg,
                'annotation': ast.unparse(node.args.vararg.annotation) if node.args.vararg.annotation else None
            }
        
        if node.args.kwarg:
            signature['kwarg'] = {
                'name': node.args.kwarg.arg,
                'annotation': ast.unparse(node.args.kwarg.annotation) if node.args.kwarg.annotation else None
            }
        
        # Extract return annotation
        if node.returns:
            signature['returns'] = ast.unparse(node.returns)
        
        return signature
    
    def _extract_call_usage(self, node: ast.Call, source_code: str, target_module: str) -> Optional[Dict[str, Any]]:
        """Extract API call usage from AST node."""
        # Check if this is a call to the target module
        if isinstance(node.func, ast.Attribute):
            # Handle module.method() calls
            if isinstance(node.func.value, ast.Name):
                module_name = node.func.value.id
                if target_module in module_name.lower():
                    return self._analyze_call_node(node, source_code, f"{module_name}.{node.func.attr}")
        elif isinstance(node.func, ast.Name):
            # Handle function() calls - check imports
            func_name = node.func.id
            if target_module.lower() in func_name.lower():
                return self._analyze_call_node(node, source_code, func_name)
        
        return None
    
    def _analyze_call_node(self, node: ast.Call, source_code: str, api_name: str) -> Dict[str, Any]:
        """Analyze an API call node."""
        usage = {
            'api_name': api_name,
            'arguments': [],
            'keyword_arguments': {},
            'source_location': self._get_source_location(node, source_code)
        }
        
        # Extract positional arguments
        for arg in node.args:
            usage['arguments'].append(ast.unparse(arg))
        
        # Extract keyword arguments
        for keyword in node.keywords:
            usage['keyword_arguments'][keyword.arg] = ast.unparse(keyword.value)
        
        return usage
    
    def _compare_signatures(self, old_entity: APIEntity, new_entity: APIEntity) -> Dict[str, Any]:
        """Compare two API entity signatures."""
        old_sig = old_entity.signature
        new_sig = new_entity.signature
        
        changes = {
            'parameter_changes': [],
            'return_type_changed': False,
            'overall_change': False
        }
        
        # Compare argument counts
        old_args = len(old_sig['args'])
        new_args = len(new_sig['args'])
        
        if old_args != new_args:
            changes['overall_change'] = True
            changes['parameter_changes'].append({
                'type': 'count_change',
                'old_count': old_args,
                'new_count': new_args
            })
        
        # Compare individual parameters
        max_args = max(old_args, new_args)
        for i in range(max_args):
            old_param = old_sig['args'][i] if i < old_args else None
            new_param = new_sig['args'][i] if i < new_args else None
            
            if old_param != new_param:
                changes['parameter_changes'].append({
                    'type': 'parameter_change',
                    'index': i,
                    'old': old_param,
                    'new': new_param
                })
        
        # Compare return types
        if old_sig['returns'] != new_sig['returns']:
            changes['return_type_changed'] = True
            changes['overall_change'] = True
        
        return changes
    
    def _entity_key(self, entity: APIEntity) -> str:
        """Generate a unique key for an API entity."""
        return f"{entity.module}.{entity.name}"
    
    def _find_similar_entity(self, key: str, entity_dict: Dict[str, APIEntity]) -> Optional[str]:
        """Find a similar entity name using fuzzy matching."""
        # Simple similarity check - can be enhanced with more sophisticated algorithms
        for existing_key in entity_dict:
            if self._calculate_similarity(key, existing_key) > 0.8:
                return existing_key
        return None
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings."""
        # Simple Levenshtein-like distance calculation
        if str1 == str2:
            return 1.0
        
        len1, len2 = len(str1), len(str2)
        if len1 == 0 or len2 == 0:
            return 0.0
        
        # Create a distance matrix
        matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]
        
        for i in range(len1 + 1):
            matrix[i][0] = i
        for j in range(len2 + 1):
            matrix[0][j] = j
        
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                if str1[i-1] == str2[j-1]:
                    matrix[i][j] = matrix[i-1][j-1]
                else:
                    matrix[i][j] = min(
                        matrix[i-1][j] + 1,    # deletion
                        matrix[i][j-1] + 1,    # insertion
                        matrix[i-1][j-1] + 1   # substitution
                    )
        
        max_len = max(len1, len2)
        return (max_len - matrix[len1][len2]) / max_len
    
    def _should_include_entity(self, entity: APIEntity, target_module: Optional[str]) -> bool:
        """Check if entity should be included in analysis."""
        if target_module:
            return target_module.lower() in entity.name.lower()
        
        if self.include_builtin_apis:
            return True
        
        # Exclude common builtin modules unless specifically requested
        return not any(builtin in entity.module.lower() for builtin in self.builtin_modules)
    
    def _get_source_location(self, node: ast.AST, source_code: str) -> str:
        """Get source location information for an AST node."""
        try:
            return f"line {node.lineno}, column {node.col_offset}"
        except:
            return "unknown location"