# QuantumQA API Documentation

## Overview

The QuantumQA API provides a comprehensive REST interface for managing AI-powered UI and API test configurations and execution. This API enables seamless integration with frontend applications for test automation workflows.

## Base Information

- **Base URL**: `http://localhost:8000`
- **API Version**: `1.0.0`
- **Content-Type**: `application/json` (unless specified otherwise)
- **Interactive Documentation**: 
  - Swagger UI: `http://localhost:8000/docs`
  - ReDoc: `http://localhost:8000/redoc`

## Authentication

Currently, no authentication is required. For production deployment, consider implementing API key or OAuth authentication.

---

# Endpoints

## Health & Status

### GET `/`
**Health Check**

Returns basic API information and available endpoints.

**Response:**
```json
{
  "message": "QuantumQA API Server is running",
  "version": "1.0.0",
  "timestamp": "2025-09-16T17:34:57.213853",
  "endpoints": {
    "docs": "/docs",
    "redoc": "/redoc",
    "test_configurations": "/test-configurations",
    "runs": "/runs",
    "credentials": "/credentials",
    "status": "/status"
  }
}
```

### GET `/status`
**API Status and Statistics**

Returns current API health and usage statistics.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-16T17:37:45.968713",
  "statistics": {
    "test_configurations": {
      "ui_tests": 1,
      "api_tests": 1,
      "total_tests": 2
    },
    "runs": {
      "completed_runs": 5,
      "running_tests": 1,
      "total_runs": 6
    }
  },
  "currently_running": ["my_test_run_1"]
}
```

---

## Test Configuration Management

### POST `/test-configurations`
**Create Test Configuration**

Creates a new test configuration with validation. Supports both form data and file upload.

**Content-Type**: `multipart/form-data`

**Parameters:**
- `test_name` (string, required): Unique name for the test
- `test_type` (string, required): "UI" or "API"
- `instruction` (string, optional): Test instructions for UI tests
- `apis_documentation` (string, optional): YAML content for API tests
- `file` (file, optional): Upload test file instead of using form fields

**Example - UI Test:**
```bash
curl -X POST "http://localhost:8000/test-configurations" \
  -F "test_name=login_flow_test" \
  -F "test_type=UI" \
  -F "instruction=Navigate to https://app.example.com
Click on login button
Type 'testuser' in username field
Type 'testpass' in password field
Click submit button
Verify dashboard page loads"
```

**Example - API Test:**
```bash
curl -X POST "http://localhost:8000/test-configurations" \
  -F "test_name=user_api_test" \
  -F "test_type=API" \
  -F "apis_documentation=name: User API Test
base_url: https://api.example.com
tests:
  - name: Get Users
    method: GET
    endpoint: /users
    expected_status: 200
  - name: Create User
    method: POST
    endpoint: /users
    headers:
      Content-Type: application/json
    body:
      name: Test User
      email: test@example.com
    expected_status: 201"
```

**Response (201 Created):**
```json
{
  "message": "Test configuration created successfully",
  "test_name": "login_flow_test",
  "test_type": "UI",
  "file_path": "Test/UI/login_flow_test.txt",
  "validation": {
    "status": "valid",
    "warnings": [],
    "errors": [],
    "last_validated": "2025-09-16T17:34:57.210440"
  },
  "created_at": "2025-09-16T17:34:57.213853"
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": "Test validation failed",
  "validation": {
    "status": "invalid",
    "errors": ["Missing required field: 'name'"],
    "warnings": [],
    "last_validated": "2025-09-16T17:34:57.210440"
  }
}
```

### GET `/test-configurations`
**List Test Configurations**

Returns a paginated list of all test configurations.

**Query Parameters:**
- `test_type` (string, optional): Filter by "UI" or "API"
- `limit` (integer, optional, default=50): Maximum results per page
- `offset` (integer, optional, default=0): Number of results to skip

**Example:**
```bash
curl "http://localhost:8000/test-configurations?test_type=UI&limit=10&offset=0"
```

**Response:**
```json
[
  {
    "test_name": "login_flow_test",
    "test_type": "UI",
    "file_path": "Test/UI/login_flow_test.txt",
    "created_at": "2025-09-16T17:34:57.210937",
    "modified_at": "2025-09-16T17:34:57.210937",
    "size_bytes": 120,
    "status": "valid"
  },
  {
    "test_name": "user_api_test",
    "test_type": "API",
    "file_path": "Test/API/user_api_test.yml",
    "created_at": "2025-09-16T17:37:39.244663",
    "modified_at": "2025-09-16T17:37:39.244663",
    "size_bytes": 350,
    "status": "valid"
  }
]
```

### GET `/test-configurations/{test_name}`
**Get Test Configuration Details**

Returns detailed information and content for a specific test configuration.

**Query Parameters:**
- `test_type` (string, optional): "UI" or "API" (helps locate the test faster)

**Example:**
```bash
curl "http://localhost:8000/test-configurations/login_flow_test?test_type=UI"
```

**Response:**
```json
{
  "test_name": "login_flow_test",
  "test_type": "UI",
  "file_path": "Test/UI/login_flow_test.txt",
  "content": "Navigate to https://app.example.com\nClick on login button\nType 'testuser' in username field\nType 'testpass' in password field\nClick submit button\nVerify dashboard page loads",
  "created_at": "2025-09-16T17:34:57.210937",
  "modified_at": "2025-09-16T17:34:57.210937",
  "size_bytes": 120,
  "validation": {
    "status": "valid",
    "warnings": [],
    "errors": [],
    "last_validated": "2025-09-16T17:37:28.987701"
  }
}
```

### PUT `/test-configurations/{test_name}`
**Update Test Configuration**

Updates an existing test configuration with validation.

**Query Parameters:**
- `test_type` (string, optional): "UI" or "API"

**Request Body:**
```json
{
  "instruction": "Updated test instructions for UI tests",
  "apis_documentation": "Updated YAML for API tests"
}
```

**Response:**
```json
{
  "message": "Test configuration updated successfully",
  "test_name": "login_flow_test",
  "test_type": "UI",
  "validation": {
    "status": "valid",
    "warnings": [],
    "errors": []
  },
  "updated_at": "2025-09-16T17:45:30.123456"
}
```

### DELETE `/test-configurations/{test_name}`
**Delete Test Configuration**

Permanently deletes a test configuration.

**Query Parameters:**
- `test_type` (string, optional): "UI" or "API"

**Response:**
```json
{
  "message": "Test configuration deleted successfully",
  "test_name": "login_flow_test",
  "test_type": "UI",
  "deleted_at": "2025-09-16T17:45:30.123456"
}
```

### POST `/test-configurations/{test_name}/validate`
**Validate Test Configuration**

Validates a test configuration without making changes.

**Response:**
```json
{
  "status": "valid",
  "warnings": [
    "Line 5: Consider adding explicit wait time for better reliability"
  ],
  "errors": [],
  "last_validated": "2025-09-16T17:45:30.123456"
}
```

---

## Test Execution Management

### POST `/runs`
**Execute Test Run**

Starts test execution in the background and returns immediately.

**Request Body:**
```json
{
  "env": "https://app.example.com",
  "credentials": {
    "username": "testuser",
    "password": "testpass",
    "api_key": "optional_api_key"
  },
  "credential_id": "optional_stored_credential_id",
  "test_file_path": "Test/UI/login_flow_test.txt",
  "test_type": "UI",
  "run_name": "login_test_run_1",
  "options": {
    "headless": false,
    "timeout": 300,
    "retry_count": 1
  }
}
```

**Response (202 Accepted):**
```json
{
  "message": "Test execution started",
  "run_name": "login_test_run_1",
  "status": "RUNNING",
  "log_file_url": "/runs/login_test_run_1/logs",
  "report_file_url": "/runs/login_test_run_1/report",
  "started_at": "2025-09-16T17:45:30.123456"
}
```

### GET `/runs`
**List Test Runs**

Returns a paginated list of test runs with filtering options.

**Query Parameters:**
- `status` (string, optional): Filter by "RUNNING", "COMPLETED", "FAILED", "CANCELLED"
- `test_type` (string, optional): Filter by "UI" or "API"
- `limit` (integer, optional, default=50): Maximum results per page
- `offset` (integer, optional, default=0): Number of results to skip

**Example:**
```bash
curl "http://localhost:8000/runs?status=COMPLETED&test_type=UI&limit=10"
```

**Response:**
```json
{
  "runs": [
    {
      "run_name": "login_test_run_1",
      "test_file": "Test/UI/login_flow_test.txt",
      "test_type": "UI",
      "status": "COMPLETED",
      "started_at": "2025-09-16T17:45:30.123456",
      "completed_at": "2025-09-16T17:47:15.654321",
      "duration_seconds": 105.53,
      "success_rate": 85.7,
      "log_file_url": "/runs/login_test_run_1/logs",
      "report_file_url": "/runs/login_test_run_1/report"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

### GET `/runs/{run_name}`
**Get Test Run Details**

Returns detailed information about a specific test run.

**Response:**
```json
{
  "run_name": "login_test_run_1",
  "test_file": "Test/UI/login_flow_test.txt",
  "test_type": "UI",
  "environment": "https://app.example.com",
  "status": "COMPLETED",
  "started_at": "2025-09-16T17:45:30.123456",
  "completed_at": "2025-09-16T17:47:15.654321",
  "duration_seconds": 105.53,
  "success_rate": 85.7,
  "steps_total": 7,
  "steps_passed": 6,
  "steps_failed": 1,
  "error_summary": "Step 4 failed: Element not found",
  "log_file_url": "/runs/login_test_run_1/logs",
  "report_file_url": "/runs/login_test_run_1/report"
}
```

### GET `/runs/{run_name}/logs`
**Download Test Run Logs**

Downloads the raw log file for a test run.

**Response**: File download with `Content-Type: text/plain`

### GET `/runs/{run_name}/report`
**Download Test Run Report**

Downloads the detailed JSON report for a test run.

**Response**: File download with `Content-Type: application/json`

### DELETE `/runs/{run_name}`
**Cancel Test Run**

Cancels a currently running test.

**Response:**
```json
{
  "message": "Test run cancelled successfully",
  "run_name": "login_test_run_1",
  "status": "CANCELLED",
  "cancelled_at": "2025-09-16T17:46:00.123456"
}
```

---

## Credentials Management

### POST `/credentials`
**Create Encrypted Credentials**

Stores credentials securely using Fernet encryption. All sensitive data is encrypted before storage.

**Request Body:**
```json
{
  "credential_name": "my_staging_creds",
  "type": "UI",
  "environment": "staging",
  "description": "UI credentials for staging environment",
  "data": {
    "username": "testuser",
    "password": "securepass123"
  }
}
```

**Response (201 Created):**
```json
{
  "message": "Credentials created successfully",
  "credential_id": "18b7a7d8-3082-48b1-aef2-e45526d3c72a",
  "credential_name": "my_staging_creds",
  "type": "UI",
  "environment": "staging",
  "fields": ["username", "password"],
  "created_at": "2025-09-17T10:02:10.980617"
}
```

### GET `/credentials`
**List Stored Credentials**

Returns metadata about stored credentials without exposing sensitive values.

**Query Parameters:**
- `type` (string, optional): Filter by "UI" or "API"
- `environment` (string, optional): Filter by environment
- `limit` (integer, optional, default=50): Maximum results per page
- `offset` (integer, optional, default=0): Number of results to skip

**Response:**
```json
[
  {
    "credential_id": "18b7a7d8-3082-48b1-aef2-e45526d3c72a",
    "credential_name": "my_staging_creds",
    "type": "UI",
    "environment": "staging",
    "description": "UI credentials for staging environment",
    "fields": ["username", "password"],
    "created_at": "2025-09-17T10:02:10.979811",
    "modified_at": "2025-09-17T10:02:10.979826"
  }
]
```

### GET `/credentials/{credential_id}`
**Get Credential Details**

Returns detailed metadata about a specific credential (never exposes actual values).

**Response:**
```json
{
  "credential_id": "18b7a7d8-3082-48b1-aef2-e45526d3c72a",
  "credential_name": "my_staging_creds",
  "type": "UI",
  "environment": "staging",
  "description": "UI credentials for staging environment",
  "fields": ["username", "password"],
  "created_at": "2025-09-17T10:02:10.979811",
  "modified_at": "2025-09-17T10:02:10.979826"
}
```

### PUT `/credentials/{credential_id}`
**Update Credentials**

Updates stored credentials. All data is re-encrypted.

**Request Body:**
```json
{
  "credential_name": "updated_staging_creds",
  "description": "Updated UI credentials for staging",
  "data": {
    "username": "newuser",
    "password": "newpassword123"
  }
}
```

### DELETE `/credentials/{credential_id}`
**Delete Credentials**

Permanently deletes stored credentials.

**Response:**
```json
{
  "message": "Credentials deleted successfully",
  "credential_id": "18b7a7d8-3082-48b1-aef2-e45526d3c72a",
  "deleted_at": "2025-09-17T10:02:46.123456"
}
```

### POST `/credentials/{credential_id}/test`
**Test Credential Connection**

Tests if credentials work by making a connection test.

**Query Parameters:**
- `test_url` (string, required): URL to test connection against

**Response:**
```json
{
  "credential_id": "18b7a7d8-3082-48b1-aef2-e45526d3c72a",
  "test_url": "https://example.com",
  "success": true,
  "status_message": "URL accessible, status: 200",
  "tested_at": "2025-09-17T10:02:27.319952"
}
```

### Using Stored Credentials in Test Execution

You can use stored credentials in test runs by providing the `credential_id` instead of inline credentials:

**Example:**
```json
{
  "env": "https://app.example.com",
  "credential_id": "18b7a7d8-3082-48b1-aef2-e45526d3c72a",
  "test_file_path": "Test/UI/login_flow_test.txt",
  "test_type": "UI",
  "run_name": "secure_test_run"
}
```

---

## Data Models

### TestConfigInfo
```json
{
  "test_name": "string",
  "test_type": "UI|API",
  "file_path": "string",
  "created_at": "ISO8601 datetime",
  "modified_at": "ISO8601 datetime",
  "size_bytes": "integer",
  "status": "valid|invalid|warning"
}
```

### ValidationResult
```json
{
  "status": "valid|invalid|warning",
  "warnings": ["string"],
  "errors": ["string"],
  "last_validated": "ISO8601 datetime"
}
```

### Credentials
```json
{
  "username": "string (optional)",
  "password": "string (optional)",
  "api_key": "string (optional)"
}
```

### RunOptions
```json
{
  "headless": "boolean (default: false)",
  "timeout": "integer (default: 300)",
  "retry_count": "integer (default: 1)"
}
```

### CredentialInfo
```json
{
  "credential_id": "string (UUID)",
  "credential_name": "string",
  "type": "UI|API",
  "environment": "string",
  "description": "string (optional)",
  "fields": ["array of field names"],
  "created_at": "ISO8601 datetime",
  "modified_at": "ISO8601 datetime"
}
```

### CredentialRequest
```json
{
  "credential_name": "string",
  "type": "UI|API",
  "environment": "string",
  "description": "string (optional)",
  "data": {
    "username": "string (for UI)",
    "password": "string (for UI)",
    "api_key": "string (for API)"
  }
}
```

---

## Error Handling

### HTTP Status Codes

- **200 OK**: Successful GET request
- **201 Created**: Successful POST request (resource created)
- **202 Accepted**: Request accepted for processing
- **400 Bad Request**: Invalid request data or validation failed
- **404 Not Found**: Resource not found
- **409 Conflict**: Resource already exists or conflicting state
- **500 Internal Server Error**: Unexpected server error

### Error Response Format

```json
{
  "detail": "Error description",
  "error": "Additional error context (optional)",
  "validation": "ValidationResult object (if applicable)"
}
```

---

## UI Integration Examples

### React/JavaScript Integration

```javascript
// Create a test configuration
const createTest = async (testData) => {
  const formData = new FormData();
  formData.append('test_name', testData.name);
  formData.append('test_type', testData.type);
  formData.append('instruction', testData.content);
  
  const response = await fetch('/api/test-configurations', {
    method: 'POST',
    body: formData
  });
  
  return response.json();
};

// Execute a test
const runTest = async (runData) => {
  const response = await fetch('/api/runs', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(runData)
  });
  
  return response.json();
};

// Poll for test status
const pollTestStatus = async (runName) => {
  const response = await fetch(`/api/runs/${runName}`);
  return response.json();
};
```

### File Upload Example

```javascript
const uploadTestFile = async (file, testName, testType) => {
  const formData = new FormData();
  formData.append('test_name', testName);
  formData.append('test_type', testType);
  formData.append('file', file);
  
  const response = await fetch('/api/test-configurations', {
    method: 'POST',
    body: formData
  });
  
  return response.json();
};
```

---

## Best Practices

1. **Test Names**: Use descriptive, unique names (e.g., `login_flow_happy_path`, `api_user_crud_operations`)

2. **Validation**: Always check the validation status before executing tests

3. **Error Handling**: Implement proper error handling for all API calls

4. **Polling**: For long-running tests, implement polling with exponential backoff

5. **File Management**: Monitor test file sizes and clean up old runs periodically

6. **Credentials**: Never log or expose credentials in client-side code

---

## Support

For issues or questions:
- Check the interactive documentation at `/docs`
- Review validation errors in API responses
- Monitor server logs for debugging information

**API Version**: 1.0.0  
**Last Updated**: September 16, 2025
