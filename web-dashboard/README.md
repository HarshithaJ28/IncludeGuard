# IncludeGuard Web Dashboard

Full-stack web application for analyzing C++ build performance online.

## 🚀 Live Demo

**Frontend**: https://includeguard.vercel.app (deploy yours)  
**API Docs**: https://includeguard-api.railway.app/docs (deploy yours)

## 📋 Architecture

```
web-dashboard/
├── frontend/          # React + TypeScript + Tailwind CSS
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api.ts
│   │   └── components/
│   └── package.json
│
└── backend/           # FastAPI + Python
    ├── main.py        # API server with WebSocket
    ├── requirements.txt
    └── README.md
```

## 🎯 Features

### Frontend
- Drag-and-drop file upload
- GitHub repository URL input
- Real-time progress via WebSocket
- Interactive charts and metrics
- Responsive design
- Download HTML reports

### Backend
- File upload handling
- GitHub repository cloning
- Background analysis processing
- WebSocket progress updates
- JSON API responses
- HTML report generation

## 🛠️ Local Development

### Prerequisites
- Node.js 18+
- Python 3.9+
- Git

### Setup

**1. Start Backend**
```bash
cd backend
pip install -r requirements.txt
python main.py
# Server runs at http://localhost:8000
```

**2. Start Frontend**
```bash
cd frontend
npm install
npm run dev
# App runs at http://localhost:5173
```

**3. Test**
- Open http://localhost:5173
- Upload a C++ project or paste GitHub URL
- Watch real-time analysis progress
- View results!

## 🌐 Deployment

### Frontend → Vercel (Free)

1. Push to GitHub
2. Go to [vercel.com](https://vercel.com)
3. New Project → Import your repo
4. Root directory: `web-dashboard/frontend`
5. Add env var: `VITE_API_URL=https://your-backend.railway.app`
6. Deploy!

### Backend → Railway (Free)

1. Go to [railway.app](https://railway.app)
2. New Project → Deploy from GitHub
3. Root directory: `web-dashboard/backend`
4. Railway auto-detects Python and deploys
5. Copy your backend URL (e.g., `https://includeguard-api.railway.app`)
6. Update frontend env var with this URL

**Alternative**: Use Render.com for backend (also free)

## 📊 API Endpoints

### File Upload
```bash
POST /api/analyze/upload
Content-Type: multipart/form-data

Response: { "job_id": "abc-123", "websocket_url": "/ws/abc-123" }
```

### GitHub Analysis
```bash
POST /api/analyze/github
Content-Type: application/json
Body: { "repo_url": "https://github.com/user/repo" }

Response: { "job_id": "def-456", "websocket_url": "/ws/def-456" }
```

### Check Status
```bash
GET /api/status/{job_id}

Response: {
  "status": "completed",
  "progress": 100,
  "message": "Analysis complete!",
  "result": { ... }
}
```

### WebSocket Updates
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/{job_id}');
ws.onmessage = (event) => {
  const status = JSON.parse(event.data);
  console.log(status.progress); // 0-100
};
```

## 💡 Usage Example

```typescript
import { api } from './api';

// Upload file
const file = document.querySelector('input[type="file"]').files[0];
const response = await api.analyzeUpload(file);

// Connect to WebSocket
const ws = new WebSocket(api.getWebSocketUrl(response.job_id));
ws.onmessage = (event) => {
  const status = JSON.parse(event.data);
  updateProgress(status.progress);
  if (status.status === 'completed') {
    displayResults(status.result);
  }
};
```

## 🔧 Environment Variables

**Frontend** (`.env`):
```env
VITE_API_URL=http://localhost:8000
```

**Backend** (optional `.env`):
```env
PORT=8000
HOST=0.0.0.0
ALLOWED_ORIGINS=http://localhost:5173,https://yourdomain.com
```

## 📝 Tech Stack

**Frontend**:
- React 19 + TypeScript
- Vite (build tool)
- Tailwind CSS (styling)
- Lucide React (icons)
- Recharts (charts)
- Axios (HTTP)
- WebSocket API

**Backend**:
- FastAPI (Python web framework)
- Uvicorn (ASGI server)
- GitPython (repo cloning)
- WebSockets (real-time updates)
- IncludeGuard CLI (analysis engine)

## 🐛 Troubleshooting

**CORS Errors**:
- Update `allow_origins` in `backend/main.py`
- Add your frontend URL to the list

**WebSocket Connection Failed**:
- Check if backend is running
- Verify WebSocket URL (ws:// for http, wss:// for https)
- Frontend falls back to polling automatically

**Analysis Fails**:
- Check backend logs: `python main.py`
- Ensure IncludeGuard CLI is installed
- Verify Python path in backend

## 📄 License

MIT - Same as main IncludeGuard project
