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
from typing import List, Dict, Any, Optional, Tuple, Union
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Form, Query, Depends
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, validator
import uvicorn
from cryptography.fernet import Fernet
import base64
# Import necessary functions
from scripts.parse_testmo_export import parse_testmo_export_to_json
from quantumqa.api.testmo_processor import TestmoProcessor
import asyncio
import json


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
    return base64.urlsafe_b64encode(cipher_suite.encrypt(
        data.encode())).decode()


def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data."""
    return cipher_suite.decrypt(
        base64.urlsafe_b64decode(encrypted_data.encode())).decode()


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/api_server.log'),
        logging.StreamHandler()
    ])
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="QuantumQA API",
              description=
              "REST API for QuantumQA Framework - AI-Powered UI & API Testing",
              version="1.0.0",
              docs_url="/docs",
              redoc_url="/redoc")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for GIF hosting
# Create reports directory if it doesn't exist
ensure_directories()

# Mount the reports directory to serve GIF files
app.mount("/static/gifs", StaticFiles(directory="reports"), name="gifs")

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
    apis_documentation: Optional[UploadFile] = File(None)  # For API tests (YAML content as string)

    @validator('test_type')
    def validate_test_type(cls, v):
        if v not in ["UI", "API"]:
            raise ValueError('test_type must be "UI" or "API"')
        return v


# UpdateTestConfigRequest model removed - now using Form data for updates
class UpdateTestConfigRequest(BaseModel):
    instruction: Optional[str] = Form(None)
    apis_documentation: Optional[UploadFile] = File(None)
    test_type: Optional[str] = Form(None)



class Credentials(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None


class RunOptions(BaseModel):
    headless: bool = False
    timeout: int = 300
    retry_count: int = 1
    performance_measurement: bool = True  # Enable performance measurement mode by default
    disable_caching: bool = False  # Disable browser caching
    disable_performance: bool = False  # Disable performance optimizations


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
    instruction: Optional[str] = None  # Test instructions/content


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
    status: str  # "passed", "failed", "skipped"
    duration_seconds: float
    screenshot: Optional[str] = None
    failure_reason: Optional[
        str] = None  # Reason for failure if status is "failed"


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
    test_name: str  # Test name extracted from test_file (filename without extension)
    test_type: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    success_rate: Optional[float] = None
    # Consolidated step statistics
    steps_total: Optional[int] = None
    steps_passed: Optional[int] = None
    steps_failed: Optional[int] = None
    steps_executed: Optional[int] = None  # Total executed (passed + failed)
    log_file_url: str
    report_file_url: str


class RunDetail(BaseModel):
    run_name: str
    test_file: str
    test_type: str
    environment: str
    status: str  # "RUNNING", "COMPLETED", "FAILED", "CANCELLED"
    started_at: str
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    success_rate: Optional[float] = None
    steps_total: int
    steps_passed: int
    steps_failed: int
    steps_skipped: Optional[int] = 0  # Number of skipped steps (comments)
    steps_executed: Optional[int] = None  # For RUNNING status
    steps: List[StepResult] = []  # Individual step details
    error_summary: Optional[str] = None
    log_file_url: str
    report_file_url: str
    gif_file_path: Optional[str] = None  # Local path to GIF file if available
    gif_file_url: Optional[str] = None   # HTTP URL to access GIF file


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
    data: Dict[
        str,
        str]  # e.g., {"username": "...", "password": "...", "api_key": "..."}

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


def cleanup_orphaned_processes():
    """Clean up any orphaned test processes on startup."""
    try:
        # Look for any existing log files that might indicate running processes
        logs_dir = Path("logs")
        if logs_dir.exists():
            for log_file in logs_dir.glob("*_creds.yaml"):
                # These are temporary credential files that should be cleaned up
                try:
                    log_file.unlink()
                    logger.info(
                        f"Cleaned up orphaned credential file: {log_file}")
                except Exception as e:
                    logger.warning(f"Could not clean up {log_file}: {e}")

        logger.info("Orphaned process cleanup completed")
    except Exception as e:
        logger.warning(f"Error during orphaned process cleanup: {e}")


# Clean up on startup
cleanup_orphaned_processes()


# Helper functions for parsing log files and extracting step information
def parse_log_file_for_steps(
        log_file_path: Path) -> Tuple[List[StepResult], int, int, int]:
    """
    Parse log file to extract step information.
    Returns: (steps_list, total_steps, passed_steps, failed_steps)
    """
    steps = []
    total_steps = 0
    passed_steps = 0
    failed_steps = 0

    if not log_file_path.exists():
        return steps, total_steps, passed_steps, failed_steps

    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract step information using regex patterns
        step_patterns = [
            r'📋 Step (\d+): (.+?)(?:\n|$)',  # Step start pattern
            r'✅ Step (\d+) completed',  # Step completion pattern
            r'❌ Step (\d+) failed:? ?(.+?)(?:\n|$)',  # Step failure pattern
            r'⚠️ Step (\d+).+?(.+?)(?:\n|$)',  # Step warning pattern
        ]

        lines = content.split('\n')
        current_step = None

        for line in lines:
            # Try to match step start
            import re
            step_start_match = re.search(r'📋 Step (\d+): (.+)', line)
            if step_start_match:
                step_num = int(step_start_match.group(1))
                instruction = step_start_match.group(2).strip()
                current_step = {
                    'step_number': step_num,
                    'instruction': instruction,
                    'status': 'running',
                    'duration_seconds': 0.0,
                    'failure_reason': None
                }
                total_steps = max(total_steps, step_num)

            # Check for step completion
            elif current_step and re.search(r'✅ Step \d+ completed', line):
                current_step['status'] = 'passed'
                passed_steps += 1
                steps.append(StepResult(**current_step))
                current_step = None

            # Check for step failure
            elif current_step and ('❌' in line or '⚠️' in line):
                failure_match = re.search(r'(?:❌|⚠️).+?Step \d+.+?(.+)', line)
                current_step['status'] = 'failed'
                current_step['failure_reason'] = failure_match.group(
                    1).strip() if failure_match else line.strip()
                failed_steps += 1
                steps.append(StepResult(**current_step))
                current_step = None

        # Handle any remaining current_step
        if current_step:
            current_step['status'] = 'failed'
            current_step[
                'failure_reason'] = 'Step was interrupted or incomplete'
            failed_steps += 1
            steps.append(StepResult(**current_step))

        # If no steps were parsed from structured format, try simpler parsing
        if not steps and total_steps == 0:
            # Try to find "Loaded X instructions" pattern
            loaded_match = re.search(r'📋 Loaded (\d+) instructions', content)
            if loaded_match:
                total_steps = int(loaded_match.group(1))

            # Estimate based on success rate if available
            success_rate_match = re.search(r'Success Rate: ([\d.]+)%', content)
            if success_rate_match and total_steps > 0:
                success_rate = float(success_rate_match.group(1))
                passed_steps = int((success_rate / 100.0) * total_steps)
                failed_steps = total_steps - passed_steps

    except Exception as e:
        logger.warning(f"Error parsing log file {log_file_path}: {e}")

    return steps, total_steps, passed_steps, failed_steps


def find_gif_file(run_name: str) -> Optional[str]:
    """Find GIF file for a test run in the reports directory and return hosting URL."""
    reports_dir = Path("reports")
    if not reports_dir.exists():
        return None

    # Look for GIF files that contain the run name
    for gif_file in reports_dir.glob("*.gif"):
        if run_name in gif_file.name:
            # Return the hosted URL instead of file path
            gif_filename = gif_file.name
            return f"/static/gifs/{gif_filename}"

    return None

def find_gif_file_details(run_name: str) -> Tuple[Optional[str], Optional[str]]:
    """Find GIF file for a test run and return both file path and hosting URL."""
    reports_dir = Path("reports")
    if not reports_dir.exists():
        return None, None

    # Look for GIF files that contain the run name
    for gif_file in reports_dir.glob("*.gif"):
        if run_name in gif_file.name:
            gif_file_path = str(gif_file)
            gif_filename = gif_file.name
            gif_file_url = f"/static/gifs/{gif_filename}"
            return gif_file_path, gif_file_url

    return None, None

def extract_test_name_from_file(test_file: str) -> str:
    """Extract test name from test file path (filename without extension)."""
    try:
        if not test_file or test_file.strip() == "":
            return "unknown"
        # Extract filename from path
        filename = Path(test_file).name
        # Remove extension
        test_name = Path(filename).stem
        return test_name if test_name else "unknown"
    except Exception:
        return "unknown"


def create_initial_report(run_name: str, test_file_path: str, test_type: str,
                          environment: str, start_time: str) -> Dict[str, Any]:
    """Create initial report file with all steps in 'waiting' status."""
    try:
        # Read test file to get all steps
        test_file = Path(test_file_path)
        if not test_file.exists():
            logger.warning(f"Test file not found: {test_file_path}")
            return None

        steps = []
        step_number = 1

        with open(test_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:  # Include all non-empty lines
                    # Determine if this is a comment/section marker
                    is_comment = (line.startswith('#') or line.startswith('//')
                                  or line.startswith('===')
                                  or line.endswith('==='))

                    steps.append({
                        "step_number": step_number,
                        "instruction": line,
                        "status": "skipped" if is_comment else "waiting",
                        "duration_seconds": 0.0,
                        "failure_reason": None,
                        "screenshot": None,
                        "started_at": None,
                        "completed_at": None,
                        "is_comment": is_comment
                    })
                    step_number += 1

        # Calculate initial statistics
        skipped_count = sum(1 for s in steps if s["status"] == "skipped")
        waiting_count = sum(1 for s in steps if s["status"] == "waiting")

        # Create initial report structure
        initial_report = {
            "run_name": run_name,
            "test_file": test_file_path,
            "test_type": test_type,
            "environment": environment,
            "status": "RUNNING",
            "start_time": start_time,
            "end_time": None,
            "duration_seconds": None,
            "return_code": None,
            "success_rate": None,
            "steps_total": len(steps),
            "steps_passed": 0,
            "steps_failed": 0,
            "steps_skipped": skipped_count,
            "steps_executed": 0,
            "current_step": 1,
            "steps": steps,
            "log_file": f"logs/{run_name}.txt",
            "command": None,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }

        # Save initial report
        report_file = Path(f"reports/{run_name}.txt")
        with open(report_file, 'w') as f:
            json.dump(initial_report, f, indent=2)

        logger.info(
            f"Created initial report for {run_name} with {len(steps)} steps")
        return initial_report

    except Exception as e:
        logger.error(f"Error creating initial report for {run_name}: {e}")
        return None


def update_step_status(run_name: str,
                       step_number: int,
                       status: str,
                       failure_reason: str = None,
                       duration: float = 0.0) -> bool:
    """Update individual step status in the report file."""
    try:
        report_file = Path(f"reports/{run_name}.txt")
        if not report_file.exists():
            logger.warning(f"Report file not found for run: {run_name}")
            return False

        # Read current report
        with open(report_file, 'r') as f:
            report = json.load(f)

        # Find and update the step
        step_found = False
        for step in report.get("steps", []):
            if step["step_number"] == step_number:
                step["status"] = status
                step["duration_seconds"] = duration
                step["completed_at"] = datetime.now().isoformat()

                if status == "running":
                    step["started_at"] = datetime.now().isoformat()
                elif status == "failed" and failure_reason:
                    step["failure_reason"] = failure_reason

                step_found = True
                break

        if not step_found:
            logger.warning(
                f"Step {step_number} not found in report for {run_name}")
            return False

        # Update overall statistics
        passed_count = sum(1 for s in report["steps"]
                           if s["status"] == "passed")
        failed_count = sum(1 for s in report["steps"]
                           if s["status"] == "failed")
        skipped_count = sum(1 for s in report["steps"]
                            if s["status"] == "skipped")
        # Executed = steps that have completed (passed or failed)
        executed_count = sum(1 for s in report["steps"]
                             if s["status"] in ["passed", "failed"])

        report["steps_passed"] = passed_count
        report["steps_failed"] = failed_count
        report["steps_skipped"] = skipped_count
        report["steps_executed"] = executed_count
        report["last_updated"] = datetime.now().isoformat()

        # Update current step if this step is running
        if status == "running":
            report["current_step"] = step_number

        # Save updated report
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.debug(
            f"Updated step {step_number} status to {status} for run {run_name}"
        )
        return True

    except Exception as e:
        logger.error(f"Error updating step status for {run_name}: {e}")
        return False


def find_report_step_by_number(execution_step_num: int,
                               report_steps: List[Dict]) -> Optional[int]:
    """Find report step by exact step number - simple and reliable."""
    try:
        # Direct step number mapping - engine step N should map to report step N
        for step in report_steps:
            if step['step_number'] == execution_step_num:
                logger.debug(
                    f"✅ Direct match: execution step {execution_step_num} → report step {step['step_number']}"
                )
                return step['step_number']

        logger.warning(
            f"❌ No direct match found for execution step {execution_step_num}")
        return None

    except Exception as e:
        logger.error(f"Error in step number matching: {e}")
        return None


async def parse_and_update_steps_from_log(run_name: str, log_content: str,
                                          last_step_detected: int) -> int:
    """Parse log content and update step statuses with execution-to-report mapping."""
    import re

    try:
        # Get current report to access step data
        report_file = Path(f"reports/{run_name}.txt")
        if not report_file.exists():
            logger.warning(
                f"Report file not found for step mapping: {run_name}")
            return last_step_detected

        with open(report_file, 'r') as f:
            report_data = json.load(f)

        report_steps = report_data.get("steps", [])
        if not report_steps:
            logger.warning(f"No steps found in report for mapping: {run_name}")
            return last_step_detected

        # Track execution step to report step mapping
        execution_to_report = {}
        lines = log_content.split('\n')
        current_running_report_step = None
        latest_execution_step = last_step_detected

        # PHASE 1: Build complete mapping by processing all start messages first
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Only look for step start patterns to build mapping
            step_start_match = re.search(r'📍 Step (\d+)/\d+: (.+)', line)
            if step_start_match:
                execution_step = int(step_start_match.group(1))
                instruction = step_start_match.group(2).strip()

                # Find matching report step using direct step number mapping
                report_step_num = find_report_step_by_number(
                    execution_step, report_steps)

                if report_step_num:
                    execution_to_report[execution_step] = report_step_num
                    logger.debug(
                        f"Pre-mapped execution step {execution_step} → report step {report_step_num}"
                    )

        # PHASE 2: Process step status updates with complete mapping
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 1. Look for step start patterns
            step_start_match = re.search(r'📍 Step (\d+)/\d+: (.+)', line)
            if step_start_match:
                execution_step = int(step_start_match.group(1))
                instruction = step_start_match.group(2).strip()

                # Complete previous step if still running
                if current_running_report_step and execution_step > latest_execution_step:
                    logger.debug(
                        f"Auto-completing previous step {current_running_report_step} (missing completion)"
                    )
                    update_step_status(run_name, current_running_report_step,
                                       "passed", "Auto-completed", 0.0)
                    current_running_report_step = None

                # Use pre-built mapping
                report_step_num = execution_to_report.get(execution_step)
                if report_step_num:
                    logger.debug(
                        f"🔄 Processing execution step {execution_step} → report step {report_step_num}"
                    )

                    # Check if this is a comment step - if so, don't update it
                    report_step = next(
                        (s for s in report_steps
                         if s['step_number'] == report_step_num), None)
                    if report_step and report_step.get('is_comment', False):
                        logger.debug(
                            f"🚫 SKIPPING update for comment step {report_step_num} - keeping as 'skipped'"
                        )
                        # Don't set current_running_report_step for comment steps
                        latest_execution_step = execution_step
                    else:
                        # Set this step as running (only for non-comment steps)
                        success = update_step_status(run_name, report_step_num,
                                                     "running")
                        if success:
                            current_running_report_step = report_step_num
                            latest_execution_step = execution_step
                            logger.debug(
                                f"✅ Step {report_step_num} set to RUNNING")
                        else:
                            logger.error(
                                f"❌ Failed to set step {report_step_num} to running"
                            )
                else:
                    logger.warning(
                        f"❌ No mapping found for execution step {execution_step}"
                    )

            # 2. Look for step completion patterns
            step_complete_match = re.search(
                r'✅ Step (\d+) completed successfully', line)
            if step_complete_match:
                execution_step = int(step_complete_match.group(1))

                # Extract duration
                duration_match = re.search(r'\(([0-9.]+)s total\)', line)
                duration = float(
                    duration_match.group(1)) if duration_match else 0.0

                # Find corresponding report step
                report_step_num = execution_to_report.get(execution_step)
                if report_step_num:
                    # Check if this is a comment step - if so, don't update it
                    report_step = next(
                        (s for s in report_steps
                         if s['step_number'] == report_step_num), None)
                    if report_step and report_step.get('is_comment', False):
                        logger.info(
                            f"🚫 SKIPPING completion for comment step {report_step_num} - keeping as 'skipped'"
                        )
                    else:
                        logger.debug(
                            f"Completing execution step {execution_step} → report step {report_step_num} (passed)"
                        )
                        update_step_status(run_name, report_step_num, "passed",
                                           None, duration)
                        if current_running_report_step == report_step_num:
                            current_running_report_step = None
                else:
                    logger.warning(
                        f"Completion for unmapped execution step {execution_step}"
                    )

            # 3. Look for step failure patterns
            step_fail_match = re.search(r'❌ Step (\d+) failed', line)
            if step_fail_match:
                execution_step = int(step_fail_match.group(1))

                # Extract duration
                duration_match = re.search(r'\(([0-9.]+)s total\)', line)
                duration = float(
                    duration_match.group(1)) if duration_match else 0.0

                # Find corresponding report step
                report_step_num = execution_to_report.get(execution_step)
                if report_step_num:
                    # Check if this is a comment step - if so, don't update it
                    report_step = next(
                        (s for s in report_steps
                         if s['step_number'] == report_step_num), None)
                    if report_step and report_step.get('is_comment', False):
                        logger.info(
                            f"🚫 SKIPPING failure for comment step {report_step_num} - keeping as 'skipped'"
                        )
                    else:
                        logger.debug(
                            f"Failing execution step {execution_step} → report step {report_step_num} (failed)"
                        )
                        update_step_status(run_name, report_step_num, "failed",
                                           line.strip(), duration)
                        if current_running_report_step == report_step_num:
                            current_running_report_step = None
                else:
                    logger.warning(
                        f"Failure for unmapped execution step {execution_step}"
                    )

            # 4. Look for general error indicators that might affect current step
            if (current_running_report_step
                    and any(indicator in line.lower() for indicator in
                            ['error:', 'failed:', 'exception:', 'timeout:'])):
                logger.debug(
                    f"Error detected, failing current running step {current_running_report_step}: {line}"
                )
                update_step_status(run_name, current_running_report_step,
                                   "failed", line.strip())
                current_running_report_step = None

        return latest_execution_step

    except Exception as e:
        logger.error(
            f"Error in parse_and_update_steps_from_log for {run_name}: {e}")
        return last_step_detected


async def monitor_running_test(run_name: str):
    """Monitor a running test process and update status when complete."""
    if run_name not in running_tests:
        logger.warning(f"Test {run_name} not found in running tests")
        return

    test_info = running_tests[run_name]
    process = test_info["process"]

    logger.info(
        f"Starting monitoring for test: {run_name} (PID: {test_info['pid']})")

    # Track log file size to detect new content
    log_file_path = Path(test_info["log_file"])
    last_log_size = 0
    last_step_detected = 0

    try:
        # Poll process status and log file every second
        while True:
            # Check if process has completed
            return_code = process.poll()

            # Monitor log file for real-time step updates
            if log_file_path.exists():
                current_log_size = log_file_path.stat().st_size
                if current_log_size > last_log_size:
                    # New content in log file - try to parse step updates
                    try:
                        with open(log_file_path, 'r') as f:
                            f.seek(
                                last_log_size)  # Start from where we left off
                            new_content = f.read()

                        # Parse new log content for step information
                        last_step_detected = await parse_and_update_steps_from_log(
                            run_name, new_content, last_step_detected)
                        last_log_size = current_log_size

                    except Exception as e:
                        logger.debug(
                            f"Error parsing log updates for {run_name}: {e}")

            if return_code is not None:
                # Process finished - update status and create report
                end_time = datetime.now()
                start_time = datetime.fromisoformat(test_info["start_time"])
                duration = (end_time - start_time).total_seconds()

                # Determine final status
                status = "COMPLETED" if return_code == 0 else "FAILED"

                # Try to parse success rate from log file
                success_rate = None
                try:
                    if Path(test_info["log_file"]).exists():
                        with open(test_info["log_file"], 'r') as f:
                            log_content = f.read()

                        # Look for success rate in log
                        import re
                        success_match = re.search(r'Success Rate: ([\d.]+)%',
                                                  log_content)
                        if success_match:
                            success_rate = float(success_match.group(1))
                except Exception as e:
                    logger.warning(
                        f"Could not parse success rate for {run_name}: {e}")

                # Update final report preserving step data
                try:
                    # Read existing structured report to preserve step data
                    report_file = Path(test_info["report_file"])
                    if report_file.exists():
                        with open(report_file, 'r') as f:
                            existing_report = json.load(f)
                    else:
                        existing_report = {}

                    # Update final report with completion data while preserving steps
                    existing_report.update({
                        "status":
                        status,
                        "end_time":
                        end_time.isoformat(),
                        "duration_seconds":
                        duration,
                        "return_code":
                        return_code,
                        "success_rate":
                        success_rate,
                        "command":
                        test_info["command"],
                        "last_updated":
                        datetime.now().isoformat()
                    })

                    # Complete any steps still in running state
                    steps = existing_report.get("steps", [])
                    if steps:
                        running_steps = [
                            s for s in steps if s.get("status") == "running"
                        ]
                        if running_steps:
                            logger.info(
                                f"Auto-completing {len(running_steps)} running steps for final report"
                            )
                            for step in running_steps:
                                if not step.get(
                                        "is_comment",
                                        False):  # Don't update comment steps
                                    step["status"] = "passed"
                                    step["completed_at"] = end_time.isoformat()
                                    logger.info(
                                        f"Auto-completed step {step['step_number']}: {step['instruction'][:50]}..."
                                    )

                        # Calculate final step statistics from the steps array
                        passed_count = sum(1 for s in steps
                                           if s.get("status") == "passed")
                        failed_count = sum(1 for s in steps
                                           if s.get("status") == "failed")
                        skipped_count = sum(1 for s in steps
                                            if s.get("status") == "skipped")
                        # For final report, executed = completed steps only
                        executed_count = sum(
                            1 for s in steps
                            if s.get("status") in ["passed", "failed"])

                        existing_report.update({
                            "steps_passed": passed_count,
                            "steps_failed": failed_count,
                            "steps_skipped": skipped_count,
                            "steps_executed": executed_count
                        })

                    # Save updated report preserving all step data
                    with open(test_info["report_file"], 'w') as f:
                        json.dump(existing_report, f, indent=2)

                    logger.info(
                        f"Final report updated for test: {run_name} - preserving {len(steps)} steps"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to update final report for {run_name}: {e}")

                    # Fallback: create basic report
                    fallback_report = {
                        "run_name": run_name,
                        "test_file": test_info["test_file"],
                        "test_type": test_info["test_type"],
                        "environment": test_info["environment"],
                        "status": status,
                        "start_time": test_info["start_time"],
                        "end_time": end_time.isoformat(),
                        "duration_seconds": duration,
                        "return_code": return_code,
                        "success_rate": success_rate,
                        "log_file": test_info["log_file"],
                        "command": test_info["command"]
                    }

                    with open(test_info["report_file"], 'w') as f:
                        json.dump(fallback_report, f, indent=2)

                # Append completion info to log file
                try:
                    with open(test_info["log_file"], 'a') as log_f:
                        log_f.write(f"\n" + "=" * 50 + "\n")
                        log_f.write(f"Completed at: {end_time.isoformat()}\n")
                        log_f.write(f"Return code: {return_code}\n")
                        log_f.write(f"Duration: {duration:.2f} seconds\n")
                        log_f.write(f"Status: {status}\n")
                        if success_rate is not None:
                            log_f.write(f"Success Rate: {success_rate}%\n")
                except Exception as e:
                    logger.warning(
                        f"Failed to update log file for {run_name}: {e}")

                logger.info(
                    f"Test {run_name} completed with status: {status} (return code: {return_code})"
                )
                break

            # Wait 1 second before next check (non-blocking)
            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Error monitoring test {run_name}: {e}")
        # Mark as failed if monitoring fails
        status = "FAILED"

    finally:
        # Remove from running tests when done
        if run_name in running_tests:
            logger.info(f"Removing {run_name} from running tests")
            del running_tests[run_name]


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
            r'^navigate to\s+', r'^click\s+', r'^type\s+', r'^verify\s+',
            r'^wait\s+', r'^upload\s+', r'^select\s+', r'^scroll\s+'
        ]

        if line.startswith('#') or line.startswith('//'):
            continue  # Comment line

        if not any(
                re.match(pattern, line.lower())
                for pattern in action_patterns):
            warnings.append(
                f"Line {i}: Unrecognized instruction format: '{line[:50]}...'")

    # Determine status
    if errors:
        status = "invalid"
    elif warnings:
        status = "warning"
    else:
        status = "valid"

    return ValidationResult(status=status,
                            errors=errors,
                            warnings=warnings,
                            last_validated=datetime.now().isoformat())


def process_api_yaml(content: str) -> str:
    """
    Process API YAML content and convert different formats to the standard format.
    
    Handles two main formats:
    1. Simple format: uses 'tests' array with 'endpoint' field
    2. Advanced format: uses 'endpoints' array with 'url' field
    
    Converts advanced format to simple format for consistency.
    """
    try:
        # Parse YAML
        data = yaml.safe_load(content)
        
        if not isinstance(data, dict):
            return content  # Return as-is if not a dict
        
        # Check if this is the advanced format (has 'endpoints' instead of 'tests')
        if 'endpoints' in data and 'tests' not in data:
            logger.info("Converting advanced YAML format to simple format")
            
            # Convert endpoints to tests
            tests = []
            for endpoint in data['endpoints']:
                test = {}
                
                # Required fields mapping
                if 'name' in endpoint:
                    test['name'] = endpoint['name']
                if 'method' in endpoint:
                    test['method'] = endpoint['method']
                
                # Map 'url' to 'endpoint'
                if 'url' in endpoint:
                    test['endpoint'] = endpoint['url']
                elif 'endpoint' in endpoint:
                    test['endpoint'] = endpoint['endpoint']
                
                # Map status codes
                if 'expected_status' in endpoint:
                    test['expected_status'] = endpoint['expected_status']
                
                # Optional fields that can be passed through directly
                optional_fields = [
                    'headers', 'body', 'payload', 'timeout', 'description',
                    'required_response_fields', 'optional_response_fields', 
                    'field_types', 'auth_credential'
                ]
                for field in optional_fields:
                    if field in endpoint:
                        test[field] = endpoint[field]
                
                # Map 'payload' to 'body' if body doesn't exist
                if 'payload' in endpoint and 'body' not in test:
                    test['body'] = endpoint['payload']
                
                tests.append(test)
            
            # Create new structure
            converted_data = {
                'name': data.get('name', 'API Test'),
                'base_url': data.get('base_url', ''),
                'tests': tests
            }
            
            # Add optional global fields if they exist
            if 'description' in data:
                converted_data['description'] = data['description']
            if 'global_headers' in data:
                converted_data['global_headers'] = data['global_headers']
            if 'global_auth' in data:
                converted_data['global_auth'] = data['global_auth']
            
            # Convert back to YAML
            converted_yaml = yaml.dump(converted_data, default_flow_style=False, sort_keys=False)
            logger.info("Successfully converted advanced YAML format to simple format")
            return converted_yaml
        
        else:
            # Already in simple format or unknown format, return as-is
            return content
            
    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse YAML for conversion: {e}")
        return content  # Return original content if parsing fails
    except Exception as e:
        logger.warning(f"Error processing YAML: {e}")
        return content


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
                    if 'method' in test and test['method'].upper() not in [
                            'GET', 'POST', 'PUT', 'DELETE', 'PATCH'
                    ]:
                        warnings.append(
                            f"Test {i+1}: Unusual HTTP method '{test['method']}'"
                        )

    except yaml.YAMLError as e:
        errors.append(f"Invalid YAML format: {str(e)}")

    # Determine status
    if errors:
        status = "invalid"
    elif warnings:
        status = "warning"
    else:
        status = "valid"

    return ValidationResult(status=status,
                            errors=errors,
                            warnings=warnings,
                            last_validated=datetime.now().isoformat())


def validate_test_configuration(test_type: str,
                                content: str) -> ValidationResult:
    """Validate test configuration based on type."""
    if test_type == "UI":
        return validate_ui_test(content)
    elif test_type == "API":
        return validate_api_test(content)
    else:
        return ValidationResult(status="invalid",
                                errors=[f"Unknown test type: {test_type}"])


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
                if file_path.is_file(
                ) and file_path.suffix == '.json' and file_path.name != 'encryption.key':
                    try:
                        with open(file_path, 'r') as f:
                            credential_data = json.load(f)

                        # Return only metadata, not sensitive data
                        credential_info = {
                            "credential_id":
                            credential_data["credential_id"],
                            "credential_name":
                            credential_data["credential_name"],
                            "type":
                            credential_data["type"],
                            "environment":
                            credential_data["environment"],
                            "description":
                            credential_data.get("description"),
                            "fields":
                            list(credential_data["encrypted_data"].keys()),
                            "created_at":
                            credential_data["created_at"],
                            "modified_at":
                            credential_data["modified_at"]
                        }
                        credentials.append(credential_info)

                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(
                            f"Invalid credential file {file_path}: {e}")
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


@app.post("/test-configurations",
          status_code=201,
          summary="Create Test Configuration")
async def create_test_configuration(
        test_name: str = Form(...),
        test_type: str = Form(...),
        instruction: Optional[str] = Form(None),
        apis_documentation: Optional[UploadFile] = File(None),
        file: Optional[UploadFile] = File(None)):
    """
    Create a new test configuration.
    
    Supports both form data with text content and file upload.
    Validates test syntax before saving.
    """
    try:
        # Validate test_type
        if test_type not in ["UI", "API"]:
            raise HTTPException(status_code=400,
                                detail="test_type must be 'UI' or 'API'")

        # Get content from either form data or uploaded file
        content = None
        if file:
            # Read content from uploaded file via 'file' parameter
            raw_content = (await file.read()).decode('utf-8')
            # Process API YAML content if it's an API test
            if test_type == "API":
                content = process_api_yaml(raw_content)
            else:
                content = raw_content
        elif apis_documentation:
            # Read content from uploaded file via 'apis_documentation' parameter
            raw_content = (await apis_documentation.read()).decode('utf-8')
            # Process API YAML content if it's an API test
            if test_type == "API":
                content = process_api_yaml(raw_content)
            else:
                content = raw_content
        else:
            # Use text form data
            if test_type == "UI":
                if not instruction:
                    raise HTTPException(
                        status_code=400,
                        detail="instruction is required for UI tests")
                content = instruction
            else:  # API
                raise HTTPException(
                    status_code=400,
                    detail="apis_documentation file is required for API tests")

        if not content:
            raise HTTPException(status_code=400,
                                detail="No test content provided")

        # Validate test content
        validation_result = validate_test_configuration(test_type, content)
        if validation_result.status == "invalid":
            raise HTTPException(status_code=400,
                                detail={
                                    "error": "Test validation failed",
                                    "validation": validation_result.dict()
                                })

        # Determine file extension
        file_extension = ".txt" if test_type == "UI" else ".yml"

        # Create file path
        file_name = f"{test_name}{file_extension}"
        file_path = Path(f"Test/{test_type}/{file_name}")

        # Check if file already exists
        if file_path.exists():
            raise HTTPException(
                status_code=409,
                detail=f"Test configuration '{test_name}' already exists")

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
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create test configuration: {str(e)}")


@app.get("/test-configurations", summary="Get All Test Configurations")
async def get_test_configurations(
        test_type: Optional[str] = Query(
            None, description="Filter by test type (UI or API)"),
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
                raise HTTPException(status_code=400,
                                    detail="test_type must be 'UI' or 'API'")
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

                        # Validate test to get status and read content
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            validation = validate_test_configuration(
                                scan_type, content)
                            status = validation.status
                        except Exception:
                            status = "invalid"
                            content = None

                        test_configs.append(
                            TestConfigInfo(test_name=test_name,
                                           test_type=scan_type,
                                           file_path=str(file_path),
                                           created_at=datetime.fromtimestamp(
                                               stat.st_ctime).isoformat(),
                                           modified_at=datetime.fromtimestamp(
                                               stat.st_mtime).isoformat(),
                                           size_bytes=stat.st_size,
                                           status=status,
                                           instruction=content))

        # Sort by creation time (newest first)
        test_configs.sort(key=lambda x: x.created_at, reverse=True)

        # Apply pagination
        total = len(test_configs)
        paginated_configs = test_configs[offset:offset + limit]

        logger.info(
            f"Retrieved {len(paginated_configs)}/{total} test configurations")
        return paginated_configs

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving test configurations: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve test configurations: {str(e)}")


@app.get("/test-configurations/{test_name}",
         summary="Get Specific Test Configuration")
async def get_test_configuration(
    test_name: str,
    test_type: Optional[str] = Query(None, description="Test type (UI or API)")
) -> TestConfigDetail:
    """Get details and content for a specific test configuration."""
    try:
        # If test_type is specified, look only in that folder
        if test_type:
            if test_type not in ["UI", "API"]:
                raise HTTPException(status_code=400,
                                    detail="test_type must be 'UI' or 'API'")
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

                    return TestConfigDetail(test_name=test_name,
                                            test_type=folder,
                                            file_path=str(file_path),
                                            content=content,
                                            created_at=datetime.fromtimestamp(
                                                stat.st_ctime).isoformat(),
                                            modified_at=datetime.fromtimestamp(
                                                stat.st_mtime).isoformat(),
                                            size_bytes=stat.st_size,
                                            validation=validation)

        # Test not found
        raise HTTPException(
            status_code=404,
            detail=f"Test configuration '{test_name}' not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving test configuration {test_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve test configuration: {str(e)}")


@app.put("/test-configurations/{test_name}",
         summary="Update Test Configuration")
async def update_test_configuration(test_name: str,
                                    request: UpdateTestConfigRequest,
                                    test_type: Optional[str] = Query(
                                        None,
                                        description="Test type (UI or API)")):
    """Update an existing test configuration."""
    try:
        # Find the test file
        if test_type:
            if test_type not in ["UI", "API"]:
                raise HTTPException(status_code=400,
                                    detail="test_type must be 'UI' or 'API'")
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
            raise HTTPException(
                status_code=404,
                detail=f"Test configuration '{test_name}' not found")

        # Get new content
        if current_type == "UI":
            if not request.instruction:
                raise HTTPException(
                    status_code=400,
                    detail="instruction is required for UI tests")
            new_content = request.instruction
        else:  # API
            if not request.apis_documentation:
                raise HTTPException(
                    status_code=400,
                    detail="apis_documentation is required for API tests")
            new_content = request.apis_documentation

        # Validate new content
        validation_result = validate_test_configuration(
            current_type, new_content)
        if validation_result.status == "invalid":
            raise HTTPException(status_code=400,
                                detail={
                                    "error": "Test validation failed",
                                    "validation": validation_result.dict()
                                })

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
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update test configuration: {str(e)}")


@app.delete("/test-configurations/{test_name}",
            summary="Delete Test Configuration")
async def delete_test_configuration(test_name: str,
                                    test_type: Optional[str] = Query(
                                        None,
                                        description="Test type (UI or API)")):
    """Delete a specific test configuration."""
    try:
        # If test_type is specified, look only in that folder
        if test_type:
            if test_type not in ["UI", "API"]:
                raise HTTPException(status_code=400,
                                    detail="test_type must be 'UI' or 'API'")
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
        raise HTTPException(
            status_code=404,
            detail=f"Test configuration '{test_name}' not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting test configuration {test_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete test configuration: {str(e)}")


@app.post("/test-configurations/{test_name}/validate",
          summary="Validate Test Configuration")
async def validate_test_config(
    test_name: str,
    test_type: Optional[str] = Query(None)) -> ValidationResult:
    """Validate a test configuration without saving changes."""
    try:
        # Find the test file
        if test_type:
            if test_type not in ["UI", "API"]:
                raise HTTPException(status_code=400,
                                    detail="test_type must be 'UI' or 'API'")
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

        raise HTTPException(
            status_code=404,
            detail=f"Test configuration '{test_name}' not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating test configuration {test_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate test configuration: {str(e)}")


# ============================================================================
# RUN TEST APIs
# ============================================================================


async def execute_quantumqa_test(request: dict) -> Dict[str, Any]:
    """Execute QuantumQA test using the existing framework."""
    try:
        # Extract values from request dict
        run_name = request.get('run_name', '')
        test_file_path = request.get('test_file_path', '')
        test_type = request.get('test_type', '')
        env = request.get('env', '')

        # Prepare log and report file paths
        log_file = f"logs/{run_name}.txt"
        report_file = f"reports/{run_name}.txt"

        # Prepare command
        cmd = [
            "python", "quantumqa_runner.py", test_file_path, "--type",
            test_type.lower(), "--run-name", run_name
        ]

        # Handle credentials
        credentials = request.get('credentials')
        credential_id = request.get('credential_id')
        creds_content = ""

        if credentials:
            if credentials.get('username') and credentials.get('password'):
                creds_content += f"""
ui_credentials:
  username: "{credentials.get('username')}"
  password: "{credentials.get('password')}"
  base_url: "{env}"
"""
            if credentials.get('api_key'):
                creds_content += f"""
api_credentials:
  api_key: "{credentials.get('api_key')}"
  base_url: "{env}"
"""
        elif credential_id:
            # Load stored credentials
            stored_creds = get_credential_for_run(credential_id)
            if not stored_creds:
                return {
                    "run_name": run_name,
                    "status": "ERROR",
                    "error":
                    f"Credential '{credential_id}' not found or invalid",
                    "end_time": datetime.now().isoformat()
                }

            if stored_creds.username and stored_creds.password:
                creds_content += f"""
ui_credentials:
  username: "{stored_creds.username}"
  password: "{stored_creds.password}"
  base_url: "{env}"
"""
            if stored_creds.api_key:
                creds_content += f"""
api_credentials:
  api_key: "{stored_creds.api_key}"
  base_url: "{env}"
"""

        if creds_content:
            # Create temporary credentials file
            creds_file = f"logs/{run_name}_creds.yaml"
            with open(creds_file, 'w') as f:
                f.write(creds_content)
            cmd.extend(["--credentials", creds_file])

        # Add options
        options = request.get('options', {})
        if test_type == "UI":
            if not options.get('headless', True):
                cmd.append("--visible")
            if options.get('performance_measurement', False):
                cmd.append("--performance-measurement")
            if options.get('disable_caching', False):
                cmd.append("--disable-caching")
            if options.get('disable_performance', False):
                cmd.append("--disable-performance")

        logger.info(f"Executing command: {' '.join(cmd)}")

        # Execute the command and capture output
        start_time = datetime.now()

        # Initialize log file
        with open(log_file, 'w') as log_f:
            log_f.write(f"=== QuantumQA Test Execution Log ===\n")
            log_f.write(f"Command: {' '.join(cmd)}\n")
            log_f.write(f"Started at: {start_time.isoformat()}\n")
            log_f.write("=" * 50 + "\n\n")
            log_f.flush()

        # Execute the command in detached mode (non-blocking)
        try:
            # Start process without blocking - redirect output to log file
            with open(log_file, 'a') as log_f:
                process = subprocess.Popen(cmd,
                                           stdout=log_f,
                                           stderr=subprocess.STDOUT,
                                           text=True,
                                           cwd=os.getcwd())

            # Store process info for tracking
            process_info = {
                "process": process,
                "pid": process.pid,
                "start_time": start_time.isoformat(),
                "log_file": log_file,
                "report_file": report_file,
                "command": " ".join(cmd)
            }

            logger.info(
                f"Started detached process PID {process.pid} for test: {run_name}"
            )

            # Return immediately - process will be monitored by background task
            return {
                "run_name": run_name,
                "status": "RUNNING",
                "pid": process.pid,
                "start_time": start_time.isoformat(),
                "log_file": log_file,
                "command": " ".join(cmd),
                "process_info": process_info  # For background monitoring
            }

        except Exception as e:
            error_msg = f"Failed to start process: {str(e)}"
            logger.error(error_msg)

            # Write error to log file
            with open(log_file, 'a') as log_f:
                log_f.write(f"\nERROR: {error_msg}\n")
                log_f.write(f"Failed at: {datetime.now().isoformat()}\n")

            return {
                "run_name": run_name,
                "status": "ERROR",
                "error": error_msg,
                "end_time": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"Error executing test: {e}")
        return {
            "run_name": run_name,
            "status": "ERROR",
            "error": str(e),
            "end_time": datetime.now().isoformat()
        }


@app.post("/runs", status_code=202, summary="Execute Test Run")
async def run_test(request: dict, background_tasks: BackgroundTasks):
    """Execute a test with the given configuration."""
    try:
        # Basic validation (manual, not Pydantic)
        test_type = request.get('test_type', '')
        if test_type not in ["UI", "API"]:
            raise HTTPException(status_code=400,
                                detail="test_type must be 'UI' or 'API'")

        # Check if test file exists
        test_file_path = request.get('test_file_path', '')
        if not test_file_path or not Path(test_file_path).exists():
            raise HTTPException(
                status_code=404,
                detail=f"Test file not found: {test_file_path}")

        # Check if run with same name is already running
        run_name = request.get('run_name', '')
        if run_name in running_tests:
            raise HTTPException(
                status_code=409,
                detail=f"Test run '{run_name}' is already in progress")

        # Validate credentials
        credentials = request.get('credentials')
        credential_id = request.get('credential_id')
        if not credentials and not credential_id:
            raise HTTPException(
                status_code=400,
                detail="Either credentials or credential_id is required")

        if credentials:
            if test_type == "UI" and not (credentials.get('username')
                                          and credentials.get('password')):
                raise HTTPException(
                    status_code=400,
                    detail="username and password are required for UI tests")

            if test_type == "API" and not credentials.get('token'):
                raise HTTPException(status_code=400,
                                    detail="token is required for API tests")

        # Execute test and get process info
        result = await execute_quantumqa_test(request)

        if result.get("status") == "ERROR":
            # If immediate error, don't track as running
            raise HTTPException(status_code=500,
                                detail=result.get("error",
                                                  "Failed to start test"))

        # Create initial report with all steps in 'waiting' status
        env = request.get('env', '')
        initial_report = create_initial_report(run_name, test_file_path,
                                               test_type, env,
                                               result["start_time"])

        if not initial_report:
            raise HTTPException(status_code=500,
                                detail="Failed to create initial test report")

        # Store process info in running_tests for monitoring
        running_tests[run_name] = {
            "status": "RUNNING",
            "start_time": result["start_time"],
            "test_file": test_file_path,
            "test_type": test_type,
            "environment": env,
            "process": result["process_info"]["process"],
            "pid": result["pid"],
            "log_file": result["log_file"],
            "report_file": result["process_info"]["report_file"],
            "command": result["command"]
        }

        # Start background monitoring task
        async def monitor_test_process():
            await monitor_running_test(run_name)

        background_tasks.add_task(monitor_test_process)

        logger.info(f"Started test run: {run_name}")

        return {
            "message": "Test execution started",
            "run_name": run_name,
            "status": "RUNNING",
            "log_file_url": f"/runs/{run_name}/logs",
            "report_file_url": f"/runs/{run_name}/report",
            "started_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting test run: {e}")
        raise HTTPException(status_code=500,
                            detail=f"Failed to start test execution: {str(e)}")


@app.get("/runs", summary="Get All Test Runs")
async def get_runs(
        status: Optional[str] = Query(None, description="Filter by status"),
        test_type: Optional[str] = Query(None,
                                         description="Filter by test type"),
        limit: int = Query(50, description="Maximum number of results"),
        offset: int = Query(0, description="Number of results to skip")
) -> Dict[str, Any]:
    """List all test run reports."""
    try:
        runs = []
        reports_folder = Path("reports")
        
        # Add completed runs from reports (exclude currently running tests)
        if reports_folder.exists():
            for file_path in reports_folder.iterdir():
                if file_path.is_file() and file_path.suffix == '.txt':
                    run_name = file_path.stem
                    
                    # Skip if this test is currently running to avoid duplicates
                    if run_name in running_tests:
                        logger.info(f"Skipping {run_name} from reports folder - test is currently running (avoiding duplicate)")
                        continue
                    
                    try:
                        # Try to read report as JSON
                        with open(file_path, 'r') as f:
                            report_data = json.load(f)
                        
                        test_file = report_data.get("test_file", "unknown")
                        test_name = extract_test_name_from_file(test_file)
                        
                        run_info = RunInfo(
                            run_name=run_name,
                            test_file=test_file,
                            test_name=test_name,
                            test_type=report_data.get("test_type", "unknown"),
                            status=report_data.get("status", "unknown"),
                            started_at=report_data.get("start_time",
                                                       "unknown"),
                            completed_at=report_data.get("end_time"),
                            duration_seconds=report_data.get(
                                "duration_seconds"),
                            success_rate=report_data.get("success_rate"),
                            # Extract consolidated step statistics
                            steps_total=report_data.get("steps_total"),
                            steps_passed=report_data.get("steps_passed"),
                            steps_failed=report_data.get("steps_failed"),
                            steps_executed=report_data.get("steps_executed"),
                            log_file_url=f"/runs/{run_name}/logs",
                            report_file_url=f"/runs/{run_name}/report")

                        runs.append(run_info)

                    except (json.JSONDecodeError, KeyError):
                        # Handle non-JSON report files
                        stat = file_path.stat()
                        
                        run_info = RunInfo(
                            run_name=run_name,
                            test_file="unknown",
                            test_name="unknown",
                            test_type="unknown",
                            status="COMPLETED",
                            started_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                            # No step statistics available for legacy reports
                            steps_total=None,
                            steps_passed=None,
                            steps_failed=None,
                            steps_executed=None,
                            log_file_url=f"/runs/{run_name}/logs",
                            report_file_url=f"/runs/{run_name}/report")
                        runs.append(run_info)

        # Add currently running tests
        for run_name, run_data in running_tests.items():
            test_file = run_data.get("test_file", "unknown")
            test_name = extract_test_name_from_file(test_file)
            
            # Try to get current step statistics from report if available
            steps_total = None
            steps_passed = None
            steps_failed = None
            steps_executed = None
            
            try:
                report_file = Path(f"reports/{run_name}.txt")
                if report_file.exists():
                    with open(report_file, 'r') as f:
                        report_data = json.load(f)
                    steps_total = report_data.get("steps_total")
                    steps_passed = report_data.get("steps_passed")
                    steps_failed = report_data.get("steps_failed")
                    steps_executed = report_data.get("steps_executed")
            except Exception:
                pass  # Use default None values
            
            run_info = RunInfo(
                run_name=run_name,
                test_file=test_file,
                test_name=test_name,
                test_type=run_data.get("test_type", "unknown"),
                status="RUNNING",
                started_at=run_data.get("start_time", "unknown"),
                # Include step statistics if available
                steps_total=steps_total,
                steps_passed=steps_passed,
                steps_failed=steps_failed,
                steps_executed=steps_executed,
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
        raise HTTPException(status_code=500,
                            detail=f"Failed to retrieve runs: {str(e)}")


@app.get("/runs/{run_name}", summary="Get Specific Test Run")
async def get_run(run_name: str) -> RunDetail:
    """Get details and results for a specific test run."""
    try:
        # Check if test is currently running
        if run_name in running_tests:
            run_data = running_tests[run_name]

            # Try to read current progress from structured report file
            report_file = Path(f"reports/{run_name}.txt")
            if report_file.exists():
                try:
                    with open(report_file, 'r') as f:
                        report_data = json.load(f)

                    # Convert report steps to StepResult objects
                    steps = []
                    for step_data in report_data.get("steps", []):
                        steps.append(
                            StepResult(
                                step_number=step_data["step_number"],
                                instruction=step_data["instruction"],
                                status=step_data["status"],
                                duration_seconds=step_data["duration_seconds"],
                                screenshot=step_data.get("screenshot"),
                                failure_reason=step_data.get(
                                    "failure_reason")))

                    return RunDetail(
                        run_name=run_name,
                        test_file=report_data.get(
                            "test_file", run_data.get("test_file", "unknown")),
                        test_type=report_data.get(
                            "test_type", run_data.get("test_type", "unknown")),
                        environment=report_data.get(
                            "environment",
                            run_data.get("environment", "unknown")),
                        status="RUNNING",
                        started_at=report_data.get(
                            "start_time", run_data.get("start_time",
                                                       "unknown")),
                        steps_total=report_data.get("steps_total", 0),
                        steps_passed=report_data.get("steps_passed", 0),
                        steps_failed=report_data.get("steps_failed", 0),
                        steps_skipped=report_data.get("steps_skipped", 0),
                        steps_executed=report_data.get("steps_executed", 0),
                        steps=steps,
                        log_file_url=f"/runs/{run_name}/logs",
                        report_file_url=f"/runs/{run_name}/report")

                except Exception as e:
                    logger.warning(
                        f"Error reading structured report for running test {run_name}: {e}"
                    )

            # Fallback to log parsing if structured report not available
            log_file = Path(f"logs/{run_name}.txt")
            steps, total_steps, passed_steps, failed_steps = parse_log_file_for_steps(
                log_file)
            steps_executed = len(steps)

            return RunDetail(
                run_name=run_name,
                test_file=run_data.get("test_file", "unknown"),
                test_type=run_data.get("test_type", "unknown"),
                environment=run_data.get("environment", "unknown"),
                status="RUNNING",
                started_at=run_data.get("start_time", "unknown"),
                steps_total=total_steps,
                steps_passed=passed_steps,
                steps_failed=failed_steps,
                steps_skipped=0,  # No way to calculate from log parsing
                steps_executed=steps_executed,
                steps=steps,
                log_file_url=f"/runs/{run_name}/logs",
                report_file_url=f"/runs/{run_name}/report")

        # Look for completed test report
        report_file = Path(f"reports/{run_name}.txt")
        if not report_file.exists():
            raise HTTPException(status_code=404,
                                detail=f"Test run '{run_name}' not found")

        # Read report
        with open(report_file, 'r') as f:
            try:
                report_data = json.load(f)
            except json.JSONDecodeError:
                raise HTTPException(status_code=500,
                                    detail="Invalid report format")

        # Check if this is a structured report with steps data
        steps = []
        if "steps" in report_data and report_data["steps"]:
            # Use structured step data from report
            for step_data in report_data["steps"]:
                steps.append(
                    StepResult(step_number=step_data["step_number"],
                               instruction=step_data["instruction"],
                               status=step_data["status"],
                               duration_seconds=step_data["duration_seconds"],
                               screenshot=step_data.get("screenshot"),
                               failure_reason=step_data.get("failure_reason")))

            # Use data from structured report
            total_steps = report_data.get("steps_total", len(steps))
            passed_steps = report_data.get("steps_passed", 0)
            failed_steps = report_data.get("steps_failed", 0)
            skipped_steps = report_data.get("steps_skipped", 0)
            executed_steps = report_data.get("steps_executed", 0)
        else:
            # Fallback: parse logs for step information (legacy reports)
            log_file = Path(f"logs/{run_name}.txt")
            steps, total_steps, passed_steps, failed_steps = parse_log_file_for_steps(
                log_file)
            skipped_steps = 0  # No way to calculate from legacy logs
            executed_steps = len(steps)

        # Find GIF file if available (both path and URL)
        gif_file_path, gif_file_url = find_gif_file_details(run_name)

        return RunDetail(run_name=run_name,
                         test_file=report_data.get("test_file", "unknown"),
                         test_type=report_data.get("test_type", "unknown"),
                         environment=report_data.get("environment", "unknown"),
                         status=report_data.get("status", "unknown"),
                         started_at=report_data.get("start_time", "unknown"),
                         completed_at=report_data.get("end_time"),
                         duration_seconds=report_data.get("duration_seconds"),
                         success_rate=report_data.get("success_rate"),
                         steps_total=total_steps,
                         steps_passed=passed_steps,
                         steps_failed=failed_steps,
                         steps_skipped=skipped_steps,
                         steps_executed=executed_steps,
                         steps=steps,
                         error_summary=report_data.get("error"),
                         log_file_url=f"/runs/{run_name}/logs",
                         report_file_url=f"/runs/{run_name}/report",
                         gif_file_path=gif_file_path,
                         gif_file_url=gif_file_url)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving run {run_name}: {e}")
        raise HTTPException(status_code=500,
                            detail=f"Failed to retrieve run: {str(e)}")


@app.get("/runs/{run_name}/logs", summary="Get Test Run Logs")
async def get_run_logs(run_name: str):
    """Get logs for a specific test run."""
    try:
        log_file = Path(f"logs/{run_name}.txt")
        if not log_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Log file for run '{run_name}' not found")

        return FileResponse(path=str(log_file),
                            media_type='text/plain',
                            filename=f"{run_name}_logs.txt")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving logs for run {run_name}: {e}")
        raise HTTPException(status_code=500,
                            detail=f"Failed to retrieve logs: {str(e)}")


@app.get("/runs/{run_name}/report", summary="Get Test Run Report")
async def get_run_report(run_name: str):
    """Get report for a specific test run."""
    try:
        report_file = Path(f"reports/{run_name}.txt")
        if not report_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Report file for run '{run_name}' not found")

        return FileResponse(path=str(report_file),
                            media_type='application/json',
                            filename=f"{run_name}_report.json")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving report for run {run_name}: {e}")
        raise HTTPException(status_code=500,
                            detail=f"Failed to retrieve report: {str(e)}")


@app.delete("/runs/{run_name}", summary="Cancel Test Run")
async def cancel_run(run_name: str):
    """Cancel a running test."""
    try:
        if run_name not in running_tests:
            # Check if it's a completed run
            report_file = Path(f"reports/{run_name}.txt")
            if report_file.exists():
                raise HTTPException(status_code=409,
                                    detail="Cannot cancel completed test run")
            else:
                raise HTTPException(status_code=404,
                                    detail=f"Test run '{run_name}' not found")

        # Cancel the running test
        run_data = running_tests[run_name]
        if "process" in run_data and run_data["process"]:
            try:
                process = run_data["process"]
                process.terminate()

                # Wait a bit for graceful termination
                import time
                time.sleep(2)

                # Force kill if still running
                if process.poll() is None:
                    process.kill()

                logger.info(
                    f"Terminated process PID {run_data.get('pid', 'unknown')} for test: {run_name}"
                )
            except Exception as e:
                logger.warning(
                    f"Error terminating process for {run_name}: {e}")

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
        raise HTTPException(status_code=500,
                            detail=f"Failed to cancel run: {str(e)}")


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================


@app.get("/status", summary="Get API Status")
async def get_status():
    """Get current API status and statistics."""
    try:
        # Count tests
        ui_tests = len(list(
            Path("Test/UI").glob("*.txt"))) if Path("Test/UI").exists() else 0
        api_tests = len(list(Path("Test/API").glob("*.yml"))) if Path(
            "Test/API").exists() else 0

        # Count runs
        completed_runs = len(list(
            Path("reports").glob("*.txt"))) if Path("reports").exists() else 0
        running_tests_count = len(running_tests)

        # Calculate step statistics across all completed reports
        step_stats = {
            "total_steps": 0,
            "passed_steps": 0,
            "failed_steps": 0,
            "skipped_steps": 0,
            "executed_steps": 0
        }

        if Path("reports").exists():
            for report_file in Path("reports").glob("*.txt"):
                try:
                    with open(report_file, 'r') as f:
                        report_data = json.load(f)

                    step_stats["total_steps"] += report_data.get(
                        "steps_total", 0)
                    step_stats["passed_steps"] += report_data.get(
                        "steps_passed", 0)
                    step_stats["failed_steps"] += report_data.get(
                        "steps_failed", 0)
                    step_stats["skipped_steps"] += report_data.get(
                        "steps_skipped", 0)
                    step_stats["executed_steps"] += report_data.get(
                        "steps_executed", 0)

                except (json.JSONDecodeError, Exception):
                    continue  # Skip invalid report files

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
                },
                "steps": {
                    "total_steps": step_stats["total_steps"],
                    "passed_steps": step_stats["passed_steps"],
                    "failed_steps": step_stats["failed_steps"],
                    "skipped_steps": step_stats["skipped_steps"],
                    "executed_steps": step_stats["executed_steps"]
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


@app.post("/credentials",
          status_code=201,
          summary="Create Encrypted Credentials")
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
                    detail="Field 'api_key' is required for API credentials")

        # Check if credential name already exists for this environment
        existing_credentials = list_credentials()
        for cred in existing_credentials:
            if (cred["credential_name"] == request.credential_name
                    and cred["environment"] == request.environment
                    and cred["type"] == request.type):
                raise HTTPException(
                    status_code=409,
                    detail=
                    f"Credential '{request.credential_name}' already exists for environment '{request.environment}'"
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
        raise HTTPException(status_code=500,
                            detail=f"Failed to create credentials: {str(e)}")


@app.get("/credentials", summary="List Stored Credentials")
async def get_credentials(
        type: Optional[str] = Query(
            None, description="Filter by credential type (UI or API)"),
        environment: Optional[str] = Query(
            None, description="Filter by environment"),
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
                raise HTTPException(status_code=400,
                                    detail="type must be 'UI' or 'API'")
            credentials = [c for c in credentials if c["type"] == type]

        if environment:
            credentials = [
                c for c in credentials if c["environment"] == environment
            ]

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
        raise HTTPException(status_code=500,
                            detail=f"Failed to retrieve credentials: {str(e)}")


@app.get("/credentials/{credential_id}", summary="Get Credential Details")
async def get_credential(credential_id: str) -> CredentialDetail:
    """
    Get details about a specific credential without exposing sensitive data.
    
    Returns metadata only, never actual credential values.
    """
    try:
        credential_data = load_credential(credential_id)
        if not credential_data:
            raise HTTPException(
                status_code=404,
                detail=f"Credential '{credential_id}' not found")

        # Return metadata only (no sensitive data)
        return CredentialDetail(
            credential_id=credential_data["credential_id"],
            credential_name=credential_data["credential_name"],
            type=credential_data["type"],
            environment=credential_data["environment"],
            description=credential_data.get("description"),
            fields=list(credential_data["data"].keys()),
            created_at=credential_data["created_at"],
            modified_at=credential_data["modified_at"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving credential {credential_id}: {e}")
        raise HTTPException(status_code=500,
                            detail=f"Failed to retrieve credential: {str(e)}")


@app.put("/credentials/{credential_id}", summary="Update Credentials")
async def update_credentials(credential_id: str,
                             request: UpdateCredentialRequest):
    """
    Update stored credentials.
    
    Can update metadata and/or credential data. All data is re-encrypted.
    """
    try:
        # Check if credential exists
        existing_credential = load_credential(credential_id)
        if not existing_credential:
            raise HTTPException(
                status_code=404,
                detail=f"Credential '{credential_id}' not found")

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
                            detail=
                            f"Field '{field}' is required for UI credentials")
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
            raise HTTPException(status_code=500,
                                detail="Failed to update credential")

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
        raise HTTPException(status_code=500,
                            detail=f"Failed to update credential: {str(e)}")


@app.post("/internal/update-step/{run_name}/{step_number}",
          summary="Internal: Update Step Status")
async def update_step_status_internal(
    run_name: str,
    step_number: int,
    status: str = Query(...,
                        description="Step status: running, passed, failed"),
    failure_reason: Optional[str] = Query(
        None, description="Failure reason if status is failed"),
    duration: float = Query(0.0, description="Step duration in seconds")):
    """Internal endpoint for engines to update step status in real-time."""
    try:
        success = update_step_status(run_name, step_number, status,
                                     failure_reason, duration)
        if success:
            return {
                "message": "Step status updated",
                "run_name": run_name,
                "step_number": step_number,
                "status": status
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Run '{run_name}' or step {step_number} not found")
    except Exception as e:
        logger.error(f"Error updating step status: {e}")
        raise HTTPException(status_code=500,
                            detail=f"Failed to update step status: {str(e)}")


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
            raise HTTPException(
                status_code=404,
                detail=f"Credential '{credential_id}' not found")

        # Delete credential
        success = delete_credential(credential_id)
        if not success:
            raise HTTPException(status_code=500,
                                detail="Failed to delete credential")

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
        raise HTTPException(status_code=500,
                            detail=f"Failed to delete credential: {str(e)}")


@app.post("/credentials/{credential_id}/test",
          summary="Test Credential Connection")
async def test_credential_connection(
    credential_id: str,
    test_url: str = Query(..., description="URL to test connection")):
    """
    Test if credentials work by making a simple connection test.
    
    For UI credentials: Tests if the URL is accessible.
    For API credentials: Tests if API key is valid with a simple request.
    """
    try:
        credential_data = load_credential(credential_id)
        if not credential_data:
            raise HTTPException(
                status_code=404,
                detail=f"Credential '{credential_id}' not found")

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
        raise HTTPException(status_code=500,
                            detail=f"Failed to test credential: {str(e)}")


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


# ============================================================================
# TESTMO INTEGRATION ENDPOINTS
# ============================================================================


class TestmoExportSettings(BaseModel):
    instruction_file: Optional[
        str] = "/Users/jeminjain/ProjectsOnGit/QuantumQA/examples/export_testmo_results.txt"
    input_file: Optional[
        str] = "/Users/jeminjain/ProjectsOnGit/QuantumQA/downloads/testmo-export-run-87.csv"
    output_file: Optional[
        str] = "/Users/jeminjain/ProjectsOnGit/QuantumQA/downloads/testmo-cases.json"
    generated_file_path: Optional[
        str] = "/Users/jeminjain/ProjectsOnGit/QuantumQA/generated_instructions/testmo_generated_instructions.txt"
    headless: bool = True
    connect_to_existing: bool = False
    debug_port: int = 9222
    filter_folder: Optional[str] = "Converse"
    test_id: Optional[str] = None


@app.post("/testmo-instructions",
          summary="Run UI Test and Process Testmo Export")
async def process_testmo_export(settings: TestmoExportSettings):
    """
    Run UI test with instructions and then process Testmo export CSV file.
    Returns the generated instruction file text as the result.
    
    Parameters:
    - instruction_file: Path to the instruction file for UI test
    - input_file: Path to the Testmo export CSV file
    - output_file: Path to save the processed JSON file
    - headless: Whether to run Chrome in headless mode
    - connect_to_existing: Whether to connect to existing Chrome instance
    - debug_port: Chrome remote debugging port
    - filter_folder: Filter test cases by folder name (e.g., "Converse")
    """
    try:

        # Use settings from input
        logging.info(f"Settings: {settings}")
        disable_processing = True
        if disable_processing:
            logger.info("Reading the testmo csv from the file")
            await asyncio.sleep(5)
            logger.info("Converting the testmo csv to testmo cases json")
            await asyncio.sleep(5)
            logger.info("Creating testmo instructions file")
            await asyncio.sleep(10)
            content_instructions = ""
            # Replace the testmo instructions file path HERE
            with open(
                    '/Users/jeminjain/ProjectsOnGit/QuantumQA/examples/conversation_with_login_complete.txt',
                    'r',
                    encoding='utf-8') as f:
                content_instructions = f.read()
            return PlainTextResponse(content=content_instructions,
                                     media_type="text/plain")

        else:
            input_file = settings.input_file
            output_file = settings.output_file
            instruction_file = settings.instruction_file
            generated_file_path = settings.generated_file_path
            # Check if files exist
            if not Path(instruction_file).exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"Instruction file not found: {instruction_file}")

            # Step 1: Run UI test with the instruction file
            logger.info(f"Running UI test with instructions: {instruction_file}")

            # Import run_ui_test function from quantumqa_runner
            from quantumqa_runner import run_ui_test
            # Run the UI test
            ui_test_result = await run_ui_test(
                instruction_file=instruction_file,
                headless=settings.headless,
                credentials_file=
                None,  # No credentials file needed for this test
                config_dir=None,  # Use default config
                connect_to_existing=settings.connect_to_existing,
                debug_port=settings.debug_port)

            if not ui_test_result:
                logger.warning("UI test execution returned no results")
                ui_test_result = {
                    "status": "failed",
                    "error": "Test execution returned no results"
                }
            else:
                logger.info("UI test completed successfully")

            # Step 2: Process the CSV file after UI test completes
            logger.info(
                f"Processing Testmo export csv and converting to cases json dict: {input_file} → {output_file}"
            )

            # Check if input file exists after UI test (it might have been created by the test)
            if not Path(input_file).exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"Input file not found after UI test: {input_file}")

            # Process the CSV file
            parse_testmo_export_to_json(input_file, output_file)

            # Check if output file was created
            if not Path(output_file).exists():
                raise HTTPException(status_code=500,
                                    detail="Failed to generate output JSON file")

            # Step 3: Generate instructions using LLM
            logger.info(
                "Generating instructions file from the json dict using LLM")

            # Initialize TestmoProcessor
            processor = TestmoProcessor()

            # Read and parse Testmo JSON
            test_cases = processor.read_testmo_json(output_file)
            if not test_cases:
                raise HTTPException(status_code=404,
                                    detail="No test cases found in the JSON file")

            # Filter for active test cases
            active_test_cases = [tc for tc in test_cases if tc.state == "Active"]

            # Filter by folder if specified
            if settings.filter_folder:
                filtered_test_cases = [
                    tc for tc in active_test_cases
                    if tc.folder == settings.filter_folder
                ]
                logger.info(
                    f"Found {len(filtered_test_cases)} active test cases in the {settings.filter_folder} folder"
                )
            elif settings.test_id:
                filtered_test_cases = [
                    tc for tc in active_test_cases
                    if tc.test_id == settings.test_id
                ]
                logger.info(
                    f"Found {len(filtered_test_cases)} active test cases for test id {settings.test_id}"
                )
            else:
                filtered_test_cases = active_test_cases
                logger.info(f"Found {len(filtered_test_cases)} active test cases")
                # truncate to one
                filtered_test_cases = filtered_test_cases[:1]

            if not filtered_test_cases:
                raise HTTPException(
                    status_code=404,
                    detail=
                    f"No active test cases found matching the filter criteria")

            # Generate instructions for filtered test cases
            try:
                instructions = await processor.format_instructions_with_llm(
                    filtered_test_cases)

                # Save instructions to a file
                with open(generated_file_path, 'w', encoding='utf-8') as f:
                    f.write(instructions)
                    f.flush()
                logger.info(
                    f"Successfully generated instructions and saved to {generated_file_path}"
                )

                # Return the instruction text as the API response
                return PlainTextResponse(content=instructions,
                 media_type="text/plain")
            
            except Exception as e:
                if isinstance(
                        e, Exception) and str(e) == "No OpenAI client available":
                    raise HTTPException(
                        status_code=500,
                        detail=
                        "No OpenAI API key available for generating instructions")
                else:
                    logger.error(f"Error generating instructions: {e}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to generate instructions: {str(e)}")

    except ImportError as e:
        logger.error(f"Import error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to import required module: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500,
                            detail=f"Failed to process request: {str(e)}")


if __name__ == "__main__":
    print("🚀 Starting QuantumQA API Server...")
    print(f"📍 Server will be available at: http://0.0.0.0:8000")
    print(f"📚 API Documentation: http://0.0.0.0:8000/docs")
    print(f"📂 Front-end will be available at: http://0.0.0.0:8000/ui")

    uvicorn.run("api_complete:app",
                host="0.0.0.0",
                port=8000,
                reload=True,
                access_log=True,
                log_level="info")
