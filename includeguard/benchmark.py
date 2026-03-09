"""
Performance benchmarking and profiling utilities.

Tracks analysis performance metrics and helps identify bottlenecks.
"""
import time
import statistics
import json
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    operation: str
    duration_ms: float
    iterations: int = 1
    min_ms: float = None
    max_ms: float = None
    mean_ms: float = None
    median_ms: float = None
    stdev_ms: float = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class Timer:
    """Context manager for measuring execution time."""
    
    def __init__(self, name: str = None):
        """
        Initialize timer.
        
        Args:
            name: Operation name for logging
        """
        self.name = name or "Operation"
        self.start_time = None
        self.end_time = None
        self.duration_ms = None
    
    def __enter__(self):
        """Start timer."""
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        """Stop timer."""
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000
    
    def __str__(self) -> str:
        """Return formatted duration."""
        if self.duration_ms is None:
            return f"{self.name}: Not completed"
        return f"{self.name}: {self.duration_ms:.2f}ms"
    
    def get_duration_seconds(self) -> float:
        """Get duration in seconds."""
        return self.duration_ms / 1000 if self.duration_ms else None


class Benchmark:
    """Benchmark suite for IncludeGuard operations."""
    
    def __init__(self, verbose: bool = False):
        """
        Initialize benchmark suite.
        
        Args:
            verbose: Print timing info to stdout
        """
        self.verbose = verbose
        self.results: List[BenchmarkResult] = []
        self._start_time = None
        self._total_duration_ms = None
    
    def start(self):
        """Start overall benchmark session."""
        self._start_time = time.perf_counter()
    
    def end(self):
        """End overall benchmark session."""
        if self._start_time:
            self._total_duration_ms = (time.perf_counter() - self._start_time) * 1000
    
    def add_result(self, result: BenchmarkResult):
        """Add benchmark result."""
        self.results.append(result)
        if self.verbose:
            print(f"✓ {result.operation}: {result.duration_ms:.2f}ms")
    
    def measure(self, operation: str, func: Callable, *args, **kwargs) -> Any:
        """
        Measure function execution time.
        
        Args:
            operation: Operation name
            func: Function to measure
            *args: Arguments to pass to func
            **kwargs: Keyword arguments to pass to func
            
        Returns:
            Result of func()
        """
        with Timer(operation) as timer:
            result = func(*args, **kwargs)
        
        self.add_result(BenchmarkResult(
            operation=operation,
            duration_ms=timer.duration_ms
        ))
        
        return result
    
    def measure_repeated(self, 
                        operation: str, 
                        func: Callable, 
                        iterations: int = 5,
                        *args, 
                        **kwargs) -> Any:
        """
        Measure function over multiple iterations.
        
        Args:
            operation: Operation name
            func: Function to measure
            iterations: Number of iterations
            *args: Arguments to func
            **kwargs: Keyword arguments to func
            
        Returns:
            Result of last iteration
        """
        durations_ms = []
        result = None
        
        for i in range(iterations):
            with Timer() as timer:
                result = func(*args, **kwargs)
            durations_ms.append(timer.duration_ms)
        
        # Calculate statistics
        result_obj = BenchmarkResult(
            operation=operation,
            duration_ms=statistics.mean(durations_ms),
            iterations=iterations,
            min_ms=min(durations_ms),
            max_ms=max(durations_ms),
            mean_ms=statistics.mean(durations_ms),
            median_ms=statistics.median(durations_ms),
            stdev_ms=statistics.stdev(durations_ms) if iterations > 1 else 0.0
        )
        
        self.add_result(result_obj)
        return result
    
    def get_summary(self) -> Dict:
        """Get benchmark summary statistics."""
        if not self.results:
            return {}
        
        durations = [r.duration_ms for r in self.results]
        
        return {
            'total_operations': len(self.results),
            'total_time_ms': sum(durations),
            'total_time_seconds': sum(durations) / 1000,
            'mean_duration_ms': statistics.mean(durations),
            'median_duration_ms': statistics.median(durations),
            'min_duration_ms': min(durations),
            'max_duration_ms': max(durations),
            'benchmark_session_time_ms': self._total_duration_ms,
        }
    
    def print_summary(self):
        """Print benchmarks summary."""
        summary = self.get_summary()
        
        if not summary:
            print("No benchmark results")
            return
        
        print("\n" + "="*60)
        print("BENCHMARK SUMMARY")
        print("="*60)
        print(f"Operations: {summary['total_operations']}")
        print(f"Total time: {summary['total_time_seconds']:.2f}s ({summary['total_time_ms']:.0f}ms)")
        print(f"Mean: {summary['mean_duration_ms']:.2f}ms")
        print(f"Median: {summary['median_duration_ms']:.2f}ms")
        print(f"Min: {summary['min_duration_ms']:.2f}ms")
        print(f"Max: {summary['max_duration_ms']:.2f}ms")
        print("="*60 + "\n")
    
    def print_per_operation(self):
        """Print timing for each operation."""
        print("\nOPERATION TIMINGS:")
        print("-" * 60)
        
        for result in sorted(self.results, key=lambda r: r.duration_ms, reverse=True):
            if result.iterations > 1:
                print(f"{result.operation:30} {result.mean_ms:8.2f}ms (±{result.stdev_ms:.2f}ms, {result.iterations}x)")
            else:
                print(f"{result.operation:30} {result.duration_ms:8.2f}ms")
    
    def export_json(self, filepath: str):
        """Export results to JSON."""
        data = {
            'summary': self.get_summary(),
            'results': [asdict(r) for r in self.results],
            'timestamp': datetime.now().isoformat(),
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def export_csv(self, filepath: str):
        """Export results to CSV."""
        import csv
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'operation', 'duration_ms', 'iterations',
                'min_ms', 'max_ms', 'mean_ms', 'median_ms', 'stdev_ms'
            ])
            writer.writeheader()
            for result in self.results:
                writer.writerow({
                    'operation': result.operation,
                    'duration_ms': f"{result.duration_ms:.2f}",
                    'iterations': result.iterations,
                    'min_ms': f"{result.min_ms:.2f}" if result.min_ms else "",
                    'max_ms': f"{result.max_ms:.2f}" if result.max_ms else "",
                    'mean_ms': f"{result.mean_ms:.2f}" if result.mean_ms else "",
                    'median_ms': f"{result.median_ms:.2f}" if result.median_ms else "",
                    'stdev_ms': f"{result.stdev_ms:.2f}" if result.stdev_ms else "",
                })


class MemoryMonitor:
    """Track memory usage during analysis."""
    
    def __init__(self):
        """Initialize memory monitor."""
        self.samples = []
    
    def get_current_usage_mb(self) -> float:
        """Get current process memory usage in MB.
        
        Returns:
            Memory usage in MB, or 0.0 if psutil not available
        """
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            # psutil not installed - silently return 0
            return 0.0
        except Exception:
            # Any other error (permissions, etc) - return 0
            return 0.0
    
    def sample(self):
        """Record current memory usage."""
        usage = self.get_current_usage_mb()
        self.samples.append(usage)
        return usage
    
    def get_stats(self) -> Dict:
        """Get memory usage statistics."""
        if not self.samples:
            return {}
        
        return {
            'initial_mb': self.samples[0],
            'peak_mb': max(self.samples),
            'final_mb': self.samples[-1],
            'delta_mb': self.samples[-1] - self.samples[0],
            'samples': len(self.samples),
        }


# Global benchmark instance for convenient usage
_global_benchmark: Optional[Benchmark] = None
_benchmark_lock = threading.Lock()


def get_benchmark(verbose: bool = False) -> Benchmark:
    """Get or create global benchmark instance (thread-safe).
    
    Uses double-check locking for efficiency.
    
    Args:
        verbose: Print timing info to console
        
    Returns:
        Global benchmark instance
    """
    global _global_benchmark
    
    # Fast path (no lock if already initialized)
    if _global_benchmark is not None:
        return _global_benchmark
    
    # Slow path with lock
    with _benchmark_lock:
        if _global_benchmark is None:
            _global_benchmark = Benchmark(verbose=verbose)
        return _global_benchmark


def reset_benchmark():
    """Reset global benchmark.
    
    Thread-safe reset for testing purposes.
    """
    global _global_benchmark
    with _benchmark_lock:
        _global_benchmark = None
