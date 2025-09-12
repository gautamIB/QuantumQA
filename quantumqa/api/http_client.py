"""
HTTP Client for API Testing

Provides HTTP request capabilities with authentication support
and integration with the credential management system.
"""

import aiohttp
import json
import time
from typing import Dict, Any, Optional, Union, Tuple
from pathlib import Path
import asyncio

from ..security.credential_manager import CredentialManager

class HTTPClient:
    """HTTP client with authentication and credential management."""
    
    def __init__(self, credentials_file: Optional[str] = None):
        """
        Initialize HTTP client.
        
        Args:
            credentials_file: Path to credentials.yaml file
        """
        self.credential_manager = None
        if credentials_file:
            cred_path = Path(credentials_file)
            if cred_path.exists():
                self.credential_manager = CredentialManager(str(cred_path))
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.request_count = 0
        self.total_time = 0.0
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=300),  # 5 minute default timeout
            connector=aiohttp.TCPConnector(limit=100)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        payload: Optional[Dict[str, Any]] = None,
        auth_credential: Optional[str] = None,
        timeout: int = 30
    ) -> Tuple[int, Dict[str, Any], Dict[str, Any]]:
        """
        Make HTTP request with optional authentication.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            headers: Request headers
            payload: Request payload/body
            auth_credential: Reference to credential in credentials.yaml
            timeout: Request timeout in seconds
            
        Returns:
            Tuple of (status_code, response_data, metadata)
        """
        if not self.session:
            raise RuntimeError("HTTPClient not initialized. Use async context manager.")
        
        start_time = time.time()
        
        try:
            # Prepare headers
            request_headers = dict(headers) if headers else {}
            
            # Handle authentication
            if auth_credential and self.credential_manager:
                auth_headers = await self._get_auth_headers(auth_credential)
                request_headers.update(auth_headers)
            
            # Prepare request parameters
            kwargs = {
                'timeout': aiohttp.ClientTimeout(total=timeout),
                'headers': request_headers
            }
            
            # Add payload for methods that support body
            if payload and method.upper() in ['POST', 'PUT', 'PATCH']:
                if isinstance(payload, dict):
                    kwargs['json'] = payload
                    if 'Content-Type' not in request_headers:
                        request_headers['Content-Type'] = 'application/json'
                else:
                    kwargs['data'] = payload
            
            # Make request
            print(f"🌐 Making {method.upper()} request to: {url}")
            if request_headers:
                masked_headers = self._mask_sensitive_headers(request_headers)
                print(f"📋 Headers ({len(masked_headers)}):")
                for key, value in masked_headers.items():
                    print(f"   {key}: {value}")
            if payload:
                print(f"📦 Payload: {self._mask_sensitive_payload(payload)}")
            
            async with self.session.request(method.upper(), url, **kwargs) as response:
                # Read response
                content_type = response.headers.get('Content-Type', '').lower()
                
                if 'application/json' in content_type:
                    response_data = await response.json()
                elif 'text/' in content_type:
                    response_text = await response.text()
                    response_data = {'text': response_text}
                else:
                    response_data = {'raw': await response.read()}
                
                # Calculate timing
                end_time = time.time()
                request_time = end_time - start_time
                
                # Update statistics
                self.request_count += 1
                self.total_time += request_time
                
                # Prepare metadata
                metadata = {
                    'request_time': request_time,
                    'response_size': len(str(response_data)),
                    'content_type': content_type,
                    'response_headers': dict(response.headers)
                }
                
                print(f"✅ Response: {response.status} in {request_time:.3f}s")
                
                # Show error details for failed requests
                if response.status >= 400:
                    print(f"   ❌ Error: {str(response_data)[:100]}...")
                
                return response.status, response_data, metadata
                
        except asyncio.TimeoutError:
            print(f"⏰ Request timeout after {timeout}s")
            return 408, {'error': 'Request timeout'}, {'request_time': timeout, 'error': 'timeout'}
            
        except aiohttp.ClientError as e:
            print(f"❌ Client error: {e}")
            return 0, {'error': str(e)}, {'request_time': time.time() - start_time, 'error': 'client_error'}
            
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return 0, {'error': str(e)}, {'request_time': time.time() - start_time, 'error': 'unexpected'}
    
    async def _get_auth_headers(self, auth_credential: str) -> Dict[str, str]:
        """
        Get authentication headers from credential reference.
        
        Args:
            auth_credential: Credential reference (e.g., 'api.token')
            
        Returns:
            Dictionary of authentication headers
        """
        if not self.credential_manager:
            return {}
        
        try:
            # Handle different credential formats
            if '.' in auth_credential:
                # Nested credential reference (e.g., 'api.token')
                parts = auth_credential.split('.')
                credential = await self.credential_manager.get_credential(parts[0])
                
                if len(parts) == 2:
                    auth_value = credential.get(parts[1])
                else:
                    # Deep nested access
                    auth_value = credential
                    for part in parts[1:]:
                        auth_value = auth_value.get(part) if isinstance(auth_value, dict) else None
                        if auth_value is None:
                            break
            else:
                # Simple credential reference
                credential = await self.credential_manager.get_credential(auth_credential)
                auth_value = credential
            
            if auth_value is None:
                print(f"⚠️ Warning: No authentication value found for '{auth_credential}'")
                return {}
            
            # Determine authentication type and format headers
            if isinstance(auth_value, str):
                # Simple token - assume Bearer token
                return {'Authorization': f'Bearer {auth_value}'}
            elif isinstance(auth_value, dict):
                # Complex credential - check for common patterns
                if 'token' in auth_value:
                    return {'Authorization': f"Bearer {auth_value['token']}"}
                elif 'api_key' in auth_value:
                    return {'X-API-Key': auth_value['api_key']}
                elif 'username' in auth_value and 'password' in auth_value:
                    # Basic auth - for now, just add as headers (can extend to actual basic auth later)
                    return {
                        'X-Username': auth_value['username'],
                        'X-Password': auth_value['password']
                    }
                else:
                    # Return all credential fields as headers (with X- prefix)
                    headers = {}
                    for key, value in auth_value.items():
                        header_name = f'X-{key.replace("_", "-").title()}'
                        headers[header_name] = str(value)
                    return headers
            else:
                return {'Authorization': str(auth_value)}
                
        except Exception as e:
            print(f"❌ Error getting auth headers for '{auth_credential}': {e}")
            return {}
    
    def _mask_sensitive_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Mask sensitive information in headers for logging."""
        masked = {}
        sensitive_keys = ['authorization', 'x-api-key', 'x-password', 'cookie']
        
        for key, value in headers.items():
            if key.lower() in sensitive_keys:
                if len(value) > 10:
                    masked[key] = f"{value[:4]}...{value[-4:]}"
                else:
                    masked[key] = "***"
            else:
                masked[key] = value
        
        return masked
    
    def _mask_sensitive_payload(self, payload: Any) -> Any:
        """Mask sensitive information in payload for logging."""
        if isinstance(payload, dict):
            masked = {}
            sensitive_keys = ['password', 'secret', 'token', 'key', 'api_key']
            
            for key, value in payload.items():
                if key.lower() in sensitive_keys:
                    if isinstance(value, str) and len(value) > 6:
                        masked[key] = f"{value[:3]}...{value[-3:]}"
                    else:
                        masked[key] = "***"
                elif isinstance(value, dict):
                    masked[key] = self._mask_sensitive_payload(value)
                else:
                    masked[key] = value
            return masked
        else:
            return payload
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get request statistics."""
        avg_time = self.total_time / self.request_count if self.request_count > 0 else 0
        
        return {
            'total_requests': self.request_count,
            'total_time': self.total_time,
            'average_time': avg_time,
            'requests_per_second': self.request_count / self.total_time if self.total_time > 0 else 0
        }
