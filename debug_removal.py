"""
Debug: Check if #include removal is working
"""
import re

code = """
#include <iostream>
#include <map>
#include <queue>

int main() {
    std::cout << "Hello";
    return 0;
}
"""

print("ORIGINAL CODE:")
print(code)
print("\n" + "="*50)

# Apply the same preprocessing as estimator.py
content = code
content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
content = re.sub(r'"[^"]*"', '""', content)
content = re.sub(r"'[^']*'", "''", content)
content = re.sub(r'#include.*', '', content)

print("\nAFTER PREPROCESSING:")
print(repr(content))
print("\n" + "="*50)

# Now check patterns
from pathlib import Path
for header in ["iostream", "map", "queue"]:
    base_name = Path(header).stem
    p1 = bool(re.search(rf'\b{re.escape(base_name)}\b', content, re.IGNORECASE))
    print(f"{header}: pattern1={p1}")
    
    # Show where it matches
    match = re.search(rf'\b{re.escape(base_name)}\b', content, re.IGNORECASE)
    if match:
        start = max(0, match.start() - 20)
        end = min(len(content), match.end() + 20)
        context = repr(content[start:end])
        print(f"  Found at: {context}")
