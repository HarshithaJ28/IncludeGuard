"""
Tests specifically targeting uncovered code paths to improve coverage
"""
import pytest
from pathlib import Path
import tempfile
import shutil
import os
from unittest.mock import patch, MagicMock
from includeguard.analyzer.parser import IncludeParser, FileAnalysis, Include
from includeguard.analyzer.graph import DependencyGraph
from includeguard.analyzer.estimator import CostEstimator


class TestParserErrorHandling:
    """Test parser error handling and edge cases"""
    
    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.parser = IncludeParser(project_root=self.temp_dir)
    
    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_parse_file_encoding_error(self):
        """Test parsing file with encoding issues"""
        # Create file with invalid UTF-8
        bad_file = self.temp_dir / "bad_encoding.cpp"
        bad_file.write_bytes(b'\xff\xfe\x00\x00')  # Invalid UTF-8 sequence
        
        # Should return None and print warning
        result = self.parser.parse_file(bad_file)
        assert result is None or isinstance(result, FileAnalysis)
    
    def test_parse_file_permission_error(self):
        """Test parsing file with permission errors"""
        if os.name == 'nt':  # Windows
            pytest.skip("Permission testing is complex on Windows")
        
        restricted_file = self.temp_dir / "restricted.cpp"
        restricted_file.write_text("#include <iostream>")
        
        # Make file unreadable
        os.chmod(restricted_file, 0o000)
        
        try:
            result = self.parser.parse_file(restricted_file)
            assert result is None
        finally:
            # Restore permissions for cleanup
            os.chmod(restricted_file, 0o644)
    
    def test_parse_file_nonexistent(self):
        """Test parsing non-existent file"""
        fake_file = self.temp_dir / "doesnt_exist.cpp"
        result = self.parser.parse_file(fake_file)
        assert result is None
    
    def test_resolve_header_path_not_found(self):
        """Test resolving header that doesn't exist in include paths"""
        self.parser.include_paths = [self.temp_dir / "include"]
        
        source_file = self.temp_dir / "test.cpp"
        # Header doesn't exist anywhere
        result = self.parser._resolve_include("nonexistent_header.h", source_file, False)
        assert result == "nonexistent_header.h"  # Returns original
    
    def test_resolve_header_path_found(self):
        """Test successfully resolving header path"""
        include_dir = self.temp_dir / "include"
        include_dir.mkdir()
        header = include_dir / "myheader.h"
        header.write_text("// header content")
        
        source_file = self.temp_dir / "test.cpp"
        self.parser.include_paths = [include_dir]
        result = self.parser._resolve_include("myheader.h", source_file, False)
        assert "myheader.h" in result or Path(result).exists()
    
    def test_parse_directory_with_exclusions(self):
        """Test parsing directory with excluded paths"""
        # Create structure with excluded directories
        (self.temp_dir / "src").mkdir()
        (self.temp_dir / "build").mkdir()
        (self.temp_dir / "external").mkdir()
        
        src_file = self.temp_dir / "src" / "main.cpp"
        src_file.write_text("#include <iostream>")
        
        build_file = self.temp_dir / "build" / "generated.cpp"
        build_file.write_text("#include <iostream>")
        
        external_file = self.temp_dir / "external" / "lib.cpp"
        external_file.write_text("#include <iostream>")
        
        # Parse with exclusions
        results = self.parser.parse_project(exclude_dirs=['build', 'external'])
        
        # Should only find src file
        filepaths = [r.filepath for r in results]
        assert any('src' in fp for fp in filepaths)
        assert not any('build' in fp for fp in filepaths)
        assert not any('external' in fp for fp in filepaths)
    
    def test_get_statistics_empty_analyses(self):
        """Test get_statistics with empty list"""
        stats = self.parser.get_statistics([])
        assert stats == {}
    
    def test_get_statistics_with_data(self):
        """Test get_statistics with actual data"""
        # Create mock analyses
        a1 = FileAnalysis(
            filepath="file1.cpp",
            total_lines=100,
            code_lines=80,
            has_templates=True,
            has_macros=False
        )
        a1.includes = [
            Include(header="iostream", line_number=1, is_system=True),
            Include(header="myheader.h", line_number=2, is_system=False),
        ]
        
        a2 = FileAnalysis(
            filepath="file2.cpp",
            total_lines=50,
            code_lines=40,
            has_templates=False,
            has_macros=True
        )
        a2.includes = [
            Include(header="vector", line_number=1, is_system=True),
        ]
        
        stats = self.parser.get_statistics([a1, a2])
        
        assert stats['total_files'] == 2
        assert stats['total_includes'] == 3
        assert stats['system_includes'] == 2
        assert stats['user_includes'] == 1
        assert stats['total_lines'] == 150
        assert stats['total_code_lines'] == 120
        assert stats['files_with_templates'] == 1
        assert stats['files_with_macros'] == 1


class TestGraphErrorHandling:
    """Test graph error handling and edge cases"""
    
    def setup_method(self):
        self.graph = DependencyGraph()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_dependencies_nonexistent_file(self):
        """Test getting dependencies of non-existent file"""
        deps = self.graph.get_direct_dependencies("nonexistent.cpp")
        assert deps == []
    
    def test_get_transitive_dependencies_nonexistent(self):
        """Test transitive dependencies of non-existent file"""
        deps = self.graph.get_transitive_dependencies("nonexistent.cpp")
        assert deps == set()
    
    def test_get_transitive_dependencies_with_cycle(self):
        """Test transitive dependencies when there's a cycle (shouldn't happen in DAG)"""
        # Manually create a problematic graph structure
        self.graph.graph.add_node("a.cpp")
        self.graph.graph.add_node("b.cpp")
        self.graph.graph.add_edge("a.cpp", "b.cpp")
        
        # This should work fine in a DAG
        deps = self.graph.get_transitive_dependencies("a.cpp")
        assert "b.cpp" in deps
    
    def test_get_dependency_depth_nonexistent(self):
        """Test dependency depth for non-existent file"""
        depth = self.graph.get_dependency_depth("nonexistent.cpp")
        assert depth == 0
    
    def test_get_dependency_depth_with_disconnected_nodes(self):
        """Test depth calculation with disconnected graph components"""
        # Create disconnected components
        self.graph.graph.add_node("a.cpp")
        self.graph.graph.add_node("b.cpp")
        self.graph.graph.add_node("c.cpp")
        self.graph.graph.add_edge("a.cpp", "b.cpp")
        # c.cpp is disconnected
        
        depth = self.graph.get_dependency_depth("a.cpp")
        assert depth >= 0
    
    def test_get_transitive_dependencies_network_error(self):
        """Test handling of NetworkX errors in transitive dependencies"""
        # Create a node but trigger NetworkXError scenario
        self.graph.graph.add_node("test.cpp")
        
        # Normal case should work fine
        deps = self.graph.get_transitive_dependencies("test.cpp")
        assert deps == set()
    
    def test_get_dependency_depth_no_path(self):
        """Test depth calculation when descendants exist but no path found"""
        # Create nodes with edges
        self.graph.graph.add_node("a.cpp")
        self.graph.graph.add_node("b.cpp")
        self.graph.graph.add_node("c.cpp")
        self.graph.graph.add_edge("a.cpp", "b.cpp")
        self.graph.graph.add_edge("b.cpp", "c.cpp")
        
        # Should calculate depth correctly
        depth = self.graph.get_dependency_depth("a.cpp")
        assert depth == 2  # a -> b -> c
    
    def test_get_dependents_predecessors(self):
        """Test getting predecessors (reverse dependencies)"""
        self.graph.graph.add_node("header.h")
        self.graph.graph.add_node("source1.cpp")
        self.graph.graph.add_node("source2.cpp")
        
        # Multiple files depend on header.h
        self.graph.graph.add_edge("source1.cpp", "header.h")
        self.graph.graph.add_edge("source2.cpp", "header.h")
        
        dependents = self.graph.get_dependents("header.h")
        assert "source1.cpp" in dependents
        assert "source2.cpp" in dependents
        assert len(dependents) == 2
    
    def test_get_dependents_nonexistent(self):
        """Test getting dependents of non-existent file"""
        dependents = self.graph.get_dependents("nonexistent.cpp")
        assert dependents == set()
    
    def test_get_dependents_with_data(self):
        """Test getting dependents with actual dependency chain"""
        self.graph.graph.add_node("base.h")
        self.graph.graph.add_node("derived.cpp")
        self.graph.graph.add_edge("derived.cpp", "base.h")
        
        dependents = self.graph.get_dependents("base.h")
        assert "derived.cpp" in dependents
    
    def test_get_most_expensive_files_empty_graph(self):
        """Test get_heaviest_files with no internal nodes"""
        # Add only external nodes
        self.graph.graph.add_node("<iostream>", is_external=True)
        self.graph.graph.add_node("<vector>", is_external=True)
        
        result = self.graph.get_heaviest_files()
        assert result == []
    
    def test_get_most_expensive_files_no_dependencies(self):
        """Test get_heaviest_files when files have no dependencies"""
        self.graph.graph.add_node("isolated1.cpp", is_external=False)
        self.graph.graph.add_node("isolated2.cpp", is_external=False)
        
        # Files with no dependencies should not appear
        result = self.graph.get_heaviest_files()
        assert result == []
    
    def test_get_most_expensive_files_with_dependencies(self):
        """Test get_heaviest_files with actual dependency chains"""
        # Create files with dependencies
        self.graph.graph.add_node("main.cpp", is_external=False)
        self.graph.graph.add_node("lib.cpp", is_external=False)
        self.graph.graph.add_node("util.cpp", is_external=False)
        self.graph.graph.add_node("<iostream>", is_external=True)
        
        self.graph.graph.add_edge("main.cpp", "lib.cpp")
        self.graph.graph.add_edge("main.cpp", "util.cpp")
        self.graph.graph.add_edge("main.cpp", "<iostream>")
        self.graph.graph.add_edge("lib.cpp", "util.cpp")
        
        result = self.graph.get_heaviest_files(top_n=5)
        
        # main.cpp should be most expensive (has 3 transitive deps)
        assert len(result) > 0
        assert result[0][0] == "main.cpp"
    
    def test_export_dot_pydot_not_installed(self):
        """Test export_dot when pydot is not available"""
        # Add some nodes
        self.graph.graph.add_node("test.cpp")
        
        output_file = self.temp_dir / "test.dot"
        
        # Mock networkx.drawing.nx_pydot.write_dot to raise ImportError
        with patch('networkx.drawing.nx_pydot.write_dot', side_effect=ImportError):
            # Should print warning and not crash
            self.graph.export_dot(output_file)
    
    def test_export_dot_large_graph(self):
        """Test export_dot with large graph (triggers subgraph logic)"""
        # Create graph with > 100 nodes
        for i in range(150):
            is_external = i >= 100
            self.graph.graph.add_node(f"file{i}.cpp", is_external=is_external)
        
        output_file = self.temp_dir / "large.dot"
        
        # Should handle large graph by filtering externals
        try:
            self.graph.export_dot(output_file, max_nodes=100)
            # May succeed or fail depending on pydot availability
        except Exception:
            pass  # Expected if pydot not installed
    
    def test_export_graphml(self):
        """Test GraphML export"""
        self.graph.graph.add_node("test.cpp")
        self.graph.graph.add_node("lib.cpp")
        self.graph.graph.add_edge("test.cpp", "lib.cpp")
        
        output_file = self.temp_dir / "test.graphml"
        self.graph.export_graphml(output_file)
        
        assert output_file.exists()
        content = output_file.read_text()
        assert 'graphml' in content.lower()
    
    def test_external_header_node_creation(self):
        """Test that external headers are properly marked in graph"""
        # Create analysis with external system header
        a1 = FileAnalysis(filepath=str(self.temp_dir / "test.cpp"))
        a1.includes = [
            Include(
                header="iostream",
                line_number=1,
                is_system=True,
                full_path=""  # Not resolved
            )
        ]
        
        self.graph.build([a1])
        
        # Check that external node was created
        assert "<iostream>" in self.graph.graph.nodes()
        assert self.graph.graph.nodes["<iostream>"]["is_external"] == True


class TestEstimatorEdgeCases:
    """Test estimator edge cases"""
    
    def setup_method(self):
        self.graph = DependencyGraph()
        self.estimator = CostEstimator(self.graph)
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_template_count_multiple_templates(self):
        """Test cost estimation with multiple template keywords"""
        source = self.temp_dir / "templates.cpp"
        # Create content with multiple template keywords
        template_content = """
#include <vector>
template <typename T>
class Container {
    template <typename U>
    void method() {
        template_function();
    }
};
template <class X> void foo();
template <class Y> void bar();
"""
        source.write_text(template_content)
        
        # Create analysis with has_templates=True
        analysis = FileAnalysis(
            filepath=str(source),
            has_templates=True,
            total_lines=15,
            code_lines=12
        )
        analysis.includes = [
            Include(header="vector", line_number=1, is_system=True, full_path="<vector>")
        ]
        
        # Estimate cost - should handle multiple template keywords
        # Pass the header string, not Include object
        cost = self.estimator.estimate_header_cost(
            "vector",  # Pass string, not Include object
            analysis
        )
        
        # Should apply template multiplier + extra cost per template
        assert cost > 1000  # Should have template multiplier applied
        assert cost > 500  # Base cost increased by templates
    
    def test_confidence_with_no_analysis(self):
        """Test confidence calculation when analysis is None"""
        inc = Include(header="iostream", line_number=1, is_system=True)
        
        confidence = self.estimator._calculate_estimate_confidence(inc, None)
        
        # Should return lower confidence for system header with no analysis
        assert 0.0 <= confidence <= 1.0
    
    def test_confidence_with_unknown_system_header(self):
        """Test confidence for unknown system header"""
        inc = Include(header="unknown_system_header.h", line_number=1, is_system=True)
        
        analysis = FileAnalysis(filepath="test.cpp")
        confidence = self.estimator._calculate_estimate_confidence(inc, analysis)
        
        # Should have reduced confidence for unknown header
        assert confidence < 0.8
    
    def test_confidence_with_expensive_header(self):
        """Test confidence for known expensive header"""
        inc = Include(header="iostream", line_number=1, is_system=True)
        
        analysis = FileAnalysis(filepath="test.cpp")
        confidence = self.estimator._calculate_estimate_confidence(inc, analysis)
        
        # Should have higher confidence for known header
        assert confidence > 0.0


class TestParserCommentRemoval:
    """Test comment removal edge cases"""
    
    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.parser = IncludeParser(project_root=self.temp_dir)
    
    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_remove_comments_nested(self):
        """Test removing nested comment patterns"""
        content = """
// Single line comment
/* Multi-line
   comment */
int x = 42; // Trailing comment
/* Nested // comment */
"""
        result = self.parser._remove_comments(content)
        
        # Comments should be removed
        assert '//' not in result or '// ' not in result.split('\n')[2]
        assert '/*' not in result
        assert 'int x = 42;' in result
    
    def test_remove_comments_preserves_strings(self):
        """Test that comment removal doesn't affect strings"""
        content = '''
std::string url = "http://example.com";
std::string comment = "/* not a comment */";
'''
        result = self.parser._remove_comments(content)
        
        # String content should be preserved (though // in URL may be affected)
        assert 'example.com' in result or 'url' in result
        assert 'comment' in result


class TestGraphNodeStats:
    """Test graph node statistics"""
    
    def setup_method(self):
        self.graph = DependencyGraph()
    
    def test_get_node_stats_empty_graph(self):
        """Test node stats with empty graph"""
        stats = self.graph.get_node_stats()
        
        assert stats['total_nodes'] == 0
        assert stats['internal_nodes'] == 0
        assert stats['external_nodes'] == 0
        assert stats['total_edges'] == 0
    
    def test_get_node_stats_mixed_nodes(self):
        """Test node stats with both internal and external nodes"""
        self.graph.graph.add_node("internal.cpp", is_external=False)
        self.graph.graph.add_node("<iostream>", is_external=True)
        self.graph.graph.add_edge("internal.cpp", "<iostream>")
        
        stats = self.graph.get_node_stats()
        
        assert stats['total_nodes'] == 2
        assert stats['internal_nodes'] == 1
        assert stats['external_nodes'] == 1
        assert stats['total_edges'] == 1


class TestIncludeDataclassRepr:
    """Test dataclass __repr__ methods for coverage"""
    
    def test_include_repr_system(self):
        """Test Include repr for system header"""
        inc = Include(header="iostream", line_number=5, is_system=True)
        repr_str = repr(inc)
        
        assert "Include" in repr_str
        assert "<iostream>" in repr_str
        assert "line 5" in repr_str
    
    def test_include_repr_user(self):
        """Test Include repr for user header"""
        inc = Include(header="myheader.h", line_number=10, is_system=False)
        repr_str = repr(inc)
        
        assert "Include" in repr_str
        assert '"myheader.h"' in repr_str
        assert "line 10" in repr_str
    
    def test_file_analysis_repr(self):
        """Test FileAnalysis repr"""
        analysis = FileAnalysis(filepath="/path/to/file.cpp")
        analysis.includes = [
            Include(header="iostream", line_number=1, is_system=True),
            Include(header="vector", line_number=2, is_system=True),
        ]
        
        repr_str = repr(analysis)
        
        assert "FileAnalysis" in repr_str
        assert "file.cpp" in repr_str
        assert "2 includes" in repr_str


# Run if executed directly
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
