# QuantumQA - Lightweight Agentic Framework Technology Stack

## Overview

This document defines the minimal, lightweight technology stack for QuantumQA's agentic framework. The focus is on minimal dependencies, easy installation, and zero infrastructure requirements while maintaining powerful AI-driven testing capabilities.

## Design Philosophy

- **Minimal Dependencies**: Only essential packages required
- **Zero Infrastructure**: No databases, message queues, or external services
- **Single Command Install**: `pip install quantumqa` and you're ready
- **Pure Python**: Runs anywhere Python 3.11+ runs
- **In-Memory Processing**: All data structures exist only during execution
- **Framework-First**: Built as a testing framework, not a service

## Core Dependencies (Required)

### Essential Framework
```python
# requirements.txt - Core dependencies only
playwright==1.40.0          # Browser automation engine
openai==1.3.8               # Primary vision-LLM integration
anthropic==0.7.8            # Alternative LLM provider
pydantic==2.5.0             # Data validation and modeling
click==8.1.7                # CLI interface
rich==13.7.0                # Beautiful terminal output
pillow==10.1.0              # Basic image processing
```

**Total size**: ~50MB installation
**Installation time**: <2 minutes
**No external services required**

**Rationale for Core Dependencies**:
- **Playwright**: Modern, reliable browser automation with excellent API
- **OpenAI/Anthropic**: Vision-LLM capabilities for element detection
- **Pydantic**: Type safety and data validation for agent communication
- **Click**: Professional CLI interface
- **Rich**: Beautiful terminal output and progress indicators
- **Pillow**: Basic image processing (resize, compress)

## Optional Dependencies (Enhanced Features)

### Advanced Image Processing
```python
# pip install quantumqa[vision]
opencv-python==4.8.1.78     # Advanced computer vision
numpy==1.24.3               # Numerical processing
```

### Environment Management
```python  
# pip install quantumqa[env]
python-dotenv==1.0.0        # Environment variables
```

### HTTP Utilities
```python
# pip install quantumqa[http]
requests==2.31.0            # HTTP requests for webhooks
httpx==0.25.2               # Async HTTP client
```

### Development Tools
```python
# pip install quantumqa[dev]
pytest==7.4.3              # Testing framework
black==23.11.0              # Code formatting
mypy==1.7.1                 # Type checking
```

## Installation Options

### Basic Installation (Recommended)
```bash
# Minimal installation - just core features
pip install quantumqa

# Verify installation
quantumqa --version
```

### Full Installation
```bash
# All optional features
pip install quantumqa[full]

# Or specific feature sets
pip install quantumqa[vision,env,http]
```

### Development Installation
```bash
# Clone and install in development mode
git clone https://github.com/your-org/quantumqa.git
cd quantumqa
pip install -e .[dev]
```

## Framework Architecture

### Agent-Based Design
```python
# Core agent classes (built-in)
class OrchestratorAgent:     # Coordinates all operations
class DecomposerAgent:       # Breaks down instructions
class PlannerAgent:          # Creates execution plans
class CritiqueAgent:         # Validates plans
class NavigatorAgent:        # Handles navigation
class ElementDetectorAgent:  # Finds UI elements
class ActionExecutorAgent:   # Performs actions
class ValidatorAgent:        # Verifies outcomes
```

### Communication Protocol
```python
# Lightweight message passing (in-memory)
@dataclass
class AgentMessage:
    sender: str
    recipient: str
    message_type: str
    payload: Dict[str, Any]
    timestamp: datetime
```

## Data Structures (In-Memory Only)

### Core Data Models
```python
# No database schemas - pure Python data classes
@dataclass
class TestResult:
    test_id: str
    instructions: List[str]
    status: TestStatus  # SUCCESS, FAILED, PARTIAL
    execution_time: float
    agent_interactions: int
    llm_api_calls: int
    total_cost: float
    steps: List[StepResult]
    artifacts: List[Artifact]
    
@dataclass 
class StepResult:
    step_number: int
    instruction: str
    agent_used: str
    status: StepStatus
    execution_time: float
    screenshot_path: Optional[str]
    error_message: Optional[str]

@dataclass
class ExecutionPlan:
    steps: List[ExecutionStep]
    dependencies: Dict[int, List[int]]
    estimated_duration: float
    validation_points: List[int]
```

## Configuration Management

### Environment Variables (Optional)
```python
# .env file (optional - uses defaults if not present)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=ant-...
QUANTUMQA_BROWSER=chrome        # Default browser
QUANTUMQA_HEADLESS=true         # Run headless by default
QUANTUMQA_TIMEOUT=30            # Default timeout in seconds
QUANTUMQA_MAX_COST_PER_TEST=1.00  # Cost limit per test
```

### Runtime Configuration
```python
# Configuration through code or CLI
config = QuantumQAConfig(
    llm_provider="openai",
    browser="chrome",
    headless=True,
    screenshot_on_failure=True,
    max_cost_per_test=0.50,
    timeout=30
)

qa = QuantumQA(config=config)
```

## Development Environment

### Lightweight Project Structure
```
quantumqa/
├── quantumqa/
│   ├── agents/              # All agent implementations
│   │   ├── orchestrator.py
│   │   ├── decomposer.py
│   │   ├── planner.py
│   │   ├── critic.py
│   │   └── executor.py
│   ├── core/               # Core framework logic
│   │   ├── browser.py      # Browser management
│   │   ├── llm.py          # LLM integrations  
│   │   └── messaging.py    # Agent communication
│   ├── cli/                # Command line interface
│   └── utils/              # Utilities and helpers
├── tests/                  # Framework tests
├── examples/               # Usage examples
├── docs/                   # Documentation
├── pyproject.toml          # Modern Python packaging
└── README.md
```

### Package Configuration (pyproject.toml)
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "quantumqa"
version = "0.1.0"
description = "Lightweight agentic UI testing framework"
authors = [{name = "QuantumQA Team"}]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "playwright>=1.40.0",
    "openai>=1.3.8",
    "anthropic>=0.7.8", 
    "pydantic>=2.5.0",
    "click>=8.1.7",
    "rich>=13.7.0",
    "pillow>=10.1.0"
]

[project.optional-dependencies]
vision = ["opencv-python>=4.8.1", "numpy>=1.24.3"]
env = ["python-dotenv>=1.0.0"]
http = ["requests>=2.31.0", "httpx>=0.25.2"]  
dev = ["pytest>=7.4.3", "black>=23.11.0", "mypy>=1.7.1"]
full = ["quantumqa[vision,env,http]"]

[project.scripts]
quantumqa = "quantumqa.cli:main"

[project.urls]
Homepage = "https://github.com/your-org/quantumqa"
Documentation = "https://docs.quantumqa.com"
Repository = "https://github.com/your-org/quantumqa.git"
```

## Testing Strategy

### Framework Testing (Internal)
```python
# Test the framework itself
pytest tests/                    # Unit tests for agents
pytest tests/integration/        # Integration tests
pytest tests/examples/           # Example test validation
```

### User Testing (External)
```python
# Users test their applications
quantumqa run my_test.txt
quantumqa validate my_instructions.txt
```

## Performance Characteristics

### Memory Usage
- **Base Framework**: ~20MB RAM
- **Per Browser Session**: ~100-200MB RAM
- **Per Test Execution**: ~5-10MB RAM (temporary)
- **No Persistent Storage**: 0 bytes disk usage

### Execution Speed
- **Framework Startup**: <2 seconds
- **Agent Communication**: <10ms per message
- **LLM API Calls**: 2-10 seconds per call
- **Browser Actions**: 100-500ms per action

### Cost Estimates
- **Basic Test (5 steps)**: $0.10-0.30
- **Complex Test (20 steps)**: $0.50-1.50
- **Image Processing**: Included in LLM costs
- **No Infrastructure Costs**: $0

## Security Considerations

### API Key Management
```python
# Secure API key handling
import os
from pathlib import Path

def get_api_key(provider: str) -> str:
    # Priority order: environment variable, config file, prompt user
    key = os.getenv(f"{provider.upper()}_API_KEY")
    if not key:
        config_file = Path.home() / ".quantumqa" / "config.json"
        if config_file.exists():
            # Load from secure config file
            pass
    if not key:
        # Prompt user securely
        key = getpass(f"Enter {provider} API key: ")
    return key
```

### Browser Security
```python
# Isolated browser sessions
browser_config = {
    'channel': 'chrome',  # Use stable browser
    'headless': True,     # No GUI by default  
    'args': [
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-extensions',
        '--incognito'
    ]
}
```

## Compatibility Matrix

### Python Versions
- **Python 3.11+**: Full support
- **Python 3.10**: Limited support (missing some type features)
- **Python 3.9 and below**: Not supported

### Operating Systems  
- **Windows 10/11**: Full support
- **macOS 12+**: Full support
- **Linux (Ubuntu 20.04+)**: Full support
- **Docker**: Full support

### Browsers
- **Chrome/Chromium**: Primary support
- **Firefox**: Full support
- **Safari (macOS only)**: Limited support
- **Edge**: Full support

This lightweight technology stack ensures QuantumQA can run anywhere Python runs, with minimal setup and maximum portability while delivering powerful AI-driven testing capabilities.
