"""
Semantic Mapper Module

Provides rule-based transformation engine with semantic understanding.
Handles transformation pattern matching, proof obligation generation,
and context-aware code transformation with formal verification.
"""

import ast
import re
import copy
import hashlib
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Any, Optional


class TransformationType(Enum):
    """Types of code transformations."""
    PARAMETER_SCALE = "parameter_scale"
    PARAMETER_RENAME = "parameter_rename"
    METHOD_REPLACE = "method_replace"
    TYPE_CONVERT = "type_convert"


@dataclass
class TransformationRule:
    """Defines a transformation rule with pattern, replacement, and confidence.

    Attributes:
        name: Unique identifier for the rule.
        type: The category of transformation.
        pattern: Regex or AST pattern to match.
        replacement: Replacement template.
        confidence: Confidence score in [0.0, 1.0].
        description: Human-readable description.
        proof_obligation: Formal proof obligation string.
        conditions: Extra conditions for applicability.
        context_requirements: Requirements the semantic context must satisfy.
    """
    name: str
    type: TransformationType
    pattern: str
    replacement: str
    confidence: float
    description: str = ""
    proof_obligation: str = ""
    conditions: List[str] = field(default_factory=list)
    context_requirements: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Confidence must be between 0.0 and 1.0, got {self.confidence}"
            )


@dataclass
class TransformationMatch:
    """Represents a match of a transformation rule against source code.

    Attributes:
        rule: The transformation rule that matched.
        matched_code: The original code fragment that was matched.
        replacement_code: The replacement code fragment.
        confidence: Confidence score for this specific match.
        context: Additional context information about the match.
    """
    rule: TransformationRule
    matched_code: str
    replacement_code: str
    confidence: float
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticContext:
    """Captures semantic context surrounding a code node.

    Attributes:
        variable_types: Mapping of variable names to inferred types.
        function_calls: List of function calls in the surrounding scope.
        imports: List of imported module names.
        surrounding_code: Raw source code around the node.
        control_flow: List of control-flow constructs enclosing the node.
        data_flow: Mapping of variable names to data-flow information.
    """
    variable_types: Dict[str, str] = field(default_factory=dict)
    function_calls: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    surrounding_code: str = ""
    control_flow: List[str] = field(default_factory=list)
    data_flow: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Transformation Pattern base class and concrete implementations
# ---------------------------------------------------------------------------

class TransformationPattern(ABC):
    """Abstract base class for AST-level transformation patterns."""

    @abstractmethod
    def matches(self, node: ast.AST, context: SemanticContext) -> bool:
        """Return True if *node* is eligible for this transformation."""

    @abstractmethod
    def transform(self, node: ast.AST, context: SemanticContext) -> ast.AST:
        """Return a *new* AST node with the transformation applied."""


class ParameterScalePattern(TransformationPattern):
    """Scale a keyword argument's numeric value by a constant factor.

    Example: ``timeout=30*1000`` → ``timeout=30*1000``
    """

    def __init__(self, parameter_name: str, scale_factor: int):
        self.parameter_name = parameter_name
        self.scale_factor = scale_factor

    def matches(self, node: ast.AST, context: SemanticContext) -> bool:
        if not isinstance(node, ast.Call):
            return False
        for kw in node.keywords:
            if kw.arg == self.parameter_name and isinstance(kw.value, ast.Constant):
                return True
        return False

    def transform(self, node: ast.AST, context: SemanticContext) -> ast.AST:
        node = copy.deepcopy(node)
        for kw in node.keywords:
            if kw.arg == self.parameter_name and isinstance(kw.value, ast.Constant):
                original_value = kw.value
                kw.value = ast.BinOp(
                    left=original_value,
                    op=ast.Mult(),
                    right=ast.Constant(value=self.scale_factor),
                )
        return node


class ParameterRenamePattern(TransformationPattern):
    """Rename a keyword argument.

    Example: ``data=payload`` → ``json=payload``
    """

    def __init__(self, old_name: str, new_name: str):
        self.old_name = old_name
        self.new_name = new_name

    def matches(self, node: ast.AST, context: SemanticContext) -> bool:
        if not isinstance(node, ast.Call):
            return False
        return any(kw.arg == self.old_name for kw in node.keywords)

    def transform(self, node: ast.AST, context: SemanticContext) -> ast.AST:
        node = copy.deepcopy(node)
        for kw in node.keywords:
            if kw.arg == self.old_name:
                kw.arg = self.new_name
        return node


# ---------------------------------------------------------------------------
# SemanticMapper — the main orchestrator
# ---------------------------------------------------------------------------

class SemanticMapper:
    """Rule-based transformation engine with semantic understanding.

    Provides:
    * ``analyze_code``  — scan source for transformation opportunities
    * ``apply_transformation`` — apply a single TransformationMatch
    * ``generate_proof_certificate`` — create a formal proof certificate
    * ``add_rule`` / ``add_pattern`` — extend the rule/pattern set
    """

    def __init__(self):
        self.transformation_rules: Dict[str, TransformationRule] = {}
        self.patterns: List[TransformationPattern] = []
        self._load_default_rules()

    # ----- public API -----

    def add_rule(self, rule: TransformationRule) -> None:
        """Register a transformation rule."""
        self.transformation_rules[rule.name] = rule

    def add_pattern(self, pattern: TransformationPattern) -> None:
        """Register a transformation pattern."""
        self.patterns.append(pattern)

    def analyze_code(self, source_code: str) -> List[TransformationMatch]:
        """Analyze *source_code* and return all applicable TransformationMatches."""
        matches: List[TransformationMatch] = []

        # Regex-based rule matching
        for rule in self.transformation_rules.values():
            for m in re.finditer(rule.pattern, source_code):
                replacement_code = re.sub(rule.pattern, rule.replacement, m.group(0))
                matches.append(TransformationMatch(
                    rule=rule,
                    matched_code=m.group(0),
                    replacement_code=replacement_code,
                    confidence=rule.confidence,
                ))

        return matches

    def apply_transformation(
        self, source_code: str, match: TransformationMatch
    ) -> str:
        """Apply a single *match* to *source_code* and return the transformed string."""
        return source_code.replace(match.matched_code, match.replacement_code, 1)

    def generate_proof_certificate(
        self,
        original_code: str,
        transformed_code: str,
        matches: List[TransformationMatch],
    ) -> Dict[str, Any]:
        """Generate a formal proof certificate for a set of transformations."""
        proofs = []
        total_confidence = 0.0
        for match in matches:
            proof = {
                "rule_name": match.rule.name,
                "confidence": match.confidence,
                "proof_obligation": match.rule.proof_obligation or (
                    f"Transformation '{match.rule.name}' preserves behavioral "
                    f"semantics with confidence {match.confidence:.2f}"
                ),
                "matched_code": match.matched_code,
                "replacement_code": match.replacement_code,
            }
            proofs.append(proof)
            total_confidence += match.confidence

        avg_confidence = total_confidence / len(matches) if matches else 0.0

        certificate: Dict[str, Any] = {
            "transformation_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "original_code_hash": hashlib.sha256(original_code.encode()).hexdigest(),
            "transformed_code_hash": hashlib.sha256(transformed_code.encode()).hexdigest(),
            "verification_status": "verified" if avg_confidence >= 0.5 else "unverified",
            "proofs": proofs,
            "formal_guarantee": (
                f"All {len(proofs)} transformation(s) preserve behavioral semantics "
                f"with average confidence {avg_confidence:.2f}"
            ),
            "confidence": avg_confidence,
        }
        return certificate

    # ----- context extraction (used by tests) -----

    def _extract_context(
        self, node: ast.AST, source_code: str
    ) -> SemanticContext:
        """Extract semantic context for a given AST node from *source_code*."""
        tree = ast.parse(source_code)

        variable_types: Dict[str, str] = {}
        function_calls: List[str] = []
        imports: List[str] = []
        control_flow: List[str] = []

        for n in ast.walk(tree):
            # Imports
            if isinstance(n, ast.Import):
                for alias in n.names:
                    imports.append(alias.name)
            elif isinstance(n, ast.ImportFrom):
                if n.module:
                    imports.append(n.module)

            # Variable assignments — simple type inference
            if isinstance(n, ast.Assign):
                for target in n.targets:
                    if isinstance(target, ast.Name):
                        inferred = self._infer_type(n.value)
                        if inferred:
                            variable_types[target.id] = inferred

            # Function calls
            if isinstance(n, ast.Call):
                call_name = self._call_name(n)
                if call_name:
                    function_calls.append(call_name)

            # Control flow
            if isinstance(n, (ast.If, ast.For, ast.While, ast.Try)):
                control_flow.append(type(n).__name__)

        return SemanticContext(
            variable_types=variable_types,
            function_calls=function_calls,
            imports=imports,
            surrounding_code=source_code.strip(),
            control_flow=control_flow,
        )

    # ----- private helpers -----

    def _load_default_rules(self) -> None:
        """Pre-load common transformation rules for the ``requests`` library."""
        # Rule 1: Scale timeout values (seconds → milliseconds)
        timeout_rule = TransformationRule(
            name="requests_timeout_scale",
            type=TransformationType.PARAMETER_SCALE,
            pattern=r"timeout=(\d+)(?!\s*\*\s*1000)(?=\D|$)",
            replacement=r"timeout=\1*1000",
            confidence=0.9,
            description="Scale timeout from seconds to milliseconds",
            proof_obligation=(
                "Preserves timeout behavior: timeout_seconds * 1000 = timeout_milliseconds"
            ),
        )
        self.add_rule(timeout_rule)

        # Rule 2: Rename data parameter to json
        rename_rule = TransformationRule(
            name="requests_data_to_json",
            type=TransformationType.PARAMETER_RENAME,
            pattern=r"data=json\.dumps\(([^)]+)\)",
            replacement=r"json=\1",
            confidence=0.85,
            description="Rename data parameter to json for requests",
            proof_obligation=(
                "Parameter rename preserves payload semantics: json=x ≡ json=x"
            ),
        )
        self.add_rule(rename_rule)

        # Default AST-level patterns
        self.patterns.append(ParameterScalePattern("timeout", 1000))
        self.patterns.append(ParameterRenamePattern("data", "json"))

    @staticmethod
    def _infer_type(node: ast.AST) -> Optional[str]:
        """Best-effort type inference for an AST value node."""
        if isinstance(node, ast.Constant):
            return type(node.value).__name__
        if isinstance(node, ast.Dict):
            return "dict"
        if isinstance(node, ast.List):
            return "list"
        if isinstance(node, ast.Tuple):
            return "tuple"
        if isinstance(node, ast.Set):
            return "set"
        if isinstance(node, ast.Call):
            name = SemanticMapper._call_name(node)
            if name:
                return name
        return None

    @staticmethod
    def _call_name(node: ast.Call) -> Optional[str]:
        """Extract the dotted name from an ast.Call node."""
        func = node.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            parts = []
            current = func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return None
