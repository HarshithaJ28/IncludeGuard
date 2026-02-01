# IncludeGuard - Quick Start Guide

## 🚀 5-Minute Quick Start

### Step 1: Installation (1 minute)

```bash
# Navigate to the project directory
cd includeguard

# Install the package
pip install -e .

# Verify installation
includeguard --version
```

### Step 2: Try the Example (2 minutes)

```bash
# Analyze the sample project
includeguard analyze examples/sample_project

# Inspect a single file
includeguard inspect examples/sample_project/processor.cpp
```

You should see:
- ✅ Beautiful colored output
- 📊 Statistics about the project
- 💰 Cost estimates for each include
- 🎯 Optimization opportunities

### Step 3: Analyze Your Own Project (2 minutes)

```bash
# Basic analysis
includeguard analyze /path/to/your/cpp/project

# With JSON export
includeguard analyze /path/to/your/cpp/project --json-output report.json

# Limit to specific extensions
includeguard analyze . --extensions .cpp --extensions .h
```

## 📝 Common Use Cases

### 1. Pre-Commit Check
```bash
# In your CI/CD pipeline
includeguard analyze . --json-output build-analysis.json
# Parse JSON to fail if waste > threshold
```

### 2. Find Expensive Includes
```bash
includeguard analyze . | grep "Est. Cost"
# Look for headers with cost > 2000
```

### 3. Clean Up Legacy Code
```bash
# Analyze
includeguard analyze legacy-module --json-output legacy-report.json

# Review report
# Manually remove identified unused headers
# Re-run to verify improvement
```

### 4. Before Major Refactoring
```bash
# Export dependency graph
includeguard analyze . --dot-output dependencies.dot

# Visualize with Graphviz (if installed)
dot -Tpng dependencies.dot -o dependencies.png
```

## 💡 Understanding the Output

### Cost Units
- **< 500**: Lightweight (basic headers, simple STL)
- **500-1000**: Moderate (containers, algorithms)
- **1000-2000**: Expensive (iostream, chrono, threading)
- **> 2000**: Very Expensive (regex, boost, template-heavy)

### Waste Percentage
- **< 10%**: Excellent include hygiene ✅
- **10-25%**: Room for improvement ⚠️
- **25-50%**: Significant waste 🔴
- **> 50%**: Critical - major cleanup needed 🚨

### Usage Confidence
- **> 66%**: Header is definitely used ✅
- **33-66%**: Uncertain - manual check recommended ⚠️
- **< 33%**: Likely unused - safe to remove 🗑️

## 🐛 Troubleshooting

### "No C++ files found"
- Check you're in the right directory
- Use `--extensions` to specify custom extensions
- Ensure files have correct extensions (.cpp, .h, etc.)

### "Module not found" errors
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Reinstall package
pip install -e .
```

### Slow on large projects
```bash
# Limit analysis
includeguard analyze . --max-files 100

# Or analyze specific directories
includeguard analyze src/
```

## 🎯 What to Do With Results

1. **Start with Top Opportunities**
   - Remove headers with high cost and low usage confidence
   - Test after each removal

2. **Focus on Frequently Compiled Files**
   - Headers with high "Wasted" cost in often-compiled files
   - Main translation units (.cpp files)

3. **Check Before Removing**
   - Even with low confidence, manually verify
   - Check if header is needed for forward declarations
   - Consider if it's used in #ifdef blocks

4. **Iterate**
   - Remove one header at a time
   - Compile to verify
   - Re-run IncludeGuard to see improvement

## 📚 Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [examples/README.md](examples/README.md) for more examples
- Review [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) for technical details
- Try on real open-source projects (nlohmann/json, fmt, spdlog)

## 🤝 Need Help?

- Check the [Instructions.md](Instructions.md) for implementation details
- Review test files in `tests/` for code examples
- All core functionality is documented with docstrings

---

**Happy Optimizing! 🚀**
