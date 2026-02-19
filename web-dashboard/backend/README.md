# IncludeGuard API Backend

FastAPI backend for real-time C++ include analysis with WebSocket support.

## Features

- 📤 **File Upload**: Upload zip files or individual C++ files
- 🔗 **GitHub Integration**: Analyze any public GitHub repository
- ⚡ **Real-time Updates**: WebSocket for live progress tracking
- 📊 **JSON API**: RESTful endpoints for all operations
- 🚀 **Async Processing**: Background tasks with progress updates

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python main.py

# Server runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### API Endpoints

- `POST /api/analyze/upload` - Upload files for analysis
- `POST /api/analyze/github` - Analyze GitHub repository
- `GET /api/status/{job_id}` - Get analysis status
- `GET /api/report/{job_id}` - Download HTML report
- `WS /ws/{job_id}` - WebSocket for real-time updates

### Example Usage

```python
import requests

# Upload file
files = {'file': open('project.zip', 'rb')}
response = requests.post('http://localhost:8000/api/analyze/upload', files=files)
job_id = response.json()['job_id']

# Check status
status = requests.get(f'http://localhost:8000/api/status/{job_id}')
print(status.json())
```

## Deployment

### Railway

1. Connect GitHub repository
2. Set root directory to `web-dashboard/backend`
3. Railway auto-detects Python and installs dependencies
4. Exposes port 8000 automatically

### Docker

```bash
docker build -t includeguard-api .
docker run -p 8000:8000 includeguard-api
```

## Architecture

```
FastAPI Server
├── File Upload Handler → Temp Storage
├── GitHub Clone Handler → Git Operations
├── Background Tasks → CLI Analysis
├── WebSocket Manager → Real-time Updates
└── Result Storage → JSON + HTML Reports
```
