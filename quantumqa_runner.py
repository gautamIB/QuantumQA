#!/usr/bin/env python3
"""
QuantumQA Framework Runner - Unified Entry Point
Supports both UI and API testing with auto-detection.
"""

import asyncio
import sys
import argparse
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from quantumqa.engines.vision_chrome_engine import VisionChromeEngine
from quantumqa.engines.chrome_engine import ChromeEngine
from quantumqa.core.llm import VisionLLMClient
from quantumqa.api.api_engine import APIEngine
from quantumqa.api.api_parser import APIDocumentationParser


def detect_test_type(instruction_file: str) -> str:
    """Auto-detect if this is a UI or API test."""
    file_path = Path(instruction_file)
    
    # Check file extension
    if file_path.suffix.lower() in ['.yaml', '.yml', '.json']:
        return 'api'
    
    # Check file content for API indicators
    if file_path.exists():
        try:
            content = file_path.read_text().lower()
            api_keywords = ['endpoint:', 'method:', 'headers:', 'payload:', 'response:', 'status_code:']
            if any(keyword in content for keyword in api_keywords):
                return 'api'
        except:
            pass
    
    return 'ui'


async def run_ui_test(instruction_file: str, headless: bool = False, 
                     credentials_file: Optional[str] = None, config_dir: Optional[str] = None,
                     connect_to_existing: bool = True, debug_port: int = 9222):
    """Run UI test using Vision-Enhanced Chrome engine."""
    print("🌐 Running Vision-Enhanced UI Test")
    print("=" * 50)
    
    # Initialize vision client for AI-powered element detection
    try:
        print("🤖 Initializing Vision-LLM Client...")
        vision_client = VisionLLMClient()
        print("✅ Vision client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize vision client: {e}")
        print("🔄 Falling back to basic Chrome engine...")
        
        # Fallback to basic engine if vision fails
        engine = ChromeEngine(
            config_dir=config_dir, 
            credentials_file=credentials_file,
            connect_to_existing=connect_to_existing,
            debug_port=debug_port
        )
    else:
        # Use vision-enhanced engine
        engine = VisionChromeEngine(
            vision_client=vision_client,
            config_dir=config_dir, 
            credentials_file=credentials_file,
            connect_to_existing=connect_to_existing,
            debug_port=debug_port
        )
    
    try:
        await engine.initialize(headless=headless)
        report = await engine.execute_test(instruction_file)
        
        print(f"\n📊 UI Test Results:")
        print(f"✅ Success Rate: {report['success_rate']:.1f}% ({report['successful_steps']}/{report['total_steps']})")
        print(f"🌐 Final URL: {report['final_url']}")
        print(f"📄 Final Title: {report['final_title']}")
        
        if report["screenshot_path"]:
            print(f"📸 Screenshot: {report['screenshot_path']}")
        
        return report
        
    except Exception as e:
        print(f"❌ UI Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        await engine.cleanup()


async def run_api_test(instruction_file: str, credentials_file: Optional[str] = None):
    """Run API test using API engine."""
    print("🚀 Running API Test")
    print("=" * 50)
    
    try:
        # Parse API documentation
        parser = APIDocumentationParser()
        api_suite = parser.parse_file(instruction_file)
        
        if not api_suite:
            print("❌ Failed to parse API test suite")
            return None
        
        # Run API tests
        engine = APIEngine(credentials_file=credentials_file)
        results = await engine.execute_test_suite(api_suite)
        
        # Display results
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.status == "success")
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n📊 API Test Results:")
        print(f"✅ Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests})")
        
        for result in results:
            status_emoji = "✅" if result.status == "success" else "❌"
            print(f"  {status_emoji} {result.test_name}: {result.status}")
            if result.status != "success" and result.error:
                print(f"     💥 Error: {result.error}")
        
        return {"success_rate": success_rate, "total_tests": total_tests, "passed_tests": passed_tests}
        
    except Exception as e:
        print(f"❌ API Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="QuantumQA Framework - AI-Powered UI & API Testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # UI Tests (auto-detected, reuses existing Chrome by default)
  python quantumqa_runner.py examples/conversation_with_login.txt --visible
  python quantumqa_runner.py examples/conversation_with_login.txt --credentials quantumqa/config/credentials.yaml
  
  # Force new browser window (don't reuse existing)
  python quantumqa_runner.py examples/my_test.txt --visible --new-browser
  
  # Use different debug port for browser connection
  python quantumqa_runner.py examples/my_test.txt --visible --debug-port 9223
  
  # API Tests (auto-detected)  
  python quantumqa_runner.py examples/api/chatbot_tests.yaml
  python quantumqa_runner.py examples/api/chatbot_tests.yaml --credentials quantumqa/config/credentials.yaml
  
  # Force test type
  python quantumqa_runner.py examples/my_test.txt --type ui --visible
  python quantumqa_runner.py examples/my_test.yaml --type api
        """
    )
    
    parser.add_argument('instruction_file', help='Path to instruction file (.txt for UI, .yaml/.json for API)')
    parser.add_argument('--type', choices=['ui', 'api', 'auto'], default='auto', 
                       help='Test type (default: auto-detect)')
    parser.add_argument('--visible', action='store_true', 
                       help='Run UI tests in visible mode (default: headless)')
    parser.add_argument('--credentials', '--creds', 
                       help='Path to credentials file (default: quantumqa/config/credentials.yaml)')
    parser.add_argument('--config', 
                       help='Path to config directory (default: quantumqa/config/)')
    parser.add_argument('--connect-existing', action='store_true', default=True,
                       help='Connect to existing Chrome browser if available (default: True)')
    parser.add_argument('--new-browser', action='store_true', 
                       help='Force launch new browser instead of connecting to existing')
    parser.add_argument('--debug-port', type=int, default=9222,
                       help='Chrome remote debugging port (default: 9222)')
    
    args = parser.parse_args()
    
    # Validate instruction file exists
    if not Path(args.instruction_file).exists():
        print(f"❌ Error: Instruction file not found: {args.instruction_file}")
        sys.exit(1)
    
    # Auto-detect credentials file if not specified
    if not args.credentials:
        default_creds = Path("quantumqa/config/credentials.yaml")
        if default_creds.exists():
            args.credentials = str(default_creds)
    
    # Determine test type
    if args.type == 'auto':
        test_type = detect_test_type(args.instruction_file)
    else:
        test_type = args.type
    
    # Determine browser connection strategy
    connect_to_existing = args.connect_existing and not args.new_browser
    
    print("🚀 QuantumQA Framework Runner")
    print("=" * 50)
    print(f"📁 Instruction File: {args.instruction_file}")
    print(f"🎯 Test Type: {test_type.upper()}")
    if args.credentials:
        print(f"🔐 Credentials: {args.credentials}")
    if test_type == 'ui':
        browser_mode = "Connect to existing" if connect_to_existing else "Launch new"
        print(f"🌐 Browser Mode: {browser_mode}")
        if connect_to_existing:
            print(f"🐛 Debug Port: {args.debug_port}")
    print("=" * 50)
    
    # Run appropriate test
    if test_type == 'api':
        result = await run_api_test(args.instruction_file, args.credentials)
    else:  # ui
        headless = not args.visible
        result = await run_ui_test(
            args.instruction_file, 
            headless, 
            args.credentials, 
            args.config,
            connect_to_existing,
            args.debug_port
        )
    
    # Exit with appropriate code
    if result:
        success_rate = result.get('success_rate', 0)
        sys.exit(0 if success_rate >= 80 else 1)
    else:
        sys.exit(1)


def sync_main():
    """Synchronous wrapper for main."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    sync_main()
