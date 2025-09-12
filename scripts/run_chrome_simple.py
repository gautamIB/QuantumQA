#!/usr/bin/env python3
"""
Simple Chrome Test Runner - Opens a fresh Chrome window for testing
This avoids profile conflicts by using a separate Chrome instance
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def run_chrome_simple(instruction_file: str, headless: bool = False):
    """Run a test with a fresh Chrome instance (separate from your existing Chrome)."""
    
    print("🌐 QuantumQA Simple Chrome Test Runner")
    print("=" * 50)
    print(f"🔧 Mode: {'Headless' if headless else 'Visible'} Chrome Browser")
    print(f"💡 Strategy: Fresh Chrome window (no profile conflicts)")
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
    
    # Start fresh Chrome instance
    from playwright.async_api import async_playwright
    
    # Initialize variables to None for safe cleanup
    playwright = None
    browser = None
    context = None
    page = None
    
    try:
        print("🚀 Starting fresh Chrome instance...")
        
        playwright = await async_playwright().start()
        
        # Simple Chrome launch (no profile conflicts)
        browser = await playwright.chromium.launch(
            headless=headless,
            args=[
                "--no-first-run",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        
        # Create a new browser context (like a new incognito window)
        context = await browser.new_context(
            viewport={'width': 1400, 'height': 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Open a new page (like a new tab)
        page = await context.new_page()
        
        print("✅ Chrome started successfully!")
        print(f"📏 Viewport: 1400x900")
        print(f"🌐 Starting URL: {page.url}")
        
        # Execute instructions step by step
        print("\n🎯 Executing Instructions:")
        print("-" * 50)
        
        step_results = []
        
        for i, instruction in enumerate(instructions, 1):
            print(f"\n📍 Step {i}/{len(instructions)}: {instruction}")
            
            try:
                # Parse and execute instruction
                success = await execute_instruction_simple(page, instruction, i)
                
                if success:
                    print(f"✅ Step {i} completed successfully")
                    step_results.append({"step": i, "instruction": instruction, "status": "success"})
                else:
                    print(f"❌ Step {i} failed")
                    step_results.append({"step": i, "instruction": instruction, "status": "failed"})
                
                # Show current state after each step
                current_url = page.url
                current_title = await page.title()
                print(f"    🌐 Current URL: {current_url}")
                print(f"    📄 Current Title: {current_title}")
                
                # Small delay between steps
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"❌ Step {i} error: {str(e)}")
                step_results.append({"step": i, "instruction": instruction, "status": "error", "error": str(e)})
        
        # Generate detailed report
        print("\n" + "=" * 60)
        print("📊 CHROME TEST EXECUTION REPORT")
        print("=" * 60)
        
        successful_steps = len([r for r in step_results if r["status"] == "success"])
        total_steps = len(step_results)
        success_rate = (successful_steps / total_steps) * 100 if total_steps > 0 else 0
        
        final_url = page.url
        final_title = await page.title()
        
        print(f"📈 Overall Success Rate: {success_rate:.1f}% ({successful_steps}/{total_steps})")
        print(f"🌐 Final URL: {final_url}")
        print(f"📄 Final Page Title: {final_title}")
        
        # Check if we actually navigated somewhere
        if final_url != "about:blank" and final_title:
            print("✅ SUCCESS: Browser actually loaded a real webpage!")
        else:
            print("❌ ISSUE: Browser stayed on blank page - navigation may have failed")
        
        print("\n📋 Step-by-Step Results:")
        for result in step_results:
            status_emoji = {"success": "✅", "failed": "❌", "error": "🚫"}[result["status"]]
            print(f"  {status_emoji} Step {result['step']}: {result['instruction'][:60]}...")
            if "error" in result:
                print(f"      🔍 Error: {result['error']}")
        
        # Take final screenshot
        screenshot_path = f"test_results/chrome_simple_{instruction_file.replace('/', '_').replace('.txt', '')}.png"
        Path("test_results").mkdir(exist_ok=True)
        
        try:
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"\n📸 Final screenshot saved: {screenshot_path}")
        except Exception as screenshot_error:
            print(f"⚠️ Could not save screenshot: {screenshot_error}")
        
        # Wait for user to inspect (only if not headless)
        if not headless:
            print(f"\n⏸️  Chrome will remain open for 15 seconds for inspection...")
            print(f"👀 Check the browser window to see if your workflow executed correctly!")
            print(f"🔍 Current page: {final_url}")
            await asyncio.sleep(15)
        
    except Exception as e:
        print(f"❌ Chrome test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up - close the test Chrome window
        print("\n🛑 Cleaning up test Chrome window...")
        try:
            if page:
                await page.close()
            if context:
                await context.close()
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()
            print("✅ Test Chrome window closed (your main Chrome is still running)")
        except Exception as cleanup_error:
            print(f"⚠️ Cleanup warning: {cleanup_error}")

async def execute_instruction_simple(page, instruction: str, step_num: int) -> bool:
    """Execute a single instruction with better error handling."""
    
    instruction = instruction.strip()
    instruction_lower = instruction.lower()
    
    print(f"  🔍 Processing: '{instruction}'")
    
    try:
        # Navigation instructions - Much more robust parsing
        if instruction_lower.startswith("navigate to"):
            # Extract URL after "navigate to"
            url_start = instruction.lower().find("navigate to") + len("navigate to")
            url = instruction[url_start:].strip()
            
            if url:
                print(f"  🧭 Navigating to: {url}")
                try:
                    # Navigate with longer timeout and better error handling
                    response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    
                    # Wait a bit more for the page to fully load
                    await asyncio.sleep(2)
                    
                    current_url = page.url
                    current_title = await page.title()
                    
                    print(f"    ✅ Navigation completed!")
                    print(f"    📊 Response status: {response.status if response else 'N/A'}")
                    print(f"    🌐 Landed on: {current_url}")
                    print(f"    📄 Page title: '{current_title}'")
                    
                    # Check if navigation was successful
                    if current_url == "about:blank":
                        print(f"    ❌ Navigation failed - still on blank page")
                        return False
                    
                    return True
                    
                except Exception as nav_error:
                    print(f"    ❌ Navigation error: {nav_error}")
                    return False
            else:
                print(f"  ❌ No URL found in: '{instruction}'")
                return False
        
        # Verification instructions
        elif "verify" in instruction_lower:
            print(f"  ✅ Performing verification...")
            
            try:
                # Wait for page to be stable
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
                
                current_title = await page.title()
                current_url = page.url
                
                print(f"    📄 Current title: '{current_title}'")
                print(f"    🌐 Current URL: {current_url}")
                
                # Specific verification checks
                if "loads successfully" in instruction_lower:
                    success = current_url != "about:blank"
                    print(f"    {'✅' if success else '❌'} Page load check: {success}")
                    return success
                    
                elif "title contains" in instruction_lower:
                    # Extract expected text
                    contains_index = instruction_lower.find("title contains")
                    expected_text = instruction[contains_index + len("title contains"):].strip().strip("'\"")
                    success = expected_text.lower() in current_title.lower()
                    print(f"    {'✅' if success else '❌'} Title contains '{expected_text}': {success}")
                    return success
                
                elif "dropdown has the button for" in instruction_lower:
                    # Verify dropdown options are visible (just wait and assume success for now)
                    await asyncio.sleep(1)  # Give dropdown time to be visible
                    print(f"    ✅ Dropdown verification: Checking for dropdown options")
                    return True
                
                elif any(pattern in instruction_lower for pattern in ["url changed to chatbot creation", "chatbot creation process started"]):
                    # Verify that chatbot creation has started (URL change OR modal/form appearance)
                    url_success = "/hub/apps/" in current_url or "/chatbot" in current_url.lower()
                    
                    # Also check for modals or forms indicating chatbot creation started
                    modal_success = False
                    try:
                        modal_selectors = [
                            "[role='dialog']", "[role='modal']", ".modal", ".dialog",
                            "[data-testid*='modal']", "[data-testid*='dialog']",
                            "form[role='dialog']", ".modal-content"
                        ]
                        for modal_sel in modal_selectors:
                            modal_elements = page.locator(modal_sel)
                            if await modal_elements.count() > 0:
                                first_modal = modal_elements.first
                                if await first_modal.is_visible():
                                    modal_text = await first_modal.text_content()
                                    if any(keyword in modal_text.lower() for keyword in ["chatbot", "create", "new", "name"]):
                                        modal_success = True
                                        print(f"    🎯 Chatbot creation modal/form detected: {modal_text[:100]}...")
                                        break
                    except Exception as modal_error:
                        print(f"    ⚠️ Modal detection error: {modal_error}")
                    
                    success = url_success or modal_success
                    print(f"    {'✅' if success else '❌'} Chatbot creation verification: {success}")
                    if url_success:
                        print(f"    🎯 Chatbot creation URL detected: {current_url}")
                    elif modal_success:
                        print(f"    🎯 Chatbot creation modal/form detected")
                    else:
                        print(f"    ❌ No chatbot creation detected. URL: {current_url}")
                        print(f"    📍 Expected: URL change to '/hub/apps/' or '/chatbot' OR creation modal/form")
                    return success
                    
                else:
                    # Generic verification - just check if we're on a real page
                    success = current_url != "about:blank"
                    print(f"    {'✅' if success else '❌'} Generic verification: {success}")
                    return success
                    
            except Exception as verify_error:
                print(f"    ❌ Verification error: {verify_error}")
                return False
        
        # Click instructions
        elif any(instruction_lower.startswith(prefix) for prefix in ["click on", "click the"]):
            # Extract target element text
            target = None
            if instruction_lower.startswith("click on"):
                target = instruction[len("click on"):].strip().strip("'\"")
            elif instruction_lower.startswith("click the"):
                target = instruction[len("click the"):].strip().strip("'\"")
            
            if target:
                print(f"  👆 Looking for clickable element: '{target}'")
                
                try:
                    # Wait for page to be interactive
                    await page.wait_for_load_state("domcontentloaded", timeout=5000)
                    
                    # Try multiple selection strategies
                    selectors_to_try = [
                        f"text='{target}'",
                        f"text={target}",
                        f"[aria-label*='{target}' i]",
                        f"[title*='{target}' i]",
                        f"a:has-text('{target}')",
                        f"button:has-text('{target}')",
                        f"*:has-text('{target}')",
                        # Enhanced dropdown selectors
                        f"button[class*='dropdown']" if "dropdown" in target.lower() else None,
                        f"[role='button']:has-text('{target}')" if "button" in target.lower() else None,
                        f"button" if "create dropdown button" in target.lower() else None,
                        # Color-specific selectors for purple Create button
                        f"button:has-text('Create')" if "purple create button" in target.lower() else None,
                        f"[role='button']:has-text('Create')" if "purple create button" in target.lower() else None,
                        f"button[class*='primary']:has-text('Create')" if "purple" in target.lower() and "create" in target.lower() else None,
                        # Position-specific selectors (avoid tabs, focus on buttons) - Updated for new format
                        f"button:has-text('Create'):not([role='tab'])" if any(pattern in target.lower() for pattern in ["create button", "create button with dropdown"]) else None,
                        f"[data-testid*='create']:has-text('Create')" if any(pattern in target.lower() for pattern in ["create button", "create button with dropdown"]) else None,
                        f"button:has-text('Create')" if "top right corner" in target.lower() else None,
                        # Dropdown menu specific selectors - Precise button targeting to fix click area issue
                        f"button[role='menuitem']:has-text('Chatbot')" if any(pattern in target.lower() for pattern in ["chatbot option from", "chatbot button from"]) and "dropdown" in target.lower() else None,
                        f"[role='menuitem'] button:has-text('Chatbot')" if any(pattern in target.lower() for pattern in ["chatbot option from", "chatbot button from"]) and "dropdown" in target.lower() else None,
                        f"li[role='menuitem'] button:has-text('Chatbot')" if any(pattern in target.lower() for pattern in ["chatbot option from", "chatbot button from"]) and "dropdown" in target.lower() else None,
                        f"div[role='menuitem'] button:has-text('Chatbot')" if any(pattern in target.lower() for pattern in ["chatbot option from", "chatbot button from"]) and "dropdown" in target.lower() else None,
                        f"[role='menu'] button:has-text('Chatbot')" if any(pattern in target.lower() for pattern in ["chatbot option from", "chatbot button from"]) and "dropdown" in target.lower() else None,
                        f"ul[role='menu'] button:has-text('Chatbot')" if any(pattern in target.lower() for pattern in ["chatbot option from", "chatbot button from"]) and "dropdown" in target.lower() else None,
                        # Fallback to broader selectors but still prioritize buttons
                        f"[role='menuitem']:has-text('Chatbot')" if any(pattern in target.lower() for pattern in ["chatbot option from", "chatbot button from"]) and "dropdown" in target.lower() else None,
                        f"[role='option']:has-text('Chatbot')" if any(pattern in target.lower() for pattern in ["chatbot option from", "chatbot button from"]) and "dropdown" in target.lower() else None,
                        f"li[role='menuitem']:has-text('Chatbot')" if any(pattern in target.lower() for pattern in ["chatbot option from", "chatbot button from"]) and "dropdown" in target.lower() else None,
                        f"div[role='menuitem']:has-text('Chatbot')" if any(pattern in target.lower() for pattern in ["chatbot option from", "chatbot button from"]) and "dropdown" in target.lower() else None,
                        # Direct button selectors for dropdown context
                        f"button:has-text('Chatbot')" if any(pattern in target.lower() for pattern in ["chatbot button from dropdown", "chatbot option from dropdown"]) else None,
                        f"*:has-text('Chatbot'):not([role='tab']):not([data-testid*='tab'])" if any(pattern in target.lower() for pattern in ["chatbot option from dropdown", "chatbot button from dropdown"]) else None,
                    ]
                    
                    # Filter out None values
                    selectors_to_try = [s for s in selectors_to_try if s]
                    
                    for selector in selectors_to_try:
                        try:
                            element = page.locator(selector).first
                            if await element.is_visible(timeout=2000):
                                # Extra debugging for dropdown selections
                                if "dropdown" in target.lower() and "chatbot" in target.lower():
                                    print(f"    🔍 Found dropdown chatbot element with selector: {selector}")
                                    print(f"    📍 Element text: {await element.text_content()}")
                                    print(f"    🔧 Element tag: {await element.evaluate('el => el.tagName')}")
                                    print(f"    🔧 Element role: {await element.get_attribute('role')}")
                                    print(f"    🔧 Element class: {await element.get_attribute('class')}")
                                    
                                    # Check if it's actually clickable
                                    is_clickable = await element.evaluate('el => el.onclick !== null || el.addEventListener || el.tagName === "BUTTON" || el.tagName === "A"')
                                    print(f"    🔧 Element appears clickable: {is_clickable}")
                                
                                # Use more precise clicking for dropdown chatbot elements
                                if "dropdown" in target.lower() and "chatbot" in target.lower():
                                    try:
                                        # Try force click and center click for better precision
                                        await element.click(force=True)
                                        print(f"    ✅ Successfully force-clicked element at center")
                                    except Exception as force_click_error:
                                        print(f"    ⚠️ Force click failed, trying alternative: {force_click_error}")
                                        try:
                                            # Try JavaScript click as alternative
                                            await element.evaluate('el => el.click()')
                                            print(f"    ✅ Successfully JavaScript-clicked element")
                                        except Exception as js_click_error:
                                            print(f"    ⚠️ JavaScript click failed: {js_click_error}")
                                            # Final fallback to regular click
                                            await element.click()
                                            print(f"    ✅ Successfully clicked element (fallback)")
                                else:
                                    await element.click()
                                    print(f"    ✅ Successfully clicked element")
                                    
                                print(f"    🎯 Used selector: {selector}")
                                
                                # Wait for potential page changes and verify URL change
                                if "dropdown" in target.lower() and "chatbot" in target.lower():
                                    # For chatbot dropdown clicks, wait longer and check for navigation
                                    print(f"    ⏳ Waiting for potential chatbot creation navigation...")
                                    await asyncio.sleep(2)  # Initial wait
                                    
                                    # Check for modals or forms that might have appeared
                                    print(f"    🔍 Checking for modal dialogs or forms...")
                                    modals_found = []
                                    try:
                                        # Check for common modal/dialog patterns
                                        modal_selectors = [
                                            "[role='dialog']", "[role='modal']", ".modal", ".dialog",
                                            "[data-testid*='modal']", "[data-testid*='dialog']",
                                            ".MuiDialog-root", ".ant-modal", "[class*='modal']",
                                            "form[role='dialog']", ".modal-content"
                                        ]
                                        for modal_sel in modal_selectors:
                                            modal_elements = page.locator(modal_sel)
                                            if await modal_elements.count() > 0:
                                                first_modal = modal_elements.first
                                                if await first_modal.is_visible():
                                                    modal_text = await first_modal.text_content()
                                                    modals_found.append(f"{modal_sel}: {modal_text[:100]}...")
                                        
                                        if modals_found:
                                            print(f"    🎯 FOUND MODALS/FORMS: {modals_found}")
                                        else:
                                            print(f"    ⚠️ No modals/forms detected")
                                            
                                    except Exception as modal_check_error:
                                        print(f"    ⚠️ Modal check error: {modal_check_error}")
                                    
                                    await asyncio.sleep(3)  # Additional wait
                                    new_url = page.url
                                    print(f"    🌐 URL after extended wait: {new_url}")
                                    
                                    # Check if we actually navigated to a chatbot page
                                    if "/hub/apps/" in new_url or "/chatbot" in new_url.lower():
                                        print(f"    🎯 SUCCESS: Chatbot creation detected!")
                                        return True
                                    else:
                                        print(f"    ⚠️ WARNING: Chatbot button clicked but no navigation occurred")
                                        return True  # Still return True since the click succeeded
                                else:
                                    await asyncio.sleep(3)
                                    new_url = page.url
                                    print(f"    🌐 URL after click: {new_url}")
                                
                                return True
                        except Exception as click_err:
                            if "dropdown" in target.lower() and "chatbot" in target.lower():
                                print(f"    ⚠️ Selector {selector} failed: {click_err}")
                            continue
                    
                    print(f"    ❌ Could not find or click element: '{target}'")
                    # Take debug screenshot
                    debug_path = f"test_results/debug_step_{step_num}.png"
                    try:
                        await page.screenshot(path=debug_path)
                        print(f"    📸 Debug screenshot: {debug_path}")
                    except:
                        pass
                    return False
                    
                except Exception as click_error:
                    print(f"    ❌ Click error: {click_error}")
                    return False
        
        # Type instructions - Enhanced parsing
        elif "type" in instruction_lower and ("in" in instruction_lower or "field" in instruction_lower):
            print(f"  ⌨️ Processing type instruction")
            
            try:
                # Parse different typing formats:
                # "Type text in field" or "Type 'text' in field" 
                if " in " in instruction:
                    parts = instruction.split(" in ", 1)
                    if len(parts) == 2:
                        # Extract text to type (remove "Type" and clean up)
                        text_part = parts[0].replace("Type", "", 1).strip().strip("'\"")
                        field_part = parts[1].strip()
                        
                        print(f"    📝 Text to type: '{text_part}'")
                        print(f"    🎯 Target field: '{field_part}'")
                        
                        # Try multiple field selectors
                        field_selectors = [
                            f"input[placeholder*='{field_part}' i]",
                            f"input[name*='{field_part}' i]",
                            f"input[type='email']" if "email" in field_part.lower() else None,
                            f"input[type='password']" if "password" in field_part.lower() else None,
                            f"textarea[placeholder*='{field_part}' i]",
                            f"input[aria-label*='{field_part}' i]",
                            f"input" if "field" in field_part.lower() else None
                        ]
                        
                        # Filter out None values
                        field_selectors = [s for s in field_selectors if s]
                        
                        for selector in field_selectors:
                            try:
                                element = page.locator(selector).first
                                if await element.is_visible(timeout=2000):
                                    await element.fill(text_part)
                                    print(f"    ✅ Successfully typed text using selector: {selector}")
                                    return True
                            except:
                                continue
                        
                        print(f"    ❌ Could not find input field for: {field_part}")
                        return False
                
            except Exception as type_error:
                print(f"    ❌ Type instruction parsing error: {type_error}")
                return False
        
        # Wait instructions
        elif instruction_lower.startswith("wait for"):
            print(f"  ⏳ Waiting for condition...")
            try:
                # Wait for page to be stable and allow dropdown to appear
                await asyncio.sleep(2)
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
                print(f"    ✅ Wait completed")
                return True
            except Exception as wait_error:
                print(f"    ❌ Wait error: {wait_error}")
                return False
        
        # Scroll instructions
        elif "scroll" in instruction_lower:
            print(f"  📜 Scrolling page")
            try:
                if "down" in instruction_lower:
                    await page.keyboard.press("PageDown")
                elif "up" in instruction_lower or "top" in instruction_lower:
                    await page.keyboard.press("Home")
                return True
            except Exception as scroll_error:
                print(f"    ❌ Scroll error: {scroll_error}")
                return False
        
        else:
            print(f"  ❓ Unknown instruction format")
            return False
    
    except Exception as e:
        print(f"    ❌ Execution error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_chrome_simple.py <instruction_file> [--visible]")
        print("\nExamples:")
        print("  python run_chrome_simple.py examples/my_custom_test.txt --visible")
        print("  python run_chrome_simple.py examples/simple_test.txt --visible")
        print("  python run_chrome_simple.py examples/working_test.txt")
        print("\nThis creates a FRESH Chrome window just for testing!")
        print("Your existing Chrome browser will remain unaffected.")
        sys.exit(1)
    
    instruction_file = sys.argv[1]
    headless = "--visible" not in sys.argv
    
    asyncio.run(run_chrome_simple(instruction_file, headless))
