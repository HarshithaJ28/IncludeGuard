"""
Flask API for IncludeGuard Dashboard
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from includeguard.analyzer.parser import IncludeParser
from includeguard.analyzer.graph import DependencyGraph
from includeguard.analyzer.estimator import CostEstimator
from includeguard.analyzer.forward_declaration import ForwardDeclarationDetector
from includeguard.analyzer.pch_recommender import PCHRecommender

app = Flask(__name__)
CORS(app)

# Store latest analysis
latest_analysis_data = None

@app.route('/api/analyze', methods=['POST'])
def analyze_project():
    """Analyze a C++ project"""
    global latest_analysis_data
    
    try:
        data = request.get_json()
        project_path = data.get('project_path', 'examples/sample_project')
        
        # Use default path if none provided
        if not project_path:
            project_path = Path(__file__).parent.parent.parent / 'examples' / 'sample_project'
        else:
            project_path = Path(project_path)
        
        if not project_path.exists():
            return jsonify({'error': 'Project path does not exist'}), 404
        
        # Parse files
        parser = IncludeParser(project_root=str(project_path))
        cpp_files = list(project_path.rglob('*.cpp')) + list(project_path.rglob('*.h'))
        
        analyses = []
        for file_path in cpp_files[:50]:  # Limit to 50 files
            try:
                analysis = parser.parse_file(str(file_path))
                analyses.append(analysis)
            except Exception as e:
                print(f"Error parsing {file_path}: {e}")
                continue
        
        # Build dependency graph
        graph = DependencyGraph()
        graph.build(analyses)
        
        # Estimate costs (requires graph)
        estimator = CostEstimator(graph)
        reports = []
        
        # Create a dict of all analyses for lookup
        all_analyses = {a.filepath: a for a in analyses}
        
        for analysis in analyses:
            # Analyze costs for this file
            cost_results = estimator.analyze_file_costs(analysis, all_analyses)
            
            # Calculate totals
            total_cost = sum(c['estimated_cost'] for c in cost_results)
            
            report = {
                'file': analysis.filepath,
                'includes': [inc.header for inc in analysis.includes],
                'total_lines': analysis.total_lines,
                'cost_details': cost_results,
                'total_estimated_cost': total_cost,
                'total_includes': len(analysis.includes)
            }
            
            # Find unused/low confidence headers
            unused = []
            wasted_cost = 0
            for cost_info in cost_results:
                # If not likely used or has high cost, mark as optimizable
                if not cost_info['likely_used'] or cost_info['estimated_cost'] > 1000:
                    unused.append({
                        'header': cost_info['header'],
                        'cost': cost_info['estimated_cost'],
                        'likely_used': cost_info['likely_used'],
                        'usage_confidence': cost_info['usage_confidence']
                    })
                    # Calculate waste based on usage confidence
                    waste_factor = 1.0 - cost_info['usage_confidence'] if not cost_info['likely_used'] else 0.3
                    wasted_cost += cost_info['estimated_cost'] * waste_factor
            
            report['unused_headers'] = unused
            report['wasted_cost'] = wasted_cost
            reports.append(report)
        
        # Analyze forward declarations
        fwd_detector = ForwardDeclarationDetector()
        forward_decls = []
        for report in reports:
            try:
                opportunities = fwd_detector.analyze_file(report['file'], report['includes'])
                forward_decls.extend(opportunities)
            except:
                pass
        
        # Generate PCH recommendations
        pch_recommender = PCHRecommender()
        try:
            pch_recommendations = pch_recommender.recommend_pch_headers(
                analyses, graph, estimator, min_usage_count=2, max_recommendations=10
            )
        except Exception as e:
            print(f"PCH recommendation error: {e}")
            pch_recommendations = []
        
        # Calculate summary
        try:
            graph_stats = graph.get_node_stats()
        except:
            graph_stats = {}
        
        total_files = len(reports)
        total_includes = sum(r['total_includes'] for r in reports)
        total_cost = sum(r['total_estimated_cost'] for r in reports)
        total_waste = sum(r['wasted_cost'] for r in reports)
        waste_percentage = (total_waste / total_cost * 100) if total_cost > 0 else 0
        avg_headers = total_includes / total_files if total_files > 0 else 0
        
        # Top opportunities
        opportunities = []
        for report in reports:
            for unused in report['unused_headers']:
                opportunities.append({
                    'file': Path(report['file']).name,
                    'header': unused['header'],
                    'cost': unused['cost'],
                    'line': 0
                })
        opportunities.sort(key=lambda x: x['cost'], reverse=True)
        
        # Top wasteful files
        top_wasteful = sorted(reports, key=lambda x: x['wasted_cost'], reverse=True)[:10]
        
        # Prepare response
        result = {
            'summary': {
                'totalFiles': total_files,
                'redundantHeadersTotal': len(opportunities),
                'avgHeadersPerFile': round(avg_headers, 1),
                'totalSavingsEst': f"{waste_percentage:.1f}%",
                'total_cost': total_cost,
                'total_waste': total_waste,
                'waste_percentage': waste_percentage
            },
            'opportunities': opportunities[:20],
            'wasteful_files': [
                {
                    'file': Path(r['file']).name,
                    'includes': r['total_includes'],
                    'total_cost': r['total_estimated_cost'],
                    'wasted': r['wasted_cost'],
                    'waste_pct': (r['wasted_cost'] / r['total_estimated_cost'] * 100) if r['total_estimated_cost'] > 0 else 0
                }
                for r in top_wasteful
            ],
            'forward_declarations': forward_decls[:15],
            'pch_recommendations': pch_recommendations[:10],
            'graph_stats': graph_stats,
            'chart_data': {
                'files': [Path(r['file']).name for r in reports[:10]],
                'costs': [r['total_estimated_cost'] for r in reports[:10]],
                'waste': [r['wasted_cost'] for r in reports[:10]]
            }
        }
        
        latest_analysis_data = result
        return jsonify(result)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/latest', methods=['GET'])
def get_latest():
    """Get latest analysis data"""
    if latest_analysis_data is None:
        # Analyze default project on first request
        from flask import Request
        with app.test_request_context(json={'project_path': None}):
            analyze_project()
    
    return jsonify(latest_analysis_data)

@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    print("🚀 Starting IncludeGuard API Server...")
    print("📊 API available at: http://localhost:5001")
    print("🔗 Frontend: http://localhost:3000\n")
    
    # Auto-analyze example project on startup
    try:
        with app.test_request_context(json={'project_path': None}):
            analyze_project()
        print("✅ Pre-loaded example project data\n")
    except Exception as e:
        print(f"⚠️  Could not pre-load data: {e}\n")
    
    app.run(debug=True, port=5001, host='0.0.0.0')
