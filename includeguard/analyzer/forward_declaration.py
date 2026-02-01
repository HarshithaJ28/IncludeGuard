"""
Forward Declaration Detector - Find opportunities to replace includes with forward declarations
"""
import re
from typing import List, Dict, Set, Tuple
from pathlib import Path
from .parser import FileAnalysis, Include


class ForwardDeclarationDetector:
    """
    Detects when headers can be replaced with forward declarations.
    This is a MAJOR build-time optimization.
    
    Forward declarations allow you to declare a class exists without including
    its full definition. This works when you only use pointers/references.
    """
    
    def __init__(self):
        # Patterns that indicate pointer/reference-only usage (forward declaration OK)
        self.pointer_patterns = [
            re.compile(r'\b(\w+)\s*\*'),           # Type* ptr
            re.compile(r'\b(\w+)\s*&'),            # Type& ref
            re.compile(r'<\s*(\w+)\s*\*\s*>'),     # vector<Type*>
            re.compile(r'unique_ptr\s*<\s*(\w+)'), # unique_ptr<Type>
            re.compile(r'shared_ptr\s*<\s*(\w+)'), # shared_ptr<Type>
            re.compile(r'weak_ptr\s*<\s*(\w+)'),   # weak_ptr<Type>
        ]
        
        # Patterns that indicate full definition needed (forward declaration NOT OK)
        self.definition_patterns = [
            re.compile(r'\b(\w+)\s+\w+\s*;'),      # Type var; (object on stack)
            re.compile(r'sizeof\s*\(\s*(\w+)'),    # sizeof(Type)
            re.compile(r'new\s+(\w+)\s*[\(\{]'),   # new Type() or new Type{}
            re.compile(r'\b(\w+)\s+\w+\s*[\(\{]'), # Type obj(args) or Type obj{args}
        ]
    
    def analyze_file(self, filepath: str, analysis: FileAnalysis) -> List[Dict]:
        """
        Analyze a file for forward declaration opportunities.
        
        Args:
            filepath: Path to the file
            analysis: Parsed FileAnalysis
            
        Returns:
            List of opportunities with suggestions
        """
        try:
            content = Path(filepath).read_text(encoding='utf-8', errors='ignore')
        except:
            return []
        
        # Remove comments and strings to avoid false positives
        content = self._remove_comments_and_strings(content)
        
        opportunities = []
        
        for inc in analysis.includes:
            # Skip system includes (can't forward declare STL classes)
            if inc.is_system:
                continue
            
            # Skip headers that are unlikely to be single-class headers
            if any(keyword in inc.header.lower() for keyword in ['util', 'common', 'helper', 'types']):
                continue
            
            # Extract likely class name from header filename
            class_name = self._extract_class_name(inc.header)
            if not class_name:
                continue
            
            # Check if class name appears in the file at all
            if class_name not in content:
                continue
            
            # Check usage patterns
            is_pointer_only = self._check_pointer_only_usage(content, class_name)
            needs_definition = self._check_needs_definition(content, class_name)
            
            if is_pointer_only and not needs_definition:
                confidence = self._calculate_confidence(content, class_name)
                
                # Only suggest if confidence is reasonable
                if confidence >= 0.5:
                    opportunities.append({
                        'header': inc.header,
                        'class_name': class_name,
                        'line': inc.line_number,
                        'confidence': confidence,
                        'suggestion': f'class {class_name};'
                    })
        
        return opportunities
    
    def _extract_class_name(self, header: str) -> str:
        """Extract likely class name from header filename"""
        # Remove path and extension
        name = Path(header).stem
        
        # Remove common suffixes
        name = name.replace('_impl', '').replace('_fwd', '')
        
        # Convert snake_case or kebab-case to PascalCase (common C++ pattern)
        if '_' in name or '-' in name:
            parts = name.replace('-', '_').split('_')
            name = ''.join(p.capitalize() for p in parts)
        else:
            # If already camelCase or PascalCase, capitalize first letter
            name = name[0].upper() + name[1:] if name else ''
        
        return name
    
    def _check_pointer_only_usage(self, content: str, class_name: str) -> bool:
        """Check if class is only used as pointer/reference"""
        for pattern in self.pointer_patterns:
            matches = pattern.findall(content)
            # Check if our class name is in the matches
            if any(class_name == match or class_name in match for match in matches):
                return True
        return False
    
    def _check_needs_definition(self, content: str, class_name: str) -> bool:
        """Check if full class definition is needed"""
        for pattern in self.definition_patterns:
            if re.search(rf'\b{class_name}\b', content):
                matches = pattern.findall(content)
                if any(class_name == match or class_name in match for match in matches):
                    return True
        
        # Check for method calls on the object (not pointer)
        # Pattern: objectName.method() where objectName is of type ClassName
        if re.search(rf'\b\w+\.', content):
            # This is complex to detect reliably, so be conservative
            # If we see any dot notation, there might be method calls
            pass
        
        return False
    
    def _calculate_confidence(self, content: str, class_name: str) -> float:
        """Calculate confidence that forward declaration will work"""
        confidence = 0.6  # Base confidence
        
        # Higher confidence if we see pointer patterns
        pointer_count = sum(
            len([m for m in p.findall(content) if class_name in str(m)])
            for p in self.pointer_patterns
        )
        confidence += min(pointer_count * 0.1, 0.3)
        
        # Lower confidence if we see definition patterns
        definition_count = sum(
            len([m for m in p.findall(content) if class_name in str(m)])
            for p in self.definition_patterns
        )
        confidence -= min(definition_count * 0.15, 0.4)
        
        # Check if class appears in function signatures (good for forward decl)
        func_sig_pattern = re.compile(rf'\b{class_name}\s*[\*&]')
        if func_sig_pattern.search(content):
            confidence += 0.1
        
        return max(0.0, min(1.0, confidence))
    
    def _remove_comments_and_strings(self, content: str) -> str:
        """Remove comments and string literals to avoid false positives"""
        # Remove // comments
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        # Remove /* */ comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        # Remove string literals
        content = re.sub(r'"[^"]*"', '""', content)
        content = re.sub(r"'[^']*'", "''", content)
        return content
