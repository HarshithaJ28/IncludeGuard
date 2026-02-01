"""
Include Parser - Fast regex-based C++ include extraction
"""
import re
from pathlib import Path
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, field

@dataclass
class Include:
    """Represents a single #include directive"""
    header: str
    line_number: int
    is_system: bool  # True for <>, False for ""
    full_path: str = ""
    
    def __repr__(self):
        bracket = ('<', '>') if self.is_system else ('"', '"')
        return f"Include({bracket[0]}{self.header}{bracket[1]} at line {self.line_number})"

@dataclass
class FileAnalysis:
    """Analysis results for a single source file"""
    filepath: str
    includes: List[Include] = field(default_factory=list)
    total_lines: int = 0
    code_lines: int = 0  # Excluding comments/blank
    comment_lines: int = 0
    blank_lines: int = 0
    has_templates: bool = False
    has_macros: bool = False
    namespace_count: int = 0
    class_count: int = 0
    
    def __repr__(self):
        return f"FileAnalysis({Path(self.filepath).name}, {len(self.includes)} includes)"

class IncludeParser:
    """
    Fast regex-based parser for C++ includes.
    Doesn't require compilation or libclang.
    """
    
    # Regex patterns
    INCLUDE_PATTERN = re.compile(
        r'^\s*#\s*include\s*([<"])([^>"]+)([>"])',
        re.MULTILINE
    )
    
    SINGLE_COMMENT = re.compile(r'//.*?$', re.MULTILINE)
    MULTI_COMMENT = re.compile(r'/\*.*?\*/', re.DOTALL)
    TEMPLATE_PATTERN = re.compile(r'\btemplate\s*<')
    MACRO_PATTERN = re.compile(r'^\s*#\s*define\s+', re.MULTILINE)
    NAMESPACE_PATTERN = re.compile(r'\bnamespace\s+\w+')
    CLASS_PATTERN = re.compile(r'\b(class|struct)\s+\w+')
    
    def __init__(self, project_root: Path, include_paths: List[Path] = None):
        """
        Initialize parser.
        
        Args:
            project_root: Root directory of the project
            include_paths: Additional include search paths
        """
        self.project_root = Path(project_root).resolve()
        self.include_paths = [Path(p).resolve() for p in (include_paths or [])]
        self.include_paths.insert(0, self.project_root)  # Search project root first
        
    def parse_file(self, filepath: Path) -> Optional[FileAnalysis]:
        """
        Parse a single C++ file for includes and metrics.
        
        Args:
            filepath: Path to the C++ file
            
        Returns:
            FileAnalysis object or None if error
        """
        try:
            filepath = Path(filepath).resolve()
            content = filepath.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            print(f"Warning: Could not read {filepath}: {e}")
            return None
        
        analysis = FileAnalysis(filepath=str(filepath))
        
        # Parse includes
        for match in self.INCLUDE_PATTERN.finditer(content):
            open_bracket = match.group(1)
            header = match.group(2)
            close_bracket = match.group(3)
            
            # Validate matching brackets
            if (open_bracket == '<' and close_bracket != '>') or \
               (open_bracket == '"' and close_bracket != '"'):
                continue
            
            line_num = content[:match.start()].count('\n') + 1
            is_system = (open_bracket == '<')
            
            full_path = self._resolve_include(header, filepath, is_system)
            
            analysis.includes.append(Include(
                header=header,
                line_number=line_num,
                is_system=is_system,
                full_path=full_path
            ))
        
        # Calculate metrics
        lines = content.split('\n')
        analysis.total_lines = len(lines)
        
        # Remove comments for accurate code analysis
        code_content = self._remove_comments(content)
        code_lines = code_content.split('\n')
        
        analysis.code_lines = len([l for l in code_lines if l.strip()])
        analysis.blank_lines = len([l for l in lines if not l.strip()])
        analysis.comment_lines = analysis.total_lines - analysis.code_lines - analysis.blank_lines
        
        # Detect features
        analysis.has_templates = bool(self.TEMPLATE_PATTERN.search(content))
        analysis.has_macros = bool(self.MACRO_PATTERN.search(content))
        analysis.namespace_count = len(self.NAMESPACE_PATTERN.findall(content))
        analysis.class_count = len(self.CLASS_PATTERN.findall(content))
        
        return analysis
    
    def _resolve_include(self, header: str, source_file: Path, is_system: bool) -> str:
        """
        Try to find the full path of an included header.
        
        Args:
            header: Header name (e.g., "vector" or "MyClass.h")
            source_file: Source file doing the include
            is_system: Whether it's a system include (<>)
            
        Returns:
            Full path if found, otherwise original header name
        """
        if is_system:
            # System headers - return with brackets for identification
            return f"<{header}>"
        
        # User headers - try to find actual file
        # First, try relative to source file
        source_dir = source_file.parent
        candidate = source_dir / header
        if candidate.exists():
            return str(candidate.resolve())
        
        # Try each include path
        for include_path in self.include_paths:
            candidate = include_path / header
            if candidate.exists():
                return str(candidate.resolve())
        
        # Not found - return original
        return header
    
    def _remove_comments(self, content: str) -> str:
        """
        Remove C++ comments from content.
        
        Args:
            content: Source code content
            
        Returns:
            Content with comments removed
        """
        # Remove multi-line comments first
        content = self.MULTI_COMMENT.sub('', content)
        # Remove single-line comments
        content = self.SINGLE_COMMENT.sub('', content)
        return content
    
    def parse_project(self, 
                     extensions: List[str] = None,
                     exclude_dirs: List[str] = None) -> List[FileAnalysis]:
        """
        Parse all C++ files in project.
        
        Args:
            extensions: File extensions to parse (default: common C++ extensions)
            exclude_dirs: Directory names to exclude (default: build dirs)
            
        Returns:
            List of FileAnalysis objects
        """
        if extensions is None:
            extensions = ['.cpp', '.cc', '.cxx', '.c', '.h', '.hpp', '.hxx', '.hh']
        
        if exclude_dirs is None:
            exclude_dirs = ['build', 'cmake-build', 'cmake-build-debug', 
                          'cmake-build-release', '.git', '.svn', 'node_modules',
                          'venv', 'env', '__pycache__']
        
        results = []
        exclude_set = set(exclude_dirs)
        
        print(f"Scanning {self.project_root} for C++ files...")
        
        for ext in extensions:
            for filepath in self.project_root.rglob(f'*{ext}'):
                # Check if file is in excluded directory
                if any(excluded in filepath.parts for excluded in exclude_set):
                    continue
                
                analysis = self.parse_file(filepath)
                if analysis:
                    results.append(analysis)
        
        print(f"Found {len(results)} C++ files")
        return results

    def get_statistics(self, analyses: List[FileAnalysis]) -> Dict:
        """
        Get overall statistics from multiple analyses.
        
        Args:
            analyses: List of FileAnalysis objects
            
        Returns:
            Dictionary of statistics
        """
        if not analyses:
            return {}
        
        total_files = len(analyses)
        total_includes = sum(len(a.includes) for a in analyses)
        total_lines = sum(a.total_lines for a in analyses)
        total_code = sum(a.code_lines for a in analyses)
        
        system_includes = sum(
            sum(1 for inc in a.includes if inc.is_system)
            for a in analyses
        )
        
        user_includes = total_includes - system_includes
        
        files_with_templates = sum(1 for a in analyses if a.has_templates)
        files_with_macros = sum(1 for a in analyses if a.has_macros)
        
        return {
            'total_files': total_files,
            'total_includes': total_includes,
            'system_includes': system_includes,
            'user_includes': user_includes,
            'total_lines': total_lines,
            'total_code_lines': total_code,
            'avg_includes_per_file': total_includes / total_files if total_files > 0 else 0,
            'avg_lines_per_file': total_lines / total_files if total_files > 0 else 0,
            'files_with_templates': files_with_templates,
            'files_with_macros': files_with_macros,
        }
