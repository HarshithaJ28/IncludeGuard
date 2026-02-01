"""
Build Profiler - Measure ACTUAL compilation time impact
"""
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class CompilationProfile:
    """Results from compiling a file"""
    source_file: str
    compilation_time_ms: float
    preprocessed_lines: int
    success: bool
    error_message: Optional[str] = None


class BuildProfiler:
    """
    Profile actual compilation times.
    This validates the cost estimates with REAL data.
    
    Uses the C++ compiler's preprocessor (-E flag) to measure the impact
    of each header without doing a full compilation.
    """
    
    def __init__(self, compiler: str = "g++"):
        """
        Initialize profiler.
        
        Args:
            compiler: Compiler command (g++, clang++, cl, etc.)
        """
        self.compiler = compiler
        self._verify_compiler()
    
    def _verify_compiler(self):
        """Check if compiler is available"""
        try:
            subprocess.run(
                [self.compiler, '--version'],
                capture_output=True,
                timeout=5
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            # Compiler not available, but don't fail - let profile_file handle it
            pass
    
    def profile_file(self, 
                     source_file: str,
                     compile_flags: List[str] = None) -> CompilationProfile:
        """
        Profile compilation time for a single file.
        
        Args:
            source_file: Path to C++ file
            compile_flags: Compiler flags (e.g., ['-std=c++17', '-O2'])
            
        Returns:
            CompilationProfile with timing data
        """
        if compile_flags is None:
            compile_flags = ['-std=c++17']  # Default to C++17
        
        # Measure preprocessing time (fastest way to measure include impact)
        start = time.time()
        
        cmd = [self.compiler, '-E', source_file] + compile_flags
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            preprocess_time = (time.time() - start) * 1000  # Convert to ms
            
            if result.returncode == 0:
                preprocessed_lines = len(result.stdout.split('\n'))
            else:
                preprocessed_lines = 0
            
            return CompilationProfile(
                source_file=source_file,
                compilation_time_ms=preprocess_time,
                preprocessed_lines=preprocessed_lines,
                success=result.returncode == 0,
                error_message=result.stderr if result.returncode != 0 else None
            )
            
        except subprocess.TimeoutExpired:
            return CompilationProfile(
                source_file=source_file,
                compilation_time_ms=30000,  # 30 seconds timeout
                preprocessed_lines=0,
                success=False,
                error_message="Compilation timeout (>30s)"
            )
        except FileNotFoundError:
            return CompilationProfile(
                source_file=source_file,
                compilation_time_ms=0,
                preprocessed_lines=0,
                success=False,
                error_message=f"Compiler '{self.compiler}' not found"
            )
        except Exception as e:
            return CompilationProfile(
                source_file=source_file,
                compilation_time_ms=0,
                preprocessed_lines=0,
                success=False,
                error_message=str(e)
            )
    
    def profile_with_and_without_header(self,
                                        source_file: str,
                                        header_to_remove: str,
                                        compile_flags: List[str] = None) -> Dict:
        """
        Profile compilation with/without a specific header.
        
        This measures the ACTUAL impact of removing a header.
        
        Args:
            source_file: C++ file to profile
            header_to_remove: Header to temporarily remove
            compile_flags: Compiler flags
            
        Returns:
            Dict with before/after timings and savings
        """
        # Profile original file
        baseline = self.profile_file(source_file, compile_flags)
        
        if not baseline.success:
            return {
                'header': header_to_remove,
                'baseline_ms': 0,
                'without_header_ms': 0,
                'savings_ms': 0,
                'savings_pct': 0,
                'baseline_lines': 0,
                'without_header_lines': 0,
                'lines_saved': 0,
                'error': baseline.error_message
            }
        
        # Create temporary file without the header
        temp_file = self._create_file_without_header(source_file, header_to_remove)
        
        try:
            # Profile without header
            without_header = self.profile_file(str(temp_file), compile_flags)
            
            if not without_header.success:
                # Header removal broke compilation (header was needed)
                return {
                    'header': header_to_remove,
                    'baseline_ms': baseline.compilation_time_ms,
                    'without_header_ms': 0,
                    'savings_ms': 0,
                    'savings_pct': 0,
                    'baseline_lines': baseline.preprocessed_lines,
                    'without_header_lines': 0,
                    'lines_saved': 0,
                    'error': 'Header is required (removal breaks compilation)'
                }
            
            savings_ms = baseline.compilation_time_ms - without_header.compilation_time_ms
            savings_pct = (savings_ms / baseline.compilation_time_ms * 100 
                          if baseline.compilation_time_ms > 0 else 0)
            
            return {
                'header': header_to_remove,
                'baseline_ms': baseline.compilation_time_ms,
                'without_header_ms': without_header.compilation_time_ms,
                'savings_ms': savings_ms,
                'savings_pct': savings_pct,
                'baseline_lines': baseline.preprocessed_lines,
                'without_header_lines': without_header.preprocessed_lines,
                'lines_saved': baseline.preprocessed_lines - without_header.preprocessed_lines,
                'error': None
            }
        finally:
            # Clean up temp file
            if temp_file.exists():
                temp_file.unlink()
    
    def _create_file_without_header(self, source_file: str, header: str) -> Path:
        """Create temporary file with header removed"""
        content = Path(source_file).read_text(encoding='utf-8', errors='ignore')
        
        # Remove the include line
        lines = content.split('\n')
        filtered_lines = []
        
        for line in lines:
            # Check if this line includes the target header
            if line.strip().startswith('#include'):
                # Extract header from include line
                if header in line:
                    # Skip this line (remove the include)
                    continue
            filtered_lines.append(line)
        
        # Create temp file
        temp = tempfile.NamedTemporaryFile(
            mode='w',
            suffix=Path(source_file).suffix,
            delete=False,
            encoding='utf-8'
        )
        temp.write('\n'.join(filtered_lines))
        temp.close()
        
        return Path(temp.name)
