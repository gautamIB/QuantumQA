# QuantumQA POC - Proof of Concept

## Overview

This is the initial Proof of Concept (POC) for QuantumQA - a lightweight agentic UI testing framework that uses AI to execute tests from natural language instructions.

## What's Implemented in POC

### ✅ Core Components
- **Base Agent System**: Foundation for multi-agent communication
- **Orchestrator Agent**: Coordinates test execution
- **Browser Automation**: Playwright integration for browser control
- **Vision-LLM Integration**: OpenAI GPT-4V for element detection
- **CLI Interface**: Command-line tool for running tests
- **Data Models**: Core data structures for test results

### ✅ Supported Actions
- **Navigate**: Go to URLs
- **Click**: Click on elements (found via AI vision)
- **Type**: Enter text into input fields  
- **Verify**: Check if elements exist
- **Wait**: Pause execution

## Quick Start

### 1. Setup Environment

```bash
# Ensure Python 3.11+ is installed
python --version

# Run setup script
python setup_poc.py
```

### 2. Set API Key

```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

### 3. Run Your First Test

```bash
# Run the example test
quantumqa run examples/simple_test.txt

# Or run inline
quantumqa run "Navigate to https://example.com"
```

## Example Tests

### Simple Navigation Test
```bash
quantumqa run "Navigate to https://google.com and verify page loads"
```

### Login Flow Test (create login_test.txt)
```
Navigate to https://demo-site.com/login
Click the email input field
Enter 'test@example.com' in the email field
Click the password field  
Enter 'password123' in the password field
Click the login button
Verify dashboard appears
```

### Using Python API
```python
from quantumqa import QuantumQA

# Initialize framework
qa = QuantumQA(api_key="sk-your-key", headless=False)  # headless=False to see browser

# Run test
result = qa.run_test_sync([
    "Navigate to https://example.com",
    "Verify the page title contains 'Example'"
])

print(f"Test Status: {result.status}")
print(result.summary())
```

## CLI Commands

```bash
# Run test from file
quantumqa run test_file.txt

# Run inline test
quantumqa run "Navigate to google.com"

# Options
quantumqa run test.txt --browser firefox --no-headless --debug

# Validate instructions (without running)
quantumqa validate test.txt

# Show examples
quantumqa examples

# Help
quantumqa --help
```

## Current Limitations (POC)

### Known Issues
1. **Simple Element Detection**: Basic vision-LLM prompts, may not work on complex UIs
2. **No Advanced Agents**: Only Orchestrator implemented, missing Decomposer/Planner/Critic agents
3. **Basic Error Handling**: Limited retry/recovery mechanisms
4. **No Caching**: Every element detection calls LLM (expensive)
5. **Simple Text Extraction**: Crude parsing of element descriptions and input text

### Browser Support
- ✅ Chromium (primary, best tested)
- ⚠️ Firefox (basic support)
- ⚠️ WebKit/Safari (basic support)

### Cost Considerations
- Each element detection ≈ $0.01-0.03
- Simple 4-step test ≈ $0.05-0.15
- No caching yet, so repeated tests cost full amount

## Troubleshooting

### Installation Issues
```bash
# If setup_poc.py fails, try manual installation:
pip install -r requirements.txt
playwright install chromium
pip install -e .
```

### API Key Issues
```bash
# Test API key works:
python -c "import openai; print(openai.api_key)"
```

### Browser Issues
```bash
# Reinstall browsers:
playwright install --force
```

### Element Not Found
- Try more specific descriptions: "blue Submit button" vs "Submit button"
- Use `--no-headless --debug` to see what the browser is showing
- Check if page is fully loaded before element detection

### Test Running Tips
1. **Be Specific**: "Click the red Login button in the top right" vs "click login"
2. **Use Quotes**: Enter 'your text here' for text input
3. **Add Waits**: "Wait 2 seconds" if page needs time to load
4. **Verify Steps**: Add verification after important actions

## Architecture (POC Version)

```
User Input (CLI/Python API)
    ↓
OrchestratorAgent
    ↓
BrowserManager (Playwright)
    ↓
VisionLLMClient (OpenAI GPT-4V)
    ↓
Action Execution & Results
```

## Next Steps for Full Framework

1. **Implement Missing Agents**:
   - DecomposerAgent: Break complex instructions into steps
   - PlannerAgent: Create optimized execution plans
   - CriticAgent: Validate plans before execution
   - ValidatorAgent: Verify action outcomes

2. **Add Intelligence**:
   - Better element detection prompts
   - Context-aware retry strategies
   - Smart caching system

3. **Enhance Reliability**:
   - Multiple detection fallbacks (OCR, DOM analysis)
   - Better error recovery
   - Adaptive element detection

4. **Performance**:
   - Response caching
   - Image optimization
   - Parallel agent execution

## Testing the POC

### Test 1: Simple Navigation
```bash
quantumqa run "Navigate to https://httpbin.org/html"
```

### Test 2: Element Interaction  
```bash
quantumqa run "Navigate to https://httpbin.org/forms/post and click the submit button"
```

### Test 3: Text Input
```bash
echo "Navigate to https://httpbin.org/forms/post
Enter 'Test User' in the customer name field
Click submit button" > test_form.txt

quantumqa run test_form.txt --debug
```

## Success Criteria for POC

✅ **Installation**: Single setup script works  
✅ **Basic Navigation**: Can navigate to URLs  
✅ **Element Detection**: Can find and click basic elements using AI vision  
✅ **Text Input**: Can type text into form fields  
✅ **CLI Interface**: User-friendly command line tool  
✅ **Error Handling**: Graceful failure with helpful error messages  
✅ **Python API**: Can be used programmatically  

The POC successfully demonstrates the core concept: **AI agents can execute UI tests from natural language instructions without brittle selectors**! 🎉
