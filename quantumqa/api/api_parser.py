"""
API Documentation Parser

Parses API documentation files (YAML/JSON) and extracts test specifications.
Supports multiple API signatures in a single file.
"""

import yaml
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field

@dataclass
class APIEndpoint:
    """Represents a single API endpoint test specification."""
    name: str
    description: str
    method: str  # GET, POST, PUT, DELETE, etc.
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    payload: Optional[Dict[str, Any]] = None
    expected_status: Union[int, List[int]] = 200
    expected_response: Optional[Dict[str, Any]] = None
    auth_credential: Optional[str] = None  # Reference to credentials.yaml
    timeout: int = 30
    
    # Advanced validation (for future phases)
    required_response_fields: List[str] = field(default_factory=list)
    optional_response_fields: List[str] = field(default_factory=list)
    field_types: Dict[str, str] = field(default_factory=dict)

@dataclass
class APITestSuite:
    """Represents a complete API test suite from documentation."""
    name: str
    description: str
    base_url: str
    global_headers: Dict[str, str] = field(default_factory=dict)
    global_auth: Optional[str] = None
    endpoints: List[APIEndpoint] = field(default_factory=list)

class APIDocumentationParser:
    """Parser for API documentation files."""
    
    def __init__(self):
        self.supported_formats = ['.yaml', '.yml', '.json']
    
    def parse_file(self, file_path: Union[str, Path]) -> APITestSuite:
        """
        Parse API documentation file and return test suite.
        
        Args:
            file_path: Path to API documentation file
            
        Returns:
            APITestSuite object containing all test specifications
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"API documentation file not found: {file_path}")
        
        if file_path.suffix not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {file_path.suffix}. "
                           f"Supported formats: {self.supported_formats}")
        
        # Load file content
        with open(file_path, 'r', encoding='utf-8') as f:
            if file_path.suffix == '.json':
                data = json.load(f)
            else:  # YAML
                data = yaml.safe_load(f)
        
        return self._parse_data(data, file_path.name)
    
    def _parse_data(self, data: Dict[str, Any], filename: str) -> APITestSuite:
        """Parse loaded data into APITestSuite."""
        
        # Extract suite-level information
        suite_name = data.get('name', f"API Test Suite - {filename}")
        suite_description = data.get('description', f"API tests from {filename}")
        base_url = data.get('base_url', '')
        global_headers = data.get('global_headers', {})
        global_auth = data.get('global_auth')
        
        # Parse endpoints (support both 'endpoints' and 'tests' arrays)
        endpoints = []
        endpoints_data = data.get('endpoints', data.get('tests', []))
        
        for i, endpoint_data in enumerate(endpoints_data):
            try:
                endpoint = self._parse_endpoint(endpoint_data, global_headers, global_auth)
                endpoints.append(endpoint)
            except Exception as e:
                print(f"⚠️ Warning: Failed to parse endpoint {i+1}: {e}")
                continue
        
        return APITestSuite(
            name=suite_name,
            description=suite_description,
            base_url=base_url,
            global_headers=global_headers,
            global_auth=global_auth,
            endpoints=endpoints
        )
    
    def _parse_endpoint(self, data: Dict[str, Any], 
                       global_headers: Dict[str, str],
                       global_auth: Optional[str]) -> APIEndpoint:
        """Parse individual endpoint specification."""
        
        # Required fields
        name = data.get('name', 'Unnamed Endpoint')
        method = data.get('method', 'GET').upper()
        # Support both 'url' (advanced format) and 'endpoint' (simple format)
        url = data.get('url', data.get('endpoint', ''))
        
        if not url:
            raise ValueError("Endpoint URL is required")
        
        # Optional fields with defaults
        description = data.get('description', f"{method} {url}")
        # Support both 'payload' (advanced format) and 'body' (simple format)
        payload = data.get('payload', data.get('body'))
        expected_status = data.get('expected_status', 200)
        expected_response = data.get('expected_response')
        timeout = data.get('timeout', 30)
        auth_credential = data.get('auth_credential', global_auth)
        
        # Merge headers (endpoint-specific overrides global)
        headers = dict(global_headers)
        endpoint_headers = data.get('headers', {})
        headers.update(endpoint_headers)
        
        # Advanced validation fields (for future phases)
        required_fields = data.get('required_response_fields', [])
        optional_fields = data.get('optional_response_fields', [])
        field_types = data.get('field_types', {})
        
        return APIEndpoint(
            name=name,
            description=description,
            method=method,
            url=url,
            headers=headers,
            payload=payload,
            expected_status=expected_status,
            expected_response=expected_response,
            auth_credential=auth_credential,
            timeout=timeout,
            required_response_fields=required_fields,
            optional_response_fields=optional_fields,
            field_types=field_types
        )
    
    def validate_suite(self, suite: APITestSuite) -> List[str]:
        """
        Validate API test suite and return list of validation errors.
        
        Args:
            suite: APITestSuite to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not suite.endpoints:
            errors.append("No endpoints defined in test suite")
        
        for i, endpoint in enumerate(suite.endpoints):
            endpoint_errors = self._validate_endpoint(endpoint, i + 1)
            errors.extend(endpoint_errors)
        
        return errors
    
    def _validate_endpoint(self, endpoint: APIEndpoint, index: int) -> List[str]:
        """Validate individual endpoint specification."""
        errors = []
        prefix = f"Endpoint {index} ({endpoint.name})"
        
        # Validate method
        valid_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
        if endpoint.method not in valid_methods:
            errors.append(f"{prefix}: Invalid HTTP method '{endpoint.method}'. "
                         f"Valid methods: {valid_methods}")
        
        # Validate URL
        if not endpoint.url:
            errors.append(f"{prefix}: URL is required")
        
        # Validate expected status
        if isinstance(endpoint.expected_status, int):
            if not (100 <= endpoint.expected_status < 600):
                errors.append(f"{prefix}: Invalid status code {endpoint.expected_status}")
        elif isinstance(endpoint.expected_status, list):
            for status in endpoint.expected_status:
                if not isinstance(status, int) or not (100 <= status < 600):
                    errors.append(f"{prefix}: Invalid status code {status} in list")
        else:
            errors.append(f"{prefix}: expected_status must be int or list of ints")
        
        # Validate timeout
        if endpoint.timeout <= 0:
            errors.append(f"{prefix}: Timeout must be positive")
        
        return errors
