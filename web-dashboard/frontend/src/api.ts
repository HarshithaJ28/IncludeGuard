/**
 * IncludeGuard Web Dashboard API client.
 * Connects to the FastAPI backend (upload, GitHub, status, WebSocket, report).
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface BackendJobStatus {
  job_id: string;
  status: 'queued' | 'cloning' | 'running' | 'completed' | 'failed';
  progress: number;
  message: string;
  result?: BackendResult;
  logs?: { timestamp: string; stream: string; message: string }[];
}

export interface BackendResult {
  total_files: number;
  total_cost: number;
  wasted_cost: number;
  waste_percentage: number;
  top_opportunities: { file: string; header: string; cost: number; line: number }[];
  pch_recommendations: { header: string; used_by: number; cost: number; pch_score?: number; savings: number }[];
}

export interface AnalysisResult {
  totalFiles: number;
  totalIncludes: number;
  totalCost: string;
  totalWaste: string;
  wastePercentage: number;
  opportunities: { file: string; waste: string; impact: 'High' | 'Medium' | 'Low'; suggestion: string; line?: number }[];
  forwardDecls: { file: string; replaceInclude: string; withForwardDecl: string; confidence: number }[];
  pchRecommendations: { header: string; usedBy: number; cost: number; pchScore: number; estSavings: number }[];
  wastefulFiles: { rank: number; file: string; includes: number; totalCost: number; wastedCost: number; wastePercentage: number }[];
  chartData: { name: string; cost: number; waste: number }[];
}

export function mapBackendResultToAnalysisResult(r: BackendResult | undefined): AnalysisResult | null {
  if (!r) return null;
  const opportunities = (r.top_opportunities || []).map((o) => ({
    file: o.file,
    waste: String(o.cost),
    impact: (o.cost >= 1500 ? 'High' : o.cost >= 1000 ? 'Medium' : 'Low') as 'High' | 'Medium' | 'Low',
    suggestion: `Unused header: ${o.header}`,
    line: o.line,
  }));
  const byFile = new Map<string, number>();
  for (const o of r.top_opportunities || []) {
    byFile.set(o.file, (byFile.get(o.file) || 0) + o.cost);
  }
  const wastefulFiles = Array.from(byFile.entries())
    .map(([file, wastedCost], i) => ({
      rank: i + 1,
      file,
      includes: 0,
      totalCost: wastedCost + Math.round(wastedCost * 0.5),
      wastedCost,
      wastePercentage: 50,
    }))
    .sort((a, b) => b.wastedCost - a.wastedCost)
    .slice(0, 10);
  const chartData = wastefulFiles.slice(0, 6).map((f) => ({
    name: f.file.length > 14 ? f.file.slice(0, 12) + '…' : f.file,
    cost: f.totalCost,
    waste: f.wastedCost,
  }));
  return {
    totalFiles: r.total_files ?? 0,
    totalIncludes: opportunities.length,
    totalCost: (r.total_cost ?? 0).toLocaleString(),
    totalWaste: (r.wasted_cost ?? 0).toLocaleString(),
    wastePercentage: r.waste_percentage ?? 0,
    opportunities,
    forwardDecls: [],
    pchRecommendations: (r.pch_recommendations || []).map((p) => ({
      header: p.header,
      usedBy: p.used_by,
      cost: p.cost,
      pchScore: p.pch_score ?? p.cost * p.used_by,
      estSavings: p.savings,
    })),
    wastefulFiles,
    chartData,
  };
}

export const api = {
  analyzeUpload: async (file: File): Promise<BackendJobStatus> => {
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${API_BASE}/api/analyze/upload`, {
      method: 'POST',
      body: form,
    });
    if (!res.ok) throw new Error(await res.text().catch(() => res.statusText));
    return res.json();
  },

  analyzeGithub: async (repoUrl: string): Promise<BackendJobStatus> => {
    const res = await fetch(`${API_BASE}/api/analyze/github`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo_url: repoUrl }),
    });
    if (!res.ok) throw new Error(await res.text().catch(() => res.statusText));
    return res.json();
  },

  getStatus: async (jobId: string): Promise<BackendJobStatus> => {
    const res = await fetch(`${API_BASE}/api/status/${jobId}`);
    if (!res.ok) throw new Error(await res.text().catch(() => res.statusText));
    return res.json();
  },

  getReportUrl: (jobId: string): string => `${API_BASE}/api/report/${jobId}`,

  getFileContent: async (jobId: string, filePath: string): Promise<{ content: string; file: string }> => {
    const res = await fetch(`${API_BASE}/api/file/${jobId}?path=${encodeURIComponent(filePath)}`);
    if (!res.ok) throw new Error(await res.text().catch(() => res.statusText));
    return res.json();
  },

  getWebSocketUrl: (jobId: string): string => {
    const base = API_BASE.replace(/^http/, 'ws');
    return `${base}/ws/${jobId}`;
  },
};
