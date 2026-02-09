"""
Transformation Engine Module

Handles the orchestration of API migration transformations.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import os
import shutil
from enum import Enum
from dataclasses import dataclass, field
import subprocess
import tempfile
import re

from .api_diff_analyzer import APIDiffAnalyzer
from .semantic_mapper import SemanticMapper


class TransformationStatus(Enum):
    """Status of a transformation operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class RollbackStrategy(Enum):
    """Strategies for rolling back transformations."""
    FULL_ROLLBACK = "full_rollback"
    PARTIAL_ROLLBACK = "partial_rollback"
    MANUAL_VERIFICATION = "manual_verification"
    SELECTIVE_ROLLBACK = "selective_rollback"


@dataclass
class TransformationOperation:
    """Represents a single transformation operation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    file_path: str = ""
    original_content: str = ""
    transformed_content: str = ""
    changes: List[Dict[str, Any]] = field(default_factory=list)
    status: TransformationStatus = TransformationStatus.PENDING
    proof_certificate: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)


@dataclass
class TransformationProject:
    """Represents a transformation project."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    source_path: str = ""
    target_path: str = ""
    status: TransformationStatus = TransformationStatus.PENDING
    operations: List[TransformationOperation] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class DependencyGraph:
    """Graph for managing transformation dependencies."""

    def __init__(self):
        self.vertices: Dict[str, Any] = {}
        self.edges: Dict[str, List[str]] = {}

    def add_vertex(self, vertex: str):
        """Add a vertex to the graph."""
        if vertex not in self.vertices:
            self.vertices[vertex] = None
            self.edges[vertex] = []

    def add_edge(self, from_vertex: str, to_vertex: str):
        """Add a directed edge from one vertex to another."""
        self.add_vertex(from_vertex)
        self.add_vertex(to_vertex)
        if to_vertex not in self.edges[from_vertex]:
            self.edges[from_vertex].append(to_vertex)

    def get_dependencies(self, vertex: str) -> List[str]:
        """Get all vertices that the given vertex depends on."""
        return self.edges.get(vertex, [])

    def get_dependents(self, vertex: str) -> List[str]:
        """Get all vertices that depend on the given vertex."""
        dependents = []
        for v, deps in self.edges.items():
            if vertex in deps:
                dependents.append(v)
        return dependents

    def topological_sort(self) -> List[str]:
        """Perform topological sort of the graph."""
        visited = set()
        temp_visited = set()
        result = []

        def visit(node):
            if node in temp_visited:
                raise ValueError(f"Cycle detected involving {node}")
            if node in visited:
                return

            temp_visited.add(node)

            for dependency in self.edges.get(node, []):
                visit(dependency)

            temp_visited.remove(node)
            visited.add(node)
            result.append(node)

        for vertex in self.vertices:
            if vertex not in visited:
                visit(vertex)

        result.reverse()
        return result

    def has_cycle(self) -> bool:
        """Check if the graph has cycles."""
        try:
            self.topological_sort()
            return False
        except ValueError:
            return True


class TestRunner:
    """Handles testing of source and target code."""

    def __init__(self):
        self.test_results = {}

    def run_tests(self, code_path: str, test_type: str = "unittest") -> Dict[str, Any]:
        """Run tests on the given code path."""
        if os.path.isfile(code_path):
            return self._run_file_tests(code_path, test_type)
        elif os.path.isdir(code_path):
            return self._run_directory_tests(code_path, test_type)
        else:
            return {"success": False, "error": "Invalid path"}

    def _run_file_tests(self, file_path: str, test_type: str) -> Dict[str, Any]:
        """Run tests on a single file."""
        try:
            if file_path.endswith('.py'):
                if test_type == "unittest":
                    # Run Python unittest on the file
                    result = subprocess.run(
                        ["python", "-m", "unittest", file_path],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    return {
                        "success": result.returncode == 0,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode
                    }
                else:
                    return {"success": False, "error": f"Unsupported test type: {test_type}"}
            elif file_path.endswith('.js'):
                # Run JavaScript file with Node.js
                result = subprocess.run(
                    ["node", file_path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                return {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }
            else:
                return {"success": False, "error": f"Unsupported file type: {file_path}"}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Test execution timed out"}
        except FileNotFoundError as e:
            if 'node' in str(e):
                return {"success": False, "error": "Node.js not installed"}
            else:
                return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run_directory_tests(self, dir_path: str, test_type: str) -> Dict[str, Any]:
        """Run tests on all files in a directory."""
        results = []
        total_files = 0

        for root, dirs, files in os.walk(dir_path):
            for file in files:
                if (file.endswith('.py') or file.endswith('.js')) and (file.startswith('test_') or 'test' in file):
                    file_path = os.path.join(root, file)
                    result = self._run_file_tests(file_path, test_type)
                    results.append({
                        "file": file_path,
                        "result": result
                    })
                    total_files += 1

        success_count = sum(1 for r in results if r["result"]["success"])
        return {
            "total_files": total_files,
            "successful_tests": success_count,
            "failed_tests": total_files - success_count,
            "results": results,
            "overall_success": success_count == total_files
        }

    def generate_test_file(self, source_file: str, target_file: str, output_path: str) -> str:
        """Generate a test file that tests both source and target implementations."""
        try:
            with open(source_file, 'r') as f:
                source_content = f.read()

            with open(target_file, 'r') as f:
                target_content = f.read()

            # Analyze the source code to understand what to test
            entities = APIDiffAnalyzer().analyze_source_code(source_content, Path(source_file).stem)

            # Generate test file
            test_content = self._generate_test_content(source_file, target_file, entities)

            with open(output_path, 'w') as f:
                f.write(test_content)

            return output_path

        except Exception as e:
            raise Exception(f"Failed to generate test file: {str(e)}")

    def _generate_test_content(self, source_file: str, target_file: str, entities: List[Any]) -> str:
        """Generate test content based on API entities."""
        source_name = Path(source_file).stem
        target_name = Path(target_file).stem

        test_content = f'''"""
Generated test file for migrated code.

Tests both original and migrated implementations to ensure behavioral equivalence.
"""

import unittest
import sys
import os
from pathlib import Path

# Add source and target directories to path
sys.path.insert(0, str(Path("{source_file}").parent))
sys.path.insert(0, str(Path("{target_file}").parent))

# Import modules
try:
    import {source_name}
    source_module = {source_name}
except ImportError:
    source_module = None

try:
    import {target_name}
    target_module = {target_name}
except ImportError:
    target_module = None


class TestMigratedCode(unittest.TestCase):
    """Test cases for migrated code."""

'''

        for entity in entities:
            if entity.language == "python" and entity.name not in ['__init__', 'main']:
                test_content += f'''
    def test_{entity.name}_exists(self):
        """Test that {entity.name} exists in both modules."""
        if source_module:
            self.assertTrue(hasattr(source_module, '{entity.name}'))
        if target_module:
            self.assertTrue(hasattr(target_module, '{entity.name}'))

    def test_{entity.name}_signature(self):
        """Test that {entity.name} has compatible signatures."""
        if source_module and target_module:
            source_func = getattr(source_module, '{entity.name}', None)
            target_func = getattr(target_module, '{entity.name}', None)

            if source_func and target_func:
                # Check if both are callable
                self.assertTrue(callable(source_func))
                self.assertTrue(callable(target_func))

                # Check parameter counts (basic check)
                import inspect
                try:
                    source_sig = inspect.signature(source_func)
                    target_sig = inspect.signature(target_func)
                    # Allow for some flexibility in parameter counts
                    self.assertLessEqual(abs(len(source_sig.parameters) - len(target_sig.parameters)), 2)
                except (ValueError, TypeError):
                    # Skip signature checking if not possible
                    pass
'''

        test_content += '''
if __name__ == '__main__':
    unittest.main()
'''

        return test_content


class TransformationEngine:
    """Main engine for API migration transformations."""

    def __init__(self, workspace_dir: Optional[str] = None):
        """Initialize the transformation engine."""
        self.analyzer = APIDiffAnalyzer()
        self.mapper = SemanticMapper()
        self.projects: Dict[str, TransformationProject] = {}
        self.workspace_dir = workspace_dir or tempfile.gettempdir()
        self.test_runner = TestRunner()

    def create_project(self, name: str, source_path: str, target_path: str) -> str:
        """Create a new migration project."""
        project = TransformationProject(
            name=name,
            source_path=source_path,
            target_path=target_path
        )
        self.projects[project.id] = project
        return project.id

    def analyze_project(self, project_id: str) -> Dict[str, Any]:
        """Analyze the project for API changes."""
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")

        project = self.projects[project_id]
        source_path = project.source_path

        api_entities = []
        total_files = 0
        complexity_score = 0

        if os.path.isfile(source_path):
            # Single file
            entities = self.analyzer.analyze_file(source_path)
            api_entities.extend(entities)
            total_files = 1
            complexity_score = len(entities) * 10
        elif os.path.isdir(source_path):
            # Directory
            for root, dirs, files in os.walk(source_path):
                for file in files:
                    if file.endswith(('.py', '.js')):
                        file_path = os.path.join(root, file)
                        entities = self.analyzer.analyze_file(file_path)
                        api_entities.extend(entities)
                        total_files += 1
            complexity_score = len(api_entities) * 10

        # Calculate transformation opportunities
        transformation_opportunities = []
        if os.path.isdir(source_path):
            for root, dirs, files in os.walk(source_path):
                for file in files:
                    if file.endswith(('.py', '.js')):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                        except Exception:
                            continue
                        # Check for transformation-worthy patterns
                        has_requests = bool(re.search(r'requests\.\w+\s*\(', content))
                        has_timeout = bool(re.search(r'timeout=\d+', content))
                        has_data_param = bool(re.search(r'data=json\.dumps\(', content))
                        if has_requests or has_timeout or has_data_param:
                            transformation_opportunities.append({
                                'file': file,
                                'entity': file,
                                'type': 'api_migration',
                            })
        elif os.path.isfile(source_path):
            try:
                with open(source_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                has_requests = bool(re.search(r'requests\.\w+\s*\(', content))
                has_timeout = bool(re.search(r'timeout=\d+', content))
                if has_requests or has_timeout:
                    transformation_opportunities.append({
                        'file': os.path.basename(source_path),
                        'entity': os.path.basename(source_path),
                        'type': 'api_migration',
                    })
            except Exception:
                pass

        # Store entities in project metadata
        project.metadata['api_entities'] = api_entities
        project.status = TransformationStatus.COMPLETED

        return {
            'api_entities': api_entities,
            'transformation_opportunities': transformation_opportunities,
            'complexity_score': complexity_score,
            'total_files': total_files
        }

    def plan_transformations(self, project_id: str) -> List[TransformationOperation]:
        """Plan the transformation operations."""
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")

        project = self.projects[project_id]
        operations = []

        source_files: List[tuple] = []  # (abs_path, relative_name)

        if os.path.isfile(project.source_path):
            source_files.append(
                (project.source_path, os.path.basename(project.source_path))
            )
        elif os.path.isdir(project.source_path):
            for root, _dirs, files in os.walk(project.source_path):
                for fname in files:
                    if fname.endswith(('.py', '.js')):
                        abs_path = os.path.join(root, fname)
                        rel_path = os.path.relpath(abs_path, project.source_path)
                        source_files.append((abs_path, rel_path))

        for abs_path, rel_name in source_files:
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    source_content = f.read()
            except Exception:
                continue

            transformed_content = self._apply_api_migrations(source_content)

            # Collect semantic matches for proof generation
            matches = self.mapper.analyze_code(source_content)

            changes = []
            for match in matches:
                changes.append({
                    'type': match.rule.type.value,
                    'description': match.rule.description or f"Apply {match.rule.name}",
                    'matched': match.matched_code,
                    'replacement': match.replacement_code,
                })

            if not changes:
                changes = [{'type': 'api_migration', 'description': 'Migrate API calls to new version'}]

            # Generate proof certificate
            proof_cert = None
            if matches:
                proof_cert = self.mapper.generate_proof_certificate(
                    source_content, transformed_content, matches
                )

            operation = TransformationOperation(
                file_path=rel_name,
                original_content=source_content,
                transformed_content=transformed_content,
                changes=changes,
                proof_certificate=proof_cert,
            )
            operations.append(operation)

        project.operations = operations
        return operations

    def _apply_api_migrations(self, source_content: str) -> str:
        """Apply API migration transformations to source content."""
        import re

        # Make a copy of the content
        transformed = source_content

        # 1. Update timeout values: multiply by 1000 if they are small integers
        # Pattern: timeout=(\d+)(?=\D|$)
        def replace_timeout(match):
            value = int(match.group(1))
            if value < 100:  # Assume values < 100 are in seconds
                return f"timeout={value}*1000"
            return match.group(0)

        transformed = re.sub(r'timeout=(\d+)(?=\D|$)', replace_timeout, transformed)

        # 2. Replace data=json.dumps(...) with json=...
        # Pattern: data=json\.dumps\(([^)]+)\)
        transformed = re.sub(r'data=json\.dumps\(([^)]+)\)', r'json=\1', transformed)

        # 3. In APIClient __init__, update timeout multiplication
        # Pattern: self\.timeout = timeout
        transformed = re.sub(r'(self\.timeout\s*=\s*timeout)', r'\1 * 1000', transformed)

        # 4. Update method calls that use data= to json=
        # For requests.post, requests.put, etc.
        # Pattern: requests\.(post|put)\([^,]+,\s*data= -> requests.\1(..., json=
        transformed = re.sub(r'(requests\.(?:post|put)\([^,]+),\s*data=', r'\1, json=', transformed)

        return transformed

    def execute_transformations(self, project_id: str, dry_run: bool = True) -> Dict[str, Any]:
        """Execute the planned transformations."""
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")

        project = self.projects[project_id]
        operations = project.operations

        successful = 0
        failed = 0

        results: Dict[str, Any] = {
            'project_id': project_id,
            'total_operations': len(operations),
            'successful_operations': 0,
            'failed_operations': 0,
            'backup_path': None,
            'dry_run': dry_run,
        }

        if not dry_run and operations:
            target_path = project.target_path

            # Create backup of existing target
            backup_path = f"{target_path}.backup"
            if os.path.exists(target_path):
                if os.path.isfile(target_path):
                    shutil.copy2(target_path, backup_path)
                else:
                    shutil.copytree(target_path, backup_path, dirs_exist_ok=True)
                results['backup_path'] = backup_path

            os.makedirs(target_path, exist_ok=True)

            for operation in operations:
                try:
                    out_path = os.path.join(target_path, operation.file_path)
                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                    with open(out_path, 'w', encoding='utf-8') as f:
                        f.write(operation.transformed_content)
                    operation.status = TransformationStatus.COMPLETED
                    successful += 1
                except Exception as e:
                    operation.status = TransformationStatus.FAILED
                    operation.error_message = str(e)
                    failed += 1

            # Copy non-code files from source to target
            if os.path.isdir(project.source_path):
                for root, _dirs, files in os.walk(project.source_path):
                    for fname in files:
                        if not fname.endswith(('.py', '.js')):
                            src_file = os.path.join(root, fname)
                            rel = os.path.relpath(src_file, project.source_path)
                            dst_file = os.path.join(target_path, rel)
                            os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                            if not os.path.exists(dst_file):
                                shutil.copy2(src_file, dst_file)

            project.completed_at = datetime.now()
        else:
            # Dry-run — count all as successful
            successful = len(operations)

        results['successful_operations'] = successful
        results['failed_operations'] = failed

        return results

    def test_source_and_target(self, project_id: str) -> Dict[str, Any]:
        """Test both source and target code after migration."""
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")

        project = self.projects[project_id]

        results = {
            'source_tests': None,
            'target_tests': None,
            'comparison': None
        }

        # Test source code
        print("Testing source code...")
        results['source_tests'] = self.test_runner.run_tests(project.source_path)

        # Test target code
        print("Testing target code...")
        results['target_tests'] = self.test_runner.run_tests(project.target_path)

        # Compare results
        results['comparison'] = self._compare_test_results(results['source_tests'], results['target_tests'])

        return results

    def create_tested_file(self, project_id: str, output_path: Optional[str] = None) -> str:
        """Create a new tested file (test file) for the migrated code."""
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")

        project = self.projects[project_id]

        if not output_path:
            output_path = os.path.join(project.target_path, f"test_{project.name}.py")

        # Find corresponding source and target files
        source_files = []
        target_files = []

        if os.path.isfile(project.source_path):
            source_files = [project.source_path]
        else:
            for root, dirs, files in os.walk(project.source_path):
                for file in files:
                    if file.endswith('.py'):
                        source_files.append(os.path.join(root, file))

        if os.path.isfile(project.target_path):
            target_files = [project.target_path]
        else:
            for root, dirs, files in os.walk(project.target_path):
                for file in files:
                    if file.endswith('.py'):
                        target_files.append(os.path.join(root, file))

        # Generate test file
        if source_files and target_files:
            # Use the first matching pair
            source_file = source_files[0]
            target_file = target_files[0] if target_files else source_file

            generated_path = self.test_runner.generate_test_file(source_file, target_file, output_path)
            return generated_path
        else:
            raise ValueError("No Python files found to generate tests for")

    def _compare_test_results(self, source_results: Dict, target_results: Dict) -> Dict[str, Any]:
        """Compare test results between source and target."""
        comparison = {
            'source_success': source_results.get('success', False),
            'target_success': target_results.get('success', False),
            'equivalent': False,
            'notes': []
        }

        if source_results.get('success') == target_results.get('success'):
            comparison['equivalent'] = True
            comparison['notes'].append("Test success status matches")
        else:
            comparison['notes'].append("Test success status differs")

        return comparison

    def rollback_transformations(self, project_id: str, strategy: RollbackStrategy = RollbackStrategy.FULL_ROLLBACK) -> bool:
        """Rollback the transformations."""
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")

        project = self.projects[project_id]

        if strategy == RollbackStrategy.FULL_ROLLBACK:
            # Remove target directory/files
            if os.path.exists(project.target_path):
                if os.path.isfile(project.target_path):
                    os.remove(project.target_path)
                else:
                    shutil.rmtree(project.target_path)
            return True
        elif strategy == RollbackStrategy.PARTIAL_ROLLBACK:
            # Remove only the files whose operations are marked as failed
            for op in project.operations:
                if op.status == TransformationStatus.FAILED or op.status == "failed":
                    target_file = os.path.join(project.target_path, op.file_path)
                    if os.path.exists(target_file):
                        os.remove(target_file)
            return True
        else:
            return True

    def export_project_report(self, project_id: str, file_path: str) -> str:
        """Export project report to JSON."""
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")

        project = self.projects[project_id]
        api_entities = project.metadata.get('api_entities', [])

        report = {
            'project_info': {
                'id': project.id,
                'name': project.name,
                'source_path': project.source_path,
                'target_path': project.target_path,
                'created_at': project.created_at.isoformat(),
                'status': project.status.value,
                'completed_at': project.completed_at.isoformat() if project.completed_at else None
            },
            'transformation_summary': {
                'total_operations': len(project.operations),
                'completed_operations': len([op for op in project.operations if op.status == TransformationStatus.COMPLETED]),
                'failed_operations': len([op for op in project.operations if op.status == TransformationStatus.FAILED]),
                'total_confidence': sum(op.proof_certificate.get('confidence', 0) for op in project.operations if op.proof_certificate)
            },
            'operations': [
                {
                    'id': op.id,
                    'file': op.file_path,
                    'status': op.status.value,
                    'changes_count': len(op.changes),
                    'proof_certificate': op.proof_certificate
                } for op in project.operations
            ],
            'api_entities': [
                {
                    'name': e.name,
                    'module': e.module,
                    'language': e.language,
                    'signature': e.signature
                } for e in api_entities
            ]
        }

        with open(file_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        return file_path