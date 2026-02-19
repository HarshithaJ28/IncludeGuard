import { useEffect, useState } from 'react';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { api } from '../api';
import type { JobStatus } from '../api';

interface ProgressViewProps {
  jobId: string;
  onComplete: (status: JobStatus) => void;
  onError: () => void;
}

export default function ProgressView({ jobId, onComplete, onError }: ProgressViewProps) {
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [wsError, setWsError] = useState(false);

  useEffect(() => {
    // Connect to WebSocket for real-time updates
    const wsUrl = api.getWebSocketUrl(jobId);
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const data: JobStatus = JSON.parse(event.data);
        setStatus(data);

        // Handle completion
        if (data.status === 'completed') {
          setTimeout(() => {
            onComplete(data);
            ws.close();
          }, 1000);
        }

        // Handle errors
        if (data.status === 'failed') {
          setWsError(true);
          setTimeout(() => {
            onError();
            ws.close();
          }, 3000);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setWsError(true);
      
      // Fallback to polling if WebSocket fails
      const pollInterval = setInterval(async () => {
        try {
          const data = await api.getStatus(jobId);
          setStatus(data);
          
          if (data.status === 'completed') {
            clearInterval(pollInterval);
            onComplete(data);
          } else if (data.status === 'failed') {
            clearInterval(pollInterval);
            onError();
          }
        } catch (err) {
          console.error('Polling error:', err);
          clearInterval(pollInterval);
          onError();
        }
      }, 1000);

      return () => clearInterval(pollInterval);
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [jobId, onComplete, onError]);

  const getStatusIcon = () => {
    if (!status) return <Loader2 className="w-8 h-8 text-purple-600 animate-spin" />;
    
    switch (status.status) {
      case 'completed':
        return <CheckCircle className="w-8 h-8 text-green-600" />;
      case 'failed':
        return <XCircle className="w-8 h-8 text-red-600" />;
      default:
        return <Loader2 className="w-8 h-8 text-purple-600 animate-spin" />;
    }
  };

  const getStatusColor = () => {
    if (!status) return 'bg-purple-600';
    switch (status.status) {
      case 'completed':
        return 'bg-green-600';
      case 'failed':
        return 'bg-red-600';
      default:
        return 'bg-purple-600';
    }
  };

  const progress = status?.progress || 0;

  return (
    <div className="bg-white rounded-2xl shadow-2xl p-8">
      <div className="text-center mb-8">
        <div className="flex justify-center mb-4">
          {getStatusIcon()}
        </div>
        <h2 className="text-2xl font-bold text-gray-800 mb-2">
          {status?.status === 'completed' ? 'Analysis Complete!' : 'Analyzing Your Project...'}
        </h2>
        <p className="text-gray-600">
          {status?.message || 'Connecting to analysis service...'}
        </p>
      </div>

      {/* Progress Bar */}
      <div className="mb-8">
        <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ease-out ${getStatusColor()}`}
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="text-center mt-2 text-sm font-semibold text-gray-600">
          {progress}%
        </div>
      </div>

      {/* Status Steps */}
      <div className="space-y-3">
        <StatusStep
          label="Queued"
          isActive={status?.status === 'queued'}
          isComplete={progress > 10}
        />
        <StatusStep
          label="Cloning Repository"
          isActive={status?.status === 'cloning'}
          isComplete={progress > 20}
        />
        <StatusStep
          label="Scanning C++ Files"
          isActive={progress >= 30 && progress < 50}
          isComplete={progress >= 50}
        />
        <StatusStep
          label="Building Dependency Graph"
          isActive={progress >= 50 && progress < 70}
          isComplete={progress >= 70}
        />
        <StatusStep
          label="Calculating Build Costs"
          isActive={progress >= 70 && progress < 90}
          isComplete={progress >= 90}
        />
        <StatusStep
          label="Generating Report"
          isActive={progress >= 90 && progress < 100}
          isComplete={progress === 100}
        />
      </div>

      {/* Error State */}
      {wsError && (
        <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-sm text-yellow-800">
            WebSocket connection failed. Falling back to polling...
          </p>
        </div>
      )}

      {status?.status === 'failed' && (
        <div className="mt-6 bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-800">
            Analysis failed. You'll be redirected back in a moment...
          </p>
        </div>
      )}
    </div>
  );
}

interface StatusStepProps {
  label: string;
  isActive: boolean;
  isComplete: boolean;
}

function StatusStep({ label, isActive, isComplete }: StatusStepProps) {
  return (
    <div className="flex items-center space-x-3">
      <div
        className={`w-3 h-3 rounded-full transition-colors ${
          isComplete ? 'bg-green-500' : isActive ? 'bg-purple-600 animate-pulse' : 'bg-gray-300'
        }`}
      />
      <span
        className={`text-sm ${
          isComplete ? 'text-green-700 font-semibold' : isActive ? 'text-purple-700 font-semibold' : 'text-gray-500'
        }`}
      >
        {label}
      </span>
      {isComplete && <CheckCircle className="w-4 h-4 text-green-600" />}
    </div>
  );
}
