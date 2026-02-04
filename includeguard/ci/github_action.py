"""
GitHub Actions integration for IncludeGuard

Generates PR comments and checks quality thresholds for CI/CD pipelines.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def generate_pr_comment(analysis_data: Dict) -> str:
    """
    Generate markdown comment for GitHub PR.
    
    Args:
        analysis_data: JSON analysis results from IncludeGuard
        
    Returns:
        Markdown formatted comment for PR
    """
    summary = analysis_data.get('summary', {})
    reports = analysis_data.get('reports', [])
    
    # Build header with overall stats
    total_cost = summary.get('total_cost', 0)
    total_waste = summary.get('total_waste', 0)
    waste_pct = summary.get('waste_percentage', 0)
    total_files = summary.get('total_files', 0)
    
    comment = f"""## 📊 IncludeGuard Analysis

**Build Impact**: {total_cost:,.0f} cost units  
**Potential Waste**: {total_waste:,.0f} units ({waste_pct:.1f}%)  
**Files Analyzed**: {total_files}

"""
    
    # Get top opportunities
    opportunities = summary.get('top_opportunities', [])[:15]
    
    if not opportunities:
        comment += "### ✅ No issues found!\n\n"
        comment += "All includes appear necessary and optimized.\n"
        comment += "\n---\n"
        comment += "*🛡️ Analyzed by [IncludeGuard](https://github.com/HarshithaJ28/IncludeGuard)*\n"
        return comment
    
    # Issues section - group by severity
    comment += "### ⚠️ Issues Found\n\n"
    
    # High priority (cost > 1500)
    high_cost = [o for o in opportunities if o.get('cost', 0) > 1500]
    if high_cost:
        comment += f"**🔴 High Priority ({len(high_cost)} unused includes)**\n"
        for opp in high_cost[:5]:
            file = opp.get('file', 'unknown')
            line = opp.get('line', 0)
            header = opp.get('header', 'unknown')
            cost = opp.get('cost', 0)
            comment += f"- `{file}` line {line}: `{header}` (cost: {cost:.0f}) - unused\n"
        if len(high_cost) > 5:
            comment += f"- ... and {len(high_cost) - 5} more high-priority issues\n"
        comment += "\n"
    
    # Medium priority (cost 500-1500)
    medium_cost = [o for o in opportunities if 500 < o.get('cost', 0) <= 1500]
    if medium_cost:
        comment += f"**🟡 Medium Priority ({len(medium_cost)} unused includes)**\n"
        for opp in medium_cost[:3]:
            file = opp.get('file', 'unknown')
            line = opp.get('line', 0)
            header = opp.get('header', 'unknown')
            cost = opp.get('cost', 0)
            comment += f"- `{file}` line {line}: `{header}` (cost: {cost:.0f})\n"
        if len(medium_cost) > 3:
            comment += f"- ... and {len(medium_cost) - 3} more medium-priority issues\n"
        comment += "\n"
    
    # Forward declaration opportunities
    fwd_decls = analysis_data.get('forward_declarations', [])[:5]
    if fwd_decls:
        comment += f"**💡 Forward Declaration Opportunities ({len(fwd_decls)})**\n"
        for fwd in fwd_decls:
            file = fwd.get('file', 'unknown')
            header = fwd.get('header', 'unknown')
            suggestion = fwd.get('suggestion', '')
            confidence = fwd.get('confidence', 0)
            comment += f"- `{file}`: Replace `#include \"{header}\"` "
            comment += f"with `{suggestion}` (confidence: {confidence:.0%})\n"
        comment += "\n"
    
    # PCH recommendations
    pch_recommendations = analysis_data.get('pch_recommendations', [])
    if pch_recommendations and len(pch_recommendations) > 0:
        comment += f"**⚡ Precompiled Header Candidates ({len(pch_recommendations)})**\n"
        for pch in pch_recommendations[:3]:
            header = pch.get('header', 'unknown')
            usage_count = pch.get('usage_count', 0)
            total_cost = pch.get('total_cost', 0)
            comment += f"- `{header}`: Used in {usage_count} files (total cost: {total_cost:.0f})\n"
        comment += "\n"
    
    # Action items / recommendations
    comment += "### ✅ Action Items\n\n"
    
    total_savings = sum(o.get('cost', 0) for o in opportunities)
    
    if high_cost or medium_cost:
        total_removable = len(high_cost) + len(medium_cost)
        comment += f"1. **Remove {total_removable} unnecessary includes**\n"
        comment += f"   - Estimated savings: {total_savings:,.0f} cost units\n"
    
    if fwd_decls:
        comment += f"2. **Apply {len(fwd_decls)} forward declarations**\n"
        comment += f"   - Further reduce compile dependencies\n"
    
    if pch_recommendations:
        comment += f"3. **Consider precompiled headers**\n"
        comment += f"   - {len(pch_recommendations)} frequently-used headers identified\n"
    
    comment += f"\n**Overall potential improvement: -{waste_pct:.1f}% build time**\n\n"
    
    # Auto-fix suggestion
    comment += "### 🔧 Automated Fixes Available\n\n"
    comment += "Generate an auto-fix patch:\n"
    comment += "```bash\n"
    comment += "includeguard fix-generate . --output fixes.patch\n"
    comment += "git apply fixes.patch\n"
    comment += "```\n\n"
    
    # Footer
    comment += "---\n"
    comment += "*🛡️ Analyzed by [IncludeGuard](https://github.com/HarshithaJ28/IncludeGuard) "
    comment += "| [View detailed report](../../../actions)*\n"
    
    return comment


def check_thresholds(analysis_data: Dict) -> Tuple[bool, List[str]]:
    """
    Check if analysis results exceed acceptable thresholds.
    
    Args:
        analysis_data: JSON analysis results
        
    Returns:
        Tuple of (passing: bool, messages: List[str])
    """
    summary = analysis_data.get('summary', {})
    waste_pct = summary.get('waste_percentage', 0)
    opportunities = summary.get('top_opportunities', [])
    
    # Configurable thresholds
    MAX_WASTE_PERCENTAGE = 50.0  # Fail if >50% waste
    MAX_HIGH_COST_UNUSED = 5      # Fail if >5 high-cost unused headers
    
    messages = []
    passing = True
    
    # Check waste percentage
    if waste_pct > MAX_WASTE_PERCENTAGE:
        messages.append(
            f"❌ FAIL: Waste percentage {waste_pct:.1f}% exceeds threshold {MAX_WASTE_PERCENTAGE}%"
        )
        passing = False
    else:
        messages.append(
            f"✅ PASS: Waste percentage {waste_pct:.1f}% (threshold: {MAX_WASTE_PERCENTAGE}%)"
        )
    
    # Check high-cost unused includes
    high_cost_unused = len([o for o in opportunities if o.get('cost', 0) > 1500])
    if high_cost_unused > MAX_HIGH_COST_UNUSED:
        messages.append(
            f"❌ FAIL: {high_cost_unused} high-cost unused headers exceeds threshold {MAX_HIGH_COST_UNUSED}"
        )
        passing = False
    else:
        messages.append(
            f"✅ PASS: High-cost unused headers: {high_cost_unused} (threshold: {MAX_HIGH_COST_UNUSED})"
        )
    
    return passing, messages


def main():
    """Command-line entry point for CI/CD integration"""
    if len(sys.argv) < 2:
        print("Usage: python github_action.py <analysis.json>")
        sys.exit(1)
    
    # Read analysis results
    analysis_file = Path(sys.argv[1])
    if not analysis_file.exists():
        print(f"Error: {analysis_file} not found")
        sys.exit(1)
    
    with open(analysis_file) as f:
        analysis_data = json.load(f)
    
    # Generate comment
    comment = generate_pr_comment(analysis_data)
    
    # Write to file for GitHub Actions to read
    output_file = Path('pr_comment.md')
    if len(sys.argv) > 2:
        output_file = Path(sys.argv[2])
    
    with open(output_file, 'w') as f:
        f.write(comment)
    
    print("Generated PR comment:")
    print("=" * 60)
    print(comment)
    print("=" * 60)
    
    # Check thresholds (exit code determines PR status)
    passing, messages = check_thresholds(analysis_data)
    
    print("\nThreshold Check Results:")
    for msg in messages:
        print(msg)
    
    if passing:
        print("\n✅ All thresholds passed")
        sys.exit(0)  # Pass
    else:
        print("\n❌ Some thresholds failed - review recommended")
        sys.exit(1)  # Fail


if __name__ == '__main__':
    main()
