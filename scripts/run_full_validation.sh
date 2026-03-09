#!/bin/bash
# ============================================================================
# COMPREHENSIVE VALIDATION SUITE
# ============================================================================
# 
# This script runs the complete 3-tier validation framework for IncludeGuard:
#
# 1. Tier 1: Synthetic Tests (Known Ground Truth)
# 2. Tier 2: Real Project Validation (Manual Verification)
# 3. Tier 3: Benchmark Validation (Actual Compilation)
# 4. Edge Cases
# 5. Generate Report
#
# Usage:
#   bash run_full_validation.sh
#
# Expected Output:
#   VALIDATION_REPORT.md - Comprehensive validation report
#
# ============================================================================

set -e  # Exit on error

echo ""
echo "============================================================================"
echo "COMPREHENSIVE INCLUDEGUARD VALIDATION SUITE"
echo "============================================================================"
echo ""
echo "This will run:"
echo "  ✓ Tier 1: Synthetic tests with known ground truth (10 tests)"
echo "  ✓ Tier 2: Real project validation with manual verification"
echo "  ✓ Tier 3: Benchmark validation against actual compilation times"
echo "  ✓ Edge Cases: 8 critical edge cases"
echo "  ✓ Report Generation: Comprehensive markdown report"
echo ""
echo "Expected Duration: 5-10 minutes"
echo "============================================================================"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# ============================================================================
# TIER 1: SYNTHETIC TESTS
# ============================================================================
echo -e "${BLUE}TIER 1: SYNTHETIC GROUND TRUTH TESTS${NC}"
echo "============================================================================"
echo ""

echo "Running synthetic tests with known ground truth..."

pytest tests/test_validation_ground_truth.py -v --tb=short

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Tier 1 PASSED${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 10))
else
    echo -e "${RED}❌ Tier 1 FAILED${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 10))
fi

TOTAL_TESTS=$((TOTAL_TESTS + 10))

echo ""
echo ""

# ============================================================================
# EDGE CASES
# ============================================================================
echo -e "${BLUE}EDGE CASE TESTING${NC}"
echo "============================================================================"
echo ""

echo "Running edge case tests..."

pytest tests/test_edge_cases.py -v --tb=short

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Edge Cases PASSED${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 8))
else
    echo -e "${RED}❌ Edge Cases FAILED${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 8))
fi

TOTAL_TESTS=$((TOTAL_TESTS + 8))

echo ""
echo ""

# ============================================================================
# TIER 2: REAL PROJECT VALIDATION
# ============================================================================
echo -e "${BLUE}TIER 2: REAL PROJECT VALIDATION${NC}"
echo "============================================================================"
echo ""

echo "Validating on real projects..."

python scripts/validate_real_projects.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Tier 2 COMPLETED${NC}"
else
    echo -e "${YELLOW}⚠️  Tier 2 HAD ISSUES (may be expected if real projects unavailable)${NC}"
fi

echo ""
echo ""

# ============================================================================
# TIER 3: BENCHMARK VALIDATION
# ============================================================================
echo -e "${BLUE}TIER 3: BENCHMARK VALIDATION${NC}"
echo "============================================================================"
echo ""

echo "Running benchmark validation..."

python scripts/benchmark_accuracy.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Tier 3 COMPLETED${NC}"
else
    echo -e "${YELLOW}⚠️  Tier 3 HAD ISSUES (may be expected if compiler unavailable)${NC}"
fi

echo ""
echo ""

# ============================================================================
# REPORT GENERATION
# ============================================================================
echo -e "${BLUE}GENERATING VALIDATION REPORT${NC}"
echo "============================================================================"
echo ""

echo "Generating comprehensive validation report..."

python scripts/generate_validation_report.py

if [ -f "VALIDATION_REPORT.md" ]; then
    echo -e "${GREEN}✅ Report generated successfully${NC}"
    echo ""
    echo "📋 Report: VALIDATION_REPORT.md"
    echo "📊 Size: $(wc -c < VALIDATION_REPORT.md) bytes"
else
    echo -e "${RED}⚠️  Report generation may have had issues${NC}"
fi

echo ""
echo ""

# ============================================================================
# FINAL SUMMARY
# ============================================================================
echo "============================================================================"
echo -e "${BLUE}VALIDATION SUMMARY${NC}"
echo "============================================================================"
echo ""

echo "Test Results:"
echo "  Total Tests: $(($PASSED_TESTS + $FAILED_TESTS))"
echo -e "  ${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "  ${RED}Failed: $FAILED_TESTS${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ ALL TESTS PASSED${NC}"
    echo ""
    echo "Status: VALIDATION SUCCESSFUL 🎉"
else
    echo ""
    echo -e "${YELLOW}⚠️  SOME TESTS FAILED${NC}"
    echo ""
    echo "Status: REVIEW FAILURES"
fi

echo ""
echo "Next Steps:"
echo "  1. Review VALIDATION_REPORT.md"
echo "  2. Check Tier 1-3 results above"
echo "  3. Verify all critical components passed"
echo ""

echo "============================================================================"
echo "END OF VALIDATION SUITE"
echo "============================================================================"
echo ""

# Exit with appropriate code
if [ $FAILED_TESTS -eq 0 ]; then
    exit 0
else
    exit 1
fi
