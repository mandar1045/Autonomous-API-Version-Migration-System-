"""
Code Transformation Engine - Module 3

Orchestrates the entire API migration process by coordinating:
1. Codebase analysis and dependency graph creation
2. Transformation application with rollback capabilities
3. Context-aware processing
4. Proof certificate generation
"""

import ast
import os
import shutil
import tempfile
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path
import json
import uuid
from datetime import datetime

from .api_diff_analyzer import APIDiffAnalyzer, APIEntity, APIDiff
from .semantic_mapper import SemanticMapper, TransformationMatch, TransformationRule

logger = logging.getLogger(__name__)


class TransformationStatus(Enum):
    """Status of transformation operations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class RollbackStrategy(Enum):
    """Strategies for rollback operations."""
    FULL_ROLLBACK = "full_rollback"  # Rollback entire transformation
    PARTIAL_ROLLBACK = "partial_rollback"  # Rollback specific changes
    MANUAL_VERIFICATION = "manual_verification"  # Require manual verification


@dataclass
class TransformationOperation:
    """Represents a single transformation operation."""
    id: str
    file_path: str
    original_content: str
    transformed_content: str
    changes: List[TransformationMatch]
    status: TransformationStatus = TransformationStatus.PENDING
    proof_certificate: Optional[Dict[str, Any]] = None
    dependencies: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    execution_order: int = 0
    
    def __post_init__(self):
        """Initialize operation ID if not provided."""
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class TransformationProject:
    """Represents a complete transformation project."""
    id: str
    name: str
    source_path: str
    target_path: str
    operations: List[TransformationOperation] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    status: TransformationStatus = TransformationStatus.PENDING


class DependencyGraph:
    """Represents dependency relationships between files and transformations."""
    
    def __init__(self):
        self.vertices: Set[str] = set()
        self.edges: Dict[str, Set[str]] = {}
        self.file_dependencies: Dict[str, Set[str]] = {}
    
    def add_vertex(self, vertex: str):
        """Add a vertex to the graph."""
        self.vertices.add(vertex)
        if vertex not in self.edges:
            self.edges[vertex] = set()
    
    def add_edge(self, from_vertex: str, to_vertex: str):
        """Add a directed edge between vertices."""
        self.add_vertex(from_vertex)
        self.add_vertex(to_vertex)
        self.edges[from_vertex].add(to_vertex)
    
    def get_dependencies(self, vertex: str) -> Set[str]:
        """Get all dependencies of a vertex."""
        return self.edges.get(vertex, set())
    
    def get_dependents(self, vertex: str) -> Set[str]:
        """Get all dependents of a vertex."""
        dependents = set()
        for v, deps in self.edges.items():
            if vertex in deps:
                dependents.add(v)
        return dependents
    
    def topological_sort(self) -> List[str]:
        """Perform topological sort of the graph."""
        in_degree = {v: 0 for v in self.vertices}
        for v in self.vertices:
            for dep in self.edges[v]:
                in_degree[dep] += 1
        
        queue = [v for v in self.vertices if in_degree[v] == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            for dependent in self.edges[current]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        return result
    
    def has_cycle(self) -> bool:
        """Check if the graph has a cycle."""
        visited = set()
        rec_stack = set()
        
        def dfs(vertex):
            visited.add(vertex)
            rec_stack.add(vertex)
            
            for dependent in self.edges[vertex]:
                if dependent not in visited:
                    if dfs(dependent):
                        return True
                elif dependent in rec_stack:
                    return True
            
            rec_stack.remove(vertex)
            return False
        
        for vertex in self.vertices:
            if vertex not in visited:
                if dfs(vertex):
                    return True
        
        return False


class TransformationEngine:
    """
    Main orchestration engine for API migration with formal verification.
    
    This engine provides:
    1. Project-based transformation management
    2. Dependency graph analysis and topological sorting
    3. Context-aware transformation ordering
    4. Rollback mechanisms with different strategies
    5. Proof certificate generation and verification
    """
    
    def __init__(self, workspace_dir: Optional[str] = None):
        """
        Initialize the transformation engine.
        
        Args:
            workspace_dir: Directory for temporary files and backups
        """
        self.workspace_dir = workspace_dir or tempfile.mkdtemp(prefix="api_migration_")
        self.projects: Dict[str, TransformationProject] = {}
        self.analyzer = APIDiffAnalyzer()
        self.mapper = SemanticMapper()
        self.backup_dir = os.path.join(self.workspace_dir, "backups")
        os.makedirs(self.backup_dir, exist_ok=True)
        
        logger.info(f"TransformationEngine initialized with workspace: {self.workspace_dir}")
    
    def create_project(self, name: str, source_path: str, target_path: str) -> str:
        """
        Create a new transformation project.
        
        Args:
            name: Name of the transformation project
            source_path: Path to source code to transform
            target_path: Path where transformed code will be written
            
        Returns:
            Project ID
        """
        project_id = str(uuid.uuid4())
        
        # Ensure target directory exists
        os.makedirs(target_path, exist_ok=True)
        
        # Analyze source structure
        source_files = self._analyze_source_structure(source_path)
        
        project = TransformationProject(
            id=project_id,
            name=name,
            source_path=source_path,
            target_path=target_path,
            metadata={
                "source_files": source_files,
                "analysis_results": {}
            }
        )
        
        self.projects[project_id] = project
        logger.info(f"Created transformation project '{name}' with ID: {project_id}")
        
        return project_id
    
    def analyze_project(self, project_id: str) -> Dict[str, Any]:
        """
        Analyze a transformation project for potential changes.
        
        Args:
            project_id: ID of the project to analyze
            
        Returns:
            Analysis results
        """
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        
        project = self.projects[project_id]
        analysis_results = {
            "api_entities": [],
            "api_diffs": [],
            "transformation_opportunities": [],
            "dependencies": {},
            "complexity_score": 0.0
        }
        
        # Analyze all Python files in the project
        for root, dirs, files in os.walk(project.source_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, project.source_path)
                    
                    # Extract API entities
                    entities = self.analyzer.analyze_file(file_path)
                    analysis_results["api_entities"].extend([
                        {
                            "file": relative_path,
                            "entity": entity.name,
                            "signature": entity.signature
                        }
                        for entity in entities
                    ])
                    
                    # Extract API usage patterns
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            source_code = f.read()
                        
                        # Look for requests usage
                        if 'requests' in source_code.lower():
                            usages = self.analyzer.extract_api_usage(source_code, 'requests')
                            analysis_results["transformation_opportunities"].extend([
                                {
                                    "file": relative_path,
                                    "usage": usage,
                                    "potential_rules": self._find_applicable_rules(usage)
                                }
                                for usage in usages
                            ])
                    except Exception as e:
                        logger.warning(f"Error analyzing {file_path}: {e}")
        
        # Calculate complexity score
        analysis_results["complexity_score"] = self._calculate_complexity_score(analysis_results)
        
        project.metadata["analysis_results"] = analysis_results
        logger.info(f"Completed analysis for project {project_id}")
        
        return analysis_results
    
    def plan_transformations(self, project_id: str, target_module: str = "requests") -> List[TransformationOperation]:
        """
        Plan transformations based on analysis results.
        
        Args:
            project_id: ID of the project
            target_module: Module to focus transformations on
            
        Returns:
            List of planned transformation operations
        """
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        
        project = self.projects[project_id]
        analysis_results = project.metadata.get("analysis_results", {})
        
        operations = []
        operation_id = 1
        
        # Group transformations by file
        file_transformations: Dict[str, List[TransformationMatch]] = {}
        
        for opportunity in analysis_results.get("transformation_opportunities", []):
            file_path = opportunity["file"]
            usage = opportunity["usage"]
            potential_rules = opportunity["potential_rules"]
            
            if file_path not in file_transformations:
                file_transformations[file_path] = []
            
            # Create transformations for each applicable rule
            for rule in potential_rules:
                # Simulate code analysis for the specific usage
                original_code = self._reconstruct_api_call(usage)
                # Apply the rule's regex pattern directly to generate transformed_code
                import re
                transformed_code = re.sub(rule.pattern, rule.replacement, original_code)

                if original_code != transformed_code:
                    match = TransformationMatch(
                        rule=rule,
                        matched_code=original_code,
                        replacement_code=transformed_code,
                        confidence=rule.confidence,
                        context={"api_usage": usage}
                    )
                    file_transformations[file_path].append(match)
        
        # Create operations for each file
        for file_path, matches in file_transformations.items():
            source_file = os.path.join(project.source_path, file_path)
            target_file = os.path.join(project.target_path, file_path)
            
            try:
                with open(source_file, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                
                # Apply all transformations to the file content
                transformed_content = original_content
                for match in matches:
                    transformed_content = self.mapper.apply_transformation(transformed_content, match)
                
                # Create operation
                operation = TransformationOperation(
                    id=f"op_{operation_id}",
                    file_path=file_path,
                    original_content=original_content,
                    transformed_content=transformed_content,
                    changes=matches,
                    execution_order=operation_id
                )
                
                operations.append(operation)
                operation_id += 1
                
            except Exception as e:
                logger.error(f"Error planning transformation for {file_path}: {e}")
        
        # Build dependency graph
        dependency_graph = self._build_dependency_graph(operations)
        
        # Sort operations by dependency order
        sorted_operations = []
        sorted_vertices = dependency_graph.topological_sort()
        
        for vertex in sorted_vertices:
            if vertex in [op.file_path for op in operations]:
                operation = next(op for op in operations if op.file_path == vertex)
                sorted_operations.append(operation)
        
        # Update project operations
        project.operations = sorted_operations
        project.dependencies = {op.file_path: list(dependency_graph.get_dependencies(op.file_path)) 
                              for op in sorted_operations}
        
        logger.info(f"Planned {len(operations)} transformation operations for project {project_id}")
        
        return sorted_operations
    
    def execute_transformations(self, project_id: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Execute planned transformations for a project.
        
        Args:
            project_id: ID of the project
            dry_run: If True, only simulate transformations without writing files
            
        Returns:
            Execution results
        """
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        
        project = self.projects[project_id]
        
        execution_results = {
            "project_id": project_id,
            "total_operations": len(project.operations),
            "successful_operations": 0,
            "failed_operations": 0,
            "rollback_operations": [],
            "proof_certificates": [],
            "execution_log": []
        }
        
        if not project.operations:
            logger.warning(f"No operations planned for project {project_id}")
            return execution_results
        
        # Create backup before transformation
        if not dry_run:
            backup_path = self._create_project_backup(project)
            execution_results["backup_path"] = backup_path
        
        # Execute operations in order
        for operation in project.operations:
            try:
                logger.info(f"Executing operation {operation.id} on {operation.file_path}")
                operation.status = TransformationStatus.IN_PROGRESS
                
                if not dry_run:
                    # Write transformed file
                    target_file = os.path.join(project.target_path, operation.file_path)
                    os.makedirs(os.path.dirname(target_file), exist_ok=True)
                    
                    with open(target_file, 'w', encoding='utf-8') as f:
                        f.write(operation.transformed_content)
                    
                    # Generate proof certificate
                    proof_certificate = self.mapper.generate_proof_certificate(
                        operation.original_content,
                        operation.transformed_content,
                        operation.changes
                    )
                    operation.proof_certificate = proof_certificate
                    execution_results["proof_certificates"].append(proof_certificate)
                
                operation.status = TransformationStatus.COMPLETED
                execution_results["successful_operations"] += 1
                execution_results["execution_log"].append({
                    "operation_id": operation.id,
                    "file": operation.file_path,
                    "status": "success",
                    "changes": len(operation.changes)
                })
                
            except Exception as e:
                logger.error(f"Error executing operation {operation.id}: {e}")
                operation.status = TransformationStatus.FAILED
                execution_results["failed_operations"] += 1
                execution_results["execution_log"].append({
                    "operation_id": operation.id,
                    "file": operation.file_path,
                    "status": "failed",
                    "error": str(e)
                })
        
        # Update project status
        if execution_results["failed_operations"] == 0:
            project.status = TransformationStatus.COMPLETED
        else:
            project.status = TransformationStatus.FAILED
        
        logger.info(f"Completed execution for project {project_id}: "
                   f"{execution_results['successful_operations']} successful, "
                   f"{execution_results['failed_operations']} failed")
        
        return execution_results
    
    def rollback_transformations(self, project_id: str, strategy: RollbackStrategy = RollbackStrategy.FULL_ROLLBACK) -> bool:
        """
        Rollback transformations for a project.
        
        Args:
            project_id: ID of the project
            strategy: Rollback strategy to use
            
        Returns:
            True if rollback was successful
        """
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        
        project = self.projects[project_id]
        
        try:
            if strategy == RollbackStrategy.FULL_ROLLBACK:
                return self._full_rollback(project)
            elif strategy == RollbackStrategy.PARTIAL_ROLLBACK:
                return self._partial_rollback(project)
            elif strategy == RollbackStrategy.MANUAL_VERIFICATION:
                return self._manual_verification_rollback(project)
            else:
                raise ValueError(f"Unknown rollback strategy: {strategy}")
        except Exception as e:
            logger.error(f"Error during rollback for project {project_id}: {e}")
            return False
    
    def export_project_report(self, project_id: str, output_path: str) -> str:
        """
        Export a comprehensive report for a transformation project.
        
        Args:
            project_id: ID of the project
            output_path: Path where the report will be written
            
        Returns:
            Path to the generated report
        """
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        
        project = self.projects[project_id]
        
        report = {
            "project_info": {
                "id": project.id,
                "name": project.name,
                "source_path": project.source_path,
                "target_path": project.target_path,
                "status": project.status.value,
                "created_at": project.created_at.isoformat()
            },
            "transformation_summary": {
                "total_operations": len(project.operations),
                "completed_operations": len([op for op in project.operations if op.status == TransformationStatus.COMPLETED]),
                "failed_operations": len([op for op in project.operations if op.status == TransformationStatus.FAILED]),
                "total_confidence": sum(sum(match.confidence for match in op.changes) for op in project.operations) / len(project.operations) if project.operations else 0
            },
            "operations": [
                {
                    "id": op.id,
                    "file": op.file_path,
                    "status": op.status.value,
                    "changes": len(op.changes),
                    "confidence": sum(match.confidence for match in op.changes) / len(op.changes) if op.changes else 0,
                    "proof_certificate": op.proof_certificate
                }
                for op in project.operations
            ],
            "dependencies": project.dependencies,
            "analysis_results": project.metadata.get("analysis_results", {})
        }
        
        # Write report to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Exported project report to {output_path}")
        return output_path
    
    def _analyze_source_structure(self, source_path: str) -> List[str]:
        """Analyze the structure of source code."""
        python_files = []
        for root, dirs, files in os.walk(source_path):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.relpath(os.path.join(root, file), source_path))
        return python_files
    
    def _find_applicable_rules(self, usage: Dict[str, Any]) -> List[TransformationRule]:
        """Find transformation rules applicable to an API usage."""
        applicable_rules = []
        api_name = usage.get('api_name', '')
        
        for rule in self.mapper.transformation_rules.values():
            # Check if the rule applies to this API usage
            if any(keyword in api_name.lower() for keyword in ['requests', 'get', 'post', 'put', 'delete']):
                applicable_rules.append(rule)
        
        return applicable_rules
    
    def _reconstruct_api_call(self, usage: Dict[str, str]) -> str:
        """Reconstruct API call string from usage information."""
        api_name = usage.get('api_name', '')
        args = usage.get('arguments', [])
        kwargs = usage.get('keyword_arguments', {})
        
        # Build argument list
        all_args = args + [f"{k}={v}" for k, v in kwargs.items()]
        
        return f"{api_name}({', '.join(all_args)})"
    
    def _calculate_complexity_score(self, analysis_results: Dict[str, Any]) -> float:
        """Calculate complexity score for transformation project."""
        num_files = len(set(opp["file"] for opp in analysis_results.get("transformation_opportunities", [])))
        num_opportunities = len(analysis_results.get("transformation_opportunities", []))
        num_entities = len(analysis_results.get("api_entities", []))
        
        # Simple complexity calculation
        complexity = (num_files * 0.4) + (num_opportunities * 0.4) + (num_entities * 0.2)
        return min(complexity / 100.0, 1.0)  # Normalize to 0-1 range
    
    def _build_dependency_graph(self, operations: List[TransformationOperation]) -> DependencyGraph:
        """Build dependency graph for transformation operations."""
        graph = DependencyGraph()
        
        # Add all operations as vertices
        for operation in operations:
            graph.add_vertex(operation.file_path)
        
        # Add dependencies based on import relationships
        for operation in operations:
            # Parse imports from original content
            imports = self._extract_imports(operation.original_content)
            
            # Check if other operations depend on this file's exports
            for other_op in operations:
                if other_op.file_path != operation.file_path:
                    other_imports = self._extract_imports(other_op.original_content)
                    
                    # If other_op imports something that might be affected by operation
                    if any(imp in str(operation.changes) for imp in other_imports):
                        graph.add_edge(other_op.file_path, operation.file_path)
        
        return graph
    
    def _extract_imports(self, content: str) -> List[str]:
        """Extract import statements from source code."""
        imports = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
        except:
            pass
        return imports
    
    def _create_project_backup(self, project: TransformationProject) -> str:
        """Create backup of project source files."""
        backup_path = os.path.join(self.backup_dir, f"{project.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copytree(project.source_path, backup_path)
        logger.info(f"Created backup at {backup_path}")
        return backup_path
    
    def _full_rollback(self, project: TransformationProject) -> bool:
        """Perform full rollback of all transformations."""
        try:
            # Remove target files
            for operation in project.operations:
                target_file = os.path.join(project.target_path, operation.file_path)
                if os.path.exists(target_file):
                    os.remove(target_file)
            
            # Update operation statuses
            for operation in project.operations:
                operation.status = TransformationStatus.ROLLED_BACK
            
            project.status = TransformationStatus.ROLLED_BACK
            logger.info(f"Full rollback completed for project {project.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error during full rollback: {e}")
            return False
    
    def _partial_rollback(self, project: TransformationProject) -> bool:
        """Perform partial rollback of failed operations."""
        try:
            for operation in project.operations:
                if operation.status == TransformationStatus.FAILED:
                    target_file = os.path.join(project.target_path, operation.file_path)
                    if os.path.exists(target_file):
                        os.remove(target_file)
                    operation.status = TransformationStatus.ROLLED_BACK
            
            logger.info(f"Partial rollback completed for project {project.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error during partial rollback: {e}")
            return False
    
    def _manual_verification_rollback(self, project: TransformationProject) -> bool:
        """Require manual verification before rollback."""
        logger.info(f"Manual verification rollback requested for project {project.id}")
        logger.info("Manual intervention required - review transformation results before proceeding")
        return True