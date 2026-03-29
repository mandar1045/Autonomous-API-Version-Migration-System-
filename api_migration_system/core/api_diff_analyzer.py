"""
API Difference Analyzer Module

This module provides functionality to analyze API differences between versions
of source code, supporting both Python and JavaScript.
"""

import ast
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path


class ChangeType(Enum):
    """Types of API changes."""
    SIGNATURE_CHANGED = "signature_changed"
    PARAMETER_ADDED = "parameter_added"
    PARAMETER_REMOVED = "parameter_removed"
    PARAMETER_TYPE_CHANGED = "parameter_type_changed"
    RETURN_TYPE_CHANGED = "return_type_changed"
    FUNCTION_ADDED = "function_added"
    FUNCTION_REMOVED = "function_removed"


@dataclass
class APIEntity:
    """Represents an API entity (function, method, etc.)."""
    name: str
    module: str
    signature: Dict[str, Any]
    docstring: Optional[str] = None
    language: str = "python"  # "python" or "javascript"
    ast_node: Optional[ast.AST] = field(default=None, compare=False, hash=False)

    def __hash__(self):
        return hash((self.name, self.module))

    def __eq__(self, other):
        if not isinstance(other, APIEntity):
            return NotImplemented
        return self.name == other.name and self.module == other.module


@dataclass
class APIDiff:
    """Represents a difference between API versions."""
    change_type: ChangeType
    description: str
    confidence: float
    old_entity: Optional[APIEntity] = None
    new_entity: Optional[APIEntity] = None


class APIDiffAnalyzer:
    """Analyzes API differences between source code versions."""

    def __init__(self):
        """Initialize the analyzer."""
        pass

    def _detect_language(self, source_code: str) -> str:
        """Detect the programming language of the source code."""
        # Simple heuristics
        if re.search(r'\bfunction\s+\w+\s*\(', source_code) or 'fetch(' in source_code or 'XMLHttpRequest' in source_code:
            return "javascript"
        elif re.search(r'\bdef\s+\w+\s*\(', source_code) or 'import ' in source_code:
            return "python"
        else:
            return "unknown"

    def analyze_source_code(self, source_code: str, module_name: str = "unknown") -> List[APIEntity]:
        """Analyze source code and extract API entities."""
        language = self._detect_language(source_code)

        if language == "python":
            return self._analyze_python_code(source_code, module_name)
        elif language == "javascript":
            return self._analyze_javascript_code(source_code, module_name)
        else:
            return []

    def _analyze_python_code(self, source_code: str, module_name: str) -> List[APIEntity]:
        """Analyze Python source code using AST."""
        entities = []
        try:
            tree = ast.parse(source_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Extract class methods with ClassName.method_name format
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            entity = self._extract_function_entity(item, source_code, module_name)
                            if entity:
                                entity.name = f"{node.name}.{item.name}"
                                entities.append(entity)
                elif isinstance(node, ast.FunctionDef):
                    # Skip methods already captured from ClassDef walk
                    # Check if this function is directly in the module (not in a class)
                    is_class_method = False
                    for parent in ast.walk(tree):
                        if isinstance(parent, ast.ClassDef):
                            for item in parent.body:
                                if item is node:
                                    is_class_method = True
                                    break
                    if not is_class_method:
                        entity = self._extract_function_entity(node, source_code, module_name)
                        if entity:
                            entities.append(entity)
        except SyntaxError:
            # If AST parsing fails, try regex fallback
            entities = self._analyze_python_with_regex(source_code, module_name)
        return entities

    def _analyze_javascript_code(self, source_code: str, module_name: str) -> List[APIEntity]:
        """Analyze JavaScript source code using regex patterns."""
        entities = []
        found_names = set()

        # Pattern for async functions: async function name(params)
        async_func_pattern = r'async\s+function\s+(\w+)\s*\(([^)]*)\)'
        for match in re.finditer(async_func_pattern, source_code):
            name = match.group(1)
            if name in found_names:
                continue
            found_names.add(name)
            params_str = match.group(2)
            params = [p.strip() for p in params_str.split(',') if p.strip()]

            entity = APIEntity(
                name=name,
                module=module_name,
                signature={'args': [{'name': p, 'type': 'unknown'} for p in params]},
                language="javascript"
            )
            entities.append(entity)

        # Pattern for regular function declarations: function name(params)
        func_pattern = r'(?<!async\s)function\s+(\w+)\s*\(([^)]*)\)'
        for match in re.finditer(func_pattern, source_code):
            name = match.group(1)
            if name in found_names:
                continue
            found_names.add(name)
            params_str = match.group(2)
            params = [p.strip() for p in params_str.split(',') if p.strip()]

            entity = APIEntity(
                name=name,
                module=module_name,
                signature={'args': [{'name': p, 'type': 'unknown'} for p in params]},
                language="javascript"
            )
            entities.append(entity)

        # Pattern for arrow functions: const name = (params) => or async (params) =>
        arrow_pattern = r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:\(([^)]*)\)|([^=>\s]+))\s*=>'
        for match in re.finditer(arrow_pattern, source_code):
            name = match.group(1)
            if name in found_names:
                continue
            found_names.add(name)
            params_str = match.group(2) if match.group(2) else ""
            params = [p.strip() for p in params_str.split(',') if p.strip()]

            entity = APIEntity(
                name=name,
                module=module_name,
                signature={'args': [{'name': p, 'type': 'unknown'} for p in params]},
                language="javascript"
            )
            entities.append(entity)

        return entities

    def _analyze_python_with_regex(self, source_code: str, module_name: str) -> List[APIEntity]:
        """Fallback analysis for Python using regex."""
        entities = []
        func_pattern = r'def\s+(\w+)\s*\(([^)]*)\):'
        for match in re.finditer(func_pattern, source_code):
            name = match.group(1)
            params_str = match.group(2)
            params = [p.strip().split('=')[0].strip() for p in params_str.split(',') if p.strip() and p.strip() != 'self']

            entity = APIEntity(
                name=name,
                module=module_name,
                signature={'args': [{'name': p, 'type': 'unknown'} for p in params]},
                language="python"
            )
            entities.append(entity)
        return entities

    def _extract_function_entity(
        self,
        node: ast.FunctionDef,
        source_code: str,
        module_name: str = "unknown",
    ) -> Optional[APIEntity]:
        """Extract API entity from AST FunctionDef node."""
        # Get function signature
        args = []
        for arg in node.args.args:
            arg_info = {'name': arg.arg}
            if arg.annotation:
                arg_info['type'] = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else str(arg.annotation)
            else:
                arg_info['type'] = 'unknown'
            args.append(arg_info)

        # Get docstring
        docstring = ast.get_docstring(node)

        return APIEntity(
            name=node.name,
            module=module_name,
            signature={'args': args},
            docstring=docstring,
            language="python",
            ast_node=node
        )

    def analyze_file(self, file_path: str) -> List[APIEntity]:
        """Analyze a file and extract API entities."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            module_name = Path(file_path).stem
            return self.analyze_source_code(source_code, module_name)
        except Exception:
            return []

    def extract_api_usage(self, source_code: str, api_name: str) -> List[Dict[str, Any]]:
        """Extract API usage patterns from source code."""
        usages = []

        if self._detect_language(source_code) == "javascript":
            return self._extract_js_api_usage(source_code, api_name)
        else:
            return self._extract_python_api_usage(source_code, api_name)

    def _extract_js_api_usage(self, source_code: str, api_name: str) -> List[Dict[str, Any]]:
        """Extract JavaScript API usage."""
        usages = []

        # Look for fetch calls
        if api_name == "fetch":
            fetch_pattern = r'fetch\s*\(\s*["\'`]([^"\'`]+)["\'`]\s*,\s*\{([^}]+)\}'
            for match in re.finditer(fetch_pattern, source_code, re.DOTALL):
                url = match.group(1)
                options = match.group(2)

                usage = {
                    'api_name': 'fetch',
                    'url': url,
                    'method': 'GET',  # default
                    'keyword_arguments': {}
                }

                # Extract method
                method_match = re.search(r'method\s*:\s*["\'`]([^"\'`]+)["\'`]', options)
                if method_match:
                    usage['method'] = method_match.group(1)

                # Extract timeout
                timeout_match = re.search(r'timeout\s*:\s*(\d+)', options)
                if timeout_match:
                    usage['keyword_arguments']['timeout'] = timeout_match.group(1)

                usages.append(usage)

        return usages

    def _extract_python_api_usage(self, source_code: str, api_name: str) -> List[Dict[str, Any]]:
        """Extract Python API usage."""
        usages = []

        if api_name == "requests":
            # Broad pattern that handles f-strings and multi-line calls
            broad_pattern = api_name + r'\.(\w+)\s*\(([^)]*(?:\([^)]*\)[^)]*)*)\)'
            for match in re.finditer(broad_pattern, source_code, re.DOTALL):
                method = match.group(1)
                args_str = match.group(2)

                # Try to extract the URL
                url = ""
                url_match = re.search(r"""['\"](?:https?://[^'\"]+)['\"]""", args_str)
                if url_match:
                    url = url_match.group(0).strip("'\"")
                else:
                    furl_match = re.search(r"""f['\"]([^'\"]*)['\"]""", args_str)
                    if furl_match:
                        url = furl_match.group(1)

                usage = {
                    'api_name': f'requests.{method}',
                    'url': url,
                    'keyword_arguments': {}
                }

                # Extract timeout
                timeout_match = re.search(r'timeout\s*=\s*(\d+)', args_str)
                if timeout_match:
                    usage['keyword_arguments']['timeout'] = timeout_match.group(1)

                usages.append(usage)

        return usages

    def compare_versions(self, old_entities: List[APIEntity], new_entities: List[APIEntity]) -> List[APIDiff]:
        """Compare two versions of API entities."""
        diffs = []
        old_dict = {self._entity_key(e): e for e in old_entities}
        new_dict = {self._entity_key(e): e for e in new_entities}

        matched_old = set()
        matched_new = set()

        # Exact-key matches first (same module.name)
        for key in old_dict.keys() & new_dict.keys():
            old_entity = old_dict[key]
            new_entity = new_dict[key]
            matched_old.add(key)
            matched_new.add(key)

            signature_changes = self._compare_signatures(old_entity, new_entity)
            if signature_changes['overall_change']:
                diffs.append(APIDiff(
                    change_type=ChangeType.SIGNATURE_CHANGED,
                    description=f"Signature of {old_entity.name} changed",
                    confidence=0.9,
                    old_entity=old_entity,
                    new_entity=new_entity
                ))

        # Fuzzy matching for unmatched entities (possible renames)
        unmatched_old = {k: v for k, v in old_dict.items() if k not in matched_old}
        unmatched_new = {k: v for k, v in new_dict.items() if k not in matched_new}

        for old_key, old_entity in list(unmatched_old.items()):
            best_match = None
            best_similarity = 0.0
            for new_key, new_entity in list(unmatched_new.items()):
                # Baseline string similarity
                str_sim = self._calculate_similarity(old_entity.name, new_entity.name)
                
                # Structural similarity (if both are Python nodes)
                struct_sim = 0.0
                if old_entity.language == 'python' and new_entity.language == 'python':
                    struct_sim = self._calculate_structural_similarity(old_entity.ast_node, new_entity.ast_node)
                
                # Blend scores: 40% name, 60% structure (if structural is available), else just name
                sim = (0.4 * str_sim + 0.6 * struct_sim) if struct_sim > 0 else str_sim

                if sim > best_similarity and sim >= 0.4:
                    best_similarity = sim
                    best_match = (new_key, new_entity)

            if best_match:
                new_key, new_entity = best_match
                del unmatched_old[old_key]
                del unmatched_new[new_key]
                diffs.append(APIDiff(
                    change_type=ChangeType.SIGNATURE_CHANGED,
                    description=f"Signature of {old_entity.name} changed (renamed to {new_entity.name})",
                    confidence=best_similarity,
                    old_entity=old_entity,
                    new_entity=new_entity
                ))

        # Remaining unmatched → added/removed
        for key, new_entity in unmatched_new.items():
            diffs.append(APIDiff(
                change_type=ChangeType.FUNCTION_ADDED,
                description=f"Function {new_entity.name} was added",
                confidence=1.0,
                new_entity=new_entity
            ))

        for key, old_entity in unmatched_old.items():
            diffs.append(APIDiff(
                change_type=ChangeType.FUNCTION_REMOVED,
                description=f"Function {old_entity.name} was removed",
                confidence=1.0,
                old_entity=old_entity
            ))

        return diffs

    def _compare_signatures(self, old_entity: APIEntity, new_entity: APIEntity) -> Dict[str, Any]:
        """Compare function signatures."""
        old_args = old_entity.signature.get('args', [])
        new_args = new_entity.signature.get('args', [])

        changes = {
            'overall_change': False,
            'parameter_changes': []
        }

        if len(old_args) != len(new_args):
            changes['overall_change'] = True
            changes['parameter_changes'].append({
                'type': 'count_change',
                'old_count': len(old_args),
                'new_count': len(new_args)
            })

        return changes

    def _entity_key(self, entity: APIEntity) -> str:
        """Generate a unique key for an API entity."""
        return f"{entity.module}.{entity.name}"

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity using simple ratio."""
        if not str1 or not str2:
            return 0.0 if str1 or str2 else 1.0

        # Simple Levenshtein-like similarity
        import difflib
        return difflib.SequenceMatcher(None, str1, str2).ratio()

    def _calculate_structural_similarity(self, node1: Optional[ast.AST], node2: Optional[ast.AST]) -> float:
        """Calculate structural similarity between two AST nodes based on statement counts."""
        if not node1 or not node2:
            return 0.0
            
        from collections import Counter
        def get_profile(node):
            counter = Counter()
            for child in ast.walk(node):
                # We skip certain common nodes like Load, Store, formatting
                if isinstance(child, (ast.Load, ast.Store, ast.alias, ast.Name)):
                    continue
                counter[type(child).__name__] += 1
            return counter
            
        p1 = get_profile(node1)
        p2 = get_profile(node2)
        
        all_keys = set(p1.keys()) | set(p2.keys())
        if not all_keys:
            return 1.0
            
        # Cosine similarity approximation or simple intersection over union
        intersection = sum(min(p1[k], p2[k]) for k in all_keys)
        union = sum(max(p1[k], p2[k]) for k in all_keys)
        
        return intersection / union if union > 0 else 0.0
