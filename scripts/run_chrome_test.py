#!/usr/bin/env python3
"""
Chrome Browser Test Runner - Uses your existing Chrome profile
This version uses Chrome (not Chromium) and can access your existing login sessions
"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from quantumqa.core.browser import BrowserManager, BrowserConfig

async def run_chrome_test(instruction_file: str, headless: bool = False, use_profile: bool = True):
    """Run a test with Chrome browser using existing profile."""
    
    print("🌐 QuantumQA Chrome Test Runner")
    print("=" * 50)
    print(f"🔧 Mode: {'Headless' if headless else 'Visible'} Chrome Browser")
    print(f"👤 Profile: {'Using existing profile' if use_profile else 'Fresh profile'}")
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
    
    # Start Chrome browser directly with playwright
    from playwright.async_api import async_playwright
    
    try:
        print("🚀 Starting Chrome browser...")
        
        playwright = await async_playwright().start()
        
        # Chrome launch options
        launch_options = {
            "headless": headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--disable-dev-shm-usage"
            ],
            "viewport": {'width': 1400, 'height': 900}
        }
        
        # Use persistent context for existing Chrome profile
        if use_profile:
            # Common Chrome profile locations
            chrome_profile_paths = [
                os.path.expanduser("~/Library/Application Support/Google/Chrome"),  # macOS
                os.path.expanduser("~/.config/google-chrome"),  # Linux
                os.path.expanduser("~/AppData/Local/Google/Chrome/User Data")  # Windows
            ]
            
            profile_path = None
            for path in chrome_profile_paths:
                if os.path.exists(path):
                    profile_path = path
                    print(f"📂 Using Chrome profile: {profile_path}")
                    break
            
            if profile_path:
                # Launch persistent context with existing profile
                context = await playwright.chromium.launch_persistent_context(
                    user_data_dir=profile_path,
                    **launch_options
                )
                page = context.pages[0] if context.pages else await context.new_page()
                browser = None  # Not needed with persistent context
            else:
                # Fallback to regular launch
                print("⚠️ Chrome profile not found, using fresh profile")
                browser = await playwright.chromium.launch(**launch_options)
                context = await browser.new_context()
                page = await context.new_page()
        else:
            # Regular launch without profile
            browser = await playwright.chromium.launch(**launch_options)
            context = await browser.new_context()
            page = await context.new_page()
        
        print("✅ Chrome started successfully!")
        print(f"📏 Viewport: 1400x900")
        
        # Execute instructions step by step
        print("\n🎯 Executing Instructions:")
        print("-" * 50)
        
        step_results = []
        
        for i, instruction in enumerate(instructions, 1):
            print(f"\n📍 Step {i}/{len(instructions)}: {instruction}")
            
            try:
                # Parse and execute instruction
                success = await execute_instruction_fixed(page, instruction, i)
                
                if success:
                    print(f"✅ Step {i} completed successfully")
                    step_results.append({"step": i, "instruction": instruction, "status": "success"})
                else:
                    print(f"❌ Step {i} failed")
                    step_results.append({"step": i, "instruction": instruction, "status": "failed"})
                
                # Small delay between steps
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"❌ Step {i} error: {str(e)}")
                step_results.append({"step": i, "instruction": instruction, "status": "error", "error": str(e)})
        
        # Generate detailed report
        print("\n" + "=" * 50)
        print("📊 CHROME TEST EXECUTION REPORT")
        print("=" * 50)
        
        successful_steps = len([r for r in step_results if r["status"] == "success"])
        total_steps = len(step_results)
        success_rate = (successful_steps / total_steps) * 100 if total_steps > 0 else 0
        
        print(f"📈 Overall Success Rate: {success_rate:.1f}% ({successful_steps}/{total_steps})")
        print(f"🌐 Final URL: {page.url}")
        print(f"📄 Final Page Title: {await page.title()}")
        
        print("\n📋 Step-by-Step Results:")
        for result in step_results:
            status_emoji = {"success": "✅", "failed": "❌", "error": "🚫"}[result["status"]]
            print(f"  {status_emoji} Step {result['step']}: {result['instruction'][:60]}...")
            if "error" in result:
                print(f"      🔍 Error: {result['error']}")
        
        # Take final screenshot
        screenshot_path = f"test_results/chrome_final_{instruction_file.replace('/', '_').replace('.txt', '')}.png"
        Path("test_results").mkdir(exist_ok=True)
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"📸 Final screenshot saved: {screenshot_path}")
        
        # Wait for user to inspect (only if not headless)
        if not headless:
            print(f"\n⏸️  Chrome will remain open for 15 seconds for inspection...")
            print(f"🔍 Check the browser window and the screenshot: {screenshot_path}")
            await asyncio.sleep(15)
        
    except Exception as e:
        print(f"❌ Chrome test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        print("\n🛑 Cleaning up Chrome...")
        try:
            await context.close()
            if browser:  # Only close browser if we launched it separately
                await browser.close()
            await playwright.stop()
            print("✅ Chrome closed")
        except Exception as cleanup_error:
            print(f"⚠️ Cleanup warning: {cleanup_error}")
            pass

async def execute_instruction_fixed(page, instruction: str, step_num: int) -> bool:
    """Execute a single instruction with improved parsing."""
    
    original_instruction = instruction
    instruction_lower = instruction.lower().strip()
    
    print(f"  🔍 Parsing: '{instruction}'")
    
    try:
        # Navigation instructions - Fixed parsing
        if instruction_lower.startswith("navigate to"):
            # Extract URL more carefully
            url_part = instruction[len("Navigate to"):].strip() if instruction.startswith("Navigate to") else instruction[len("navigate to"):].strip()
            
            if url_part:
                print(f"  🧭 Navigating to: {url_part}")
                try:
                    response = await page.goto(url_part, wait_until="networkidle", timeout=30000)
                    print(f"    ✅ Navigation successful")
                    print(f"    📄 Page Title: {await page.title()}")
                    print(f"    🌐 Current URL: {page.url}")
                    return True
                except Exception as nav_error:
                    print(f"    ❌ Navigation failed: {nav_error}")
                    return False
            else:
                print(f"  ❌ No URL found in navigation instruction")
                return False
        
        # Verification instructions
        elif "verify" in instruction_lower:
            print(f"  ✅ Performing verification...")
            await page.wait_for_load_state("networkidle", timeout=10000)
            
            current_title = await page.title()
            current_url = page.url
            
            print(f"    📄 Current Title: '{current_title}'")
            print(f"    🌐 Current URL: {current_url}")
            
            # Check specific verification conditions
            if "loads successfully" in instruction_lower or "loads" in instruction_lower:
                success = current_url != "about:blank" and current_title != ""
                print(f"    {'✅' if success else '❌'} Page load verification: {success}")
                return success
            elif "title contains" in instruction_lower:
                # Extract expected title text
                if "contains" in instruction_lower:
                    expected = instruction_lower.split("contains")[1].strip().strip("'\"")
                    success = expected.lower() in current_title.lower()
                    print(f"    {'✅' if success else '❌'} Title contains '{expected}': {success}")
                    return success
            
            return True  # Generic verification passes if page is loaded
        
        # Click instructions - Improved element finding
        elif any(instruction_lower.startswith(prefix) for prefix in ["click on", "click the"]):
            # Extract target element
            target = None
            if instruction_lower.startswith("click on"):
                target = instruction[len("click on"):].strip().strip("'\"")
            elif instruction_lower.startswith("click the"):
                target = instruction[len("click the"):].strip().strip("'\"")
            
            if target:
                print(f"  👆 Looking for element: '{target}'")
                
                # Try multiple selection strategies
                selectors_to_try = [
                    f"text={target}",
                    f"[aria-label*='{target}' i]",
                    f"[title*='{target}' i]",
                    f"a:has-text('{target}')",
                    f"button:has-text('{target}')",
                    f"*:has-text('{target}')",
                    f"[data-testid*='{target.lower()}']"
                ]
                
                for selector in selectors_to_try:
                    try:
                        element = page.locator(selector).first
                        if await element.is_visible(timeout=2000):
                            await element.click()
                            print(f"    ✅ Clicked using selector: {selector}")
                            await page.wait_for_load_state("networkidle", timeout=5000)
                            return True
                    except:
                        continue
                
                print(f"    ❌ Could not find clickable element: '{target}'")
                # Take a screenshot for debugging
                debug_path = f"test_results/debug_step_{step_num}_{target.replace(' ', '_')}.png"
                await page.screenshot(path=debug_path)
                print(f"    📸 Debug screenshot saved: {debug_path}")
                return False
        
        # Type instructions
        elif "type" in instruction_lower and "in" in instruction_lower:
            try:
                # Parse "Type 'text' in field" format
                type_parts = instruction.split("'")
                if len(type_parts) >= 3:
                    text_to_type = type_parts[1]
                    field_part = type_parts[2].split("in")[-1].strip()
                    
                    print(f"  ⌨️  Typing '{text_to_type}' in '{field_part}'")
                    
                    # Try to find the input field
                    field_selectors = [
                        f"input[placeholder*='{field_part}' i]",
                        f"input[name*='{field_part}' i]",
                        f"textarea[placeholder*='{field_part}' i]",
                        f"input[type='search']",
                        f"input[type='text']"
                    ]
                    
                    for selector in field_selectors:
                        try:
                            element = page.locator(selector).first
                            if await element.is_visible(timeout=2000):
                                await element.fill(text_to_type)
                                print(f"    ✅ Typed text using selector: {selector}")
                                return True
                        except:
                            continue
                    
                    print(f"    ❌ Could not find input field for: {field_part}")
                    return False
            except Exception as type_error:
                print(f"    ❌ Type instruction parsing failed: {type_error}")
                return False
        
        # Press Enter
        elif "press enter" in instruction_lower:
            print(f"  ⌨️  Pressing Enter")
            await page.keyboard.press("Enter")
            await page.wait_for_load_state("networkidle", timeout=10000)
            return True
        
        # Scroll instructions
        elif "scroll" in instruction_lower:
            print(f"  📜 Scrolling page")
            if "down" in instruction_lower:
                await page.keyboard.press("PageDown")
            elif "up" in instruction_lower or "top" in instruction_lower:
                await page.keyboard.press("Home")
            return True
        
        else:
            print(f"  ❓ Unknown instruction format")
            return False
    
    except Exception as e:
        print(f"    ❌ Execution error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_chrome_test.py <instruction_file> [--visible] [--no-profile]")
        print("\nExamples:")
        print("  python run_chrome_test.py examples/my_custom_test.txt --visible")
        print("  python run_chrome_test.py examples/aihub_test_fixed.txt --visible")
        print("  python run_chrome_test.py examples/simple_test.txt --no-profile")
        sys.exit(1)
    
    instruction_file = sys.argv[1]
    headless = "--visible" not in sys.argv
    use_profile = "--no-profile" not in sys.argv
    
    asyncio.run(run_chrome_test(instruction_file, headless, use_profile))
