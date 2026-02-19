"""
IncludeGuard Web Dashboard - FastAPI Backend
Real-time C++ include analysis API with WebSocket support
"""

from fastapi import FastAPI, UploadFile, File, WebSocket, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
import asyncio
import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
import zipfile
import git
from datetime import datetime

app = FastAPI(
    title="IncludeGuard API",
    description="Real-time C++ include analysis and optimization recommendations",
    version="1.0.0"
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "*"  # In production, specify your frontend domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for analysis jobs (use Redis in production)
analysis_jobs = {}

# Temporary directory for uploads
UPLOAD_DIR = Path(tempfile.gettempdir()) / "includeguard_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

class AnalysisRequest(BaseModel):
    repo_url: Optional[HttpUrl] = None
    project_name: Optional[str] = None

class AnalysisStatus(BaseModel):
    job_id: str
    status: str  # "queued", "running", "completed", "failed"
    progress: int  # 0-100
    message: str
    result: Optional[dict] = None

@app.get("/")
async def root():
    """API health check"""
    return {
        "service": "IncludeGuard API",
        "status": "online",
        "version": "1.0.0",
        "endpoints": {
            "analyze_upload": "/api/analyze/upload",
            "analyze_github": "/api/analyze/github",
            "status": "/api/status/{job_id}",
            "report": "/api/report/{job_id}",
            "websocket": "/ws/{job_id}"
        }
    }

@app.get("/favicon.ico")
async def favicon():
    """Return 204 No Content for favicon requests"""
    from fastapi.responses import Response
    return Response(status_code=204)

@app.post("/api/analyze/upload")
async def analyze_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload C++ project (zip or individual files) for analysis
    Returns job_id to track progress via WebSocket
    """
    job_id = str(uuid.uuid4())
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Save uploaded file
        file_path = job_dir / file.filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Extract if zip
        if file.filename.endswith('.zip'):
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(job_dir / "project")
            analyze_path = job_dir / "project"
        else:
            analyze_path = job_dir
        
        # Initialize job status
        analysis_jobs[job_id] = {
            "status": "queued",
            "progress": 0,
            "message": "Analysis queued",
            "created_at": datetime.now().isoformat(),
            "project_path": str(analyze_path)
        }
        
        # Start analysis in background
        background_tasks.add_task(run_analysis, job_id, analyze_path)
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Analysis started. Connect to WebSocket for real-time updates.",
            "websocket_url": f"/ws/{job_id}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/api/analyze/github")
async def analyze_github(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks
):
    """
    Clone GitHub repository and analyze
    Supports public repos without authentication
    """
    if not request.repo_url:
        raise HTTPException(status_code=400, detail="repo_url is required")
    
    job_id = str(uuid.uuid4())
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Initialize job status
        analysis_jobs[job_id] = {
            "status": "cloning",
            "progress": 5,
            "message": f"Cloning {request.repo_url}...",
            "created_at": datetime.now().isoformat(),
            "repo_url": str(request.repo_url)
        }
        
        # Start cloning and analysis in background
        background_tasks.add_task(clone_and_analyze, job_id, str(request.repo_url), job_dir)
        
        return {
            "job_id": job_id,
            "status": "cloning",
            "message": "Repository cloning started",
            "websocket_url": f"/ws/{job_id}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GitHub analysis failed: {str(e)}")

@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    """Get current status of an analysis job"""
    if job_id not in analysis_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return analysis_jobs[job_id]

@app.get("/api/report/{job_id}")
async def get_report(job_id: str):
    """Download HTML report for completed analysis"""
    if job_id not in analysis_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = analysis_jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Analysis not completed yet")
    
    report_path = UPLOAD_DIR / job_id / "report.html"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    
    return FileResponse(report_path, media_type="text/html", filename=f"analysis_{job_id}.html")

@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time analysis updates
    Sends progress updates as analysis runs
    """
    await websocket.accept()
    
    try:
        # Send initial status
        if job_id in analysis_jobs:
            await websocket.send_json(analysis_jobs[job_id])
        
        # Poll for updates every 500ms
        while True:
            if job_id in analysis_jobs:
                job = analysis_jobs[job_id]
                await websocket.send_json(job)
                
                # Close connection when job completes or fails
                if job["status"] in ["completed", "failed"]:
                    break
            
            await asyncio.sleep(0.5)
            
    except Exception as e:
        print(f"WebSocket error for job {job_id}: {e}")
    finally:
        await websocket.close()

async def clone_and_analyze(job_id: str, repo_url: str, job_dir: Path):
    """Clone GitHub repository and run analysis"""
    try:
        # Update status
        analysis_jobs[job_id]["status"] = "cloning"
        analysis_jobs[job_id]["progress"] = 10
        analysis_jobs[job_id]["message"] = "Cloning repository..."
        
        # Clone repo (shallow clone for speed)
        repo_path = job_dir / "repo"
        git.Repo.clone_from(repo_url, repo_path, depth=1)
        
        # Update project path and start analysis
        analysis_jobs[job_id]["project_path"] = str(repo_path)
        analysis_jobs[job_id]["progress"] = 20
        analysis_jobs[job_id]["message"] = "Repository cloned, starting analysis..."
        
        await run_analysis(job_id, repo_path)
        
    except Exception as e:
        analysis_jobs[job_id]["status"] = "failed"
        analysis_jobs[job_id]["message"] = f"Clone failed: {str(e)}"
        print(f"Clone error for job {job_id}: {e}")

async def run_analysis(job_id: str, project_path: Path):
    """Run IncludeGuard CLI analysis on project"""
    try:
        # Update status
        analysis_jobs[job_id]["status"] = "running"
        analysis_jobs[job_id]["progress"] = 30
        analysis_jobs[job_id]["message"] = "Scanning C++ files..."
        
        # Output paths
        json_output = UPLOAD_DIR / job_id / "result.json"
        html_output = UPLOAD_DIR / job_id / "report.html"
        
        # Run CLI analysis with JSON output
        cmd = [
            "python", "-m", "includeguard.cli",
            "analyze", str(project_path),
            "--output", str(html_output)
        ]
        
        # Set environment to handle Unicode properly
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        # Execute in subprocess
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=Path(__file__).parent.parent.parent,  # Go to project root
            env=env
        )
        
        # Update progress while running
        analysis_jobs[job_id]["progress"] = 50
        analysis_jobs[job_id]["message"] = "Building dependency graph..."
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Analysis failed: {stderr.decode()}")
        
        # Parse HTML report to extract summary data
        analysis_jobs[job_id]["progress"] = 90
        analysis_jobs[job_id]["message"] = "Generating report..."
        
        # Read the generated HTML report for summary extraction
        with open(html_output, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Extract key metrics from CLI output and HTML report
        output_text = stdout.decode()
        result = parse_analysis_output(output_text, html_output)
        
        # Mark as completed
        analysis_jobs[job_id]["status"] = "completed"
        analysis_jobs[job_id]["progress"] = 100
        analysis_jobs[job_id]["message"] = "Analysis complete!"
        analysis_jobs[job_id]["result"] = result
        analysis_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        
    except Exception as e:
        analysis_jobs[job_id]["status"] = "failed"
        analysis_jobs[job_id]["message"] = f"Analysis failed: {str(e)}"
        print(f"Analysis error for job {job_id}: {e}")

def parse_analysis_output(output: str, html_path: Path = None) -> dict:
    """Parse CLI output and HTML report to extract key metrics"""
    result = {
        "total_files": 0,
        "total_cost": 0,
        "wasted_cost": 0,
        "waste_percentage": 0.0,
        "potential_savings": 0.0,
        "build_efficiency": 0.0,
        "top_opportunities": [],
        "pch_recommendations": []
    }
    
    try:
        # Extract total cost and wasted cost from output
        if "Total Build Cost:" in output:
            parts = output.split("Total Build Cost:")
            if len(parts) > 1:
                cost_line = parts[1].split("\n")[0]
                result["total_cost"] = int(''.join(filter(str.isdigit, cost_line.split("units")[0])))
        
        if "Wasted Cost:" in output:
            parts = output.split("Wasted Cost:")
            if len(parts) > 1:
                waste_line = parts[1].split("\n")[0]
                wasted = int(''.join(filter(str.isdigit, waste_line.split("units")[0])))
                result["wasted_cost"] = wasted
                
                # Extract percentage
                if "(" in waste_line and "%" in waste_line:
                    pct_str = waste_line.split("(")[1].split("%")[0]
                    result["waste_percentage"] = float(pct_str)
        
        if "Build Efficiency:" in output:
            parts = output.split("Build Efficiency:")
            if len(parts) > 1:
                eff_line = parts[1].split("\n")[0]
                result["build_efficiency"] = float(''.join(filter(lambda x: x.isdigit() or x == '.', eff_line.split("%")[0])))
        
        # Count files
        if "Found" in output and "C++ files" in output:
            parts = output.split("Found")[1].split("C++ files")[0]
            result["total_files"] = int(''.join(filter(str.isdigit, parts)))
        
        # Parse HTML report for detailed opportunities
        if html_path and html_path.exists():
            import re
            from html.parser import HTMLParser
            
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Extract opportunities from HTML table
            # Look for table rows with file, header, cost, and line information
            opp_pattern = r'<tr>\s*<td>(\d+)</td>\s*<td><code[^>]*>([^<]+)</code></td>\s*<td><code[^>]*>([^<]+)</code></td>\s*<td[^>]*>(\d+(?:,\d+)?)</td>\s*<td>(\d+)</td>'
            opportunities = re.findall(opp_pattern, html_content, re.MULTILINE)
            
            for match in opportunities:
                result["top_opportunities"].append({
                    "file": match[1],
                    "header": match[2],
                    "cost": int(match[3].replace(',', '')),
                    "line": int(match[4])
                })
            
            # Extract PCH recommendations
            pch_pattern = r'<tr>\s*<td>(\d+)</td>\s*<td><code[^>]*>([^<]+)</code></td>\s*<td>(\d+)\s*files</td>\s*<td[^>]*>(\d+(?:,\d+)?)</td>\s*<td[^>]*>(\d+(?:,\d+)?)</td>\s*<td[^>]*>(\d+(?:,\d+)?)</td>'
            pch_matches = re.findall(pch_pattern, html_content, re.MULTILINE)
            
            for match in pch_matches:
                result["pch_recommendations"].append({
                    "header": match[1],
                    "used_by": int(match[2]),
                    "cost": int(match[3].replace(',', '')),
                    "pch_score": int(match[4].replace(',', '')),
                    "savings": int(match[5].replace(',', ''))
                })
        
    except Exception as e:
        print(f"Error parsing output: {e}")
        import traceback
        traceback.print_exc()
    
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
