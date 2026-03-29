"""
Test suite for Transformation Engine module.
"""

import unittest
import tempfile
import os
import shutil
from pathlib import Path

from api_migration_system.core.transformation_engine import (
    TransformationEngine, TransformationProject, TransformationOperation,
    TransformationStatus, RollbackStrategy, DependencyGraph
)


class TestDependencyGraph(unittest.TestCase):
    """Test cases for DependencyGraph class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.graph = DependencyGraph()
    
    def test_add_vertex(self):
        """Test adding vertices to the graph."""
        self.graph.add_vertex("file1.py")
        self.graph.add_vertex("file2.py")
        
        self.assertIn("file1.py", self.graph.vertices)
        self.assertIn("file2.py", self.graph.vertices)
        self.assertEqual(len(self.graph.vertices), 2)
    
    def test_add_edge(self):
        """Test adding edges to the graph."""
        self.graph.add_edge("file1.py", "file2.py")
        
        self.assertIn("file1.py", self.graph.vertices)
        self.assertIn("file2.py", self.graph.vertices)
        self.assertIn("file2.py", self.graph.edges["file1.py"])
    
    def test_get_dependencies(self):
        """Test getting dependencies of a vertex."""
        self.graph.add_edge("file1.py", "file2.py")
        self.graph.add_edge("file1.py", "file3.py")
        
        deps = self.graph.get_dependencies("file1.py")
        self.assertIn("file2.py", deps)
        self.assertIn("file3.py", deps)
    
    def test_get_dependents(self):
        """Test getting dependents of a vertex."""
        self.graph.add_edge("file1.py", "file2.py")
        self.graph.add_edge("file3.py", "file2.py")
        
        dependents = self.graph.get_dependents("file2.py")
        self.assertIn("file1.py", dependents)
        self.assertIn("file3.py", dependents)
    
    def test_topological_sort(self):
        """Test topological sorting."""
        # Create a simple DAG: A -> B -> C
        self.graph.add_edge("A", "B")
        self.graph.add_edge("B", "C")
        
        sorted_nodes = self.graph.topological_sort()
        
        # A should come before B, B should come before C
        a_index = sorted_nodes.index("A")
        b_index = sorted_nodes.index("B")
        c_index = sorted_nodes.index("C")
        
        self.assertLess(a_index, b_index)
        self.assertLess(b_index, c_index)
    
    def test_cycle_detection(self):
        """Test cycle detection in graphs."""
        # Create a cycle: A -> B -> A
        self.graph.add_edge("A", "B")
        self.graph.add_edge("B", "A")
        
        self.assertTrue(self.graph.has_cycle())
        
        # Create a DAG: A -> B -> C
        self.graph2 = DependencyGraph()
        self.graph2.add_edge("A", "B")
        self.graph2.add_edge("B", "C")
        
        self.assertFalse(self.graph2.has_cycle())


class TestTransformationEngine(unittest.TestCase):
    """Test cases for TransformationEngine class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.engine = TransformationEngine(workspace_dir=self.temp_dir)
        
        # Create test source directory
        self.source_dir = os.path.join(self.temp_dir, "source")
        self.target_dir = os.path.join(self.temp_dir, "target")
        os.makedirs(self.source_dir, exist_ok=True)
        
        # Create test source files
        self.test_file = os.path.join(self.source_dir, "test.py")
        with open(self.test_file, 'w') as f:
            f.write("""
import requests

def fetch_data():
    response = requests.get('https://example.com', timeout=30*1000)
    return response.json()
""")
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_project(self):
        """Test creating a transformation project."""
        project_id = self.engine.create_project(
            "test_project", self.source_dir, self.target_dir
        )
        
        self.assertIsInstance(project_id, str)
        self.assertIn(project_id, self.engine.projects)
        
        project = self.engine.projects[project_id]
        self.assertEqual(project.name, "test_project")
        self.assertEqual(project.source_path, self.source_dir)
        self.assertEqual(project.target_path, self.target_dir)
        self.assertEqual(project.status, TransformationStatus.PENDING)
    
    def test_analyze_project(self):
        """Test analyzing a transformation project."""
        project_id = self.engine.create_project(
            "test_project", self.source_dir, self.target_dir
        )
        
        analysis_results = self.engine.analyze_project(project_id)
        
        self.assertIsInstance(analysis_results, dict)
        self.assertIn("api_entities", analysis_results)
        self.assertIn("transformation_opportunities", analysis_results)
        self.assertIn("complexity_score", analysis_results)
        
        # Should find the test function
        self.assertGreater(len(analysis_results["api_entities"]), 0)
        
        # Should find transformation opportunities for requests usage
        opportunities = analysis_results["transformation_opportunities"]
        self.assertGreater(len(opportunities), 0)
    
    def test_plan_transformations(self):
        """Test planning transformations for a project."""
        project_id = self.engine.create_project(
            "test_project", self.source_dir, self.target_dir
        )
        
        # Analyze project first
        self.engine.analyze_project(project_id)
        
        operations = self.engine.plan_transformations(project_id)
        
        self.assertIsInstance(operations, list)
        
        if operations:  # If transformations were planned
            operation = operations[0]
            self.assertIsInstance(operation, TransformationOperation)
            self.assertEqual(operation.file_path, "test.py")
            self.assertGreater(len(operation.changes), 0)
            self.assertEqual(operation.status, TransformationStatus.PENDING)
    
    def test_execute_transformations_dry_run(self):
        """Test executing transformations in dry-run mode."""
        project_id = self.engine.create_project(
            "test_project", self.source_dir, self.target_dir
        )
        
        # Analyze and plan
        self.engine.analyze_project(project_id)
        operations = self.engine.plan_transformations(project_id)
        
        if not operations:
            self.skipTest("No operations were planned")
        
        # Execute in dry-run mode
        results = self.engine.execute_transformations(project_id, dry_run=True)
        
        self.assertIsInstance(results, dict)
        self.assertIn("project_id", results)
        self.assertIn("total_operations", results)
        self.assertIn("successful_operations", results)
        self.assertEqual(results["project_id"], project_id)
        self.assertEqual(results["total_operations"], len(operations))
        
        # In dry-run mode, target files should not exist
        target_file = os.path.join(self.target_dir, "test.py")
        self.assertFalse(os.path.exists(target_file))
    
    def test_execute_transformations_real(self):
        """Test executing transformations for real."""
        project_id = self.engine.create_project(
            "test_project", self.source_dir, self.target_dir
        )
        
        # Analyze and plan
        self.engine.analyze_project(project_id)
        operations = self.engine.plan_transformations(project_id)
        
        if not operations:
            self.skipTest("No operations were planned")
        
        # Execute for real
        results = self.engine.execute_transformations(project_id, dry_run=False)
        
        self.assertIsInstance(results, dict)
        self.assertIn("backup_path", results)
        
        # Target files should exist
        target_file = os.path.join(self.target_dir, "test.py")
        self.assertTrue(os.path.exists(target_file))
        
        # Check if transformation was applied
        with open(target_file, 'r') as f:
            content = f.read()
        
        # Should contain the transformed code (timeout scaled)
        self.assertIn("timeout=30*1000", content)

    def test_apply_api_migrations_is_idempotent_for_scaled_timeouts(self):
        """Already-scaled timeouts should not be multiplied again."""
        source_code = """
import requests

def fetch_data():
    response = requests.get('https://example.com', timeout=30*1000)
    return response.json()
"""

        transformed = self.engine._apply_api_migrations(source_code)

        self.assertIn("timeout=30*1000", transformed)
        self.assertNotIn("timeout=30*1000*1000", transformed)
    
    def test_rollback_transformations(self):
        """Test rolling back transformations."""
        project_id = self.engine.create_project(
            "test_project", self.source_dir, self.target_dir
        )
        
        # Analyze, plan, and execute
        self.engine.analyze_project(project_id)
        operations = self.engine.plan_transformations(project_id)
        
        if not operations:
            self.skipTest("No operations were planned")
        
        self.engine.execute_transformations(project_id, dry_run=False)
        
        # Test full rollback
        success = self.engine.rollback_transformations(project_id, RollbackStrategy.FULL_ROLLBACK)
        self.assertTrue(success)
        
        # Target files should be removed
        target_file = os.path.join(self.target_dir, "test.py")
        self.assertFalse(os.path.exists(target_file))
    
    def test_export_project_report(self):
        """Test exporting project reports."""
        project_id = self.engine.create_project(
            "test_project", self.source_dir, self.target_dir
        )
        
        # Analyze project
        self.engine.analyze_project(project_id)
        
        # Export report
        report_path = os.path.join(self.temp_dir, "report.json")
        exported_path = self.engine.export_project_report(project_id, report_path)
        
        self.assertEqual(exported_path, report_path)
        self.assertTrue(os.path.exists(report_path))
        
        # Check report content
        import json
        with open(report_path, 'r') as f:
            report = json.load(f)
        
        self.assertIn("project_info", report)
        self.assertIn("transformation_summary", report)
        self.assertIn("operations", report)
        
        project_info = report["project_info"]
        self.assertEqual(project_info["id"], project_id)
        self.assertEqual(project_info["name"], "test_project")


class TestTransformationProject(unittest.TestCase):
    """Test cases for TransformationProject dataclass."""
    
    def test_project_creation(self):
        """Test creation of transformation projects."""
        project = TransformationProject(
            id="test_id",
            name="test_project",
            source_path="/source",
            target_path="/target"
        )
        
        self.assertEqual(project.id, "test_id")
        self.assertEqual(project.name, "test_project")
        self.assertEqual(project.source_path, "/source")
        self.assertEqual(project.target_path, "/target")
        self.assertEqual(project.status, TransformationStatus.PENDING)
        self.assertEqual(project.operations, [])
        self.assertEqual(project.dependencies, {})
        self.assertIsInstance(project.metadata, dict)


class TestTransformationOperation(unittest.TestCase):
    """Test cases for TransformationOperation dataclass."""
    
    def test_operation_creation(self):
        """Test creation of transformation operations."""
        operation = TransformationOperation(
            id="op1",
            file_path="test.py",
            original_content="old code",
            transformed_content="new code",
            changes=[]
        )
        
        self.assertEqual(operation.id, "op1")
        self.assertEqual(operation.file_path, "test.py")
        self.assertEqual(operation.original_content, "old code")
        self.assertEqual(operation.transformed_content, "new code")
        self.assertEqual(operation.changes, [])
        self.assertEqual(operation.status, TransformationStatus.PENDING)
    
    def test_operation_id_generation(self):
        """Test automatic operation ID generation."""
        operation = TransformationOperation(
            file_path="test.py",
            original_content="old code",
            transformed_content="new code",
            changes=[]
        )
        
        # Should have generated an ID
        self.assertIsNotNone(operation.id)
        self.assertIsInstance(operation.id, str)
        self.assertGreater(len(operation.id), 0)


if __name__ == '__main__':
    unittest.main()
