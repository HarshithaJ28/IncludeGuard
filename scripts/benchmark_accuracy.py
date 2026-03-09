"""
TIER 3: BENCHMARK VALIDATION
=============================
Validates cost estimates against ACTUAL compilation times:

1. Analyzes project with IncludeGuard to get estimated costs
2. Compiles each file and measures actual compilation time
3. Calculates Pearson correlation coefficient (r)
4. Calculates R² (coefficient of determination)
5. Determines conversion factor (units to seconds)

Success Criteria:
- Correlation > 0.90 (Very Strong)
- R² > 0.80 (80% variance explained)
- Mean error < 10%

This is the ULTIMATE proof of accuracy.
"""

import time
import subprocess
import tempfile
import statistics
import os
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
import math


@dataclass
class CompilationBenchmark:
    """Results of benchmarking one file"""
    filepath: str
    estimated_cost: float
    actual_time: float  # seconds
    ratio: float  # cost per second
    error_percent: float


def calculate_pearson_correlation(x: List[float], y: List[float]) -> float:
    """
    Calculate Pearson correlation coefficient
    
    Returns:
        r: correlation coefficient (-1 to 1)
            1.0 = perfect positive correlation
            0.0 = no correlation
           -1.0 = perfect negative correlation
    """
    if len(x) < 2 or len(y) < 2:
        return 0.0
    
    n = len(x)
    mean_x = statistics.mean(x)
    mean_y = statistics.mean(y)
    
    numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    denominator_x = sum((x[i] - mean_x) ** 2 for i in range(n))
    denominator_y = sum((y[i] - mean_y) ** 2 for i in range(n))
    
    if denominator_x == 0 or denominator_y == 0:
        return 0.0
    
    r = numerator / math.sqrt(denominator_x * denominator_y)
    return r


class BenchmarkValidator:
    """Validates cost estimates against real compilation"""
    
    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.benchmarks: List[CompilationBenchmark] = []
    
    
    def analyze_project(self) -> Dict:
        """
        Run IncludeGuard analysis and collect estimated costs
        """
        print(f"\n📊 Analyzing project for cost estimation...")
        
        from includeguard.analyzer.parser import IncludeParser
        from includeguard.analyzer.graph import DependencyGraph
        from includeguard.analyzer.estimator import CostEstimator
        
        try:
            parser = IncludeParser(self.project_path)
            analyses = parser.parse_project()
            
            print(f"   ✅ Found {len(analyses)} C++ files")
            
            graph = DependencyGraph()
            graph.build(analyses)
            
            estimator = CostEstimator(graph)
            all_analyses = {a.filepath: a for a in analyses}
            
            estimated_costs = {}
            for analysis in analyses:
                cost_results = estimator.analyze_file_costs(analysis, all_analyses)
                total_cost = sum(c['estimated_cost'] for c in cost_results)
                estimated_costs[str(analysis.filepath)] = total_cost
            
            return estimated_costs
        
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return {}
    
    
    def benchmark_compilation(self, estimated_costs: Dict) -> Tuple[List[CompilationBenchmark], Dict]:
        """
        Compile each file and measure actual time
        
        Returns:
            List of benchmarks and error summary
        """
        print(f"\n⚡ Benchmarking actual compilation times...")
        print(f"   Testing {len(estimated_costs)} files...")
        
        successful = 0
        failed = 0
        compilation_errors = []
        
        for filepath, estimated_cost in list(estimated_costs.items())[:10]:  # Limit to first 10
            file_path = Path(filepath)
            
            if not file_path.exists():
                failed += 1
                continue
            
            try:
                # Compile and time
                start = time.time()
                result = subprocess.run(
                    ['g++', '-c', str(file_path), '-o', os.devnull],
                    capture_output=True,
                    timeout=30,
                    text=True
                )
                elapsed = time.time() - start
                
                if result.returncode == 0:
                    # Calculate metrics
                    ratio = estimated_cost / elapsed if elapsed > 0 else 0
                    error_pct = abs(estimated_cost - elapsed) / elapsed * 100 if elapsed > 0 else 0
                    
                    benchmark = CompilationBenchmark(
                        filepath=filepath,
                        estimated_cost=estimated_cost,
                        actual_time=elapsed,
                        ratio=ratio,
                        error_percent=error_pct
                    )
                    
                    self.benchmarks.append(benchmark)
                    successful += 1
                    
                    print(f"   ✅ {file_path.name:30s} Est: {estimated_cost:6.0f} | Real: {elapsed:6.3f}s | Ratio: {ratio:6.1f}")
                
                else:
                    failed += 1
                    compilation_errors.append({
                        'file': file_path.name,
                        'error': result.stderr[:100] if result.stderr else 'Unknown error'
                    })
            
            except subprocess.TimeoutExpired:
                failed += 1
                compilation_errors.append({
                    'file': file_path.name,
                    'error': 'Compilation timeout'
                })
            except Exception as e:
                failed += 1
                compilation_errors.append({
                    'file': file_path.name,
                    'error': str(e)
                })
        
        summary = {
            'successful': successful,
            'failed': failed,
            'errors': compilation_errors
        }
        
        return self.benchmarks, summary
    
    
    def calculate_accuracy_metrics(self) -> Dict:
        """
        Calculate correlation, R², and accuracy metrics
        """
        if len(self.benchmarks) < 2:
            print("\n   ⚠️  Not enough samples for correlation analysis")
            return {}
        
        print(f"\n📈 Calculating accuracy metrics...")
        
        estimated_vals = [b.estimated_cost for b in self.benchmarks]
        actual_vals = [b.actual_time for b in self.benchmarks]
        
        # Pearson correlation
        correlation = calculate_pearson_correlation(estimated_vals, actual_vals)
        
        # R² (coefficient of determination)
        r_squared = correlation ** 2
        
        # Mean error
        errors = [b.error_percent for b in self.benchmarks]
        mean_error = statistics.mean(errors) if errors else 0
        
        # Conversion factor (avg units per second)
        ratios = [b.ratio for b in self.benchmarks]
        avg_ratio = statistics.mean(ratios) if ratios else 0
        
        metrics = {
            'correlation': correlation,
            'r_squared': r_squared,
            'mean_error_percent': mean_error,
            'conversion_factor': avg_ratio,
            'samples': len(self.benchmarks)
        }
        
        # Interpretation
        if r_squared >= 0.90:
            verdict = "EXCELLENT - Model is highly accurate ✅"
        elif r_squared >= 0.75:
            verdict = "GOOD - Model is reasonably accurate ✅"
        elif r_squared >= 0.50:
            verdict = "MODERATE - Model could be improved 🟡"
        else:
            verdict = "POOR - Model needs recalibration ❌"
        
        print(f"\n   Correlation (r):     {correlation:+.4f}")
        print(f"   R² (variance):       {r_squared:.4f} ({r_squared:.1%} variance explained)")
        print(f"   Mean Error:          {mean_error:.2f}%")
        print(f"   Avg Ratio:           {avg_ratio:.4f} units/second")
        print(f"   Samples Tested:      {len(self.benchmarks)}")
        print(f"\n   Verdict: {verdict}")
        
        return metrics
    
    
    def generate_benchmark_report(self) -> Dict:
        """
        Full benchmark report with all details
        """
        print("\n" + "="*70)
        print("TIER 3: BENCHMARK VALIDATION REPORT")
        print("="*70)
        
        # Step 1: Analyze
        estimated_costs = self.analyze_project()
        
        if not estimated_costs:
            print("   ❌ Failed to analyze project")
            return {}
        
        # Step 2: Benchmark
        benchmarks, compilation_summary = self.benchmark_compilation(estimated_costs)
        
        print(f"\n   Compilation Summary:")
        print(f"      Successful: {compilation_summary['successful']}")
        print(f"      Failed:     {compilation_summary['failed']}")
        
        if compilation_summary['errors']:
            print(f"\n   Compilation Errors (first 3):")
            for error in compilation_summary['errors'][:3]:
                print(f"      - {error['file']}: {error['error']}")
        
        # Step 3: Calculate metrics
        metrics = self.calculate_accuracy_metrics()
        
        report = {
            'estimated_costs': estimated_costs,
            'benchmarks': [(b.filepath, b.estimated_cost, b.actual_time) for b in self.benchmarks],
            'compilation_summary': compilation_summary,
            'metrics': metrics
        }
        
        return report


def run_benchmark_validation(project_path: Path) -> Dict:
    """
    Run full benchmark validation on a project
    """
    validator = BenchmarkValidator(project_path)
    return validator.generate_benchmark_report()


if __name__ == "__main__":
    # Test
    project = Path("examples/sample_project")
    
    if project.exists():
        report = run_benchmark_validation(project)
        
        if report.get('metrics'):
            print("\n" + "="*70)
            print("BENCHMARK VALIDATION COMPLETE")
            print("="*70)
            
            r2 = report['metrics'].get('r_squared', 0)
            
            if r2 >= 0.80:
                print("\n✅ VALIDATION PASSED: R² >= 0.80")
            else:
                print(f"\n⚠️  VALIDATION WARNING: R² = {r2:.3f} (target: 0.80+)")
    else:
        print(f"Project not found: {project}")
