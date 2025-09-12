"""
Secure credential management for QuantumQA framework.
Provides secure storage and retrieval of sensitive information.
"""

import yaml
import base64
import os
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet


class CredentialManager:
    """Manages secure storage and retrieval of credentials."""
    
    def __init__(self, credentials_file: str, encryption_key: Optional[str] = None):
        """
        Initialize credential manager.
        
        Args:
            credentials_file: Path to credentials YAML file (string)
            encryption_key: Optional encryption key (uses env var if not provided)
        """
        self.credentials_file = Path(credentials_file)
        self.encryption_key = encryption_key or os.getenv('QUANTUMQA_ENCRYPTION_KEY')
        self.credentials = {}
        self._load_credentials()
    
    def _load_credentials(self):
        """Load credentials from file."""
        try:
            if self.credentials_file.exists():
                with open(self.credentials_file, 'r') as f:
                    raw_data = yaml.safe_load(f) or {}
                    
                # Decrypt credentials if encryption key is available
                if self.encryption_key:
                    self.credentials = self._decrypt_credentials(raw_data)
                else:
                    self.credentials = raw_data
                    
                print(f"✅ Loaded credentials from: {self.credentials_file}")
            else:
                print(f"⚠️ Credentials file not found: {self.credentials_file}")
                self.credentials = {}
                
        except Exception as e:
            print(f"❌ Error loading credentials: {e}")
            self.credentials = {}
    
    def _decrypt_credentials(self, encrypted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt credential values."""
        try:
            fernet = Fernet(self.encryption_key.encode())
            decrypted = {}
            
            for key, value in encrypted_data.items():
                if isinstance(value, dict):
                    decrypted[key] = {}
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, str) and sub_value.startswith('encrypted:'):
                            encrypted_value = sub_value.replace('encrypted:', '')
                            decrypted[key][sub_key] = fernet.decrypt(encrypted_value.encode()).decode()
                        else:
                            decrypted[key][sub_key] = sub_value
                else:
                    decrypted[key] = value
                    
            return decrypted
            
        except Exception as e:
            print(f"⚠️ Decryption failed, using plain text: {e}")
            return encrypted_data
    
    def get_credential(self, credential_path: str) -> Optional[str]:
        """
        Retrieve credential by path (e.g., 'aihub.email' or 'aihub.password').
        
        Args:
            credential_path: Dot-separated path to credential
            
        Returns:
            Credential value or None if not found
        """
        try:
            parts = credential_path.split('.')
            current = self.credentials
            
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    print(f"❌ Credential not found: {credential_path}")
                    return None
                    
            return str(current) if current is not None else None
            
        except Exception as e:
            print(f"❌ Error retrieving credential {credential_path}: {e}")
            return None
    
    def list_available_credentials(self) -> Dict[str, Any]:
        """List all available credential paths (without values)."""
        def extract_paths(data: Dict[str, Any], prefix: str = "") -> Dict[str, str]:
            paths = {}
            for key, value in data.items():
                current_path = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    paths.update(extract_paths(value, current_path))
                else:
                    paths[current_path] = type(value).__name__
            return paths
        
        return extract_paths(self.credentials)
    
    def encrypt_credential(self, value: str) -> str:
        """Encrypt a credential value for storage."""
        if not self.encryption_key:
            return value
            
        try:
            fernet = Fernet(self.encryption_key.encode())
            encrypted = fernet.encrypt(value.encode())
            return f"encrypted:{encrypted.decode()}"
        except Exception as e:
            print(f"❌ Encryption failed: {e}")
            return value
    
    @staticmethod
    def generate_encryption_key() -> str:
        """Generate a new encryption key."""
        return Fernet.generate_key().decode()


def resolve_credentials_in_text(text: str, credential_manager: CredentialManager) -> str:
    """
    Resolve credential references in text.
    
    Supports formats:
    - {cred:aihub.email}
    - {credential:aihub.password}
    - {creds:database.username}
    
    Args:
        text: Text containing credential references
        credential_manager: CredentialManager instance
        
    Returns:
        Text with resolved credentials
    """
    import re
    
    # Pattern to match credential references
    pattern = r'\{(?:cred|credential|creds):([^}]+)\}'
    
    def replace_credential(match):
        credential_path = match.group(1).strip()
        value = credential_manager.get_credential(credential_path)
        if value is not None:
            return value
        else:
            print(f"⚠️ Could not resolve credential: {credential_path}")
            return match.group(0)  # Return original if not found
    
    resolved_text = re.sub(pattern, replace_credential, text)
    return resolved_text
