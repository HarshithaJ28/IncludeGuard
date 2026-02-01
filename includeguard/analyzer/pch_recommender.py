"""
PCH Recommender - Suggest optimal precompiled header configuration
"""
from typing import List, Dict, Set
from collections import Counter
from .parser import FileAnalysis


class PCHRecommender:
    """
    Recommends headers for precompiled header (PCH) files.
    
    Precompiled headers are a compiler feature that compiles common headers
    once and reuses the compiled result across multiple translation units.
    This dramatically speeds up compilation.
    
    We want to include headers that are:
    1. Used by many files (high frequency)
    2. Expensive to compile (high cost)
    3. Rarely change (stability)
    
    The PCH score = usage_count × cost
    Higher score = better PCH candidate
    """
    
    def __init__(self):
        # System headers that are commonly used and stable (good PCH candidates)
        self.stable_system_headers = {
            '<iostream>', '<vector>', '<string>', '<map>', '<algorithm>',
            '<memory>', '<functional>', '<utility>', '<array>', '<tuple>',
            '<unordered_map>', '<set>', '<queue>', '<stack>', '<deque>',
            '<list>', '<cmath>', '<cstring>', '<cstdio>', '<cstdlib>',
            '<fstream>', '<sstream>', '<iomanip>', '<stdexcept>',
            '<type_traits>', '<chrono>', '<thread>', '<mutex>',
        }
    
    def recommend_pch_headers(self,
                             all_analyses: List[FileAnalysis],
                             graph,
                             estimator,
                             min_usage_count: int = 3,
                             max_recommendations: int = 20) -> List[Dict]:
        """
        Recommend headers for PCH based on usage frequency and cost.
        
        Args:
            all_analyses: All FileAnalysis objects
            graph: DependencyGraph
            estimator: CostEstimator
            min_usage_count: Minimum times header must be used
            max_recommendations: Maximum number of recommendations
            
        Returns:
            List of recommended headers with scores and metrics
        """
        # Count header usage across all files
        header_usage = Counter()
        header_costs = {}
        header_files = {}  # Track which files use each header
        
        for analysis in all_analyses:
            for inc in analysis.includes:
                header_key = inc.header
                header_usage[header_key] += 1
                
                # Track files using this header
                if header_key not in header_files:
                    header_files[header_key] = set()
                header_files[header_key].add(Path(analysis.filepath).name)
                
                # Get cost estimate
                if header_key not in header_costs:
                    cost = estimator.estimate_header_cost(inc.header)
                    header_costs[header_key] = cost
        
        # Calculate PCH scores
        recommendations = []
        
        for header, usage_count in header_usage.items():
            if usage_count < min_usage_count:
                continue
            
            cost = header_costs.get(header, 0)
            
            # Skip low-cost headers (not worth PCH overhead)
            if cost < 100:
                continue
            
            # PCH score = usage × cost (benefit from caching)
            pch_score = usage_count * cost
            
            # Estimate savings
            # Each file that uses this header saves the compile time
            # But subtract PCH compilation cost (amortized)
            pch_creation_cost = cost * 1.2  # PCH creation is slightly more expensive
            estimated_savings = (cost * usage_count) - pch_creation_cost
            
            # Bonus for stable system headers
            is_system = header.startswith('<')
            is_stable = header in self.stable_system_headers
            stability_bonus = 1.5 if is_stable else (1.2 if is_system else 1.0)
            
            # Adjusted score with stability
            adjusted_score = pch_score * stability_bonus
            
            recommendations.append({
                'header': header,
                'usage_count': usage_count,
                'cost': cost,
                'pch_score': adjusted_score,
                'estimated_savings': max(0, estimated_savings),
                'is_system': is_system,
                'is_stable': is_stable,
                'used_by_files': sorted(list(header_files[header]))[:5],  # Top 5 files
                'total_files_using': len(header_files[header])
            })
        
        # Sort by PCH score (highest first)
        recommendations.sort(key=lambda x: x['pch_score'], reverse=True)
        
        return recommendations[:max_recommendations]
    
    def generate_pch_file_content(self, recommendations: List[Dict], max_headers: int = 15) -> str:
        """
        Generate the actual PCH header file content.
        
        Args:
            recommendations: List of recommended headers
            max_headers: Maximum headers to include
            
        Returns:
            String content for the PCH file
        """
        lines = [
            "// Precompiled Header File",
            "// Generated by IncludeGuard",
            "//",
            "// This file should be included first in all translation units.",
            "// Compile with: g++ -x c++-header pch.h -o pch.h.gch",
            "//",
            "",
            "#ifndef PCH_H",
            "#define PCH_H",
            "",
            "// Most frequently used and expensive headers",
            ""
        ]
        
        # Add headers
        for rec in recommendations[:max_headers]:
            header = rec['header']
            usage = rec['usage_count']
            cost = rec['cost']
            lines.append(f"#include {header}  // Used by {usage} files, cost: {cost:.0f}")
        
        lines.extend([
            "",
            "#endif // PCH_H"
        ])
        
        return '\n'.join(lines)
    
    def estimate_pch_benefit(self, recommendations: List[Dict]) -> Dict:
        """
        Estimate the overall benefit of using PCH.
        
        Args:
            recommendations: List of PCH recommendations
            
        Returns:
            Dict with benefit metrics
        """
        if not recommendations:
            return {
                'total_savings': 0,
                'files_benefiting': 0,
                'estimated_speedup': 0
            }
        
        total_savings = sum(r['estimated_savings'] for r in recommendations)
        
        # Count unique files that would benefit
        all_files = set()
        for rec in recommendations:
            all_files.update(rec.get('used_by_files', []))
        
        files_benefiting = len(all_files)
        
        # Estimate speedup percentage
        # PCH typically provides 40-60% speedup for clean builds
        # and 20-30% for incremental builds
        estimated_speedup = min(60, total_savings / 1000)  # Cap at 60%
        
        return {
            'total_savings': total_savings,
            'files_benefiting': files_benefiting,
            'estimated_speedup': estimated_speedup,
            'headers_in_pch': len(recommendations)
        }


# Import Path for file tracking
from pathlib import Path
