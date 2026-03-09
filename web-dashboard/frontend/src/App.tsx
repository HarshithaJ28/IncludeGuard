import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Terminal } from './components/Terminal';
import { Report, ReportTab } from './components/Report';
import { UploadForm, type OnAnalyze } from './components/UploadForm';
import { CodeEditor } from './components/CodeEditor';
import type { TerminalLine, AnalysisResult, AppState, FileNode } from './types';
import { api, mapBackendResultToAnalysisResult } from './api';
import { motion, AnimatePresence } from 'motion/react';
import {
  File, Code, Settings, HelpCircle, LogOut, Sparkles, Layout, Search,
  ChevronDown, ChevronRight, FileCode as FileCodeIcon, MoreHorizontal, X,
  ShieldCheck, Globe, Cpu, Info, AlertTriangle, Folder,
} from 'lucide-react';

const MOCK_FILE_TREE: FileNode[] = [
  {
    name: 'src',
    type: 'folder',
    isOpen: true,
    children: [
      { name: 'main.cpp', type: 'file' },
      { name: 'database_client.cpp', type: 'file' },
      { name: 'processor.cpp', type: 'file' },
      { name: 'service.cpp', type: 'file' },
      {
        name: 'include',
        type: 'folder',
        isOpen: true,
        children: [
          { name: 'utils.h', type: 'file' },
          { name: 'database.h', type: 'file' },
        ],
      },
    ],
  },
  { name: 'CMakeLists.txt', type: 'file' },
  { name: 'README.md', type: 'file' },
  { name: '.gitignore', type: 'file' },
];

export default function App() {
  const [appState, setAppState] = useState<AppState>('initial');
  const [terminalLines, setTerminalLines] = useState<TerminalLine[]>([]);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [isMobile, setIsMobile] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(260);
  const [reportWidth, setReportWidth] = useState(600);
  const [terminalHeight, setTerminalHeight] = useState(30);
  const [openFiles, setOpenFiles] = useState<string[]>([]);
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [isReportOpen, setIsReportOpen] = useState(false);
  const [fileTree, setFileTree] = useState<FileNode[]>(MOCK_FILE_TREE);
  const [fileContents, setFileContents] = useState<Record<string, string>>({});
  const [loadingFiles, setLoadingFiles] = useState<Set<string>>(new Set());
  const wsRef = useRef<WebSocket | null>(null);
  const isResizingSidebar = useRef(false);
  const isResizingTerminal = useRef(false);
  const isResizingReport = useRef(false);

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Initialize terminal with welcome banner on first project load
  useEffect(() => {
    if (appState === 'processing' && terminalLines.length === 0) {
      addTerminalLine('═══════════════════════════════════════════════════════════════', 'info');
      addTerminalLine('⚡ IncludeGuard v0.1.0 - C++ Build Analyzer', 'success');
      addTerminalLine('🚀 Fast Include Dependency Analysis & Build Cost Estimation', 'info');
      addTerminalLine('═══════════════════════════════════════════════════════════════', 'info');
      addTerminalLine('Type "help" to see available commands', 'progress');
      addTerminalLine('', 'info');
    }
  }, [appState, terminalLines.length]);

  const startResizingSidebar = useCallback(() => {
    isResizingSidebar.current = true;
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', stopResizing);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, []);

  const startResizingTerminal = useCallback(() => {
    isResizingTerminal.current = true;
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', stopResizing);
    document.body.style.cursor = 'row-resize';
    document.body.style.userSelect = 'none';
  }, []);

  const startResizingReport = useCallback(() => {
    isResizingReport.current = true;
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', stopResizing);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, []);

  const stopResizing = useCallback(() => {
    isResizingSidebar.current = false;
    isResizingTerminal.current = false;
    isResizingReport.current = false;
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', stopResizing);
    document.body.style.cursor = 'default';
    document.body.style.userSelect = 'auto';
  }, []);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (isResizingSidebar.current) {
      const newWidth = e.clientX;
      if (newWidth > 150 && newWidth < 500) setSidebarWidth(newWidth);
    } else if (isResizingTerminal.current) {
      const newHeight = ((window.innerHeight - e.clientY) / window.innerHeight) * 100;
      if (newHeight > 10 && newHeight < 70) setTerminalHeight(newHeight);
    } else if (isResizingReport.current) {
      const newWidth = window.innerWidth - e.clientX;
      if (newWidth > 200 && newWidth < 800) setReportWidth(newWidth);
    }
  }, []);

  const addTerminalLine = useCallback((text: string, type: TerminalLine['type'] = 'info') => {
    const newLine: TerminalLine = {
      id: Math.random().toString(36).substr(2, 9),
      timestamp: new Date().toLocaleTimeString('en-GB', { hour12: false }),
      text,
      type,
    };
    setTerminalLines((prev) => [...prev, newLine]);
  }, []);

  const runAnalysis: OnAnalyze = useCallback(async (source, value, file) => {
    setAppState('processing');
    setTerminalLines([]);
    try {
      let jobId: string;
      if (source === 'github') {
        const res = await api.analyzeGithub(value);
        jobId = res.job_id;
        setCurrentJobId(jobId);
        addTerminalLine(`Cloning repository from ${value}...`, 'info');
      } else if (source === 'files' && file) {
        const res = await api.analyzeUpload(file);
        jobId = res.job_id;
        setCurrentJobId(jobId);
        addTerminalLine(`Upload received: ${file.name}. Starting analysis...`, 'info');
      } else {
        addTerminalLine('Please select a file or enter a GitHub URL.', 'error');
        return;
      }

      const wsUrl = api.getWebSocketUrl(jobId);
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.logs && Array.isArray(data.logs)) {
            setTerminalLines(
              data.logs.map(
                (log: { timestamp: string; stream: string; message: string }, i: number) =>
                  ({
                    id: `${jobId}-${i}-${log.timestamp}`,
                    timestamp: log.timestamp,
                    text: log.message,
                    type:
                      log.stream === 'stderr'
                        ? 'error'
                        : log.stream === 'stdout'
                          ? 'command'
                          : log.message.toLowerCase().includes('complete') || log.message.toLowerCase().includes('success')
                            ? 'success'
                            : log.message.toLowerCase().includes('error') || log.message.toLowerCase().includes('failed')
                              ? 'error'
                              : 'info',
                  }) as TerminalLine
              )
            );
          }
          if (data.status === 'completed' && data.result) {
            console.log('[Analysis] Completed. Result:', data.result);
            const mapped = mapBackendResultToAnalysisResult(data.result);
            if (mapped) setAnalysisResult(mapped);
            // Update file tree if backend provides it
            if (data.result.file_tree && Array.isArray(data.result.file_tree)) {
              console.log('[FileTree] Received file tree with', data.result.file_tree.length, 'root items');
              setFileTree(data.result.file_tree);
              addTerminalLine('📁 Project files loaded! Click files in the explorer to view contents.', 'success');
            } else {
              console.warn('[FileTree] No file tree in result. Result keys:', Object.keys(data.result || {}));
            }
            setAppState('completed');
            setIsReportOpen(true);
            ws.close();
          }
          if (data.status === 'failed') {
            addTerminalLine(data.message || 'Analysis failed', 'error');
            setAppState('completed');
            ws.close();
          }
        } catch (_) {}
      };

      ws.onerror = () => addTerminalLine('WebSocket error. Falling back to polling...', 'error');
      ws.onclose = () => { wsRef.current = null; };
    } catch (err) {
      addTerminalLine(err instanceof Error ? err.message : 'Analysis request failed', 'error');
      setAppState('initial');
    }
  }, [addTerminalLine]);

  const handleClearTerminal = () => setTerminalLines([]);

  const handleCommand = (command: string) => {
    const cmd = command.trim().toLowerCase();
    const args = command.trim().split(/\s+/);
    
    addTerminalLine(command, 'command');
    
    setTimeout(() => {
      switch (cmd) {
        case 'help':
          addTerminalLine('Available commands:', 'info');
          addTerminalLine('  analyze      - Run IncludeGuard analysis on opened project', 'info');
          addTerminalLine('  clear        - Clear the terminal screen', 'info');
          addTerminalLine('  ls / dir     - List files in current directory', 'info');
          addTerminalLine('  help         - Show this help message', 'info');
          addTerminalLine('  version      - Show IncludeGuard version', 'info');
          addTerminalLine('  whoami       - Show current user information', 'info');
          addTerminalLine('  date         - Show current date and time', 'info');
          addTerminalLine('  status       - Show current analysis status', 'info');
          addTerminalLine('  exit         - Exit the application', 'info');
          break;
        
        case 'clear':
        case 'cls':
          handleClearTerminal();
          break;
        
        case 'ls':
        case 'dir':
          addTerminalLine('Directory: C:\\IncludeGuard\\project', 'info');
          addTerminalLine('Mode                LastWriteTime         Length Name', 'info');
          addTerminalLine('----                -------------         ------ ----', 'info');
          addTerminalLine('d-----        26/02/2026    14:30                src', 'info');
          addTerminalLine('d-----        26/02/2026    14:30                include', 'info');
          addTerminalLine('-a----        26/02/2026    14:30           1242 CMakeLists.txt', 'info');
          addTerminalLine('-a----        26/02/2026    14:30            452 README.md', 'info');
          addTerminalLine('-a----        26/02/2026    14:30            128 .gitignore', 'info');
          break;
        
        case 'version':
          addTerminalLine('IncludeGuard v0.1.0 - Fast C++ Include Analyzer & Build Cost Estimator', 'success');
          addTerminalLine('Copyright © 2026. All rights reserved.', 'info');
          break;
        
        case 'whoami':
          addTerminalLine('IncludeGuard\\developer-user', 'info');
          break;
        
        case 'date':
          addTerminalLine(new Date().toString(), 'info');
          break;
        
        case 'status':
          if (appState === 'processing') {
            addTerminalLine('Status: Analysis in progress...', 'progress');
          } else if (appState === 'completed' && analysisResult) {
            addTerminalLine('Status: Analysis complete', 'success');
            addTerminalLine(`Total Files: ${analysisResult.totalFiles}`, 'info');
            addTerminalLine(`Total Cost: ${analysisResult.totalCost} units`, 'info');
            addTerminalLine(`Wasted Cost: ${analysisResult.totalWaste} units (${analysisResult.wastePercentage}%)`, 'info');
          } else {
            addTerminalLine('Status: Ready for analysis', 'info');
          }
          break;
        
        case 'analyze':
          if (appState === 'processing') {
            addTerminalLine('Error: Analysis is already in progress. Please wait for it to complete.', 'error');
          } else if (appState === 'initial') {
            addTerminalLine('Error: No project loaded. Please upload a project or GitHub repository first.', 'error');
          } else {
            addTerminalLine('Starting new analysis...', 'progress');
            handleNewAnalysis();
          }
          break;
        
        case 'exit':
          addTerminalLine('Exiting IncludeGuard. Goodbye!', 'success');
          break;
        
        default:
          if (args[0]) {
            addTerminalLine(`Command not found: '${args[0]}'. Type 'help' to see available commands.`, 'error');
          }
          break;
      }
    }, 100);
  };

  const handleNewAnalysis = () => {
    if (wsRef.current) wsRef.current.close();
    wsRef.current = null;
    setAppState('initial');
    setAnalysisResult(null);
    setTerminalLines([]);
  };

  const handleFileClick = useCallback(async (filePath: string) => {
    // Add to open files if not already there
    setOpenFiles((prev) => prev.includes(filePath) ? prev : [...prev, filePath]);
    setActiveFile(filePath);
    
    // Load file content from backend if not already loaded and not already loading
    const isLoading = loadingFiles.has(filePath);
    const isLoaded = !!fileContents[filePath];
    
    if (!isLoaded && !isLoading && currentJobId) {
      setLoadingFiles((prev) => new Set(prev).add(filePath));
      try {
        console.log(`[FileLoader] Fetching: ${filePath} (JobID: ${currentJobId})`);
        const response = await api.getFileContent(currentJobId, filePath);
        console.log(`[FileLoader] Success: ${filePath}, size: ${response.content.length} bytes`);
        setFileContents((prev) => ({ ...prev, [filePath]: response.content }));
      } catch (err) {
        console.error(`[FileLoader] Failed to fetch ${filePath}:`, err);
        const errorMsg = err instanceof Error ? err.message : 'Unknown error';
        const errorContent = `// ❌ Failed to load: ${errorMsg}\n// 📁 Path: ${filePath}\n// 🔍 JobID: ${currentJobId}`;
        setFileContents((prev) => ({ ...prev, [filePath]: errorContent }));
      } finally {
        setLoadingFiles((prev) => {
          const updated = new Set(prev);
          updated.delete(filePath);
          return updated;
        });
      }
    }
  }, [currentJobId, fileContents, loadingFiles]);

  const handleCloseFile = (fileName: string) => {
    const newOpenFiles = openFiles.filter((f) => f !== fileName);
    setOpenFiles(newOpenFiles);
    if (activeFile === fileName) {
      setActiveFile(newOpenFiles.length > 0 ? newOpenFiles[newOpenFiles.length - 1] : null);
    }
  };

  const handleCodeChange = (newCode: string) => {
    if (activeFile) setFileContents((prev) => ({ ...prev, [activeFile]: newCode }));
  };

  return (
    <div className="h-screen w-full bg-[#0d1117] text-[#c9d1d9] flex flex-col overflow-hidden font-sans">
      <header className="h-12 border-b border-[#30363d] bg-[#161b22] flex items-center justify-between px-4 shrink-0 z-50">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <ShieldCheck size={20} className="text-white" />
            </div>
            <span className="font-bold text-lg tracking-tight text-white">IncludeGuard</span>
          </div>
          <nav className="hidden lg:flex items-center gap-4 text-xs font-medium text-[#8b949e]">
            {['File', 'Edit', 'View', 'Navigation', 'Debug', 'Account'].map((item) => (
              <button key={item} type="button" className="hover:text-white transition-colors">
                {item}
              </button>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-4">
          {appState === 'completed' && (
            <button
              type="button"
              onClick={() => setIsReportOpen(!isReportOpen)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all border ${
                isReportOpen ? 'bg-cyan-500/10 border-cyan-500/50 text-cyan-400' : 'bg-[#0d1117] border-[#30363d] text-[#8b949e] hover:text-white hover:border-[#8b949e]/50'
              }`}
            >
              <Layout size={14} />
              <span>Analysis Report</span>
            </button>
          )}
          <div className="relative hidden md:block">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#8b949e]" size={14} />
            <input type="text" placeholder="Search..." className="bg-[#0d1117] border border-[#30363d] rounded-md pl-9 pr-4 py-1.5 text-xs w-64 focus:outline-none focus:border-cyan-500/50 transition-all" />
          </div>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <aside style={{ width: sidebarWidth }} className="bg-[#161b22] border-r border-[#30363d] flex flex-col shrink-0 relative">
          <div className="h-9 flex items-center justify-between px-4 border-b border-[#30363d] bg-[#0d1117]">
            <span className="text-[10px] font-bold text-[#8b949e] uppercase tracking-widest">Explorer</span>
            <button type="button" className="text-[#8b949e] hover:text-white">
              <MoreHorizontal size={14} />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto custom-scrollbar">
            {appState === 'initial' ? (
              <div className="p-4 space-y-4">
                <div className="p-4 rounded-lg border border-dashed border-[#30363d] text-center">
                  <p className="text-[10px] text-[#8b949e]">No folder opened</p>
                </div>
                <button type="button" onClick={handleNewAnalysis} className="w-full bg-[#238636] hover:bg-[#2ea043] text-white py-2 rounded-md text-sm font-semibold flex items-center justify-center gap-2 transition-all shadow-lg shadow-green-900/20">
                  <Sparkles size={16} />
                  Open Project
                </button>
              </div>
            ) : (
              <div className="py-2">
                <div className="px-4 py-1 flex items-center gap-2 text-[#c9d1d9] font-bold text-[11px] uppercase tracking-wider mb-1">
                  <ChevronDown size={14} className="text-[#8b949e]" />
                  <span>IncludeGuard-Project</span>
                </div>
                <div className="pl-2">
                  <FileExplorer nodes={fileTree} onFileClick={handleFileClick} />
                </div>
              </div>
            )}
          </div>
          <div className="mt-auto border-t border-[#30363d] p-2 space-y-0.5">
            <SidebarItem icon={<Settings size={16} />} label="Settings" />
            <SidebarItem icon={<HelpCircle size={16} />} label="Help" />
            <SidebarItem icon={<LogOut size={16} />} label="Logout" />
          </div>
          <div onMouseDown={startResizingSidebar} className="absolute right-0 top-0 w-1 h-full cursor-col-resize hover:bg-cyan-500/30 transition-colors z-20" />
        </aside>

        <main className="flex-1 flex flex-col overflow-hidden bg-[#0d1117]">
          <AnimatePresence mode="wait">
            {appState === 'initial' ? (
              <motion.div key="upload" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="h-full">
                <UploadForm onAnalyze={runAnalysis} />
              </motion.div>
            ) : (
              <motion.div key="dashboard" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full flex flex-row overflow-hidden">
                <div className="flex-1 flex flex-col overflow-hidden">
                  <div style={{ height: `${100 - terminalHeight}%` }} className="flex flex-col overflow-hidden">
                    <div className="h-9 flex items-center bg-[#161b22] border-b border-[#30363d] shrink-0 overflow-x-auto no-scrollbar">
                      {openFiles.length === 0 && (
                        <div className="px-4 h-full flex items-center gap-2 text-[#8b949e] text-[11px]">No files open</div>
                      )}
                      {openFiles.map((fileName) => (
                        <div key={fileName} className="relative group">
                          <ReportTab
                            icon={<FileCodeIcon size={14} className="text-cyan-400" />}
                            label={fileName}
                            active={activeFile === fileName}
                            onClick={() => setActiveFile(fileName)}
                          />
                          <button
                            type="button"
                            onClick={(e) => { e.stopPropagation(); handleCloseFile(fileName); }}
                            className="absolute right-1 top-1/2 -translate-y-1/2 p-0.5 hover:bg-[#30363d] rounded text-[#8b949e] hover:text-white opacity-0 group-hover:opacity-100 transition-all"
                          >
                            <X size={10} />
                          </button>
                        </div>
                      ))}
                    </div>
                    <div className="flex-1 overflow-hidden relative">
                      {activeFile ? (
                        loadingFiles.has(activeFile) ? (
                          <div className="flex-1 flex items-center justify-center text-[#8b949e]">
                            <div className="text-center">
                              <div className="animate-spin rounded-full h-8 w-8 border border-[#30363d] border-t-cyan-500 mx-auto mb-2"></div>
                              <p className="text-sm">Loading file...</p>
                            </div>
                          </div>
                        ) : (
                          <CodeEditor code={fileContents[activeFile] || ''} onChange={handleCodeChange} fileName={activeFile} />
                        )
                      ) : (
                        <div className="flex-1 flex flex-col items-center justify-center text-[#8b949e] gap-4">
                          <div className="p-4 rounded-full bg-[#161b22] border border-[#30363d]">
                            <Code size={48} className="opacity-20" />
                          </div>
                          <div className="text-center">
                            <p className="text-sm font-medium text-[#c9d1d9]">No file selected</p>
                            <p className="text-xs">Select a file from the explorer to start editing</p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                  <div onMouseDown={startResizingTerminal} className="h-1 w-full bg-[#30363d] hover:bg-cyan-500/50 transition-colors shrink-0 z-10 cursor-row-resize" />
                  <div style={{ height: `${terminalHeight}%` }} className="shrink-0 flex flex-col">
                    <Terminal lines={terminalLines} onClear={handleClearTerminal} onCommand={handleCommand} />
                  </div>
                </div>
                {isReportOpen && (
                  <>
                    <div onMouseDown={startResizingReport} className="w-1 h-full bg-[#30363d] hover:bg-cyan-500/50 transition-colors shrink-0 z-10 cursor-col-resize" />
                    <aside style={{ width: reportWidth }} className="bg-[#0d1117] border-l border-[#30363d] flex flex-col shrink-0 relative">
                      <div className="h-9 flex items-center justify-between px-4 border-b border-[#30363d] bg-[#161b22] shrink-0">
                        <div className="flex items-center gap-2">
                          <Globe size={14} className="text-cyan-400" />
                          <span className="text-[11px] font-bold text-white uppercase tracking-wider">Analysis Report</span>
                        </div>
                        <button type="button" onClick={() => setIsReportOpen(false)} className="p-1 hover:bg-[#30363d] rounded text-[#8b949e] hover:text-white transition-colors">
                          <X size={14} />
                        </button>
                      </div>
                      <div className="flex-1 overflow-hidden">
                        <Report data={analysisResult} isProcessing={appState === 'processing'} onNewAnalysis={handleNewAnalysis} />
                      </div>
                    </aside>
                  </>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </main>
      </div>

      <footer className="h-6 bg-[#161b22] border-t border-[#30363d] flex items-center justify-between px-3 shrink-0 text-[10px] text-[#8b949e] z-50">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span>Ready</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Globe size={12} />
            <span>main</span>
          </div>
          <div className="flex items-center gap-1.5">
            <AlertTriangle size={12} />
            <span>0</span>
            <Info size={12} />
            <span>0</span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span>UTF-8</span>
          <span>TypeScript JSX</span>
          <div className="flex items-center gap-1">
            <Cpu size={12} />
            <span>IncludeGuard v0.1.0</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

const SidebarItem = ({ icon, label }: { icon: React.ReactNode; label: string }) => (
  <button type="button" className="w-full flex items-center gap-2 px-3 py-1.5 rounded-md text-[11px] font-medium text-[#8b949e] hover:bg-[#21262d] hover:text-[#c9d1d9] transition-all">
    {icon}
    {label}
  </button>
);

const FileExplorer: React.FC<{ nodes: FileNode[]; onFileClick: (fileName: string) => void }> = ({ nodes, onFileClick }) => (
  <div className="space-y-0.5">
    {nodes.map((node, i) => (
      <FileNodeItem key={i} node={node} depth={0} path="" onFileClick={onFileClick} />
    ))}
  </div>
);

const FileNodeItem: React.FC<{ node: FileNode; depth: number; path: string; onFileClick: (filePath: string) => void }> = ({ node, depth, path, onFileClick }) => {
  const [isOpen, setIsOpen] = useState(node.isOpen ?? false);
  const currentPath = path ? `${path}/${node.name}` : node.name;
  const toggle = () => {
    if (node.type === 'folder') setIsOpen(!isOpen);
    else onFileClick(currentPath);
  };
  const getIcon = () => {
    if (node.type === 'folder') return isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />;
    if (node.name.endsWith('.cpp') || node.name.endsWith('.h')) return <FileCodeIcon size={14} className="text-cyan-400" />;
    return <File size={14} className="text-[#8b949e]" />;
  };
  return (
    <div>
      <button
        type="button"
        onClick={toggle}
        className="w-full flex items-center gap-1.5 py-1 px-2 hover:bg-[#21262d] text-[#8b949e] hover:text-[#c9d1d9] transition-colors group"
        style={{ paddingLeft: `${depth * 12 + 16}px` }}
      >
        <span className="shrink-0">{getIcon()}</span>
        {node.type === 'folder' && <Folder size={14} className="text-blue-400/80 shrink-0" />}
        <span className="text-[12px] truncate">{node.name}</span>
      </button>
      {node.type === 'folder' && isOpen && node.children && (
        <div className="mt-0.5">
          {node.children.map((child, i) => (
            <FileNodeItem key={i} node={child} depth={depth + 1} path={currentPath} onFileClick={onFileClick} />
          ))}
        </div>
      )}
    </div>
  );
};
