# Example: Using IncludeGuard

This directory contains example C++ projects for testing IncludeGuard.

## Sample Project

The `sample_project` directory contains a small C++ project with intentional include issues:

- **main.cpp**: Has unused includes (`<map>`, `<string>`)
- **utils.h**: Has an expensive unused include (`<iostream>`)
- **processor.cpp**: Includes expensive headers (`<regex>`, `<boost>`) that aren't used

### Running Analysis

```bash
# Analyze the entire project
includeguard analyze examples/sample_project

# Inspect individual files
includeguard inspect examples/sample_project/main.cpp
includeguard inspect examples/sample_project/processor.cpp
```

### Expected Results

You should see:
- Total cost around 11,000-12,000 units
- 25-30% waste identified
- Top optimization opportunities identifying unused expensive headers
- Clear recommendations for which includes to remove

## Testing on Real Projects

Try IncludeGuard on popular open-source C++ projects:

```bash
# Clone a project
git clone https://github.com/nlohmann/json.git

# Analyze it
includeguard analyze json/include

# Export results
includeguard analyze json/include --json-output json_analysis.json
```

## Creating Test Cases

To create your own test cases:

1. Create a directory with .cpp and .h files
2. Add some unnecessary includes
3. Run IncludeGuard
4. Verify it identifies the issues

Example problematic patterns to test:
- Transitive includes (A includes B includes C, but A only needs B)
- Expensive headers like `<iostream>`, `<regex>`, `<algorithm>`
- Headers included in .h files but only used in .cpp files
- Forward declaration opportunities
