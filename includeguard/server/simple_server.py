"""
Simple Flask server to serve the IncludeGuard dashboard
"""

from flask import Flask, send_file, jsonify
from flask_cors import CORS
from pathlib import Path

app = Flask(__name__)
CORS(app)

# Path to the dashboard HTML
DASHBOARD_PATH = Path(__file__).parent.parent / 'ui' / 'dashboard.html'

@app.route('/')
def serve_dashboard():
    """Serve the main dashboard"""
    return send_file(DASHBOARD_PATH)

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'IncludeGuard Dashboard'})

if __name__ == '__main__':
    print("🚀 Starting IncludeGuard Dashboard...")
    print("📊 Dashboard available at: http://localhost:5000")
    print("Press Ctrl+C to stop the server\n")
    app.run(debug=False, port=5000, host='0.0.0.0')
