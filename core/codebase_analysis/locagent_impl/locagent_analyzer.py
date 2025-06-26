"""
LocAgent implementation of the CodebaseAnalyzer interface.

This module integrates LocAgent's capabilities into the standardized interface.
"""

import sys
import json
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from utils.logger import logger

# Add LocAgent to path
locagent_path = Path(__file__).parent.parent.parent.parent.parent / "DEL" / "tools" / "LocAgent"
if str(locagent_path) not in sys.path:
    sys.path.append(str(locagent_path))

try:
    from repo_index.repository import FileRepository
    from dependency_graph.build_graph import build_graph
    import networkx as nx
except ImportError as e:
    logger.warning(f"LocAgent modules not available: {e}")
    FileRepository = None
    build_graph = None
    nx = None

from ..interfaces.analyzer import CodebaseAnalyzer
from ..models.context_models import CodebaseContext, CodebaseStats, FileInfo, CodeEntity
from ..models.query_models import QueryRequest, QueryResponse, QueryMatch, QueryType
from ..models.response_models import BugImpactResult, CodebaseFactResult, ImpactedCode, DependencyInfo
from .locagent_storage import LocAgentStorageManager


class LocAgentAnalyzer(CodebaseAnalyzer):
    """
    LocAgent implementation of the CodebaseAnalyzer interface.
    
    Uses LocAgent's dependency graph building and analysis capabilities
    to provide codebase analysis functionality.
    """
    
    def __init__(self, storage_base_path: str, config: Optional[Dict[str, Any]] = None):
        """Initialize LocAgent analyzer."""
        super().__init__(storage_base_path, config)
        
        # Check if LocAgent is available
        if not all([FileRepository, build_graph, nx]):
            raise ImportError("LocAgent dependencies not available. Please ensure LocAgent is properly installed.")
        
        # Initialize LocAgent components
        self.file_repository: Optional[FileRepository] = None
        self.dependency_graph: Optional[nx.MultiDiGraph] = None
        
        # Initialize storage manager
        self.storage_manager = LocAgentStorageManager(str(self.code_analysis_dir))
        
        # Analysis state
        self._analysis_config = self.config.get('analysis', {})
        self._ai_config = self.config.get('ai', {})
        
        logger.info("LocAgent analyzer initialized")
    
    def build_context(self, source_path: str, force_rebuild: bool = False) -> CodebaseContext:
        """
        Build codebase context using LocAgent.
        
        Args:
            source_path: Path to source code to analyze
            force_rebuild: Whether to force a complete rebuild
            
        Returns:
            CodebaseContext with analysis results
        """
        start_time = time.time()
        source_path = Path(source_path).resolve()
        
        logger.info(f"Building context for {source_path}")
        
        try:
            # Check if we should rebuild
            if not force_rebuild and self._should_use_cached_context(str(source_path)):
                logger.info("Using cached context")
                return self._load_cached_context()
            
            # Initialize file repository
            self.file_repository = FileRepository(str(source_path))
            
            # Build dependency graph
            logger.info("Building dependency graph...")
            self.dependency_graph = build_graph(
                str(source_path),
                fuzzy_search=self._analysis_config.get('fuzzy_search', True),
                global_import=self._analysis_config.get('global_import', False)
            )
            
            # Collect file information
            files = self._collect_file_info(source_path)
            
            # Extract entities from graph
            entities = self._extract_entities_from_graph()
            
            # Build dependency mappings
            dependencies, reverse_dependencies = self._build_dependency_mappings()
            
            # Generate statistics
            stats = self._generate_stats(files, entities)
            
            # Create context object
            context = CodebaseContext(
                source_path=str(source_path),
                storage_path=str(self.storage_base_path),
                stats=stats,
                files=files,
                entities=entities,
                dependencies=dependencies,
                reverse_dependencies=reverse_dependencies,
                analyzer_type="locagent",
                analyzer_version=self._get_locagent_version(),
                created_at=datetime.now(),
                analysis_config=self._analysis_config,
                vector_store_path=str(self.vectors_dir),
                graph_store_path=str(self.context_dir),
                text_index_path=str(self.indexes_dir)
            )
            
            # Save context
            self._save_context(context)
            
            # Update state
            self._context_loaded = True
            self._current_source_path = source_path
            
            # Calculate analysis time
            analysis_time = time.time() - start_time
            context.stats.analysis_duration = analysis_time
            
            logger.info(f"Context built successfully in {analysis_time:.2f}s")
            return context
            
        except Exception as e:
            logger.error(f"Failed to build context: {e}")
            raise
    
    def update_context(self, source_path: Optional[str] = None) -> CodebaseContext:
        """Update existing context with changes."""
        if source_path is None:
            source_path = self._current_source_path
        
        if source_path is None:
            raise ValueError("No source path provided and no previous analysis found")
        
        logger.info(f"Updating context for {source_path}")
        
        # For now, do a full rebuild
        # TODO: Implement incremental updates
        return self.build_context(str(source_path), force_rebuild=True)
    
    def query_codebase(self, request: QueryRequest) -> QueryResponse:
        """Query the codebase using LocAgent's capabilities."""
        start_time = time.time()
        
        if not self.dependency_graph:
            raise ValueError("No context loaded. Call build_context() first.")
        
        try:
            matches = []
            
            if request.query_type == QueryType.FIND_FUNCTION:
                matches = self._find_functions(request.query, request.parameters)
            elif request.query_type == QueryType.FIND_CLASS:
                matches = self._find_classes(request.query, request.parameters)
            elif request.query_type == QueryType.FIND_FILE:
                matches = self._find_files(request.query, request.parameters)
            elif request.query_type == QueryType.GET_DEPENDENCIES:
                matches = self._get_dependencies(request.query, request.parameters)
            elif request.query_type == QueryType.GET_CALL_CHAIN:
                matches = self._get_call_chains(request.query, request.parameters)
            elif request.query_type == QueryType.SEARCH_CODE:
                matches = self._search_code(request.query, request.parameters)
            elif request.query_type == QueryType.NATURAL_LANGUAGE:
                return self._handle_natural_language_query(request)
            else:
                # Default to general search
                matches = self._general_search(request.query, request.parameters)
            
            execution_time = time.time() - start_time
            
            response = QueryResponse(
                request=request,
                matches=matches[:request.max_results],
                total_matches=len(matches),
                execution_time=execution_time,
                success=True
            )
            
            logger.debug(f"Query completed in {execution_time:.3f}s with {len(matches)} matches")
            return response
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Query failed: {e}")
            
            return QueryResponse(
                request=request,
                execution_time=execution_time,
                success=False,
                error_message=str(e)
            )
    
    def get_summary(self) -> CodebaseFactResult:
        """Get a high-level summary of the codebase."""
        if not self.dependency_graph:
            raise ValueError("No context loaded. Call build_context() first.")
        
        try:
            context = self._load_cached_context()
            
            result = CodebaseFactResult(
                query="codebase summary",
                response_type="summary",
                confidence_score=1.0,
                data_freshness=context.created_at
            )
            
            # Basic statistics
            result.add_statistic("total_files", context.stats.total_files, "files")
            result.add_statistic("total_functions", context.stats.total_functions, "functions")
            result.add_statistic("total_classes", context.stats.total_classes, "classes")
            result.add_statistic("total_lines", context.stats.total_lines, "lines")
            
            # Language breakdown
            for lang, count in context.stats.languages.items():
                result.add_statistic(f"{lang}_files", count, "files")
            
            # Key facts
            result.add_fact("analyzer_type", context.analyzer_type)
            result.add_fact("last_analysis", context.created_at.isoformat())
            result.add_fact("source_path", context.source_path)
            
            # Generate summary text
            summary_parts = [
                f"Codebase contains {context.stats.total_files} files",
                f"with {context.stats.total_functions} functions and {context.stats.total_classes} classes.",
                f"Languages: {', '.join(context.stats.languages.keys())}.",
                f"Analyzed using {context.analyzer_type} on {context.created_at.strftime('%Y-%m-%d %H:%M')}."
            ]
            result.summary_text = " ".join(summary_parts)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            raise
    
    def analyze_bug_impact(self, 
                          bug_details: str,
                          context_lines: int = 5,
                          max_depth: int = 3) -> BugImpactResult:
        """Analyze bug impact using LocAgent's dependency analysis."""
        if not self.dependency_graph:
            raise ValueError("No context loaded. Call build_context() first.")
        
        start_time = time.time()
        
        try:
            # Extract relevant information from bug details
            extracted_info = self._extract_bug_info(bug_details)
            
            # Find primary impact locations
            primary_locations = self._find_primary_impact_locations(extracted_info, context_lines)
            
            # Find secondary impacts through dependencies
            secondary_impacts = self._find_secondary_impacts(primary_locations, max_depth)
            
            # Analyze call chains
            affected_call_chains = self._find_affected_call_chains(primary_locations)
            
            # Generate recommendations
            suggestions = self._generate_fix_suggestions(bug_details, primary_locations)
            testing_recommendations = self._generate_testing_recommendations(primary_locations, secondary_impacts)
            
            analysis_time = time.time() - start_time
            
            result = BugImpactResult(
                bug_description=bug_details,
                primary_locations=primary_locations,
                secondary_impacts=secondary_impacts,
                affected_call_chains=affected_call_chains,
                analysis_method="static",
                confidence_score=self._calculate_impact_confidence(primary_locations),
                analysis_time=analysis_time,
                suggested_fixes=suggestions,
                testing_recommendations=testing_recommendations,
                risk_assessment=self._assess_risk_level(primary_locations, secondary_impacts)
            )
            
            logger.info(f"Bug impact analysis completed in {analysis_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Bug impact analysis failed: {e}")
            raise
    
    def find_dependent_code(self, 
                           file_path: str, 
                           function_name: Optional[str] = None,
                           class_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find code that depends on the specified component."""
        if not self.dependency_graph:
            raise ValueError("No context loaded. Call build_context() first.")
        
        try:
            dependents = []
            
            # Build target identifier
            if function_name and class_name:
                target = f"{file_path}:{class_name}.{function_name}"
            elif function_name:
                target = f"{file_path}:{function_name}"
            elif class_name:
                target = f"{file_path}:{class_name}"
            else:
                target = file_path
            
            # Find nodes that depend on the target
            for node, data in self.dependency_graph.nodes(data=True):
                # Check for edges pointing to our target
                for successor in self.dependency_graph.successors(node):
                    if successor == target or successor.startswith(target):
                        dependents.append({
                            "dependent_entity": node,
                            "target_entity": successor,
                            "dependency_type": "unknown",  # Would need edge data
                            "file_path": node.split(':')[0] if ':' in node else node,
                            "confidence": 0.8
                        })
            
            return dependents
            
        except Exception as e:
            logger.error(f"Failed to find dependent code: {e}")
            return []
    
    def get_call_chain(self, target_function: str, max_depth: int = 5) -> List[List[str]]:
        """Get call chains leading to the target function."""
        if not self.dependency_graph:
            raise ValueError("No context loaded. Call build_context() first.")
        
        try:
            call_chains = []
            
            # Find all nodes that could be the target function
            target_nodes = []
            for node in self.dependency_graph.nodes():
                if target_function in node:
                    target_nodes.append(node)
            
            if not target_nodes:
                return call_chains
            
            # For each target node, find paths leading to it
            for target_node in target_nodes:
                # Use NetworkX to find paths
                for source_node in self.dependency_graph.nodes():
                    if source_node != target_node:
                        try:
                            # Find shortest path (there might be multiple)
                            if nx.has_path(self.dependency_graph, source_node, target_node):
                                path = nx.shortest_path(self.dependency_graph, source_node, target_node)
                                if len(path) <= max_depth + 1:  # +1 because path includes both endpoints
                                    call_chains.append(path)
                        except nx.NetworkXNoPath:
                            continue
            
            # Remove duplicates and sort by length
            unique_chains = []
            for chain in call_chains:
                if chain not in unique_chains:
                    unique_chains.append(chain)
            
            unique_chains.sort(key=len)
            return unique_chains[:10]  # Return top 10 chains
            
        except Exception as e:
            logger.error(f"Failed to get call chains: {e}")
            return []
    
    # Helper methods
    
    def _should_use_cached_context(self, source_path: str) -> bool:
        """Check if we should use cached context."""
        if not self.is_context_available():
            return False
        
        metadata = self.get_context_metadata()
        if not metadata:
            return False
        
        # Check if source path matches
        if metadata.get('source_path') != source_path:
            return False
        
        # Check if context is recent enough (basic freshness check)
        # This could be enhanced with file modification time checks
        return True
    
    def _load_cached_context(self) -> CodebaseContext:
        """Load cached context from storage."""
        try:
            metadata_file = self.context_dir / "context.json"
            with open(metadata_file, 'r') as f:
                context_data = json.load(f)
            
            return CodebaseContext.from_dict(context_data)
            
        except Exception as e:
            logger.error(f"Failed to load cached context: {e}")
            raise
    
    def _save_context(self, context: CodebaseContext) -> None:
        """Save context to storage."""
        try:
            # Save main context
            context_file = self.context_dir / "context.json"
            with open(context_file, 'w') as f:
                json.dump(context.to_dict(), f, indent=2, default=str)
            
            # Save metadata for quick access
            metadata = {
                "source_path": context.source_path,
                "created_at": context.created_at.isoformat(),
                "analyzer_type": context.analyzer_type,
                "total_files": context.stats.total_files,
                "total_entities": len(context.entities)
            }
            self._save_context_metadata(metadata)
            
            # Save dependency graph if available
            if self.dependency_graph:
                import pickle
                graph_file = self.context_dir / "dependency_graph.pkl"
                with open(graph_file, 'wb') as f:
                    pickle.dump(self.dependency_graph, f)
            
            logger.debug("Context saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save context: {e}")
            raise
    
    def _collect_file_info(self, source_path: Path) -> List[FileInfo]:
        """Collect information about files in the codebase."""
        files = []
        
        for file_path in source_path.rglob("*"):
            if file_path.is_file() and self._should_include_file(file_path):
                try:
                    stat = file_path.stat()
                    
                    # Basic file info
                    file_info = FileInfo(
                        path=str(file_path.relative_to(source_path)),
                        size=stat.st_size,
                        lines_of_code=self._count_lines_of_code(file_path),
                        language=self._detect_language(file_path),
                        last_modified=datetime.fromtimestamp(stat.st_mtime),
                        test_file=self._is_test_file(file_path)
                    )
                    
                    files.append(file_info)
                    
                except Exception as e:
                    logger.warning(f"Failed to process file {file_path}: {e}")
                    continue
        
        return files
    
    def _extract_entities_from_graph(self) -> List[CodeEntity]:
        """Extract code entities from LocAgent's dependency graph."""
        entities = []
        
        if not self.dependency_graph:
            return entities
        
        for node, data in self.dependency_graph.nodes(data=True):
            node_type = data.get('type', 'unknown')
            
            if node_type in ['function', 'class']:
                # Extract file path and entity name
                if ':' in node:
                    file_path, entity_name = node.split(':', 1)
                else:
                    file_path = node
                    entity_name = node
                
                entity = CodeEntity(
                    id=node,
                    name=entity_name,
                    type=node_type,
                    file_path=file_path,
                    start_line=data.get('start_line'),
                    end_line=data.get('end_line'),
                    content=data.get('code'),
                    metadata=data
                )
                
                entities.append(entity)
        
        return entities
    
    def _build_dependency_mappings(self) -> tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        """Build dependency mappings from the graph."""
        dependencies = {}
        reverse_dependencies = {}
        
        if not self.dependency_graph:
            return dependencies, reverse_dependencies
        
        for source, target, data in self.dependency_graph.edges(data=True):
            edge_type = data.get('type', 'unknown')
            
            if edge_type in ['imports', 'invokes']:
                # Extract file paths
                source_file = source.split(':')[0] if ':' in source else source
                target_file = target.split(':')[0] if ':' in target else target
                
                # Add to dependencies
                if source_file not in dependencies:
                    dependencies[source_file] = []
                if target_file not in dependencies[source_file]:
                    dependencies[source_file].append(target_file)
                
                # Add to reverse dependencies
                if target_file not in reverse_dependencies:
                    reverse_dependencies[target_file] = []
                if source_file not in reverse_dependencies[target_file]:
                    reverse_dependencies[target_file].append(source_file)
        
        return dependencies, reverse_dependencies
    
    def _generate_stats(self, files: List[FileInfo], entities: List[CodeEntity]) -> CodebaseStats:
        """Generate statistics from collected data."""
        
        # Count by language
        languages = {}
        for file in files:
            lang = file.language
            languages[lang] = languages.get(lang, 0) + 1
        
        # Count by entity type
        total_functions = len([e for e in entities if e.type == 'function'])
        total_classes = len([e for e in entities if e.type == 'class'])
        total_variables = len([e for e in entities if e.type == 'variable'])
        
        # Calculate total lines
        total_lines = sum(file.lines_of_code for file in files)
        
        # Get directories
        directories = list(set(Path(file.path).parent.as_posix() for file in files))
        
        # Count test files
        test_files = len([file for file in files if file.test_file])
        
        return CodebaseStats(
            total_files=len(files),
            total_lines=total_lines,
            total_functions=total_functions,
            total_classes=total_classes,
            total_variables=total_variables,
            languages=languages,
            directories=directories,
            test_files=test_files,
            dependency_count=len(self.dependency_graph.edges()) if self.dependency_graph else 0,
            last_analysis=datetime.now()
        )
    
    def _should_include_file(self, file_path: Path) -> bool:
        """Check if file should be included in analysis."""
        # Check extension
        if not any(str(file_path).endswith(ext) for ext in self._analysis_config.get('supported_extensions', ['.py'])):
            return False
        
        # Check exclude patterns
        exclude_patterns = self._analysis_config.get('exclude_patterns', [])
        for pattern in exclude_patterns:
            if file_path.match(pattern):
                return False
        
        # Check size limit
        max_size = self._analysis_config.get('max_file_size', 10 * 1024 * 1024)
        if file_path.stat().st_size > max_size:
            return False
        
        return True
    
    def _count_lines_of_code(self, file_path: Path) -> int:
        """Count lines of code in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return len(f.readlines())
        except Exception:
            return 0
    
    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension."""
        extension_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.h': 'C/C++',
            '.hpp': 'C++',
            '.cs': 'C#',
            '.rb': 'Ruby',
            '.go': 'Go',
            '.rs': 'Rust',
            '.php': 'PHP',
            '.swift': 'Swift',
            '.kt': 'Kotlin'
        }
        return extension_map.get(file_path.suffix.lower(), 'Unknown')
    
    def _is_test_file(self, file_path: Path) -> bool:
        """Check if file is a test file."""
        name = file_path.name.lower()
        return any(pattern in name for pattern in ['test_', '_test', 'test.', '.test', 'spec_', '_spec'])
    
    def _get_locagent_version(self) -> str:
        """Get LocAgent version."""
        try:
            from dependency_graph.build_graph import VERSION
            return VERSION
        except ImportError:
            return "unknown"
    
    # Query implementation methods
    
    def _find_functions(self, query: str, parameters: Dict[str, Any]) -> List[QueryMatch]:
        """Find functions matching the query."""
        matches = []
        
        for node, data in self.dependency_graph.nodes(data=True):
            if data.get('type') == 'function' and query.lower() in node.lower():
                match = self._create_query_match(node, data, query)
                matches.append(match)
        
        return matches
    
    def _find_classes(self, query: str, parameters: Dict[str, Any]) -> List[QueryMatch]:
        """Find classes matching the query."""
        matches = []
        
        for node, data in self.dependency_graph.nodes(data=True):
            if data.get('type') == 'class' and query.lower() in node.lower():
                match = self._create_query_match(node, data, query)
                matches.append(match)
        
        return matches
    
    def _find_files(self, query: str, parameters: Dict[str, Any]) -> List[QueryMatch]:
        """Find files matching the query."""
        matches = []
        
        for node, data in self.dependency_graph.nodes(data=True):
            if data.get('type') == 'file' and query.lower() in node.lower():
                match = self._create_query_match(node, data, query)
                matches.append(match)
        
        return matches
    
    def _get_dependencies(self, query: str, parameters: Dict[str, Any]) -> List[QueryMatch]:
        """Get dependencies for the specified entity."""
        matches = []
        
        # Find the entity
        target_nodes = [node for node in self.dependency_graph.nodes() if query.lower() in node.lower()]
        
        for target_node in target_nodes:
            for successor in self.dependency_graph.successors(target_node):
                data = self.dependency_graph.nodes[successor]
                match = self._create_query_match(successor, data, query)
                match.metadata['dependency_type'] = 'depends_on'
                matches.append(match)
        
        return matches
    
    def _get_call_chains(self, query: str, parameters: Dict[str, Any]) -> List[QueryMatch]:
        """Get call chains for the specified function."""
        # This would use the get_call_chain method
        chains = self.get_call_chain(query, parameters.get('max_depth', 5))
        
        matches = []
        for i, chain in enumerate(chains):
            match = QueryMatch(
                entity_id=f"call_chain_{i}",
                entity_name=f"Call Chain {i+1}",
                entity_type="call_chain",
                file_path="multiple",
                matched_content=" -> ".join(chain),
                metadata={'chain': chain, 'length': len(chain)}
            )
            matches.append(match)
        
        return matches
    
    def _search_code(self, query: str, parameters: Dict[str, Any]) -> List[QueryMatch]:
        """Search for code content matching the query."""
        matches = []
        
        # Search in node code content
        for node, data in self.dependency_graph.nodes(data=True):
            code = data.get('code', '')
            if code and query.lower() in code.lower():
                match = self._create_query_match(node, data, query)
                
                # Find the specific line with the match
                lines = code.split('\n')
                for i, line in enumerate(lines):
                    if query.lower() in line.lower():
                        match.line_number = data.get('start_line', 1) + i
                        match.matched_content = line.strip()
                        break
                
                matches.append(match)
        
        return matches
    
    def _general_search(self, query: str, parameters: Dict[str, Any]) -> List[QueryMatch]:
        """General search across all entities."""
        matches = []
        
        # Search in entity names
        for node, data in self.dependency_graph.nodes(data=True):
            if query.lower() in node.lower():
                match = self._create_query_match(node, data, query)
                matches.append(match)
        
        return matches
    
    def _create_query_match(self, node: str, data: Dict[str, Any], query: str) -> QueryMatch:
        """Create a QueryMatch from graph node data."""
        
        # Extract file path and entity name
        if ':' in node:
            file_path, entity_name = node.split(':', 1)
        else:
            file_path = node
            entity_name = node
        
        # Calculate relevance score based on query match
        relevance = 1.0
        if query.lower() == entity_name.lower():
            relevance = 1.0
        elif entity_name.lower().startswith(query.lower()):
            relevance = 0.9
        elif query.lower() in entity_name.lower():
            relevance = 0.7
        else:
            relevance = 0.5
        
        return QueryMatch(
            entity_id=node,
            entity_name=entity_name,
            entity_type=data.get('type', 'unknown'),
            file_path=file_path,
            line_number=data.get('start_line'),
            matched_content=data.get('code', ''),
            confidence_score=0.8,
            relevance_score=relevance,
            metadata=data
        )
    
    def _handle_natural_language_query(self, request: QueryRequest) -> QueryResponse:
        """Handle natural language queries using AI if available."""
        
        if not self._ai_config.get('enabled', False):
            return QueryResponse(
                request=request,
                success=False,
                error_message="Natural language queries require AI configuration"
            )
        
        # For now, fall back to keyword search
        # TODO: Implement AI-powered natural language understanding
        simplified_query = self._extract_keywords_from_nl(request.query)
        
        request.query_type = QueryType.SEARCH_CODE
        request.query = simplified_query
        
        response = self.query_codebase(request)
        response.natural_language_response = f"Based on your query '{request.query}', here are the relevant code locations:"
        
        return response
    
    def _extract_keywords_from_nl(self, query: str) -> str:
        """Extract keywords from natural language query."""
        # Simple keyword extraction - could be enhanced with NLP
        import re
        
        # Remove common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'what', 'where', 'when', 'who', 'how', 'why'}
        
        words = re.findall(r'\b\w+\b', query.lower())
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        return ' '.join(keywords[:3])  # Use top 3 keywords
    
    # Bug impact analysis helper methods
    
    def _extract_bug_info(self, bug_details: str) -> Dict[str, Any]:
        """Extract relevant information from bug details."""
        info = {
            'file_paths': [],
            'function_names': [],
            'class_names': [],
            'line_numbers': [],
            'error_types': [],
            'keywords': []
        }
        
        # Extract file paths
        file_patterns = [r'([^/\s]*\.py(?::\d+)?)', r'File "([^"]*)"', r'in ([^/\s]*\.py)']
        for pattern in file_patterns:
            matches = re.findall(pattern, bug_details)
            info['file_paths'].extend(matches)
        
        # Extract line numbers
        line_matches = re.findall(r'line (\d+)', bug_details, re.IGNORECASE)
        line_matches.extend(re.findall(r':(\d+)', bug_details))
        info['line_numbers'] = [int(ln) for ln in line_matches]
        
        # Extract function/class names
        function_matches = re.findall(r'in (\w+)\(', bug_details)
        info['function_names'].extend(function_matches)
        
        class_matches = re.findall(r'(\w+)\.(\w+)', bug_details)
        for class_name, method_name in class_matches:
            info['class_names'].append(class_name)
            info['function_names'].append(method_name)
        
        # Extract error types
        error_types = re.findall(r'(\w*Error|\w*Exception)', bug_details)
        info['error_types'] = error_types
        
        return info
    
    def _find_primary_impact_locations(self, extracted_info: Dict[str, Any], context_lines: int) -> List[ImpactedCode]:
        """Find primary locations affected by the bug."""
        locations = []
        
        # Search for mentioned files and functions
        for file_path in extracted_info['file_paths']:
            clean_path = file_path.split(':')[0]  # Remove line numbers
            
            # Find matching nodes in graph
            for node, data in self.dependency_graph.nodes(data=True):
                if clean_path in node:
                    location = ImpactedCode(
                        entity_id=node,
                        entity_name=node.split(':')[-1] if ':' in node else node,
                        entity_type=data.get('type', 'unknown'),
                        file_path=clean_path,
                        line_number=data.get('start_line'),
                        impact_type='direct',
                        impact_reason='Mentioned in bug report',
                        impact_level='high',
                        code_snippet=data.get('code'),
                        risk_score=0.9
                    )
                    locations.append(location)
        
        # Search for mentioned functions
        for func_name in extracted_info['function_names']:
            for node, data in self.dependency_graph.nodes(data=True):
                if data.get('type') == 'function' and func_name in node:
                    location = ImpactedCode(
                        entity_id=node,
                        entity_name=func_name,
                        entity_type='function',
                        file_path=node.split(':')[0] if ':' in node else 'unknown',
                        line_number=data.get('start_line'),
                        impact_type='direct',
                        impact_reason='Function mentioned in bug report',
                        impact_level='high',
                        code_snippet=data.get('code'),
                        risk_score=0.8
                    )
                    locations.append(location)
        
        return locations
    
    def _find_secondary_impacts(self, primary_locations: List[ImpactedCode], max_depth: int) -> List[ImpactedCode]:
        """Find secondary impacts through dependency analysis."""
        secondary_impacts = []
        
        for location in primary_locations:
            if not location.entity_id:
                continue
            
            # Find dependencies (what this code calls)
            for successor in self.dependency_graph.successors(location.entity_id):
                data = self.dependency_graph.nodes[successor]
                
                impact = ImpactedCode(
                    entity_id=successor,
                    entity_name=successor.split(':')[-1] if ':' in successor else successor,
                    entity_type=data.get('type', 'unknown'),
                    file_path=successor.split(':')[0] if ':' in successor else 'unknown',
                    line_number=data.get('start_line'),
                    impact_type='indirect',
                    impact_reason=f'Called by {location.entity_name}',
                    impact_level='medium',
                    risk_score=0.6
                )
                secondary_impacts.append(impact)
            
            # Find dependents (what calls this code)
            for predecessor in self.dependency_graph.predecessors(location.entity_id):
                data = self.dependency_graph.nodes[predecessor]
                
                impact = ImpactedCode(
                    entity_id=predecessor,
                    entity_name=predecessor.split(':')[-1] if ':' in predecessor else predecessor,
                    entity_type=data.get('type', 'unknown'),
                    file_path=predecessor.split(':')[0] if ':' in predecessor else 'unknown',
                    line_number=data.get('start_line'),
                    impact_type='indirect',
                    impact_reason=f'Calls {location.entity_name}',
                    impact_level='medium',
                    risk_score=0.5
                )
                secondary_impacts.append(impact)
        
        return secondary_impacts[:20]  # Limit to 20 secondary impacts
    
    def _find_affected_call_chains(self, primary_locations: List[ImpactedCode]) -> List[List[str]]:
        """Find call chains that might be affected."""
        all_chains = []
        
        for location in primary_locations:
            if location.entity_id and location.entity_type == 'function':
                chains = self.get_call_chain(location.entity_name, max_depth=3)
                all_chains.extend(chains)
        
        return all_chains[:10]  # Limit to 10 chains
    
    def _generate_fix_suggestions(self, bug_details: str, locations: List[ImpactedCode]) -> List[str]:
        """Generate suggestions for fixing the bug."""
        suggestions = []
        
        # Basic suggestions based on error types
        if 'AttributeError' in bug_details:
            suggestions.append("Check if the object has the expected attribute/method")
            suggestions.append("Verify object initialization and type")
        
        if 'TypeError' in bug_details:
            suggestions.append("Check parameter types and function signatures")
            suggestions.append("Verify data type conversions")
        
        if 'NameError' in bug_details:
            suggestions.append("Check variable names and import statements")
            suggestions.append("Verify scope and variable definitions")
        
        # Generic suggestions
        suggestions.extend([
            "Add error handling and input validation",
            "Review recent changes to affected code",
            "Add logging to trace execution flow"
        ])
        
        return suggestions
    
    def _generate_testing_recommendations(self, primary: List[ImpactedCode], secondary: List[ImpactedCode]) -> List[str]:
        """Generate testing recommendations."""
        recommendations = []
        
        # Test primary locations
        if primary:
            recommendations.append("Create unit tests for directly affected functions")
            recommendations.append("Test edge cases and error conditions")
        
        # Test integration
        if secondary:
            recommendations.append("Run integration tests for dependent components")
            recommendations.append("Test end-to-end workflows involving affected code")
        
        # General recommendations
        recommendations.extend([
            "Verify fix with original bug reproduction steps",
            "Test similar code patterns for related issues",
            "Run full regression test suite"
        ])
        
        return recommendations
    
    def _calculate_impact_confidence(self, locations: List[ImpactedCode]) -> float:
        """Calculate confidence score for impact analysis."""
        if not locations:
            return 0.0
        
        # Base confidence on number of direct matches and specificity
        direct_matches = len([loc for loc in locations if loc.impact_type == 'direct'])
        
        if direct_matches >= 3:
            return 0.9
        elif direct_matches >= 1:
            return 0.7
        else:
            return 0.4
    
    def _assess_risk_level(self, primary: List[ImpactedCode], secondary: List[ImpactedCode]) -> str:
        """Assess overall risk level of the bug."""
        total_impacts = len(primary) + len(secondary)
        high_risk_count = len([loc for loc in primary + secondary if loc.risk_score >= 0.7])
        
        if high_risk_count >= 5 or total_impacts >= 20:
            return "critical"
        elif high_risk_count >= 3 or total_impacts >= 10:
            return "high"
        elif high_risk_count >= 1 or total_impacts >= 5:
            return "medium"
        else:
            return "low"