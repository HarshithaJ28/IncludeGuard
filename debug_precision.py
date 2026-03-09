"""
Debug: Why is precision different with longer code?
"""
import tempfile
from pathlib import Path
from includeguard.analyzer.parser import IncludeParser
from includeguard.analyzer.graph import DependencyGraph
from includeguard.analyzer.estimator import CostEstimator

# Test 1: Short code
print("=== TEST 1: Short code ===")
code_short = "#include <map>\nint x = 0;"
with tempfile.TemporaryDirectory() as tmpdir:
    file_path = Path(tmpdir) / "test.cpp"
    file_path.write_text(code_short)
    
    graph = DependencyGraph()
    estimator = CostEstimator(graph)
    is_used, conf = estimator.check_header_usage(str(file_path), "map")
    print(f"Short code: map used={is_used}, confidence={conf:.1%}")

# Test 2: Longer code with main()
print("\n=== TEST 2: Longer code with main() ===")
code_long = """
#include <iostream>
#include <map>
#include <queue>

int main() {
    std::cout << "Hello";
    return 0;
}
"""
with tempfile.TemporaryDirectory() as tmpdir:
    file_path = Path(tmpdir) / "test.cpp"
    file_path.write_text(code_long)
    
    graph = DependencyGraph()
    estimator = CostEstimator(graph)
    
    # Check each header
    for header in ["iostream", "map", "queue"]:
        is_used, conf = estimator.check_header_usage(str(file_path), header)
        print(f"Longer code: {header} used={is_used}, confidence={conf:.1%}")

# Test 3: Check what patterns match in longer code
print("\n=== TEST 3: Pattern analysis in longer code ===")
with tempfile.TemporaryDirectory() as tmpdir:
    file_path = Path(tmpdir) / "test.cpp"
    file_path.write_text(code_long)
    
    content = file_path.read_text()
    
    # For each header, check the 3 patterns
    for header in ["iostream", "map", "queue"]:
        import re
        from pathlib import Path as PathLib
        
        base_name = PathLib(header).stem
        print(f"\nHeader: {header} (base: {base_name})")
        
        # Pattern 1: Direct name usage
        p1 = bool(re.search(rf'\b{re.escape(base_name)}\b', content, re.IGNORECASE))
        print(f"  Pattern 1 (direct name '{base_name}'): {p1}")
        
        # Pattern 2: Symbol usage (would need the dict, skip)
        print(f"  Pattern 2 (symbol usage): <would need symbol dict>")
        
        # Pattern 3: std:: usage
        p3 = bool(re.search(r'\bstd::\w+', content))
        print(f"  Pattern 3 (std:: usage): {p3}")
