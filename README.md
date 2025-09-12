# QuantumQA - Lightweight Agentic UI Testing Framework

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/badge/PyPI-quantumqa-blue.svg)](https://pypi.org/project/quantumqa/)

## Overview

QuantumQA is a revolutionary lightweight testing framework that uses AI agents to execute UI tests from natural language instructions. No databases, no servers, no complex setup - just install with pip and start testing with AI-powered vision.

**🎯 Zero Infrastructure Required** • **🤖 Multi-Agent Intelligence** • **👁️ Vision-Powered Element Detection**

## Key Features

🎭 **Multi-Agent System**: Specialized AI agents collaborate to understand, plan, and execute tests
🔍 **Vision-First Testing**: Uses GPT-4V/Claude-3.5 to identify UI elements without selectors
📝 **Natural Language Tests**: Write tests in plain English - no code required
⚡ **Zero Setup**: Single `pip install` command gets you testing immediately
🛡️ **Self-Healing**: Automatically adapts to UI changes and recovers from failures
🚀 **Multi-Browser**: Chrome, Firefox, Safari, Edge via Playwright
💰 **Cost-Optimized**: Intelligent caching reduces LLM API costs by 50%+
📊 **Rich Output**: Beautiful terminal progress and detailed test results

## Agent Architecture

QuantumQA uses multiple specialized AI agents that collaborate to execute your tests:

```
🎭 Orchestrator Agent → Coordinates the entire test execution
    ↓
🔍 Decomposer Agent → Breaks instructions into atomic steps  
    ↓
📋 Planner Agent → Creates optimized execution plan
    ↓  
🎯 Critique Agent → Validates plan before execution
    ↓
🧭 Navigator Agent → Handles page navigation
    ↓
👁️ Element Detector Agent → Finds UI elements using vision
    ↓
⚡ Action Executor Agent → Performs interactions
    ↓
✅ Validator Agent → Verifies outcomes
```

### Minimal Technology Stack

- **Core Framework**: Python 3.11+, Pydantic, Click
- **Browser Automation**: Playwright
- **AI/Vision**: OpenAI GPT-4V, Anthropic Claude-3.5
- **Image Processing**: Pillow (basic), OpenCV (advanced)
- **UI**: Rich terminal output
- **Dependencies**: Only 7 core packages, ~50MB install

## Quick Start

### Installation (30 seconds)

```bash
# Install QuantumQA
pip install quantumqa

# Verify installation
quantumqa --version

# Set up your OpenAI API key
export OPENAI_API_KEY="sk-your-api-key-here"
```

That's it! No databases, no servers, no configuration files needed.

### Your First Test (2 minutes)

#### 1. Create a test file

```bash
# Create test_login.txt
echo "Navigate to https://demo.example.com
Click the Login button
Enter 'demo@example.com' in the email field
Enter 'password123' in the password field  
Click the Submit button
Verify the dashboard page loads" > test_login.txt
```

#### 2. Run the test

```bash
# Execute your test
quantumqa run test_login.txt

# Watch the agents work their magic! 
# ✨ Orchestrator coordinates the execution
# 🔍 Decomposer breaks down instructions  
# 📋 Planner creates execution strategy
# 🎯 Critic validates the plan
# 🧭 Navigator handles page navigation
# 👁️ Vision agents find elements
# ⚡ Executor performs actions
# ✅ Validator checks outcomes
```

#### 3. Using the Python API

```python
from quantumqa import QuantumQA

# Initialize the framework
qa = QuantumQA(llm_provider="openai", browser="chrome")

# Execute test with natural language
result = qa.run_test([
    "Navigate to https://example.com",
    "Click the login button",
    "Enter credentials and submit",
    "Verify successful login"
])

# Get results
print(f"Test Status: {result.status}")
print(f"Execution Time: {result.execution_time}s")
print(f"Cost: ${result.cost_estimate}")

# Save artifacts (screenshots, logs)
result.save_artifacts("./test_results/")
```

## Real-World Examples

### E-commerce Purchase Flow

```bash
# ecommerce_test.txt
Navigate to https://shop.example.com
Search for 'wireless headphones' 
Click on the first product with rating above 4 stars
Select Black color if available
Add item to cart
Proceed to checkout
Fill in shipping address form
Select Express Delivery option
Verify order total is calculated correctly
```

```bash
quantumqa run ecommerce_test.txt --browser chrome --save-screenshots
```

### Form Validation Testing

```bash
# form_validation.txt  
Navigate to https://forms.example.com/contact
Submit the form without filling required fields
Verify error messages appear for empty fields
Fill in a valid email address
Enter phone number in wrong format
Verify phone validation error appears
Correct the phone number format
Submit form successfully
Verify success message is displayed
```

```bash
quantumqa run form_validation.txt --debug --max-cost 0.50
```

### API Testing with UI Verification

```python
from quantumqa import QuantumQA

# Test that combines API calls with UI verification
qa = QuantumQA(llm_provider="openai")

# Custom test with setup and teardown
result = qa.run_test([
    "Navigate to https://api-demo.example.com",
    "Click 'Create New User' button",
    "Fill in user registration form with test data",
    "Submit the form",
    "Verify success message appears",
    "Navigate to user list page", 
    "Verify new user appears in the list"
], config={
    "timeout": 60,
    "screenshot_on_failure": True,
    "cost_limit": 1.00
})

print(f"Test {'PASSED' if result.success else 'FAILED'}")
```

## CLI Commands

```bash
# Basic usage
quantumqa run test_file.txt                    # Run test from file
quantumqa run "Navigate to google.com"         # Run inline test

# Configuration options
quantumqa run test.txt --browser firefox       # Use specific browser
quantumqa run test.txt --headless false        # Show browser window
quantumqa run test.txt --timeout 60            # Set timeout
quantumqa run test.txt --max-cost 0.25         # Limit test cost

# Output and debugging
quantumqa run test.txt --save-artifacts        # Save screenshots/logs
quantumqa run test.txt --debug                 # Verbose output
quantumqa run test.txt --format json           # JSON output

# Validation (without execution)
quantumqa validate test.txt                    # Check test syntax
quantumqa plan test.txt                        # Show execution plan

# Utilities
quantumqa --version                             # Show version
quantumqa examples                              # List example tests
quantumqa cost-estimate test.txt               # Estimate test cost
```

## Configuration

### Environment Variables (Optional)

```bash
# LLM Provider Setup (choose one)
export OPENAI_API_KEY="sk-..."                 # Primary choice
export ANTHROPIC_API_KEY="ant-..."             # Alternative

# Optional Configuration  
export QUANTUMQA_BROWSER="chrome"              # Default browser
export QUANTUMQA_HEADLESS="true"               # Run headless
export QUANTUMQA_TIMEOUT="30"                  # Default timeout
export QUANTUMQA_MAX_COST="0.50"              # Cost limit per test
```

### Configuration File (Optional)

```json
// ~/.quantumqa/config.json
{
    "llm_provider": "openai",
    "browser": "chrome", 
    "headless": true,
    "timeout": 30,
    "screenshot_on_failure": true,
    "max_cost_per_test": 0.50,
    "artifacts_dir": "./quantumqa_artifacts"
}
```

## Development

### Simple Project Structure

```
quantumqa/
├── quantumqa/
│   ├── agents/              # All AI agents
│   │   ├── orchestrator.py
│   │   ├── decomposer.py
│   │   ├── planner.py
│   │   └── executor.py
│   ├── core/               # Core framework logic
│   │   ├── browser.py
│   │   ├── llm.py
│   │   └── messaging.py
│   ├── cli/                # Command line interface
│   └── utils/              # Utilities
├── tests/                  # Framework tests
├── examples/               # Example tests
└── pyproject.toml          # Modern Python packaging
```

### Contributing

```bash
# Fork and clone the repository
git clone https://github.com/your-fork/quantumqa.git
cd quantumqa

# Install in development mode  
pip install -e .[dev]

# Run tests
pytest tests/

# Run examples
quantumqa run examples/login_test.txt

# Submit a pull request
```

## Troubleshooting

### Common Issues

1. **"Element Not Found" Errors**
   - Try more specific descriptions: "blue Login button" vs "Login button"
   - Check if page finished loading: add wait instructions
   - Use `--debug` flag to see what the vision model sees

2. **High API Costs**
   - Enable caching: `--cache` flag (reduces costs by 50-70%)
   - Use cost limits: `--max-cost 0.25` 
   - Optimize descriptions: be concise but specific

3. **Browser Issues**
   - Try different browser: `--browser firefox`
   - Run with GUI: `--headless false` to see what's happening
   - Check browser is installed: `playwright install`

### Debug Mode

```bash
# See detailed execution steps
quantumqa run test.txt --debug

# Save all artifacts for troubleshooting
quantumqa run test.txt --save-artifacts --debug

# Estimate cost before running
quantumqa cost-estimate test.txt
```

## Features & Roadmap

### ✅ Current Features (v0.1)
- Multi-agent test execution
- Vision-based element detection
- Natural language instructions
- Chrome/Firefox/Safari support
- Intelligent error recovery

### 🔄 Coming Soon (v0.2)
- Mobile device testing
- Advanced caching system
- CI/CD integrations
- Test result sharing

### 📋 Future (v1.0)
- AI-powered test generation
- Community test repository  
- Advanced analytics
- Team collaboration features

## Why QuantumQA?

**Traditional Testing:**
```python
# Brittle, breaks when UI changes
driver.find_element(By.CSS_SELECTOR, "#login-btn-2023-new").click()
driver.find_element(By.XPATH, "//input[@data-testid='email-field']").send_keys("test@example.com")
```

**QuantumQA Testing:**
```bash
# Resilient, adapts to changes
Click the login button
Enter test@example.com in the email field
```

**The difference:** QuantumQA uses AI vision to understand your UI like a human would, making tests that survive redesigns, A/B tests, and framework changes.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Community

- 🐙 **GitHub**: [github.com/quantumqa/quantumqa](https://github.com/quantumqa/quantumqa)
- 💬 **Discord**: Join our community for help and discussions  
- 🐦 **Twitter**: [@quantumqa](https://twitter.com/quantumqa) for updates
- 📧 **Email**: hello@quantumqa.com for enterprise inquiries

---

**🚀 Ready to revolutionize your UI testing? `pip install quantumqa` and start testing with AI!**
