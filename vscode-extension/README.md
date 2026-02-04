# IncludeGuard VS Code Extension

Real-time C++ include analysis with build cost estimates directly in your editor.

## Features

- **🚀 Real-time Analysis**: Automatically analyze files on save or open
- **⚠️ Inline Warnings**: See unused includes as warnings in your code
- **💰 Cost Estimates**: View build cost estimates for each include
- **📊 Status Bar**: See project-wide statistics at a glance
- **🔧 Quick Actions**: One-click commands to analyze files or projects

## Requirements

- **Python 3.8+** installed and in PATH
- **IncludeGuard** Python package installed:
  ```bash
  pip install includeguard
  ```

## Usage

### Automatic Analysis

The extension automatically analyzes C++ files when you:
- Open a file
- Save a file

### Manual Commands

- **Analyze Current File**: `Ctrl+Shift+P` → `IncludeGuard: Analyze Current File`
- **Analyze Entire Project**: `Ctrl+Shift+P` → `IncludeGuard: Analyze Entire Project`
- **Clear Warnings**: `Ctrl+Shift+P` → `IncludeGuard: Clear Warnings`

### What You'll See

1. **Inline Warnings** 🟡  
   Unused includes appear as warnings with estimated cost:
   ```
   #include <vector>  // ⚠️ Unused include 'vector' (costs 1200 units)
   ```

2. **Cost Decorations** 💰  
   Each include shows its build cost:
   ```
   #include <iostream>    // 💰 1.2k units ✓
   #include <algorithm>   // 💰 2.5k units ✗
   ```

3. **Status Bar** 📊  
   Bottom right shows:
   ```
   🛡️ IncludeGuard: 15.3% waste (2400 units)
   ```

## Extension Settings

- `includeguard.pythonPath`: Path to Python executable (default: `"python"`)
- `includeguard.analyzeOnSave`: Auto-analyze on save (default: `true`)
- `includeguard.analyzeOnOpen`: Auto-analyze when opening files (default: `true`)
- `includeguard.costThreshold`: Minimum cost to show warnings in units (default: `500`)
- `includeguard.showCostDecorations`: Show cost estimates inline (default: `true`)

## Troubleshooting

### "Python not found" error
Make sure Python is in your PATH or set the full path in settings:
```json
"includeguard.pythonPath": "C:\\Python39\\python.exe"
```

### "includeguard module not found"
Install the Python package:
```bash
pip install includeguard
```

Or install from source:
```bash
cd /path/to/includeguard
pip install -e .
```

## How It Works

1. Extension calls `includeguard inspect <file> --json` using Python
2. Parses JSON output containing include analysis
3. Displays warnings and decorations in VS Code
4. Updates status bar with project statistics

## Performance

- Analysis speed: ~39ms per file
- Works without C++ compilation
- Minimal impact on editor performance

## License

MIT

## Links

- [GitHub Repository](https://github.com/HarshithaJ28/IncludeGuard)
- [Report Issues](https://github.com/HarshithaJ28/IncludeGuard/issues)
