#!/usr/bin/env python3

import sys
import os
import tempfile
import shutil
import unittest
sys.path.insert(0, os.path.dirname(__file__))

from api_migration_system import TransformationEngine

class DebugTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.engine = TransformationEngine(workspace_dir=self.temp_dir)
        
        # Create source directory structure
        self.source_dir = os.path.join(self.temp_dir, "source")
        os.makedirs(self.source_dir)
        
        self.create_test_files()
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_files(self):
        """Create test files with various API usage patterns."""
        
        # File 1: Simple requests usage
        file1_content = """
import requests

def fetch_user(user_id):
    response = requests.get(f"https://api.example.com/users/{user_id}", timeout=30*1000)
    return response.json()

def create_user(data):
    return requests.post("https://api.example.com/users", json=data, timeout=60*1000)
"""
        with open(os.path.join(self.source_dir, "user_api.py"), 'w') as f:
            f.write(file1_content)
    
    def test_debug(self):
        target_dir = os.path.join(self.temp_dir, "target")
        
        # Step 1: Create project
        project_id = self.engine.create_project(
            "requests_migration", self.source_dir, target_dir
        )
        
        # Step 2: Analyze project
        analysis_results = self.engine.analyze_project(project_id)
        
        opportunities = analysis_results["transformation_opportunities"]
        print(f"Number of opportunities: {len(opportunities)}")
        for opp in opportunities:
            print(f"Opportunity: {opp}")
        
        file_names = {opp["file"] for opp in opportunities}
        print(f"File names: {file_names}")
        
        self.assertIn("user_api.py", file_names)

if __name__ == '__main__':
    unittest.main()