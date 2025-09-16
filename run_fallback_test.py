#!/usr/bin/env python3
"""
E2E Test Runner with Traditional Element Detection (No Vision Required)
Demonstrates the complete framework without OpenAI API dependency.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from quantumqa.engines.chrome_engine import ChromeEngine


async def run_traditional_e2e_test(instruction_file: str, headless: bool = False, 
                                   connect_to_existing: bool = True, debug_port: int = 9222):
    """Run E2E test using traditional element detection (no vision API)."""
    
    print("🔧 QuantumQA Traditional E2E Test Runner")
    print("=" * 60)
    print("📋 Using traditional DOM-based element detection")
    print("💡 No OpenAI API quota required")
    
    # Verify instruction file exists
    if not Path(instruction_file).exists():
        print(f"❌ Instruction file not found: {instruction_file}")
        return None
    
    print(f"📋 Instruction file: {instruction_file}")
    print(f"🖥️ Headless mode: {headless}")
    
    browser_mode = "Connect to existing" if connect_to_existing else "Launch new"
    print(f"🌐 Browser Mode: {browser_mode}")
    if connect_to_existing:
        print(f"🐛 Debug Port: {debug_port}")
    
    # Initialize traditional Chrome engine with browser reuse
    print(f"\n🚀 Initializing Traditional Chrome Engine...")
    engine = ChromeEngine(
        connect_to_existing=connect_to_existing,
        debug_port=debug_port
    )
    
    try:
        # Initialize browser
        await engine.initialize(headless=headless)
        
        print(f"\n🎯 Executing Traditional E2E Test...")
        
        # Execute test
        report = await engine.execute_test(instruction_file)
        
        # Display results
        print(f"\n" + "=" * 60)
        print(f"📊 TRADITIONAL E2E TEST RESULTS")
        print(f"=" * 60)
        
        print(f"✅ Success Rate: {report['success_rate']:.1f}% ({report['successful_steps']}/{report['total_steps']})")
        print(f"🌐 Final URL: {report['final_url']}")
        print(f"📄 Final Title: {report['final_title']}")
        
        # Step-by-step results
        print(f"\n📝 Step-by-Step Results:")
        for result in report['step_results']:
            status_emoji = "✅" if result['status'] == 'success' else "❌"
            print(f"  {status_emoji} Step {result['step']}: {result['instruction'][:70]}...")
            if result['status'] == 'error' and 'error' in result:
                print(f"      💥 Error: {result['error']}")
        
        if report.get('screenshot_path'):
            print(f"\n📸 Final screenshot: {report['screenshot_path']}")
        
        # Keep browser open for inspection if not headless
        if not headless:
            print(f"\n⏸️  Browser will remain open for 10 seconds for inspection...")
            await asyncio.sleep(10)
        
        return report
        
    except Exception as e:
        print(f"❌ Traditional E2E test failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        # Cleanup
        print(f"\n🛑 Cleaning up...")
        await engine.cleanup()


def main():
    """Main entry point."""
    
    import argparse
    
    parser = argparse.ArgumentParser(
        description="QuantumQA Traditional E2E Test Runner (No Vision API Required)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_fallback_test.py examples/e2e_form_test.txt
  python run_fallback_test.py examples/e2e_form_test.txt --headless
  python run_fallback_test.py examples/e2e_form_test.txt --new-browser  # Force new browser
  python run_fallback_test.py examples/e2e_form_test.txt --debug-port 9223  # Custom port
        """
    )
    
    parser.add_argument(
        "instruction_file",
        help="Path to instruction file"
    )
    
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode"
    )
    
    parser.add_argument(
        "--new-browser",
        action="store_true",
        help="Force launch new browser instead of connecting to existing"
    )
    
    parser.add_argument(
        "--debug-port",
        type=int,
        default=9222,
        help="Chrome remote debugging port (default: 9222)"
    )
    
    args = parser.parse_args()
    
    # Determine browser connection strategy
    connect_to_existing = not args.new_browser
    
    # Run the test
    asyncio.run(run_traditional_e2e_test(
        instruction_file=args.instruction_file,
        headless=args.headless,
        connect_to_existing=connect_to_existing,
        debug_port=args.debug_port
    ))


if __name__ == "__main__":
    main()
