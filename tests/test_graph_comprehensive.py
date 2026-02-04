"""
Comprehensive tests for DependencyGraph - covering all edge cases
"""
import pytest
from includeguard.analyzer.graph import DependencyGraph
from includeguard.analyzer.parser import FileAnalysis, Include


class TestGraphBuilding:
    """Test dependency graph construction"""
    
    def test_empty_graph(self):
        """Test empty graph"""
        graph = DependencyGraph()
        assert graph.graph.number_of_nodes() == 0
        assert graph.graph.number_of_edges() == 0
    
    def test_single_file_no_includes(self):
        """Test graph with single file and no includes"""
        analyses = [
            FileAnalysis(
                filepath="/project/standalone.cpp",
                includes=[],
                total_lines=10,
                code_lines=8
            )
        ]
        
        graph = DependencyGraph()
        graph.build(analyses)
        
        assert graph.graph.number_of_nodes() == 1
        assert graph.graph.number_of_edges() == 0
    
    def test_simple_dependency_chain(self):
        """Test A -> B -> C chain"""
        analyses = [
            FileAnalysis(
                filepath="/project/a.cpp",
                includes=[Include("b.h", 1, False, "/project/b.h")],
                total_lines=10,
                code_lines=8
            ),
            FileAnalysis(
                filepath="/project/b.h",
                includes=[Include("c.h", 1, False, "/project/c.h")],
                total_lines=10,
                code_lines=8
            ),
            FileAnalysis(
                filepath="/project/c.h",
                includes=[],
                total_lines=10,
                code_lines=8
            )
        ]
        
        graph = DependencyGraph()
        graph.build(analyses)
        
        assert graph.graph.number_of_nodes() == 3
        assert graph.graph.number_of_edges() == 2
        
        # Check transitive dependencies
        trans = graph.get_transitive_dependencies("/project/a.cpp")
        assert len(trans) == 2  # b.h and c.h
    
    def test_diamond_dependency(self):
        """Test diamond pattern: A -> B,C -> D"""
        analyses = [
            FileAnalysis(
                filepath="/project/a.cpp",
                includes=[
                    Include("b.h", 1, False, "/project/b.h"),
                    Include("c.h", 2, False, "/project/c.h")
                ],
                total_lines=10,
                code_lines=8
            ),
            FileAnalysis(
                filepath="/project/b.h",
                includes=[Include("d.h", 1, False, "/project/d.h")],
                total_lines=10,
                code_lines=8
            ),
            FileAnalysis(
                filepath="/project/c.h",
                includes=[Include("d.h", 1, False, "/project/d.h")],
                total_lines=10,
                code_lines=8
            ),
            FileAnalysis(
                filepath="/project/d.h",
                includes=[],
                total_lines=10,
                code_lines=8
            )
        ]
        
        graph = DependencyGraph()
        graph.build(analyses)
        
        # A should see all 3 dependencies
        trans = graph.get_transitive_dependencies("/project/a.cpp")
        assert len(trans) == 3
    
    def test_multiple_files_same_include(self):
        """Test multiple files including same header"""
        analyses = [
            FileAnalysis(
                filepath="/project/file1.cpp",
                includes=[Include("common.h", 1, False, "/project/common.h")],
                total_lines=10,
                code_lines=8
            ),
            FileAnalysis(
                filepath="/project/file2.cpp",
                includes=[Include("common.h", 1, False, "/project/common.h")],
                total_lines=10,
                code_lines=8
            ),
            FileAnalysis(
                filepath="/project/common.h",
                includes=[],
                total_lines=10,
                code_lines=8
            )
        ]
        
        graph = DependencyGraph()
        graph.build(analyses)
        
        # Both files should depend on common.h
        deps1 = graph.get_direct_dependencies("/project/file1.cpp")
        deps2 = graph.get_direct_dependencies("/project/file2.cpp")
        
        assert "/project/common.h" in deps1
        assert "/project/common.h" in deps2


class TestCircularDependencies:
    """Test circular dependency detection"""
    
    def test_simple_cycle_two_files(self):
        """Test A -> B -> A"""
        analyses = [
            FileAnalysis(
                filepath="/project/a.h",
                includes=[Include("b.h", 1, False, "/project/b.h")],
                total_lines=10,
                code_lines=8
            ),
            FileAnalysis(
                filepath="/project/b.h",
                includes=[Include("a.h", 1, False, "/project/a.h")],
                total_lines=10,
                code_lines=8
            )
        ]
        
        graph = DependencyGraph()
        graph.build(analyses)
        
        cycles = graph.find_cycles()
        assert len(cycles) >= 1
        
        # Verify cycle contains both files
        cycle = cycles[0]
        assert "/project/a.h" in cycle
        assert "/project/b.h" in cycle
    
    def test_three_file_cycle(self):
        """Test A -> B -> C -> A"""
        analyses = [
            FileAnalysis(
                filepath="/project/a.h",
                includes=[Include("b.h", 1, False, "/project/b.h")],
                total_lines=10,
                code_lines=8
            ),
            FileAnalysis(
                filepath="/project/b.h",
                includes=[Include("c.h", 1, False, "/project/c.h")],
                total_lines=10,
                code_lines=8
            ),
            FileAnalysis(
                filepath="/project/c.h",
                includes=[Include("a.h", 1, False, "/project/a.h")],
                total_lines=10,
                code_lines=8
            )
        ]
        
        graph = DependencyGraph()
        graph.build(analyses)
        
        cycles = graph.find_cycles()
        assert len(cycles) >= 1
        assert len(cycles[0]) == 3
    
    def test_self_cycle(self):
        """Test file including itself"""
        analyses = [
            FileAnalysis(
                filepath="/project/self.h",
                includes=[Include("self.h", 1, False, "/project/self.h")],
                total_lines=10,
                code_lines=8
            )
        ]
        
        graph = DependencyGraph()
        graph.build(analyses)
        
        cycles = graph.find_cycles()
        assert len(cycles) >= 1
    
    def test_no_cycles(self):
        """Test graph with no cycles"""
        analyses = [
            FileAnalysis(
                filepath="/project/a.cpp",
                includes=[Include("b.h", 1, False, "/project/b.h")],
                total_lines=10,
                code_lines=8
            ),
            FileAnalysis(
                filepath="/project/b.h",
                includes=[Include("c.h", 1, False, "/project/c.h")],
                total_lines=10,
                code_lines=8
            ),
            FileAnalysis(
                filepath="/project/c.h",
                includes=[],
                total_lines=10,
                code_lines=8
            )
        ]
        
        graph = DependencyGraph()
        graph.build(analyses)
        
        cycles = graph.find_cycles()
        assert len(cycles) == 0


class TestDependencyQueries:
    """Test dependency query methods"""
    
    def test_direct_dependencies(self):
        """Test getting direct dependencies"""
        analyses = [
            FileAnalysis(
                filepath="/project/main.cpp",
                includes=[
                    Include("a.h", 1, False, "/project/a.h"),
                    Include("b.h", 2, False, "/project/b.h")
                ],
                total_lines=10,
                code_lines=8
            ),
            FileAnalysis(
                filepath="/project/a.h",
                includes=[],
                total_lines=10,
                code_lines=8
            ),
            FileAnalysis(
                filepath="/project/b.h",
                includes=[],
                total_lines=10,
                code_lines=8
            )
        ]
        
        graph = DependencyGraph()
        graph.build(analyses)
        
        deps = graph.get_direct_dependencies("/project/main.cpp")
        assert len(deps) == 2
        assert "/project/a.h" in deps
        assert "/project/b.h" in deps
    
    def test_transitive_dependencies(self):
        """Test getting transitive dependencies"""
        analyses = [
            FileAnalysis(
                filepath="/project/a.cpp",
                includes=[Include("b.h", 1, False, "/project/b.h")],
                total_lines=10,
                code_lines=8
            ),
            FileAnalysis(
                filepath="/project/b.h",
                includes=[Include("c.h", 1, False, "/project/c.h")],
                total_lines=10,
                code_lines=8
            ),
            FileAnalysis(
                filepath="/project/c.h",
                includes=[Include("d.h", 1, False, "/project/d.h")],
                total_lines=10,
                code_lines=8
            ),
            FileAnalysis(
                filepath="/project/d.h",
                includes=[],
                total_lines=10,
                code_lines=8
            )
        ]
        
        graph = DependencyGraph()
        graph.build(analyses)
        
        trans = graph.get_transitive_dependencies("/project/a.cpp")
        assert len(trans) == 3  # b.h, c.h, d.h
    
    def test_dependency_depth(self):
        """Test dependency depth calculation"""
        analyses = [
            FileAnalysis(
                filepath="/project/a.cpp",
                includes=[Include("b.h", 1, False, "/project/b.h")],
                total_lines=10,
                code_lines=8
            ),
            FileAnalysis(
                filepath="/project/b.h",
                includes=[Include("c.h", 1, False, "/project/c.h")],
                total_lines=10,
                code_lines=8
            ),
            FileAnalysis(
                filepath="/project/c.h",
                includes=[],
                total_lines=10,
                code_lines=8
            )
        ]
        
        graph = DependencyGraph()
        graph.build(analyses)
        
        # Depth is maximum depth from source file
        depth_a = graph.get_dependency_depth("/project/a.cpp")
        assert depth_a == 2  # a -> b -> c is 2 levels deep
    
    def test_reverse_dependencies(self):
        """Test getting reverse dependencies (who depends on me)"""
        analyses = [
            FileAnalysis(
                filepath="/project/a.cpp",
                includes=[Include("util.h", 1, False, "/project/util.h")],
                total_lines=10,
                code_lines=8
            ),
            FileAnalysis(
                filepath="/project/b.cpp",
                includes=[Include("util.h", 1, False, "/project/util.h")],
                total_lines=10,
                code_lines=8
            ),
            FileAnalysis(
                filepath="/project/util.h",
                includes=[],
                total_lines=10,
                code_lines=8
            )
        ]
        
        graph = DependencyGraph()
        graph.build(analyses)
        
        # util.h should be used by both a.cpp and b.cpp
        reverse = graph.get_dependents("/project/util.h")
        assert len(reverse) >= 2


class TestGraphStatistics:
    """Test graph statistics and metrics"""
    
    def test_node_stats(self):
        """Test node statistics calculation"""
        analyses = [
            FileAnalysis(
                filepath="/project/a.cpp",
                includes=[Include("b.h", 1, False, "/project/b.h")],
                total_lines=10,
                code_lines=8
            ),
            FileAnalysis(
                filepath="/project/b.h",
                includes=[],
                total_lines=20,
                code_lines=15
            )
        ]
        
        graph = DependencyGraph()
        graph.build(analyses)
        
        stats = graph.get_node_stats()
        assert stats['total_nodes'] == 2
        assert stats['total_edges'] == 1
        assert 'avg_degree' in stats
    
    def test_most_included_headers(self):
        """Test finding most frequently included headers"""
        analyses = [
            FileAnalysis(
                filepath="/project/a.cpp",
                includes=[Include("common.h", 1, False, "/project/common.h")],
                total_lines=10,
                code_lines=8
            ),
            FileAnalysis(
                filepath="/project/b.cpp",
                includes=[Include("common.h", 1, False, "/project/common.h")],
                total_lines=10,
                code_lines=8
            ),
            FileAnalysis(
                filepath="/project/c.cpp",
                includes=[
                    Include("common.h", 1, False, "/project/common.h"),
                    Include("rare.h", 2, False, "/project/rare.h")
                ],
                total_lines=10,
                code_lines=8
            ),
            FileAnalysis(
                filepath="/project/common.h",
                includes=[],
                total_lines=50,
                code_lines=40
            ),
            FileAnalysis(
                filepath="/project/rare.h",
                includes=[],
                total_lines=10,
                code_lines=8
            )
        ]
        
        graph = DependencyGraph()
        graph.build(analyses)
        
        # common.h should be most included
        most_used = graph.get_most_included_headers(top_n=1)
        assert len(most_used) >= 1
        assert most_used[0][0] == "/project/common.h"
        assert most_used[0][1] == 3  # Included 3 times


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_nonexistent_file_dependency(self):
        """Test dependency on file that doesn't exist in project"""
        analyses = [
            FileAnalysis(
                filepath="/project/main.cpp",
                includes=[Include("missing.h", 1, False, "/project/missing.h")],
                total_lines=10,
                code_lines=8
            )
        ]
        
        graph = DependencyGraph()
        graph.build(analyses)
        
        # Should still build graph, just won't have target node
        assert graph.graph.number_of_nodes() >= 1
    
    def test_system_header_dependencies(self):
        """Test handling of system headers"""
        analyses = [
            FileAnalysis(
                filepath="/project/main.cpp",
                includes=[
                    Include("iostream", 1, True, "<iostream>"),
                    Include("vector", 2, True, "<vector>")
                ],
                total_lines=10,
                code_lines=8
            )
        ]
        
        graph = DependencyGraph()
        graph.build(analyses)
        
        # System headers should be tracked
        deps = graph.get_direct_dependencies("/project/main.cpp")
        assert len(deps) >= 2
    
    def test_very_large_graph(self):
        """Test handling of large dependency graph"""
        # Create 100 files
        analyses = []
        for i in range(100):
            # Each file includes the next one (chain)
            next_file = f"/project/file_{i+1}.h" if i < 99 else None
            includes = [Include(f"file_{i+1}.h", 1, False, next_file)] if next_file else []
            
            analyses.append(FileAnalysis(
                filepath=f"/project/file_{i}.h",
                includes=includes,
                total_lines=10,
                code_lines=8
            ))
        
        graph = DependencyGraph()
        graph.build(analyses)
        
        assert graph.graph.number_of_nodes() == 100
        
        # First file should transitively depend on all others
        trans = graph.get_transitive_dependencies("/project/file_0.h")
        assert len(trans) == 99


# Run tests if executed directly
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
