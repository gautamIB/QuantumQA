# QuantumQA - AI-Powered UI and API Testing Framework

QuantumQA is a Python-based testing framework that uses AI vision and natural language processing to execute UI tests from plain text instructions. It also supports API testing with YAML/JSON test files.

## Features

- **🌐 UI Testing**: Execute tests from natural language instructions
- **🔌 API Testing**: Test REST APIs with YAML/JSON test definitions
- **👁️ Vision-Powered**: Uses OpenAI GPT-4V for intelligent element detection
- **🚀 Browser Automation**: Powered by Playwright
- **🔄 Browser Reuse**: Connect to existing Chrome instances for faster testing
- **📸 Visual Reports**: Generate GIFs and screenshots automatically
- **🔐 Credential Management**: Secure credential handling with encryption

## Installation

### Prerequisites

- Python 3.9 or higher
- Google Chrome or Chromium browser
- OpenAI API key

### Setup Steps

1. **Clone or download the repository**

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Install Playwright browsers**:
```bash
python3 -m playwright install chromium
```

4. **Set up credentials** (optional):
```bash
# Copy the template
cp quantumqa/config/credentials.template.yaml quantumqa/config/credentials.yaml

# Edit credentials.yaml with your API keys and test credentials
```

5. **Set OpenAI API key** (required for vision-based testing):
```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

## Quick Start

### UI Testing

1. **Create a test file** (e.g., `my_test.txt`):
```
Navigate to https://www.google.com
Click the search box
Type 'QuantumQA testing' in the search box
Click the Google Search button
Wait 3 seconds
Verify that the page shows search results
```

2. **Run the test**:
```bash
# Using the main runner (recommended)
python quantumqa_runner.py examples/e2e_google_search.txt --visible

# Or use the vision-enhanced runner
python run_vision_test.py examples/e2e_google_search.txt --visible

# Or use the generic Chrome engine
python scripts/run_generic_test.py examples/e2e_google_search.txt --visible
```

### API Testing

1. **Create an API test file** (e.g., `api_test.yaml`):
```yaml
name: Sample API Test
base_url: https://jsonplaceholder.typicode.com
tests:
  - name: Get all posts
    endpoint: /posts
    method: GET
    expected_status: 200
    validations:
      - field: $[0].userId
        expected_type: integer
```

2. **Run the API test**:
```bash
python quantumqa_runner.py examples/api/jsonplaceholder_tests.yaml
```

## Available Runners

The framework provides multiple ways to run tests:

### 1. Main Runner (`quantumqa_runner.py`)
**Recommended** - Auto-detects UI vs API tests and uses appropriate engine.

```bash
# UI test (auto-detected from .txt file)
python quantumqa_runner.py examples/e2e_google_search.txt --visible

# API test (auto-detected from .yaml file)
python quantumqa_runner.py examples/api/chatbot_tests.yaml

# Force new browser (don't connect to existing)
python quantumqa_runner.py examples/my_test.txt --visible --new-browser

# Use custom credentials file
python quantumqa_runner.py examples/test.txt --credentials path/to/credentials.yaml
```

### 2. Vision Test Runner (`run_vision_test.py`)
Vision-enhanced UI testing with AI element detection.

```bash
python run_vision_test.py examples/conversation_with_login.txt --visible

# Connect to existing Chrome (faster, preserves auth)
python run_vision_test.py examples/test.txt --connect-existing --visible

# Launch fresh browser
python run_vision_test.py examples/test.txt --new-browser --visible
```

### 3. Generic Chrome Runner (`scripts/run_generic_test.py`)
Basic Chrome engine without vision features (faster, lower cost).

```bash
python scripts/run_generic_test.py examples/e2e_form_test.txt --visible
```

### 4. Chrome Test Runner (`scripts/run_chrome_test.py`)
Simple Chrome test runner with profile support.

```bash
python scripts/run_chrome_test.py examples/my_test.txt --visible
```

## Common Options

Most runners support these options:

- `--visible` / `-v`: Run browser in visible mode (default: headless)
- `--credentials` / `--creds`: Path to credentials file
- `--new-browser`: Force launch new browser (don't connect to existing)
- `--connect-existing`: Connect to existing Chrome on debug port (default: 9222)
- `--debug-port`: Chrome remote debugging port (default: 9222)
- `--run-name`: Custom name for GIF/report files
- `--performance-measurement`: Enable performance measurement mode
- `--disable-caching`: Disable browser caching
- `--disable-performance`: Disable performance optimizations

## Browser Reuse (Faster Testing)

To speed up tests and preserve authentication:

1. **Start Chrome with debugging** (Terminal 1):
```bash
python start_chrome_debug.py
```

2. **Run tests** (Terminal 2):
```bash
python quantumqa_runner.py examples/test.txt --visible
```

Tests will automatically connect to the existing Chrome instance, preserving cookies and login sessions.

See [BROWSER_REUSE_GUIDE.md](BROWSER_REUSE_GUIDE.md) for more details.

## Test File Examples

### UI Test (`.txt` file)
```
Navigate to https://example.com
Click the Login button
Enter 'user@example.com' in the email field
Enter 'password123' in the password field
Click the Submit button
Verify that the dashboard page loads
```

### API Test (`.yaml` file)
```yaml
name: User API Tests
base_url: https://api.example.com
headers:
  Content-Type: application/json
tests:
  - name: Create user
    endpoint: /users
    method: POST
    payload:
      name: "John Doe"
      email: "john@example.com"
    expected_status: 201
    validations:
      - field: $.name
        expected_value: "John Doe"
```

See the `examples/` directory for more examples.

## Project Structure

```
QuantumQA/
├── quantumqa/              # Main framework code
│   ├── agents/            # AI agent implementations
│   ├── api/               # API testing engine
│   ├── engines/           # Browser engines (Chrome, Vision)
│   ├── executors/         # Action executors
│   ├── finders/           # Element finders
│   ├── parsers/           # Instruction parsers
│   ├── security/          # Credential management
│   └── config/            # Configuration files
├── examples/              # Example test files
│   ├── api/               # API test examples
│   └── legacy_test/       # Legacy UI test examples
├── scripts/               # Utility scripts
├── docs/                  # Documentation
├── quantumqa_runner.py    # Main test runner
├── run_vision_test.py     # Vision test runner
└── requirements.txt       # Python dependencies
```

## Troubleshooting

### Chrome Browser Won't Launch

1. **Check Playwright browsers are installed**:
```bash
python3 check_permissions.py
```

2. **If browsers missing, install them**:
```bash
python3 -m playwright install chromium
```

3. **Check macOS permissions** (if on macOS):
   - System Settings > Privacy & Security > Accessibility
   - Add Terminal.app to allowed apps

See [docs/CHROME_PERMISSIONS_FIX.md](docs/CHROME_PERMISSIONS_FIX.md) for detailed troubleshooting.

### Connection Refused Errors

If you see `ECONNREFUSED` errors when trying to connect to existing Chrome:
- This is normal if Chrome isn't running with debugging enabled
- The framework will automatically fallback to launching a new browser
- Or start Chrome manually: `python start_chrome_debug.py`

### Element Not Found

- Use more specific descriptions: "blue Login button" vs "Login button"
- Add wait steps: "Wait 2 seconds" before interacting
- Run with `--visible` to see what's happening
- Check if page has finished loading

### API Key Issues

Ensure your OpenAI API key is set:
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

Or pass it in credentials file:
```yaml
api_keys:
  openai: "sk-your-key-here"
```

## Documentation

- [API Documentation](API_DOCUMENTATION.md) - Complete API reference
- [API Quick Start](API_QUICK_START.md) - API testing guide
- [Browser Reuse Guide](BROWSER_REUSE_GUIDE.md) - Reusing Chrome instances
- [Architecture](docs/ARCHITECTURE.md) - Framework architecture
- [Chrome Permissions Fix](docs/CHROME_PERMISSIONS_FIX.md) - Browser launch troubleshooting

## Requirements

See `requirements.txt` for complete list. Key dependencies:
- `playwright>=1.40.0` - Browser automation
- `openai>=1.3.8` - AI/Vision API
- `pydantic>=2.5.0` - Data validation
- `rich>=13.7.0` - Terminal UI
- `PyYAML>=5.4.1` - Configuration parsing

## License

See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues and questions:
- Check the [Troubleshooting](#troubleshooting) section
- Review the documentation in `docs/`
- Check example tests in `examples/`

---

**Ready to start testing?** Create a `.txt` file with your test steps and run:
```bash
python quantumqa_runner.py your_test.txt --visible
```
