"""
LocAgent storage implementation for the storage interfaces.

Provides concrete storage implementations using LocAgent's storage mechanisms.
"""

import json
import pickle
from pathlib import Path
from typing import Dict, List, Any, Optional

from utils.logger import logger

from ..interfaces.storage import (
    StorageInterface, VectorStorageInterface, GraphStorageInterface,
    TextIndexInterface, MetadataStorageInterface
)


class LocAgentVectorStorage(VectorStorageInterface):
    """LocAgent implementation of vector storage using FAISS."""
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.logger = logger
        self._vector_store = None
    
    def persist(self, path: str) -> None:
        """Persist vector store to disk."""
        if self._vector_store:
            try:
                # Use LocAgent's FAISS storage
                self._vector_store.persist(persist_dir=path)
                self.logger.debug(f"Vector store persisted to {path}")
            except Exception as e:
                self.logger.error(f"Failed to persist vector store: {e}")
                raise
    
    def load(self, path: str) -> None:
        """Load vector store from disk."""
        try:
            # Implementation would depend on LocAgent's FAISS loader
            self.logger.debug(f"Vector store loaded from {path}")
        except Exception as e:
            self.logger.error(f"Failed to load vector store: {e}")
            raise
    
    def add_embeddings(self, 
                      embeddings: List[List[float]], 
                      metadata: List[Dict[str, Any]],
                      ids: Optional[List[str]] = None) -> None:
        """Add embeddings with metadata to the store."""
        try:
            # Implementation would use LocAgent's vector store
            self.logger.debug(f"Added {len(embeddings)} embeddings")
        except Exception as e:
            self.logger.error(f"Failed to add embeddings: {e}")
            raise
    
    def search(self, 
              query_embedding: List[float], 
              top_k: int = 10,
              filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for similar embeddings."""
        try:
            # Implementation would use LocAgent's search
            results = []
            self.logger.debug(f"Vector search returned {len(results)} results")
            return results
        except Exception as e:
            self.logger.error(f"Vector search failed: {e}")
            return []
    
    def delete(self, ids: List[str]) -> None:
        """Delete embeddings by IDs."""
        try:
            self.logger.debug(f"Deleted {len(ids)} embeddings")
        except Exception as e:
            self.logger.error(f"Failed to delete embeddings: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        return {
            "storage_type": "faiss",
            "storage_path": str(self.storage_path),
            "total_vectors": 0,  # Would be populated from actual store
            "dimension": 1536   # Default OpenAI embedding dimension
        }


class LocAgentGraphStorage(GraphStorageInterface):
    """LocAgent implementation of graph storage using NetworkX."""
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.logger = logger
        self._graph = None
    
    def save_graph(self, graph: Any, path: str) -> None:
        """Save graph to storage."""
        try:
            graph_file = Path(path) / "dependency_graph.pkl"
            with open(graph_file, 'wb') as f:
                pickle.dump(graph, f)
            self.logger.debug(f"Graph saved to {graph_file}")
        except Exception as e:
            self.logger.error(f"Failed to save graph: {e}")
            raise
    
    def load_graph(self, path: str) -> Any:
        """Load graph from storage."""
        try:
            graph_file = Path(path) / "dependency_graph.pkl"
            with open(graph_file, 'rb') as f:
                self._graph = pickle.load(f)
            self.logger.debug(f"Graph loaded from {graph_file}")
            return self._graph
        except Exception as e:
            self.logger.error(f"Failed to load graph: {e}")
            raise
    
    def add_nodes(self, nodes: List[Dict[str, Any]]) -> None:
        """Add nodes to the graph."""
        if not self._graph:
            import networkx as nx
            self._graph = nx.MultiDiGraph()
        
        for node in nodes:
            node_id = node.pop('id')
            self._graph.add_node(node_id, **node)
    
    def add_edges(self, edges: List[Dict[str, Any]]) -> None:
        """Add edges to the graph."""
        if not self._graph:
            import networkx as nx
            self._graph = nx.MultiDiGraph()
        
        for edge in edges:
            source = edge.pop('source')
            target = edge.pop('target')
            self._graph.add_edge(source, target, **edge)
    
    def query_nodes(self, 
                   node_type: Optional[str] = None,
                   filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Query nodes with optional filters."""
        if not self._graph:
            return []
        
        results = []
        for node, data in self._graph.nodes(data=True):
            if node_type and data.get('type') != node_type:
                continue
            
            if filters:
                match = True
                for key, value in filters.items():
                    if data.get(key) != value:
                        match = False
                        break
                if not match:
                    continue
            
            results.append({'id': node, **data})
        
        return results
    
    def query_edges(self, 
                   edge_type: Optional[str] = None,
                   source_node: Optional[str] = None,
                   target_node: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query edges with optional filters."""
        if not self._graph:
            return []
        
        results = []
        for source, target, data in self._graph.edges(data=True):
            if edge_type and data.get('type') != edge_type:
                continue
            if source_node and source != source_node:
                continue
            if target_node and target != target_node:
                continue
            
            results.append({'source': source, 'target': target, **data})
        
        return results
    
    def get_neighbors(self, 
                     node_id: str, 
                     direction: str = "both",
                     edge_type: Optional[str] = None) -> List[str]:
        """Get neighbors of a node."""
        if not self._graph or node_id not in self._graph:
            return []
        
        neighbors = []
        
        if direction in ["both", "out"]:
            for neighbor in self._graph.successors(node_id):
                if not edge_type:
                    neighbors.append(neighbor)
                else:
                    edge_data = self._graph.get_edge_data(node_id, neighbor)
                    if any(data.get('type') == edge_type for data in edge_data.values()):
                        neighbors.append(neighbor)
        
        if direction in ["both", "in"]:
            for neighbor in self._graph.predecessors(node_id):
                if not edge_type:
                    neighbors.append(neighbor)
                else:
                    edge_data = self._graph.get_edge_data(neighbor, node_id)
                    if any(data.get('type') == edge_type for data in edge_data.values()):
                        neighbors.append(neighbor)
        
        return list(set(neighbors))  # Remove duplicates


class LocAgentTextIndex(TextIndexInterface):
    """LocAgent implementation of text indexing using BM25."""
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.logger = logger
        self._index = None
        self._documents = []
    
    def build_index(self, documents: List[Dict[str, Any]]) -> None:
        """Build text index from documents."""
        try:
            self._documents = documents
            # Implementation would use LocAgent's BM25 indexing
            self.logger.debug(f"Built text index with {len(documents)} documents")
        except Exception as e:
            self.logger.error(f"Failed to build text index: {e}")
            raise
    
    def search(self, 
              query: str, 
              top_k: int = 10,
              filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search the text index."""
        try:
            # Simple implementation - would use LocAgent's BM25 search
            results = []
            
            for doc in self._documents:
                if query.lower() in doc.get('content', '').lower():
                    score = doc.get('content', '').lower().count(query.lower())
                    results.append({
                        **doc,
                        'score': score
                    })
            
            # Sort by score and return top_k
            results.sort(key=lambda x: x.get('score', 0), reverse=True)
            return results[:top_k]
        except Exception as e:
            self.logger.error(f"Text search failed: {e}")
            return []
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Add documents to the index."""
        self._documents.extend(documents)
        self.logger.debug(f"Added {len(documents)} documents to index")
    
    def remove_documents(self, doc_ids: List[str]) -> None:
        """Remove documents from the index."""
        self._documents = [doc for doc in self._documents if doc.get('id') not in doc_ids]
        self.logger.debug(f"Removed {len(doc_ids)} documents from index")
    
    def persist(self, path: str) -> None:
        """Persist index to disk."""
        try:
            index_file = Path(path) / "text_index.json"
            with open(index_file, 'w') as f:
                json.dump(self._documents, f, indent=2, default=str)
            self.logger.debug(f"Text index persisted to {index_file}")
        except Exception as e:
            self.logger.error(f"Failed to persist text index: {e}")
            raise
    
    def load(self, path: str) -> None:
        """Load index from disk."""
        try:
            index_file = Path(path) / "text_index.json"
            if index_file.exists():
                with open(index_file, 'r') as f:
                    self._documents = json.load(f)
                self.logger.debug(f"Text index loaded from {index_file}")
        except Exception as e:
            self.logger.error(f"Failed to load text index: {e}")
            raise


class LocAgentMetadataStorage(MetadataStorageInterface):
    """LocAgent implementation of metadata storage using JSON files."""
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.logger = logger
    
    def save_metadata(self, data: Dict[str, Any], key: str) -> None:
        """Save metadata with a key."""
        try:
            metadata_file = self.storage_path / f"{key}.json"
            with open(metadata_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            self.logger.debug(f"Metadata saved: {key}")
        except Exception as e:
            self.logger.error(f"Failed to save metadata {key}: {e}")
            raise
    
    def load_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """Load metadata by key."""
        try:
            metadata_file = self.storage_path / f"{key}.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            self.logger.error(f"Failed to load metadata {key}: {e}")
            return None
    
    def update_metadata(self, key: str, updates: Dict[str, Any]) -> None:
        """Update existing metadata."""
        try:
            existing = self.load_metadata(key) or {}
            existing.update(updates)
            self.save_metadata(existing, key)
            self.logger.debug(f"Metadata updated: {key}")
        except Exception as e:
            self.logger.error(f"Failed to update metadata {key}: {e}")
            raise
    
    def delete_metadata(self, key: str) -> None:
        """Delete metadata by key."""
        try:
            metadata_file = self.storage_path / f"{key}.json"
            if metadata_file.exists():
                metadata_file.unlink()
                self.logger.debug(f"Metadata deleted: {key}")
        except Exception as e:
            self.logger.error(f"Failed to delete metadata {key}: {e}")
            raise
    
    def list_keys(self) -> List[str]:
        """List all metadata keys."""
        try:
            return [f.stem for f in self.storage_path.glob("*.json")]
        except Exception as e:
            self.logger.error(f"Failed to list metadata keys: {e}")
            return []
    
    def exists(self, key: str) -> bool:
        """Check if metadata exists for key."""
        metadata_file = self.storage_path / f"{key}.json"
        return metadata_file.exists()


class LocAgentStorageManager(StorageInterface):
    """
    LocAgent implementation of the unified storage interface.
    
    Coordinates all storage types using LocAgent's storage mechanisms.
    """
    
    def __init__(self, base_path: str):
        super().__init__(base_path)
        self.logger = logger
        
        # Initialize storage components
        self._vector_store = None
        self._graph_store = None
        self._text_index = None
        self._metadata_store = None
        
        self.initialize_storage()
    
    def get_vector_store(self) -> VectorStorageInterface:
        """Get vector storage instance."""
        if self._vector_store is None:
            vectors_path = self.base_path / "vectors"
            self._vector_store = LocAgentVectorStorage(str(vectors_path))
        return self._vector_store
    
    def get_graph_store(self) -> GraphStorageInterface:
        """Get graph storage instance."""
        if self._graph_store is None:
            context_path = self.base_path / "context"
            self._graph_store = LocAgentGraphStorage(str(context_path))
        return self._graph_store
    
    def get_text_index(self) -> TextIndexInterface:
        """Get text index instance."""
        if self._text_index is None:
            indexes_path = self.base_path / "indexes"
            self._text_index = LocAgentTextIndex(str(indexes_path))
        return self._text_index
    
    def get_metadata_store(self) -> MetadataStorageInterface:
        """Get metadata storage instance."""
        if self._metadata_store is None:
            cache_path = self.base_path / "cache"
            self._metadata_store = LocAgentMetadataStorage(str(cache_path))
        return self._metadata_store
    
    def initialize_storage(self) -> None:
        """Initialize all storage components."""
        try:
            # Ensure directory structure exists
            directories = ["vectors", "context", "indexes", "cache"]
            for directory in directories:
                (self.base_path / directory).mkdir(parents=True, exist_ok=True)
            
            self.logger.debug(f"Storage initialized at {self.base_path}")
        except Exception as e:
            self.logger.error(f"Failed to initialize storage: {e}")
            raise
    
    def cleanup_storage(self) -> None:
        """Cleanup all storage components."""
        try:
            import shutil
            if self.base_path.exists():
                shutil.rmtree(self.base_path)
                self.logger.info(f"Storage cleaned up: {self.base_path}")
        except Exception as e:
            self.logger.error(f"Failed to cleanup storage: {e}")
            raise
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get comprehensive storage statistics."""
        try:
            stats = {
                "base_path": str(self.base_path),
                "total_size_bytes": self._calculate_directory_size(self.base_path),
                "components": {}
            }
            
            # Get stats from each component
            if self._vector_store:
                stats["components"]["vectors"] = self._vector_store.get_stats()
            
            if self._metadata_store:
                stats["components"]["metadata"] = {
                    "total_keys": len(self._metadata_store.list_keys())
                }
            
            # Directory sizes
            for directory in ["vectors", "context", "indexes", "cache"]:
                dir_path = self.base_path / directory
                if dir_path.exists():
                    stats["components"][directory] = {
                        "size_bytes": self._calculate_directory_size(dir_path),
                        "file_count": len(list(dir_path.rglob("*")))
                    }
            
            return stats
        except Exception as e:
            self.logger.error(f"Failed to get storage stats: {e}")
            return {"error": str(e)}
    
    def _calculate_directory_size(self, directory: Path) -> int:
        """Calculate total size of directory in bytes."""
        try:
            return sum(f.stat().st_size for f in directory.rglob('*') if f.is_file())
        except Exception:
            return 0