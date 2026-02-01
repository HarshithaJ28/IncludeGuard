"""Test dependency graph"""
from includeguard.analyzer.parser import IncludeParser, FileAnalysis, Include
from includeguard.analyzer.graph import DependencyGraph

def test_graph_building():
    # Create mock analyses
    analyses = [
        FileAnalysis(
            filepath="/project/main.cpp",
            includes=[
                Include("iostream", 1, True, "<iostream>"),
                Include("utils.h", 2, False, "/project/utils.h")
            ],
            total_lines=50,
            code_lines=40
        ),
        FileAnalysis(
            filepath="/project/utils.h",
            includes=[
                Include("vector", 1, True, "<vector>"),
                Include("string", 2, True, "<string>")
            ],
            total_lines=30,
            code_lines=25
        )
    ]
    
    # Build graph
    graph = DependencyGraph()
    graph.build(analyses)
    
    assert graph.graph.number_of_nodes() >= 2
    assert graph.graph.number_of_edges() >= 2
    
    # Test dependencies
    deps = graph.get_direct_dependencies("/project/main.cpp")
    assert len(deps) == 2
    
    trans_deps = graph.get_transitive_dependencies("/project/main.cpp")
    assert len(trans_deps) >= 2  # Should include utils.h dependencies
    
    stats = graph.get_node_stats()
    print("✓ Graph test passed!")
    print(f"  Nodes: {stats['total_nodes']}")
    print(f"  Edges: {stats['total_edges']}")
    print(f"  Average degree: {stats['avg_degree']:.2f}")

if __name__ == '__main__':
    test_graph_building()
