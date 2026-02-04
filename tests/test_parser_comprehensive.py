"""
Comprehensive tests for IncludeParser - covering all edge cases
"""
import pytest
from pathlib import Path
import tempfile
import shutil
from includeguard.analyzer.parser import IncludeParser, FileAnalysis, Include


class TestBasicParsing:
    """Test basic parsing functionality"""
    
    def test_system_includes(self):
        """Test parsing system includes with <>"""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            test_file = temp_dir / "test.cpp"
            test_file.write_text("""
#include <iostream>
#include <vector>
#include <algorithm>
""")
            
            parser = IncludeParser(temp_dir)
            analysis = parser.parse_file(test_file)
            
            assert len(analysis.includes) == 3
            assert all(inc.is_system for inc in analysis.includes)
            assert analysis.includes[0].header == 'iostream'
            assert analysis.includes[1].header == 'vector'
            assert analysis.includes[2].header == 'algorithm'
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_user_includes(self):
        """Test parsing user includes with quotes"""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            test_file = temp_dir / "test.cpp"
            test_file.write_text("""
#include "myheader.h"
#include "utils/helper.h"
#include "../parent.h"
""")
            
            parser = IncludeParser(temp_dir)
            analysis = parser.parse_file(test_file)
            
            assert len(analysis.includes) == 3
            assert all(not inc.is_system for inc in analysis.includes)
            assert analysis.includes[0].header == 'myheader.h'
            assert analysis.includes[1].header == 'utils/helper.h'
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_mixed_includes(self):
        """Test parsing mixed system and user includes"""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            test_file = temp_dir / "test.cpp"
            test_file.write_text("""
#include <iostream>
#include "myheader.h"
#include <vector>
#include "another.h"
""")
            
            parser = IncludeParser(temp_dir)
            analysis = parser.parse_file(test_file)
            
            assert len(analysis.includes) == 4
            assert analysis.includes[0].is_system == True
            assert analysis.includes[1].is_system == False
            assert analysis.includes[2].is_system == True
            assert analysis.includes[3].is_system == False
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestEdgeCases:
    """Test edge cases and malformed input"""
    
    def test_empty_file(self):
        """Test parsing empty file"""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            test_file = temp_dir / "empty.cpp"
            test_file.write_text("")
            
            parser = IncludeParser(temp_dir)
            analysis = parser.parse_file(test_file)
            
            assert analysis is not None
            assert len(analysis.includes) == 0
            assert analysis.total_lines == 1  # Parser counts trailing newline
            assert analysis.code_lines == 0
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_only_whitespace(self):
        """Test file with only whitespace"""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            test_file = temp_dir / "whitespace.cpp"
            test_file.write_text("\n\n   \n\t\n  \n")
            
            parser = IncludeParser(temp_dir)
            analysis = parser.parse_file(test_file)
            
            assert len(analysis.includes) == 0
            assert analysis.total_lines == 6  # Parser counts each line including empty ones
            assert analysis.blank_lines >= 4
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_only_comments(self):
        """Test file with only comments"""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            test_file = temp_dir / "comments.cpp"
            test_file.write_text("""
// This is a comment
/* Multi-line
   comment */
// Another comment
""")
            
            parser = IncludeParser(temp_dir)
            analysis = parser.parse_file(test_file)
            
            assert len(analysis.includes) == 0
            assert analysis.comment_lines >= 2
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_include_in_comment(self):
        """Test that includes in comments are NOT parsed"""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            test_file = temp_dir / "commented_include.cpp"
            test_file.write_text("""
// #include <iostream>
/* #include <vector> */
#include <algorithm>
""")
            
            parser = IncludeParser(temp_dir)
            analysis = parser.parse_file(test_file)
            
            # Should only find algorithm, not the commented ones
            assert len(analysis.includes) == 1
            assert analysis.includes[0].header == 'algorithm'
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_include_in_string(self):
        """Test include-like text in strings"""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            test_file = temp_dir / "string_include.cpp"
            test_file.write_text("""
#include <iostream>

int main() {
    const char* str = "#include <fake>";
    std::cout << str << std::endl;
    return 0;
}
""")
            
            parser = IncludeParser(temp_dir)
            analysis = parser.parse_file(test_file)
            
            # Should only find real include
            assert len(analysis.includes) == 1
            assert analysis.includes[0].header == 'iostream'
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_malformed_include(self):
        """Test malformed include directives"""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            test_file = temp_dir / "malformed.cpp"
            test_file.write_text("""
#include <iostream>
#include <vector
#include "missing_quote.h
# include < spaces >
#include
""")
            
            parser = IncludeParser(temp_dir)
            analysis = parser.parse_file(test_file)
            
            # Should parse valid ones, skip invalid
            assert len(analysis.includes) >= 1
            assert analysis.includes[0].header == 'iostream'
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_include_with_spaces(self):
        """Test include with extra spaces"""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            test_file = temp_dir / "spaces.cpp"
            test_file.write_text("""
#  include   <iostream>
#include     "myheader.h"
  #  include  <vector>
""")
            
            parser = IncludeParser(temp_dir)
            analysis = parser.parse_file(test_file)
            
            assert len(analysis.includes) == 3
            assert analysis.includes[0].header == 'iostream'
            assert analysis.includes[1].header == 'myheader.h'
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_ifndef_include_guard(self):
        """Test parsing file with include guards"""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            test_file = temp_dir / "guarded.h"
            test_file.write_text("""
#ifndef MYHEADER_H
#define MYHEADER_H

#include <iostream>
#include <vector>

class MyClass {};

#endif // MYHEADER_H
""")
            
            parser = IncludeParser(temp_dir)
            analysis = parser.parse_file(test_file)
            
            assert len(analysis.includes) == 2
            assert analysis.has_macros == True
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_unicode_file(self):
        """Test parsing file with unicode characters"""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            test_file = temp_dir / "unicode.cpp"
            test_file.write_text("""
#include <iostream>

// 测试 unicode
int main() {
    std::cout << "Hello 世界" << std::endl;  // 中文
    return 0;
}
""", encoding='utf-8')
            
            parser = IncludeParser(temp_dir)
            analysis = parser.parse_file(test_file)
            
            assert analysis is not None
            assert len(analysis.includes) == 1
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_very_long_line(self):
        """Test file with very long lines"""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            test_file = temp_dir / "longline.cpp"
            long_string = "x" * 10000
            test_file.write_text(f"""
#include <iostream>

const char* longstr = "{long_string}";
""")
            
            parser = IncludeParser(temp_dir)
            analysis = parser.parse_file(test_file)
            
            assert analysis is not None
            assert len(analysis.includes) == 1
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestMetricCounting:
    """Test counting of metrics (lines, templates, classes, etc.)"""
    
    def test_line_counting(self):
        """Test accurate line counting"""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            test_file = temp_dir / "lines.cpp"
            test_file.write_text("""
#include <iostream>

// Comment
int main() {

    return 0;
}
""")
            
            parser = IncludeParser(temp_dir)
            analysis = parser.parse_file(test_file)
            
            assert analysis.total_lines == 9  # Parser counts all lines
            assert analysis.code_lines > 0
            assert analysis.blank_lines >= 2
            assert analysis.comment_lines >= 1
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_template_detection(self):
        """Test template detection"""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            test_file = temp_dir / "template.h"
            test_file.write_text("""
template<typename T>
class MyClass {
    T value;
};

template<typename T, typename U>
void foo(T a, U b) {}
""")
            
            parser = IncludeParser(temp_dir)
            analysis = parser.parse_file(test_file)
            
            assert analysis.has_templates == True
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_macro_detection(self):
        """Test macro definition detection"""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            test_file = temp_dir / "macros.h"
            test_file.write_text("""
#define MY_MACRO 42
#define ANOTHER_MACRO(x) ((x) * 2)
#define   SPACES   100
""")
            
            parser = IncludeParser(temp_dir)
            analysis = parser.parse_file(test_file)
            
            assert analysis.has_macros == True
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_namespace_counting(self):
        """Test namespace counting"""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            test_file = temp_dir / "namespaces.cpp"
            test_file.write_text("""
namespace foo {
    namespace bar {
        int x = 42;
    }
}

namespace baz {
    void func() {}
}
""")
            
            parser = IncludeParser(temp_dir)
            analysis = parser.parse_file(test_file)
            
            assert analysis.namespace_count >= 2
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_class_counting(self):
        """Test class/struct counting"""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            test_file = temp_dir / "classes.cpp"
            test_file.write_text("""
class MyClass {
public:
    int x;
};

struct MyStruct {
    double y;
};

class AnotherClass {};
""")
            
            parser = IncludeParser(temp_dir)
            analysis = parser.parse_file(test_file)
            
            assert analysis.class_count >= 3
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectParsing:
    """Test parsing entire projects"""
    
    def test_parse_multi_file_project(self):
        """Test parsing project with multiple files"""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            # Create multiple files
            (temp_dir / "main.cpp").write_text("""
#include <iostream>
#include "utils.h"

int main() {
    return 0;
}
""")
            
            (temp_dir / "utils.h").write_text("""
#pragma once
#include <vector>

void utility() {}
""")
            
            (temp_dir / "helper.cpp").write_text("""
#include "utils.h"
#include <algorithm>

void helper() {}
""")
            
            parser = IncludeParser(temp_dir)
            analyses = parser.parse_project()
            
            assert len(analyses) == 3
            assert all(isinstance(a, FileAnalysis) for a in analyses)
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_parse_nested_directories(self):
        """Test parsing nested directory structure"""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            # Create nested structure
            (temp_dir / "src").mkdir()
            (temp_dir / "include").mkdir()
            (temp_dir / "src" / "subdir").mkdir()
            
            (temp_dir / "src" / "main.cpp").write_text("#include <iostream>")
            (temp_dir / "include" / "header.h").write_text("#pragma once")
            (temp_dir / "src" / "subdir" / "file.cpp").write_text("#include <vector>")
            
            parser = IncludeParser(temp_dir)
            analyses = parser.parse_project()
            
            assert len(analyses) == 3
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_ignore_non_cpp_files(self):
        """Test that non-C++ files are ignored"""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            (temp_dir / "test.cpp").write_text("#include <iostream>")
            (temp_dir / "readme.txt").write_text("This is not C++")
            (temp_dir / "data.json").write_text("{}")
            (temp_dir / "script.py").write_text("print('hello')")
            
            parser = IncludeParser(temp_dir)
            analyses = parser.parse_project()
            
            # Should only parse .cpp file
            assert len(analyses) == 1
            assert analyses[0].filepath.endswith('.cpp')
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# Run tests if executed directly
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
