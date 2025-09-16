#!/usr/bin/env python3
"""
Credentials Loader Utility for QuantumQA.
Handles secure loading of credentials from YAML configuration.
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional


class CredentialsLoader:
    """Utility class for loading credentials from YAML configuration."""
    
    def __init__(self, credentials_file: Optional[str] = None):
        """
        Initialize credentials loader.
        
        Args:
            credentials_file: Path to credentials YAML file. If None, uses default location.
        """
        if credentials_file:
            self.credentials_file = Path(credentials_file)
        else:
            # Default location: quantumqa/config/credentials.yaml
            self.credentials_file = Path(__file__).parent.parent / "config" / "credentials.yaml"
        
        self._credentials = None
    
    def load_credentials(self) -> Dict[str, Any]:
        """Load credentials from YAML file."""
        
        if self._credentials is not None:
            return self._credentials
        
        try:
            if not self.credentials_file.exists():
                print(f"⚠️ Credentials file not found: {self.credentials_file}")
                return {}
            
            with open(self.credentials_file, 'r') as f:
                self._credentials = yaml.safe_load(f) or {}
            
            print(f"✅ Loaded credentials from: {self.credentials_file}")
            return self._credentials
            
        except Exception as e:
            print(f"❌ Failed to load credentials: {e}")
            return {}
    
    def get_openai_credentials(self) -> Dict[str, Any]:
        """Get OpenAI API credentials."""
        
        credentials = self.load_credentials()
        openai_creds = credentials.get('openai', {})
        
        # Fallback to environment variable if not in credentials file
        if not openai_creds.get('api_key'):
            env_key = os.getenv('OPENAI_API_KEY')
            if env_key:
                print("🔑 Using OpenAI API key from environment variable")
                openai_creds['api_key'] = env_key
            else:
                print("❌ No OpenAI API key found in credentials file or environment")
        else:
            print("🔑 Using OpenAI API key from credentials file")
        
        # Set defaults
        openai_creds.setdefault('model', 'gpt-4o-mini')  # Default to cost-effective model
        openai_creds.setdefault('max_tokens', 1500)
        openai_creds.setdefault('temperature', 0.1)
        
        return openai_creds
    
    def get_credentials_for_service(self, service_name: str) -> Dict[str, Any]:
        """Get credentials for a specific service."""
        
        credentials = self.load_credentials()
        return credentials.get(service_name, {})
    
    def has_openai_credentials(self) -> bool:
        """Check if OpenAI credentials are available."""
        
        openai_creds = self.get_openai_credentials()
        return bool(openai_creds.get('api_key'))
    
    def get_available_services(self) -> list:
        """Get list of services with credentials configured."""
        
        credentials = self.load_credentials()
        return list(credentials.keys())
    
    def validate_openai_key_format(self) -> bool:
        """Validate OpenAI API key format."""
        
        openai_creds = self.get_openai_credentials()
        api_key = openai_creds.get('api_key', '')
        
        # OpenAI keys should start with 'sk-' and be reasonably long
        if api_key.startswith('sk-') and len(api_key) > 40:
            return True
        
        print(f"⚠️ OpenAI API key format validation failed")
        return False
    


# Global instance for easy access
_global_loader = None


def get_credentials_loader(credentials_file: Optional[str] = None) -> CredentialsLoader:
    """Get global credentials loader instance."""
    
    global _global_loader
    
    if _global_loader is None or credentials_file:
        _global_loader = CredentialsLoader(credentials_file)
    
    return _global_loader


def get_openai_credentials() -> Dict[str, Any]:
    """Convenience function to get OpenAI credentials."""
    
    loader = get_credentials_loader()
    return loader.get_openai_credentials()


def has_openai_credentials() -> bool:
    """Convenience function to check if OpenAI credentials are available."""
    
    loader = get_credentials_loader()
    return loader.has_openai_credentials()


# Example usage and testing
if __name__ == "__main__":
    print("🔧 Testing Credentials Loader")
    
    loader = CredentialsLoader()
    
    print(f"\n📋 Available services: {loader.get_available_services()}")
    
    if loader.has_openai_credentials():
        openai_creds = loader.get_openai_credentials()
        api_key = openai_creds.get('api_key', '')
        print(f"✅ OpenAI API key: {api_key[:15]}... (length: {len(api_key)})")
        print(f"🤖 Model: {openai_creds.get('model')}")
        print(f"🎛️ Temperature: {openai_creds.get('temperature')}")
        print(f"📝 Max tokens: {openai_creds.get('max_tokens')}")
        
        if loader.validate_openai_key_format():
            print("✅ OpenAI API key format is valid")
        else:
            print("❌ OpenAI API key format is invalid")
    else:
        print("❌ No OpenAI credentials found")
