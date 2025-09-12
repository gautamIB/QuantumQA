#!/usr/bin/env python3
"""
Generic Chrome Testing Engine - Application-agnostic browser automation
No hardcoded selectors or app-specific logic
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from ..parsers.instruction_parser import InstructionParser
from ..finders.element_finder import ElementFinder  
from ..executors.action_executor import ActionExecutor


class ChromeEngine:
    """Generic Chrome testing engine that works with any application."""
    
    def __init__(self, config_dir: Optional[str] = None, credentials_file: Optional[str] = None):
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent / "config"

        # Handle credentials file path
        self.credentials_file = None
        if credentials_file:
            cred_path = Path(credentials_file)
            if cred_path.is_absolute():
                self.credentials_file = cred_path
            else:
                # Relative to project root
                self.credentials_file = Path.cwd() / cred_path

        # Initialize modular components
        self.instruction_parser = InstructionParser(self.config_dir)
        self.element_finder = ElementFinder(self.config_dir)
        self.action_executor = ActionExecutor(self.credentials_file)
        
        # 🧠 CONTEXT TRACKING: Track navigation expectations and step dependencies
        self.navigation_context = {
            "expected_navigation": False,
            "expected_url_pattern": None,
            "last_navigation_step": None,
            "navigation_succeeded": None,
            "current_page_context": "initial"
        }
        
        # Browser instances
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    async def initialize(self, headless: bool = False, viewport: Dict[str, int] = None) -> None:
        """Initialize browser with generic settings."""
        print("🚀 Initializing Generic Chrome Engine...")
        
        self.playwright = await async_playwright().start()
        
        # Launch Google Chrome (not Chromium) for better performance and existing profile access
        self.browser = await self.playwright.chromium.launch(
            channel="chrome",  # Use installed Chrome instead of bundled Chromium
            headless=headless,
            args=[
                "--no-first-run",
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",  # For testing across domains
                "--disable-features=VizDisplayCompositor"
            ]
        )
        
        # Create context with sensible defaults
        viewport = viewport or {'width': 1400, 'height': 900}
        self.context = await self.browser.new_context(
            viewport=viewport,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        
        self.page = await self.context.new_page()
        
        # Enable console logging for debugging
        self.page.on("console", lambda msg: print(f"🟦 Console: {msg.text}"))
        
        print("✅ Generic Chrome Engine initialized")
    
    async def execute_test(self, instruction_file: str) -> Dict[str, Any]:
        """Execute test instructions from file using generic engine."""
        
        # Load and parse instructions generically
        instructions = self._load_instructions(instruction_file)
        print(f"📋 Loaded {len(instructions)} instructions")
        
        results = []
        total_steps = len(instructions)
        
        print("\n🎯 Executing Test Steps:")
        print("=" * 50)
        
        for i, instruction in enumerate(instructions, 1):
            print(f"\n📍 Step {i}/{total_steps}: {instruction}")
            
            try:
                # Parse instruction generically
                action_plan = await self.instruction_parser.parse(instruction)
                print(f"  🔍 Parsed as: {action_plan['action']} -> {action_plan.get('target', 'N/A')}")
                
                # Execute action generically
                success = await self._execute_action(action_plan, step_number=i)
                
                # Record result
                result = {
                    "step": i,
                    "instruction": instruction,
                    "action_plan": action_plan,
                    "status": "success" if success else "failed",
                    "url": self.page.url,
                    "title": await self.page.title()
                }
                
                results.append(result)
                
                if success:
                    print(f"  ✅ Step {i} completed successfully")
                else:
                    print(f"  ❌ Step {i} failed")
                
                # Brief pause between steps
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"  ❌ Step {i} error: {str(e)}")
                results.append({
                    "step": i,
                    "instruction": instruction,
                    "status": "error",
                    "error": str(e),
                    "url": self.page.url,
                    "title": await self.page.title()
                })
        
        # Generate comprehensive report
        return await self._generate_report(results, instruction_file)
    
    async def _execute_action(self, action_plan: Dict[str, Any], step_number: int) -> bool:
        """Execute a single action using generic components."""
        
        action = action_plan["action"]
        
        # 🧠 CONTEXT TRACKING: Update navigation expectations before execution
        self._update_navigation_context(action_plan, step_number)
        
        try:
            if action == "navigate":
                success = await self.action_executor.navigate(self.page, action_plan["url"])
                
            elif action == "click":
                # Find element generically
                element = await self.element_finder.find_clickable_element(
                    self.page, 
                    action_plan["target"],
                    context=action_plan.get("context", {})
                )
                
                if element:
                    # Pass target information to the action executor for dropdown detection
                    click_options = action_plan.get("click_options", {})
                    click_options["target"] = action_plan["target"]  # Pass the target text
                    success = await self.action_executor.click(element, click_options)
                else:
                    print(f"    ❌ Could not find clickable element: {action_plan['target']}")
                    await self._save_debug_screenshot(step_number)
                    success = False
            
            elif action == "type":
                # Find input field generically  
                element = await self.element_finder.find_input_field(
                    self.page,
                    action_plan["field"],
                    field_type=action_plan.get("field_type")
                )
                
                if element:
                    success = await self.action_executor.type_text(element, action_plan["text"])
                else:
                    print(f"    ❌ Could not find input field: {action_plan['field']}")
                    success = False
            
            elif action == "upload":
                file_path = action_plan.get("file_path")
                if file_path:
                    print(f"    📤 Uploading file: {file_path}")
                    success = await self.action_executor.upload_file(self.page, file_path)
                else:
                    print(f"    ❌ No file path provided for upload")
                    success = False
            
            elif action == "send":
                # Enhanced send action - find and click send button with smart waiting
                target = action_plan.get("target", "send")
                element = await self.element_finder.find_clickable_element(self.page, target)
                if element:
                    # Wait for element to be enabled before clicking
                    print(f"    ⏳ Waiting for send button to be enabled...")
                    await self._wait_for_enabled(element, timeout=10000)
                    success = await self.action_executor.click(element)
                else:
                    print(f"    ❌ Could not find send element: {target}")
                    success = False
            
            elif action in ["select", "explore", "test", "confirm", "close"]:
                # Generic target-based actions
                target = action_plan.get("target")
                if target:
                    print(f"    🎯 {action.title()} action on: {target}")
                    element = await self.element_finder.find_clickable_element(self.page, target)
                    if element:
                        success = await self.action_executor.click(element)
                    else:
                        print(f"    ❌ Could not find element for {action}: {target}")
                        success = False
                else:
                    print(f"    ❌ No target specified for {action}")
                    success = False
            
            elif action == "verify":
                # 🧠 CONTEXT-AWARE VERIFICATION: Pass navigation context
                verification_options = action_plan.get("verification_options", {}).copy()
                verification_options["navigation_context"] = self.navigation_context
                verification_options["step_number"] = step_number
                
                success = await self.action_executor.verify(
                    self.page,
                    action_plan["verification_type"],
                    action_plan.get("expected_value"),
                    verification_options
                )
            
            elif action == "wait":
                success = await self.action_executor.wait(
                    self.page,
                    action_plan.get("wait_type", "time"),
                    action_plan.get("duration", 2)
                )
            
            elif action == "comment":
                # Skip comment lines and section headers
                print(f"    📝 Comment/Section: {action_plan.get('raw_instruction', '')}")
                success = True
            
            else:
                print(f"    ❓ Unknown action type: {action}")
                success = False
                
            # 🧠 UPDATE CONTEXT: Track navigation results after execution
            self._update_navigation_result(action_plan, success, step_number)
            
            return success
                
        except Exception as e:
            print(f"    ❌ Action execution error: {e}")
            return False
    
    async def _wait_for_enabled(self, element, timeout: int = 10000) -> bool:
        """Wait for element to become enabled (not disabled)."""
        try:
            # Wait for element to not have disabled attribute
            await element.wait_for(state="attached", timeout=timeout)
            
            # Check if element is enabled by trying to click it (without actually clicking)
            start_time = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - start_time) * 1000 < timeout:
                try:
                    # Check if element is enabled
                    is_disabled = await element.is_disabled()
                    if not is_disabled:
                        print(f"    ✅ Element is now enabled")
                        return True
                    await asyncio.sleep(0.1)
                except:
                    await asyncio.sleep(0.1)
            
            print(f"    ⚠️ Element still disabled after {timeout}ms")
            return False
        except Exception as e:
            print(f"    ⚠️ Wait for enabled error: {e}")
            return False
    
    def _update_navigation_context(self, action_plan: Dict[str, Any], step_number: int):
        """Track when navigation/redirection is expected in upcoming steps."""
        verification_type = action_plan.get("verification_type")
        
        # 🧠 DETECT NAVIGATION EXPECTATIONS
        if verification_type in ["url_redirect_with_patterns", "url_change"]:
            print(f"    🧠 Context: Navigation expected in Step {step_number}")
            self.navigation_context.update({
                "expected_navigation": True,
                "expected_url_pattern": action_plan.get("verification_options", {}),
                "last_navigation_step": step_number,
                "navigation_succeeded": None,  # Will be determined after execution
                "current_page_context": "expecting_navigation"
            })
            
        # 🧠 DETECT ACTIONS THAT SHOULD TRIGGER NAVIGATION
        elif (action_plan.get("action") == "click" and 
              action_plan.get("target", "").lower() in ["chatbot", "create", "new", "add"]):
            print(f"    🧠 Context: Click action may trigger navigation")
            self.navigation_context.update({
                "potential_navigation_trigger": step_number,
                "trigger_action": action_plan.get("target", "")
            })
    
    def _update_navigation_result(self, action_plan: Dict[str, Any], success: bool, step_number: int):
        """Update context based on action results, especially navigation outcomes."""
        verification_type = action_plan.get("verification_type")
        
        # 🧠 TRACK NAVIGATION VERIFICATION RESULTS  
        if verification_type in ["url_redirect_with_patterns", "url_change"]:
            # 🔧 STORE NAVIGATION EXPECTATION for context-aware verification
            expected_pattern_info = {}
            
            if verification_type == "url_redirect_with_patterns":
                # Store prefix/suffix pattern info
                verification_options = action_plan.get("verification_options", {})
                expected_pattern_info = {
                    "pattern_type": "prefix_suffix",
                    "url_prefix": verification_options.get("url_prefix", ""),
                    "url_suffix": verification_options.get("url_suffix", "")
                }
            elif verification_type == "url_change":
                # Store expected value info
                expected_pattern_info = {
                    "pattern_type": "expected_value",
                    "expected_value": action_plan.get("expected_value", "")
                }
            
            self.navigation_context.update({
                "navigation_succeeded": success,
                "current_page_context": "navigation_verified" if success else "navigation_failed",
                "expected_navigation_info": expected_pattern_info
            })
            
            if success:
                print(f"    🧠 Context: Navigation succeeded - now on expected page")
            else:
                print(f"    🧠 Context: Navigation FAILED - still on wrong page!")
                print(f"    🚨 Subsequent page verifications should be context-aware!")
    
    async def _generate_report(self, results: List[Dict], instruction_file: str) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        
        successful_steps = len([r for r in results if r["status"] == "success"])
        total_steps = len(results)
        success_rate = (successful_steps / total_steps * 100) if total_steps > 0 else 0
        
        final_url = self.page.url
        final_title = await self.page.title()
        
        print("\n" + "=" * 60)
        print("📊 GENERIC CHROME ENGINE REPORT") 
        print("=" * 60)
        print(f"📈 Success Rate: {success_rate:.1f}% ({successful_steps}/{total_steps})")
        print(f"🌐 Final URL: {final_url}")
        print(f"📄 Final Title: {final_title}")
        
        # Save final screenshot
        screenshot_path = await self._save_final_screenshot(instruction_file)
        
        report = {
            "instruction_file": instruction_file,
            "total_steps": total_steps,
            "successful_steps": successful_steps,
            "success_rate": success_rate,
            "final_url": final_url,
            "final_title": final_title,
            "screenshot_path": screenshot_path,
            "step_results": results
        }
        
        return report
    
    async def _save_debug_screenshot(self, step_number: int) -> str:
        """Save debug screenshot."""
        Path("test_results").mkdir(exist_ok=True)
        screenshot_path = f"test_results/debug_step_{step_number}.png"
        
        try:
            await self.page.screenshot(path=screenshot_path)
            print(f"    📸 Debug screenshot: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            print(f"    ⚠️ Could not save debug screenshot: {e}")
            return ""
    
    async def _save_final_screenshot(self, instruction_file: str) -> str:
        """Save final test screenshot."""
        Path("test_results").mkdir(exist_ok=True)
        clean_filename = instruction_file.replace('/', '_').replace('.txt', '')
        screenshot_path = f"test_results/final_{clean_filename}.png"
        
        try:
            await self.page.screenshot(path=screenshot_path, full_page=True)
            print(f"📸 Final screenshot: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            print(f"⚠️ Could not save final screenshot: {e}")
            return ""
    
    def _load_instructions(self, instruction_file: str) -> List[str]:
        """Load instructions from file."""
        instruction_path = Path(instruction_file)
        if not instruction_path.exists():
            raise FileNotFoundError(f"Instruction file not found: {instruction_file}")
        
        with open(instruction_path, 'r') as f:
            instructions = [line.strip() for line in f.readlines() if line.strip()]
        
        return instructions
    
    async def cleanup(self):
        """Clean up browser resources."""
        print("\n🛑 Cleaning up browser resources...")
        
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            print("✅ Cleanup completed")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
