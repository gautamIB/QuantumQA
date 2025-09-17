#!/usr/bin/env python3
"""
QuantumQA API Server - REST API for QuantumQA Framework
Provides endpoints for test management and execution.
"""

import asyncio
import os
import json
import uuid
import subprocess
import logging
import yaml
import re
import signal
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Form, Query, Depends
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
import uvicorn
from cryptography.fernet import Fernet
import base64

# Create directory structure
def ensure_directories():
    """Ensure required directories exist."""
    directories = ["Test/UI", "Test/API", "logs", "reports", "credentials"]
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

ensure_directories()

# Encryption setup for credentials
def get_or_create_encryption_key():
    """Get or create encryption key for credential storage."""
    key_file = Path("credentials/encryption.key")
    if key_file.exists():
        with open(key_file, 'rb') as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(key_file, 'wb') as f:
            f.write(key)
        return key

ENCRYPTION_KEY = get_or_create_encryption_key()
cipher_suite = Fernet(ENCRYPTION_KEY)

def encrypt_data(data: str) -> str:
    """Encrypt sensitive data."""
    return base64.urlsafe_b64encode(cipher_suite.encrypt(data.encode())).decode()

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data."""
    return cipher_suite.decrypt(base64.urlsafe_b64decode(encrypted_data.encode())).decode()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/api_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="QuantumQA API",
    description="REST API for QuantumQA Framework - AI-Powered UI & API Testing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
class ValidationResult(BaseModel):
    status: str  # "valid", "invalid", "warning"
    warnings: List[str] = []
    errors: List[str] = []
    last_validated: Optional[str] = None

class CreateTestConfigRequest(BaseModel):
    test_name: str
    test_type: str  # "UI" or "API"
    instruction: Optional[str] = None  # For UI tests (text content)
    apis_documentation: Optional[str] = None  # For API tests (YAML content)
    
    @validator('test_type')
    def validate_test_type(cls, v):
        if v not in ["UI", "API"]:
            raise ValueError('test_type must be "UI" or "API"')
        return v

class UpdateTestConfigRequest(BaseModel):
    instruction: Optional[str] = None
    apis_documentation: Optional[str] = None
    test_type: Optional[str] = None

class Credentials(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None

class RunOptions(BaseModel):
    headless: bool = False
    timeout: int = 300
    retry_count: int = 1

class RunTestRequest(BaseModel):
    env: str  # HTTP URL
    credentials: Optional[Credentials] = None
    credential_id: Optional[str] = None  # Use stored credentials
    test_file_path: str
    test_type: str  # "UI" or "API"
    run_name: str
    options: Optional[RunOptions] = RunOptions()
    
    @validator('test_type')
    def validate_test_type(cls, v):
        if v not in ["UI", "API"]:
            raise ValueError('test_type must be "UI" or "API"')
        return v

class TestConfigInfo(BaseModel):
    test_name: str
    test_type: str
    file_path: str
    created_at: str
    modified_at: str
    size_bytes: int
    status: str  # "valid", "invalid", "warning"

class TestConfigDetail(BaseModel):
    test_name: str
    test_type: str
    file_path: str
    content: str
    created_at: str
    modified_at: str
    size_bytes: int
    validation: ValidationResult

class StepResult(BaseModel):
    step_number: int
    instruction: str
    status: str
    duration_seconds: float
    screenshot: Optional[str] = None

class RunSummary(BaseModel):
    status: str
    success_rate: float
    total_steps: int
    passed_steps: int
    failed_steps: int

class RunFailure(BaseModel):
    step_number: int
    error: str
    details: str

class RunPerformance(BaseModel):
    total_duration: float
    average_step_time: float

class RunInfo(BaseModel):
    run_name: str
    test_file: str
    test_type: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    success_rate: Optional[float] = None
    log_file_url: str
    report_file_url: str

class RunDetail(BaseModel):
    run_name: str
    test_file: str
    test_type: str
    environment: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    success_rate: Optional[float] = None
    steps_total: int
    steps_passed: int
    steps_failed: int
    error_summary: Optional[str] = None
    log_file_url: str
    report_file_url: str

class RunReport(BaseModel):
    run_name: str
    summary: RunSummary
    steps: List[StepResult]
    performance: RunPerformance
    failures: List[RunFailure]

class CredentialRequest(BaseModel):
    credential_name: str
    type: str  # "UI" or "API"
    environment: str
    data: Dict[str, str]

# Global variable to track running tests
running_tests: Dict[str, Dict[str, Any]] = {}

# Test validation functions
def validate_ui_test(content: str) -> ValidationResult:
    """Validate UI test content."""
    errors = []
    warnings = []
    
    if not content.strip():
        errors.append("Test content cannot be empty")
        return ValidationResult(status="invalid", errors=errors)
    
    lines = content.strip().split('\n')
    
    # Check for basic structure
    if len(lines) < 1:
        errors.append("Test must have at least one instruction")
    
    # Validate each line
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
            
        # Check for common action patterns
        action_patterns = [
            r'^navigate to\s+',
            r'^click\s+',
            r'^type\s+',
            r'^verify\s+',
            r'^wait\s+',
            r'^upload\s+',
            r'^select\s+',
            r'^scroll\s+'
        ]
        
        if line.startswith('#') or line.startswith('//'):
            continue  # Comment line
            
        if not any(re.match(pattern, line.lower()) for pattern in action_patterns):
            warnings.append(f"Line {i}: Unrecognized instruction format: '{line[:50]}...'")
    
    # Determine status
    if errors:
        status = "invalid"
    elif warnings:
        status = "warning"
    else:
        status = "valid"
    
    return ValidationResult(
        status=status,
        errors=errors,
        warnings=warnings,
        last_validated=datetime.now().isoformat()
    )

def validate_api_test(content: str) -> ValidationResult:
    """Validate API test YAML content."""
    errors = []
    warnings = []
    
    if not content.strip():
        errors.append("Test content cannot be empty")
        return ValidationResult(status="invalid", errors=errors)
    
    try:
        # Parse YAML
        test_data = yaml.safe_load(content)
        
        if not isinstance(test_data, dict):
            errors.append("API test must be a valid YAML object")
            return ValidationResult(status="invalid", errors=errors)
        
        # Check required fields
        required_fields = ['name', 'base_url', 'tests']
        for field in required_fields:
            if field not in test_data:
                errors.append(f"Missing required field: '{field}'")
        
        # Validate tests array
        if 'tests' in test_data:
            if not isinstance(test_data['tests'], list):
                errors.append("'tests' must be an array")
            else:
                for i, test in enumerate(test_data['tests']):
                    if not isinstance(test, dict):
                        errors.append(f"Test {i+1}: Must be an object")
                        continue
                    
                    if 'name' not in test:
                        errors.append(f"Test {i+1}: Missing 'name' field")
                    if 'method' not in test:
                        errors.append(f"Test {i+1}: Missing 'method' field")
                    if 'endpoint' not in test:
                        errors.append(f"Test {i+1}: Missing 'endpoint' field")
                    
                    # Validate HTTP method
                    if 'method' in test and test['method'].upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                        warnings.append(f"Test {i+1}: Unusual HTTP method '{test['method']}'")
        
    except yaml.YAMLError as e:
        errors.append(f"Invalid YAML format: {str(e)}")
    
    # Determine status
    if errors:
        status = "invalid"
    elif warnings:
        status = "warning"
    else:
        status = "valid"
    
    return ValidationResult(
        status=status,
        errors=errors,
        warnings=warnings,
        last_validated=datetime.now().isoformat()
    )

def validate_test_configuration(test_type: str, content: str) -> ValidationResult:
    """Validate test configuration based on type."""
    if test_type == "UI":
        return validate_ui_test(content)
    elif test_type == "API":
        return validate_api_test(content)
    else:
        return ValidationResult(
            status="invalid",
            errors=[f"Unknown test type: {test_type}"]
        )

@app.get("/", summary="API Health Check")
async def root():
    """Health check endpoint."""
    return {
        "message": "QuantumQA API Server is running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "test_configurations": "/test-configurations",
            "runs": "/runs",
            "credentials": "/credentials",
            "status": "/status"
        }
    }

# ============================================================================
# TEST CONFIGURATION CRUD APIs
# ============================================================================

@app.post("/test-configurations", status_code=201, summary="Create Test Configuration")
async def create_test_configuration(
    test_name: str = Form(...),
    test_type: str = Form(...),
    instruction: Optional[str] = Form(None),
    apis_documentation: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """
    Create a new test configuration.
    
    Supports both form data with text content and file upload.
    Validates test syntax before saving.
    """
    try:
        # Validate test_type
        if test_type not in ["UI", "API"]:
            raise HTTPException(status_code=400, detail="test_type must be 'UI' or 'API'")
        
        # Get content from either form data or uploaded file
        content = None
        if file:
            # Read content from uploaded file
            content = (await file.read()).decode('utf-8')
        else:
            # Use form data
            if test_type == "UI":
                if not instruction:
                    raise HTTPException(status_code=400, detail="instruction is required for UI tests")
                content = instruction
            else:  # API
                if not apis_documentation:
                    raise HTTPException(status_code=400, detail="apis_documentation is required for API tests")
                content = apis_documentation
        
        if not content:
            raise HTTPException(status_code=400, detail="No test content provided")
        
        # Validate test content
        validation_result = validate_test_configuration(test_type, content)
        if validation_result.status == "invalid":
            raise HTTPException(
                status_code=400, 
                detail={
                    "error": "Test validation failed",
                    "validation": validation_result.dict()
                }
            )
        
        # Determine file extension
        file_extension = ".txt" if test_type == "UI" else ".yml"
        
        # Create file path
        file_name = f"{test_name}{file_extension}"
        file_path = Path(f"Test/{test_type}/{file_name}")
        
        # Check if file already exists
        if file_path.exists():
            raise HTTPException(status_code=409, detail=f"Test configuration '{test_name}' already exists")
        
        # Write content to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Created test configuration: {file_path}")
        
        return {
            "message": "Test configuration created successfully",
            "test_name": test_name,
            "test_type": test_type,
            "file_path": str(file_path),
            "validation": validation_result.dict(),
            "created_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating test configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create test configuration: {str(e)}")

@app.get("/test-configurations", summary="Get All Test Configurations")
async def get_test_configurations(
    test_type: Optional[str] = Query(None, description="Filter by test type (UI or API)"),
    limit: int = Query(50, description="Maximum number of results"),
    offset: int = Query(0, description="Number of results to skip")
) -> List[TestConfigInfo]:
    """
    List all test configuration files available in the Test folder.
    """
    try:
        test_configs = []
        test_folder = Path("Test")
        
        # Determine which folders to scan
        if test_type:
            if test_type not in ["UI", "API"]:
                raise HTTPException(status_code=400, detail="test_type must be 'UI' or 'API'")
            scan_types = [test_type]
        else:
            scan_types = ["UI", "API"]
        
        # Scan test folders
        for scan_type in scan_types:
            type_folder = test_folder / scan_type
            if type_folder.exists():
                for file_path in type_folder.iterdir():
                    if file_path.is_file():
                        # Extract test name (remove extension)
                        test_name = file_path.stem
                        
                        # Get file stats
                        stat = file_path.stat()
                        
                        # Validate test to get status
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            validation = validate_test_configuration(scan_type, content)
                            status = validation.status
                        except Exception:
                            status = "invalid"
                        
                        test_configs.append(TestConfigInfo(
                            test_name=test_name,
                            test_type=scan_type,
                            file_path=str(file_path),
                            created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                            modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            size_bytes=stat.st_size,
                            status=status
                        ))
        
        # Sort by creation time (newest first)
        test_configs.sort(key=lambda x: x.created_at, reverse=True)
        
        # Apply pagination
        total = len(test_configs)
        paginated_configs = test_configs[offset:offset + limit]
        
        logger.info(f"Retrieved {len(paginated_configs)}/{total} test configurations")
        return paginated_configs
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving test configurations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve test configurations: {str(e)}")

@app.get("/tests/{test_name}", summary="Get Specific Test")
async def get_test(test_name: str, test_type: Optional[str] = None):
    """
    Get details and content for a specific test.
    
    If test_type is not provided, searches both UI and API folders.
    """
    try:
        # If test_type is specified, look only in that folder
        if test_type:
            if test_type not in ["UI", "API"]:
                raise HTTPException(status_code=400, detail="test_type must be 'UI' or 'API'")
            search_folders = [test_type]
        else:
            search_folders = ["UI", "API"]
        
        for folder in search_folders:
            # Try both .txt and .yml extensions
            for ext in [".txt", ".yml"]:
                file_path = Path(f"Test/{folder}/{test_name}{ext}")
                if file_path.exists():
                    # Read file content
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Get file stats
                    stat = file_path.stat()
                    
                    return {
                        "test_name": test_name,
                        "test_type": folder,
                        "file_path": str(file_path),
                        "content": content,
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "size_bytes": stat.st_size
                    }
        
        # Test not found
        raise HTTPException(status_code=404, detail=f"Test '{test_name}' not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving test {test_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve test: {str(e)}")

@app.delete("/tests/{test_name}", summary="Delete Test")
async def delete_test(test_name: str, test_type: Optional[str] = None):
    """
    Delete a specific test.
    """
    try:
        # If test_type is specified, look only in that folder
        if test_type:
            if test_type not in ["UI", "API"]:
                raise HTTPException(status_code=400, detail="test_type must be 'UI' or 'API'")
            search_folders = [test_type]
        else:
            search_folders = ["UI", "API"]
        
        for folder in search_folders:
            # Try both .txt and .yml extensions
            for ext in [".txt", ".yml"]:
                file_path = Path(f"Test/{folder}/{test_name}{ext}")
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Deleted test: {file_path}")
                    return {
                        "message": "Test deleted successfully",
                        "test_name": test_name,
                        "test_type": folder,
                        "deleted_at": datetime.now().isoformat()
                    }
        
        # Test not found
        raise HTTPException(status_code=404, detail=f"Test '{test_name}' not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting test {test_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete test: {str(e)}")

# ============================================================================
# RUN TEST APIs
# ============================================================================

async def execute_quantumqa_test(request: RunTestRequest) -> Dict[str, Any]:
    """
    Execute QuantumQA test using the existing framework.
    """
    try:
        # Prepare log and report file paths
        log_file = f"logs/{request.run_name}.txt"
        report_file = f"reports/{request.run_name}.txt"
        
        # Prepare command
        cmd = [
            "python", "quantumqa_runner.py", 
            request.test_file_path,
            "--type", request.test_type.lower()
        ]
        
        # Add credentials file if needed
        if request.username and request.password:
            # Create temporary credentials file
            creds_file = f"logs/{request.run_name}_creds.yaml"
            creds_content = f"""
ui_credentials:
  username: "{request.username}"
  password: "{request.password}"
  base_url: "{request.env}"
"""
            if request.api_key:
                creds_content += f"""
api_credentials:
  api_key: "{request.api_key}"
  base_url: "{request.env}"
"""
            
            with open(creds_file, 'w') as f:
                f.write(creds_content)
            
            cmd.extend(["--credentials", creds_file])
        
        # Add headless flag for UI tests
        if request.test_type == "UI" and request.headless:
            pass  # Default is already headless unless --visible is specified
        elif request.test_type == "UI" and not request.headless:
            cmd.append("--visible")
        
        logger.info(f"Executing command: {' '.join(cmd)}")
        
        # Execute the command and capture output
        start_time = datetime.now()
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=os.getcwd()
        )
        
        # Read output in real-time and save to log file
        output_lines = []
        with open(log_file, 'w') as log_f:
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    output_lines.append(output.strip())
                    log_f.write(output)
                    log_f.flush()
        
        # Wait for process to complete
        return_code = process.poll()
        end_time = datetime.now()
        
        # Determine status
        status = "COMPLETED" if return_code == 0 else "FAILED"
        
        # Create report
        report_data = {
            "run_name": request.run_name,
            "test_file": request.test_file_path,
            "test_type": request.test_type,
            "environment": request.env,
            "status": status,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "return_code": return_code,
            "log_file": log_file,
            "command": " ".join(cmd)
        }
        
        # Parse success rate from output if available
        for line in output_lines:
            if "Success Rate:" in line:
                # Extract success rate
                try:
                    parts = line.split("Success Rate:")
                    if len(parts) > 1:
                        rate_part = parts[1].strip().split()[0]
                        success_rate = float(rate_part.replace('%', ''))
                        report_data["success_rate"] = success_rate
                except:
                    pass
                break
        
        # Save report
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        return report_data
        
    except Exception as e:
        logger.error(f"Error executing test: {e}")
        return {
            "run_name": request.run_name,
            "status": "ERROR",
            "error": str(e),
            "end_time": datetime.now().isoformat()
        }

@app.post("/runs", status_code=202, summary="Run Test")
async def run_test(request: RunTestRequest, background_tasks: BackgroundTasks):
    """
    Execute a test with the given configuration.
    
    Runs the QuantumQA framework with the provided credentials and saves logs/reports.
    """
    try:
        # Validate request
        if request.test_type not in ["UI", "API"]:
            raise HTTPException(status_code=400, detail="test_type must be 'UI' or 'API'")
        
        # Check if test file exists
        if not Path(request.test_file_path).exists():
            raise HTTPException(status_code=404, detail=f"Test file not found: {request.test_file_path}")
        
        # Check if run with same name is already running
        if request.run_name in running_tests:
            raise HTTPException(status_code=409, detail=f"Test run '{request.run_name}' is already in progress")
        
        # Validate credentials based on test type
        if request.test_type == "UI" and not (request.username and request.password):
            raise HTTPException(status_code=400, detail="username and password are required for UI tests")
        
        if request.test_type == "API" and not request.api_key:
            raise HTTPException(status_code=400, detail="api_key is required for API tests")
        
        # Mark test as running
        running_tests[request.run_name] = {
            "status": "RUNNING",
            "start_time": datetime.now().isoformat(),
            "test_file": request.test_file_path,
            "test_type": request.test_type
        }
        
        # Execute test in background
        async def run_and_cleanup():
            try:
                result = await execute_quantumqa_test(request)
                running_tests[request.run_name].update(result)
            finally:
                # Remove from running tests when completed
                if request.run_name in running_tests:
                    del running_tests[request.run_name]
        
        background_tasks.add_task(run_and_cleanup)
        
        logger.info(f"Started test run: {request.run_name}")
        
        return {
            "message": "Test execution started",
            "run_name": request.run_name,
            "status": "RUNNING",
            "log_file": f"logs/{request.run_name}.txt",
            "report_file": f"reports/{request.run_name}.txt",
            "started_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting test run: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start test execution: {str(e)}")

@app.get("/runs", summary="Get All Test Runs")
async def get_runs() -> List[RunInfo]:
    """
    List all test run reports available in the reports folder.
    """
    try:
        runs = []
        reports_folder = Path("reports")
        
        if reports_folder.exists():
            for file_path in reports_folder.iterdir():
                if file_path.is_file() and file_path.suffix == '.txt':
                    try:
                        # Try to read report as JSON
                        with open(file_path, 'r') as f:
                            report_data = json.load(f)
                        
                        run_name = file_path.stem
                        log_file = f"logs/{run_name}.txt"
                        
                        runs.append(RunInfo(
                            run_name=run_name,
                            test_file=report_data.get("test_file", "unknown"),
                            test_type=report_data.get("test_type", "unknown"),
                            status=report_data.get("status", "unknown"),
                            created_at=report_data.get("start_time", "unknown"),
                            log_file=log_file,
                            report_file=str(file_path)
                        ))
                        
                    except (json.JSONDecodeError, KeyError):
                        # Handle non-JSON report files
                        stat = file_path.stat()
                        run_name = file_path.stem
                        
                        runs.append(RunInfo(
                            run_name=run_name,
                            test_file="unknown",
                            test_type="unknown",
                            status="unknown",
                            created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                            log_file=f"logs/{run_name}.txt",
                            report_file=str(file_path)
                        ))
        
        # Add currently running tests
        for run_name, run_info in running_tests.items():
            runs.append(RunInfo(
                run_name=run_name,
                test_file=run_info.get("test_file", "unknown"),
                test_type=run_info.get("test_type", "unknown"),
                status="RUNNING",
                created_at=run_info.get("start_time", "unknown"),
                log_file=f"logs/{run_name}.txt",
                report_file=f"reports/{run_name}.txt"
            ))
        
        # Sort by creation time (newest first)
        runs.sort(key=lambda x: x.created_at, reverse=True)
        
        logger.info(f"Retrieved {len(runs)} test runs")
        return runs
        
    except Exception as e:
        logger.error(f"Error retrieving runs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve runs: {str(e)}")

@app.get("/runs/{run_name}", summary="Get Specific Test Run")
async def get_run(run_name: str):
    """
    Get details and results for a specific test run.
    """
    try:
        # Check if test is currently running
        if run_name in running_tests:
            return {
                "run_name": run_name,
                "status": "RUNNING",
                **running_tests[run_name]
            }
        
        # Look for completed test report
        report_file = Path(f"reports/{run_name}.txt")
        if not report_file.exists():
            raise HTTPException(status_code=404, detail=f"Test run '{run_name}' not found")
        
        # Read report
        with open(report_file, 'r') as f:
            try:
                report_data = json.load(f)
            except json.JSONDecodeError:
                # Handle non-JSON report files
                content = f.read()
                report_data = {
                    "run_name": run_name,
                    "status": "COMPLETED",
                    "content": content
                }
        
        return report_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving run {run_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve run: {str(e)}")

@app.get("/runs/{run_name}/logs", summary="Get Test Run Logs")
async def get_run_logs(run_name: str):
    """
    Get logs for a specific test run.
    """
    try:
        log_file = Path(f"logs/{run_name}.txt")
        if not log_file.exists():
            raise HTTPException(status_code=404, detail=f"Log file for run '{run_name}' not found")
        
        return FileResponse(
            path=str(log_file),
            media_type='text/plain',
            filename=f"{run_name}_logs.txt"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving logs for run {run_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve logs: {str(e)}")

@app.get("/runs/{run_name}/report", summary="Get Test Run Report")
async def get_run_report(run_name: str):
    """
    Get report for a specific test run.
    """
    try:
        report_file = Path(f"reports/{run_name}.txt")
        if not report_file.exists():
            raise HTTPException(status_code=404, detail=f"Report file for run '{run_name}' not found")
        
        return FileResponse(
            path=str(report_file),
            media_type='application/json',
            filename=f"{run_name}_report.json"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving report for run {run_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve report: {str(e)}")

# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@app.get("/status", summary="Get API Status")
async def get_status():
    """
    Get current API status and statistics.
    """
    try:
        # Count tests
        ui_tests = len(list(Path("Test/UI").glob("*.txt"))) if Path("Test/UI").exists() else 0
        api_tests = len(list(Path("Test/API").glob("*.yml"))) if Path("Test/API").exists() else 0
        
        # Count runs
        completed_runs = len(list(Path("reports").glob("*.txt"))) if Path("reports").exists() else 0
        running_tests_count = len(running_tests)
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "statistics": {
                "tests": {
                    "ui_tests": ui_tests,
                    "api_tests": api_tests,
                    "total_tests": ui_tests + api_tests
                },
                "runs": {
                    "completed_runs": completed_runs,
                    "running_tests": running_tests_count,
                    "total_runs": completed_runs + running_tests_count
                }
            },
            "currently_running": list(running_tests.keys())
        }
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="QuantumQA API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    
    args = parser.parse_args()
    
    print("🚀 Starting QuantumQA API Server...")
    print(f"📍 Server will be available at: http://{args.host}:{args.port}")
    print(f"📚 API Documentation: http://{args.host}:{args.port}/docs")
    print(f"📖 ReDoc Documentation: http://{args.host}:{args.port}/redoc")
    
    uvicorn.run(
        "api_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        access_log=True,
        log_level="info"
    )
