#!/usr/bin/env python3
"""
Generic Chrome Test Runner - Works with ANY application
No hardcoded selectors or app-specific logic!

This replaces the tightly-coupled run_chrome_simple.py with a modular,
scalable architecture that can handle any test case.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from quantumqa.engines.chrome_engine import ChromeEngine


async def run_generic_test(instruction_file: str, headless: bool = False, config_dir: str = None, credentials_file: str = None):
    """Run test using the generic Chrome engine."""
    
    print("🚀 QuantumQA Generic Test Runner")
    print("=" * 50)
    print("🎯 Architecture: Modular, Generic, Scalable")
    print("🔧 Mode:", "Headless" if headless else "Visible Browser")
    print("📝 Instructions:", instruction_file)
    print("🧠 AI-Powered Element Detection")
    print("⚙️ Configuration-Driven Logic")
    
    if credentials_file:
        cred_path = Path(credentials_file)
        if cred_path.exists():
            print("🔐 Security: Credential management enabled")
        else:
            print("⚠️ Security: Credentials file not found, using plain text")
    else:
        print("ℹ️ Security: No credentials file specified")
    
    print("-" * 50)
    
    # Initialize generic engine with credentials
    engine = ChromeEngine(config_dir=config_dir, credentials_file=credentials_file)
    
    try:
        # Initialize browser
        await engine.initialize(headless=headless)
        
        # Execute test
        report = await engine.execute_test(instruction_file)
        
        # Display final results
        await display_final_report(report)
        
        # Keep browser open for inspection if visible
        if not headless and report["success_rate"] > 0:
            print("\n⏸️  Browser will remain open for 15 seconds...")
            print("👀 Inspect the browser to see results!")
            await asyncio.sleep(15)
        
        return report
        
    except Exception as e:
        print(f"❌ Generic test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        # Clean up
        await engine.cleanup()


async def display_final_report(report: dict):
    """Display comprehensive test report."""
    
    print("\n" + "=" * 70)
    print("📊 GENERIC TEST EXECUTION REPORT")
    print("=" * 70)
    
    success_rate = report["success_rate"]
    successful_steps = report["successful_steps"] 
    total_steps = report["total_steps"]
    
    print(f"📈 Overall Success Rate: {success_rate:.1f}% ({successful_steps}/{total_steps})")
    print(f"🌐 Final URL: {report['final_url']}")
    print(f"📄 Final Title: {report['final_title']}")
    
    if success_rate >= 95:
        print("🎉 EXCELLENT: Test execution nearly perfect!")
    elif success_rate >= 80:
        print("✅ GOOD: Most steps executed successfully")
    elif success_rate >= 50:
        print("⚠️ PARTIAL: Some issues detected")
    else:
        print("❌ ISSUES: Multiple failures detected")
    
    # Show step breakdown
    print(f"\n📋 Step-by-Step Results:")
    for result in report["step_results"]:
        status_emoji = {
            "success": "✅",
            "failed": "❌", 
            "error": "🚫"
        }[result["status"]]
        
        instruction = result["instruction"][:60] + "..." if len(result["instruction"]) > 60 else result["instruction"]
        
        print(f"  {status_emoji} Step {result['step']}: {instruction}")
        
        if result["status"] in ["failed", "error"]:
            action_plan = result.get("action_plan", {})
            if action_plan:
                print(f"      🔍 Parsed as: {action_plan.get('action', 'unknown')} -> {action_plan.get('target', 'N/A')}")
            
            if "error" in result:
                print(f"      🚫 Error: {result['error']}")
    
    if report["screenshot_path"]:
        print(f"\n📸 Final Screenshot: {report['screenshot_path']}")


def main():
    """Main entry point."""
    
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    instruction_file = sys.argv[1]
    
    # Parse command line options
    headless = "--visible" not in sys.argv
    config_dir = None
    credentials_file = None
    
    # Check for config directory option
    if "--config" in sys.argv:
        config_index = sys.argv.index("--config")
        if config_index + 1 < len(sys.argv):
            config_dir = sys.argv[config_index + 1]
    
    # Check for credentials file option
    if "--credentials" in sys.argv:
        cred_index = sys.argv.index("--credentials")
        if cred_index + 1 < len(sys.argv):
            credentials_file = sys.argv[cred_index + 1]
    elif "--creds" in sys.argv:
        cred_index = sys.argv.index("--creds")
        if cred_index + 1 < len(sys.argv):
            credentials_file = sys.argv[cred_index + 1]
    else:
        # Check for default credentials file in config folder
        default_creds = Path("quantumqa/config/credentials.yaml")
        if default_creds.exists():
            credentials_file = str(default_creds)
    
    # Validate instruction file exists
    if not Path(instruction_file).exists():
        print(f"❌ Error: Instruction file not found: {instruction_file}")
        sys.exit(1)
    
    # Run the test
    asyncio.run(run_generic_test(instruction_file, headless, config_dir, credentials_file))


def print_usage():
    """Print usage information."""
    
    print("🚀 QuantumQA Generic Test Runner")
    print("=" * 40)
    print("Usage: python run_generic_test.py <instruction_file> [options]")
    print("\nOptions:")
    print("  --visible                      Run in visible mode (default: headless)")
    print("  --config <dir>                 Use custom config directory")
    print("  --credentials <file>           Use credentials file for secure data")
    print("  --creds <file>                 Shorthand for --credentials")
    print("\nExamples:")
    print("  python run_generic_test.py examples/aihub_with_login.txt --visible")
    print("  python run_generic_test.py examples/my_custom_test.txt --visible --creds credentials.yaml")
    print("  python run_generic_test.py examples/any_app_test.txt --config my_configs/ --credentials secrets.yaml")
    print("\n🎯 Key Features:")
    print("  ✅ Works with ANY application (no hardcoded selectors)")
    print("  ✅ AI-powered element detection")
    print("  ✅ Configuration-driven (no code changes needed)")
    print("  ✅ Modular architecture (easy to extend)")
    print("  ✅ Intelligent action execution strategies")
    print("  🔐 Secure credential management (no plain text passwords)")
    print("\n🔧 Architecture:")
    print("  📋 Instruction Parser  -> Converts natural language to actions")
    print("  🔍 Element Finder      -> Smart element detection")
    print("  ⚡ Action Executor     -> Intelligent action execution") 
    print("  🖥️ Chrome Engine       -> Coordinates everything")
    print("  ⚙️ Config Files        -> No hardcoded logic!")


if __name__ == "__main__":
    main()
