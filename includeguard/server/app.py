"""
Flask Web Server for IncludeGuard Dashboard
Serves the React frontend and provides REST API for analysis data
"""

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from pathlib import Path
import json
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from includeguard.parser.cpp_parser import CppParser
from includeguard.analyzer.dependency_graph import DependencyGraph
from includeguard.analyzer.cost_estimator import SimpleCostEstimator
from includeguard.analyzer.forward_declaration import ForwardDeclarationDetector
from includeguard.analyzer.pch_recommender import PCHRecommender

app = Flask(__name__, static_folder='../../sample_frontend/dist')
CORS(app)

# Store latest analysis results
latest_analysis = {}

@app.route('/')
def serve_frontend():
    """Serve the React frontend"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory(app.static_folder, path)

@app.route('/api/analyze', methods=['POST'])
def analyze_project():
    """
    Analyze a C++ project
    Expected JSON: { "project_path": "/path/to/project" }
    """
    try:
        data = request.get_json()
        project_path = data.get('project_path')
        
        if not project_path:
            return jsonify({'error': 'project_path is required'}), 400
        
        project_path = Path(project_path)
        if not project_path.exists():
            return jsonify({'error': 'Project path does not exist'}), 404
        
        # Parse C++ files
        parser = CppParser()
        cpp_files = list(project_path.rglob('*.cpp')) + list(project_path.rglob('*.h'))
        
        reports = []
        for file_path in cpp_files:
            report = parser.parse_file(str(file_path))
            reports.append(report)
        
        # Build dependency graph
        graph = DependencyGraph()
        for report in reports:
            graph.add_file(report['file'], report['includes'])
        
        # Estimate costs
        estimator = SimpleCostEstimator()
        for report in reports:
            costs = estimator.estimate_costs(report['includes'])
            report['estimated_costs'] = costs
            report['total_estimated_cost'] = sum(costs.values())
            report['total_includes'] = len(report['includes'])
        
        # Analyze forward declarations
        fwd_detector = ForwardDeclarationDetector()
        forward_decls = []
        for report in reports:
            opportunities = fwd_detector.analyze_file(
                report['file'],
                report['includes']
            )
            forward_decls.extend(opportunities)
        
        # Generate PCH recommendations
        pch_recommender = PCHRecommender()
        for report in reports:
            for header in report['includes']:
                cost = report['estimated_costs'].get(header, 0)
                pch_recommender.add_header_usage(header, report['file'], cost)
        
        pch_recommendations = pch_recommender.get_recommendations()
        
        # Generate summary
        graph_stats = graph.get_statistics()
        
        total_files = len(reports)
        total_includes = sum(r['total_includes'] for r in reports)
        total_cost = sum(r['total_estimated_cost'] for r in reports)
        
        # Calculate waste
        for report in reports:
            used_symbols = report.get('used_symbols', set())
            unused = []
            wasted_cost = 0
            
            for include in report['includes']:
                # Simple heuristic: if no symbols from this header are used, it's wasteful
                if not any(sym.startswith(include.replace('.h', '').replace('.hpp', '')) for sym in used_symbols):
                    cost = report['estimated_costs'].get(include, 0)
                    unused.append({'header': include, 'cost': cost})
                    wasted_cost += cost
            
            report['unused_headers'] = unused
            report['wasted_cost'] = wasted_cost
        
        total_waste = sum(r['wasted_cost'] for r in reports)
        waste_percentage = (total_waste / total_cost * 100) if total_cost > 0 else 0
        
        # Top opportunities
        opportunities = []
        for report in reports:
            for unused in report['unused_headers']:
                opportunities.append({
                    'file': report['file'],
                    'header': unused['header'],
                    'cost': unused['cost'],
                    'line': 0  # Would need to parse file to get exact line
                })
        
        opportunities.sort(key=lambda x: x['cost'], reverse=True)
        
        # Top wasteful files
        top_wasteful = sorted(reports, key=lambda x: x['wasted_cost'], reverse=True)[:10]
        
        summary = {
            'total_files': total_files,
            'total_includes': total_includes,
            'total_cost': total_cost,
            'total_waste': total_waste,
            'waste_percentage': waste_percentage,
            'top_opportunities': opportunities[:20],
            'top_wasteful_files': [
                {
                    'file': r['file'],
                    'total_includes': r['total_includes'],
                    'total_estimated_cost': r['total_estimated_cost'],
                    'wasted_cost': r['wasted_cost'],
                    'potential_savings_pct': (r['wasted_cost'] / r['total_estimated_cost'] * 100) if r['total_estimated_cost'] > 0 else 0
                }
                for r in top_wasteful
            ]
        }
        
        result = {
            'summary': summary,
            'graph_stats': graph_stats,
            'forward_declarations': forward_decls[:15],
            'pch_recommendations': pch_recommendations[:10],
            'reports': reports
        }
        
        global latest_analysis
        latest_analysis = result
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/latest')
def get_latest_analysis():
    """Get the latest analysis results"""
    if not latest_analysis:
        return jsonify({'error': 'No analysis available'}), 404
    
    return jsonify(latest_analysis)

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'IncludeGuard API'})

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
