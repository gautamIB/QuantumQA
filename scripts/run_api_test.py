#!/usr/bin/env python3
"""
QuantumQA API Test Runner

Main entry point for running API tests from documentation files.
Supports YAML and JSON API documentation formats.
"""

import sys
import asyncio
import argparse
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from quantumqa.api import APIEngine

def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="QuantumQA API Test Runner - Automated API testing from documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s examples/api/jsonplaceholder_tests.yaml
  %(prog)s examples/api/httpbin_auth_tests.yaml --creds quantumqa/config/credentials.yaml
  %(prog)s my_api_tests.yaml --base-url https://api.example.com --timeout 60
  %(prog)s api_suite.json --stop-on-failure --verbose
        """
    )
    
    # Required arguments
    parser.add_argument(
        'documentation_file',
        help='Path to API documentation file (YAML or JSON)'
    )
    
    # Optional arguments
    parser.add_argument(
        '--creds', '--credentials',
        dest='credentials_file',
        help='Path to credentials.yaml file (default: quantumqa/config/credentials.yaml)'
    )
    
    parser.add_argument(
        '--base-url',
        dest='base_url_override',
        help='Override base URL from documentation'
    )
    
    parser.add_argument(
        '--timeout',
        dest='timeout_override',
        type=int,
        help='Override timeout for all requests (seconds)'
    )
    
    parser.add_argument(
        '--stop-on-failure',
        action='store_true',
        help='Stop execution on first test failure'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    return parser

async def main():
    """Main entry point for API test runner."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Validate documentation file exists
    doc_file = Path(args.documentation_file)
    if not doc_file.exists():
        print(f"❌ Error: API documentation file not found: {doc_file}")
        return 1
    
    # Handle credentials file
    credentials_file = None
    if args.credentials_file:
        cred_path = Path(args.credentials_file)
        if cred_path.exists():
            credentials_file = str(cred_path)
        else:
            print(f"❌ Error: Credentials file not found: {cred_path}")
            return 1
    else:
        # Check for default credentials file in config folder
        default_creds = Path("quantumqa/config/credentials.yaml")
        if default_creds.exists():
            credentials_file = str(default_creds)
    
    # Display configuration
    print("🚀 QuantumQA API Test Runner")
    print("=" * 50)
    print(f"📖 Documentation: {doc_file}")
    if credentials_file:
        print(f"🔐 Credentials: {credentials_file}")
    else:
        print("🔓 No credentials file (public APIs only)")
    
    if args.base_url_override:
        print(f"🔧 Base URL Override: {args.base_url_override}")
    if args.timeout_override:
        print(f"⏱️  Timeout Override: {args.timeout_override}s")
    if args.stop_on_failure:
        print("🛑 Stop on failure: Enabled")
    
    print()
    
    try:
        # Initialize API engine
        engine = APIEngine(credentials_file=credentials_file)
        
        # Run test suite
        result = await engine.run_test_suite(
            documentation_file=doc_file,
            base_url_override=args.base_url_override,
            timeout_override=args.timeout_override,
            stop_on_failure=args.stop_on_failure
        )
        
        # Return appropriate exit code
        if result.success_rate == 100.0:
            print("🎉 All tests passed!")
            return 0
        elif result.success_rate >= 50.0:
            print(f"⚠️ Some tests failed ({result.success_rate:.1f}% success)")
            return 1
        else:
            print(f"❌ Most tests failed ({result.success_rate:.1f}% success)")
            return 2
            
    except KeyboardInterrupt:
        print("\n⏹️ Test execution interrupted by user")
        return 130
    except Exception as e:
        print(f"❌ Critical error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️ Interrupted")
        sys.exit(130)
