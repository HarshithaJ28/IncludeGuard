import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface AnalysisResult {
  total_files: number;
  total_cost: number;
  wasted_cost: number;
  waste_percentage: number;
  potential_savings: number;
  build_efficiency: number;
  top_opportunities: Array<{
    file: string;
    header: string;
    cost: number;
    line: number;
  }>;
  pch_recommendations: Array<{
    header: string;
    used_by: number;
    cost: number;
    pch_score: number;
    savings: number;
  }>;
}

export type JobStatus = {
  job_id: string;
  status: 'queued' | 'cloning' | 'running' | 'completed' | 'failed';
  progress: number;
  message: string;
  result?: AnalysisResult;
  created_at?: string;
  completed_at?: string;
};

export const api = {
  analyzeUpload: async (file: File): Promise<JobStatus> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await axios.post(`${API_BASE_URL}/api/analyze/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  analyzeGithub: async (repoUrl: string): Promise<JobStatus> => {
    const response = await axios.post(`${API_BASE_URL}/api/analyze/github`, {
      repo_url: repoUrl,
    });
    return response.data;
  },

  getStatus: async (jobId: string): Promise<JobStatus> => {
    const response = await axios.get(`${API_BASE_URL}/api/status/${jobId}`);
    return response.data;
  },

  getReportUrl: (jobId: string): string => {
    return `${API_BASE_URL}/api/report/${jobId}`;
  },

  getWebSocketUrl: (jobId: string): string => {
    const wsUrl = API_BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://');
    return `${wsUrl}/ws/${jobId}`;
  },
};
