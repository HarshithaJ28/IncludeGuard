"""Integration test - Full pipeline"""
from pathlib import Path
import tempfile
import shutil
from includeguard.analyzer.parser import IncludeParser
from includeguard.analyzer.graph import DependencyGraph
from includeguard.analyzer.estimator import CostEstimator

def create_test_project():
    """Create a temporary test C++ project"""
    temp_dir = Path(tempfile.mkdtemp())
    
    # Create main.cpp
    main_cpp = temp_dir / "main.cpp"
    main_cpp.write_text("""
#include <iostream>
#include <vector>
#include <regex>
#include "utils.h"

int main() {
    std::vector<int> vec = {1, 2, 3};
    Utils::print(vec);
    return 0;
}
""")
    
    # Create utils.h
    utils_h = temp_dir / "utils.h"
    utils_h.write_text("""
#pragma once
#include <vector>
#include <iostream>
#include <string>  // Not used!

class Utils {
public:
    template<typename T>
    static void print(const std::vector<T>& vec) {
        for (const auto& item : vec) {
            std::cout << item << " ";
        }
    }
};
""")
    
    # Create unused.h
    unused_h = temp_dir / "unused.h"
    unused_h.write_text("""
#pragma once
#include <map>
#include <algorithm>

// This file is not included anywhere
""")
    
    return temp_dir

def test_full_pipeline():
    """Test the complete analysis pipeline"""
    print("\n=== Integration Test ===\n")
    
    # Create test project
    project_dir = create_test_project()
    print(f"Created test project in {project_dir}")
    
    try:
        # Step 1: Parse
        print("\n1. Parsing files...")
        parser = IncludeParser(project_dir)
        analyses = parser.parse_project()
        print(f"   Found {len(analyses)} files")
        
        for analysis in analyses:
            print(f"   - {Path(analysis.filepath).name}: {len(analysis.includes)} includes")
        
        # Step 2: Build graph
        print("\n2. Building dependency graph...")
        graph = DependencyGraph()
        graph.build(analyses)
        stats = graph.get_node_stats()
        print(f"   Nodes: {stats['total_nodes']}, Edges: {stats['total_edges']}")
        
        # Step 3: Estimate costs
        print("\n3. Estimating costs...")
        estimator = CostEstimator(graph)
        
        analysis_dict = {a.filepath: a for a in analyses}
        reports = []
        
        for analysis in analyses:
            report = estimator.generate_report(analysis, analysis_dict)
            reports.append(report)
            
            print(f"\n   {Path(analysis.filepath).name}:")
            print(f"      Total cost: {report['total_estimated_cost']:.1f}")
            print(f"      Wasted cost: {report['wasted_cost']:.1f}")
            print(f"      Potential savings: {report['potential_savings_pct']:.1f}%")
            
            if report['optimization_opportunities']:
                print(f"      Optimization opportunities:")
                for opp in report['optimization_opportunities'][:3]:
                    print(f"         - {opp['header']} (cost: {opp['estimated_cost']:.0f})")
        
        # Step 4: Project summary
        print("\n4. Project summary:")
        summary = estimator.generate_project_summary(reports)
        print(f"   Total cost: {summary['total_cost']:.1f}")
        print(f"   Total waste: {summary['total_waste']:.1f}")
        print(f"   Waste percentage: {summary['waste_percentage']:.1f}%")
        
        print("\n✓ Integration test passed!")
        
    finally:
        # Cleanup
        shutil.rmtree(project_dir)
        print(f"\nCleaned up test project")

if __name__ == '__main__':
    test_full_pipeline()
