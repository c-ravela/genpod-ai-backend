"""
Storage interface abstractions for different storage backends.

Provides pluggable storage for vectors, graphs, text indexes, and metadata.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from pathlib import Path


class VectorStorageInterface(ABC):
    """Abstract interface for vector storage operations."""
    
    @abstractmethod
    def persist(self, path: str) -> None:
        """Persist vector store to disk."""
        pass
    
    @abstractmethod
    def load(self, path: str) -> None:
        """Load vector store from disk."""
        pass
    
    @abstractmethod
    def add_embeddings(self, 
                      embeddings: List[List[float]], 
                      metadata: List[Dict[str, Any]],
                      ids: Optional[List[str]] = None) -> None:
        """Add embeddings with metadata to the store."""
        pass
    
    @abstractmethod
    def search(self, 
              query_embedding: List[float], 
              top_k: int = 10,
              filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for similar embeddings."""
        pass
    
    @abstractmethod
    def delete(self, ids: List[str]) -> None:
        """Delete embeddings by IDs."""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        pass


class GraphStorageInterface(ABC):
    """Abstract interface for graph storage operations."""
    
    @abstractmethod
    def save_graph(self, graph: Any, path: str) -> None:
        """Save graph to storage."""
        pass
    
    @abstractmethod
    def load_graph(self, path: str) -> Any:
        """Load graph from storage."""
        pass
    
    @abstractmethod
    def add_nodes(self, nodes: List[Dict[str, Any]]) -> None:
        """Add nodes to the graph."""
        pass
    
    @abstractmethod
    def add_edges(self, edges: List[Dict[str, Any]]) -> None:
        """Add edges to the graph."""
        pass
    
    @abstractmethod
    def query_nodes(self, 
                   node_type: Optional[str] = None,
                   filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Query nodes with optional filters."""
        pass
    
    @abstractmethod
    def query_edges(self, 
                   edge_type: Optional[str] = None,
                   source_node: Optional[str] = None,
                   target_node: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query edges with optional filters."""
        pass
    
    @abstractmethod
    def get_neighbors(self, 
                     node_id: str, 
                     direction: str = "both",
                     edge_type: Optional[str] = None) -> List[str]:
        """Get neighbors of a node."""
        pass


class TextIndexInterface(ABC):
    """Abstract interface for text indexing and search."""
    
    @abstractmethod
    def build_index(self, documents: List[Dict[str, Any]]) -> None:
        """Build text index from documents."""
        pass
    
    @abstractmethod
    def search(self, 
              query: str, 
              top_k: int = 10,
              filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search the text index."""
        pass
    
    @abstractmethod
    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Add documents to the index."""
        pass
    
    @abstractmethod
    def remove_documents(self, doc_ids: List[str]) -> None:
        """Remove documents from the index."""
        pass
    
    @abstractmethod
    def persist(self, path: str) -> None:
        """Persist index to disk."""
        pass
    
    @abstractmethod
    def load(self, path: str) -> None:
        """Load index from disk."""
        pass


class MetadataStorageInterface(ABC):
    """Abstract interface for metadata storage."""
    
    @abstractmethod
    def save_metadata(self, data: Dict[str, Any], key: str) -> None:
        """Save metadata with a key."""
        pass
    
    @abstractmethod
    def load_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """Load metadata by key."""
        pass
    
    @abstractmethod
    def update_metadata(self, key: str, updates: Dict[str, Any]) -> None:
        """Update existing metadata."""
        pass
    
    @abstractmethod
    def delete_metadata(self, key: str) -> None:
        """Delete metadata by key."""
        pass
    
    @abstractmethod
    def list_keys(self) -> List[str]:
        """List all metadata keys."""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if metadata exists for key."""
        pass


class StorageInterface(ABC):
    """
    Unified storage interface that coordinates all storage types.
    
    This is the main interface that analyzer implementations use.
    """
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
    
    @abstractmethod
    def get_vector_store(self) -> VectorStorageInterface:
        """Get vector storage instance."""
        pass
    
    @abstractmethod
    def get_graph_store(self) -> GraphStorageInterface:
        """Get graph storage instance."""
        pass
    
    @abstractmethod
    def get_text_index(self) -> TextIndexInterface:
        """Get text index instance."""
        pass
    
    @abstractmethod
    def get_metadata_store(self) -> MetadataStorageInterface:
        """Get metadata storage instance."""
        pass
    
    @abstractmethod
    def initialize_storage(self) -> None:
        """Initialize all storage components."""
        pass
    
    @abstractmethod
    def cleanup_storage(self) -> None:
        """Cleanup all storage components."""
        pass
    
    @abstractmethod
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get comprehensive storage statistics."""
        pass
    
    def get_storage_paths(self) -> Dict[str, str]:
        """Get all storage paths."""
        return {
            "base_path": str(self.base_path),
            "vectors_path": str(self.base_path / "vectors"),
            "graphs_path": str(self.base_path / "context"),
            "indexes_path": str(self.base_path / "indexes"),
            "metadata_path": str(self.base_path / "cache")
        }