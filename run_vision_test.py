#!/usr/bin/env python3
"""
QuantumQA Vision-Enhanced Test Runner

This script runs tests using the vision-enhanced Chrome engine that leverages
OpenAI's vision models for intelligent element detection.
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Optional

from quantumqa.engines.vision_chrome_engine import VisionChromeEngine
from quantumqa.core.llm import VisionLLMClient
from quantumqa.utils.credentials_loader import has_openai_credentials


async def run_vision_test(
    instruction_file: str,
    headless: bool = False,
    visible: bool = False,
    api_key: Optional[str] = None,
    use_vision_primary: bool = True,
    connect_to_existing: bool = True,
    debug_port: int = 9222
):
    """
    Run a test using the vision-enhanced Chrome engine.
    
    Args:
        instruction_file: Path to instruction file
        headless: Run browser in headless mode
        visible: Force browser to be visible (overrides headless)
        api_key: OpenAI API key (if not in environment)
        use_vision_primary: Use vision as primary detection method
        connect_to_existing: Connect to existing Chrome instance (preserves auth/cookies)
        debug_port: Chrome remote debugging port
    """
    
    print("🔮 QuantumQA Vision-Enhanced Test Runner")
    print("=" * 60)
    
    # Check credentials (automatic loading from credentials file)
    if not has_openai_credentials() and not api_key:
        print("❌ No OpenAI credentials found!")
        print("💡 Please either:")
        print("   1. Add OpenAI API key to quantumqa/config/credentials.yaml")
        print("   2. Set OPENAI_API_KEY environment variable")
        print("   3. Use --api-key parameter")
        return None
    
    # Validate instruction file
    if not Path(instruction_file).exists():
        print(f"❌ Instruction file not found: {instruction_file}")
        return None
    
    # Handle visible/headless logic (visible overrides headless)
    actual_headless = headless and not visible
    
    print(f"📋 Instruction file: {instruction_file}")
    print(f"👁️ Vision detection: {'Primary' if use_vision_primary else 'Fallback only'}")
    print(f"🖥️ Browser mode: {'Visible' if not actual_headless else 'Headless'}")
    print(f"🔗 Browser connection: {'Connect to existing' if connect_to_existing else 'Launch new'}")
    if connect_to_existing:
        print(f"🐛 Debug port: {debug_port}")
    
    # Initialize vision client (auto-loads from credentials if api_key is None)
    print(f"\n🤖 Initializing Vision-LLM Client...")
    try:
        vision_client = VisionLLMClient(api_key=api_key)
    except Exception as e:
        print(f"❌ Failed to initialize vision client: {e}")
        return None
    
    # Initialize vision-enhanced engine
    print(f"🚀 Initializing Vision-Enhanced Chrome Engine...")
    engine = VisionChromeEngine(
        vision_client=vision_client,
        use_vision_primary=use_vision_primary,
        connect_to_existing=connect_to_existing,
        debug_port=debug_port
    )
    
    # Initialize the browser with headless option
    await engine.initialize(headless=actual_headless)
    
    try:
        print(f"\n🎯 Executing Vision-Enhanced Test...")
        results = await engine.execute_test(instruction_file)
        
        print("\n" + "=" * 60)
        print("📊 VISION-ENHANCED TEST RESULTS")
        print("=" * 60)
        
        if results:
            total_steps = results.get('total_steps', 0)
            successful_steps = results.get('successful_steps', 0)
            failed_steps = total_steps - successful_steps
            success_rate = results.get('success_rate', 0)
            
            print(f"✅ Overall Success Rate: {success_rate:.1f}% ({successful_steps}/{total_steps})")
            print(f"🌐 Final URL: {results.get('final_url', 'Unknown')}")
            print(f"📄 Final Title: {results.get('final_title', 'Unknown')}")
            
            # Vision statistics from results
            vision_stats = results.get('vision_statistics', {})
            if vision_stats:
                print(f"\n👁️ Vision Detection Performance:")
                print(f"  • Vision attempts: {vision_stats.get('vision_detections', 0)}")
                
                # Calculate vision success rate
                vision_detections = vision_stats.get('vision_detections', 0)
                detection_failures = vision_stats.get('detection_failures', 0)
                if vision_detections > 0:
                    vision_success_rate = ((vision_detections - detection_failures) / vision_detections) * 100
                    print(f"  • Vision success rate: {vision_success_rate:.1f}%")
                else:
                    print(f"  • Vision success rate: 0.0%")
                    
                print(f"  • Traditional fallbacks: {vision_stats.get('traditional_fallbacks', 0)}")
                print(f"  • Detection failures: {detection_failures}")
            
            # LLM usage stats from results
            llm_stats = vision_stats.get('llm_usage_stats', {}) if vision_stats else {}
            if llm_stats:
                print(f"\n💰 LLM Usage & Costs:")
                print(f"  • Total requests: {llm_stats.get('total_requests', 0)}")
                print(f"  • Estimated cost: ${llm_stats.get('estimated_cost', 0.0):.4f}")
                print(f"  • Model used: {llm_stats.get('model', 'Unknown')}")
            
            # Element detector performance stats
            element_stats = vision_stats.get('element_detector_stats', {}) if vision_stats else {}
            if element_stats:
                print(f"\n🔍 Element Detector Performance:")
                print(f"  • Cache hit rate: {element_stats.get('cache_hit_rate', 0):.1f}%")
                print(f"  • Average detection time: {element_stats.get('avg_detection_time', 0):.2f}s")
                print(f"  • Average confidence: {element_stats.get('avg_confidence', 0):.2f}")
            
            # Performance statistics
            perf_stats = results.get('performance_statistics', {})
            if perf_stats:
                print(f"\n⚡ Performance Analysis:")
                print(f"  • Total test time: {perf_stats.get('total_test_time', 0):.2f}s")
                print(f"  • Average step time: {perf_stats.get('average_step_time', 0):.2f}s")
                print(f"  • Fastest step: {perf_stats.get('min_step_time', 0):.2f}s")
                print(f"  • Slowest step: {perf_stats.get('max_step_time', 0):.2f}s")
                print(f"  • Average parse time: {perf_stats.get('average_parse_time', 0):.3f}s")
                print(f"  • Average execute time: {perf_stats.get('average_execute_time', 0):.2f}s")
                print(f"  • Test speed: {perf_stats.get('steps_per_minute', 0):.1f} steps/min")
                
                # Performance analysis 
                avg_step = perf_stats.get('average_step_time', 0)
                if avg_step > 15:
                    print(f"  ⚠️ SLOW: Steps averaging {avg_step:.1f}s - likely network/server delays")
                elif avg_step > 8:
                    print(f"  ⚡ MODERATE: Steps averaging {avg_step:.1f}s - vision AI processing time")
                else:
                    print(f"  🚀 FAST: Steps averaging {avg_step:.1f}s - efficient execution")
            
            # Step details
            step_results = results.get('step_results', [])
            if step_results:
                print(f"\n📝 Step-by-Step Results:")
                for i, step in enumerate(step_results):
                    # Handle both dict and object formats
                    if isinstance(step, dict):
                        success = step.get('success', False)
                        instruction = step.get('instruction', f'Step {i+1}')
                    else:
                        success = getattr(step, 'success', False)
                        instruction = getattr(step, 'instruction', f'Step {i+1}')
                    
                    status = "✅" if success else "❌"
                    instruction_short = instruction[:80] + "..." if len(instruction) > 80 else instruction
                    print(f"  {status} Step {i+1}: {instruction_short}")
            
            screenshot_path = results.get('screenshot_path', 'Unknown')
            print(f"\n📸 Final screenshot: {screenshot_path}")
            
        else:
            print("❌ Test execution failed - no results returned")
            
        return results
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        print(f"\n🛑 Cleaning up...")
        await engine.cleanup()


def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="QuantumQA Vision-Enhanced Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Connect to existing Chrome (fast, preserves auth):
  python run_vision_test.py examples/conversation_with_login.txt --visible
  
  # Launch fresh browser (slow, clean session):
  python run_vision_test.py examples/simple_test.txt --new-browser
  
  # Other options:
  python run_vision_test.py examples/form_test.txt --headless
  python run_vision_test.py examples/complex_test.txt --debug-port 9223
  
Setup for existing Chrome connection:
  1. Start Chrome with: google-chrome --remote-debugging-port=9222
  2. Run tests to connect to this instance
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
        "--visible",
        action="store_true",
        help="Force browser to be visible (overrides --headless, useful for debugging)"
    )
    
    parser.add_argument(
        "--api-key",
        help="OpenAI API key (overrides environment variable)"
    )
    
    parser.add_argument(
        "--no-vision-primary",
        action="store_true",
        help="Use traditional detection as primary, vision as fallback"
    )
    
    parser.add_argument(
        "--new-browser",
        action="store_true",
        help="Launch new browser instead of connecting to existing (slower, fresh session)"
    )
    
    parser.add_argument(
        "--debug-port",
        type=int,
        default=9222,
        help="Chrome remote debugging port (default: 9222)"
    )
    
    args = parser.parse_args()
    
    # Run the test
    asyncio.run(run_vision_test(
        instruction_file=args.instruction_file,
        headless=args.headless,
        visible=args.visible,
        api_key=args.api_key,
        use_vision_primary=not args.no_vision_primary,
        connect_to_existing=not args.new_browser,
        debug_port=args.debug_port
    ))


if __name__ == "__main__":
    main()
