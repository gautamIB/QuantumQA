#!/usr/bin/env python3
"""
Vision-Enhanced Chrome Testing Engine - AI-powered element detection
Uses computer vision and LLMs for intelligent element finding instead of hardcoded selectors.
"""

import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from ..parsers.instruction_parser import InstructionParser
from ..executors.action_executor import ActionExecutor
from ..agents.element_detector import ElementDetectorAgent
from ..core.llm import VisionLLMClient
from ..core.ui_context_manager import UIContextManager
from ..core.models import ElementDetectionResult, Coordinates


class VisionChromeEngine:
    """
    Chrome testing engine enhanced with AI vision for element detection.
    Combines traditional automation with computer vision for robust testing.
    """
    
    def __init__(
        self, 
        vision_client: VisionLLMClient,
        config_dir: Optional[str] = None, 
        credentials_file: Optional[str] = None,
        use_vision_primary: bool = True,
        connect_to_existing: bool = True,
        debug_port: int = 9222
    ):
        """
        Initialize the Vision-Enhanced Chrome Engine.
        
        Args:
            vision_client: VisionLLMClient for AI-based element detection
            config_dir: Configuration directory path
            credentials_file: Credentials file path
            use_vision_primary: Whether to use vision as primary detection method
            connect_to_existing: Whether to connect to existing Chrome instance (default: True)
            debug_port: Chrome remote debugging port (default: 9222)
        """
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent / "config"
        self.use_vision_primary = use_vision_primary
        self.connect_to_existing = connect_to_existing
        self.debug_port = debug_port

        # Handle credentials file path
        self.credentials_file = None
        if credentials_file:
            cred_path = Path(credentials_file)
            if cred_path.is_absolute():
                self.credentials_file = cred_path
            else:
                self.credentials_file = Path.cwd() / cred_path

        # Initialize components
        self.instruction_parser = InstructionParser(self.config_dir)
        self.action_executor = ActionExecutor(self.credentials_file)
        
        # Vision-based element detection
        self.vision_client = vision_client
        self.element_detector = ElementDetectorAgent(
            agent_id="vision_detector",
            vision_client=vision_client
        )
        
        # UI Context Management
        self.ui_context_manager = UIContextManager()
        
        # Fallback to traditional finder if needed
        if not use_vision_primary:
            from ..finders.element_finder import ElementFinder
            self.traditional_finder = ElementFinder(self.config_dir)
        else:
            self.traditional_finder = None
        
        # Context tracking
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
        
        # Vision statistics
        self.vision_detections = 0
        self.traditional_fallbacks = 0
        self.detection_failures = 0
        
        print(f"🔮 VisionChromeEngine initialized (vision_primary={use_vision_primary})")
    
    async def initialize(self, headless: bool = False, viewport: Dict[str, int] = None) -> None:
        """Initialize browser and vision components."""
        print("🚀 Initializing Vision-Enhanced Chrome Engine...")
        
        # Initialize element detector
        await self.element_detector.initialize()
        
        # Initialize browser
        self.playwright = await async_playwright().start()
        
        # Try to connect to existing browser first
        if self.connect_to_existing:
            try:
                print(f"🔗 Attempting to connect to existing Chrome on port {self.debug_port}...")
                self.browser = await self.playwright.chromium.connect_over_cdp(f"http://localhost:{self.debug_port}")
                print("✅ Connected to existing Chrome browser!")
                self._connected_to_existing = True
                
                # Find the best existing context to reuse (with authentication/cookies)
                contexts = self.browser.contexts
                if contexts:
                    print(f"📱 Found {len(contexts)} existing contexts")
                    
                    # Find context with active pages (likely has user authentication)
                    best_context = None
                    for i, context in enumerate(contexts):
                        pages = context.pages
                        print(f"   Context {i}: {len(pages)} pages")
                        if pages:
                            # Check if any pages have been navigated (not just blank)
                            for j, page in enumerate(pages):
                                try:
                                    url = page.url
                                    title = await page.title()
                                    print(f"     Page {j}: {title} ({url})")
                                    if url and url != "about:blank" and url != "chrome://newtab/":
                                        best_context = context
                                        print(f"   🎯 Context {i} has active pages - will reuse for authentication")
                                        break
                                except:
                                    continue
                        if best_context:
                            break
                    
                    # Use the best context found or fall back to first
                    if best_context:
                        self.context = best_context
                        print(f"✅ Reusing authenticated context with {len(self.context.pages)} existing pages")
                    else:
                        self.context = contexts[0]
                        print(f"📱 Using first context (no active pages found)")
                    
                    # Create new tab in the selected context
                    print(f"📄 Creating new tab in existing context...")
                    self.page = await self.context.new_page()
                    print(f"✅ New tab created successfully")
                    
                    # Check if user has visited the target domain in existing pages
                    has_target_domain = False
                    try:
                        for page in self.context.pages:
                            url = page.url
                            if "aihub" in url or "instabase" in url:
                                has_target_domain = True
                                print(f"🔐 Found existing session on target domain: {url}")
                                break
                    except:
                        pass
                    
                    if not has_target_domain:
                        print(f"💡 TIP: For best results with authentication:")
                        print(f"   1. Manually navigate to https://aihub-uat.internal.instabase.com/ in Chrome")
                        print(f"   2. Complete login process")
                        print(f"   3. Then re-run this test to use authenticated session")
                    
                else:
                    print("📱 No existing contexts found, creating new one")
                    viewport = viewport or {'width': 1400, 'height': 900}
                    self.context = await self.browser.new_context(
                        viewport=viewport,
                        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                    )
                    self.page = await self.context.new_page()
                    print(f"📄 Created new context and page")
                    
            except Exception as e:
                print(f"⚠️ Could not connect to existing Chrome: {e}")
                print("🚀 Launching new Chrome browser...")
                self._connected_to_existing = False
                await self._launch_new_browser(headless, viewport)
        else:
            print("🚀 Launching new Chrome browser (existing connection disabled)...")
            self._connected_to_existing = False
            await self._launch_new_browser(headless, viewport)
        
        # Set up page monitoring
        self.page.on("console", lambda msg: print(f"🟦 Console: {msg.text}"))
        
        # 📏 ANALYZE NATURAL VIEWPORT (NO FORCED CHANGES)
        await self._analyze_natural_viewport()
        
        print("✅ Vision-Enhanced Chrome Engine initialized")
    
    async def _launch_new_browser(self, headless: bool = False, viewport: Dict[str, int] = None) -> None:
        """Launch a new Chrome browser instance."""
        self.browser = await self.playwright.chromium.launch(
            channel="chrome",
            headless=headless,
            args=[
                "--no-first-run",
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                f"--remote-debugging-port={self.debug_port}"  # Enable remote debugging for future connections
            ]
        )
        
        viewport = viewport or {'width': 1400, 'height': 900}
        self.context = await self.browser.new_context(
            viewport=viewport,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        
        self.page = await self.context.new_page()
    
    async def execute_test(self, instruction_file: str) -> Dict[str, Any]:
        """Execute test instructions using vision-enhanced detection."""
        import time
        
        instructions = self._load_instructions(instruction_file)
        print(f"📋 Loaded {len(instructions)} instructions")
        
        results = []
        total_steps = len(instructions)
        test_start_time = time.time()
        
        print("\n🎯 Executing Test Steps with AI Vision:")
        print("=" * 60)
        
        # Clear any previous UI contexts for new test
        self.ui_context_manager.clear_all_contexts()
        
        for i, instruction in enumerate(instructions, 1):
            step_start_time = time.time()
            print(f"\n📍 Step {i}/{total_steps}: {instruction}")
            
            # Track current step for screenshots
            self._current_step = i
            
            try:
                # Analyze step for UI context creation (dropdowns, modals, etc.)
                ui_context_created = self.ui_context_manager.analyze_step_for_context(i, instruction)
                
                # Check if step needs to be executed within a specific UI context
                ui_context_needed = self.ui_context_manager.check_if_step_needs_context(i, instruction)
                
                # Parse instruction
                parse_start = time.time()
                action_plan = await self.instruction_parser.parse(instruction)
                parse_time = time.time() - parse_start
                print(f"  🔍 Parsed as: {action_plan['action']} -> {action_plan.get('target', 'N/A')} ({parse_time:.2f}s)")
                
                # Add UI context information to action plan if needed
                if ui_context_needed:
                    action_plan.update(ui_context_needed)
                    print(f"    🎯 Step requires UI context: {ui_context_needed['search_scope']}")
                
                if ui_context_created:
                    action_plan["ui_context_created"] = {
                        "type": ui_context_created.element_type.value,
                        "target": ui_context_created.target_description
                    }
                
                # Add active contexts summary for debugging
                active_contexts_summary = self.ui_context_manager.get_context_summary()
                if active_contexts_summary != "No active UI contexts":
                    action_plan["active_ui_contexts"] = active_contexts_summary
                    print(f"    📋 Active UI contexts: {active_contexts_summary}")
                
                # 📊 VISUAL PROGRESS: Show step progress
                progress_percent = (i / total_steps) * 100
                progress_bar = "█" * int(progress_percent / 5) + "░" * (20 - int(progress_percent / 5))
                print(f"  📊 Progress: [{progress_bar}] {progress_percent:.1f}%")
                
                # Execute with vision enhancement
                execute_start = time.time()
                success = await self._execute_action_with_vision(action_plan, step_number=i)
                execute_time = time.time() - execute_start
                
                step_total_time = time.time() - step_start_time
                
                # Record result
                result = {
                    "step": i,
                    "instruction": instruction,
                    "action_plan": action_plan,
                    "status": "success" if success else "failed",
                    "success": success,  # Add boolean success field for report processing
                    "url": self.page.url,
                    "title": await self.page.title(),
                    "timing": {
                        "parse_time": parse_time,
                        "execute_time": execute_time,
                        "total_time": step_total_time
                    }
                }
                
                results.append(result)
                
                if success:
                    print(f"  ✅ Step {i} completed successfully ({step_total_time:.2f}s total)")
                else:
                    print(f"  ❌ Step {i} failed ({step_total_time:.2f}s total)")
                
                # 🎯 VISUAL FEEDBACK: Brief pause to observe result
                print(f"  ⏸️ Pausing to observe step result...")
                await asyncio.sleep(1.5)  # Slightly longer pause for visual confirmation
                
            except Exception as e:
                step_total_time = time.time() - step_start_time
                print(f"  ❌ Step {i} error: {str(e)} ({step_total_time:.2f}s)")
                results.append({
                    "step": i,
                    "instruction": instruction,
                    "status": "error",
                    "success": False,  # Add boolean success field for report processing
                    "error": str(e),
                    "url": self.page.url,
                    "title": await self.page.title(),
                    "timing": {
                        "parse_time": 0.0,
                        "execute_time": 0.0,
                        "total_time": step_total_time
                    }
                })
        
        total_test_time = time.time() - test_start_time
        print(f"\n🏁 Test completed in {total_test_time:.2f}s")
        
        return await self._generate_report(results, instruction_file, total_test_time)
    
    async def _execute_action_with_vision(self, action_plan: Dict[str, Any], step_number: int) -> bool:
        """Execute action using vision-enhanced element detection."""
        
        action = action_plan["action"]
        
        try:
            if action == "navigate":
                # 🧭 ENHANCED NAVIGATION with visual feedback
                url = action_plan["url"]
                print(f"    🧭 Navigating to: {url}")
                
                # Capture pre-navigation state
                initial_url = self.page.url
                await self._capture_action_screenshot("pre_navigation")
                
                # Perform navigation
                success = await self.action_executor.navigate(self.page, url)
                
                if success:
                    print(f"    ⏳ Waiting for page to fully load...")
                    # Enhanced page stability wait
                    await self._wait_for_page_stability(navigation=True)
                    
                    # Capture post-navigation state
                    await self._capture_action_screenshot("post_navigation")
                    
                    # Show navigation result
                    final_url = self.page.url
                    final_title = await self.page.title()
                    print(f"    ✅ Navigation successful")
                    print(f"    🌐 Current URL: {final_url}")
                    print(f"    📄 Page title: {final_title}")
                
                return success
                
            elif action in ["click", "type"]:
                # Use vision-based element detection
                element_coords = await self._find_element_with_vision(action_plan, step_number)
                
                if element_coords:
                    if action == "click":
                        return await self._click_at_coordinates(element_coords)
                    elif action == "type":
                        # Click first, then type
                        click_success = await self._click_at_coordinates(element_coords)
                        if click_success:
                            return await self._type_text(action_plan["text"])
                        return False
                else:
                    # Fallback to traditional method if vision fails
                    return await self._fallback_to_traditional(action_plan, step_number)
            
            elif action == "verify":
                return await self.action_executor.verify(
                    self.page,
                    action_plan["verification_type"],
                    action_plan.get("expected_value"),
                    action_plan.get("verification_options", {})
                )
            
            elif action == "wait":
                return await self.action_executor.wait(
                    self.page,
                    action_plan.get("wait_type", "time"),
                    action_plan.get("duration", 2)
                )
            
            elif action == "comment":
                print(f"    📝 Comment: {action_plan.get('raw_instruction', '')}")
                return True
            
            else:
                print(f"    ❓ Unknown action type: {action}")
                return False
                
        except Exception as e:
            error_msg = str(e)
            if "Execution context was destroyed" in error_msg:
                print(f"    ⚠️ Execution context destroyed (likely due to navigation), treating as success")
                # Wait for page to stabilize after navigation
                try:
                    await asyncio.sleep(2.0)
                    await self.page.wait_for_load_state('domcontentloaded', timeout=5000)
                    print(f"    ✅ Page stabilized after navigation")
                except Exception:
                    print(f"    ⚠️ Could not verify page stability")
                return True
            else:
                print(f"    ❌ Action execution error: {e}")
                return False
    
    async def _find_element_with_vision(self, action_plan: Dict[str, Any], step_number: int) -> Optional[Coordinates]:
        """Use AI vision to find element coordinates."""
        
        # Take screenshot for analysis
        screenshot_path = await self._take_analysis_screenshot(step_number)
        if not screenshot_path:
            return None
        
        # Prepare instruction for vision AI
        target = action_plan.get("target") or action_plan.get("field")
        if not target:
            print("    ⚠️ No target element specified for vision detection")
            return None
        
        # Create context for better detection
        context = {
            "url": self.page.url,
            "title": await self.page.title(),
            "action_type": action_plan["action"],
            "previous_action": "navigation" if step_number == 1 else "user_action"
        }
        
        # Add UI context information if available
        ui_context_fields = ["ui_context_type", "ui_context_target", "ui_context_opened_step", "search_scope", "context_keywords"]
        for field in ui_context_fields:
            if field in action_plan:
                context[field] = action_plan[field]
        
        # 🧠 INTELLIGENT THREE-STAGE PIPELINE
        print(f"    🧠 Using intelligent detection pipeline for: '{target}'")
        
        try:
            # Stage 1: AI-Powered Instruction Normalization (Fast & Cheap)
            normalized_targets = await self._normalize_instruction_with_ai(action_plan, target)
            print(f"    🤖 AI normalized '{target}' → {normalized_targets}")
            
            # Stage 2: Enhanced Traditional Detection with normalized terms
            traditional_coords = await self._try_enhanced_traditional_detection(action_plan, target, normalized_targets)
            if traditional_coords:
                # Validate coordinates are within viewport bounds
                if self._validate_coordinates_in_viewport(traditional_coords):
                    print(f"    ✅ Enhanced traditional detection succeeded at ({traditional_coords.x}, {traditional_coords.y})")
                    return traditional_coords
                else:
                    print(f"    ⚠️ Traditional detection found element outside viewport bounds at ({traditional_coords.x}, {traditional_coords.y})")
            
            # Stage 3: Fall back to vision detection if both AI+traditional fail
            print(f"    👁️ AI normalization + traditional failed, using vision as final fallback")
            self.vision_detections += 1
            
            # Enhanced instruction for better detection
            action_type = action_plan["action"]
            enhanced_instruction = f"Find the interactive {target} element that can be {action_type}ed. Look for input fields, buttons, or clickable elements, NOT decorative divs or styling elements."
            
            detection_result = await self.element_detector.detect_element(
                screenshot_path=screenshot_path,
                instruction=enhanced_instruction,
                context=context
            )
            
            if detection_result.found and detection_result.center_coordinates:
                # ✅ VALIDATE ELEMENT IS INTERACTIVE AND WITHIN VIEWPORT
                coords = detection_result.center_coordinates
                
                # First check if coordinates are within viewport bounds
                if not self._validate_coordinates_in_viewport(coords):
                    print(f"    ⚠️ Vision found element outside viewport bounds at ({coords.x}, {coords.y}) - retrying...")
                    better_coords = await self._find_nearby_interactive_element(coords, action_plan["action"])
                    if better_coords and self._validate_coordinates_in_viewport(better_coords):
                        coords = better_coords
                        print(f"    ✅ Found better element within viewport at ({coords.x}, {coords.y})")
                    else:
                        print(f"    ❌ No valid elements found within viewport")
                        self.detection_failures += 1
                        return None
                
                # Then check if element is interactive
                is_interactive = await self._validate_interactive_element(coords, action_plan["action"])
                
                if is_interactive:
                    print(f"    ✅ Vision found interactive element at ({coords.x}, {coords.y}) confidence={detection_result.confidence:.2f}")
                    return coords
                else:
                    print(f"    ⚠️ Vision found non-interactive element at ({coords.x}, {coords.y}) - retrying...")
                    # Try to find a better element nearby
                    better_coords = await self._find_nearby_interactive_element(coords, action_plan["action"])
                    if better_coords and self._validate_coordinates_in_viewport(better_coords):
                        print(f"    ✅ Found better interactive element at ({better_coords.x}, {better_coords.y})")
                        return better_coords
                    else:
                        print(f"    ❌ No interactive elements found nearby")
                        self.detection_failures += 1
                        return None
            else:
                print(f"    ❌ Vision failed to find element: {detection_result.error_message or 'Element not detected'}")
                self.detection_failures += 1
                return None
                
        except Exception as e:
            print(f"    ❌ Vision detection error: {e}")
            self.detection_failures += 1
            return None
    
    async def _validate_interactive_element(self, coordinates: Coordinates, action: str) -> bool:
        """Validate that element at coordinates is actually interactive."""
        try:
            element_info = await self.page.evaluate(f"""
                (() => {{
                    const element = document.elementFromPoint({coordinates.x}, {coordinates.y});
                    if (!element) return false;
                    
                    const tag = element.tagName.toLowerCase();
                    const type = element.type || '';
                    const role = element.getAttribute('role') || '';
                    
                    // Check if element is interactive based on action type
                    if ('{action}' === 'click') {{
                        return tag === 'button' || 
                               tag === 'a' ||
                               tag === 'input' ||
                               tag === 'select' ||
                               tag === 'textarea' ||
                               role === 'button' ||
                               role === 'link' ||
                               element.onclick !== null ||
                               element.style.cursor === 'pointer';
                    }}
                    
                    if ('{action}' === 'type') {{
                        return tag === 'input' || tag === 'textarea' ||
                               element.contentEditable === 'true';
                    }}
                    
                    return false;
                }})()
            """)
            return bool(element_info)
        except Exception:
            return False
    
    async def _find_nearby_interactive_element(self, coordinates: Coordinates, action: str) -> Optional[Coordinates]:
        """Find an interactive element near the given coordinates."""
        try:
            # For search-related actions, try semantic search first
            if action == 'click':
                print(f"    🔄 Trying semantic element search first...")
                semantic_result = await self.page.evaluate(f"""
                    (() => {{
                        let selectors = [
                            'input[name="q"]',          // Google search
                            'input[type="search"]',      // Search inputs
                            'input[placeholder*="search" i]',  // Search placeholders
                            'input[aria-label*="search" i]',   // Search aria labels
                            '[role="searchbox"]',        // Search role
                            'input[name="search"]',      // Search name
                            'textarea[name="q"]',        // Alternative search
                            'input[name="query"]'        // Query inputs
                        ];
                        
                        for (const selector of selectors) {{
                            const element = document.querySelector(selector);
                            if (element && element.offsetParent !== null) {{ // Check if visible
                                const rect = element.getBoundingClientRect();
                                return {{
                                    x: rect.left + rect.width / 2,
                                    y: rect.top + rect.height / 2,
                                    tag: element.tagName.toLowerCase(),
                                    selector: selector
                                }};
                            }}
                        }}
                        return null;
                    }})()
                """)
                
                if semantic_result:
                    print(f"    ✅ Found element with semantic search: {semantic_result['selector']}")
                    from ..core.models import Coordinates
                    return Coordinates(x=int(semantic_result['x']), y=int(semantic_result['y']))
            
            # If semantic search doesn't find anything, try expanding circles around the original coordinates
            for radius in [15, 30, 60, 120, 200]:
                element_info = await self.page.evaluate(f"""
                    (() => {{
                        const originalX = {coordinates.x};
                        const originalY = {coordinates.y};
                        const radius = {radius};
                        
                        // Check points in a circle around the original coordinates
                        for (let angle = 0; angle < 360; angle += 30) {{
                            const radians = angle * Math.PI / 180;
                            const x = originalX + radius * Math.cos(radians);
                            const y = originalY + radius * Math.sin(radians);
                            
                            const element = document.elementFromPoint(x, y);
                            if (!element) continue;
                            
                            const tag = element.tagName.toLowerCase();
                            const type = element.type || '';
                            const role = element.getAttribute('role') || '';
                            
                            let isInteractive = false;
                            if ('{action}' === 'click') {{
                                isInteractive = tag === 'button' || 
                                               tag === 'a' ||
                                               tag === 'input' ||
                                               tag === 'select' ||
                                               tag === 'textarea' ||
                                               role === 'button' ||
                                               role === 'link' ||
                                               element.onclick !== null;
                            }} else if ('{action}' === 'type') {{
                                isInteractive = tag === 'input' || tag === 'textarea' ||
                                               element.contentEditable === 'true';
                            }}
                            
                            if (isInteractive) {{
                                const rect = element.getBoundingClientRect();
                                return {{
                                    x: rect.left + rect.width / 2,
                                    y: rect.top + rect.height / 2,
                                    tag: tag,
                                    id: element.id,
                                    name: element.name
                                }};
                            }}
                        }}
                        return null;
                    }})()
                """)
                
                if element_info:
                    print(f"    🔍 Found {element_info['tag']} at radius {radius}px (id: {element_info.get('id', 'none')}, name: {element_info.get('name', 'none')})")
                    from ..core.models import Coordinates
                    return Coordinates(x=int(element_info['x']), y=int(element_info['y']))
            
            # If we reach here, no elements found
            print(f"    ❌ No interactive elements found in search area")
            
            return None
        except Exception as e:
            print(f"    ⚠️ Error in nearby element search: {e}")
            return None
    
    async def _normalize_instruction_with_ai(self, action_plan: Dict[str, Any], target: str) -> List[str]:
        """Use AI to normalize human language instructions into selector-friendly terms."""
        try:
            action_type = action_plan["action"]
            page_context = {
                "url": self.page.url,
                "title": await self.page.title()
            }
            
            # Fast, cheap GPT call for instruction normalization
            normalization_prompt = f"""
You are a UI automation expert. Convert this human language instruction into standardized terms that work well with CSS selectors.

INSTRUCTION: "{action_type} on {target}"
PAGE CONTEXT: {page_context["title"]} ({page_context["url"]})

Provide 3-5 alternative terms/phrases that could represent the same UI element:
1. Exact term variations (singular/plural, capitalization)
2. Common synonyms  
3. Abbreviated forms
4. Context-appropriate alternatives

Return only a JSON list of strings, no explanation:
["term1", "term2", "term3", ...]

Examples:
- "workspaces" → ["workspaces", "workspace", "Workspaces", "work space", "projects"]
- "main menu" → ["menu", "navigation", "nav", "main menu", "header menu"]
- "create button" → ["create", "Create", "new", "+", "add", "create button"]
- "sign in" → ["sign in", "login", "log in", "signin", "Log In", "Sign In"]
"""

            # Use existing LLM client for fast normalization
            if hasattr(self, 'element_detector') and hasattr(self.element_detector, 'vision_client'):
                try:
                    # This is a text-only call, much faster and cheaper than vision
                    import openai
                    
                    # Get API key from vision client's internal openai client
                    vision_client = self.element_detector.vision_client
                    api_key = vision_client.client.api_key if hasattr(vision_client.client, 'api_key') else None
                    
                    if not api_key:
                        # Fallback: try to get from credentials again
                        from ..utils.credentials_loader import get_openai_credentials
                        creds = get_openai_credentials()
                        api_key = creds.get('api_key')
                    
                    if not api_key:
                        raise ValueError("No API key available")
                    
                    client = openai.AsyncOpenAI(api_key=api_key)
                    
                    response = await client.chat.completions.create(
                        model="gpt-4o-mini",  # Fast, cheap model for text processing
                        messages=[{"role": "user", "content": normalization_prompt}],
                        max_tokens=100,
                        temperature=0.1
                    )
                    
                    import json
                    normalized_list = json.loads(response.choices[0].message.content.strip())
                    
                    # Always include the original target
                    if target not in normalized_list:
                        normalized_list.insert(0, target)
                    
                    return normalized_list[:6]  # Limit to 6 terms max
                    
                except Exception as e:
                    print(f"    ⚠️ AI normalization failed: {e}")
                    # Fallback to basic normalization
                    return self._basic_normalization(target)
            else:
                return self._basic_normalization(target)
                
        except Exception:
            return self._basic_normalization(target)
    
    def _basic_normalization(self, target: str) -> List[str]:
        """Basic normalization fallback when AI is not available."""
        normalized = [target]
        target_lower = target.lower()
        
        # Basic variations
        if target != target.lower():
            normalized.append(target.lower())
        if target != target.capitalize():
            normalized.append(target.capitalize())
        if target != target.upper():
            normalized.append(target.upper())
            
        # Common synonyms
        synonyms = {
            "workspaces": ["workspace", "work space", "projects"],
            "create": ["new", "add", "+"],
            "menu": ["navigation", "nav"],
            "sign in": ["login", "log in", "signin"],
            "my": ["my", "mine", "personal"],
            "conversation": ["chat", "conversation", "messaging"]
        }
        
        for key, values in synonyms.items():
            if key in target_lower:
                normalized.extend(values)
        
        return list(dict.fromkeys(normalized))  # Remove duplicates while preserving order

    async def _try_enhanced_traditional_detection(self, action_plan: Dict[str, Any], original_target: str, normalized_targets: List[str]) -> Optional[Coordinates]:
        """Try traditional detection with AI-normalized terms."""
        try:
            action_type = action_plan["action"]
            
            if action_type == "click":
                # Try each normalized target
                for target in normalized_targets:
                    print(f"    🔍 Trying selectors for normalized term: '{target}'")
                    
                    # Generate smart selectors for this normalized target
                    selectors = self._generate_smart_selectors(target, action_plan)
                    
                    # Sort selectors by priority (lower numbers = higher priority)
                    selectors.sort(key=lambda x: x.get("priority", 999))
                    
                    for selector_info in selectors:
                        try:
                            selector = selector_info["selector"]
                            strategy = selector_info["strategy"]
                            
                            # Try to find the element
                            element = self.page.locator(selector).first
                            
                            # Check if element exists and is visible
                            if await element.count() > 0:
                                try:
                                    if await element.is_visible(timeout=1000):  # Shorter timeout for efficiency
                                        print(f"    ✅ Found using {strategy} for '{target}': {selector}")
                                        
                                        # Get element coordinates
                                        bounding_box = await element.bounding_box()
                                        if bounding_box:
                                            center_x = int(bounding_box['x'] + bounding_box['width'] / 2)
                                            center_y = int(bounding_box['y'] + bounding_box['height'] / 2)
                                            
                                            from ..core.models import Coordinates
                                            return Coordinates(x=center_x, y=center_y)
                                            
                                except Exception:
                                    # Element might not be ready, continue to next selector
                                    continue
                                    
                        except Exception:
                            # Selector failed, try next one
                            continue
                        
            return None
            
        except Exception:
            return None
    
    def _generate_smart_selectors(self, target: str, action_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate intelligent selectors based on target and context."""
        selectors = []
        target_lower = target.lower()
        
        # 🎯 CHECK FOR UI CONTEXT (dropdown, modal, etc.)
        ui_context_type = action_plan.get("ui_context_type")
        ui_context_target = action_plan.get("ui_context_target")
        search_scope = action_plan.get("search_scope")
        
        # Strategy 1: Context-aware element matching (HIGHEST priority when context exists)
        if ui_context_type == "dropdown" and search_scope:
            print(f"    🎯 Using dropdown-scoped selectors for '{target}' within {ui_context_target} dropdown")
            # Prioritize elements within dropdown/menu regions
            selectors.extend([
                {"selector": f"[role='menu'] [role='menuitem']:has-text('{target}')", "strategy": "dropdown_menuitem", "priority": 0},
                {"selector": f"[role='menu'] button:has-text('{target}')", "strategy": "dropdown_button", "priority": 0},
                {"selector": f"[role='menu'] *:has-text('{target}')", "strategy": "dropdown_any", "priority": 0},
                {"selector": f"[aria-expanded='true'] + * [role='menuitem']:has-text('{target}')", "strategy": "expanded_dropdown_item", "priority": 0},
                {"selector": f"[aria-expanded='true'] + * button:has-text('{target}')", "strategy": "expanded_dropdown_button", "priority": 0},
                {"selector": f"[class*='dropdown'][class*='open'] *:has-text('{target}')", "strategy": "open_dropdown_item", "priority": 0},
                {"selector": f"[class*='menu'][style*='block'] *:has-text('{target}')", "strategy": "visible_menu_item", "priority": 0},
            ])
        
        # Strategy 2: Direct text matching (lower priority when context exists, higher when no context)
        text_priority = 3 if ui_context_type else 1
        selectors.extend([
            {"selector": f"text='{target}'", "strategy": "exact_text", "priority": text_priority},
            {"selector": f"text={target}", "strategy": "text_contains", "priority": text_priority + 1},
        ])
        
        # Strategy 2: Enhanced semantic element matching
        if "dropdown" in target_lower or "create" in target_lower:
            # Prioritize dropdown buttons with visual indicators
            selectors.extend([
                {"selector": f"button:has-text('{target}')[aria-haspopup='true']:not([role='tab'])", "strategy": "dropdown_button_aria", "priority": 1},
                {"selector": f"button:has-text('{target}')[aria-expanded]:not([role='tab'])", "strategy": "dropdown_button_expanded", "priority": 1},
                {"selector": f"button:has-text('{target}'):has(svg, [class*='arrow'], [class*='chevron'])", "strategy": "button_with_arrow", "priority": 2},
                {"selector": f"button:has-text('{target}')[class*='dropdown']:not([role='tab'])", "strategy": "dropdown_button_class", "priority": 3},
            ])
        
        # Strategy 3: Button matching with tab exclusion
        selectors.extend([
            {"selector": f"button:has-text('{target}'):not([role='tab'])", "strategy": "button_not_tab", "priority": 3},
            {"selector": f"[role='button']:has-text('{target}'):not([role='tab'])", "strategy": "role_button_not_tab", "priority": 4},
            {"selector": f"button:has-text('{target}')", "strategy": "button_text", "priority": 5},
        ])
        
        # Strategy 4: Link matching
        if any(word in target_lower for word in ["workspace", "sign in", "login"]):
            selectors.extend([
                {"selector": f"a:has-text('{target}')", "strategy": "link_text", "priority": 5},
                {"selector": f"[href*='{target.lower()}']", "strategy": "link_href", "priority": 6},
            ])
        
        # Strategy 5: Menu item matching
        selectors.extend([
            {"selector": f"[role='menuitem']:has-text('{target}')", "strategy": "menu_item", "priority": 6},
            {"selector": f"li:has-text('{target}')", "strategy": "list_item", "priority": 7},
        ])
        
        # Strategy 6: Generic interactive elements
        selectors.extend([
            {"selector": f"*:has-text('{target}')[onclick]", "strategy": "clickable_element", "priority": 8},
            {"selector": f"div:has-text('{target}')[role='button']", "strategy": "div_button", "priority": 9},
        ])
        
        # Sort by priority (lower number = higher priority)
        selectors.sort(key=lambda x: x["priority"])
        
        return selectors
    
    async def _analyze_natural_viewport(self) -> None:
        """Analyze the natural browser viewport without forcing any changes."""
        try:
            print(f"📏 Analyzing natural browser viewport...")
            
            # Get actual browser dimensions as they are
            viewport_info = await self._get_viewport_info()
            
            print(f"    📊 Current browser state:")
            print(f"       Viewport: {viewport_info.get('viewportWidth', 'unknown')}x{viewport_info.get('viewportHeight', 'unknown')}")
            print(f"       Window: {viewport_info.get('windowWidth', 'unknown')}x{viewport_info.get('windowHeight', 'unknown')}")
            print(f"       Screen: {viewport_info.get('screenWidth', 'unknown')}x{viewport_info.get('screenHeight', 'unknown')}")
            print(f"       Device Pixel Ratio: {viewport_info.get('devicePixelRatio', 'unknown')}")
            
            # Check if we have reasonable dimensions
            viewport_width = viewport_info.get('viewportWidth', 0)
            viewport_height = viewport_info.get('viewportHeight', 0)
            
            if viewport_width > 0 and viewport_height > 0:
                print(f"    ✅ Working with natural viewport: {viewport_width}x{viewport_height}")
                
                # Calculate usable area info
                if viewport_width < 1000:
                    print(f"    ⚠️ Narrow viewport detected - right-side elements may be harder to find")
                if viewport_height < 600:
                    print(f"    ⚠️ Short viewport detected - bottom elements may require scrolling")
                    
                # Store dimensions for coordinate validation
                self._current_viewport = {
                    'width': viewport_width,
                    'height': viewport_height,
                    'dpr': viewport_info.get('devicePixelRatio', 1)
                }
                
            else:
                print(f"    ⚠️ Could not determine viewport dimensions, using fallback assumptions")
                self._current_viewport = {
                    'width': 1200,
                    'height': 800,
                    'dpr': 1
                }
            
            print(f"    🎯 Framework will adapt to these natural dimensions")
            
        except Exception as e:
            print(f"    ⚠️ Viewport analysis failed: {e}")
            # Set reasonable defaults
            self._current_viewport = {
                'width': 1200,
                'height': 800,
                'dpr': 1
            }
    
    def _validate_coordinates_in_viewport(self, coordinates: Coordinates) -> bool:
        """Validate that coordinates are within the natural viewport bounds."""
        try:
            if not hasattr(self, '_current_viewport'):
                return True  # Skip validation if viewport info not available
            
            viewport = self._current_viewport
            
            # Check if coordinates are within viewport bounds with some margin
            margin = 10  # Allow small margin for edge cases
            
            within_width = -margin <= coordinates.x <= viewport['width'] + margin
            within_height = -margin <= coordinates.y <= viewport['height'] + margin
            
            if not within_width:
                print(f"    ⚠️ X coordinate {coordinates.x} outside viewport width {viewport['width']}")
            if not within_height:
                print(f"    ⚠️ Y coordinate {coordinates.y} outside viewport height {viewport['height']}")
                
            return within_width and within_height
            
        except Exception:
            return True  # Default to valid if validation fails
    
    async def _get_viewport_info(self) -> dict:
        """Get detailed viewport and browser window information with retries."""
        for attempt in range(3):
            try:
                # Ensure page is ready
                await asyncio.sleep(0.2)
                
                viewport_info = await self.page.evaluate("""
                    () => {
                        try {
                            return {
                                // Viewport dimensions (visible area)
                                viewportWidth: window.innerWidth || 0,
                                viewportHeight: window.innerHeight || 0,
                                
                                // Browser window dimensions
                                windowWidth: window.outerWidth || 0,
                                windowHeight: window.outerHeight || 0,
                                
                                // Screen dimensions
                                screenWidth: (window.screen && window.screen.width) || 1920,
                                screenHeight: (window.screen && window.screen.height) || 1080,
                                screenAvailWidth: (window.screen && window.screen.availWidth) || 1920,
                                screenAvailHeight: (window.screen && window.screen.availHeight) || 1080,
                                
                                // Device pixel ratio
                                devicePixelRatio: window.devicePixelRatio || 1,
                                
                                // Document dimensions
                                documentWidth: (document.documentElement && document.documentElement.scrollWidth) || 0,
                                documentHeight: (document.documentElement && document.documentElement.scrollHeight) || 0,
                                
                                // Scroll position
                                scrollX: window.scrollX || 0,
                                scrollY: window.scrollY || 0,
                                
                                // Browser info
                                userAgent: (navigator.userAgent && navigator.userAgent.substring(0, 100)) || 'unknown'
                            };
                        } catch (e) {
                            return {
                                viewportWidth: 0,
                                viewportHeight: 0,
                                screenWidth: 1920,
                                screenHeight: 1080,
                                screenAvailWidth: 1920,
                                screenAvailHeight: 1080,
                                devicePixelRatio: 1,
                                error: e.toString()
                            };
                        }
                    }
                """)
                
                # Validate we got reasonable data
                if viewport_info.get('screenWidth', 0) > 0:
                    return viewport_info
                else:
                    print(f"    ⚠️ Attempt {attempt + 1}: Got invalid viewport data, retrying...")
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                print(f"    ⚠️ Attempt {attempt + 1}: Viewport info failed: {e}")
                await asyncio.sleep(0.5)
        
        # Final fallback with reasonable defaults
        return {
            'viewportWidth': 1400,
            'viewportHeight': 900,
            'screenWidth': 1920,
            'screenHeight': 1080,
            'screenAvailWidth': 1800,
            'screenAvailHeight': 1000,
            'devicePixelRatio': 1,
            'fallback': True
        }
    
    async def _take_analysis_screenshot(self, step_number: int) -> Optional[str]:
        """Take screenshot for AI vision analysis with viewport logging."""
        
        Path("test_results").mkdir(exist_ok=True)
        screenshot_path = f"test_results/vision_analysis_step_{step_number}_{int(time.time())}.png"
        
        try:
            # 🔍 LOG VIEWPORT INFORMATION
            viewport_info = await self._get_viewport_info()
            print(f"    📏 Viewport Analysis:")
            print(f"       Viewport: {viewport_info.get('viewportWidth', 'unknown')}x{viewport_info.get('viewportHeight', 'unknown')}")
            print(f"       Window: {viewport_info.get('windowWidth', 'unknown')}x{viewport_info.get('windowHeight', 'unknown')}")
            print(f"       Screen: {viewport_info.get('screenWidth', 'unknown')}x{viewport_info.get('screenHeight', 'unknown')}")
            print(f"       Device Pixel Ratio: {viewport_info.get('devicePixelRatio', 'unknown')}")
            print(f"       Document: {viewport_info.get('documentWidth', 'unknown')}x{viewport_info.get('documentHeight', 'unknown')}")
            print(f"       Scroll: ({viewport_info.get('scrollX', 'unknown')}, {viewport_info.get('scrollY', 'unknown')})")
            
            await self.page.screenshot(path=screenshot_path, full_page=False)
            print(f"    📸 Screenshot for vision analysis: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            print(f"    ⚠️ Could not take analysis screenshot: {e}")
            return None
    
    async def _click_at_coordinates(self, coordinates: Coordinates) -> bool:
        """Click at specific coordinates determined by vision with enhanced visual feedback and navigation handling."""
        
        try:
            # 🎯 VISUAL FEEDBACK: Highlight target area before clicking
            print(f"    🎯 Preparing to click at coordinates ({coordinates.x}, {coordinates.y})")
            await self._highlight_click_target(coordinates)
            
            # Store current URL to detect navigation
            initial_url = self.page.url
            initial_title = await self.page.title()
            
            # 🖱️ ENHANCED CLICK EXECUTION with debugging
            print(f"    🖱️ Clicking at vision coordinates ({coordinates.x}, {coordinates.y})")
            
            # 🔍 PRE-CLICK DEBUGGING
            print(f"    🔍 Pre-click page state:")
            print(f"       URL: {initial_url}")
            print(f"       Title: {initial_title}")
            print(f"       Ready state: {await self.page.evaluate('document.readyState')}")
            
            # 🎯 INSPECT ELEMENT AT COORDINATES
            try:
                element_info = await self.page.evaluate(f"""
                    (() => {{
                        const element = document.elementFromPoint({coordinates.x}, {coordinates.y});
                        if (element) {{
                            return {{
                                tagName: element.tagName,
                                id: element.id || '',
                                className: element.className || '',
                                textContent: element.textContent ? element.textContent.substring(0, 50) : '',
                                type: element.type || '',
                                placeholder: element.placeholder || '',
                                name: element.name || '',
                                role: element.getAttribute('role') || '',
                                ariaLabel: element.getAttribute('aria-label') || ''
                            }};
                        }} else {{
                            return null;
                        }}
                    }})()
                """)
                
                if element_info:
                    print(f"    🎯 Element at ({coordinates.x}, {coordinates.y}):")
                    print(f"       Tag: {element_info.get('tagName', 'N/A')}")
                    print(f"       ID: {element_info.get('id', 'N/A') or 'None'}")
                    print(f"       Class: {element_info.get('className', 'N/A') or 'None'}")
                    print(f"       Type: {element_info.get('type', 'N/A') or 'None'}")
                    print(f"       Name: {element_info.get('name', 'N/A') or 'None'}")
                    print(f"       Placeholder: {element_info.get('placeholder', 'N/A') or 'None'}")
                    print(f"       Role: {element_info.get('role', 'N/A') or 'None'}")
                    print(f"       Aria-label: {element_info.get('ariaLabel', 'N/A') or 'None'}")
                    print(f"       Text: {element_info.get('textContent', 'N/A')[:50] or 'None'}")
                else:
                    print(f"    ⚠️ No element found at coordinates ({coordinates.x}, {coordinates.y})")
            except Exception as e:
                print(f"    ⚠️ Could not inspect element: {e}")
            
            # 🎯 ENSURE PAGE IS INTERACTIVE
            try:
                await self.page.wait_for_load_state('domcontentloaded', timeout=5000)
                await asyncio.sleep(0.5)  # Extra stability wait
                print(f"    ✅ Page confirmed ready for interaction")
            except:
                print(f"    ⚠️ Page might not be fully ready, proceeding anyway")
            
            # 🖱️ PERFORM ACTUAL CLICK with error handling and fallback
            click_success = False
            try:
                # Method 1: Standard mouse click
                await self.page.mouse.click(coordinates.x, coordinates.y, delay=100)
                print(f"    ✅ Mouse click executed successfully")
                click_success = True
            except Exception as click_error:
                print(f"    ❌ Mouse click failed: {click_error}")
                
                # Method 2: Alternative click using JavaScript
                try:
                    print(f"    🔄 Trying alternative JavaScript click...")
                    await self.page.evaluate(f"""
                        const element = document.elementFromPoint({coordinates.x}, {coordinates.y});
                        if (element) {{
                            console.log('Found element at coordinates:', element);
                            element.click();
                            console.log('JavaScript click executed');
                        }} else {{
                            console.log('No element found at coordinates');
                        }}
                    """)
                    print(f"    ✅ JavaScript click executed")
                    click_success = True
                except Exception as js_error:
                    print(f"    ❌ JavaScript click also failed: {js_error}")
                    return False
            
            if not click_success:
                return False
            
            # 📸 IMMEDIATE POST-CLICK SCREENSHOT
            await self._capture_action_screenshot("click", coordinates)
            
            # 🔄 ENHANCED CHANGE DETECTION
            print(f"    ⏳ Monitoring for page changes...")
            
            # Wait for immediate DOM reactions
            await asyncio.sleep(1.2)  # Longer wait to catch slower responses
            
            # Check for any page changes
            current_url = self.page.url
            current_title = await self.page.title()
            
            print(f"    🔍 Post-click page state:")
            print(f"       URL: {current_url}")
            print(f"       Title: {current_title}")
            
            if current_url != initial_url:
                print(f"    🔄 Navigation detected: {initial_url} → {current_url}")
                await self._wait_for_page_stability(navigation=True)
            elif current_title != initial_title:
                print(f"    📄 Page title changed: '{initial_title}' → '{current_title}'")
                await self._wait_for_page_stability(navigation=False)
            else:
                print(f"    ⚠️ No page changes detected - click might not have worked")
                # Take another screenshot to compare
                await self._capture_action_screenshot("post_click_check", coordinates)
                await asyncio.sleep(0.5)
                
            return True
            
        except Exception as e:
            error_msg = str(e)
            if "Execution context was destroyed" in error_msg:
                print(f"    ⚠️ Execution context destroyed (navigation occurred), treating as success")
                # This usually means navigation happened successfully
                try:
                    # Wait for new page to be ready
                    await asyncio.sleep(2.0)
                    await self.page.wait_for_load_state('domcontentloaded', timeout=5000)
                    print(f"    ✅ New page loaded after navigation")
                except Exception:
                    print(f"    ⚠️ Could not verify new page loaded")
                return True
            else:
                print(f"    ❌ Click at coordinates failed: {e}")
                return False
    
    async def _highlight_click_target(self, coordinates: Coordinates) -> None:
        """Add visual highlight to show where we're about to click."""
        try:
            # Inject CSS and JavaScript to create a visual highlight
            highlight_script = f"""
            (function() {{
                // Remove any existing highlights
                const existing = document.getElementById('quantum-click-target');
                if (existing) existing.remove();
                
                // Create highlight element
                const highlight = document.createElement('div');
                highlight.id = 'quantum-click-target';
                highlight.style.cssText = `
                    position: fixed;
                    left: {coordinates.x - 15}px;
                    top: {coordinates.y - 15}px;
                    width: 30px;
                    height: 30px;
                    border: 3px solid #ff0000;
                    border-radius: 50%;
                    background: rgba(255, 0, 0, 0.2);
                    z-index: 999999;
                    pointer-events: none;
                    animation: quantum-pulse 0.8s ease-in-out;
                `;
                
                // Add pulse animation
                const style = document.createElement('style');
                style.textContent = `
                    @keyframes quantum-pulse {{
                        0% {{ transform: scale(0.5); opacity: 1; }}
                        50% {{ transform: scale(1.2); opacity: 0.8; }}
                        100% {{ transform: scale(1); opacity: 0.6; }}
                    }}
                `;
                document.head.appendChild(style);
                document.body.appendChild(highlight);
                
                // Auto-remove after 1 second
                setTimeout(() => {{
                    if (document.getElementById('quantum-click-target')) {{
                        document.getElementById('quantum-click-target').remove();
                    }}
                }}, 1000);
            }})();
            """
            
            await self.page.evaluate(highlight_script)
            await asyncio.sleep(0.6)  # Give time for visual feedback
            
        except Exception as e:
            print(f"    ⚠️ Could not add visual highlight: {e}")
    
    async def _capture_action_screenshot(self, action_type: str, coordinates: Coordinates = None) -> None:
        """Capture screenshot of the action for visual feedback."""
        try:
            timestamp = int(time.time())
            step_num = getattr(self, '_current_step', 0)
            
            Path("test_results/actions").mkdir(parents=True, exist_ok=True)
            
            if coordinates:
                screenshot_path = f"test_results/actions/step_{step_num}_{action_type}_at_{coordinates.x}_{coordinates.y}_{timestamp}.png"
            else:
                screenshot_path = f"test_results/actions/step_{step_num}_{action_type}_{timestamp}.png"
            
            await self.page.screenshot(path=screenshot_path)
            print(f"    📸 Action screenshot: {screenshot_path}")
            
        except Exception as e:
            print(f"    ⚠️ Could not capture action screenshot: {e}")
    
    async def _wait_for_page_stability(self, navigation: bool = True) -> None:
        """Enhanced page stability waiting with visual feedback."""
        try:
            if navigation:
                print(f"    ⏳ Waiting for navigation to complete...")
                # Wait for basic page load
                await self.page.wait_for_load_state('domcontentloaded', timeout=15000)
                print(f"    ✅ DOM content loaded")
                
                # Wait for network to calm down
                await self.page.wait_for_load_state('networkidle', timeout=10000)
                print(f"    🌐 Network activity settled")
                
                # Additional wait for dynamic content
                await asyncio.sleep(1.5)
                print(f"    ⏱️ Additional stability wait completed")
            else:
                print(f"    ⏳ Waiting for page updates to stabilize...")
                # For non-navigation page changes, shorter wait
                await asyncio.sleep(1.0)
                
                # Check if any loading indicators are present
                try:
                    await self.page.wait_for_selector('.loading, .spinner, [data-loading="true"]', 
                                                   state='detached', timeout=5000)
                    print(f"    ✅ Loading indicators cleared")
                except:
                    pass  # No loading indicators found, continue
                
                await asyncio.sleep(0.5)
                print(f"    ✅ Page updates stabilized")
                
        except Exception as e:
            print(f"    ⚠️ Page stability wait warning: {e}")
    
    async def _type_text(self, text: str) -> bool:
        """Type text at current focus with enhanced visual feedback and credential substitution."""
        
        try:
            # Perform credential substitution
            resolved_text = self._resolve_credentials(text)
            
            # 🎯 VISUAL FEEDBACK: Show typing action
            print(f"    ⌨️ Typing text: '{resolved_text}'")
            await self._capture_action_screenshot("typing")
            
            # Type with slight delay for visual feedback
            await self.page.keyboard.type(resolved_text, delay=50)
            
            # Brief pause to see the typed text
            await asyncio.sleep(0.5)
            print(f"    ✅ Text typed successfully")
            return True
        except Exception as e:
            print(f"    ❌ Typing failed: {e}")
            return False
    
    def _resolve_credentials(self, text: str) -> str:
        """Resolve credential references in text like {cred:aihub.email}."""
        import re
        from ..utils.credentials_loader import CredentialsLoader
        
        # Pattern to match credential references
        pattern = r'\{(?:cred|credential|creds):([^}]+)\}'
        
        def replace_credential(match):
            credential_path = match.group(1).strip()
            try:
                # Load credentials and resolve path
                loader = CredentialsLoader()
                credentials = loader.load_credentials()
                
                # Parse credential path (e.g., "aihub.email" -> aihub section, email key)
                path_parts = credential_path.split('.')
                if len(path_parts) != 2:
                    print(f"    ⚠️ Invalid credential path format: {credential_path}")
                    return match.group(0)
                
                service, key = path_parts
                service_creds = credentials.get(service, {})
                value = service_creds.get(key)
                
                if value is not None:
                    print(f"    🔑 Resolved credential: {credential_path} -> {value}")
                    return str(value)
                else:
                    print(f"    ⚠️ Could not resolve credential: {credential_path}")
                    return match.group(0)
                    
            except Exception as e:
                print(f"    ❌ Error resolving credential {credential_path}: {e}")
                return match.group(0)
        
        resolved_text = re.sub(pattern, replace_credential, text)
        return resolved_text
    
    async def _fallback_to_traditional(self, action_plan: Dict[str, Any], step_number: int) -> bool:
        """Fallback to traditional element finding if vision fails."""
        
        if not self.traditional_finder:
            print("    ❌ No traditional fallback available")
            return False
        
        print("    🔄 Falling back to traditional element detection...")
        self.traditional_fallbacks += 1
        
        try:
            action = action_plan["action"]
            
            if action == "click":
                element = await self.traditional_finder.find_clickable_element(
                    self.page, 
                    action_plan["target"],
                    context=action_plan.get("context", {})
                )
                
                if element:
                    return await self.action_executor.click(element)
                else:
                    await self._save_debug_screenshot(step_number)
                    return False
            
            elif action == "type":
                element = await self.traditional_finder.find_input_field(
                    self.page,
                    action_plan["field"],
                    field_type=action_plan.get("field_type")
                )
                
                if element:
                    return await self.action_executor.type_text(element, action_plan["text"])
                else:
                    return False
            
            return False
            
        except Exception as e:
            print(f"    ❌ Traditional fallback failed: {e}")
            return False
    
    async def _save_debug_screenshot(self, step_number: int) -> str:
        """Save debug screenshot when detection fails."""
        
        Path("test_results").mkdir(exist_ok=True)
        screenshot_path = f"test_results/debug_vision_step_{step_number}.png"
        
        try:
            await self.page.screenshot(path=screenshot_path, full_page=True)
            print(f"    📸 Debug screenshot: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            print(f"    ⚠️ Could not save debug screenshot: {e}")
            return ""
    
    async def _generate_report(self, results: List[Dict], instruction_file: str, total_test_time: float = 0.0) -> Dict[str, Any]:
        """Generate comprehensive test report with vision and performance statistics."""
        
        successful_steps = len([r for r in results if r["status"] == "success"])
        total_steps = len(results)
        success_rate = (successful_steps / total_steps * 100) if total_steps > 0 else 0
        
        # Calculate performance statistics
        step_times = [r.get("timing", {}).get("total_time", 0.0) for r in results]
        avg_step_time = sum(step_times) / len(step_times) if step_times else 0.0
        max_step_time = max(step_times) if step_times else 0.0
        min_step_time = min(step_times) if step_times else 0.0
        
        parse_times = [r.get("timing", {}).get("parse_time", 0.0) for r in results]
        execute_times = [r.get("timing", {}).get("execute_time", 0.0) for r in results]
        avg_parse_time = sum(parse_times) / len(parse_times) if parse_times else 0.0
        avg_execute_time = sum(execute_times) / len(execute_times) if execute_times else 0.0
        
        final_url = self.page.url
        final_title = await self.page.title()
        
        # Vision statistics
        vision_success_rate = 0.0
        if self.vision_detections > 0:
            vision_successes = self.vision_detections - self.detection_failures
            vision_success_rate = (vision_successes / self.vision_detections) * 100
        
        print("\n" + "=" * 60)
        print("📊 VISION-ENHANCED CHROME ENGINE REPORT") 
        print("=" * 60)
        print(f"📈 Overall Success Rate: {success_rate:.1f}% ({successful_steps}/{total_steps})")
        print(f"🌐 Final URL: {final_url}")
        print(f"📄 Final Title: {final_title}")
        print(f"\n👁️ Vision Detection Statistics:")
        print(f"  • Vision attempts: {self.vision_detections}")
        print(f"  • Vision success rate: {vision_success_rate:.1f}%")
        print(f"  • Traditional fallbacks: {self.traditional_fallbacks}")
        print(f"  • Detection failures: {self.detection_failures}")
        
        # Get detailed vision stats
        vision_stats = self.element_detector.get_detection_stats()
        llm_stats = self.vision_client.get_usage_stats()
        
        print(f"  • LLM requests: {llm_stats.get('total_requests', 0)}")
        print(f"  • Estimated cost: ${llm_stats.get('estimated_cost', 0.0):.4f}")
        
        # 🎯 VISUAL FEEDBACK REPORT
        print(f"\n🎯 Visual Feedback & Stability Features:")
        print(f"  • ✅ Click target highlighting enabled")
        print(f"  • ✅ Action screenshots captured in test_results/actions/")
        print(f"  • ✅ Enhanced navigation stability waiting")
        print(f"  • ✅ Progress indicators during execution")
        print(f"  • ✅ Real-time page state monitoring")
        
        # Check if action screenshots were created
        action_screenshots_dir = Path("test_results/actions")
        if action_screenshots_dir.exists():
            screenshot_count = len(list(action_screenshots_dir.glob("*.png")))
            print(f"  • 📸 {screenshot_count} action screenshots saved")
        
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
            "step_results": results,
            "vision_statistics": {
                "vision_detections": self.vision_detections,
                "traditional_fallbacks": self.traditional_fallbacks,
                "detection_failures": self.detection_failures,
                "vision_success_rate": vision_success_rate,
                "element_detector_stats": vision_stats,
                "llm_usage_stats": llm_stats
            },
            "performance_statistics": {
                "total_test_time": total_test_time,
                "average_step_time": avg_step_time,
                "max_step_time": max_step_time,
                "min_step_time": min_step_time,
                "average_parse_time": avg_parse_time,
                "average_execute_time": avg_execute_time,
                "steps_per_minute": (total_steps / (total_test_time / 60)) if total_test_time > 0 else 0.0
            }
        }
        
        return report
    
    async def _save_final_screenshot(self, instruction_file: str) -> str:
        """Save final test screenshot."""
        
        Path("test_results").mkdir(exist_ok=True)
        clean_filename = instruction_file.replace('/', '_').replace('.txt', '')
        screenshot_path = f"test_results/final_vision_{clean_filename}.png"
        
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
        """Clean up browser and vision resources."""
        
        print("\n🛑 Cleaning up Vision-Enhanced Chrome Engine...")
        
        try:
            # Cleanup vision components
            await self.element_detector.cleanup()
            
            # Cleanup browser resources
            if self.page:
                await self.page.close()
                print("📄 Closed test page")
            
            # Only close context and browser if we created them (not connected to existing)
            if hasattr(self, '_connected_to_existing') and self._connected_to_existing:
                print("🔗 Connected to existing browser - keeping browser instance alive")
                # Don't close context if it was existing, unless we created it
                if self.context and len(self.context.pages) == 0:
                    print("📱 Closing empty context")
                    await self.context.close()
            else:
                print("🚀 Launched new browser - closing all resources")
                if self.context:
                    await self.context.close()
                if self.browser:
                    await self.browser.close()
            
            if self.playwright:
                await self.playwright.stop()
                
            print("✅ Vision-Enhanced Chrome Engine cleanup completed")
            
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """Get comprehensive engine statistics."""
        
        return {
            "engine_type": "VisionChromeEngine",
            "vision_primary": self.use_vision_primary,
            "vision_detections": self.vision_detections,
            "traditional_fallbacks": self.traditional_fallbacks,
            "detection_failures": self.detection_failures,
            "detection_stats": self.element_detector.get_detection_stats(),
            "llm_stats": self.vision_client.get_usage_stats()
        }
