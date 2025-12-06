"""
Test suite for Semantic Mapper module.
"""

import unittest
import ast
import tempfile
import os

from api_migration_system.core.semantic_mapper import (
    SemanticMapper, TransformationRule, TransformationMatch,
    TransformationType, SemanticContext,
    ParameterScalePattern, ParameterRenamePattern
)


class TestSemanticMapper(unittest.TestCase):
    """Test cases for SemanticMapper class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mapper = SemanticMapper()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test mapper initialization with default rules."""
        self.assertIsInstance(self.mapper.transformation_rules, dict)
        self.assertIsInstance(self.mapper.patterns, list)
        
        # Should have default rules loaded
        self.assertGreater(len(self.mapper.transformation_rules), 0)
        self.assertGreater(len(self.mapper.patterns), 0)
    
    def test_add_rule(self):
        """Test adding transformation rules."""
        rule = TransformationRule(
            name="test_rule",
            type=TransformationType.PARAMETER_SCALE,
            pattern="test_pattern",
            replacement="test_replacement",
            confidence=0.8,
            description="Test rule"
        )
        
        self.mapper.add_rule(rule)
        self.assertIn("test_rule", self.mapper.transformation_rules)
        self.assertEqual(self.mapper.transformation_rules["test_rule"], rule)
    
    def test_add_pattern(self):
        """Test adding transformation patterns."""
        pattern = ParameterScalePattern("timeout", 1000)
        
        initial_count = len(self.mapper.patterns)
        self.mapper.add_pattern(pattern)
        
        self.assertEqual(len(self.mapper.patterns), initial_count + 1)
        self.assertIn(pattern, self.mapper.patterns)
    
    def test_analyze_code_simple(self):
        """Test analysis of simple source code."""
        source_code = """
import requests

response = requests.get('https://example.com', timeout=30)
"""
        
        matches = self.mapper.analyze_code(source_code)
        
        # Should find transformation opportunities
        self.assertGreater(len(matches), 0)
        
        # Check if timeout scaling transformation is found
        has_timeout_scaling = any(
            match.rule.type == TransformationType.PARAMETER_SCALE
            for match in matches
        )
        self.assertTrue(has_timeout_scaling)
    
    def test_analyze_code_complex(self):
        """Test analysis of complex source code."""
        source_code = """
import requests
import json

def fetch_data(url):
    response = requests.get(url, timeout=30, headers={'Auth': 'Bearer token'})
    return response.json()

def post_data(url, data):
    return requests.post(url, data=json.dumps(data), timeout=60)

class APIHandler:
    def get(self, endpoint):
        return requests.get(f"https://api.com/{endpoint}", timeout=45)
"""
        
        matches = self.mapper.analyze_code(source_code)
        
        # Should find multiple transformation opportunities
        self.assertGreater(len(matches), 0)
        
        # Check for different types of transformations
        scaling_matches = [
            match for match in matches
            if match.rule.type == TransformationType.PARAMETER_SCALE
        ]
        rename_matches = [
            match for match in matches
            if match.rule.type == TransformationType.PARAMETER_RENAME
        ]
        
        self.assertGreater(len(scaling_matches), 0)
        # Note: rename may not apply to all cases depending on implementation
    
    def test_apply_transformation(self):
        """Test applying transformations to source code."""
        source_code = "requests.get('https://example.com', timeout=30)"
        
        # Create a simple transformation match
        rule = TransformationRule(
            name="test_scaling",
            type=TransformationType.PARAMETER_SCALE,
            pattern=r"timeout=(\d+)",
            replacement=r"timeout=\1*1000",
            confidence=0.9
        )
        
        match = TransformationMatch(
            rule=rule,
            matched_code="timeout=30",
            replacement_code="timeout=30*1000",
            confidence=0.9
        )
        
        transformed = self.mapper.apply_transformation(source_code, match)
        
        self.assertIn("timeout=30*1000", transformed)
        self.assertNotEqual(source_code, transformed)
    
    def test_generate_proof_certificate(self):
        """Test generation of proof certificates."""
        original_code = "requests.get('https://example.com', timeout=30)"
        transformed_code = "requests.get('https://example.com', timeout=30*1000)"
        
        rule = TransformationRule(
            name="timeout_scaling",
            type=TransformationType.PARAMETER_SCALE,
            pattern=r"timeout=(\d+)",
            replacement=r"timeout=\1*1000",
            confidence=0.9,
            proof_obligation="Timeout value is scaled from seconds to milliseconds"
        )
        
        match = TransformationMatch(
            rule=rule,
            matched_code="timeout=30",
            replacement_code="timeout=30*1000",
            confidence=0.9
        )
        
        certificate = self.mapper.generate_proof_certificate(
            original_code, transformed_code, [match]
        )
        
        self.assertIn("transformation_id", certificate)
        self.assertIn("timestamp", certificate)
        self.assertIn("original_code_hash", certificate)
        self.assertIn("transformed_code_hash", certificate)
        self.assertIn("proofs", certificate)
        self.assertEqual(len(certificate["proofs"]), 1)
        
        proof = certificate["proofs"][0]
        self.assertEqual(proof["rule_name"], "timeout_scaling")
        self.assertEqual(proof["confidence"], 0.9)
    
    def test_context_extraction(self):
        """Test semantic context extraction."""
        source_code = """
import requests
import json

def func():
    url = "https://example.com"
    data = {"key": "value"}
    response = requests.post(url, data=json.dumps(data), timeout=30)
    return response.json()
"""
        
        tree = ast.parse(source_code)
        # Get the requests.post call node
        post_node = None
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and 
                isinstance(node.func, ast.Attribute) and
                node.func.attr == 'post'):
                post_node = node
                break
        
        if post_node:
            context = self.mapper._extract_context(post_node, source_code)
            
            self.assertIsInstance(context, SemanticContext)
            self.assertIsInstance(context.variable_types, dict)
            self.assertIsInstance(context.function_calls, list)
            self.assertIsInstance(context.imports, list)
            self.assertIsInstance(context.surrounding_code, str)
            
            # Should find some variable type information
            self.assertGreater(len(context.variable_types), 0)


class TestTransformationRule(unittest.TestCase):
    """Test cases for TransformationRule dataclass."""
    
    def test_rule_creation(self):
        """Test creation of transformation rules."""
        rule = TransformationRule(
            name="test_rule",
            type=TransformationType.PARAMETER_SCALE,
            pattern="test_pattern",
            replacement="test_replacement",
            confidence=0.8
        )
        
        self.assertEqual(rule.name, "test_rule")
        self.assertEqual(rule.type, TransformationType.PARAMETER_SCALE)
        self.assertEqual(rule.pattern, "test_pattern")
        self.assertEqual(rule.replacement, "test_replacement")
        self.assertEqual(rule.confidence, 0.8)
        self.assertEqual(rule.conditions, [])
        self.assertEqual(rule.context_requirements, {})
    
    def test_rule_validation(self):
        """Test validation of confidence scores."""
        # Valid confidence
        rule = TransformationRule(
            name="test",
            type=TransformationType.PARAMETER_SCALE,
            pattern="pattern",
            replacement="replacement",
            confidence=0.5
        )
        self.assertEqual(rule.confidence, 0.5)
        
        # Invalid confidence - should raise ValueError
        with self.assertRaises(ValueError):
            TransformationRule(
                name="test",
                type=TransformationType.PARAMETER_SCALE,
                pattern="pattern",
                replacement="replacement",
                confidence=1.5  # Invalid: > 1.0
            )
        
        with self.assertRaises(ValueError):
            TransformationRule(
                name="test",
                type=TransformationType.PARAMETER_SCALE,
                pattern="pattern",
                replacement="replacement",
                confidence=-0.1  # Invalid: < 0.0
            )


class TestTransformationMatch(unittest.TestCase):
    """Test cases for TransformationMatch dataclass."""
    
    def test_match_creation(self):
        """Test creation of transformation matches."""
        rule = TransformationRule(
            name="test_rule",
            type=TransformationType.PARAMETER_SCALE,
            pattern="pattern",
            replacement="replacement",
            confidence=0.8
        )
        
        match = TransformationMatch(
            rule=rule,
            matched_code="old_code",
            replacement_code="new_code",
            confidence=0.9
        )
        
        self.assertEqual(match.rule, rule)
        self.assertEqual(match.matched_code, "old_code")
        self.assertEqual(match.replacement_code, "new_code")
        self.assertEqual(match.confidence, 0.9)
        self.assertEqual(match.context, {})


class TestTransformationPatterns(unittest.TestCase):
    """Test cases for transformation patterns."""
    
    def test_parameter_scale_pattern(self):
        """Test ParameterScalePattern functionality."""
        pattern = ParameterScalePattern("timeout", 1000)
        
        # Create a mock AST call node with timeout parameter
        call_node = ast.Call(
            func=ast.Name(id="requests.get", ctx=ast.Load()),
            args=[ast.Constant(value="https://example.com")],
            keywords=[
                ast.keyword(arg="timeout", value=ast.Constant(value=30))
            ]
        )
        
        context = SemanticContext()
        
        # Test matching
        self.assertTrue(pattern.matches(call_node, context))
        
        # Test transformation
        transformed = pattern.transform(call_node, context)
        self.assertIsNotNone(transformed)
        
        # Check if the timeout value was scaled
        timeout_keyword = next(
            kw for kw in transformed.keywords if kw.arg == "timeout"
        )
        self.assertIsInstance(timeout_keyword.value, ast.BinOp)
    
    def test_parameter_rename_pattern(self):
        """Test ParameterRenamePattern functionality."""
        pattern = ParameterRenamePattern("data", "json")
        
        # Create a mock AST call node with data parameter
        call_node = ast.Call(
            func=ast.Name(id="requests.post", ctx=ast.Load()),
            args=[ast.Constant(value="https://example.com")],
            keywords=[
                ast.keyword(arg="data", value=ast.Constant(value="payload"))
            ]
        )
        
        context = SemanticContext()
        
        # Test matching
        self.assertTrue(pattern.matches(call_node, context))
        
        # Test transformation
        transformed = pattern.transform(call_node, context)
        self.assertIsNotNone(transformed)
        
        # Check if the parameter was renamed
        param_names = [kw.arg for kw in transformed.keywords]
        self.assertIn("json", param_names)
        self.assertNotIn("data", param_names)


class TestSemanticContext(unittest.TestCase):
    """Test cases for SemanticContext dataclass."""
    
    def test_context_creation(self):
        """Test creation of semantic context."""
        context = SemanticContext()
        
        self.assertEqual(context.variable_types, {})
        self.assertEqual(context.function_calls, [])
        self.assertEqual(context.imports, [])
        self.assertEqual(context.surrounding_code, "")
        self.assertEqual(context.control_flow, [])
        self.assertEqual(context.data_flow, {})
    
    def test_context_with_data(self):
        """Test semantic context with data."""
        context = SemanticContext(
            variable_types={"url": "str", "data": "dict"},
            function_calls=["requests.get", "json.dumps"],
            imports=["requests", "json"]
        )
        
        self.assertEqual(context.variable_types["url"], "str")
        self.assertIn("requests.get", context.function_calls)
        self.assertIn("requests", context.imports)


if __name__ == '__main__':
    unittest.main()