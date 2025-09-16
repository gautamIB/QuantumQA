#!/usr/bin/env python3
"""
Test script for the new vision-based element detection system.
Demonstrates AI-powered UI element finding using computer vision.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from quantumqa.engines.vision_chrome_engine import VisionChromeEngine
from quantumqa.core.llm import VisionLLMClient


async def test_vision_detection():
    """Test the vision-based element detection system."""
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Please set OPENAI_API_KEY environment variable")
        print("   export OPENAI_API_KEY='your-key-here'")
        return
    
    print("🔮 Testing Vision-Based Element Detection System")
    print("=" * 60)
    
    # Initialize vision client
    print("🤖 Initializing Vision-LLM Client...")
    vision_client = VisionLLMClient(api_key=api_key)
    
    # Initialize vision-enhanced engine
    print("🚀 Initializing Vision-Enhanced Chrome Engine...")
    engine = VisionChromeEngine(
        vision_client=vision_client,
        use_vision_primary=True
    )
    
    try:
        # Initialize browser
        await engine.initialize(headless=False)  # Visible for demonstration
        
        # Test instructions that will use vision
        test_instructions = [
            "Navigate to https://httpbin.org/forms/post",
            "Click the customer name field",
            "Type 'John Doe' in the customer name field",
            "Click the submit button"
        ]
        
        # Create temporary instruction file
        instruction_file = "test_results/vision_test_instructions.txt"
        Path("test_results").mkdir(exist_ok=True)
        
        with open(instruction_file, 'w') as f:
            f.write('\n'.join(test_instructions))
        
        print(f"\n📋 Test Instructions:")
        for i, instruction in enumerate(test_instructions, 1):
            print(f"  {i}. {instruction}")
        
        print(f"\n🎯 Executing Vision-Enhanced Test...")
        
        # Execute test with vision detection
        report = await engine.execute_test(instruction_file)
        
        # Display results
        print(f"\n📊 Vision Test Results:")
        print(f"✅ Success Rate: {report['success_rate']:.1f}% ({report['successful_steps']}/{report['total_steps']})")
        print(f"🌐 Final URL: {report['final_url']}")
        
        # Display vision statistics
        vision_stats = report.get('vision_statistics', {})
        print(f"\n👁️ Vision Detection Performance:")
        print(f"  • Vision attempts: {vision_stats.get('vision_detections', 0)}")
        print(f"  • Success rate: {vision_stats.get('vision_success_rate', 0):.1f}%")
        print(f"  • Traditional fallbacks: {vision_stats.get('traditional_fallbacks', 0)}")
        print(f"  • LLM requests: {vision_stats.get('llm_usage_stats', {}).get('total_requests', 0)}")
        print(f"  • Estimated cost: ${vision_stats.get('llm_usage_stats', {}).get('estimated_cost', 0):.4f}")
        
        # Show detailed element detector stats
        detector_stats = vision_stats.get('element_detector_stats', {})
        if detector_stats:
            print(f"\n🔍 Element Detector Statistics:")
            print(f"  • Cache hit rate: {detector_stats.get('cache_hit_rate', 0):.1f}%")
            print(f"  • Average detection time: {detector_stats.get('average_detection_time', 0):.2f}s")
            print(f"  • Average confidence: {detector_stats.get('average_confidence', 0):.2f}")
        
        # Display step details
        print(f"\n📝 Step Details:")
        for result in report['step_results']:
            status_emoji = "✅" if result['status'] == 'success' else "❌"
            print(f"  {status_emoji} Step {result['step']}: {result['instruction'][:60]}...")
        
        print(f"\n📸 Final screenshot: {report.get('screenshot_path', 'Not saved')}")
        
        # Keep browser open for inspection
        print(f"\n⏸️  Browser will remain open for 15 seconds for inspection...")
        await asyncio.sleep(15)
        
    except Exception as e:
        print(f"❌ Vision test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        await engine.cleanup()


async def test_vision_element_detection_only():
    """Test just the element detection without full automation."""
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Please set OPENAI_API_KEY environment variable")
        return
    
    print("🔍 Testing Vision Element Detection Only")
    print("=" * 50)
    
    # Initialize components
    vision_client = VisionLLMClient(api_key=api_key)
    engine = VisionChromeEngine(vision_client=vision_client)
    
    try:
        await engine.initialize(headless=False)
        
        # Navigate to a test page
        print("🌐 Navigating to test page...")
        await engine.page.goto("https://httpbin.org/forms/post")
        await asyncio.sleep(2)
        
        # Take screenshot for analysis
        screenshot_path = "test_results/element_detection_test.png"
        Path("test_results").mkdir(exist_ok=True)
        
        await engine.page.screenshot(path=screenshot_path, full_page=True)
        print(f"📸 Screenshot saved: {screenshot_path}")
        
        # Test element detection
        test_cases = [
            "customer name input field",
            "submit button",
            "email input field",
            "telephone input field"
        ]
        
        print(f"\n👁️ Testing Element Detection:")
        
        for test_case in test_cases:
            print(f"\n🔍 Looking for: '{test_case}'")
            
            result = await engine.element_detector.detect_element(
                screenshot_path=screenshot_path,
                instruction=f"Find the {test_case}",
                context={
                    "url": engine.page.url,
                    "title": await engine.page.title()
                }
            )
            
            if result.found:
                coords = result.center_coordinates
                print(f"  ✅ Found at ({coords.x}, {coords.y}) confidence={result.confidence:.2f}")
                print(f"     Type: {result.element_type}, Text: '{result.visible_text}'")
            else:
                print(f"  ❌ Not found: {result.error_message}")
        
        # Display detection statistics
        stats = engine.element_detector.get_detection_stats()
        print(f"\n📊 Detection Statistics:")
        print(f"  • Total detections: {stats['total_detections']}")
        print(f"  • Success rate: {stats['success_rate']:.1f}%")
        print(f"  • Average confidence: {stats['average_confidence']:.2f}")
        print(f"  • Cache hit rate: {stats['cache_hit_rate']:.1f}%")
        
        print(f"\n⏸️  Browser will remain open for 10 seconds...")
        await asyncio.sleep(10)
        
    except Exception as e:
        print(f"❌ Element detection test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await engine.cleanup()


if __name__ == "__main__":
    print("🔮 QuantumQA Vision Detection Test Suite")
    print("=" * 60)
    
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--detection-only":
        print("Running element detection test only...")
        asyncio.run(test_vision_element_detection_only())
    else:
        print("Running full vision-enhanced automation test...")
        asyncio.run(test_vision_detection())
    
    print("\n🎉 Vision detection tests completed!")
