"""
Integration tests for the complete API migration system.
"""

import unittest
import tempfile
import os
import shutil
import time
from pathlib import Path

from api_migration_system import APIDiffAnalyzer, SemanticMapper, TransformationEngine
from api_migration_system.core.transformation_engine import RollbackStrategy


class TestCompletePipeline(unittest.TestCase):
    """Integration tests for the complete migration pipeline."""
    
    def setUp(self):
        """Set up test fixtures with real sample code."""
        self.temp_dir = tempfile.mkdtemp()
        self.engine = TransformationEngine(workspace_dir=self.temp_dir)
        
        # Create source directory structure
        self.source_dir = os.path.join(self.temp_dir, "source")
        os.makedirs(self.source_dir)
        
        # Create multiple test files with different API usage patterns
        self.create_test_files()
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_files(self):
        """Create test files with various API usage patterns."""
        
        # File 1: Simple requests usage
        file1_content = """
import requests

def fetch_user(user_id):
    response = requests.get("https://api.example.com/users/" + str(user_id), timeout=30)
    return response.json()

def create_user(data):
    return requests.post("https://api.example.com/users", data=data, timeout=60)
"""
        with open(os.path.join(self.source_dir, "user_api.py"), 'w') as f:
            f.write(file1_content)
        
        # File 2: Complex requests usage with class
        file2_content = """
import requests
import json

class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
    
    def get_data(self, endpoint, params=None):
        response = requests.get(
            f"{self.base_url}/{endpoint}",
            params=params,
            timeout=45,
            headers={'Authorization': 'Bearer token'}
        )
        return response.json()
    
    def post_data(self, endpoint, data):
        response = requests.post(
            f"{self.base_url}/{endpoint}",
            data=json.dumps(data),
            timeout=60
        )
        return response.json()
    
    def batch_requests(self, requests_list):
        results = []
        for req in requests_list:
            if req['type'] == 'get':
                response = requests.get(req['url'], timeout=30)
                results.append(response.json())
            elif req['type'] == 'post':
                response = requests.post(req['url'], data=req['data'], timeout=120)
                results.append(response.json())
        return results
"""
        with open(os.path.join(self.source_dir, "client.py"), 'w') as f:
            f.write(file2_content)
        
        # File 3: Mixed API usage
        file3_content = """
import requests
from typing import Dict, Any

class DataService:
    def __init__(self):
        self.session = requests.Session()
    
    def fetch_with_custom_timeout(self, url, timeout_seconds=30):
        return self.session.get(url, timeout=timeout_seconds)
    
    def update_record(self, record_id: int, data: Dict[str, Any]):
        url = f"https://api.example.com/records/{record_id}"
        return requests.put(url, data=json.dumps(data), timeout=90)
    
    def delete_with_long_timeout(self, item_id):
        return requests.delete(f"https://api.example.com/items/{item_id}", timeout=300)
"""
        with open(os.path.join(self.source_dir, "service.py"), 'w') as f:
            f.write(file3_content)
        
        # File 4: File with no requests usage (control)
        file4_content = """
import json
from datetime import datetime

def format_timestamp(timestamp):
    return datetime.fromtimestamp(timestamp).isoformat()

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)
"""
        with open(os.path.join(self.source_dir, "utils.py"), 'w') as f:
            f.write(file4_content)
    
    def test_complete_migration_pipeline(self):
        """Test the complete migration pipeline from analysis to execution."""
        target_dir = os.path.join(self.temp_dir, "target")
        
        # Step 1: Create project
        project_id = self.engine.create_project(
            "requests_migration", self.source_dir, target_dir
        )
        
        self.assertIsNotNone(project_id)
        self.assertIn(project_id, self.engine.projects)
        
        # Step 2: Analyze project
        analysis_results = self.engine.analyze_project(project_id)
        
        self.assertIsInstance(analysis_results, dict)
        self.assertIn("api_entities", analysis_results)
        self.assertIn("transformation_opportunities", analysis_results)
        
        # Should find API entities in our test files
        self.assertGreater(len(analysis_results["api_entities"]), 0)
        
        # Should find transformation opportunities for requests usage
        opportunities = analysis_results["transformation_opportunities"]
        self.assertGreater(len(opportunities), 0)
        
        # Check that we found opportunities in the right files
        file_names = {opp["file"] for opp in opportunities}
        self.assertIn("user_api.py", file_names)
        self.assertIn("client.py", file_names)
        self.assertIn("service.py", file_names)
        # utils.py should not have requests usage
        self.assertNotIn("utils.py", file_names)
        
        # Step 3: Plan transformations
        operations = self.engine.plan_transformations(project_id)
        
        self.assertIsInstance(operations, list)
        
        # Should have operations for files with requests usage
        operation_files = {op.file_path for op in operations}
        self.assertIn("user_api.py", operation_files)
        self.assertIn("client.py", operation_files)
        self.assertIn("service.py", operation_files)
        
        # Step 4: Execute transformations (dry run first)
        execution_results = self.engine.execute_transformations(project_id, dry_run=True)
        
        self.assertIsInstance(execution_results, dict)
        self.assertIn("total_operations", execution_results)
        self.assertIn("successful_operations", execution_results)
        self.assertEqual(execution_results["total_operations"], len(operations))
        
        # Step 5: Execute transformations (real execution)
        execution_results = self.engine.execute_transformations(project_id, dry_run=False)
        
        self.assertIsInstance(execution_results, dict)
        self.assertIn("backup_path", execution_results)
        self.assertGreater(execution_results["successful_operations"], 0)
        
        # Step 6: Verify transformed files exist
        for operation in operations:
            target_file = os.path.join(target_dir, operation.file_path)
            self.assertTrue(os.path.exists(target_file))
            
            # Read and verify transformation was applied
            with open(target_file, 'r') as f:
                content = f.read()
            
            # Should contain scaled timeout values (e.g., 30*1000 instead of 30)
            if "timeout" in content:
                self.assertIn("*1000", content)
        
        # Step 7: Verify control file was copied unchanged
        utils_target = os.path.join(target_dir, "utils.py")
        self.assertTrue(os.path.exists(utils_target))
        
        with open(utils_target, 'r') as f:
            utils_content = f.read()
        
        # Should still contain only json and datetime imports, no requests
        self.assertNotIn("requests", utils_content)
        
        # Step 8: Export project report
        report_path = os.path.join(self.temp_dir, "migration_report.json")
        exported_path = self.engine.export_project_report(project_id, report_path)
        
        self.assertEqual(exported_path, report_path)
        self.assertTrue(os.path.exists(report_path))
        
        # Verify report content
        import json
        with open(report_path, 'r') as f:
            report = json.load(f)
        
        self.assertIn("project_info", report)
        self.assertIn("transformation_summary", report)
        self.assertIn("operations", report)
        
        # Check proof certificates
        for operation in operations:
            if operation.proof_certificate:
                self.assertIn("transformation_id", operation.proof_certificate)
                self.assertIn("proofs", operation.proof_certificate)
    
    def test_migration_with_rollback(self):
        """Test migration with rollback capability."""
        target_dir = os.path.join(self.temp_dir, "target")
        
        # Create project and execute migration
        project_id = self.engine.create_project(
            "rollback_test", self.source_dir, target_dir
        )
        
        self.engine.analyze_project(project_id)
        operations = self.engine.plan_transformations(project_id)
        self.engine.execute_transformations(project_id, dry_run=False)
        
        # Verify files were created
        for operation in operations:
            target_file = os.path.join(target_dir, operation.file_path)
            self.assertTrue(os.path.exists(target_file))
        
        # Test rollback
        rollback_success = self.engine.rollback_transformations(
            project_id, RollbackStrategy.FULL_ROLLBACK
        )
        
        self.assertTrue(rollback_success)
        
        # Verify files were removed
        for operation in operations:
            target_file = os.path.join(target_dir, operation.file_path)
            self.assertFalse(os.path.exists(target_file))
    
    def test_partial_rollback(self):
        """Test partial rollback functionality."""
        target_dir = os.path.join(self.temp_dir, "target")
        
        project_id = self.engine.create_project(
            "partial_rollback_test", self.source_dir, target_dir
        )
        
        self.engine.analyze_project(project_id)
        operations = self.engine.plan_transformations(project_id)
        
        if not operations:
            self.skipTest("No operations were planned")
        
        # Execute transformations
        self.engine.execute_transformations(project_id, dry_run=False)
        
        # Mark one operation as failed (simulate failure)
        if operations:
            operations[0].status = "failed"
        
        # Test partial rollback
        rollback_success = self.engine.rollback_transformations(
            project_id, RollbackStrategy.PARTIAL_ROLLBACK
        )
        
        self.assertTrue(rollback_success)
        
        # Check that failed operations were rolled back
        target_file = os.path.join(target_dir, operations[0].file_path)
        self.assertFalse(os.path.exists(target_file))
    
    def test_evidence_generation(self):
        """Test generation of proof certificates and evidence."""
        target_dir = os.path.join(self.temp_dir, "target")
        
        project_id = self.engine.create_project(
            "evidence_test", self.source_dir, target_dir
        )
        
        self.engine.analyze_project(project_id)
        operations = self.engine.plan_transformations(project_id)
        
        if not operations:
            self.skipTest("No operations were planned")
        
        self.engine.execute_transformations(project_id, dry_run=False)
        
        # Check proof certificates
        certificates_generated = 0
        for operation in operations:
            if operation.proof_certificate:
                certificates_generated += 1
                
                certificate = operation.proof_certificate
                self.assertIn("transformation_id", certificate)
                self.assertIn("timestamp", certificate)
                self.assertIn("original_code_hash", certificate)
                self.assertIn("transformed_code_hash", certificate)
                self.assertIn("proofs", certificate)
                
                # Verify proof structure
                for proof in certificate["proofs"]:
                    self.assertIn("rule_name", proof)
                    self.assertIn("confidence", proof)
                    self.assertIn("proof_obligation", proof)
        
        self.assertGreater(certificates_generated, 0)


class TestPerformanceBenchmarks(unittest.TestCase):
    """Performance benchmarks for the migration system."""
    
    def setUp(self):
        """Set up performance test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.engine = TransformationEngine(workspace_dir=self.temp_dir)
    
    def tearDown(self):
        """Clean up performance test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_large_test_project(self, num_files: int = 50) -> str:
        """Create a large test project with many files."""
        source_dir = os.path.join(self.temp_dir, "large_project")
        os.makedirs(source_dir)
        
        for i in range(num_files):
            content = f"""
import requests
import json

def function_{i}():
    # Various API calls
    response1 = requests.get('https://api.example.com/endpoint{i}', timeout=30)
    response2 = requests.post('https://api.example.com/create', data={{'id': {i}}}, timeout=60)
    response3 = requests.put(f'https://api.example.com/update/{{i}}', timeout=45)
    return [response1.json(), response2.json(), response3.json()]

class APIHandler_{i}:
    def __init__(self):
        self.timeout = 30
    
    def get_data(self, endpoint):
        return requests.get(f'https://api.example.com/{{endpoint}}', timeout=self.timeout)
    
    def post_data(self, data):
        return requests.post('https://api.example.com/data', json=data, timeout=120)
"""
            with open(os.path.join(source_dir, f"file_{i}.py"), 'w') as f:
                f.write(content)
        
        return source_dir
    
    def benchmark_analysis_performance(self):
        """Benchmark the analysis performance."""
        source_dir = self.create_large_test_project(num_files=20)
        target_dir = os.path.join(self.temp_dir, "target")
        
        project_id = self.engine.create_project(
            "performance_test", source_dir, target_dir
        )
        
        start_time = time.time()
        analysis_results = self.engine.analyze_project(project_id)
        end_time = time.time()
        
        analysis_time = end_time - start_time
        
        # Performance assertions
        self.assertLess(analysis_time, 10.0)  # Should complete within 10 seconds
        self.assertIsInstance(analysis_results, dict)
        
        print(f"Analysis of 20 files completed in {analysis_time:.2f} seconds")
    
    def benchmark_transformation_performance(self):
        """Benchmark the transformation performance."""
        source_dir = self.create_large_test_project(num_files=20)
        target_dir = os.path.join(self.temp_dir, "target")
        
        project_id = self.engine.create_project(
            "performance_test", source_dir, target_dir
        )
        
        # Measure analysis time
        start_time = time.time()
        self.engine.analyze_project(project_id)
        analysis_time = time.time() - start_time
        
        # Measure planning time
        start_time = time.time()
        operations = self.engine.plan_transformations(project_id)
        planning_time = time.time() - start_time
        
        # Measure execution time
        start_time = time.time()
        execution_results = self.engine.execute_transformations(project_id, dry_run=True)
        execution_time = time.time() - start_time
        
        # Performance assertions
        self.assertLess(planning_time, 5.0)  # Should complete within 5 seconds
        self.assertLess(execution_time, 3.0)  # Should complete within 3 seconds
        
        print(f"Performance results:")
        print(f"  Analysis: {analysis_time:.2f}s")
        print(f"  Planning: {planning_time:.2f}s")
        print(f"  Execution: {execution_time:.2f}s")
        print(f"  Total operations: {len(operations)}")


if __name__ == '__main__':
    unittest.main()