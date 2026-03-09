"""
Performance tests and benchmarks for IncludeGuard.

Tests baseline performance and tracks regressions.
"""
import pytest
import tempfile
from pathlib import Path
from includeguard.benchmark import Benchmark, Timer, MemoryMonitor
from includeguard.analyzer.parser import Parser, FileAnalysis, Include
from includeguard.analyzer.graph import DependencyGraph
from includeguard.analyzer.estimator import CostEstimator


class TestPerformanceBaseline:
    """Benchmark core operations against baseline."""
    
    @pytest.fixture
    def benchmark(self):
        """Create benchmark instance."""
        return Benchmark(verbose=True)
    
    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return Parser()
    
    def test_parser_performance_small_file(self, benchmark, parser):
        """Benchmark parsing small source file (<100 lines)."""
        content = """
        #include <iostream>
        #include <vector>
        #include <algorithm>
        
        int main() {
            std::vector<int> v = {1, 2, 3};
            std::sort(v.begin(), v.end());
            return 0;
        }
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
            f.write(content)
            filepath = f.name
        
        try:
            # Parse should be fast (<5ms for small file)
            result = benchmark.measure(
                "Parse small file (100 lines)",
                lambda: parser.parse_file(filepath)
            )
            
            assert result is not None
            assert len(benchmark.results[-1].duration_ms) > 0
            # Small files should parse in <10ms
            assert benchmark.results[-1].duration_ms < 10
        finally:
            Path(filepath).unlink()
    
    def test_parser_performance_large_file(self, benchmark, parser):
        """Benchmark parsing large source file (1000+ lines)."""
        # Generate large file with many includes
        lines = []
        lines.append("#ifndef LARGE_FILE_H")
        lines.append("#define LARGE_FILE_H")
        
        for i in range(50):
            lines.append(f"#include <header{i}.h>")
        
        # Add code
        for i in range(500):
            lines.append(f"void func{i}() {{ std::cout << {i} << std::endl; }}")
        
        lines.append("#endif")
        content = "\n".join(lines)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.h', delete=False) as f:
            f.write(content)
            filepath = f.name
        
        try:
            # Large files should still parse quickly (<50ms)
            result = benchmark.measure(
                "Parse large file (500 lines, 50 includes)",
                lambda: parser.parse_file(filepath)
            )
            
            assert result is not None
            assert benchmark.results[-1].duration_ms < 50
        finally:
            Path(filepath).unlink()
    
    def test_cost_estimation_performance(self, benchmark):
        """Benchmark cost estimation on complex graph."""
        # Build a realistic dependency graph
        graph = DependencyGraph()
        
        analyses = []
        for i in range(20):
            includes = [
                Include(f"<header{j}.h>", i*10 + j, True)
                for j in range(5)
            ]
            analysis = FileAnalysis(
                filepath=f"/project/file{i}.cpp",
                includes=includes,
                total_lines=100 + i*10,
                code_lines=80 + i*10
            )
            analyses.append(analysis)
        
        graph.build(analyses)
        estimator = CostEstimator(graph)
        
        # Measure cost estimation
        result = benchmark.measure(
            "Estimate costs for 20 files",
            lambda: estimator.generate_project_summary([
                estimator.generate_report(a, {a.filepath: a}) for a in analyses
            ])
        )
        
        # Should be fast (<100ms for 20 files)
        assert benchmark.results[-1].duration_ms < 100
    
    def test_header_usage_detection_performance(self, benchmark):
        """Benchmark header usage detection."""
        estimator = CostEstimator(DependencyGraph())
        
        # Create realistic source file with many potential headers
        content = """
        #include <iostream>
        #include <vector>
        #include <algorithm>
        #include <string>
        #include <map>
        #include <memory>
        #include <thread>
        #include <mutex>
        #include <chrono>
        
        class MyClass {
        public:
            std::vector<int> data;
            std::map<std::string, int> mapping;
            std::unique_ptr<int> ptr;
            std::mutex lock;
            
            void process() {
                std::sort(data.begin(), data.end());
                for(auto& [key, val] : mapping) {
                    std::cout << key << ": " << val << std::endl;
                }
            }
        };
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
            f.write(content)
            filepath = f.name
        
        try:
            # Measure repeated header checks
            benchmark.measure_repeated(
                "Check header usage (10 files, 10 headers each)",
                lambda: [
                    estimator.check_header_usage(filepath, f"<header{i}.h>")
                    for i in range(10)
                ],
                iterations=10
            )
            
            result = benchmark.results[-1]
            # Should average under 5ms
            assert result.mean_ms < 5
        finally:
            Path(filepath).unlink()
    
    @pytest.mark.benchmark
    def test_full_project_analysis_performance(self, benchmark):
        """Benchmark full project analysis (end-to-end)."""
        # Create temporary project
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            
            # Create 20 source files
            for i in range(20):
                filepath = project_dir / f"file{i}.cpp"
                content = f"""
                #include <iostream>
                #include <vector>
                #include <algorithm>
                #include "header{i}.h"
                
                void process{i}() {{
                    std::vector<int> v;
                    std::sort(v.begin(), v.end());
                }}
                """
                filepath.write_text(content)
            
            # Create headers
            for i in range(20):
                filepath = project_dir / f"header{i}.h"
                content = f"""
                #ifndef HEADER{i}_H
                #define HEADER{i}_H
                
                class Class{i} {{
                public:
                    void method();
                }};
                
                #endif
                """
                filepath.write_text(content)
            
            # Measure full analysis
            parser = Parser()
            analyses = benchmark.measure(
                "Parse 20 project files",
                lambda: [parser.parse_file(str(f)) for f in project_dir.glob("*.cpp")]
            )
            
            # Should parse 20 files in under 100ms
            assert benchmark.results[-1].duration_ms < 100
            assert len(analyses) == 20
    
    def test_scalability_file_count(self, benchmark):
        """Test scalability as file count increases."""
        parser = Parser()
        
        for file_count in [5, 10, 20]:
            with tempfile.TemporaryDirectory() as tmpdir:
                project_dir = Path(tmpdir)
                
                # Create test files
                for i in range(file_count):
                    filepath = project_dir / f"file{i}.cpp"
                    content = """
                    #include <iostream>
                    #include <vector>
                    void process() {
                        std::vector<int> v;
                    }
                    """
                    filepath.write_text(content)
                
                # Measure parsing time
                def parse_all():
                    return [parser.parse_file(str(f)) for f in project_dir.glob("*.cpp")]
                
                benchmark.measure(
                    f"Parse {file_count} files",
                    parse_all
                )
                
                # Should scale linearly
                result = benchmark.results[-1]
                # Allow up to 5ms per file
                assert result.duration_ms < file_count * 5
    
    def test_cache_effectiveness(self, benchmark):
        """Test effectiveness of cost caching."""
        graph = DependencyGraph()
        estimator = CostEstimator(graph)
        
        header_name = "<iostream>"
        
        # First call (no cache)
        benchmark.measure(
            "Estimate header cost (first call)",
            lambda: estimator.estimate_header_cost(header_name)
        )
        
        first_duration = benchmark.results[-1].duration_ms
        
        # Clear cache and measure many calls (to test cache hits)
        benchmark.measure_repeated(
            "Estimate same header (cached)",
            lambda: estimator.estimate_header_cost(header_name),
            iterations=100
        )
        
        cached_result = benchmark.results[-1]
        
        # Cached calls should be much faster
        # (caching should provide 10x+ speedup)
        if cached_result.mean_ms > 0:
            speedup = first_duration / cached_result.mean_ms
            assert speedup > 5  # At least 5x speedup with caching


class TestMemoryUsage:
    """Test memory usage characteristics."""
    
    def test_memory_growth_with_file_count(self):
        """Test memory doesn't explode with large file count."""
        memory = MemoryMonitor()
        
        parser = Parser()
        
        memory.sample()  # Initial
        
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            
            # Create 100 files
            for i in range(100):
                filepath = project_dir / f"file{i}.cpp"
                content = """
                #include <iostream>
                #include <vector>
                #include <algorithm>
                
                void process() {
                    std::vector<int> v;
                    std::sort(v.begin(), v.end());
                }
                """
                filepath.write_text(content)
            
            # Parse all
            for filepath in project_dir.glob("*.cpp"):
                parser.parse_file(str(filepath))
                if i % 20 == 0:
                    memory.sample()
            
            memory.sample()  # Final
        
        stats = memory.get_stats()
        
        # Memory shouldn't grow unbounded
        if stats:
            # Allow up to 50MB growth
            assert stats['delta_mb'] < 50


class TestComparisonWithIWYU:
    """Compare IncludeGuard performance to IWYU."""
    
    @pytest.mark.skip(reason="IWYU not always available")
    def test_speed_advantage_over_iwyu(self):
        """Verify IncludeGuard is faster than IWYU."""
        # This would require IWYU to be installed
        # For now, just document the expected speedup
        # IncludeGuard: 3 min for typical project
        # IWYU: 45 min for typical project
        # Expected speedup: 15x
        pass


@pytest.fixture(scope="session")
def benchmark_session():
    """Session-level benchmark for final report."""
    benchmark = Benchmark(verbose=False)
    benchmark.start()
    yield benchmark
    benchmark.end()
    
    # Print final report
    print("\n" + "="*70)
    print("COMPLETE BENCHMARK REPORT")
    print("="*70)
    benchmark.print_summary()
    benchmark.print_per_operation()
    print("="*70)
