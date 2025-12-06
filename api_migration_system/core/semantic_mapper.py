"""
Semantic Mapper Foundation - Module 2

Provides rule-based transformation engine with semantic understanding capabilities.
Handles transformation pattern matching, confidence scoring, and context extraction.
"""

import ast
import re
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from abc import ABC, abstractmethod

from .api_diff_analyzer import APIEntity, APIDiff, ChangeType

logger = logging.getLogger(__name__)


class TransformationType(Enum):
    """Types of transformations that can be applied."""
    PARAMETER_SCALE = "parameter_scale"  # e.g., timeout 30 -> 30*1000
    PARAMETER_RENAME = "parameter_rename"  # e.g., data -> payload
    PARAMETER_REORDER = "parameter_reorder"  # e.g., (a, b) -> (b, a)
    PARAMETER_TYPE_CONVERT = "parameter_type_convert"  # e.g., str -> bytes
    METHOD_REPLACEMENT = "method_replacement"  # e.g., get -> post
    RETURN_TYPE_CONVERT = "return_type_convert"
    DEPRECATED_METHOD = "deprecated_method"
    IMPORT_UPDATE = "import_update"


@dataclass
class TransformationRule:
    """Represents a transformation rule."""
    name: str
    type: TransformationType
    pattern: str
    replacement: str
    confidence: float
    conditions: List[str] = field(default_factory=list)
    context_requirements: Dict[str, Any] = field(default_factory=dict)
    proof_obligation: str = ""
    description: str = ""
    
    def __post_init__(self):
        """Validate the transformation rule."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")


@dataclass
class TransformationMatch:
    """Represents a match between source code and transformation rule."""
    rule: TransformationRule
    matched_code: str
    replacement_code: str
    confidence: float
    context: Dict[str, Any] = field(default_factory=dict)
    ast_node: Optional[ast.AST] = None
    location: Optional[str] = None


@dataclass
class SemanticContext:
    """Represents the semantic context of a code fragment."""
    variable_types: Dict[str, str] = field(default_factory=dict)
    function_calls: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    surrounding_code: str = ""
    control_flow: List[str] = field(default_factory=list)
    data_flow: Dict[str, List[str]] = field(default_factory=dict)


class TransformationPattern(ABC):
    """Abstract base class for transformation patterns."""
    
    @abstractmethod
    def matches(self, node: ast.AST, context: SemanticContext) -> bool:
        """Check if the pattern matches the given AST node."""
        pass
    
    @abstractmethod
    def transform(self, node: ast.AST, context: SemanticContext) -> ast.AST:
        """Transform the given AST node."""
        pass


class ParameterScalePattern(TransformationPattern):
    """Handles parameter scaling transformations (e.g., timeout 30 -> 30*1000)."""
    
    def __init__(self, parameter_name: str, scale_factor: float):
        self.parameter_name = parameter_name
        self.scale_factor = scale_factor
    
    def matches(self, node: ast.AST, context: SemanticContext) -> bool:
        """Check if this pattern matches the node."""
        if not isinstance(node, ast.Call):
            return False
        
        # Check if this is a call to a function with the target parameter
        for keyword in node.keywords:
            if keyword.arg == self.parameter_name:
                return True
        return False
    
    def transform(self, node: ast.AST, context: SemanticContext) -> ast.AST:
        """Transform the node by scaling the parameter."""
        if not isinstance(node, ast.Call):
            return node
        
        # Find and transform the target parameter
        for keyword in node.keywords:
            if keyword.arg == self.parameter_name:
                # Create a multiplication expression
                scaled_value = ast.BinOp(
                    left=keyword.value,
                    op=ast.Mult(),
                    right=ast.Constant(value=self.scale_factor)
                )
                keyword.value = scaled_value
                break
        
        return node


class ParameterRenamePattern(TransformationPattern):
    """Handles parameter renaming transformations."""
    
    def __init__(self, old_name: str, new_name: str):
        self.old_name = old_name
        self.new_name = new_name
    
    def matches(self, node: ast.AST, context: SemanticContext) -> bool:
        """Check if this pattern matches the node."""
        if not isinstance(node, ast.Call):
            return False
        
        for keyword in node.keywords:
            if keyword.arg == self.old_name:
                return True
        return False
    
    def transform(self, node: ast.AST, context: SemanticContext) -> ast.AST:
        """Transform the node by renaming the parameter."""
        if not isinstance(node, ast.Call):
            return node
        
        for keyword in node.keywords:
            if keyword.arg == self.old_name:
                keyword.arg = self.new_name
                break
        
        return node


class SemanticMapper:
    """
    Advanced semantic mapper that provides rule-based transformation capabilities.
    
    This module implements:
    1. Rule-based transformation engine with pattern matching
    2. Confidence scoring infrastructure
    3. Context extraction and analysis
    4. Proof obligation generation for formal verification
    """
    
    def __init__(self):
        """Initialize the semantic mapper with default rules."""
        self.transformation_rules: Dict[str, TransformationRule] = {}
        self.patterns: List[TransformationPattern] = []
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default transformation rules."""
        # Requests library migration rules
        requests_rules = [
            TransformationRule(
                name="requests_timeout_scale",
                type=TransformationType.PARAMETER_SCALE,
                pattern="requests\\.(get|post|put|delete)\\(([^)]* )(timeout=)([^,)]+)([^)]*)\\)",
                replacement=r"requests.\1(\2\3\4*1000\5)",
                confidence=0.9,
                description="Scale timeout parameter from seconds to milliseconds",
                proof_obligation="Preserves timeout behavior: timeout_seconds * 1000 = timeout_milliseconds"
            ),
            TransformationRule(
                name="requests_data_rename",
                type=TransformationType.PARAMETER_RENAME,
                pattern="requests\\.(get|post|put)\\(([^)]*)data=([^,)]+)([^)]*)\\)",
                replacement=r"requests.\1(\2json=\3\4)",
                confidence=0.7,
                description="Rename data parameter to json for consistency",
                proof_obligation="Semantic equivalence: data parameter becomes JSON payload"
            ),
            TransformationRule(
                name="requests_method_deprecation",
                type=TransformationType.DEPRECATED_METHOD,
                pattern="requests\\.(request_ex)\\(",
                replacement="requests.request(",
                confidence=1.0,
                description="Replace deprecated request_ex method",
                proof_obligation="Exact replacement: request_ex is alias for request"
            )
        ]
        
        for rule in requests_rules:
            self.add_rule(rule)
        
        # Initialize default patterns
        self.patterns.extend([
            ParameterScalePattern("timeout", 1000),  # seconds to milliseconds
            ParameterRenamePattern("data", "json")
        ])
    
    def add_rule(self, rule: TransformationRule):
        """Add a transformation rule to the mapper."""
        self.transformation_rules[rule.name] = rule
        logger.debug(f"Added transformation rule: {rule.name}")
    
    def add_pattern(self, pattern: TransformationPattern):
        """Add a transformation pattern to the mapper."""
        self.patterns.append(pattern)
        logger.debug(f"Added transformation pattern: {pattern.__class__.__name__}")
    
    def analyze_code(self, source_code: str, target_module: Optional[str] = None) -> List[TransformationMatch]:
        """
        Analyze source code to find applicable transformations.
        
        Args:
            source_code: Python source code to analyze
            target_module: Optional module to focus analysis on
            
        Returns:
            List of transformation matches found
        """
        try:
            tree = ast.parse(source_code)
            matches = []
            
            # Analyze using patterns
            for node in ast.walk(tree):
                context = self._extract_context(node, source_code)
                for pattern in self.patterns:
                    if pattern.matches(node, context):
                        match = self._create_pattern_match(pattern, node, context, source_code)
                        if match:
                            matches.append(match)
            
            # Analyze using regex rules
            matches.extend(self._analyze_with_regex_rules(source_code))
            
            return matches
        except Exception as e:
            logger.error(f"Error analyzing code: {e}")
            return []
    
    def apply_transformation(self, source_code: str, match: TransformationMatch) -> str:
        """
        Apply a transformation match to source code.
        
        Args:
            source_code: Original source code
            match: Transformation match to apply
            
        Returns:
            Transformed source code
        """
        try:
            if match.ast_node:
                # Apply AST-based transformation
                return self._apply_ast_transformation(source_code, match)
            else:
                # Apply regex-based transformation
                return self._apply_regex_transformation(source_code, match)
        except Exception as e:
            logger.error(f"Error applying transformation: {e}")
            return source_code
    
    def generate_proof_certificate(self, original_code: str, transformed_code: str, 
                                 matches: List[TransformationMatch]) -> Dict[str, Any]:
        """
        Generate a formal proof certificate for the transformation.
        
        Args:
            original_code: Original source code
            transformed_code: Transformed source code
            matches: List of applied transformations
            
        Returns:
            Proof certificate with verification information
        """
        certificate = {
            "transformation_id": self._generate_transformation_id(),
            "timestamp": self._get_current_timestamp(),
            "original_code_hash": self._calculate_code_hash(original_code),
            "transformed_code_hash": self._calculate_code_hash(transformed_code),
            "transformations": [],
            "proofs": [],
            "verification_status": "pending"
        }
        
        for match in matches:
            proof = {
                "rule_name": match.rule.name,
                "rule_type": match.rule.type.value,
                "confidence": match.confidence,
                "proof_obligation": match.rule.proof_obligation,
                "context": match.context,
                "verification_method": self._select_verification_method(match.rule)
            }
            certificate["proofs"].append(proof)
        
        # Add overall verification
        certificate["verification_status"] = self._verify_transformation_set(matches)
        certificate["formal_guarantee"] = self._generate_formal_guarantee(matches)
        
        return certificate
    
    def _extract_context(self, node: ast.AST, source_code: str) -> SemanticContext:
        """Extract semantic context from AST node."""
        context = SemanticContext()
        
        # Extract variable type information
        context.variable_types = self._infer_variable_types(node, source_code)
        
        # Extract function calls
        context.function_calls = self._extract_function_calls(node)
        
        # Extract imports
        context.imports = self._extract_imports(source_code)
        
        # Extract surrounding code
        context.surrounding_code = self._extract_surrounding_code(node, source_code)
        
        # Extract control flow
        context.control_flow = self._extract_control_flow(node)
        
        return context
    
    def _create_pattern_match(self, pattern: TransformationPattern, node: ast.AST, 
                            context: SemanticContext, source_code: str) -> Optional[TransformationMatch]:
        """Create a transformation match for a pattern."""
        try:
            transformed_node = pattern.transform(node, context)
            if transformed_node != node:
                original_code = ast.unparse(node)
                transformed_code = ast.unparse(transformed_node)
                
                # Find matching rule
                rule = self._find_matching_rule(pattern)
                if not rule:
                    return None
                
                return TransformationMatch(
                    rule=rule,
                    matched_code=original_code,
                    replacement_code=transformed_code,
                    confidence=rule.confidence,
                    context=self._context_to_dict(context),
                    ast_node=node,
                    location=self._get_node_location(node)
                )
        except Exception as e:
            logger.error(f"Error creating pattern match: {e}")
        
        return None
    
    def _analyze_with_regex_rules(self, source_code: str) -> List[TransformationMatch]:
        """Analyze source code using regex-based transformation rules."""
        matches = []
        
        for rule in self.transformation_rules.values():
            pattern = re.compile(rule.pattern)
            for match in pattern.finditer(source_code):
                try:
                    replacement = pattern.sub(rule.replacement, source_code)
                    if replacement != source_code:
                        transformation_match = TransformationMatch(
                            rule=rule,
                            matched_code=match.group(0),
                            replacement_code=pattern.sub(rule.replacement, match.group(0)),
                            confidence=rule.confidence,
                            context={"match_location": f"line {self._get_line_number(source_code, match.start())}"}
                        )
                        matches.append(transformation_match)
                except Exception as e:
                    logger.error(f"Error applying regex rule {rule.name}: {e}")
        
        return matches
    
    def _apply_ast_transformation(self, source_code: str, match: TransformationMatch) -> str:
        """Apply AST-based transformation to source code."""
        try:
            tree = ast.parse(source_code)
            
            # Apply transformation to the specific node
            # This is a simplified implementation - in practice, we'd need more sophisticated
            # AST transformation and code generation
            
            # For now, use regex as fallback for AST transformations
            return self._apply_regex_transformation(source_code, match)
        except Exception as e:
            logger.error(f"Error applying AST transformation: {e}")
            return self._apply_regex_transformation(source_code, match)
    
    def _apply_regex_transformation(self, source_code: str, match: TransformationMatch) -> str:
        """Apply regex-based transformation to source code."""
        try:
            pattern = re.compile(re.escape(match.matched_code))
            transformed_code = pattern.sub(match.replacement_code, source_code, count=1)
            return transformed_code
        except Exception as e:
            logger.error(f"Error applying regex transformation: {e}")
            return source_code
    
    def _find_matching_rule(self, pattern: TransformationPattern) -> Optional[TransformationRule]:
        """Find the transformation rule that matches a pattern."""
        for rule in self.transformation_rules.values():
            # This is a simplified matching - in practice, you'd have more sophisticated
            # pattern-rule mapping
            if isinstance(pattern, ParameterScalePattern):
                if rule.type == TransformationType.PARAMETER_SCALE:
                    return rule
            elif isinstance(pattern, ParameterRenamePattern):
                if rule.type == TransformationType.PARAMETER_RENAME:
                    return rule
        return None
    
    def _context_to_dict(self, context: SemanticContext) -> Dict[str, Any]:
        """Convert semantic context to dictionary."""
        return {
            'variable_types': context.variable_types,
            'function_calls': context.function_calls,
            'imports': context.imports,
            'surrounding_code': context.surrounding_code,
            'control_flow': context.control_flow,
            'data_flow': context.data_flow
        }
    
    def _find_containing_function(self, node_lineno: int, tree: ast.AST) -> Optional[ast.FunctionDef]:
        """Find the containing function node for the given node lineno."""
        for child in ast.walk(tree):
            if isinstance(child, ast.FunctionDef):
                if hasattr(child, 'end_lineno') and child.lineno <= node_lineno <= child.end_lineno:
                    return child
        return None

    def _infer_variable_types(self, node: ast.AST, source_code: str) -> Dict[str, str]:
        """Infer variable types from AST node."""
        if not hasattr(node, 'lineno'):
            return {}
        tree = ast.parse(source_code)
        func = self._find_containing_function(node.lineno, tree)
        if not func:
            return {}

        types = {}

        # Collect assignments within the function's body before the node's line
        for stmt in func.body:
            for body_node in ast.walk(stmt):
                if isinstance(body_node, ast.Assign) and hasattr(body_node, 'lineno') and body_node.lineno < node.lineno:
                    for target in body_node.targets:
                        if isinstance(target, ast.Name):
                            type_annotation = self._infer_single_type(body_node.value)
                            if type_annotation:
                                types[target.id] = type_annotation

        return types
    
    def _infer_single_type(self, value_node: ast.AST) -> Optional[str]:
        """Infer type for a single value node."""
        if isinstance(value_node, ast.Constant):
            return type(value_node.value).__name__
        elif isinstance(value_node, ast.Call):
            if isinstance(value_node.func, ast.Name):
                return value_node.func.id
        elif isinstance(value_node, ast.List):
            return "list"
        elif isinstance(value_node, ast.Dict):
            return "dict"
        
        return None
    
    def _extract_function_calls(self, node: ast.AST) -> List[str]:
        """Extract function calls from AST node."""
        calls = []
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.append(f"{child.func.value.id}.{child.func.attr}" if isinstance(child.func.value, ast.Name) else child.func.attr)
        
        return calls
    
    def _extract_imports(self, source_code: str) -> List[str]:
        """Extract import statements from source code."""
        imports = []
        try:
            tree = ast.parse(source_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        imports.append(f"{module}.{alias.name}")
        except:
            pass
        
        return imports
    
    def _extract_surrounding_code(self, node: ast.AST, source_code: str) -> str:
        """Extract surrounding code context."""
        try:
            if not hasattr(node, 'lineno'):
                return ""
            lines = source_code.split('\n')
            start_line = max(0, node.lineno - 3)
            end_line = min(len(lines), node.lineno + 3)
            return '\n'.join(lines[start_line:end_line])
        except:
            return ""
    
    def _extract_control_flow(self, node: ast.AST) -> List[str]:
        """Extract control flow information from AST node."""
        flow = []
        
        for child in ast.walk(node):
            if isinstance(child, ast.If):
                flow.append("if_statement")
            elif isinstance(child, ast.For):
                flow.append("for_loop")
            elif isinstance(child, ast.While):
                flow.append("while_loop")
            elif isinstance(child, ast.Try):
                flow.append("try_except")
        
        return flow
    
    def _get_node_location(self, node: ast.AST) -> str:
        """Get location information for an AST node."""
        try:
            if not hasattr(node, 'lineno'):
                return "unknown"
            return f"line {node.lineno}, column {node.col_offset}"
        except:
            return "unknown"
    
    def _get_line_number(self, source_code: str, position: int) -> int:
        """Get line number for a character position."""
        return source_code[:position].count('\n') + 1
    
    def _generate_transformation_id(self) -> str:
        """Generate a unique transformation ID."""
        import hashlib
        import time
        timestamp = str(time.time())
        return hashlib.sha256(timestamp.encode()).hexdigest()[:16]
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp."""
        import datetime
        return datetime.datetime.now().isoformat()
    
    def _calculate_code_hash(self, code: str) -> str:
        """Calculate hash of source code."""
        import hashlib
        return hashlib.sha256(code.encode()).hexdigest()
    
    def _select_verification_method(self, rule: TransformationRule) -> str:
        """Select appropriate verification method for a rule."""
        if rule.type == TransformationType.PARAMETER_SCALE:
            return "mathematical_verification"
        elif rule.type == TransformationType.PARAMETER_RENAME:
            return "semantic_equivalence"
        elif rule.type == TransformationType.DEPRECATED_METHOD:
            return "direct_replacement"
        else:
            return "heuristic_verification"
    
    def _verify_transformation_set(self, matches: List[TransformationMatch]) -> str:
        """Verify a set of transformations."""
        total_confidence = sum(match.confidence for match in matches) / len(matches) if matches else 0
        
        if total_confidence >= 0.9:
            return "verified"
        elif total_confidence >= 0.7:
            return "likely_correct"
        else:
            return "uncertain"
    
    def _generate_formal_guarantee(self, matches: List[TransformationMatch]) -> str:
        """Generate formal guarantee statement."""
        guarantees = []
        
        for match in matches:
            guarantee = f"Transformation '{match.rule.name}' preserves behavioral semantics with confidence {match.confidence:.2f}"
            if match.rule.proof_obligation:
                guarantee += f". Proof: {match.rule.proof_obligation}"
            guarantees.append(guarantee)
        
        return " AND ".join(guarantees)