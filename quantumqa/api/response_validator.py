"""
Response Validator for API Testing

Validates API responses against expected criteria including:
- Status codes
- Response structure
- Field types and values
- Required/optional fields
"""

import json
from typing import Dict, Any, List, Union, Optional, Tuple
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Result of response validation."""
    success: bool
    errors: List[str]
    warnings: List[str]
    details: Dict[str, Any]

class ResponseValidator:
    """Validates API responses against expected criteria."""
    
    def __init__(self):
        """Initialize response validator."""
        self.validation_count = 0
        self.success_count = 0
    
    def validate_response(
        self,
        actual_status: int,
        actual_response: Dict[str, Any],
        expected_status: Union[int, List[int]],
        expected_response: Optional[Dict[str, Any]] = None,
        required_fields: Optional[List[str]] = None,
        optional_fields: Optional[List[str]] = None,
        field_types: Optional[Dict[str, str]] = None
    ) -> ValidationResult:
        """
        Validate API response against expected criteria.
        
        Args:
            actual_status: Actual HTTP status code
            actual_response: Actual response data
            expected_status: Expected status code(s)
            expected_response: Expected response structure/data
            required_fields: List of required fields in response
            optional_fields: List of optional fields in response  
            field_types: Expected types for fields
            
        Returns:
            ValidationResult with success status and details
        """
        self.validation_count += 1
        
        errors = []
        warnings = []
        details = {
            'status_validation': {},
            'response_validation': {},
            'field_validation': {},
            'type_validation': {}
        }
        
        # Validate status code
        status_valid = self._validate_status_code(
            actual_status, expected_status, errors, details['status_validation']
        )
        
        # Validate response structure/content
        response_valid = True
        if expected_response is not None:
            response_valid = self._validate_response_content(
                actual_response, expected_response, errors, warnings, details['response_validation']
            )
        
        # Validate required fields
        fields_valid = True
        if required_fields or optional_fields:
            fields_valid = self._validate_fields(
                actual_response, required_fields or [], optional_fields or [],
                errors, warnings, details['field_validation']
            )
        
        # Validate field types
        types_valid = True
        if field_types:
            types_valid = self._validate_field_types(
                actual_response, field_types, errors, warnings, details['type_validation']
            )
        
        # Overall success
        success = status_valid and response_valid and fields_valid and types_valid
        if success:
            self.success_count += 1
        
        return ValidationResult(
            success=success,
            errors=errors,
            warnings=warnings,
            details=details
        )
    
    def _validate_status_code(
        self,
        actual_status: int,
        expected_status: Union[int, List[int]],
        errors: List[str],
        details: Dict[str, Any]
    ) -> bool:
        """Validate HTTP status code."""
        details['actual_status'] = actual_status
        details['expected_status'] = expected_status
        
        if isinstance(expected_status, int):
            expected_codes = [expected_status]
        else:
            expected_codes = expected_status
        
        details['expected_codes'] = expected_codes
        
        if actual_status in expected_codes:
            details['status_match'] = True
            return True
        else:
            details['status_match'] = False
            errors.append(
                f"Status code mismatch: expected {expected_codes}, got {actual_status}"
            )
            return False
    
    def _validate_response_content(
        self,
        actual_response: Dict[str, Any],
        expected_response: Dict[str, Any],
        errors: List[str],
        warnings: List[str],
        details: Dict[str, Any]
    ) -> bool:
        """Validate response content structure and values."""
        details['validation_type'] = 'content_match'
        
        try:
            # Deep comparison of response structure
            comparison_result = self._deep_compare(actual_response, expected_response)
            details.update(comparison_result)
            
            if comparison_result['matches']:
                return True
            else:
                errors.extend(comparison_result['errors'])
                warnings.extend(comparison_result['warnings'])
                return False
                
        except Exception as e:
            errors.append(f"Response validation error: {str(e)}")
            details['validation_error'] = str(e)
            return False
    
    def _validate_fields(
        self,
        response: Dict[str, Any],
        required_fields: List[str],
        optional_fields: List[str],
        errors: List[str],
        warnings: List[str],
        details: Dict[str, Any]
    ) -> bool:
        """Validate required and optional fields in response."""
        details['required_fields'] = required_fields
        details['optional_fields'] = optional_fields
        details['present_fields'] = []
        details['missing_required'] = []
        details['unexpected_fields'] = []
        
        all_expected_fields = set(required_fields + optional_fields)
        actual_fields = set(self._get_all_field_paths(response))
        
        details['present_fields'] = list(actual_fields)
        
        # Check required fields
        success = True
        for field in required_fields:
            if not self._field_exists(response, field):
                details['missing_required'].append(field)
                errors.append(f"Required field missing: {field}")
                success = False
        
        # Check for unexpected fields (only if we have specific field lists)
        if all_expected_fields:
            for field in actual_fields:
                if field not in all_expected_fields:
                    details['unexpected_fields'].append(field)
                    warnings.append(f"Unexpected field found: {field}")
        
        return success
    
    def _validate_field_types(
        self,
        response: Dict[str, Any],
        field_types: Dict[str, str],
        errors: List[str],
        warnings: List[str],
        details: Dict[str, Any]
    ) -> bool:
        """Validate field types in response."""
        details['expected_types'] = field_types
        details['actual_types'] = {}
        details['type_mismatches'] = []
        
        success = True
        
        for field_path, expected_type in field_types.items():
            try:
                value = self._get_field_value(response, field_path)
                if value is not None:
                    actual_type = type(value).__name__
                    details['actual_types'][field_path] = actual_type
                    
                    if not self._type_matches(value, expected_type):
                        details['type_mismatches'].append({
                            'field': field_path,
                            'expected': expected_type,
                            'actual': actual_type
                        })
                        errors.append(
                            f"Type mismatch for field '{field_path}': "
                            f"expected {expected_type}, got {actual_type}"
                        )
                        success = False
                else:
                    warnings.append(f"Field '{field_path}' not found for type validation")
                    
            except Exception as e:
                warnings.append(f"Error validating type for field '{field_path}': {str(e)}")
        
        return success
    
    def _deep_compare(self, actual: Any, expected: Any, path: str = "") -> Dict[str, Any]:
        """Deep comparison of response structures."""
        result = {
            'matches': True,
            'errors': [],
            'warnings': [],
            'comparisons': []
        }
        
        comparison = {
            'path': path or 'root',
            'expected': expected,
            'actual': actual,
            'match': True
        }
        
        if type(actual) != type(expected):
            comparison['match'] = False
            result['matches'] = False
            result['errors'].append(
                f"Type mismatch at {path or 'root'}: "
                f"expected {type(expected).__name__}, got {type(actual).__name__}"
            )
        elif isinstance(expected, dict):
            for key, expected_value in expected.items():
                current_path = f"{path}.{key}" if path else key
                if key not in actual:
                    comparison['match'] = False
                    result['matches'] = False
                    result['errors'].append(f"Missing key at {current_path}")
                else:
                    sub_result = self._deep_compare(actual[key], expected_value, current_path)
                    result['comparisons'].extend(sub_result['comparisons'])
                    if not sub_result['matches']:
                        comparison['match'] = False
                        result['matches'] = False
                        result['errors'].extend(sub_result['errors'])
                        result['warnings'].extend(sub_result['warnings'])
        elif isinstance(expected, list):
            if len(actual) != len(expected):
                comparison['match'] = False
                result['matches'] = False
                result['errors'].append(
                    f"Array length mismatch at {path or 'root'}: "
                    f"expected {len(expected)}, got {len(actual)}"
                )
            else:
                for i, (actual_item, expected_item) in enumerate(zip(actual, expected)):
                    current_path = f"{path}[{i}]" if path else f"[{i}]"
                    sub_result = self._deep_compare(actual_item, expected_item, current_path)
                    result['comparisons'].extend(sub_result['comparisons'])
                    if not sub_result['matches']:
                        comparison['match'] = False
                        result['matches'] = False
                        result['errors'].extend(sub_result['errors'])
                        result['warnings'].extend(sub_result['warnings'])
        else:
            if actual != expected:
                comparison['match'] = False
                result['matches'] = False
                result['errors'].append(
                    f"Value mismatch at {path or 'root'}: "
                    f"expected {expected}, got {actual}"
                )
        
        result['comparisons'].append(comparison)
        return result
    
    def _get_all_field_paths(self, data: Any, prefix: str = "") -> List[str]:
        """Get all field paths in a nested structure."""
        paths = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{prefix}.{key}" if prefix else key
                paths.append(current_path)
                if isinstance(value, (dict, list)):
                    paths.extend(self._get_all_field_paths(value, current_path))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{prefix}[{i}]"
                paths.append(current_path)
                if isinstance(item, (dict, list)):
                    paths.extend(self._get_all_field_paths(item, current_path))
        
        return paths
    
    def _field_exists(self, data: Dict[str, Any], field_path: str) -> bool:
        """Check if a field exists in nested structure."""
        try:
            self._get_field_value(data, field_path)
            return True
        except (KeyError, IndexError, TypeError):
            return False
    
    def _get_field_value(self, data: Any, field_path: str) -> Any:
        """Get value from nested structure using field path."""
        if not field_path:
            return data
        
        current = data
        parts = field_path.split('.')
        
        for part in parts:
            if '[' in part and ']' in part:
                # Handle array indexing
                field_name = part[:part.index('[')]
                index_str = part[part.index('[') + 1:part.index(']')]
                index = int(index_str)
                
                if field_name:
                    current = current[field_name]
                current = current[index]
            else:
                current = current[part]
        
        return current
    
    def _type_matches(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type string."""
        type_mapping = {
            'str': str,
            'string': str,
            'int': int,
            'integer': int,
            'float': float,
            'number': (int, float),
            'bool': bool,
            'boolean': bool,
            'list': list,
            'array': list,
            'dict': dict,
            'object': dict,
            'null': type(None),
            'none': type(None)
        }
        
        expected_python_type = type_mapping.get(expected_type.lower())
        if expected_python_type is None:
            return True  # Unknown type, assume valid
        
        return isinstance(value, expected_python_type)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get validation statistics."""
        success_rate = (self.success_count / self.validation_count * 100) if self.validation_count > 0 else 0
        
        return {
            'total_validations': self.validation_count,
            'successful_validations': self.success_count,
            'failed_validations': self.validation_count - self.success_count,
            'success_rate': success_rate
        }
