"""
IMPROVED TIER 2: COMPILATION-BASED VALIDATION
==============================================
This script validates IncludeGuard accuracy by actually compiling.
Ground truth: Does the code compile without each header?

Strategy:
1. Get ALL headers from a file
2. Try removing EACH ONE and compiling
3. If compilation succeeds = header is truly unused
4. If compilation fails = header is truly used

This eliminates guessing and gives us ground truth.
"""

import subprocess
import tempfile
import os
from pathlib import Path
from typing import Dict, List, Tuple

class CompilationTruthValidator:
    """Validate headers using actual compilation truth"""
    
    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.results = {
            'truly_unused': [],
            'truly_used': [],
            'compilation_errors': []
        }
    
    def find_all_headers(self, file_path: Path) -> List[Tuple[str, int]]:
        """Find all #include directives in a file"""
        includes = []
        try:
            content = file_path.read_text(errors='ignore')
            for line_num, line in enumerate(content.split('\n'), 1):
                stripped = line.strip()
                if stripped.startswith('#include'):
                    # Extract header name
                    if '<' in stripped and '>' in stripped:
                        header = stripped[stripped.find('<')+1:stripped.find('>')]
                    elif '"' in stripped:
                        header = stripped.split('"')[1]
                    else:
                        continue
                    includes.append((header, line_num))
        except:
            pass
        return includes
    
    def test_header_by_compilation(self, file_path: Path, header: str) -> bool:
        """
        Test if a header is truly needed by checking if code compiles without it.
        
        Returns: True if header is TRULY UNUSED (code compiles without it)
                 False if header is TRULY USED (code doesn't compile without it)
        """
        try:
            content = file_path.read_text(errors='ignore')
            lines = content.split('\n')
            
            # Remove the include directive
            test_lines = []
            removed = False
            for line in lines:
                if f'#include <{header}>' in line or f'#include "{header}"' in line:
                    removed = False
                    continue
                test_lines.append(line)
            
            if not removed:
                # Couldn't find the include, try harder
                for i, line in enumerate(lines):
                    if '#include' in line and header in line:
                        lines.pop(i)
                        break
                test_lines = lines
            
            # Write to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
                f.write('\n'.join(test_lines))
                temp_file = f.name
            
            try:
                # Try to compile
                result = subprocess.run(
                    ['g++', '-c', temp_file, '-o', os.devnull],
                    capture_output=True,
                    timeout=10,
                    text=True
                )
                
                # If compilation succeeds = header is TRULY UNUSED
                return result.returncode == 0
            finally:
                Path(temp_file).unlink(missing_ok=True)
        
        except Exception as e:
            print(f"      [Error testing {header}: {str(e)[:50]}]")
            return False
    
    def validate_file(self, file_path: Path) -> Dict:
        """Validate all headers in a file through compilation"""
        if not file_path.exists():
            return {'status': 'error', 'reason': 'file not found'}
        
        results = {
            'file': str(file_path),
            'truly_unused': [],
            'truly_used': [],
            'test_count': 0
        }
        
        headers = self.find_all_headers(file_path)
        
        for header, line_num in headers:
            results['test_count'] += 1
            is_truly_unused = self.test_header_by_compilation(file_path, header)
            
            if is_truly_unused:
                results['truly_unused'].append({
                    'header': header,
                    'line': line_num
                })
                self.results['truly_unused'].append(header)
                print(f"      [UNUSED] {header}")
            else:
                results['truly_used'].append({
                    'header': header,
                    'line': line_num
                })
                self.results['truly_used'].append(header)
                print(f"      [USED] {header}")
        
        return results
    
    def validate_project(self) -> Dict:
        """Validate all C++ files in the project"""
        print("\n[GROUND TRUTH VALIDATION - Compilation-Based]")
        print(f"Project: {self.project_path.name}\n")
        
        cpp_files = list(self.project_path.glob('**/*.cpp')) + list(self.project_path.glob('**/*.h'))
        cpp_files = cpp_files[:3]  # Test first 3 files only (for speed)
        
        all_results = []
        
        for file_path in cpp_files:
            print(f"\n[TESTING] {file_path.name}")
            result = self.validate_file(file_path)
            all_results.append(result)
        
        #Summary
        print("\n" + "="*70)
        print("GROUND TRUTH RESULTS")
        print("="*70)
        
        total_tested = len(self.results['truly_unused']) + len(self.results['truly_used'])
        truly_unused_count = len(self.results['truly_unused'])
        
        if total_tested > 0:
            percentage = (truly_unused_count / total_tested) * 100
            print(f"\nTotal headers tested: {total_tested}")
            print(f"Truly unused (safe to remove): {truly_unused_count} ({percentage:.1f}%)")
            print(f"Truly used (must keep): {len(self.results['truly_used'])} ({100-percentage:.1f}%)")
            
            print(f"\nUnused headers you can safely remove:")
            for header in set(self.results['truly_unused']):
                print(f"  - {header}")
        else:
            print("No headers tested")
        
        return all_results


if __name__ == "__main__":
    project = Path("examples/sample_project")
    validator = CompilationTruthValidator(project)
    results = validator.validate_project()
