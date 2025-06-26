"""
Data models for codebase context and metadata.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path


@dataclass
class CodeEntity:
    """Represents a code entity (function, class, variable, etc.)."""
    
    id: str
    name: str
    type: str  # function, class, variable, module, etc.
    file_path: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    content: Optional[str] = None
    docstring: Optional[str] = None
    parameters: Optional[List[str]] = None
    return_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass  
class FileInfo:
    """Information about a file in the codebase."""
    
    path: str
    size: int
    lines_of_code: int
    language: str
    last_modified: datetime
    entities: List[CodeEntity] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    complexity_score: Optional[float] = None
    test_file: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodebaseStats:
    """Statistics about the analyzed codebase."""
    
    total_files: int
    total_lines: int
    total_functions: int
    total_classes: int
    total_variables: int
    languages: Dict[str, int]  # language -> file count
    directories: List[str]
    test_files: int
    complexity_metrics: Dict[str, float] = field(default_factory=dict)
    dependency_count: int = 0
    last_analysis: Optional[datetime] = None
    analysis_duration: Optional[float] = None  # seconds


@dataclass
class CodebaseContext:
    """
    Complete context information about a codebase.
    
    This is the main data structure returned by context building operations.
    """
    
    source_path: str
    storage_path: str
    stats: CodebaseStats
    files: List[FileInfo] = field(default_factory=list)
    entities: List[CodeEntity] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)  # file -> dependencies
    reverse_dependencies: Dict[str, List[str]] = field(default_factory=dict)  # file -> dependents
    
    # Analysis metadata
    analyzer_type: str = "unknown"
    analyzer_version: str = "unknown"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    # Configuration used for analysis
    analysis_config: Dict[str, Any] = field(default_factory=dict)
    
    # Additional storage references
    vector_store_path: Optional[str] = None
    graph_store_path: Optional[str] = None
    text_index_path: Optional[str] = None
    
    def get_file(self, file_path: str) -> Optional[FileInfo]:
        """Get file information by path."""
        for file_info in self.files:
            if file_info.path == file_path:
                return file_info
        return None
    
    def get_entity(self, entity_id: str) -> Optional[CodeEntity]:
        """Get entity by ID."""
        for entity in self.entities:
            if entity.id == entity_id:
                return entity
        return None
    
    def get_entities_by_type(self, entity_type: str) -> List[CodeEntity]:
        """Get all entities of a specific type."""
        return [entity for entity in self.entities if entity.type == entity_type]
    
    def get_entities_in_file(self, file_path: str) -> List[CodeEntity]:
        """Get all entities in a specific file."""
        return [entity for entity in self.entities if entity.file_path == file_path]
    
    def find_entities(self, name_pattern: str, entity_type: Optional[str] = None) -> List[CodeEntity]:
        """Find entities matching a name pattern."""
        import re
        
        pattern = re.compile(name_pattern, re.IGNORECASE)
        results = []
        
        for entity in self.entities:
            if pattern.search(entity.name):
                if entity_type is None or entity.type == entity_type:
                    results.append(entity)
        
        return results
    
    def get_file_dependencies(self, file_path: str, include_reverse: bool = False) -> Dict[str, List[str]]:
        """Get dependencies for a specific file."""
        result = {
            "dependencies": self.dependencies.get(file_path, []),
        }
        
        if include_reverse:
            result["dependents"] = self.reverse_dependencies.get(file_path, [])
        
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for serialization."""
        from dataclasses import asdict
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodebaseContext':
        """Create context from dictionary."""
        # Handle datetime fields
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        # Handle nested objects
        if 'stats' in data and isinstance(data['stats'], dict):
            if 'last_analysis' in data['stats'] and isinstance(data['stats']['last_analysis'], str):
                data['stats']['last_analysis'] = datetime.fromisoformat(data['stats']['last_analysis'])
            data['stats'] = CodebaseStats(**data['stats'])
        
        if 'files' in data:
            files = []
            for file_data in data['files']:
                if isinstance(file_data, dict):
                    # Handle datetime
                    if 'last_modified' in file_data and isinstance(file_data['last_modified'], str):
                        file_data['last_modified'] = datetime.fromisoformat(file_data['last_modified'])
                    
                    # Handle entities
                    if 'entities' in file_data:
                        entities = []
                        for entity_data in file_data['entities']:
                            if isinstance(entity_data, dict):
                                entities.append(CodeEntity(**entity_data))
                            else:
                                entities.append(entity_data)
                        file_data['entities'] = entities
                    
                    files.append(FileInfo(**file_data))
                else:
                    files.append(file_data)
            data['files'] = files
        
        if 'entities' in data:
            entities = []
            for entity_data in data['entities']:
                if isinstance(entity_data, dict):
                    entities.append(CodeEntity(**entity_data))
                else:
                    entities.append(entity_data)
            data['entities'] = entities
        
        return cls(**data)
