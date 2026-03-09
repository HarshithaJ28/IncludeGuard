"""
TIER 2: REAL PROJECT VALIDATION
================================
Validates accuracy on real open-source projects through:
1. Analyzing directories with IncludeGuard
2. Manually spot-checking 10 findings per project
3. Calculating precision metrics
4. Compile tests (remove headers, verify compilation)

Success Criteria:
- Precision > 80% on manual checks
- Zero false positives on obvious cases (std::cout, std::vector, etc.)
- Successful compilation when removing unused headers
"""

import json
import subprocess
import tempfile
import os
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict


@dataclass
class Finding:
    """A finding: file has unused header"""
    file: str
    header: str
    line_number: int
    confidence: float = 0.0


@dataclass
class ValidationResult:
    """Result of validating one finding"""
    finding: Finding
    is_true_positive: bool = False  # True = header IS unused
    is_false_positive: bool = False  # True = header IS used
    is_uncertain: bool = False  # Can't determine
    reason: str = ""


class RealProjectValidator:
    """Validates IncludeGuard on real projects"""
    
    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.findings: List[Finding] = []
        self.validations: List[ValidationResult] = []
    
    
    def analyze_project(self) -> Dict:
        """
        Run IncludeGuard analysis on project and extract ACTUAL unused findings
        
        Returns summary of findings identified by IncludeGuard as unused
        """
        print(f"\n[ANALYZING] Project: {self.project_path.name}")
        print(f"   Path: {self.project_path}")
        
        from includeguard.analyzer.parser import IncludeParser
        from includeguard.analyzer.graph import DependencyGraph
        from includeguard.analyzer.estimator import CostEstimator
        
        try:
            # Parse
            parser = IncludeParser(self.project_path)
            analyses = parser.parse_project()
            
            print(f"   [OK] Found {len(analyses)} C++ files")
            
            # Build graph
            graph = DependencyGraph()
            graph.build(analyses)
            
            # Estimate costs
            estimator = CostEstimator(graph)
            all_analyses = {a.filepath: a for a in analyses}
            
            findings_count = 0
            
            # *** CRITICAL FIX: Only collect headers that IncludeGuard identifies as UNUSED ***
            for analysis in analyses:
                # Get cost analysis for this file
                cost_results = estimator.analyze_file_costs(analysis, all_analyses)
                
                # Filter for UNUSED headers (likely_used == False)
                for cost_info in cost_results:
                    # Only include if IncludeGuard says it's unused
                    if not cost_info['likely_used']:
                        finding = Finding(
                            file=str(analysis.filepath),
                            header=cost_info['header'],
                            line_number=cost_info.get('line', 0),
                            confidence=cost_info.get('usage_confidence', 0)
                        )
                        self.findings.append(finding)
                        findings_count += 1
            
            return {
                'files_analyzed': len(analyses),
                'unused_headers_found': findings_count,
                'status': 'success'
            }
        
        except Exception as e:
            print(f"   ❌ Error analyzing project: {e}")
            import traceback
            traceback.print_exc()
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    
    def manually_verify_finding(self, finding: Finding) -> ValidationResult:
        """
        Manually verify if a finding is correct
        
        Checks:
        1. Is header name mentioned in code?
        2. Are common symbols used (cout, vector, etc.)?
        3. Try compiling without header
        """
        file_path = Path(finding.file)
        
        if not file_path.exists():
            return ValidationResult(
                finding=finding,
                is_uncertain=True,
                reason="File not found"
            )
        
        try:
            content = file_path.read_text(errors='ignore')
            
            # Check 1: Known symbol patterns
            header_lower = finding.header.lower().replace('<', '').replace('>', '')
            
            symbol_checks = {
                'iostream': ['cout', 'cin', 'cerr', 'endl'],
                'vector': ['vector<'],
                'string': ['string '],
                'map': ['map<'],
                'set': ['set<'],
                'algorithm': ['sort', 'find', 'transform'],
                'memory': ['unique_ptr', 'shared_ptr', 'make_unique'],
                'stdexcept': ['exception', 'runtime_error'],
            }
            
            if header_lower in symbol_checks:
                symbols = symbol_checks[header_lower]
                if any(sym in content for sym in symbols):
                    return ValidationResult(
                        finding=finding,
                        is_true_positive=False,
                        is_false_positive=True,
                        reason=f"Symbol '{symbols[0]}' found in code"
                    )
            
            # Check 2: Try removing include and compile
            lines = content.split('\n')
            test_lines = []
            include_removed = False
            
            for i, line in enumerate(lines):
                # Check both <> and "" formats
                if f'#include <{finding.header}>' in line or \
                   f'#include "{finding.header}"' in line or \
                   f'#include <{finding.header}' in line:  # Partial match for edge cases
                    # Skip this line
                    include_removed = True
                    continue
                test_lines.append(line)
            
            if not include_removed:
                return ValidationResult(
                    finding=finding,
                    is_uncertain=True,
                    reason="Could not find include to remove"
                )
            
            # Write test file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
                f.write('\n'.join(test_lines))
                test_file = f.name
            
            try:
                # Try to compile
                result = subprocess.run(
                    ['g++', '-c', test_file, '-o', os.devnull],
                    capture_output=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    # Compiles without header - TRUE POSITIVE
                    return ValidationResult(
                        finding=finding,
                        is_true_positive=True,
                        reason="Compiles successfully without header"
                    )
                else:
                    # Doesn't compile - FALSE POSITIVE
                    return ValidationResult(
                        finding=finding,
                        is_false_positive=True,
                        reason=f"Compilation fails without header"
                    )
            
            finally:
                Path(test_file).unlink(missing_ok=True)
        
        except Exception as e:
            return ValidationResult(
                finding=finding,
                is_uncertain=True,
                reason=f"Verification error: {str(e)}"
            )
    
    
    def validate_sample(self, sample_size: int = 10) -> Dict:
        """
        Validate a random sample of findings
        
        Returns precision/recall metrics
        """
        import random
        
        if not self.findings:
            print("   ⚠️  No findings to validate")
            return {}
        
        sample = random.sample(
            self.findings,
            min(sample_size, len(self.findings))
        )
        
        print(f"\n[VALIDATING] Sample of {len(sample)} findings...")
        
        for i, finding in enumerate(sample, 1):
            print(f"\n   [{i}/{len(sample)}] Checking {Path(finding.file).name}:{finding.line_number}")
            print(f"      Header: {finding.header}")
            
            result = self.manually_verify_finding(finding)
            self.validations.append(result)
            
            if result.is_true_positive:
                print(f"      [TRUE] {result.reason}")
            elif result.is_false_positive:
                print(f"      [FALSE] {result.reason}")
            else:
                print(f"      ⚠️  UNCERTAIN: {result.reason}")
        
        # Calculate metrics
        true_positives = sum(1 for v in self.validations if v.is_true_positive)
        false_positives = sum(1 for v in self.validations if v.is_false_positive)
        uncertain = sum(1 for v in self.validations if v.is_uncertain)
        
        precision = true_positives / (true_positives + false_positives) \
            if (true_positives + false_positives) > 0 else 0
        
        recall = true_positives / len(self.validations) if self.validations else 0
        
        metrics = {
            'sample_size': len(sample),
            'true_positives': true_positives,
            'false_positives': false_positives,
            'uncertain': uncertain,
            'precision': precision,
            'recall': recall
        }
        
        print(f"\n[METRICS]")
        print(f"   Precision: {precision:.1%}")
        print(f"   True Positives: {true_positives}")
        print(f"   False Positives: {false_positives}")
        print(f"   Uncertain: {uncertain}")
        
        return metrics
    
    
    def compile_test_validation(self) -> Tuple[int, int, int]:
        """
        Remove all "unused" headers and try compiling
        Ultimate validation: Does code compile without these headers?
        
        Returns:
            (successful_removals, failed_removals, error_count)
        """
        print(f"\n[COMPILE TESTS]")
        
        successful = 0
        failed = 0
        errors = 0
        
        # Group findings by file
        findings_by_file = {}
        for finding in self.findings:
            if finding.file not in findings_by_file:
                findings_by_file[finding.file] = []
            findings_by_file[finding.file].append(finding)
        
        for file_path, file_findings in list(findings_by_file.items())[:5]:  # Test first 5 files
            try:
                file_path_obj = Path(file_path)
                if not file_path_obj.exists():
                    continue
                
                content = file_path_obj.read_text(errors='ignore')
                lines = content.split('\n')
                
                # Remove all found headers
                test_lines = []
                for line in lines:
                    skip = False
                    for finding in file_findings:
                        if f'#include <{finding.header}>' in line or \
                           f'#include "{finding.header}"' in line or \
                           f'#include <{finding.header}' in line:
                            skip = True
                            break
                    if not skip:
                        test_lines.append(line)
                
                # Try to compile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
                    f.write('\n'.join(test_lines))
                    test_file = f.name
                
                try:
                    result = subprocess.run(
                        ['g++', '-c', test_file, '-o', os.devnull],
                        capture_output=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        print(f"   [OK] {Path(file_path).name}: Compiles without headers")
                        successful += 1
                    else:
                        print(f"   [FAIL] {Path(file_path).name}: Compilation failed")
                        failed += 1
                
                finally:
                    Path(test_file).unlink(missing_ok=True)
            
            except Exception as e:
                print(f"   [WARN] {Path(file_path).name}: Error - {str(e)}")
                errors += 1
        
        return successful, failed, errors


def validate_multiple_projects(project_paths: List[Path]) -> Dict:
    """
    Validate IncludeGuard on multiple real projects
    """
    
    print("="*70)
    print("TIER 2: REAL PROJECT VALIDATION")
    print("="*70)
    
    results = {}
    
    for project_path in project_paths:
        if not project_path.exists():
            print(f"\n⚠️  Project not found: {project_path}")
            continue
        
        validator = RealProjectValidator(project_path)
        
        # 1. Analyze
        analysis_result = validator.analyze_project()
        
        if analysis_result['status'] != 'success':
            print(f"   ❌ Analysis failed")
            continue
        
        # 2. Validate sample
        metrics = validator.validate_sample(sample_size=10)
        
        # 3. Compile tests
        successful, failed, errors = validator.compile_test_validation()
        
        results[project_path.name] = {
            'analysis': analysis_result,
            'metrics': metrics,
            'compile_tests': {
                'successful': successful,
                'failed': failed,
                'errors': errors
            }
        }
    
    # Summary
    print("\n" + "="*70)
    print("TIER 2 SUMMARY")
    print("="*70)
    
    if results:
        avg_precision = sum(r['metrics'].get('precision', 0) 
                          for r in results.values()) / len(results)
        print(f"\nAverage Precision: {avg_precision:.1%}")
        print(f"Projects Tested: {len(results)}")
        
        compile_success = sum(r['compile_tests']['successful'] 
                            for r in results.values())
        compile_failed = sum(r['compile_tests']['failed'] 
                           for r in results.values())
        
        if compile_success + compile_failed > 0:
            success_rate = compile_success / (compile_success + compile_failed)
            print(f"Compile Test Success Rate: {success_rate:.1%}")
    
    return results


if __name__ == "__main__":
    # Example projects to test
    sample_projects = [
        Path("examples/sample_project"),
    ]
    
    validate_multiple_projects(sample_projects)
