"""
Test suite for API Diff Analyzer module.
"""

import unittest
import ast
import tempfile
import os
from pathlib import Path

from api_migration_system.core.api_diff_analyzer import (
    APIDiffAnalyzer, APIEntity, APIDiff, ChangeType
)


class TestAPIDiffAnalyzer(unittest.TestCase):
    """Test cases for APIDiffAnalyzer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = APIDiffAnalyzer()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_extract_function_entity(self):
        """Test extraction of function entities from AST."""
        source_code = """
def old_function(param1, param2=None):
    '''Test function docstring.'''
    return param1 + param2
"""
        tree = ast.parse(source_code)
        func_node = tree.body[0]
        
        entity = self.analyzer._extract_function_entity(func_node, source_code)
        
        self.assertEqual(entity.name, "old_function")
        self.assertEqual(len(entity.signature['args']), 2)
        self.assertEqual(entity.signature['args'][0]['name'], 'param1')
        self.assertEqual(entity.signature['args'][1]['name'], 'param2')
        self.assertEqual(entity.docstring, "Test function docstring.")
    
    def test_compare_signatures(self):
        """Test comparison of function signatures."""
        old_source = """
def func(a, b):
    return a + b
"""
        new_source = """
def func(a, b, c=None):
    return a + b + (c or 0)
"""
        
        old_entities = self.analyzer.analyze_source_code(old_source)
        new_entities = self.analyzer.analyze_source_code(new_source)
        
        old_entity = old_entities[0]
        new_entity = new_entities[0]
        
        changes = self.analyzer._compare_signatures(old_entity, new_entity)
        
        self.assertTrue(changes['overall_change'])
        self.assertEqual(len(changes['parameter_changes']), 1)
        self.assertEqual(changes['parameter_changes'][0]['type'], 'count_change')
    
    def test_extract_api_usage(self):
        """Test extraction of API usage patterns."""
        source_code = """
import requests

response = requests.get('https://api.example.com', timeout=30)
data = response.json()
"""
        usages = self.analyzer.extract_api_usage(source_code, 'requests')
        
        self.assertEqual(len(usages), 1)
        self.assertEqual(usages[0]['api_name'], 'requests.get')
        self.assertEqual(usages[0]['keyword_arguments']['timeout'], '30')
    
    def test_analyze_file(self):
        """Test analysis of a Python file."""
        test_file = os.path.join(self.temp_dir, 'test.py')
        with open(test_file, 'w') as f:
            f.write("""
def test_func():
    requests.get('https://example.com', timeout=30)
""")
        
        entities = self.analyzer.analyze_file(test_file)
        
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0].name, 'test_func')
    
    def test_compare_versions(self):
        """Test comparison of API versions."""
        old_code = """
def old_api(param):
    return param * 2
"""
        new_code = """
def new_api(param, scale=1):
    return param * 2 * scale
"""
        
        old_entities = self.analyzer.analyze_source_code(old_code)
        new_entities = self.analyzer.analyze_source_code(new_code)
        
        diffs = self.analyzer.compare_versions(old_entities, new_entities)
        
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0].change_type, ChangeType.SIGNATURE_CHANGED)
    
    def test_entity_key_generation(self):
        """Test unique key generation for API entities."""
        entity = APIEntity(
            name="test_function",
            module="test_module",
            signature={}
        )
        
        key = self.analyzer._entity_key(entity)
        self.assertEqual(key, "test_module.test_function")
    
    def test_similarity_calculation(self):
        """Test string similarity calculation."""
        similarity = self.analyzer._calculate_similarity("old_function", "new_function")
        self.assertGreater(similarity, 0.5)
        self.assertLessEqual(similarity, 1.0)
        
        # Test exact match
        similarity = self.analyzer._calculate_similarity("same", "same")
        self.assertEqual(similarity, 1.0)
        
        # Test no match
        similarity = self.analyzer._calculate_similarity("abc", "xyz")
        self.assertEqual(similarity, 0.0)
    
    def test_complex_source_code_analysis(self):
        """Test analysis of complex source code with multiple patterns."""
        source_code = """
import requests
import json

class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
    
    def get_data(self, endpoint):
        response = requests.get(
            f"{self.base_url}/{endpoint}",
            timeout=30,
            headers={'Content-Type': 'application/json'}
        )
        return response.json()
    
    def post_data(self, endpoint, data):
        return requests.post(
            f"{self.base_url}/{endpoint}",
            data=json.dumps(data),
            timeout=60
        )
"""
        
        entities = self.analyzer.analyze_source_code(source_code)
        usages = self.analyzer.extract_api_usage(source_code, 'requests')
        
        # Should find class methods
        method_names = [entity.name for entity in entities]
        self.assertIn('APIClient.get_data', method_names)
        self.assertIn('APIClient.post_data', method_names)
        
        # Should find API usages
        self.assertEqual(len(usages), 2)
        api_calls = [usage['api_name'] for usage in usages]
        self.assertIn('requests.get', api_calls)
        self.assertIn('requests.post', api_calls)


class TestAPIEntity(unittest.TestCase):
    """Test cases for APIEntity dataclass."""
    
    def test_entity_creation(self):
        """Test creation of APIEntity objects."""
        entity = APIEntity(
            name="test_function",
            module="test_module",
            signature={'args': []}
        )
        
        self.assertEqual(entity.name, "test_function")
        self.assertEqual(entity.module, "test_module")
        self.assertEqual(entity.signature, {'args': []})
    
    def test_entity_hashing(self):
        """Test hashing of APIEntity objects."""
        entity1 = APIEntity(
            name="test_function",
            module="test_module",
            signature={}
        )
        entity2 = APIEntity(
            name="test_function",
            module="test_module",
            signature={}
        )
        
        self.assertEqual(hash(entity1), hash(entity2))
        
        # Different modules should have different hashes
        entity3 = APIEntity(
            name="test_function",
            module="other_module",
            signature={}
        )
        self.assertNotEqual(hash(entity1), hash(entity3))


class TestAPIDiff(unittest.TestCase):
    """Test cases for APIDiff dataclass."""
    
    def test_diff_creation(self):
        """Test creation of APIDiff objects."""
        diff = APIDiff(
            change_type=ChangeType.PARAMETER_ADDED,
            description="Parameter was added",
            confidence=0.8
        )
        
        self.assertEqual(diff.change_type, ChangeType.PARAMETER_ADDED)
        self.assertEqual(diff.description, "Parameter was added")
        self.assertEqual(diff.confidence, 0.8)
        self.assertIsNone(diff.old_entity)
        self.assertIsNone(diff.new_entity)


if __name__ == '__main__':
    unittest.main()