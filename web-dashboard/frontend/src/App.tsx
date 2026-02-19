import { useState } from 'react';
import { Shield } from 'lucide-react';
import UploadSection from './components/UploadSection';
import ProgressView from './components/ProgressView';
import ResultsView from './components/ResultsView';
import type { JobStatus } from './api';

type ViewState = 'upload' | 'progress' | 'results';

function App() {
  const [currentView, setCurrentView] = useState<ViewState>('upload');
  const [jobId, setJobId] = useState<string>('');
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);

  const handleAnalysisStarted = (newJobId: string) => {
    setJobId(newJobId);
    setCurrentView('progress');
  };

  const handleAnalysisComplete = (status: JobStatus) => {
    setJobStatus(status);
    setCurrentView('results');
  };

  const handleReset = () => {
    setCurrentView('upload');
    setJobId('');
    setJobStatus(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-600 via-purple-700 to-indigo-800">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="flex items-center justify-center mb-4">
            <Shield className="w-16 h-16 text-white" />
          </div>
          <h1 className="text-5xl font-bold text-white mb-3">
            IncludeGuard
          </h1>
          <p className="text-xl text-purple-100">
            Analyze C++ Build Performance in Seconds
          </p>
          <p className="text-sm text-purple-200 mt-2">
            Find unused includes • Reduce build times • Zero installation required
          </p>
        </div>

        {/* Main Content */}
        <div className="max-w-4xl mx-auto">
          {currentView === 'upload' && (
            <UploadSection onAnalysisStarted={handleAnalysisStarted} />
          )}

          {currentView === 'progress' && (
            <ProgressView
              jobId={jobId}
              onComplete={handleAnalysisComplete}
              onError={handleReset}
            />
          )}

          {currentView === 'results' && jobStatus && (
            <ResultsView jobStatus={jobStatus} onReset={handleReset} />
          )}
        </div>

        {/* Footer */}
        <div className="text-center mt-16 text-purple-200 text-sm">
          <p>
            Open source project •{' '}
            <a
              href="https://github.com/HarshithaJ28/IncludeGuard"
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-white"
            >
              View on GitHub
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}

export default App;
