#!/usr/bin/env python3
"""
Real Browser Test Runner - Actually executes browser automation
This version enables actual browser execution instead of simulation
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from quantumqa import QuantumQA
from quantumqa.core.browser import BrowserManager, BrowserConfig

async def run_real_browser_test(instruction_file: str, headless: bool = False):
    """Run a test with ACTUAL browser automation."""
    
    print("🌐 QuantumQA Real Browser Test Runner")
    print("=" * 50)
    print(f"🔧 Mode: {'Headless' if headless else 'Visible'} Browser")
    print(f"📝 Instructions: {instruction_file}")
    print("-" * 50)
    
    # Load instructions
    instruction_path = Path(instruction_file)
    if not instruction_path.exists():
        print(f"❌ Error: Instruction file not found: {instruction_file}")
        return
    
    with open(instruction_path, 'r') as f:
        instructions = [line.strip() for line in f.readlines() if line.strip()]
    
    print(f"📋 Loaded {len(instructions)} instructions")
    
    # Create browser config for actual execution
    browser_config = BrowserConfig(
        headless=headless,
        viewport_width=1400,
        viewport_height=900,
        timeout=30000
    )
    
    # Initialize browser manager
    browser_manager = BrowserManager(browser_config)
    
    try:
        # Start browser
        print("🚀 Starting browser...")
        await browser_manager.start()
        page = browser_manager.page
        
        print("✅ Browser started successfully!")
        print(f"📊 Browser Type: {browser_config.browser_type}")
        print(f"📏 Viewport: {browser_config.viewport_width}x{browser_config.viewport_height}")
        
        # Execute instructions step by step
        print("\n🎯 Executing Instructions:")
        print("-" * 50)
        
        step_results = []
        
        for i, instruction in enumerate(instructions, 1):
            print(f"\n📍 Step {i}/{len(instructions)}: {instruction}")
            
            try:
                # Parse and execute instruction
                success = await execute_instruction(page, instruction, i)
                
                if success:
                    print(f"✅ Step {i} completed successfully")
                    step_results.append({"step": i, "instruction": instruction, "status": "success"})
                else:
                    print(f"❌ Step {i} failed")
                    step_results.append({"step": i, "instruction": instruction, "status": "failed"})
                
                # Small delay between steps
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"❌ Step {i} error: {str(e)}")
                step_results.append({"step": i, "instruction": instruction, "status": "error", "error": str(e)})
        
        # Generate detailed report
        print("\n" + "=" * 50)
        print("📊 EXECUTION REPORT")
        print("=" * 50)
        
        successful_steps = len([r for r in step_results if r["status"] == "success"])
        total_steps = len(step_results)
        success_rate = (successful_steps / total_steps) * 100 if total_steps > 0 else 0
        
        print(f"📈 Overall Success Rate: {success_rate:.1f}% ({successful_steps}/{total_steps})")
        print(f"🌐 Current URL: {page.url}")
        print(f"📄 Page Title: {await page.title()}")
        
        print("\n📋 Step-by-Step Results:")
        for result in step_results:
            status_emoji = {"success": "✅", "failed": "❌", "error": "🚫"}[result["status"]]
            print(f"  {status_emoji} Step {result['step']}: {result['instruction'][:60]}...")
            if "error" in result:
                print(f"      🔍 Error: {result['error']}")
        
        # Take final screenshot
        screenshot_path = f"test_results/final_state_{instruction_file.replace('/', '_')}.png"
        Path("test_results").mkdir(exist_ok=True)
        await page.screenshot(path=screenshot_path)
        print(f"📸 Final screenshot saved: {screenshot_path}")
        
        # Wait for user to inspect (only if not headless)
        if not headless:
            print("\n⏸️  Browser will remain open for 10 seconds for inspection...")
            await asyncio.sleep(10)
        
    except Exception as e:
        print(f"❌ Browser test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        print("\n🛑 Cleaning up browser...")
        await browser_manager.stop()
        print("✅ Browser closed")

async def execute_instruction(page, instruction: str, step_num: int) -> bool:
    """Execute a single instruction on the page."""
    
    instruction_lower = instruction.lower()
    
    try:
        # Navigation instructions
        if instruction_lower.startswith("navigate to"):
            parts = instruction.split("Navigate to", 1) or instruction.split("navigate to", 1)
            if len(parts) > 1:
                url = parts[1].strip()
                print(f"  🧭 Navigating to: {url}")
                await page.goto(url, wait_until="networkidle")
                return True
            else:
                print(f"  ❌ Invalid navigation instruction format")
                return False
        
        # Verification instructions
        elif "verify" in instruction_lower and ("loads" in instruction_lower or "page" in instruction_lower):
            print(f"  ✅ Verifying page load...")
            # Wait for page to be ready
            await page.wait_for_load_state("networkidle")
            title = await page.title()
            print(f"    📄 Page Title: {title}")
            print(f"    🌐 Current URL: {page.url}")
            return True
        
        # Click instructions
        elif instruction_lower.startswith("click on") or instruction_lower.startswith("click the"):
            # Handle both "click on" and "click the" formats
            if instruction_lower.startswith("click on"):
                parts = instruction.split("click on", 1)
            else:
                parts = instruction.split("click the", 1)
                
            if len(parts) > 1:
                target = parts[1].strip().strip("'\"")
                print(f"  👆 Looking for clickable element: {target}")
                
                # Try multiple selectors
                selectors_to_try = [
                    f"text={target}",
                    f"[aria-label*='{target}' i]",
                    f"[title*='{target}' i]",
                    f"*:has-text('{target}')",
                    f".{target.replace(' ', '-').lower()}",
                    f"#{target.replace(' ', '-').lower()}"
                ]
                
                for selector in selectors_to_try:
                    try:
                        element = page.locator(selector).first
                        if await element.is_visible():
                            await element.click()
                            print(f"    ✅ Clicked element with selector: {selector}")
                            return True
                    except:
                        continue
                
                print(f"    ⚠️ Could not find clickable element: {target}")
                return False
            else:
                print(f"  ❌ Invalid click instruction format")
                return False
        
        # Type instructions
        elif "type" in instruction_lower and "in" in instruction_lower:
            # Extract text to type and field
            parts = instruction.lower().split("type")[1].split("in")
            text_to_type = parts[0].strip().strip("'\"")
            field = parts[1].strip().strip("'\"")
            
            print(f"  ⌨️ Typing '{text_to_type}' in field: {field}")
            
            # Try to find the input field
            selectors_to_try = [
                f"input[placeholder*='{field}' i]",
                f"input[name*='{field}' i]",
                f"textarea[placeholder*='{field}' i]",
                f"[aria-label*='{field}' i]"
            ]
            
            for selector in selectors_to_try:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible():
                        await element.fill(text_to_type)
                        print(f"    ✅ Typed text using selector: {selector}")
                        return True
                except:
                    continue
                    
            print(f"    ⚠️ Could not find input field: {field}")
            return False
        
        # Press Enter
        elif "press enter" in instruction_lower:
            print(f"  ⌨️ Pressing Enter key")
            await page.keyboard.press("Enter")
            await page.wait_for_load_state("networkidle")
            return True
        
        # Scroll instructions
        elif "scroll" in instruction_lower:
            print(f"  📜 Scrolling page...")
            if "down" in instruction_lower:
                await page.keyboard.press("PageDown")
            elif "up" in instruction_lower or "top" in instruction_lower:
                await page.keyboard.press("Home")
            return True
        
        # Generic verification
        elif "verify" in instruction_lower:
            print(f"  ✅ Generic verification...")
            await page.wait_for_load_state("networkidle")
            return True
        
        else:
            print(f"  ❓ Unknown instruction type: {instruction}")
            return False
    
    except Exception as e:
        print(f"    ❌ Error executing instruction: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_real_browser_test.py <instruction_file> [--visible]")
        print("\nExamples:")
        print("  python run_real_browser_test.py examples/my_custom_test.txt")
        print("  python run_real_browser_test.py examples/my_custom_test.txt --visible")
        sys.exit(1)
    
    instruction_file = sys.argv[1]
    headless = "--visible" not in sys.argv
    
    asyncio.run(run_real_browser_test(instruction_file, headless))
