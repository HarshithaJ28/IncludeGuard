"""
Run all comprehensive tests and generate summary
"""
import subprocess
import sys

def run_test_suite(test_file, name):
    """Run a test file and return results"""
    print(f"\n{'='*70}")
    print(f"Running {name}")
    print('='*70)
    
    cmd = [
        sys.executable,
        '-m', 'pytest',
        test_file,
        '-v',
        '--tb=short',
        '-x'  # Stop on first failure for debugging
    ]
    
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0

def main():
    """Run all test suites"""
    results = {}
    
    test_suites = [
        ('tests/test_parser_comprehensive.py', 'Parser Tests'),
        ('tests/test_graph_comprehensive.py', 'Graph Tests'),
        ('tests/test_estimator_comprehensive.py', 'Estimator Tests'),
    ]
    
    for test_file, name in test_suites:
        results[name] = run_test_suite(test_file, name)
    
    # Summary
    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print('='*70)
    
    total = len(results)
    passed = sum(1 for r in results.values() if r)
    
    for name, passed_flag in results.items():
        status = "✅ PASSED" if passed_flag else "❌ FAILED"
        print(f"{name:40} {status}")
    
    print(f"\nOverall: {passed}/{total} test suites passed")
    
    return 0 if all(results.values()) else 1

if __name__ == '__main__':
    sys.exit(main())
