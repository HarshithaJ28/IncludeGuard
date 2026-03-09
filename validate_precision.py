"""
BRUTAL PRECISION AUDIT - What's the REAL accuracy?
===================================================
"""
import tempfile
from pathlib import Path
from includeguard.analyzer.parser import IncludeParser
from includeguard.analyzer.graph import DependencyGraph
from includeguard.analyzer.estimator import CostEstimator


def test_case(name, code, header, expected_used):
    """Test a single case and return if it's correct"""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.cpp"
        file_path.write_text(code)
        
        parser = IncludeParser(Path(tmpdir))
        analysis = parser.parse_file(file_path)
        
        graph = DependencyGraph()
        estimator = CostEstimator(graph)
        is_used, confidence = estimator.check_header_usage(str(file_path), header)
        
        is_correct = is_used == expected_used
        status = "PASS" if is_correct else "FAIL"
        
        print(f"{status}: {name}")
        print(f"  Expected: used={expected_used}, Got: used={is_used}, confidence={confidence:.1%}")
        
        return is_correct


# Test ground truth cases
test_cases = [
    # SHOULD BE USED (correct detection is priority)
    ("vector usage", "#include <vector>\nstd::vector<int> v;", "vector", True),
    ("iostream cout", "#include <iostream>\nstd::cout << 1;", "iostream", True),
    ("algorithm sort", "#include <algorithm>\nstd::sort(a, b);", "algorithm", True),
    ("string usage", "#include <string>\nstd::string s;", "string", True),
    
    # SHOULD BE UNUSED (but conservative approach might miss)
    ("unused map", "#include <map>\nint x = 0;", "map", False),
    ("unused queue", "#include <queue>\nint x = 0;", "queue", False),
    ("unused set", "#include <set>\nint x = 0;", "set", False),
    ("unused stack", "#include <stack>\nint x = 0;", "stack", False),
    
    # EDGE CASES  
    ("iostream unused", "#include <iostream>\nint x = 0;", "iostream", False),
    ("algorithm unused", "#include <algorithm>\nint x = 0;", "algorithm", False),
    ("boost included but unused", "#include <boost/algorithm/string.hpp>\nint x = 0;", "boost/algorithm/string.hpp", False),
]

correct = 0
for name, code, header, expected in test_cases:
    if test_case(name, code, header, expected):
        correct += 1
    print()

print(f"\n=== RESULTS ===")
print(f"Correct: {correct}/{len(test_cases)}")
precision = correct / len(test_cases)
print(f"Precision: {precision:.1%}")
print()

if precision < 0.50:
    print("❌ CRITICAL: Precision is BELOW 50%!")
    print("The algorithm is WORSE than original 33%")
elif precision < 0.75:
    print("⚠️  WARNING: Precision is below 75% target")
    print("Need significant improvements")
else:
    print("✅ GOAL MET: 75%+ precision achieved")
