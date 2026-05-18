import numpy as np
from typing import Optional, Dict, Any, List, Callable
import hashlib
import json
from collections import defaultdict


class TopologyNode:
    def __init__(self, node_id: str, data: Any, 
                 dimensions: Optional[List[float]] = None):
        self.node_id = node_id
        self.data = data
        self.dimensions = dimensions or []
        self.connections = {}
        self.metadata = {}

    def add_connection(self, target_id: str, weight: float = 1.0):
        self.connections[target_id] = weight

    def get_vector(self) -> np.ndarray:
        return np.array(self.dimensions)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'node_id': self.node_id,
            'data': self.data,
            'dimensions': self.dimensions,
            'connections': self.connections,
            'metadata': self.metadata
        }


class TopologySearchEngine:
    def __init__(self, dimensions: int = 11):
        self.dimensions = dimensions
        self.nodes = {}
        self.index = defaultdict(list)
        self.node_vectors = {}

    def _hash_key(self, key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def add_node(self, node_id: str, data: Any, 
                dimensions: Optional[List[float]] = None) -> TopologyNode:
        if dimensions is None:
            dimensions = np.random.randn(self.dimensions).tolist()
        
        node = TopologyNode(node_id, data, dimensions)
        self.nodes[node_id] = node
        self.node_vectors[node_id] = np.array(dimensions)
        
        for i, dim_val in enumerate(dimensions):
            bucket = int(dim_val * 10)
            self.index[f'dim_{i}_{bucket}'].append(node_id)
        
        return node

    def connect_nodes(self, source_id: str, target_id: str, 
                     weight: float = 1.0):
        if source_id in self.nodes and target_id in self.nodes:
            self.nodes[source_id].add_connection(target_id, weight)
            self.nodes[target_id].add_connection(source_id, weight)

    def cosine_similarity(self, vec1: np.ndarray, 
                         vec2: np.ndarray) -> float:
        dot = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        return dot / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0

    def euclidean_distance(self, vec1: np.ndarray, 
                          vec2: np.ndarray) -> float:
        return np.linalg.norm(vec1 - vec2)

    def search_by_vector(self, query_vector: List[float], 
                        top_k: int = 10,
                        metric: str = 'cosine') -> List[Dict[str, Any]]:
        query_vec = np.array(query_vector)
        scores = []
        
        for node_id, node_vec in self.node_vectors.items():
            if metric == 'cosine':
                score = self.cosine_similarity(query_vec, node_vec)
            else:
                score = -self.euclidean_distance(query_vec, node_vec)
            
            scores.append({
                'node_id': node_id,
                'node': self.nodes[node_id],
                'score': score
            })
        
        scores.sort(key=lambda x: x['score'], reverse=True)
        return scores[:top_k]

    def search_by_id(self, node_id: str, 
                    max_depth: int = 2) -> Dict[str, Any]:
        if node_id not in self.nodes:
            return {}
        
        visited = set()
        results = {
            'center': self.nodes[node_id].to_dict(),
            'connections': {}
        }
        
        queue = [(node_id, 0)]
        visited.add(node_id)
        
        while queue:
            current_id, depth = queue.pop(0)
            
            if depth >= max_depth:
                continue
            
            current_node = self.nodes[current_id]
            for neighbor_id, weight in current_node.connections.items():
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    results['connections'][neighbor_id] = {
                        'node': self.nodes[neighbor_id].to_dict(),
                        'depth': depth + 1,
                        'weight': weight
                    }
                    queue.append((neighbor_id, depth + 1))
        
        return results

    def search_by_metadata(self, key: str, value: Any) -> List[TopologyNode]:
        results = []
        for node in self.nodes.values():
            if key in node.metadata and node.metadata[key] == value:
                results.append(node)
        return results

    def add_metadata(self, node_id: str, key: str, value: Any):
        if node_id in self.nodes:
            self.nodes[node_id].metadata[key] = value

    def get_subgraph(self, node_ids: List[str]) -> Dict[str, Any]:
        subgraph = {
            'nodes': [],
            'edges': []
        }
        
        node_set = set(node_ids)
        
        for node_id in node_ids:
            if node_id in self.nodes:
                subgraph['nodes'].append(self.nodes[node_id].to_dict())
                for neighbor_id, weight in self.nodes[node_id].connections.items():
                    if neighbor_id in node_set:
                        subgraph['edges'].append({
                            'source': node_id,
                            'target': neighbor_id,
                            'weight': weight
                        })
        
        return subgraph

    def export_graph(self) -> Dict[str, Any]:
        return {
            'dimensions': self.dimensions,
            'nodes': [node.to_dict() for node in self.nodes.values()],
            'edges': [
                {
                    'source': source_id,
                    'target': target_id,
                    'weight': weight
                }
                for source_id, node in self.nodes.items()
                for target_id, weight in node.connections.items()
                if source_id < target_id
            ]
        }

    def import_graph(self, graph_data: Dict[str, Any]):
        self.dimensions = graph_data.get('dimensions', self.dimensions)
        self.nodes = {}
        self.node_vectors = {}
        self.index = defaultdict(list)
        
        for node_data in graph_data.get('nodes', []):
            node = TopologyNode(
                node_data['node_id'],
                node_data['data'],
                node_data['dimensions']
            )
            node.connections = node_data.get('connections', {})
            node.metadata = node_data.get('metadata', {})
            self.nodes[node.node_id] = node
            self.node_vectors[node.node_id] = np.array(node.dimensions)
        
        for node_data in graph_data.get('nodes', []):
            for i, dim_val in enumerate(node_data['dimensions']):
                bucket = int(dim_val * 10)
                self.index[f'dim_{i}_{bucket}'].append(node_data['node_id'])
