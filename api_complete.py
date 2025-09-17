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
from fastapi.staticfiles import StaticFiles
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
    description: Optional[str] = None
    data: Dict[str, str]  # e.g., {"username": "...", "password": "...", "api_key": "..."}
    
    @validator('type')
    def validate_credential_type(cls, v):
        if v not in ["UI", "API"]:
            raise ValueError('type must be "UI" or "API"')
        return v

class CredentialInfo(BaseModel):
    credential_id: str
    credential_name: str
    type: str
    environment: str
    description: Optional[str] = None
    fields: List[str]  # List of field names (without values)
    created_at: str
    modified_at: str

class CredentialDetail(BaseModel):
    credential_id: str
    credential_name: str
    type: str
    environment: str
    description: Optional[str] = None
    fields: List[str]  # List of field names (without values)
    created_at: str
    modified_at: str
    # Note: Never expose actual credential values in API responses

class UpdateCredentialRequest(BaseModel):
    credential_name: Optional[str] = None
    description: Optional[str] = None
    data: Optional[Dict[str, str]] = None

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

# ============================================================================
# CREDENTIAL MANAGEMENT FUNCTIONS
# ============================================================================

def save_credential(credential_data: Dict[str, Any]) -> str:
    """Save encrypted credential data and return credential ID."""
    try:
        credential_id = str(uuid.uuid4())
        
        # Encrypt sensitive data
        encrypted_data = {}
        for key, value in credential_data["data"].items():
            encrypted_data[key] = encrypt_data(str(value))
        
        # Prepare credential file content
        credential_file_data = {
            "credential_id": credential_id,
            "credential_name": credential_data["credential_name"],
            "type": credential_data["type"],
            "environment": credential_data["environment"],
            "description": credential_data.get("description"),
            "encrypted_data": encrypted_data,
            "created_at": datetime.now().isoformat(),
            "modified_at": datetime.now().isoformat()
        }
        
        # Save to file
        credential_file = Path(f"credentials/{credential_id}.json")
        with open(credential_file, 'w') as f:
            json.dump(credential_file_data, f, indent=2)
        
        logger.info(f"Saved credential: {credential_id}")
        return credential_id
        
    except Exception as e:
        logger.error(f"Error saving credential: {e}")
        raise

def load_credential(credential_id: str) -> Optional[Dict[str, Any]]:
    """Load and decrypt credential data."""
    try:
        credential_file = Path(f"credentials/{credential_id}.json")
        if not credential_file.exists():
            return None
        
        with open(credential_file, 'r') as f:
            credential_data = json.load(f)
        
        # Decrypt sensitive data
        decrypted_data = {}
        for key, encrypted_value in credential_data["encrypted_data"].items():
            decrypted_data[key] = decrypt_data(encrypted_value)
        
        credential_data["data"] = decrypted_data
        del credential_data["encrypted_data"]  # Remove encrypted version
        
        return credential_data
        
    except Exception as e:
        logger.error(f"Error loading credential {credential_id}: {e}")
        return None

def list_credentials() -> List[Dict[str, Any]]:
    """List all credential metadata without sensitive data."""
    try:
        credentials = []
        credentials_folder = Path("credentials")
        
        if credentials_folder.exists():
            for file_path in credentials_folder.iterdir():
                if file_path.is_file() and file_path.suffix == '.json' and file_path.name != 'encryption.key':
                    try:
                        with open(file_path, 'r') as f:
                            credential_data = json.load(f)
                        
                        # Return only metadata, not sensitive data
                        credential_info = {
                            "credential_id": credential_data["credential_id"],
                            "credential_name": credential_data["credential_name"],
                            "type": credential_data["type"],
                            "environment": credential_data["environment"],
                            "description": credential_data.get("description"),
                            "fields": list(credential_data["encrypted_data"].keys()),
                            "created_at": credential_data["created_at"],
                            "modified_at": credential_data["modified_at"]
                        }
                        credentials.append(credential_info)
                        
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Invalid credential file {file_path}: {e}")
                        continue
        
        # Sort by creation time (newest first)
        credentials.sort(key=lambda x: x["created_at"], reverse=True)
        return credentials
        
    except Exception as e:
        logger.error(f"Error listing credentials: {e}")
        return []

def update_credential(credential_id: str, update_data: Dict[str, Any]) -> bool:
    """Update an existing credential."""
    try:
        credential_file = Path(f"credentials/{credential_id}.json")
        if not credential_file.exists():
            return False
        
        # Load existing data
        with open(credential_file, 'r') as f:
            credential_data = json.load(f)
        
        # Update metadata
        if "credential_name" in update_data:
            credential_data["credential_name"] = update_data["credential_name"]
        if "description" in update_data:
            credential_data["description"] = update_data["description"]
        
        # Update sensitive data if provided
        if "data" in update_data:
            encrypted_data = {}
            for key, value in update_data["data"].items():
                encrypted_data[key] = encrypt_data(str(value))
            credential_data["encrypted_data"] = encrypted_data
        
        credential_data["modified_at"] = datetime.now().isoformat()
        
        # Save updated data
        with open(credential_file, 'w') as f:
            json.dump(credential_data, f, indent=2)
        
        logger.info(f"Updated credential: {credential_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating credential {credential_id}: {e}")
        return False

def delete_credential(credential_id: str) -> bool:
    """Delete a credential."""
    try:
        credential_file = Path(f"credentials/{credential_id}.json")
        if not credential_file.exists():
            return False
        
        credential_file.unlink()
        logger.info(f"Deleted credential: {credential_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting credential {credential_id}: {e}")
        return False

def get_credential_for_run(credential_id: str) -> Optional[Credentials]:
    """Get decrypted credentials for test execution."""
    try:
        credential_data = load_credential(credential_id)
        if not credential_data:
            return None
        
        # Convert to Credentials model
        creds = Credentials()
        data = credential_data["data"]
        
        if "username" in data:
            creds.username = data["username"]
        if "password" in data:
            creds.password = data["password"]
        if "api_key" in data:
            creds.api_key = data["api_key"]
        
        return creds
        
    except Exception as e:
        logger.error(f"Error getting credential for run {credential_id}: {e}")
        return None

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
    """List all test configuration files."""
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

@app.get("/test-configurations/{test_name}", summary="Get Specific Test Configuration")
async def get_test_configuration(
    test_name: str, 
    test_type: Optional[str] = Query(None, description="Test type (UI or API)")
) -> TestConfigDetail:
    """Get details and content for a specific test configuration."""
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
                    
                    # Validate content
                    validation = validate_test_configuration(folder, content)
                    
                    return TestConfigDetail(
                        test_name=test_name,
                        test_type=folder,
                        file_path=str(file_path),
                        content=content,
                        created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        size_bytes=stat.st_size,
                        validation=validation
                    )
        
        # Test not found
        raise HTTPException(status_code=404, detail=f"Test configuration '{test_name}' not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving test configuration {test_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve test configuration: {str(e)}")

@app.put("/test-configurations/{test_name}", summary="Update Test Configuration")
async def update_test_configuration(
    test_name: str,
    request: UpdateTestConfigRequest,
    test_type: Optional[str] = Query(None, description="Test type (UI or API)")
):
    """Update an existing test configuration."""
    try:
        # Find the test file
        if test_type:
            if test_type not in ["UI", "API"]:
                raise HTTPException(status_code=400, detail="test_type must be 'UI' or 'API'")
            search_folders = [test_type]
        else:
            search_folders = ["UI", "API"]
        
        file_path = None
        current_type = None
        for folder in search_folders:
            for ext in [".txt", ".yml"]:
                potential_path = Path(f"Test/{folder}/{test_name}{ext}")
                if potential_path.exists():
                    file_path = potential_path
                    current_type = folder
                    break
            if file_path:
                break
        
        if not file_path:
            raise HTTPException(status_code=404, detail=f"Test configuration '{test_name}' not found")
        
        # Get new content
        if current_type == "UI":
            if not request.instruction:
                raise HTTPException(status_code=400, detail="instruction is required for UI tests")
            new_content = request.instruction
        else:  # API
            if not request.apis_documentation:
                raise HTTPException(status_code=400, detail="apis_documentation is required for API tests")
            new_content = request.apis_documentation
        
        # Validate new content
        validation_result = validate_test_configuration(current_type, new_content)
        if validation_result.status == "invalid":
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Test validation failed",
                    "validation": validation_result.dict()
                }
            )
        
        # Write updated content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.info(f"Updated test configuration: {file_path}")
        
        return {
            "message": "Test configuration updated successfully",
            "test_name": test_name,
            "test_type": current_type,
            "validation": validation_result.dict(),
            "updated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating test configuration {test_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update test configuration: {str(e)}")

@app.delete("/test-configurations/{test_name}", summary="Delete Test Configuration")
async def delete_test_configuration(
    test_name: str, 
    test_type: Optional[str] = Query(None, description="Test type (UI or API)")
):
    """Delete a specific test configuration."""
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
                    logger.info(f"Deleted test configuration: {file_path}")
                    return {
                        "message": "Test configuration deleted successfully",
                        "test_name": test_name,
                        "test_type": folder,
                        "deleted_at": datetime.now().isoformat()
                    }
        
        # Test not found
        raise HTTPException(status_code=404, detail=f"Test configuration '{test_name}' not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting test configuration {test_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete test configuration: {str(e)}")

@app.post("/test-configurations/{test_name}/validate", summary="Validate Test Configuration")
async def validate_test_config(test_name: str, test_type: Optional[str] = Query(None)) -> ValidationResult:
    """Validate a test configuration without saving changes."""
    try:
        # Find the test file
        if test_type:
            if test_type not in ["UI", "API"]:
                raise HTTPException(status_code=400, detail="test_type must be 'UI' or 'API'")
            search_folders = [test_type]
        else:
            search_folders = ["UI", "API"]
        
        for folder in search_folders:
            for ext in [".txt", ".yml"]:
                file_path = Path(f"Test/{folder}/{test_name}{ext}")
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    validation = validate_test_configuration(folder, content)
                    logger.info(f"Validated test configuration: {file_path}")
                    return validation
        
        raise HTTPException(status_code=404, detail=f"Test configuration '{test_name}' not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating test configuration {test_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to validate test configuration: {str(e)}")

# ============================================================================
# RUN TEST APIs
# ============================================================================

async def execute_quantumqa_test(request: RunTestRequest) -> Dict[str, Any]:
    """Execute QuantumQA test using the existing framework."""
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
        
        # Handle credentials
        creds_content = ""
        if request.credentials:
            if request.credentials.username and request.credentials.password:
                creds_content += f"""
ui_credentials:
  username: "{request.credentials.username}"
  password: "{request.credentials.password}"
  base_url: "{request.env}"
"""
            if request.credentials.api_key:
                creds_content += f"""
api_credentials:
  api_key: "{request.credentials.api_key}"
  base_url: "{request.env}"
"""
        elif request.credential_id:
            # Load stored credentials
            stored_creds = get_credential_for_run(request.credential_id)
            if not stored_creds:
                return {
                    "run_name": request.run_name,
                    "status": "ERROR",
                    "error": f"Credential '{request.credential_id}' not found or invalid",
                    "end_time": datetime.now().isoformat()
                }
            
            if stored_creds.username and stored_creds.password:
                creds_content += f"""
ui_credentials:
  username: "{stored_creds.username}"
  password: "{stored_creds.password}"
  base_url: "{request.env}"
"""
            if stored_creds.api_key:
                creds_content += f"""
api_credentials:
  api_key: "{stored_creds.api_key}"
  base_url: "{request.env}"
"""
        
        if creds_content:
            # Create temporary credentials file
            creds_file = f"logs/{request.run_name}_creds.yaml"
            with open(creds_file, 'w') as f:
                f.write(creds_content)
            cmd.extend(["--credentials", creds_file])
        
        # Add options
        if request.test_type == "UI" and not request.options.headless:
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
        
        # Parse success rate from output if available
        success_rate = None
        for line in output_lines:
            if "Success Rate:" in line:
                try:
                    parts = line.split("Success Rate:")
                    if len(parts) > 1:
                        rate_part = parts[1].strip().split()[0]
                        success_rate = float(rate_part.replace('%', ''))
                except:
                    pass
                break
        
        # Create report data
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
            "success_rate": success_rate,
            "log_file": log_file,
            "command": " ".join(cmd)
        }
        
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

@app.post("/runs", status_code=202, summary="Execute Test Run")
async def run_test(request: RunTestRequest, background_tasks: BackgroundTasks):
    """Execute a test with the given configuration."""
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
        
        # Validate credentials
        if not request.credentials and not request.credential_id:
            raise HTTPException(status_code=400, detail="Either credentials or credential_id is required")
        
        if request.credentials:
            if request.test_type == "UI" and not (request.credentials.username and request.credentials.password):
                raise HTTPException(status_code=400, detail="username and password are required for UI tests")
            
            if request.test_type == "API" and not request.credentials.api_key:
                raise HTTPException(status_code=400, detail="api_key is required for API tests")
        
        # Mark test as running
        running_tests[request.run_name] = {
            "status": "RUNNING",
            "start_time": datetime.now().isoformat(),
            "test_file": request.test_file_path,
            "test_type": request.test_type,
            "process": None
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
            "log_file_url": f"/runs/{request.run_name}/logs",
            "report_file_url": f"/runs/{request.run_name}/report",
            "started_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting test run: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start test execution: {str(e)}")

@app.get("/runs", summary="Get All Test Runs")
async def get_runs(
    status: Optional[str] = Query(None, description="Filter by status"),
    test_type: Optional[str] = Query(None, description="Filter by test type"),
    limit: int = Query(50, description="Maximum number of results"),
    offset: int = Query(0, description="Number of results to skip")
) -> Dict[str, Any]:
    """List all test run reports."""
    try:
        runs = []
        reports_folder = Path("reports")
        
        # Add completed runs from reports
        if reports_folder.exists():
            for file_path in reports_folder.iterdir():
                if file_path.is_file() and file_path.suffix == '.txt':
                    try:
                        # Try to read report as JSON
                        with open(file_path, 'r') as f:
                            report_data = json.load(f)
                        
                        run_name = file_path.stem
                        
                        run_info = RunInfo(
                            run_name=run_name,
                            test_file=report_data.get("test_file", "unknown"),
                            test_type=report_data.get("test_type", "unknown"),
                            status=report_data.get("status", "unknown"),
                            started_at=report_data.get("start_time", "unknown"),
                            completed_at=report_data.get("end_time"),
                            duration_seconds=report_data.get("duration_seconds"),
                            success_rate=report_data.get("success_rate"),
                            log_file_url=f"/runs/{run_name}/logs",
                            report_file_url=f"/runs/{run_name}/report"
                        )
                        
                        runs.append(run_info)
                        
                    except (json.JSONDecodeError, KeyError):
                        # Handle non-JSON report files
                        stat = file_path.stat()
                        run_name = file_path.stem
                        
                        run_info = RunInfo(
                            run_name=run_name,
                            test_file="unknown",
                            test_type="unknown",
                            status="COMPLETED",
                            started_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                            log_file_url=f"/runs/{run_name}/logs",
                            report_file_url=f"/runs/{run_name}/report"
                        )
                        runs.append(run_info)
        
        # Add currently running tests
        for run_name, run_data in running_tests.items():
            run_info = RunInfo(
                run_name=run_name,
                test_file=run_data.get("test_file", "unknown"),
                test_type=run_data.get("test_type", "unknown"),
                status="RUNNING",
                started_at=run_data.get("start_time", "unknown"),
                log_file_url=f"/runs/{run_name}/logs",
                report_file_url=f"/runs/{run_name}/report"
            )
            runs.append(run_info)
        
        # Apply filters
        if status:
            runs = [r for r in runs if r.status == status]
        if test_type:
            runs = [r for r in runs if r.test_type == test_type]
        
        # Sort by start time (newest first)
        runs.sort(key=lambda x: x.started_at, reverse=True)
        
        # Apply pagination
        total = len(runs)
        paginated_runs = runs[offset:offset + limit]
        
        logger.info(f"Retrieved {len(paginated_runs)}/{total} test runs")
        
        return {
            "runs": [run.dict() for run in paginated_runs],
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Error retrieving runs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve runs: {str(e)}")

@app.get("/runs/{run_name}", summary="Get Specific Test Run")
async def get_run(run_name: str) -> RunDetail:
    """Get details and results for a specific test run."""
    try:
        # Check if test is currently running
        if run_name in running_tests:
            run_data = running_tests[run_name]
            return RunDetail(
                run_name=run_name,
                test_file=run_data.get("test_file", "unknown"),
                test_type=run_data.get("test_type", "unknown"),
                environment="unknown",
                status="RUNNING",
                started_at=run_data.get("start_time", "unknown"),
                steps_total=0,
                steps_passed=0,
                steps_failed=0,
                log_file_url=f"/runs/{run_name}/logs",
                report_file_url=f"/runs/{run_name}/report"
            )
        
        # Look for completed test report
        report_file = Path(f"reports/{run_name}.txt")
        if not report_file.exists():
            raise HTTPException(status_code=404, detail=f"Test run '{run_name}' not found")
        
        # Read report
        with open(report_file, 'r') as f:
            try:
                report_data = json.load(f)
            except json.JSONDecodeError:
                raise HTTPException(status_code=500, detail="Invalid report format")
        
        return RunDetail(
            run_name=run_name,
            test_file=report_data.get("test_file", "unknown"),
            test_type=report_data.get("test_type", "unknown"),
            environment=report_data.get("environment", "unknown"),
            status=report_data.get("status", "unknown"),
            started_at=report_data.get("start_time", "unknown"),
            completed_at=report_data.get("end_time"),
            duration_seconds=report_data.get("duration_seconds"),
            success_rate=report_data.get("success_rate"),
            steps_total=0,  # Would need to parse from output
            steps_passed=0,  # Would need to parse from output
            steps_failed=0,  # Would need to parse from output
            error_summary=report_data.get("error"),
            log_file_url=f"/runs/{run_name}/logs",
            report_file_url=f"/runs/{run_name}/report"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving run {run_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve run: {str(e)}")

@app.get("/runs/{run_name}/logs", summary="Get Test Run Logs")
async def get_run_logs(run_name: str):
    """Get logs for a specific test run."""
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
    """Get report for a specific test run."""
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

@app.delete("/runs/{run_name}", summary="Cancel Test Run")
async def cancel_run(run_name: str):
    """Cancel a running test."""
    try:
        if run_name not in running_tests:
            # Check if it's a completed run
            report_file = Path(f"reports/{run_name}.txt")
            if report_file.exists():
                raise HTTPException(status_code=409, detail="Cannot cancel completed test run")
            else:
                raise HTTPException(status_code=404, detail=f"Test run '{run_name}' not found")
        
        # Cancel the running test
        run_data = running_tests[run_name]
        if "process" in run_data and run_data["process"]:
            try:
                run_data["process"].terminate()
            except:
                pass
        
        # Remove from running tests
        del running_tests[run_name]
        
        logger.info(f"Cancelled test run: {run_name}")
        
        return {
            "message": "Test run cancelled successfully",
            "run_name": run_name,
            "status": "CANCELLED",
            "cancelled_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling run {run_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel run: {str(e)}")

# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@app.get("/status", summary="Get API Status")
async def get_status():
    """Get current API status and statistics."""
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
                "test_configurations": {
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

# ============================================================================
# CREDENTIALS MANAGEMENT APIs
# ============================================================================

@app.post("/credentials", status_code=201, summary="Create Encrypted Credentials")
async def create_credentials(request: CredentialRequest):
    """
    Store encrypted credentials securely.
    
    Credentials are encrypted using Fernet encryption and stored on disk.
    The actual credential values are never returned in API responses.
    """
    try:
        # Validate credential data based on type
        if request.type == "UI":
            required_fields = ["username", "password"]
            for field in required_fields:
                if field not in request.data or not request.data[field]:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Field '{field}' is required for UI credentials"
                    )
        
        elif request.type == "API":
            if "api_key" not in request.data or not request.data["api_key"]:
                raise HTTPException(
                    status_code=400, 
                    detail="Field 'api_key' is required for API credentials"
                )
        
        # Check if credential name already exists for this environment
        existing_credentials = list_credentials()
        for cred in existing_credentials:
            if (cred["credential_name"] == request.credential_name and 
                cred["environment"] == request.environment and
                cred["type"] == request.type):
                raise HTTPException(
                    status_code=409, 
                    detail=f"Credential '{request.credential_name}' already exists for environment '{request.environment}'"
                )
        
        # Save encrypted credentials
        credential_id = save_credential(request.dict())
        
        logger.info(f"Created encrypted credentials: {credential_id}")
        
        return {
            "message": "Credentials created successfully",
            "credential_id": credential_id,
            "credential_name": request.credential_name,
            "type": request.type,
            "environment": request.environment,
            "fields": list(request.data.keys()),
            "created_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating credentials: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create credentials: {str(e)}")

@app.get("/credentials", summary="List Stored Credentials")
async def get_credentials(
    type: Optional[str] = Query(None, description="Filter by credential type (UI or API)"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    limit: int = Query(50, description="Maximum number of results"),
    offset: int = Query(0, description="Number of results to skip")
) -> List[CredentialInfo]:
    """
    List all stored credentials without exposing sensitive data.
    
    Returns only metadata about credentials, never actual values.
    """
    try:
        credentials = list_credentials()
        
        # Apply filters
        if type:
            if type not in ["UI", "API"]:
                raise HTTPException(status_code=400, detail="type must be 'UI' or 'API'")
            credentials = [c for c in credentials if c["type"] == type]
        
        if environment:
            credentials = [c for c in credentials if c["environment"] == environment]
        
        # Apply pagination
        total = len(credentials)
        paginated_credentials = credentials[offset:offset + limit]
        
        # Convert to response models
        result = []
        for cred in paginated_credentials:
            result.append(CredentialInfo(**cred))
        
        logger.info(f"Retrieved {len(result)}/{total} credentials")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving credentials: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve credentials: {str(e)}")

@app.get("/credentials/{credential_id}", summary="Get Credential Details")
async def get_credential(credential_id: str) -> CredentialDetail:
    """
    Get details about a specific credential without exposing sensitive data.
    
    Returns metadata only, never actual credential values.
    """
    try:
        credential_data = load_credential(credential_id)
        if not credential_data:
            raise HTTPException(status_code=404, detail=f"Credential '{credential_id}' not found")
        
        # Return metadata only (no sensitive data)
        return CredentialDetail(
            credential_id=credential_data["credential_id"],
            credential_name=credential_data["credential_name"],
            type=credential_data["type"],
            environment=credential_data["environment"],
            description=credential_data.get("description"),
            fields=list(credential_data["data"].keys()),
            created_at=credential_data["created_at"],
            modified_at=credential_data["modified_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving credential {credential_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve credential: {str(e)}")

@app.put("/credentials/{credential_id}", summary="Update Credentials")
async def update_credentials(credential_id: str, request: UpdateCredentialRequest):
    """
    Update stored credentials.
    
    Can update metadata and/or credential data. All data is re-encrypted.
    """
    try:
        # Check if credential exists
        existing_credential = load_credential(credential_id)
        if not existing_credential:
            raise HTTPException(status_code=404, detail=f"Credential '{credential_id}' not found")
        
        # Prepare update data
        update_data = {}
        if request.credential_name is not None:
            update_data["credential_name"] = request.credential_name
        if request.description is not None:
            update_data["description"] = request.description
        if request.data is not None:
            # Validate new credential data
            cred_type = existing_credential["type"]
            if cred_type == "UI":
                required_fields = ["username", "password"]
                for field in required_fields:
                    if field not in request.data or not request.data[field]:
                        raise HTTPException(
                            status_code=400, 
                            detail=f"Field '{field}' is required for UI credentials"
                        )
            elif cred_type == "API":
                if "api_key" not in request.data or not request.data["api_key"]:
                    raise HTTPException(
                        status_code=400, 
                        detail="Field 'api_key' is required for API credentials"
                    )
            
            update_data["data"] = request.data
        
        # Update credential
        success = update_credential(credential_id, update_data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update credential")
        
        logger.info(f"Updated credentials: {credential_id}")
        
        return {
            "message": "Credentials updated successfully",
            "credential_id": credential_id,
            "updated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating credential {credential_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update credential: {str(e)}")

@app.delete("/credentials/{credential_id}", summary="Delete Credentials")
async def delete_credentials(credential_id: str):
    """
    Permanently delete stored credentials.
    
    This action cannot be undone.
    """
    try:
        # Check if credential exists
        existing_credential = load_credential(credential_id)
        if not existing_credential:
            raise HTTPException(status_code=404, detail=f"Credential '{credential_id}' not found")
        
        # Delete credential
        success = delete_credential(credential_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete credential")
        
        logger.info(f"Deleted credentials: {credential_id}")
        
        return {
            "message": "Credentials deleted successfully",
            "credential_id": credential_id,
            "deleted_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting credential {credential_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete credential: {str(e)}")

@app.post("/credentials/{credential_id}/test", summary="Test Credential Connection")
async def test_credential_connection(credential_id: str, test_url: str = Query(..., description="URL to test connection")):
    """
    Test if credentials work by making a simple connection test.
    
    For UI credentials: Tests if the URL is accessible.
    For API credentials: Tests if API key is valid with a simple request.
    """
    try:
        credential_data = load_credential(credential_id)
        if not credential_data:
            raise HTTPException(status_code=404, detail=f"Credential '{credential_id}' not found")
        
        cred_type = credential_data["type"]
        
        if cred_type == "UI":
            # For UI credentials, just test if URL is accessible
            try:
                import requests
                response = requests.get(test_url, timeout=10)
                success = response.status_code < 400
                status_message = f"URL accessible, status: {response.status_code}"
            except requests.RequestException as e:
                success = False
                status_message = f"Connection failed: {str(e)}"
        
        elif cred_type == "API":
            # For API credentials, test with the API key
            try:
                import requests
                api_key = credential_data["data"].get("api_key")
                headers = {"Authorization": f"Bearer {api_key}"}
                response = requests.get(test_url, headers=headers, timeout=10)
                success = response.status_code < 400
                status_message = f"API accessible, status: {response.status_code}"
            except requests.RequestException as e:
                success = False
                status_message = f"API connection failed: {str(e)}"
        
        logger.info(f"Tested credential {credential_id}: {status_message}")
        
        return {
            "credential_id": credential_id,
            "test_url": test_url,
            "success": success,
            "status_message": status_message,
            "tested_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing credential {credential_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test credential: {str(e)}")

# Serve the React app for all UI routes (catch-all)
@app.get("/ui/{path:path}")
async def serve_ui(path: str):
    """Serve the React frontend for all UI routes"""
    from fastapi.responses import FileResponse
    import os
    
    # Try to serve the requested file first
    file_path = os.path.join("front-end/build", path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # For all other routes, serve index.html (SPA fallback)
    return FileResponse("front-end/build/index.html")

# Serve the root UI route
@app.get("/ui")
async def serve_ui_root():
    """Serve the React frontend for the root UI route"""
    from fastapi.responses import FileResponse
    return FileResponse("front-end/build/index.html")

if __name__ == "__main__":
    print("🚀 Starting QuantumQA API Server...")
    print(f"📍 Server will be available at: http://0.0.0.0:8000")
    print(f"📚 API Documentation: http://0.0.0.0:8000/docs")
    print(f"📂 Front-end will be available at: http://0.0.0.0:8000/ui")
    
    uvicorn.run(
        "api_complete:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        access_log=True,
        log_level="info"
    )
