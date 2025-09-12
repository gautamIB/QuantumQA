#!/usr/bin/env python3
"""
QuantumQA Unified Test Runner

Main entry point for running both UI and API tests.
Automatically detects test type based on file format and content.
"""

import sys
import asyncio
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="QuantumQA Unified Test Runner - UI and API testing automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Types:
  UI Tests: .txt files with natural language instructions
  API Tests: .yaml/.json files with API documentation

Examples:
  # UI Testing
  %(prog)s examples/conversation_with_login.txt --visible --creds quantumqa/config/credentials.yaml
  %(prog)s examples/aihub_with_login_secure.txt --headless
  
  # API Testing  
  %(prog)s examples/api/jsonplaceholder_tests.yaml
  %(prog)s examples/api/httpbin_auth_tests.yaml --creds quantumqa/config/credentials.yaml
  
  # Mixed Testing (detect automatically)
  %(prog)s my_tests.yaml --base-url https://api.example.com
        """
    )
    
    # Required arguments
    parser.add_argument(
        'test_file',
        help='Path to test file (UI: .txt, API: .yaml/.json)'
    )
    
    # Common arguments (both UI and API)
    parser.add_argument(
        '--creds', '--credentials',
        dest='credentials_file',
        help='Path to credentials.yaml file'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    # UI-specific arguments
    ui_group = parser.add_argument_group('UI Testing Options')
    ui_group.add_argument(
        '--visible',
        action='store_true',
        help='Run browser in visible mode (not headless)'
    )
    
    ui_group.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode (default)'
    )
    
    # API-specific arguments
    api_group = parser.add_argument_group('API Testing Options')
    api_group.add_argument(
        '--base-url',
        dest='base_url_override',
        help='Override base URL from API documentation'
    )
    
    api_group.add_argument(
        '--timeout',
        dest='timeout_override',
        type=int,
        help='Override timeout for all API requests (seconds)'
    )
    
    api_group.add_argument(
        '--stop-on-failure',
        action='store_true',
        help='Stop API test execution on first failure'
    )
    
    # Force test type (override auto-detection)
    parser.add_argument(
        '--type',
        choices=['ui', 'api'],
        help='Force test type (overrides auto-detection)'
    )
    
    return parser

def detect_test_type(test_file: Path) -> str:
    """
    Detect test type based on file extension and content.
    
    Args:
        test_file: Path to test file
        
    Returns:
        'ui' or 'api'
    """
    extension = test_file.suffix.lower()
    
    # Simple extension-based detection
    if extension == '.txt':
        return 'ui'
    elif extension in ['.yaml', '.yml', '.json']:
        return 'api'
    
    # Content-based detection for ambiguous cases
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read().lower()
            
        # Look for API-specific keywords
        api_keywords = ['endpoints:', 'method:', 'base_url:', 'payload:', 'expected_status:']
        api_score = sum(1 for keyword in api_keywords if keyword in content)
        
        # Look for UI-specific keywords  
        ui_keywords = ['click', 'navigate', 'type', 'verify', 'wait', 'screenshot']
        ui_score = sum(1 for keyword in ui_keywords if keyword in content)
        
        return 'api' if api_score > ui_score else 'ui'
        
    except Exception:
        # Default to UI if can't determine
        return 'ui'

async def run_ui_test(args) -> int:
    """Run UI test using existing UI test runner."""
    try:
        import subprocess
        
        # Build command for UI test runner
        cmd = [sys.executable, "scripts/run_generic_test.py", args.test_file]
        
        if args.visible:
            cmd.append("--visible")
        if args.credentials_file:
            cmd.extend(["--creds", args.credentials_file])
        
        print("🖥️ Running UI Test...")
        print("=" * 50)
        print(f"Command: {' '.join(cmd)}")
        print()
        
        # Execute UI test
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        return result.returncode
        
    except Exception as e:
        print(f"❌ Error running UI test: {e}")
        return 1

async def run_api_test(args) -> int:
    """Run API test using API test engine."""
    try:
        from quantumqa.api import APIEngine
        
        print("🌐 Running API Test...")
        print("=" * 50)
        
        # Initialize API engine
        engine = APIEngine(credentials_file=args.credentials_file)
        
        # Run test suite
        result = await engine.run_test_suite(
            documentation_file=args.test_file,
            base_url_override=args.base_url_override,
            timeout_override=args.timeout_override,
            stop_on_failure=args.stop_on_failure
        )
        
        # Return appropriate exit code
        if result.success_rate == 100.0:
            print("🎉 All API tests passed!")
            return 0
        elif result.success_rate >= 50.0:
            print(f"⚠️ Some API tests failed ({result.success_rate:.1f}% success)")
            return 1
        else:
            print(f"❌ Most API tests failed ({result.success_rate:.1f}% success)")
            return 2
            
    except Exception as e:
        print(f"❌ Error running API test: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

async def main():
    """Main entry point for unified test runner."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Validate test file exists
    test_file = Path(args.test_file)
    if not test_file.exists():
        print(f"❌ Error: Test file not found: {test_file}")
        return 1
    
    # Detect test type
    if args.type:
        test_type = args.type
        print(f"🔧 Force test type: {test_type.upper()}")
    else:
        test_type = detect_test_type(test_file)
        print(f"🔍 Detected test type: {test_type.upper()}")
    
    print(f"📂 Test file: {test_file}")
    
    # Handle credentials file
    if args.credentials_file:
        cred_path = Path(args.credentials_file)
        if not cred_path.exists():
            print(f"❌ Error: Credentials file not found: {cred_path}")
            return 1
        print(f"🔐 Credentials: {cred_path}")
    
    print()
    
    try:
        # Route to appropriate test runner
        if test_type == 'api':
            return await run_api_test(args)
        else:  # ui
            return await run_ui_test(args)
            
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
