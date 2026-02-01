"""
Dependency Graph - Build and analyze include relationships
"""
import networkx as nx
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from .parser import FileAnalysis, Include

class DependencyGraph:
    """
    Build and analyze include dependency graph using NetworkX.
    """
    
    def __init__(self):
        """Initialize empty dependency graph"""
        self.graph = nx.DiGraph()
        self.file_to_includes: Dict[str, List[str]] = {}
        self.header_to_files: Dict[str, Set[str]] = {}
        
    def build(self, analyses: List[FileAnalysis]) -> None:
        """
        Build dependency graph from parsed files.
        
        Args:
            analyses: List of FileAnalysis objects
        """
        print(f"Building dependency graph from {len(analyses)} files...")
        
        # First pass: Add all files as nodes with attributes
        for analysis in analyses:
            self.graph.add_node(
                analysis.filepath,
                lines=analysis.total_lines,
                code_lines=analysis.code_lines,
                has_templates=analysis.has_templates,
                has_macros=analysis.has_macros,
                namespace_count=analysis.namespace_count,
                class_count=analysis.class_count,
                is_external=False,
                is_header=self._is_header_file(analysis.filepath)
            )
            
            self.file_to_includes[analysis.filepath] = []
            
            # Build reverse index
            for inc in analysis.includes:
                header_id = inc.full_path if inc.full_path else inc.header
                if header_id not in self.header_to_files:
                    self.header_to_files[header_id] = set()
                self.header_to_files[header_id].add(analysis.filepath)
        
        # Second pass: Add edges for includes
        for analysis in analyses:
            for inc in analysis.includes:
                # Determine target node ID
                if inc.full_path and inc.full_path != inc.header:
                    # We resolved the header to an actual file
                    target = inc.full_path
                else:
                    # Use header name (likely external/system)
                    target = f"<{inc.header}>" if inc.is_system else inc.header
                
                # Add target node if not exists (external headers)
                if target not in self.graph:
                    self.graph.add_node(
                        target,
                        is_external=True,
                        is_system=inc.is_system
                    )
                
                # Add edge
                self.graph.add_edge(analysis.filepath, target)
                self.file_to_includes[analysis.filepath].append(target)
        
        print(f"Graph built: {self.graph.number_of_nodes()} nodes, "
              f"{self.graph.number_of_edges()} edges")
    
    def _is_header_file(self, filepath: str) -> bool:
        """Check if file is a header file"""
        ext = Path(filepath).suffix.lower()
        return ext in ['.h', '.hpp', '.hxx', '.hh']
    
    def get_direct_dependencies(self, filepath: str) -> List[str]:
        """
        Get direct dependencies (includes) of a file.
        
        Args:
            filepath: Path to the file
            
        Returns:
            List of direct dependencies
        """
        if filepath not in self.graph:
            return []
        return list(self.graph.successors(filepath))
    
    def get_transitive_dependencies(self, filepath: str) -> Set[str]:
        """
        Get all dependencies (direct + transitive) of a file.
        
        Args:
            filepath: Path to the file
            
        Returns:
            Set of all dependencies
        """
        if filepath not in self.graph:
            return set()
        
        try:
            # Get all descendants in the DAG
            return set(nx.descendants(self.graph, filepath))
        except nx.NetworkXError:
            return set()
    
    def get_dependency_depth(self, filepath: str) -> int:
        """
        Calculate maximum depth of dependency tree.
        
        Args:
            filepath: Path to the file
            
        Returns:
            Maximum depth (0 if no dependencies)
        """
        if filepath not in self.graph:
            return 0
        
        descendants = self.get_transitive_dependencies(filepath)
        if not descendants:
            return 0
        
        max_depth = 0
        for desc in descendants:
            try:
                # Find shortest path length to this descendant
                path_len = nx.shortest_path_length(self.graph, filepath, desc)
                max_depth = max(max_depth, path_len)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
        
        return max_depth
    
    def get_dependents(self, filepath: str) -> Set[str]:
        """
        Get files that depend on this file (reverse dependencies).
        
        Args:
            filepath: Path to the file
            
        Returns:
            Set of files that include this file
        """
        if filepath not in self.graph:
            return set()
        return set(self.graph.predecessors(filepath))
    
    def find_cycles(self) -> List[List[str]]:
        """
        Find circular dependencies.
        
        Returns:
            List of cycles (each cycle is a list of filepaths)
        """
        try:
            cycles = list(nx.simple_cycles(self.graph))
            return cycles
        except Exception:
            return []
    
    def get_most_included_headers(self, top_n: int = 10) -> List[Tuple[str, int]]:
        """
        Get the most frequently included headers.
        
        Args:
            top_n: Number of top headers to return
            
        Returns:
            List of (header, include_count) tuples
        """
        include_counts = {}
        
        for node in self.graph.nodes():
            in_degree = self.graph.in_degree(node)
            if in_degree > 0:
                include_counts[node] = in_degree
        
        # Sort by count
        sorted_headers = sorted(
            include_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_headers[:top_n]
    
    def get_heaviest_files(self, top_n: int = 10) -> List[Tuple[str, int]]:
        """
        Get files with most dependencies.
        
        Args:
            top_n: Number of files to return
            
        Returns:
            List of (filepath, dependency_count) tuples
        """
        dependency_counts = []
        
        for node in self.graph.nodes():
            if self.graph.nodes[node].get('is_external', False):
                continue
            
            dep_count = len(self.get_transitive_dependencies(node))
            if dep_count > 0:
                dependency_counts.append((node, dep_count))
        
        dependency_counts.sort(key=lambda x: x[1], reverse=True)
        return dependency_counts[:top_n]
    
    def get_node_stats(self) -> Dict:
        """
        Get overall graph statistics.
        
        Returns:
            Dictionary of statistics
        """
        total_nodes = self.graph.number_of_nodes()
        total_edges = self.graph.number_of_edges()
        
        internal_nodes = sum(
            1 for n in self.graph.nodes()
            if not self.graph.nodes[n].get('is_external', False)
        )
        external_nodes = total_nodes - internal_nodes
        
        cycles = self.find_cycles()
        
        # Calculate average degree
        degrees = [d for _, d in self.graph.degree()]
        avg_degree = sum(degrees) / len(degrees) if degrees else 0
        
        return {
            'total_nodes': total_nodes,
            'internal_nodes': internal_nodes,
            'external_nodes': external_nodes,
            'total_edges': total_edges,
            'avg_degree': avg_degree,
            'cycles': len(cycles),
            'max_depth': max(
                (self.get_dependency_depth(n) for n in self.graph.nodes()
                 if not self.graph.nodes[n].get('is_external', False)),
                default=0
            )
        }
    
    def export_dot(self, output_path: Path, max_nodes: int = 100) -> None:
        """
        Export graph to DOT format for visualization.
        
        Args:
            output_path: Path to save DOT file
            max_nodes: Maximum nodes to include (for large graphs)
        """
        # For large graphs, only show internal nodes
        if self.graph.number_of_nodes() > max_nodes:
            subgraph = self.graph.subgraph([
                n for n in self.graph.nodes()
                if not self.graph.nodes[n].get('is_external', False)
            ])
        else:
            subgraph = self.graph
        
        # Write DOT file
        try:
            from networkx.drawing.nx_pydot import write_dot
            write_dot(subgraph, str(output_path))
            print(f"DOT file saved to {output_path}")
        except ImportError:
            print("Warning: pydot not installed, skipping DOT export")
    
    def export_graphml(self, output_path: Path) -> None:
        """
        Export graph to GraphML format.
        
        Args:
            output_path: Path to save GraphML file
        """
        nx.write_graphml(self.graph, str(output_path))
        print(f"GraphML file saved to {output_path}")
