"""
Trace through the EXACT logic for each header
"""
import tempfile
from pathlib import Path
import re

code_long = """
#include <iostream>
#include <map>
#include <queue>

int main() {
    std::cout << "Hello";
    return 0;
}
"""

with tempfile.TemporaryDirectory() as tmpdir:
    file_path = Path(tmpdir) / "test.cpp"
    file_path.write_text(code_long)
    
    # Preprocess like estimator does
    content = code_long
    content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    content = re.sub(r'"[^"]*"', '""', content)
    content = re.sub(r"'[^']*'", "''", content)
    content = re.sub(r'#include.*', '', content)
    
    print("PREPROCESSED CONTENT:")
    print(repr(content))
    print("\n" + "="*60)
    
    # Trace through each header
    for header in ["iostream", "map", "queue"]:
        print(f"\nHEADER: {header}")
        
        # Classification
        is_system = header.startswith('<') or '/' not in header
        print(f"  is_system: {is_system} (starts with '<': {header.startswith('<')}, no '/': {'/' not in header})")
        
        # Base name
        base_name = Path(header).stem
        print(f"  base_name: {base_name}")
        
        # Pattern checks
        patterns = []
        
        # Pattern 1: Direct name
        p1 = bool(re.search(rf'\b{re.escape(base_name)}\b', content, re.IGNORECASE))
        patterns.append(p1)
        print(f"  Pattern 1 (direct name '{base_name}'): {p1}")
        
        # Pattern 2: Symbol usage (CAN'T TRACE WITHOUT THE DICT, but we can check manually)
        # For iostream, check if 'cout' is in content
        if header == "iostream":
            p2 = 'cout' in content
            print(f"  Pattern 2 (symbol 'cout'): {p2}")
            patterns.append(p2)
        elif header == "map":
            # Check if any map symbols exist
            map_symbols = ['insert', 'find', 'erase', 'count', 'at', 'begin', 'end', 'clear', 'empty', 'size']
            p2 = any(sym in content for sym in map_symbols)
            print(f"  Pattern 2 (any map symbols): {p2}")
            patterns.append(p2)
        elif header == "queue":
            queue_symbols = ['push', 'pop', 'front', 'back', 'empty', 'size']
            p2 = any(sym in content for sym in queue_symbols)
            print(f"  Pattern 2 (any queue symbols): {p2}")
            patterns.append(p2)
        
        # Pattern 3: std:: for system headers
        p3 = is_system and bool(re.search(r'\bstd::\w+', content))
        patterns.append(p3)
        print(f"  Pattern 3 (std:: usage): {p3}")
        
        patterns_found = sum(patterns)
        confidence = patterns_found / 3
        print(f"\n  RESULT: {patterns_found}/3 patterns = {confidence:.1%} confidence")
        print(f"  is_likely_used: {confidence > 0.30}")
