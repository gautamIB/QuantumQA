"""
API Testing Engine

Main orchestrator for API testing that coordinates parsing, execution,
validation, and reporting of API tests.
"""

import asyncio
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field

from .api_parser import APIDocumentationParser, APITestSuite, APIEndpoint
from .http_client import HTTPClient
from .response_validator import ResponseValidator, ValidationResult

@dataclass
class APITestResult:
    """Result of a single API test."""
    endpoint_name: str
    method: str
    url: str
    success: bool
    status_code: int
    response_data: Dict[str, Any]
    validation_result: ValidationResult
    request_time: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class APITestSuiteResult:
    """Result of complete API test suite."""
    suite_name: str
    description: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    success_rate: float
    total_time: float
    test_results: List[APITestResult] = field(default_factory=list)
    suite_metadata: Dict[str, Any] = field(default_factory=dict)

class APIEngine:
    """Main API testing engine."""
    
    def __init__(self, credentials_file: Optional[str] = None):
        """
        Initialize API testing engine.
        
        Args:
            credentials_file: Path to credentials.yaml file
        """
        self.credentials_file = credentials_file
        self.parser = APIDocumentationParser()
        self.validator = ResponseValidator()
        self.test_count = 0
        self.suite_count = 0
    
    async def run_test_suite(
        self,
        documentation_file: Union[str, Path],
        base_url_override: Optional[str] = None,
        timeout_override: Optional[int] = None,
        stop_on_failure: bool = False
    ) -> APITestSuiteResult:
        """
        Run complete API test suite from documentation file.
        
        Args:
            documentation_file: Path to API documentation file
            base_url_override: Override base URL from documentation
            timeout_override: Override timeout for all requests
            stop_on_failure: Stop execution on first failure
            
        Returns:
            APITestSuiteResult with complete test results
        """
        self.suite_count += 1
        start_time = time.time()
        
        print(f"🚀 Starting API Test Suite: {documentation_file}")
        print("=" * 80)
        
        try:
            # Parse documentation
            print("📖 Parsing API documentation...")
            test_suite = self.parser.parse_file(documentation_file)
            
            # Validate test suite
            validation_errors = self.parser.validate_suite(test_suite)
            if validation_errors:
                print("❌ Test suite validation errors:")
                for error in validation_errors:
                    print(f"   • {error}")
                return self._create_failed_suite_result(test_suite, validation_errors)
            
            print(f"✅ Parsed {len(test_suite.endpoints)} endpoints")
            
            # Apply overrides
            if base_url_override:
                test_suite.base_url = base_url_override
                print(f"🔧 Base URL override: {base_url_override}")
            
            # Run tests
            test_results = []
            async with HTTPClient(self.credentials_file) as http_client:
                # Resolve credential placeholders in global headers
                test_suite.global_headers = await self._resolve_header_credentials(
                    test_suite.global_headers, http_client
                )
                for i, endpoint in enumerate(test_suite.endpoints, 1):
                    print(f"\n📍 Test {i}/{len(test_suite.endpoints)}: {endpoint.name}")
                    print("-" * 60)
                    
                    # Apply timeout override
                    endpoint_timeout = timeout_override if timeout_override else endpoint.timeout
                    
                    # Run single test
                    test_result = await self._run_single_test(
                        http_client, endpoint, test_suite.base_url, endpoint_timeout, test_suite.global_headers
                    )
                    test_results.append(test_result)
                    
                    # Print result summary
                    status_icon = "✅" if test_result.success else "❌"
                    print(f"{status_icon} {endpoint.method} {endpoint.url} - "
                          f"{test_result.status_code} in {test_result.request_time:.3f}s")
                    
                    if not test_result.success:
                        print(f"   ❌ {test_result.error_message}")
                        if test_result.validation_result.errors:
                            for error in test_result.validation_result.errors:
                                print(f"      • {error}")
                    
                    # Stop on failure if requested
                    if stop_on_failure and not test_result.success:
                        print(f"\n🛑 Stopping execution due to failure (stop_on_failure=True)")
                        break
                
                # Get HTTP client statistics
                http_stats = http_client.get_statistics()
            
            # Calculate suite results
            end_time = time.time()
            total_time = end_time - start_time
            passed_tests = sum(1 for result in test_results if result.success)
            failed_tests = len(test_results) - passed_tests
            success_rate = (passed_tests / len(test_results) * 100) if test_results else 0
            
            # Create suite result
            suite_result = APITestSuiteResult(
                suite_name=test_suite.name,
                description=test_suite.description,
                total_tests=len(test_results),
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                success_rate=success_rate,
                total_time=total_time,
                test_results=test_results,
                suite_metadata={
                    'base_url': test_suite.base_url,
                    'global_headers': test_suite.global_headers,
                    'http_statistics': http_stats,
                    'validation_statistics': self.validator.get_statistics()
                }
            )
            
            # Print final summary
            self._print_suite_summary(suite_result)
            return suite_result
            
        except Exception as e:
            print(f"❌ Critical error running test suite: {e}")
            return self._create_error_suite_result(
                documentation_file, str(e), time.time() - start_time
            )
    
    async def _run_single_test(
        self,
        http_client: HTTPClient,
        endpoint: APIEndpoint,
        base_url: str,
        timeout: int,
        global_headers: Dict[str, str] = None
    ) -> APITestResult:
        """Run a single API endpoint test."""
        self.test_count += 1
        
        # Construct full URL
        if endpoint.url.startswith('http'):
            full_url = endpoint.url
        else:
            full_url = f"{base_url.rstrip('/')}/{endpoint.url.lstrip('/')}"
        
        try:
            # Resolve credentials in endpoint headers too
            endpoint_headers_resolved = endpoint.headers
            if endpoint.headers:
                endpoint_headers_resolved = await self._resolve_header_credentials(
                    endpoint.headers, http_client
                )
            
            # Merge global headers with endpoint-specific headers (endpoint overrides global)
            merged_headers = dict(global_headers) if global_headers else {}
            if endpoint_headers_resolved:
                merged_headers.update(endpoint_headers_resolved)
            
            # Make HTTP request
            status_code, response_data, metadata = await http_client.make_request(
                method=endpoint.method,
                url=full_url,
                headers=merged_headers,
                payload=endpoint.payload,
                auth_credential=endpoint.auth_credential,
                timeout=timeout
            )
            
            # Validate response
            validation_result = self.validator.validate_response(
                actual_status=status_code,
                actual_response=response_data,
                expected_status=endpoint.expected_status,
                expected_response=endpoint.expected_response,
                required_fields=endpoint.required_response_fields,
                optional_fields=endpoint.optional_response_fields,
                field_types=endpoint.field_types
            )
            
            # Determine overall success
            success = validation_result.success and status_code > 0
            error_message = None if success else self._format_error_message(validation_result)
            
            return APITestResult(
                endpoint_name=endpoint.name,
                method=endpoint.method,
                url=full_url,
                success=success,
                status_code=status_code,
                response_data=response_data,
                validation_result=validation_result,
                request_time=metadata.get('request_time', 0),
                error_message=error_message,
                metadata=metadata
            )
            
        except Exception as e:
            return APITestResult(
                endpoint_name=endpoint.name,
                method=endpoint.method,
                url=full_url,
                success=False,
                status_code=0,
                response_data={'error': str(e)},
                validation_result=ValidationResult(False, [str(e)], [], {}),
                request_time=0,
                error_message=f"Test execution error: {str(e)}",
                metadata={}
            )
    
    def _format_error_message(self, validation_result: ValidationResult) -> str:
        """Format validation errors into a readable error message."""
        if not validation_result.errors:
            return "Unknown validation error"
        
        if len(validation_result.errors) == 1:
            return validation_result.errors[0]
        else:
            return f"Multiple errors: {'; '.join(validation_result.errors[:3])}"
    
    def _create_failed_suite_result(
        self,
        test_suite: APITestSuite,
        validation_errors: List[str]
    ) -> APITestSuiteResult:
        """Create a failed suite result for validation errors."""
        return APITestSuiteResult(
            suite_name=test_suite.name,
            description=test_suite.description,
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            success_rate=0,
            total_time=0,
            test_results=[],
            suite_metadata={'validation_errors': validation_errors}
        )
    
    def _create_error_suite_result(
        self,
        documentation_file: Union[str, Path],
        error_message: str,
        total_time: float
    ) -> APITestSuiteResult:
        """Create an error suite result for critical failures."""
        return APITestSuiteResult(
            suite_name=f"Failed Suite: {Path(documentation_file).name}",
            description="Suite failed to execute due to critical error",
            total_tests=0,
            passed_tests=0,
            failed_tests=1,
            success_rate=0,
            total_time=total_time,
            test_results=[],
            suite_metadata={'critical_error': error_message}
        )
    
    def _print_suite_summary(self, suite_result: APITestSuiteResult):
        """Print formatted test suite summary."""
        print("\n" + "=" * 80)
        print("📊 API TEST SUITE SUMMARY")
        print("=" * 80)
        print(f"Suite: {suite_result.suite_name}")
        print(f"Description: {suite_result.description}")
        print(f"Total Tests: {suite_result.total_tests}")
        print(f"✅ Passed: {suite_result.passed_tests}")
        print(f"❌ Failed: {suite_result.failed_tests}")
        print(f"📈 Success Rate: {suite_result.success_rate:.1f}%")
        print(f"⏱️  Total Time: {suite_result.total_time:.3f}s")
        
        if suite_result.test_results:
            avg_time = sum(r.request_time for r in suite_result.test_results) / len(suite_result.test_results)
            print(f"⚡ Average Response Time: {avg_time:.3f}s")
        
        # Show failed tests details
        failed_tests = [r for r in suite_result.test_results if not r.success]
        if failed_tests:
            print(f"\n❌ Failed Tests ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"   • {test.endpoint_name}: {test.error_message}")
        
        # Show HTTP statistics
        http_stats = suite_result.suite_metadata.get('http_statistics', {})
        if http_stats:
            print(f"\n🌐 HTTP Statistics:")
            print(f"   • Total Requests: {http_stats.get('total_requests', 0)}")
            print(f"   • Total Time: {http_stats.get('total_time', 0):.3f}s")
            print(f"   • Requests/sec: {http_stats.get('requests_per_second', 0):.2f}")
        
        print("=" * 80)
    
    async def _resolve_header_credentials(
        self, 
        headers: Dict[str, str], 
        http_client: HTTPClient
    ) -> Dict[str, str]:
        """Resolve credential placeholders in headers."""
        import re
        
        resolved_headers = {}
        
        for key, value in headers.items():
            # Look for {cred:path} pattern in header values
            cred_pattern = r'\{cred:([^}]+)\}'
            matches = re.findall(cred_pattern, value)
            
            resolved_value = value
            for cred_ref in matches:
                try:
                    if http_client.credential_manager:
                        # Use the credential manager's existing dot-notation support
                        cred_value = http_client.credential_manager.get_credential(cred_ref)
                        
                        if cred_value is not None:
                            # Replace the {cred:path} placeholder with actual value
                            placeholder = f"{{cred:{cred_ref}}}"
                            resolved_value = resolved_value.replace(placeholder, str(cred_value))
                            print(f"🔐 Resolved credential in header '{key}': {placeholder} → [CREDENTIAL:{len(str(cred_value))} chars]")
                        else:
                            print(f"⚠️ Warning: Credential '{cred_ref}' not found")
                    else:
                        print(f"⚠️ Warning: No credential manager available for '{cred_ref}'")
                        
                except Exception as e:
                    print(f"❌ Error resolving credential '{cred_ref}': {e}")
            
            resolved_headers[key] = resolved_value
        
        return resolved_headers
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            'total_test_suites': self.suite_count,
            'total_individual_tests': self.test_count,
            'validator_statistics': self.validator.get_statistics()
        }
