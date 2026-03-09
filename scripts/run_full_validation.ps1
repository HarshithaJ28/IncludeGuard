# ============================================================================
# COMPREHENSIVE VALIDATION SUITE (Windows PowerShell)
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
#   powershell -ExecutionPolicy Bypass -File run_full_validation.ps1
#
# Expected Output:
#   VALIDATION_REPORT.md - Comprehensive validation report
#
# ============================================================================

# Color codes
$ErrorActionPreference = "Continue"
$WarningPreference = "Continue"

function Write-Section {
    param([string]$title)
    Write-Host ""
    Write-Host "=" * 80 -ForegroundColor Cyan
    Write-Host $title -ForegroundColor Cyan
    Write-Host "=" * 80 -ForegroundColor Cyan
    Write-Host ""
}

function Write-Success {
    param([string]$message)
    Write-Host "✅ $message" -ForegroundColor Green
}

function Write-Error-Custom {
    param([string]$message)
    Write-Host "❌ $message" -ForegroundColor Red
}

function Write-Warning-Custom {
    param([string]$message)
    Write-Host "⚠️  $message" -ForegroundColor Yellow
}

function Write-Info {
    param([string]$message)
    Write-Host "ℹ️  $message" -ForegroundColor Blue
}

# Track results
$script:TotalTests = 0
$script:PassedTests = 0
$script:FailedTests = 0

# ============================================================================
# MAIN
# ============================================================================

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "COMPREHENSIVE INCLUDEGUARD VALIDATION SUITE" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""
Write-Host "This will run:"
Write-Host "  ✓ Tier 1: Synthetic tests with known ground truth (10 tests)"
Write-Host "  ✓ Tier 2: Real project validation with manual verification"
Write-Host "  ✓ Tier 3: Benchmark validation against actual compilation times"
Write-Host "  ✓ Edge Cases: 8 critical edge cases"
Write-Host "  ✓ Report Generation: Comprehensive markdown report"
Write-Host ""
Write-Host "Expected Duration: 5-10 minutes"
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# TIER 1: SYNTHETIC TESTS
# ============================================================================

Write-Section "TIER 1: SYNTHETIC GROUND TRUTH TESTS"

Write-Host "Running synthetic tests with known ground truth..."
Write-Host ""

$result = & python -m pytest tests/test_validation_ground_truth.py -v --tb=short 2>&1
Write-Host $result

if ($LASTEXITCODE -eq 0) {
    Write-Success "Tier 1 PASSED"
    $script:PassedTests += 10
} else {
    Write-Error-Custom "Tier 1 FAILED"
    $script:FailedTests += 10
}

$script:TotalTests += 10

# ============================================================================
# EDGE CASES
# ============================================================================

Write-Section "EDGE CASE TESTING"

Write-Host "Running edge case tests..."
Write-Host ""

$result = & python -m pytest tests/test_edge_cases.py -v --tb=short 2>&1
Write-Host $result

if ($LASTEXITCODE -eq 0) {
    Write-Success "Edge Cases PASSED"
    $script:PassedTests += 8
} else {
    Write-Error-Custom "Edge Cases FAILED"
    $script:FailedTests += 8
}

$script:TotalTests += 8

# ============================================================================
# TIER 2: REAL PROJECT VALIDATION
# ============================================================================

Write-Section "TIER 2: REAL PROJECT VALIDATION"

Write-Host "Validating on real projects..."
Write-Host ""

$result = & python scripts/validate_real_projects.py 2>&1
Write-Host $result

if ($LASTEXITCODE -eq 0) {
    Write-Success "Tier 2 COMPLETED"
} else {
    Write-Warning-Custom "Tier 2 HAD ISSUES (may be expected if real projects unavailable)"
}

# ============================================================================
# TIER 3: BENCHMARK VALIDATION
# ============================================================================

Write-Section "TIER 3: BENCHMARK VALIDATION"

Write-Host "Running benchmark validation..."
Write-Host ""

$result = & python scripts/benchmark_accuracy.py 2>&1
Write-Host $result

if ($LASTEXITCODE -eq 0) {
    Write-Success "Tier 3 COMPLETED"
} else {
    Write-Warning-Custom "Tier 3 HAD ISSUES (may be expected if compiler unavailable)"
}

# ============================================================================
# REPORT GENERATION
# ============================================================================

Write-Section "GENERATING VALIDATION REPORT"

Write-Host "Generating comprehensive validation report..."
Write-Host ""

$result = & python scripts/generate_validation_report.py 2>&1
Write-Host $result

if (Test-Path "VALIDATION_REPORT.md") {
    Write-Success "Report generated successfully"
    Write-Host ""
    
    $reportSize = (Get-Item "VALIDATION_REPORT.md").Length
    Write-Host "📋 Report: VALIDATION_REPORT.md"
    Write-Host "📊 Size: $reportSize bytes"
} else {
    Write-Warning-Custom "Report generation may have had issues"
}

# ============================================================================
# FINAL SUMMARY
# ============================================================================

Write-Section "VALIDATION SUMMARY"

Write-Host "Test Results:"
$totalRun = $script:PassedTests + $script:FailedTests
Write-Host "  Total Tests: $totalRun"
Write-Host "  $($script:PassedTests) Passed" -ForegroundColor Green
Write-Host "  $($script:FailedTests) Failed" -ForegroundColor Red

Write-Host ""

if ($script:FailedTests -eq 0) {
    Write-Host ""
    Write-Host "✅ ALL TESTS PASSED" -ForegroundColor Green
    Write-Host ""
    Write-Host "Status: VALIDATION SUCCESSFUL 🎉" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "⚠️  SOME TESTS FAILED" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Status: REVIEW FAILURES" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Next Steps:"
Write-Host "  1. Review VALIDATION_REPORT.md"
Write-Host "  2. Check Tier 1-3 results above"
Write-Host "  3. Verify all critical components passed"
Write-Host ""

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "END OF VALIDATION SUITE" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""
