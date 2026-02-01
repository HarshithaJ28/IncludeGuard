"""
HTML Report Generator - Creates beautiful interactive reports
"""
from pathlib import Path
from typing import List, Dict
import json

class HTMLReportGenerator:
    """Generate interactive HTML reports with charts"""
    
    def generate(self, 
                reports: List[Dict],
                summary: Dict,
                graph_stats: Dict,
                output_path: str,
                forward_decls: List[Dict] = None,
                pch_recommendations: List[Dict] = None):
        """
        Generate complete HTML report.
        
        Args:
            reports: List of file reports
            summary: Project summary
            graph_stats: Graph statistics
            output_path: Where to save HTML file
            forward_decls: Forward declaration opportunities
            pch_recommendations: PCH recommendations
        """
        html = self._generate_html(reports, summary, graph_stats, 
                                   forward_decls or [], 
                                   pch_recommendations or [])
        Path(output_path).write_text(html, encoding='utf-8')
        print(f"HTML report saved to: {output_path}")
    
    def _generate_html(self, reports, summary, graph_stats, forward_decls, pch_recommendations):
        """Generate the HTML content"""
        
        # Prepare data for charts
        top_files = summary['top_wasteful_files'][:10]
        file_names = [Path(f['file']).name for f in top_files]
        file_costs = [f['total_estimated_cost'] for f in top_files]
        file_waste = [f['wasted_cost'] for f in top_files]
        
        # Top opportunities
        opportunities = summary['top_opportunities'][:20]
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IncludeGuard Analysis Report</title>
    <script src="https://cdn.plot.ly/plotly-2.18.0.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            padding: 20px;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        header {{
            text-align: center;
            padding: 40px 0;
            border-bottom: 2px solid #00d4ff;
            margin-bottom: 40px;
        }}
        
        h1 {{
            font-size: 3em;
            color: #00d4ff;
            margin-bottom: 10px;
            text-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
        }}
        
        .subtitle {{
            color: #aaa;
            font-size: 1.2em;
        }}
        
        .card {{
            background: rgba(22, 33, 62, 0.8);
            backdrop-filter: blur(10px);
            padding: 30px;
            margin: 20px 0;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(0, 212, 255, 0.1);
        }}
        
        .card h2 {{
            color: #00d4ff;
            margin-bottom: 20px;
            font-size: 1.8em;
            border-bottom: 2px solid rgba(0, 212, 255, 0.3);
            padding-bottom: 10px;
        }}
        
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        
        .metric {{
            text-align: center;
            padding: 20px;
            background: rgba(0, 212, 255, 0.05);
            border-radius: 10px;
            border: 1px solid rgba(0, 212, 255, 0.2);
        }}
        
        .metric-value {{
            font-size: 2.5em;
            color: #00d4ff;
            font-weight: bold;
            display: block;
            margin-bottom: 5px;
        }}
        
        .metric-label {{
            color: #aaa;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        
        th {{
            background: rgba(0, 212, 255, 0.1);
            padding: 15px;
            text-align: left;
            color: #00d4ff;
            font-weight: 600;
            border-bottom: 2px solid rgba(0, 212, 255, 0.3);
        }}
        
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}
        
        tr:hover {{
            background: rgba(0, 212, 255, 0.03);
        }}
        
        .cost-high {{
            color: #ff6b6b;
            font-weight: bold;
        }}
        
        .cost-medium {{
            color: #ffa500;
        }}
        
        .cost-low {{
            color: #4ecdc4;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }}
        
        .badge-danger {{
            background: rgba(255, 107, 107, 0.2);
            color: #ff6b6b;
            border: 1px solid #ff6b6b;
        }}
        
        .badge-warning {{
            background: rgba(255, 165, 0, 0.2);
            color: #ffa500;
            border: 1px solid #ffa500;
        }}
        
        .badge-success {{
            background: rgba(78, 205, 196, 0.2);
            color: #4ecdc4;
            border: 1px solid #4ecdc4;
        }}
        
        .chart-container {{
            background: rgba(255, 255, 255, 0.03);
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }}
        
        code {{
            background: rgba(0, 0, 0, 0.3);
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            color: #ffa500;
        }}
        
        .recommendation {{
            background: rgba(255, 165, 0, 0.1);
            border-left: 4px solid #ffa500;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
        }}
        
        .recommendation-title {{
            color: #ffa500;
            font-weight: 600;
            margin-bottom: 5px;
        }}
        
        footer {{
            text-align: center;
            padding: 40px 0;
            margin-top: 60px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🛡️ IncludeGuard</h1>
            <div class="subtitle">C++ Include Analysis Report</div>
        </header>
        
        <!-- Summary Metrics -->
        <div class="card">
            <h2>📊 Project Summary</h2>
            <div class="metrics">
                <div class="metric">
                    <span class="metric-value">{summary['total_files']}</span>
                    <span class="metric-label">Files Analyzed</span>
                </div>
                <div class="metric">
                    <span class="metric-value">{summary['total_includes']:,}</span>
                    <span class="metric-label">Total Includes</span>
                </div>
                <div class="metric">
                    <span class="metric-value">{summary['total_cost']:,.0f}</span>
                    <span class="metric-label">Total Cost</span>
                </div>
                <div class="metric">
                    <span class="metric-value" style="color: #ff6b6b">{summary['total_waste']:,.0f}</span>
                    <span class="metric-label">Wasted Cost</span>
                </div>
                <div class="metric">
                    <span class="metric-value" style="color: #ffa500">{summary['waste_percentage']:.1f}%</span>
                    <span class="metric-label">Waste Percentage</span>
                </div>
                <div class="metric">
                    <span class="metric-value">{graph_stats['cycles']}</span>
                    <span class="metric-label">Circular Deps</span>
                </div>
            </div>
        </div>
        
        <!-- Cost Distribution Chart -->
        <div class="card">
            <h2>💰 Cost Distribution by File</h2>
            <div class="chart-container">
                <div id="cost-chart"></div>
            </div>
        </div>
        
        <!-- Waste Chart -->
        <div class="card">
            <h2>📉 Wasted Cost by File</h2>
            <div class="chart-container">
                <div id="waste-chart"></div>
            </div>
        </div>
        
        <!-- Top Opportunities -->
        <div class="card">
            <h2>🎯 Top Optimization Opportunities</h2>
            <p style="color: #aaa; margin-bottom: 20px;">
                Remove these unused includes to reduce build time:
            </p>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>File</th>
                        <th>Unused Header</th>
                        <th>Estimated Cost</th>
                        <th>Line</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        # Add opportunities rows
        for i, opp in enumerate(opportunities, 1):
            cost = opp['cost']
            cost_class = 'cost-high' if cost > 2000 else 'cost-medium' if cost > 1000 else 'cost-low'
            badge_class = 'badge-danger' if cost > 2000 else 'badge-warning' if cost > 1000 else 'badge-success'
            
            html += f"""
                    <tr>
                        <td>{i}</td>
                        <td><code>{opp['file']}</code></td>
                        <td><code>{opp['header']}</code></td>
                        <td class="{cost_class}">{cost:.0f}</td>
                        <td>{opp['line']}</td>
                        <td><span class="{badge_class}">Remove</span></td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
        </div>
        
        <!-- Most Wasteful Files -->
        <div class="card">
            <h2>📁 Most Wasteful Files</h2>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>File</th>
                        <th>Includes</th>
                        <th>Total Cost</th>
                        <th>Wasted Cost</th>
                        <th>Waste %</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        # Add wasteful files
        for i, report in enumerate(top_files, 1):
            filename = Path(report['file']).name
            waste_pct = report['potential_savings_pct']
            badge = 'badge-danger' if waste_pct > 50 else 'badge-warning' if waste_pct > 25 else 'badge-success'
            
            html += f"""
                    <tr>
                        <td>{i}</td>
                        <td><code>{filename}</code></td>
                        <td>{report['total_includes']}</td>
                        <td>{report['total_estimated_cost']:.0f}</td>
                        <td class="cost-high">{report['wasted_cost']:.0f}</td>
                        <td><span class="{badge}">{waste_pct:.1f}%</span></td>
                    </tr>
"""
        
        html += f"""
                </tbody>
            </table>
        </div>
"""
        
        # Forward Declaration Opportunities
        if forward_decls:
            html += """
        <!-- Forward Declaration Opportunities -->
        <div class="card">
            <h2>💡 Forward Declaration Opportunities</h2>
            <p style="color: #aaa; margin-bottom: 20px;">
                Replace expensive includes with forward declarations when only using pointers/references:
            </p>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>File</th>
                        <th>Replace Include</th>
                        <th>With Forward Decl</th>
                        <th>Confidence</th>
                    </tr>
                </thead>
                <tbody>
"""
            
            for i, opp in enumerate(forward_decls[:15], 1):
                conf = opp['confidence']
                badge_class = 'badge-success' if conf > 0.7 else 'badge-warning' if conf > 0.5 else 'badge-secondary'
                
                html += f"""
                    <tr>
                        <td>{i}</td>
                        <td><code>{opp['file']}</code></td>
                        <td><code>#include "{opp['header']}"</code></td>
                        <td><code style="color: #51cf66">{opp['suggestion']}</code></td>
                        <td><span class="{badge_class}">{conf:.0%}</span></td>
                    </tr>
"""
            
            html += """
                </tbody>
            </table>
            <div style="margin-top: 15px; padding: 10px; background: rgba(81, 207, 102, 0.1); border-left: 3px solid #51cf66; border-radius: 5px;">
                <strong>💡 Tip:</strong> Forward declarations work when you only use pointers/references. 
                This can dramatically reduce compile times by avoiding expensive template header parsing.
            </div>
        </div>
"""
        
        # PCH Recommendations
        if pch_recommendations:
            html += """
        <!-- Precompiled Header Recommendations -->
        <div class="card">
            <h2>🔧 Precompiled Header (PCH) Recommendations</h2>
            <p style="color: #aaa; margin-bottom: 20px;">
                These headers are used frequently and expensive to compile. Consider adding them to a precompiled header:
            </p>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Header</th>
                        <th>Used By</th>
                        <th>Cost</th>
                        <th>PCH Score</th>
                        <th>Est. Savings</th>
                    </tr>
                </thead>
                <tbody>
"""
            
            for i, rec in enumerate(pch_recommendations[:15], 1):
                score = rec['pch_score']
                badge_class = 'badge-danger' if score > 10000 else 'badge-warning'
                
                html += f"""
                    <tr>
                        <td>{i}</td>
                        <td><code>{rec['header']}</code></td>
                        <td>{rec['usage_count']} files</td>
                        <td>{rec['cost']:.0f}</td>
                        <td><span class="{badge_class}">{score:.0f}</span></td>
                        <td class="cost-low">{rec['estimated_savings']:.0f}</td>
                    </tr>
"""
            
            html += """
                </tbody>
            </table>
            
            <div style="margin-top: 20px; padding: 15px; background: rgba(138, 80, 243, 0.1); border-left: 3px solid #8a50f7; border-radius: 5px;">
                <strong>📚 Suggested PCH File (pch.h):</strong>
                <pre style="margin-top: 10px; padding: 10px; background: rgba(0,0,0,0.3); border-radius: 5px; overflow-x: auto;">
<code style="color: #51cf66;">// Precompiled Header
#ifndef PCH_H
#define PCH_H

"""
            
            # Add top headers to PCH file
            for rec in pch_recommendations[:10]:
                html += f"""// Used by {rec['usage_count']} files, cost: {rec['cost']:.0f}
#include {rec['header']}
"""
            
            html += """
#endif // PCH_H
</code></pre>
                <p style="margin-top: 10px; color: #aaa; font-size: 0.9em;">
                    Compile with: <code style="color: #00d4ff;">g++ -x c++-header pch.h -o pch.h.gch</code><br>
                    Then use in your build with: <code style="color: #00d4ff;">-include pch.h</code>
                </p>
            </div>
        </div>
"""
        
        html += """
        
        <!-- Recommendations -->
        <div class="card">
            <h2>💡 Recommendations</h2>
            
            <div class="recommendation">
                <div class="recommendation-title">1. Remove Unused Includes</div>
                <div>Focus on the top {min(10, len(opportunities))} opportunities listed above. 
                These have the highest cost and are likely unused.</div>
            </div>
            
            <div class="recommendation">
                <div class="recommendation-title">2. Use Forward Declarations</div>
                <div>For headers only used as pointers/references, consider forward declarations 
                instead of full includes.</div>
            </div>
            
            <div class="recommendation">
                <div class="recommendation-title">3. Reduce Transitive Dependencies</div>
                <div>Headers with deep dependency trees ({graph_stats['max_depth']} max depth found) 
                are expensive. Consider splitting them.</div>
            </div>
            
            <div class="recommendation">
                <div class="recommendation-title">4. Fix Circular Dependencies</div>
                <div>Found {graph_stats['cycles']} circular dependencies. These can cause compilation 
                issues and slow builds.</div>
            </div>
        </div>
        
        <footer>
            Generated by IncludeGuard v0.1.0 | 
            <a href="https://github.com/HarshithaJ28/IncludeGuard" style="color: #00d4ff;">GitHub</a>
        </footer>
    </div>
    
    <script>
        // Cost distribution chart
        var costData = [{{
            values: {file_costs},
            labels: {file_names},
            type: 'pie',
            hole: 0.4,
            marker: {{
                colors: ['#ff6b6b', '#ee5a6f', '#f06595', '#cc5de8', '#845ef7', 
                         '#5c7cfa', '#339af0', '#22b8cf', '#20c997', '#51cf66']
            }},
            textinfo: 'label+percent',
            textposition: 'outside',
            automargin: true
        }}];
        
        var costLayout = {{
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: {{ color: '#eee', size: 12 }},
            showlegend: false,
            height: 500,
            margin: {{ t: 20, b: 20, l: 20, r: 20 }}
        }};
        
        Plotly.newPlot('cost-chart', costData, costLayout, {{responsive: true}});
        
        // Waste bar chart
        var wasteData = [{{
            x: {file_names},
            y: {file_waste},
            type: 'bar',
            marker: {{
                color: '#ff6b6b',
                line: {{
                    color: '#cc5555',
                    width: 1
                }}
            }}
        }}];
        
        var wasteLayout = {{
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: {{ color: '#eee' }},
            xaxis: {{
                tickangle: -45,
                gridcolor: 'rgba(255,255,255,0.1)'
            }},
            yaxis: {{
                title: 'Wasted Cost',
                gridcolor: 'rgba(255,255,255,0.1)'
            }},
            height: 400,
            margin: {{ t: 20, b: 100, l: 60, r: 20 }}
        }};
        
        Plotly.newPlot('waste-chart', wasteData, wasteLayout, {{responsive: true}});
    </script>
</body>
</html>
"""
        
        return html
