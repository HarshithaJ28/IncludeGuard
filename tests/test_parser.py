"""Test the include parser"""
from pathlib import Path
from includeguard.analyzer.parser import IncludeParser
import tempfile

def test_basic_parsing():
    # Create a temporary C++ file
    test_code = """
#include <iostream>
#include <vector>
#include "MyClass.h"

// This is a comment
int main() {
    std::cout << "Hello" << std::endl;
    return 0;
}
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
        f.write(test_code)
        temp_path = Path(f.name)
    
    try:
        parser = IncludeParser(temp_path.parent)
        analysis = parser.parse_file(temp_path)
        
        assert analysis is not None
        assert len(analysis.includes) == 3
        assert analysis.includes[0].header == 'iostream'
        assert analysis.includes[0].is_system == True
        assert analysis.includes[2].header == 'MyClass.h'
        assert analysis.includes[2].is_system == False
        
        print("✓ Parser test passed!")
        print(f"  Found {len(analysis.includes)} includes")
        print(f"  Total lines: {analysis.total_lines}")
        print(f"  Code lines: {analysis.code_lines}")
        
    finally:
        temp_path.unlink()

if __name__ == '__main__':
    test_basic_parsing()
