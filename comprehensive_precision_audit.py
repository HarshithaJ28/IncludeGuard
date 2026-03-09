"""
COMPREHENSIVE PRECISION AUDIT - After Pattern 3 Fix
====================================================
Tests with various realistic scenarios
"""
import tempfile
from pathlib import Path
from includeguard.analyzer.parser import IncludeParser
from includeguard.analyzer.graph import DependencyGraph
from includeguard.analyzer.estimator import CostEstimator


def test_case(name, code, tests):
    """Test multiple headers in same code
    
    tests: list of (header, expected_used) tuples
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.cpp"
        file_path.write_text(code)
        
        graph = DependencyGraph()
        estimator = CostEstimator(graph)
        
        results = []
        for header, expected_used in tests:
            is_used, confidence = estimator.check_header_usage(str(file_path), header)
            is_correct = is_used == expected_used
            results.append((header, expected_used, is_used, confidence, is_correct))
        
        return results


# Comprehensive test cases
print("=== COMPREHENSIVE PRECISION AUDIT ===\n")

test_suites = [
    {
        "name": "Basic C++ with only iostream",
        "code": """
#include <iostream>
int main() { std::cout << "Hi"; }
""",
        "tests": [
            ("iostream", True),   # Used
        ]
    },
    {
        "name": "Multiple headers, only cout used",
        "code": """
#include <iostream>
#include <vector>
#include <map>
#include <queue>
int main() { std::cout << "Hi"; }
""",
        "tests": [
            ("iostream", True),   # Used (has cout)
            ("vector", False),    # Unused
            ("map", False),       # Unused
            ("queue", False),     # Unused
        ]
    },
    {
        "name": "Vector actually used",
        "code": """
#include <vector>
int main() { 
    std::vector<int> v;
    v.push_back(42);
}
""",
        "tests": [
            ("vector", True),     # Used
        ]
    },
    {
        "name": "Map actually used",
        "code": """
#include <map>
int main() {
    std::map<std::string, int> m;
    m["key"] = 42;
}
""",
        "tests": [
            ("map", True),        # Used
        ]
    },
    {
        "name": "Algorithm usage",
        "code": """
#include <algorithm>
#include <vector>
int main() {
    std::vector<int> v = {3,1,2};
    std::sort(v.begin(), v.end());
}
""",
        "tests": [
            ("algorithm", True),  # Used (std::sort)
            ("vector", True),     # Used
        ]
    },
    {
        "name": "String operations",
        "code": """
#include <string>
int main() {
    std::string s = "hello";
    s.append(" world");
}
""",
        "tests": [
            ("string", True),     # Used
        ]
    },
    {
        "name": "Regex usage",
        "code": """
#include <regex>
int main() {
    std::regex pattern("[0-9]+");
}
""",
        "tests": [
            ("regex", True),      # Used
        ]
    },
    {
        "name": "Mixed used / unused",
        "code": """
#include <iostream>
#include <regex>
#include <cmath>
#include <thread>
#include <chrono>
int main() {
    std::cout << "test";
    std::cout << std::sqrt(9.0);
}
""",
        "tests": [
            ("iostream", True),   # Used (cout)
            ("cmath", True),      # Used (sqrt)
            ("regex", False),     # Unused
            ("thread", False),    # Unused
            ("chrono", False),    # Unused
        ]
    },
    {
        "name": "Empty main - all unused",
        "code": """
#include <vector>
#include<map>
#include <set>
int main() { }
""",
        "tests": [
            ("vector", False),    # Unused
            ("map", False),       # Unused
            ("set", False),       # Unused
        ]
    },
]

total_correct = 0
total_tests = 0

for suite in test_suites:
    print(f"TEST SUITE: {suite['name']}")
    results = test_case(suite['name'], suite['code'], suite['tests'])
    
    suite_correct = 0
    for header, expected, got, conf, is_correct in results:
        status = "PASS" if is_correct else "FAIL"
        print(f"  {status}: {header} - expected={expected}, got={got}, conf={conf:.1%}")
        if is_correct:
            suite_correct += 1
            total_correct += 1
        total_tests += 1
    
    suite_precision = suite_correct / len(suite['tests']) if suite['tests'] else 0
    print(f"  Suite precision: {suite_precision:.0%}\n")

print()
print(f"=== FINAL RESULTS ===")
print(f"Correct: {total_correct}/{total_tests}")
precision = total_correct / total_tests
print(f"Precision: {precision:.1%}")
print()

if precision >= 0.75:
    print("✓ SUCCESS: Precision >= 75% target achieved")
elif precision >= 0.65:
    print("~ GOOD: Precision 65-75%, close to target")
elif precision >= 0.50:
    print("! WARNING: Precision 50-65%, below target")
else:
    print("✗ FAILURE: Precision < 50%, unacceptable")
