"""
Pytest configuration and fixtures for IncludeGuard tests.

Provides common fixtures and test configuration.
"""
import pytest
import tempfile
from pathlib import Path


@pytest.fixture
def temp_cpp_file():
    """Create a temporary C++ file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
        f.write("""
#include <iostream>
#include <vector>
#include <algorithm>

int main() {
    std::vector<int> v = {3, 1, 2};
    std::sort(v.begin(), v.end());
    std::cout << "Done" << std::endl;
    return 0;
}
""")
        filepath = f.name
    
    yield filepath
    
    # Cleanup
    Path(filepath).unlink(missing_ok=True)


@pytest.fixture
def temp_header_file():
    """Create a temporary header file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.h', delete=False) as f:
        f.write("""
#ifndef TEST_HEADER_H
#define TEST_HEADER_H

#include <vector>
#include <string>

class TestClass {
public:
    void process(const std::vector<int>& data);
    std::string getName() const;
};

#endif
""")
        filepath = f.name
    
    yield filepath
    
    # Cleanup
    Path(filepath).unlink(missing_ok=True)


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory with multiple files."""
    tmpdir = Path(tempfile.mkdtemp())
    
    # Create source files
    (tmpdir / "main.cpp").write_text("""
#include <iostream>
#include <vector>
#include "utils.h"

int main() {
    std::vector<int> v;
    process_data(v);
    return 0;
}
""")
    
    (tmpdir / "utils.h").write_text("""
#ifndef UTILS_H
#define UTILS_H
#include <vector>

void process_data(const std::vector<int>& data);

#endif
""")
    
    (tmpdir / "utils.cpp").write_text("""
#include "utils.h"
#include <algorithm>
#include <iostream>

void process_data(const std::vector<int>& data) {
    for(int val : data) {
        std::cout << val << std::endl;
    }
}
""")
    
    yield tmpdir
    
    # Cleanup
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture(autouse=True)
def reset_benchmark_globals():
    """Reset global benchmark instance between tests."""
    from includeguard import benchmark as bm
    bm._global_benchmark = None
    yield
    bm._global_benchmark = None


@pytest.fixture(autouse=True)
def reset_formatter_globals():
    """Reset global formatter instance between tests."""
    from includeguard.ui import rich_formatter as rf
    rf._global_formatter = None
    yield
    rf._global_formatter = None


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", 
        "benchmark: mark test as a benchmark"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow"
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers",
        "edge_case: mark test as edge case"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle test markers."""
    for item in items:
        # Add markers based on test name
        if "benchmark" in item.nodeid:
            item.add_marker(pytest.mark.benchmark)
        if "slow" in item.nodeid:
            item.add_marker(pytest.mark.slow)
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        if "edge_case" in item.nodeid:
            item.add_marker(pytest.mark.edge_case)


@pytest.fixture
def mock_parser():
    """Mock parser that doesn't require real files."""
    from includeguard.analyzer.parser import FileAnalysis, Include
    
    analyses = [
        FileAnalysis(
            filepath="main.cpp",
            includes=[
                Include("<iostream>", 1, True),
                Include("<vector>", 2, True),
                Include("utils.h", 3, False),
            ],
            total_lines=50,
            code_lines=40
        ),
        FileAnalysis(
            filepath="utils.cpp",
            includes=[
                Include("utils.h", 1, False),
                Include("<algorithm>", 2, True),
            ],
            total_lines=30,
            code_lines=25
        ),
    ]
    
    class MockParser:
        def parse_project(self):
            return analyses
        
        def parse_file(self, path):
            for analysis in analyses:
                if path in analysis.filepath:
                    return analysis
            # Return default analysis if not found
            return FileAnalysis(filepath=path, includes=[], total_lines=0)
    
    return MockParser()
