"""
Patch Generator - Create Git patches to automatically fix include issues

Generates unified diff patches that can be applied with `git apply` to:
- Remove unused includes
- Replace includes with forward declarations
- Optimize header dependencies
"""
import difflib
from pathlib import Path
from typing import List, Dict, Set, Optional


class PatchGenerator:
    """Generate Git-compatible patches for include optimizations"""
    
    def __init__(self, min_confidence: float = 0.7):
        """
        Initialize patch generator.
        
        Args:
            min_confidence: Minimum confidence (0-1) for applying auto-fixes
        """
        self.min_confidence = min_confidence
        self.fixes_applied = 0
        self.files_modified = set()
    
    def generate_patch(self,
                      reports: List[Dict],
                      forward_decls: List[Dict],
                      output_path: str) -> int:
        """
        Generate unified diff patch file.
        
        Args:
            reports: Analysis reports with optimization opportunities
            forward_decls: Forward declaration opportunities
            output_path: Where to save patch file
            
        Returns:
            Number of files modified
        """
        patches = []
        
        # Group forward declarations by file
        fwd_by_file = {}
        for fwd in forward_decls:
            if fwd.get('confidence', 0) >= self.min_confidence:
                filename = fwd.get('file', '')
                if filename not in fwd_by_file:
                    fwd_by_file[filename] = []
                fwd_by_file[filename].append(fwd)
        
        # Process each analyzed file
        processed_files = set()
        
        for report in reports:
            filepath_str = report.get('file', '')
            filepath = Path(filepath_str)
            
            if not filepath.exists():
                continue
            
            # Avoid processing same file twice
            if str(filepath) in processed_files:
                continue
            processed_files.add(str(filepath))
            
            # Get original content
            try:
                original = filepath.read_text(encoding='utf-8')
            except Exception as e:
                print(f"Warning: Could not read {filepath}: {e}")
                continue
            
            # Apply fixes
            opportunities = report.get('optimization_opportunities', [])
            fwd_decls_for_file = fwd_by_file.get(filepath.name, [])
            
            modified = self._apply_fixes(
                original,
                opportunities,
                fwd_decls_for_file
            )
            
            if modified != original:
                # Generate unified diff
                diff_lines = list(difflib.unified_diff(
                    original.splitlines(keepends=True),
                    modified.splitlines(keepends=True),
                    fromfile=f'a/{filepath}',
                    tofile=f'b/{filepath}',
                    lineterm=''
                ))
                
                if diff_lines:
                    patch = ''.join(diff_lines)
                    patches.append(patch)
                    self.files_modified.add(str(filepath))
        
        # Write patch file
        if patches:
            output = Path(output_path)
            output.write_text('\n'.join(patches), encoding='utf-8')
        
        return len(self.files_modified)
    
    def _apply_fixes(self,
                    content: str,
                    unused_includes: List[Dict],
                    forward_decls: List[Dict]) -> str:
        """
        Apply fixes to file content.
        
        Args:
            content: Original file content
            unused_includes: List of unused include opportunities
            forward_decls: List of forward declaration opportunities
            
        Returns:
            Modified content with fixes applied
        """
        lines = content.split('\n')
        
        # Track which lines to remove/modify
        lines_to_remove: Set[int] = set()
        lines_to_modify: Dict[int, str] = {}
        
        # Remove unused includes with high cost
        for inc in unused_includes:
            # Only remove if not likely used and has significant cost
            if not inc.get('likely_used', True) and inc.get('cost', 0) > 500:
                line_idx = inc.get('line', 0) - 1  # Convert to 0-indexed
                if 0 <= line_idx < len(lines):
                    lines_to_remove.add(line_idx)
                    self.fixes_applied += 1
        
        # Replace includes with forward declarations
        for fwd in forward_decls:
            if fwd.get('confidence', 0) >= self.min_confidence:
                line_idx = fwd.get('line', 0) - 1
                if 0 <= line_idx < len(lines):
                    # Don't modify if already marked for removal
                    if line_idx not in lines_to_remove:
                        suggestion = fwd.get('suggestion', '')
                        if suggestion:
                            lines_to_modify[line_idx] = suggestion
                            self.fixes_applied += 1
        
        # Apply changes
        result_lines = []
        for i, line in enumerate(lines):
            if i in lines_to_remove:
                continue  # Skip this line (remove it)
            elif i in lines_to_modify:
                result_lines.append(lines_to_modify[i])
            else:
                result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about applied fixes"""
        return {
            'fixes_applied': self.fixes_applied,
            'files_modified': len(self.files_modified)
        }


def generate_safe_patch(reports: List[Dict],
                       forward_decls: List[Dict],
                       output_path: str,
                       min_confidence: float = 0.8) -> Dict[str, int]:
    """
    Convenience function to generate a safe patch with high confidence threshold.
    
    Args:
        reports: Analysis reports
        forward_decls: Forward declaration opportunities
        output_path: Output patch file path
        min_confidence: Minimum confidence for auto-fixes (default 0.8 for safety)
        
    Returns:
        Statistics dictionary with fixes_applied and files_modified
    """
    generator = PatchGenerator(min_confidence=min_confidence)
    files_modified = generator.generate_patch(reports, forward_decls, output_path)
    
    stats = generator.get_stats()
    return stats
