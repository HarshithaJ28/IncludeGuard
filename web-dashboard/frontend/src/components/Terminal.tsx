import React, { useState, useEffect, useRef } from 'react';
import { Terminal as TerminalIcon, Trash2, Copy, Download } from 'lucide-react';
import type { TerminalLine } from '../types';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface TerminalProps {
  lines: TerminalLine[];
  onClear: () => void;
  onCommand?: (command: string) => void;
}

export const Terminal: React.FC<TerminalProps> = ({ lines, onClear, onCommand }) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [input, setInput] = useState('');
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [lines]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      if (input.trim()) {
        onCommand?.(input);
        setHistory(prev => [input, ...prev]);
        setInput('');
        setHistoryIndex(-1);
      }
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (historyIndex < history.length - 1) {
        const nextIndex = historyIndex + 1;
        setHistoryIndex(nextIndex);
        setInput(history[nextIndex]);
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex > 0) {
        const nextIndex = historyIndex - 1;
        setHistoryIndex(nextIndex);
        setInput(history[nextIndex]);
      } else if (historyIndex === 0) {
        setHistoryIndex(-1);
        setInput('');
      }
    }
  };

  const focusInput = () => {
    inputRef.current?.focus();
  };

  const copyToClipboard = () => {
    const text = lines.map(l => `[${l.timestamp}] ${l.text}`).join('\n');
    navigator.clipboard.writeText(text);
  };

  const downloadLog = () => {
    const text = lines.map(l => `[${l.timestamp}] ${l.text}`).join('\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `includeguard-log-${new Date().toISOString().slice(0, 10)}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col h-full bg-[#0d1117] text-[#c9d1d9] font-mono text-[13px] overflow-hidden border-r border-[#30363d]">
      <div className="flex items-center bg-[#161b22] border-b border-[#30363d] shrink-0 z-10 h-9">
        <div className="flex items-center h-full">
          <div className="px-4 h-full flex items-center gap-2 bg-[#0d1117] border-r border-[#30363d] text-xs font-medium text-white border-t-2 border-t-cyan-500">
            <TerminalIcon size={14} className="text-cyan-400" />
            <span>Terminal</span>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2 px-3">
          <button onClick={copyToClipboard} className="p-1 hover:bg-[#30363d] rounded transition-colors text-[#8b949e] hover:text-white" title="Copy Output">
            <Copy size={14} />
          </button>
          <button onClick={downloadLog} className="p-1 hover:bg-[#30363d] rounded transition-colors text-[#8b949e] hover:text-white" title="Download Logs">
            <Download size={14} />
          </button>
          <button onClick={onClear} className="p-1 hover:bg-[#30363d] rounded transition-colors text-[#8b949e] hover:text-red-400" title="Clear Terminal">
            <Trash2 size={14} />
          </button>
        </div>
      </div>
      <div
        ref={scrollRef}
        onClick={focusInput}
        className="flex-1 overflow-y-auto p-4 space-y-0.5 custom-scrollbar selection:bg-cyan-500/30 cursor-text"
      >
        {lines.map((line) => (
          <div key={line.id} className="group flex gap-3 hover:bg-[#2a2d2e] -mx-4 px-4 py-0.5 transition-colors items-start">
            <span className="text-[#858585] shrink-0 select-none opacity-50 text-[11px] mt-0.5">[{line.timestamp}]</span>
            <span className={cn(
              "whitespace-pre-wrap break-words leading-relaxed",
              line.type === 'success' && "text-[#4ec9b0]",
              line.type === 'error' && "text-[#f48771]",
              line.type === 'command' && "text-[#569cd6] font-bold",
              line.type === 'progress' && "text-[#dcdcaa]",
              line.type === 'info' && "text-[#cccccc]"
            )}>
              {line.type === 'command' && <span className="mr-2 text-[#569cd6] opacity-70">PS C:\IncludeGuard&gt;</span>}
              {line.text}
            </span>
          </div>
        ))}
        <div className="flex items-center gap-2 pt-1">
          <span className="text-[#569cd6] font-bold shrink-0">PS C:\IncludeGuard&gt;</span>
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1 bg-transparent border-none outline-none text-[#c9d1d9] caret-violet-500"
            autoFocus
          />
        </div>
      </div>
    </div>
  );
};
