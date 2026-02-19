import { useState, useRef } from 'react';
import { Upload, Github, FileCode, AlertCircle } from 'lucide-react';
import { api } from '../api';

interface UploadSectionProps {
  onAnalysisStarted: (jobId: string) => void;
}

export default function UploadSection({ onAnalysisStarted }: UploadSectionProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadMethod, setUploadMethod] = useState<'file' | 'github'>('file');
  const [githubUrl, setGithubUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      await handleFileUpload(file);
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      await handleFileUpload(file);
    }
  };

  const handleFileUpload = async (file: File) => {
    setError('');
    setIsLoading(true);
    try {
      const response = await api.analyzeUpload(file);
      onAnalysisStarted(response.job_id);
    } catch (err) {
      setError('Failed to upload file. Please try again.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGithubSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    if (!githubUrl.trim()) {
      setError('Please enter a GitHub URL');
      return;
    }

    // Basic URL validation
    if (!githubUrl.includes('github.com')) {
      setError('Please enter a valid GitHub URL');
      return;
    }

    setIsLoading(true);
    try {
      const response = await api.analyzeGithub(githubUrl);
      onAnalysisStarted(response.job_id);
    } catch (err) {
      setError('Failed to analyze repository. Make sure it\'s public.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-2xl overflow-hidden">
      {/* Method Selection Tabs */}
      <div className="flex border-b">
        <button
          onClick={() => setUploadMethod('file')}
          className={`flex-1 py-4 px-6 font-semibold transition-colors ${
            uploadMethod === 'file'
              ? 'bg-purple-50 text-purple-700 border-b-2 border-purple-600'
              : 'text-gray-500 hover:bg-gray-50'
          }`}
        >
          <Upload className="w-5 h-5 inline mr-2" />
          Upload Files
        </button>
        <button
          onClick={() => setUploadMethod('github')}
          className={`flex-1 py-4 px-6 font-semibold transition-colors ${
            uploadMethod === 'github'
              ? 'bg-purple-50 text-purple-700 border-b-2 border-purple-600'
              : 'text-gray-500 hover:bg-gray-50'
          }`}
        >
          <Github className="w-5 h-5 inline mr-2" />
          GitHub Repository
        </button>
      </div>

      <div className="p-8">
        {/* File Upload */}
        {uploadMethod === 'file' && (
          <div>
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-3 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all ${
                isDragging
                  ? 'border-purple-600 bg-purple-50'
                  : 'border-gray-300 hover:border-purple-400 hover:bg-gray-50'
              }`}
            >
              <FileCode className="w-16 h-16 mx-auto mb-4 text-gray-400" />
              <h3 className="text-xl font-semibold text-gray-700 mb-2">
                Drop your C++ project here
              </h3>
              <p className="text-gray-500 mb-4">
                or click to browse files
              </p>
              <p className="text-sm text-gray-400">
                Supports: .zip archives or individual .cpp/.h files
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".zip,.cpp,.h,.hpp,.cxx,.cc,.c"
                onChange={handleFileSelect}
                className="hidden"
              />
            </div>

            <div className="mt-6 space-y-2">
              <h4 className="font-semibold text-gray-700">💡 Tips:</h4>
              <ul className="text-sm text-gray-600 space-y-1 ml-4">
                <li>• Zip your entire C++ project for best results</li>
                <li>• Analysis takes 10-60 seconds depending on project size</li>
                <li>• We analyze include patterns without compiling</li>
              </ul>
            </div>
          </div>
        )}

        {/* GitHub URL */}
        {uploadMethod === 'github' && (
          <form onSubmit={handleGithubSubmit}>
            <div className="mb-6">
              <label className="block text-sm font-semibold text-gray-700 mb-3">
                GitHub Repository URL
              </label>
              <input
                type="url"
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                placeholder="https://github.com/nlohmann/json"
                className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none text-lg"
                disabled={isLoading}
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-purple-600 hover:bg-purple-700 text-white font-semibold py-4 px-6 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Starting Analysis...' : 'Analyze Repository'}
            </button>

            <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h4 className="font-semibold text-blue-900 mb-2">
                📚 Example Repositories to Try:
              </h4>
              <div className="space-y-2">
                {[
                  'https://github.com/nlohmann/json',
                  'https://github.com/fmtlib/fmt',
                  'https://github.com/gabime/spdlog',
                ].map((url) => (
                  <button
                    key={url}
                    type="button"
                    onClick={() => setGithubUrl(url)}
                    className="block w-full text-left text-sm text-blue-700 hover:text-blue-900 hover:underline"
                  >
                    {url}
                  </button>
                ))}
              </div>
            </div>
          </form>
        )}

        {/* Error Display */}
        {error && (
          <div className="mt-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-start">
            <AlertCircle className="w-5 h-5 text-red-600 mr-3 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-semibold text-red-900">Error</h4>
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="mt-6 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Preparing analysis...</p>
          </div>
        )}
      </div>
    </div>
  );
}
