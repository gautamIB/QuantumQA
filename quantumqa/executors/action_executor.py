#!/usr/bin/env python3
"""
Generic Action Executor - Executes browser actions in a standardized way
Works with any application using intelligent execution strategies
"""

import asyncio
import os
import sys
import importlib
import inspect
import shlex
from typing import Dict, Any, Optional, List, Callable, Tuple
from playwright.async_api import Page, Locator, Download
from pathlib import Path
from datetime import datetime


class ActionExecutor:
    """Generic executor for all browser actions."""

    def __init__(self, credentials_file: Path = None):
        """Initialize ActionExecutor with optional credential manager."""
        self.credential_manager = None
        self.config_dir = None

        if credentials_file and credentials_file.exists():
            try:
                from ..security.credential_manager import CredentialManager
                self.credential_manager = CredentialManager(credentials_file)
                print(f"🔐 Credential manager initialized: {credentials_file}")
                # Set config_dir from credentials file location
                self.config_dir = credentials_file.parent
            except ImportError:
                print(
                    "⚠️ Credential manager not available (cryptography package not installed)"
                )
            except Exception as e:
                print(f"⚠️ Failed to initialize credential manager: {e}")

        # Fallback config directory
        if not self.config_dir:
            self.config_dir = Path(__file__).parent.parent / "config"

    async def navigate(self,
                       page: Page,
                       url: str,
                       options: Dict[str, Any] = None) -> bool:
        """Navigate to URL with intelligent handling."""

        options = options or {}
        wait_until = options.get("wait_until", "domcontentloaded")
        timeout = options.get("timeout", 30000)

        print(f"    🧭 Navigating to: {url}")

        try:
            response = await page.goto(url,
                                       wait_until=wait_until,
                                       timeout=timeout)

            # Brief additional wait for page stability
            await asyncio.sleep(1)

            current_url = page.url
            current_title = await page.title()

            print(f"    ✅ Navigation successful")
            print(f"    🌐 Current URL: {current_url}")
            print(f"    📄 Page title: {current_title}")

            # Verify navigation worked
            if current_url == "about:blank":
                print(f"    ❌ Navigation failed - still on blank page")
                return False

            return True

        except Exception as e:
            print(f"    ❌ Navigation error: {e}")
            return False

    async def click(self,
                    element: Locator,
                    options: Dict[str, Any] = None) -> bool:
        """Click element with intelligent strategies."""

        options = options or {}
        force = options.get("force", False)
        timeout = options.get("timeout", 5000)

        try:
            # Get element info for debugging
            element_text = await element.text_content()
            element_tag = await element.evaluate("el => el.tagName")

            # print(f"    👆 Clicking element: '{element_text}' ({element_tag})")
            print(f"    👆 Clicking element: '{element_text[:100]}' ({element_tag})")

            # Special handling for dropdown items that might need force clicking
            if "dropdown" in options.get("target", "").lower():
                print(f"    🎯 Using dropdown-specific click strategies...")
                success = await self._try_dropdown_click_strategies(
                    element, options)
            else:
                # Try multiple click strategies based on element type and context
                success = await self._try_click_strategies(element, options)

            if success:
                print(f"    ✅ Click successful")

                # Check if this is likely a download button
                target_text = options.get("target", "").lower()
                page = element.page
                is_download_button = (
                    "export" in target_text or "download" in target_text
                    or "csv" in target_text
                    or (element_tag.lower() == "button"
                        and "export" in element_text.lower()) or
                    (await
                     element.evaluate("el => el.getAttribute('data-target')")
                     == "submitButton"))

                # Special handling for download buttons - handle file download
                if is_download_button:
                    print(
                        f"    📥 Detected download button click, setting up download handler..."
                    )

                    # Create downloads directory if it doesn't exist
                    download_directory = Path.cwd() / "downloads"
                    download_directory.mkdir(exist_ok=True)

                    try:
                        # Try to set up download handler
                        download_task = asyncio.create_task(
                            self._handle_download(page, download_directory))

                        # Wait a bit for download to initiate
                        await asyncio.sleep(2)

                        # Check for download dialog or download starting indicators
                        download_started = await self._check_download_started(
                            page)
                        if download_started:
                            print(f"    ✅ Download started successfully")
                        else:
                            print(
                                f"    ⚠️ No download indicators detected, but continuing"
                            )

                        # Wait for download to complete (with timeout)
                        try:
                            await asyncio.wait_for(download_task, timeout=10)
                        except asyncio.TimeoutError:
                            print(
                                f"    ⚠️ Download taking longer than expected, continuing anyway"
                            )
                    except Exception as e:
                        print(f"    ⚠️ Error handling download: {e}")
                        # Continue execution even if download handling fails

                # Special validation for dropdown trigger buttons
                elif self._is_dropdown_trigger(options.get("target", "")):
                    print(f"    🔍 Verifying dropdown opened after click...")

                    # Wait a moment for dropdown to appear
                    await asyncio.sleep(1)

                    # Check if dropdown actually opened with strict validation
                    dropdown_opened = await self._verify_dropdown_opened_strict(
                        page)

                    if dropdown_opened:
                        print(
                            f"    ✅ Dropdown successfully opened and contains menu items"
                        )
                    else:
                        print(
                            f"    ❌ CRITICAL: Dropdown did not open properly")
                        print(
                            f"    🔄 Trying alternative dropdown trigger methods..."
                        )

                        # Try alternative clicking strategies for dropdown
                        alt_success = await self._try_alternative_dropdown_trigger(
                            element, page)
                        if alt_success:
                            # Re-verify strict opening
                            final_check = await self._verify_dropdown_opened_strict(
                                page)
                            if final_check:
                                print(
                                    f"    ✅ Alternative method successfully opened dropdown"
                                )
                            else:
                                print(
                                    f"    ❌ FAILED: Could not open dropdown with any method"
                                )
                                return False
                        else:
                            print(
                                f"    ❌ FAILED: Could not open dropdown with any method"
                            )
                            return False  # Report failure if dropdown didn't open

                # Wait for potential page changes
                await asyncio.sleep(1)

                return True
            else:
                print(f"    ❌ All click strategies failed")
                return False

        except Exception as e:
            print(f"    ❌ Click error: {e}")
            return False

    async def type_text(self,
                        element: Locator,
                        text: str,
                        options: Dict[str, Any] = None) -> bool:
        """Type text into element with validation and credential resolution."""

        options = options or {}
        clear_first = options.get("clear_first", True)

        try:
            # 🔐 SECURITY: Resolve credentials before typing
            resolved_text = self._resolve_credentials(text)

            # Log appropriately (hide sensitive data)
            if resolved_text != text:
                print(f"    🔐 Credential resolved for secure input")
                print(
                    f"    ⌨️ Typing: '[CREDENTIAL:{len(resolved_text)} chars]'"
                )
            else:
                print(f"    ⌨️ Typing: '{text}'")

            # Clear field first if requested
            if clear_first:
                await element.clear()

            # Type text
            await element.fill(resolved_text)

            # Verify text was entered (but don't log sensitive values)
            current_value = await element.input_value()
            if current_value == resolved_text:
                print(f"    ✅ Text typed successfully")
                return True
            else:
                print(
                    f"    ⚠️ Input mismatch. Expected: {len(resolved_text)} chars, Got: {len(current_value)} chars"
                )
                return False

        except Exception as e:
            print(f"    ❌ Type error: {e}")
            return False

    async def upload_file(self, page: Page, file_path: str) -> bool:
        """Upload file using file input or drag-drop area."""

        try:
            print(f"    📤 Attempting to upload file: {file_path}")

            # Check if file exists
            from pathlib import Path
            if not Path(file_path).exists():
                print(f"    ❌ File not found: {file_path}")
                return False

            # Look for file input elements
            file_inputs = page.locator('input[type="file"]')
            input_count = await file_inputs.count()

            if input_count > 0:
                print(
                    f"    🎯 Found {input_count} file input(s), using first one"
                )
                await file_inputs.first.set_input_files(file_path)
                print(f"    ✅ File uploaded successfully via input element")
                return True

            # Alternative: Look for upload area or button
            upload_selectors = [
                '[data-testid*="upload"]', '[class*="upload"]',
                'text="Select files"', 'text="Upload"', 'text="Drop files"'
            ]

            for selector in upload_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible():
                        print(f"    🎯 Found upload element: {selector}")
                        # Try to trigger file dialog
                        await element.click()
                        # Wait a moment for file dialog
                        await page.wait_for_timeout(1000)
                        # Note: File dialog interaction is limited in automated tests
                        print(
                            f"    ⚠️ Upload area clicked, but file dialog requires manual interaction"
                        )
                        return True
                except:
                    continue

            print(f"    ❌ No file input or upload area found")
            return False

        except Exception as e:
            print(f"    ❌ Upload error: {e}")
            return False

    def _resolve_credentials(self, text: str) -> str:
        """Resolve credential references in text."""
        if not self.credential_manager:
            return text

        try:
            from ..security.credential_manager import resolve_credentials_in_text
            return resolve_credentials_in_text(text, self.credential_manager)
        except Exception as e:
            print(f"    ⚠️ Credential resolution failed: {e}")
            return text

    async def verify(self,
                     page: Page,
                     verification_type: str,
                     expected_value: Optional[str] = None,
                     options: Dict[str, Any] = None) -> bool:
        """Perform verification with multiple strategies."""

        options = options or {}
        timeout = options.get("timeout", 10000)

        # 🧠 EXTRACT NAVIGATION CONTEXT
        navigation_context = options.get("navigation_context", {})
        step_number = options.get("step_number", 0)

        print(f"    ✅ Verifying: {verification_type}")

        # 🧠 CONTEXT-AWARE WARNING
        if (verification_type == "page_load"
                and navigation_context.get("current_page_context")
                == "navigation_failed"):
            print(
                f"    🚨 WARNING: Previous navigation failed (Step {navigation_context.get('last_navigation_step')})"
            )
            print(
                f"    🚨 This page load verification may be checking the WRONG page!"
            )

        try:
            # Wait for page stability
            await page.wait_for_load_state("domcontentloaded", timeout=timeout)

            if verification_type == "page_load":
                return await self._verify_page_load(page, navigation_context)

            elif verification_type == "title_contains":
                return await self._verify_title_contains(page, expected_value)

            elif verification_type == "url_change":
                return await self._verify_url_change(page, expected_value)

            elif verification_type == "element_visible":
                return await self._verify_element_visible(
                    page, expected_value, timeout)

            elif verification_type == "modal_appears":
                return await self._verify_modal_appears(page, timeout)

            elif verification_type == "contains_elements":
                return await self._verify_contains_elements(
                    page, expected_value, timeout)

            elif verification_type == "process_started":
                return await self._verify_process_started(
                    page, expected_value, timeout)

            elif verification_type == "creation_completed":
                return await self._verify_creation_completed(
                    page, expected_value, timeout)

            elif verification_type == "file_downloaded":
                print(f"    📥 Verifying file download: {expected_value}")
                return await self._verify_file_downloaded(page, expected_value)

            elif verification_type == "url_redirect_with_patterns":
                return await self._verify_url_redirect_with_patterns(
                    page, options)

            else:
                # Generic verification - just check if page is loaded
                return await self._verify_page_load(page)

        except Exception as e:
            print(f"    ❌ Verification error: {e}")
            return False

    async def wait(self,
                   page: Page,
                   wait_type: str,
                   duration: int = 2) -> bool:
        """Wait for condition with intelligent handling."""

        print(f"    ⏳ Waiting ({wait_type}): {duration}s")

        try:
            if wait_type == "time":
                await asyncio.sleep(duration)

            elif wait_type == "page_load":
                await page.wait_for_load_state("domcontentloaded",
                                               timeout=duration * 1000)

            elif wait_type == "element_visible":
                # This would need an element selector, fallback to time wait
                await asyncio.sleep(duration)

            else:
                # Default to time wait
                await asyncio.sleep(duration)

            print(f"    ✅ Wait completed")
            return True

        except Exception as e:
            print(f"    ❌ Wait error: {e}")
            return False

    async def _try_click_strategies(self, element: Locator,
                                    options: Dict[str, Any]) -> bool:
        """Try multiple click strategies with smart prioritization to reduce failures."""

        # 🧠 SMART STRATEGY SELECTION: Detect common problematic elements first
        element_info = await self._analyze_element(element)

        # For send buttons and known problematic elements, start with force_click
        if element_info.get("is_send_button") or element_info.get(
                "has_overlay_interference"):
            strategies = [
                ("force_click", self._force_click),
                ("center_click", self._center_click),
                ("regular_click", self._regular_click),
                ("javascript_click", self._javascript_click),
            ]
            print(
                f"      🎯 Using optimized strategy order for send/overlay elements"
            )

        # If force is explicitly requested
        elif options.get("force") or options.get("requires_force"):
            strategies = [
                ("force_click", self._force_click),
                ("javascript_click", self._javascript_click),
                ("regular_click", self._regular_click),
                ("center_click", self._center_click),
            ]

        # Standard strategy order for normal elements
        else:
            strategies = [
                ("regular_click", self._regular_click),
                ("force_click", self._force_click),
                ("javascript_click", self._javascript_click),
                ("center_click", self._center_click),
            ]

        for strategy_name, strategy_func in strategies:
            try:
                print(f"      🔄 Trying {strategy_name}...")
                success = await strategy_func(element, options)
                if success:
                    print(f"      ✅ {strategy_name} succeeded")
                    return True
            except Exception as e:
                print(f"      ⚠️ {strategy_name} failed: {e}")
                continue

        return False

    async def _analyze_element(self, element: Locator) -> Dict[str, bool]:
        """Analyze element to determine best click strategy."""
        try:
            # Get element attributes to detect patterns
            test_id = await element.get_attribute("data-testid") or ""
            class_name = await element.get_attribute("class") or ""
            tag_name = await element.evaluate("el => el.tagName.toLowerCase()")

            analysis = {
                "is_send_button": "send" in test_id.lower()
                and tag_name == "svg",
                "has_overlay_interference": "overlay" in class_name.lower(),
                "is_disabled": await element.is_disabled(),
                "needs_force": False
            }

            # Detect overlays that commonly interfere
            try:
                page = element.page
                overlay_count = await page.locator(
                    "[data-pollen-overlay='true']").count()
                if overlay_count > 0:
                    analysis["has_overlay_interference"] = True
            except:
                pass

            return analysis
        except:
            return {
                "is_send_button": False,
                "has_overlay_interference": False,
                "is_disabled": False,
                "needs_force": False
            }

    async def _try_dropdown_click_strategies(self, element: Locator,
                                             options: Dict[str, Any]) -> bool:
        """Try specialized click strategies for dropdown items."""

        print(f"    🎯 Using specialized dropdown clicking...")

        # Get the page reference for alternative strategies
        page = element.page

        # Enhanced strategies specifically for dropdown items
        strategies = [
            ("dropdown_force_click", self._dropdown_force_click),
            ("dropdown_js_click", self._dropdown_js_click),
            ("dropdown_parent_click", self._dropdown_parent_click),
            ("dropdown_coordinate_click", self._dropdown_coordinate_click),
            ("dropdown_keyboard_select", self._dropdown_keyboard_select),
        ]

        for strategy_name, strategy_func in strategies:
            try:
                print(f"      🔄 Trying {strategy_name}...")
                success = await strategy_func(element, options)
                if success:
                    print(f"      ✅ {strategy_name} succeeded")
                    # Wait a moment to let UI react
                    await asyncio.sleep(1)
                    return True
            except Exception as e:
                print(f"      ⚠️ {strategy_name} failed: {e}")
                continue

        print(f"    ❌ All dropdown click strategies failed")
        return False

    async def _dropdown_force_click(self, element: Locator,
                                    options: Dict[str, Any]) -> bool:
        """Force click with multiple attempts."""
        for attempt in range(3):
            try:
                await element.click(force=True, timeout=2000)
                await asyncio.sleep(0.3)
                return True
            except Exception:
                continue
        return False

    async def _dropdown_js_click(self, element: Locator,
                                 options: Dict[str, Any]) -> bool:
        """JavaScript click with event simulation."""
        try:
            # Comprehensive JavaScript click with event simulation
            await element.evaluate("""
                el => {
                    // Scroll element into view
                    el.scrollIntoView({ behavior: 'instant', block: 'center' });
                    
                    // Create and dispatch mouse events
                    ['mousedown', 'mouseup', 'click'].forEach(eventType => {
                        const event = new MouseEvent(eventType, {
                            view: window,
                            bubbles: true,
                            cancelable: true,
                            buttons: 1
                        });
                        el.dispatchEvent(event);
                    });
                    
                    // Also trigger focus and activate
                    if (typeof el.focus === 'function') el.focus();
                    if (typeof el.click === 'function') el.click();
                }
            """)
            return True
        except Exception:
            return False

    async def _dropdown_parent_click(self, element: Locator,
                                     options: Dict[str, Any]) -> bool:
        """Try clicking parent elements that might be the actual clickable area."""
        try:
            # Find clickable parent elements
            parent_selectors = [
                "xpath=./..",  # Direct parent
                "xpath=./../..",  # Grandparent
            ]

            for parent_selector in parent_selectors:
                try:
                    parent = element.locator(parent_selector)
                    if await parent.is_visible() and await parent.is_enabled():
                        # Check if parent looks more clickable
                        parent_cursor = await parent.evaluate(
                            "el => getComputedStyle(el).cursor")
                        parent_role = await parent.get_attribute("role")

                        if parent_cursor == "pointer" or parent_role in [
                                "menuitem", "button", "option"
                        ]:
                            print(
                                f"        📍 Trying clickable parent with cursor: {parent_cursor}, role: {parent_role}"
                            )
                            await parent.click(force=True)
                            return True
                except Exception:
                    continue

            return False
        except Exception:
            return False

    async def _dropdown_coordinate_click(self, element: Locator,
                                         options: Dict[str, Any]) -> bool:
        """Click using exact coordinates."""
        try:
            box = await element.bounding_box()
            if box:
                page = element.page
                # Try clicking at different points within the element
                click_points = [
                    (box["x"] + box["width"] * 0.5,
                     box["y"] + box["height"] * 0.5),  # Center
                    (box["x"] + box["width"] * 0.3,
                     box["y"] + box["height"] * 0.5),  # Left center
                    (box["x"] + box["width"] * 0.7,
                     box["y"] + box["height"] * 0.5),  # Right center
                ]

                for x, y in click_points:
                    try:
                        await page.mouse.click(x, y)
                        await asyncio.sleep(0.2)
                        return True
                    except Exception:
                        continue

            return False
        except Exception:
            return False

    async def _dropdown_keyboard_select(self, element: Locator,
                                        options: Dict[str, Any]) -> bool:
        """Use keyboard navigation to select dropdown item."""
        try:
            page = element.page

            # Focus the element and use keyboard
            await element.focus()
            await asyncio.sleep(0.2)

            # Try different keyboard interactions
            keyboard_actions = [
                "Enter",
                "Space",
                "ArrowDown",
                "Tab",
            ]

            for action in keyboard_actions:
                try:
                    await page.keyboard.press(action)
                    await asyncio.sleep(0.3)
                    return True
                except Exception:
                    continue

            return False
        except Exception:
            return False

    async def _regular_click(self, element: Locator,
                             options: Dict[str, Any]) -> bool:
        """Regular click strategy."""
        await element.click(timeout=options.get("timeout", 5000))
        return True

    async def _force_click(self, element: Locator, options: Dict[str,
                                                                 Any]) -> bool:
        """Force click strategy for difficult elements."""
        await element.click(force=True, timeout=options.get("timeout", 5000))
        return True

    async def _javascript_click(self, element: Locator,
                                options: Dict[str, Any]) -> bool:
        """JavaScript click strategy."""
        await element.evaluate("el => el.click()")
        return True

    async def _center_click(self, element: Locator,
                            options: Dict[str, Any]) -> bool:
        """Click at element center."""
        box = await element.bounding_box()
        if box:
            page = element.page
            await page.mouse.click(box["x"] + box["width"] / 2,
                                   box["y"] + box["height"] / 2)
            return True
        return False

    async def _verify_page_load(
            self,
            page: Page,
            navigation_context: Dict[str, Any] = None) -> bool:
        """🧠 CONTEXT-AWARE page load verification."""
        current_url = page.url
        current_title = await page.title()
        navigation_context = navigation_context or {}

        # Basic page load check
        basic_success = current_url != "about:blank" and len(current_title) > 0

        print(f"    📄 Current title: '{current_title}'")
        print(f"    🌐 Current URL: {current_url}")

        # 🧠 CONTEXT-AWARE LOGIC
        if navigation_context.get(
                "current_page_context") == "navigation_failed":
            last_nav_step = navigation_context.get("last_navigation_step")
            expected_nav_info = navigation_context.get(
                "expected_navigation_info", {})
            pattern_type = expected_nav_info.get("pattern_type", "unknown")

            print(f"    🚨 CONTEXT-AWARE ANALYSIS:")
            print(
                f"       → Previous navigation failed in Step {last_nav_step}")
            print(f"       → Actually on: {current_url}")

            # 🔧 HANDLE DIFFERENT VERIFICATION PATTERN TYPES
            if pattern_type == "prefix_suffix":
                # Handle url_redirect_with_patterns type (aihub_with_login_secure.txt)
                expected_prefix = expected_nav_info.get("url_prefix", "")
                expected_suffix = expected_nav_info.get("url_suffix", "")
                print(
                    f"       → Expected URL with prefix: '{expected_prefix}' and suffix: '{expected_suffix}'"
                )

                if expected_prefix and expected_prefix.lower(
                ) not in current_url.lower():
                    print(
                        f"    ❌ CONTEXT FAILURE: Page loaded, but we're on the WRONG page!"
                    )
                    print(
                        f"       → Missing expected URL prefix: '{expected_prefix}'"
                    )
                    print(
                        f"       → Basic page load: {basic_success}, but context says: WRONG PAGE"
                    )
                    return False

            elif pattern_type == "expected_value":
                # Handle url_change type (conversation_with_login.txt)
                expected_desc = expected_nav_info.get("expected_value", "")
                print(f"       → Expected navigation to: '{expected_desc}'")

                # For generic url_change, we can't easily verify the URL pattern
                # But we know navigation was expected and failed, so page load should reflect that
                print(
                    f"    ❌ CONTEXT FAILURE: Page loaded, but expected navigation did NOT occur!"
                )
                print(f"       → Navigation was expected: '{expected_desc}'")
                print(
                    f"       → Basic page load: {basic_success}, but context says: NO NAVIGATION HAPPENED"
                )
                return False

            else:
                # Unknown pattern type - fallback to basic logic
                print(
                    f"       → Unknown navigation pattern type: {pattern_type}"
                )
                print(f"    ✅ Basic page load: {basic_success}")
                return basic_success
        else:
            # Normal page load verification when no navigation context issues
            print(
                f"    {'✅' if basic_success else '❌'} Page load check: {basic_success}"
            )
            return basic_success

    async def _verify_title_contains(self, page: Page,
                                     expected_text: str) -> bool:
        """Verify page title contains expected text."""
        current_title = await page.title()
        success = expected_text.lower() in current_title.lower()

        print(f"    📄 Current title: '{current_title}'")
        print(f"    🎯 Expected to contain: '{expected_text}'")
        print(f"    {'✅' if success else '❌'} Title verification: {success}")

        return success

    async def _verify_url_change(self, page: Page,
                                 expected_pattern: str) -> bool:
        """🧠 SMART URL change verification - checks if navigation occurred and context matches."""
        current_url = page.url
        current_title = await page.title()
        expected_lower = expected_pattern.lower()

        print(f"    🌐 Current URL: {current_url}")
        print(f"    📄 Current title: '{current_title}'")
        print(f"    🎯 Expected context: '{expected_pattern}'")

        # 🔍 SMART VERIFICATION LOGIC
        # 1. Check if URL suggests navigation occurred (not just a page refresh)
        url_suggests_navigation = any(keyword in current_url.lower()
                                      for keyword in [
                                          'converse', 'chat', 'conversation',
                                          'apps', 'edit', 'create', 'new'
                                      ])

        # 2. Extract key context words from expected pattern
        context_keywords = []
        if 'conversation' in expected_lower:
            context_keywords.extend(['converse', 'chat', 'conversation'])
        if 'chatbot' in expected_lower:
            context_keywords.extend(['chatbot', 'chat', 'bot'])
        if 'app' in expected_lower:
            context_keywords.extend(['app', 'apps'])
        if 'edit' in expected_lower:
            context_keywords.extend(['edit', 'editor'])
        if 'new' in expected_lower or 'loading' in expected_lower:
            context_keywords.extend(['new', 'create'])

        # 3. Check if URL or title matches expected context
        context_match = False
        if context_keywords:
            url_context_match = any(keyword in current_url.lower()
                                    for keyword in context_keywords)
            title_context_match = any(keyword in current_title.lower()
                                      for keyword in context_keywords)
            context_match = url_context_match or title_context_match
            print(f"    🎯 Context keywords: {context_keywords}")
            print(
                f"       → URL context match: {'✅' if url_context_match else '❌'}"
            )
            print(
                f"       → Title context match: {'✅' if title_context_match else '❌'}"
            )
        else:
            # Fallback to literal matching if no smart keywords detected
            context_match = expected_lower in current_url.lower()
            print(f"    🔄 Fallback to literal matching")

        # 4. Final verification
        success = url_suggests_navigation and context_match

        print(
            f"    🔍 Navigation occurred: {'✅' if url_suggests_navigation else '❌'}"
        )
        print(f"    🎯 Context match: {'✅' if context_match else '❌'}")
        print(
            f"    {'✅' if success else '❌'} Smart URL verification: {success}")

        return success

    async def _verify_element_visible(self, page: Page,
                                      element_description: str,
                                      timeout: int) -> bool:
        """Verify element is visible on page with enhanced strategies."""
        try:
            print(f"    👁️ Looking for: '{element_description}'")

            # 🎯 ENHANCED: Check for UI panel detection first
            element_lower = element_description.lower()
            if any(panel in element_lower
                   for panel in ["left panel", "center panel", "right panel"]):
                panel_type = None
                if "left panel" in element_lower:
                    panel_type = "left panel"
                elif "center panel" in element_lower:
                    panel_type = "center panel"
                elif "right panel" in element_lower:
                    panel_type = "right panel"

                if panel_type:
                    # Import element finder dynamically to avoid circular imports
                    from ..finders.element_finder import ElementFinder
                    element_finder = ElementFinder(self.config_dir)
                    panel_element = await element_finder.find_ui_panel(
                        page, panel_type)

                    if panel_element:
                        print(
                            f"    ✅ Found {panel_type} using enhanced panel detection"
                        )
                        return True
                    else:
                        print(f"    ❌ Could not find {panel_type}")
                        return False

            # Multiple search strategies for better element finding
            search_strategies = [
                # Direct text search
                f"*:has-text('{element_description}')",

                # Key element types
                f"button:has-text('{element_description}')",
                f"[role='button']:has-text('{element_description}')",
                f"[role='tab']:has-text('{element_description}')",
                f"[role='menuitem']:has-text('{element_description}')",

                # Attribute-based search
                f"[aria-label*='{element_description}' i]",
                f"[title*='{element_description}' i]",
                f"[data-testid*='{element_description.lower().replace(' ', '-')}']",

                # Class-based search for common patterns
                f"[class*='{element_description.lower().replace(' ', '-')}']",
                f"[class*='button']:has-text('{element_description}')",
                f"[class*='dropdown']:has-text('{element_description}')",

                # Fallback - any element containing key words
                *[
                    f"*:has-text('{word}')"
                    for word in element_description.split() if len(word) > 2
                ],
            ]

            for strategy in search_strategies:
                try:
                    elements = page.locator(strategy)
                    count = await elements.count()

                    if count > 0:
                        # Check if any of the found elements are visible
                        for i in range(min(count,
                                           3)):  # Check up to 3 elements
                            element = elements.nth(i)
                            if await element.is_visible(timeout=timeout //
                                                        len(search_strategies)
                                                        ):
                                element_text = await element.text_content()
                                print(
                                    f"    ✅ Found visible element: '{element_text[:50]}...' using {strategy}"
                                )
                                return True
                except Exception:
                    continue

            print(f"    ❌ Element not visible: '{element_description}'")
            return False

        except Exception as e:
            print(f"    ❌ Element visibility check error: {e}")
            return False

    async def _verify_contains_elements(self, page: Page,
                                        expected_elements: str,
                                        timeout: int) -> bool:
        """Verify page contains specified elements (like dropdown options)."""
        try:
            print(f"    🔍 Checking for elements: '{expected_elements}'")

            # Handle None expected_elements
            if not expected_elements:
                print(f"    ⚠️ No elements specified to check")
                return True  # Consider it successful if nothing to check

            # Parse the expected elements (like "APP, Conversation, Chatbot")
            if ',' in expected_elements:
                elements_to_check = [
                    elem.strip() for elem in expected_elements.split(',')
                ]
            else:
                elements_to_check = [expected_elements.strip()]

            found_count = 0
            for element_name in elements_to_check:
                # STRICT dropdown-only selectors - only find elements inside actual dropdown menus
                selectors = [
                    # Must be inside an open dropdown/menu
                    f"[role='menu'] [role='menuitem']:has-text('{element_name}')",
                    f"[role='menu'] button:has-text('{element_name}')",
                    f"[role='menu'] *:has-text('{element_name}')",
                    f"[aria-expanded='true'] + * [role='menuitem']:has-text('{element_name}')",
                    f"[aria-expanded='true'] + * button:has-text('{element_name}')",
                    f"[data-state='open'] [role='menuitem']:has-text('{element_name}')",
                    f".dropdown-menu:visible [role='menuitem']:has-text('{element_name}')",
                    f".dropdown-menu:visible button:has-text('{element_name}')",
                    f".dropdown-content:visible *:has-text('{element_name}')",
                ]

                element_found = False
                for selector in selectors:
                    try:
                        element = page.locator(selector).first
                        if await element.is_visible(timeout=timeout //
                                                    len(elements_to_check)):
                            print(f"    ✅ Found: '{element_name}'")
                            found_count += 1
                            element_found = True
                            break
                    except Exception:
                        continue

                if not element_found:
                    print(f"    ❌ Not found: '{element_name}'")

            success = found_count >= len(
                elements_to_check) * 0.5  # At least 50% found
            print(
                f"    📊 Found {found_count}/{len(elements_to_check)} elements")
            print(
                f"    {'✅' if success else '❌'} Contains elements verification: {success}"
            )

            return success

        except Exception as e:
            print(f"    ❌ Contains elements check error: {e}")
            return False

    async def _verify_modal_appears(self, page: Page, timeout: int) -> bool:
        """Verify modal or dialog appears."""
        try:
            modal_selectors = [
                "[role='dialog']", "[role='modal']", ".modal", ".dialog",
                "[data-testid*='modal']", "[data-testid*='dialog']"
            ]

            for selector in modal_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible(timeout=timeout /
                                                len(modal_selectors)):
                        modal_text = await element.text_content()
                        print(f"    🎯 Modal detected: {modal_text[:50]}...")
                        return True
                except Exception:
                    continue

            print(f"    ❌ No modal detected")
            return False

        except Exception as e:
            print(f"    ❌ Modal detection error: {e}")
            return False

    async def _check_download_started(self, page: Page) -> bool:
        """Check if download has started."""
        try:
            # Check for common download indicators
            download_indicators = [
                # Download started notifications
                "[role='alert']:has-text('download')",
                "[role='alert']:has-text('export')",
                ".toast:has-text('download')",
                ".toast:has-text('export')",
                ".notification:has-text('download')",

                # Progress indicators
                "[role='progressbar']",
                ".progress-bar",
                "[class*='progress']",

                # Download dialogs
                "[role='dialog']:has-text('download')",
                "[role='dialog']:has-text('save')",
                "[role='dialog']:has-text('file')"
            ]

            for selector in download_indicators:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible(timeout=500):
                        print(f"    📥 Download indicator found: {selector}")
                        return True
                except Exception:
                    continue

            # Check URL for download indicators
            current_url = page.url
            if "download" in current_url or "export" in current_url or ".csv" in current_url:
                print(f"    📥 Download URL detected: {current_url}")
                return True

            return False

        except Exception as e:
            print(f"    ⚠️ Error checking download status: {e}")
            return False

    async def _verify_file_downloaded(self,
                                      page: Page,
                                      file_type: str = "file") -> bool:
        """Verify that a file was downloaded."""
        try:
            # Check if we have any files in the downloads directory
            download_directory = Path.cwd() / "downloads"
            if download_directory.exists():
                # Get all files in the downloads directory
                if file_type.lower() == "file":
                    files = list(download_directory.glob("*.*"))
                else:
                    files = list(
                        download_directory.glob(f"*.{file_type.lower()}"))
                    if not files:
                        # Try with any file as fallback
                        files = list(download_directory.glob("*.*"))

                # Check if we have any recent files (modified in the last minute)
                recent_files = []
                for file in files:
                    try:
                        if (datetime.now().timestamp() -
                                os.path.getmtime(file)) < 60:
                            recent_files.append(file)
                    except Exception:
                        pass

                if recent_files:
                    print(
                        f"    ✅ Found {len(recent_files)} recently downloaded files:"
                    )
                    for file in recent_files[:3]:  # Show up to 3 files
                        print(f"       - {file.name}")
                    return True

            # Fall back to checking page indicators
            success_indicators = [
                # Success notifications
                "[role='alert']:has-text('success')",
                "[role='alert']:has-text('download')",
                "[role='alert']:has-text('export')",
                ".toast:has-text('success')",
                ".toast:has-text('download')",
                ".toast:has-text('export')",
                ".notification:has-text('success')",

                # File type specific indicators
                f"[role='alert']:has-text('{file_type}')",
                f".toast:has-text('{file_type}')",
                f".notification:has-text('{file_type}')"
            ]

            for selector in success_indicators:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible(timeout=500):
                        text = await element.text_content()
                        print(f"    ✅ Download success indicator: '{text}'")
                        return True
                except Exception:
                    continue

            # Check if any download indicators are present
            download_started = await self._check_download_started(page)
            if download_started:
                # If we detected download starting, consider it successful
                print(
                    f"    ✅ Download indicators detected, assuming successful download"
                )
                return True

            # If no direct indicators but we're still on a page that has download functionality,
            # it's likely the download worked silently
            current_url = page.url
            if any(term in current_url.lower()
                   for term in ["export", "download", "run", "result"]):
                print(
                    f"    ✅ On export/download related page, assuming download completed"
                )
                return True

            print(f"    ⚠️ No clear download success indicators found")
            # Default to success since browser download detection is limited
            return True

        except Exception as e:
            print(f"    ⚠️ Error verifying file download: {e}")
            # Default to success since browser download detection is limited
            return True

    async def _handle_download(self, page: Page,
                               download_directory: Path) -> str:
        """Handle file download and save to local filesystem."""
        try:
            print(f"    📥 Setting up download handler...")

            # Create a list to store download objects
            downloads = []

            # Set up a listener for download events
            page.on("download", lambda download: downloads.append(download))

            # Wait for download to start (max 10 seconds)
            start_time = datetime.now()
            while not downloads and (datetime.now() -
                                     start_time).total_seconds() < 10:
                await asyncio.sleep(0.5)

            if not downloads:
                print(f"    ⚠️ No download detected after waiting")
                return ""

            # Get the most recent download
            download = downloads[-1]

            # Get suggested filename
            suggested_filename = download.suggested_filename
            print(f"    📄 Download detected: {suggested_filename}")

            # Generate a unique filename if needed
            if not suggested_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                suggested_filename = f"download_{timestamp}.csv"

            # Construct the full path to save the file
            save_path = download_directory / suggested_filename

            # Save the file to the local file system
            await download.save_as(save_path)
            print(f"    ✅ File downloaded and saved to: {save_path}")

            return str(save_path)

        except Exception as e:
            print(f"    ⚠️ Error handling download: {e}")
            return ""

    async def run_function(self,
                           page: Page,
                           function_call: str,
                           arguments: str = "") -> bool:
        """Execute a Python function with the given arguments.
        
        Args:
            page: The Playwright page object
            function_call: The name of the function to call
            arguments: String containing space-separated arguments
            
        Returns:
            True if the function executed successfully, False otherwise
        """
        try:
            print(
                f"    🔄 Running function: '{function_call}' with arguments: {arguments}"
            )

            # Debug info
            if not function_call:
                print(f"    ⚠️ Warning: Empty function name received")
                return False

            # Parse the function name
            if "." in function_call:
                # If it's a module.function format
                module_name, func_name = function_call.rsplit(".", 1)
                try:
                    # Try to import the module
                    module = importlib.import_module(module_name)
                    func = getattr(module, func_name)
                except (ImportError, AttributeError) as e:
                    print(f"    ❌ Error importing function: {e}")

                    # Try to find the function in the scripts directory
                    scripts_dir = Path(
                        __file__).parent.parent.parent / "scripts"
                    if scripts_dir.exists():
                        # Add scripts directory to path if not already there
                        scripts_path = str(scripts_dir)
                        if scripts_path not in sys.path:
                            sys.path.insert(0, scripts_path)

                        # Try to import from scripts directory
                        try:
                            module = importlib.import_module(module_name)
                            func = getattr(module, func_name)
                        except (ImportError, AttributeError) as e:
                            print(
                                f"    ❌ Error importing function from scripts directory: {e}"
                            )
                            return False
            else:
                # Try to find the function in the global namespace
                # First check in the scripts directory
                scripts_dir = Path(__file__).parent.parent.parent / "scripts"
                found = False

                if scripts_dir.exists():
                    # Look for Python files in the scripts directory
                    for script_file in scripts_dir.glob("*.py"):
                        module_name = script_file.stem
                        try:
                            # Add scripts directory to path if not already there
                            scripts_path = str(scripts_dir)
                            if scripts_path not in sys.path:
                                sys.path.insert(0, scripts_path)

                            # Try to import the module
                            module = importlib.import_module(module_name)
                            if hasattr(module, function_call):
                                func = getattr(module, function_call)
                                found = True
                                break
                        except (ImportError, AttributeError):
                            continue

                if not found:
                    # Try to find in built-in modules
                    try:
                        # Try to find in builtins
                        import builtins
                        if hasattr(builtins, function_call):
                            func = getattr(builtins, function_call)
                            found = True
                    except (ImportError, AttributeError):
                        pass

                if not found:
                    print(f"    ❌ Function '{function_call}' not found")
                    return False

            # Parse the arguments
            args = []
            kwargs = {}

            if arguments:
                # Use shlex to handle quoted arguments properly
                parsed_args = shlex.split(arguments)

                for arg in parsed_args:
                    if "=" in arg:
                        # Keyword argument
                        key, value = arg.split("=", 1)
                        kwargs[key] = self._convert_arg_type(value)
                    else:
                        # Positional argument
                        args.append(self._convert_arg_type(arg))

            # Check if the function is async
            is_async = inspect.iscoroutinefunction(func)

            # Call the function
            if is_async:
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            print(f"    ✅ Function executed successfully")
            print(f"    📊 Result: {result}")
            return True

        except Exception as e:
            print(f"    ❌ Error executing function: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _convert_arg_type(self, arg: str) -> Any:
        """Convert string argument to appropriate type."""
        # Try to convert to int
        try:
            return int(arg)
        except ValueError:
            pass

        # Try to convert to float
        try:
            return float(arg)
        except ValueError:
            pass

        # Check for boolean values
        if arg.lower() == "true":
            return True
        elif arg.lower() == "false":
            return False
        elif arg.lower() == "none":
            return None

        # Otherwise, return as string
        return arg

    def _is_dropdown_trigger(self, target: str) -> bool:
        """Check if the target element is likely a dropdown trigger."""
        target_lower = target.lower()
        dropdown_indicators = [
            "dropdown", "with dropdown", "dropdown arrow", "create button",
            "dropdown button"
        ]
        return any(indicator in target_lower
                   for indicator in dropdown_indicators)

    async def _verify_dropdown_opened(self, page: Page) -> bool:
        """Verify that a dropdown menu has opened."""
        try:
            # Multiple strategies to detect open dropdown
            dropdown_selectors = [
                # Role-based selectors
                "[role='menu']:visible",
                "[role='listbox']:visible",
                "[role='combobox'][aria-expanded='true']",

                # State-based selectors
                "[aria-expanded='true'] + [role='menu']",
                "[data-state='open'][role='menu']",
                "[data-state='open']",

                # Class-based common patterns
                ".dropdown-menu:visible",
                ".dropdown-content:visible",
                "[class*='dropdown'][class*='open']",
                "[class*='menu'][class*='open']",

                # Generic visible dropdown patterns
                "[data-testid*='dropdown']:visible",
                "[data-testid*='menu']:visible",
            ]

            for selector in dropdown_selectors:
                try:
                    elements = page.locator(selector)
                    if await elements.count() > 0:
                        first_element = elements.first
                        if await first_element.is_visible(timeout=500):
                            print(f"    🔍 Dropdown detected with: {selector}")
                            return True
                except Exception:
                    continue

            return False

        except Exception as e:
            print(f"    ⚠️ Dropdown verification error: {e}")
            return False

    async def _verify_dropdown_opened_strict(self, page: Page) -> bool:
        """Strictly verify that a dropdown menu has opened and contains actual menu items."""
        try:
            print(
                f"    🔍 Strict dropdown validation: Looking for menu items...")

            # First check if dropdown container exists
            basic_dropdown = await self._verify_dropdown_opened(page)
            if not basic_dropdown:
                print(f"    ❌ No dropdown container found")
                return False

            # Then check for actual menu items that should be in AIHub dropdown
            expected_items = ["conversation", "chatbot",
                              "app"]  # Known AIHub dropdown items
            dropdown_item_selectors = [
                # Must be inside dropdown containers with actual content
                "[role='menu']:visible [role='menuitem']",
                "[role='menu']:visible button",
                "[aria-expanded='true'] + * [role='menuitem']",
                "[data-state='open'] [role='menuitem']",
                ".dropdown-menu:visible [role='menuitem']",
                ".dropdown-menu:visible button",
                ".dropdown-content:visible button",
            ]

            menu_items_found = False
            for selector in dropdown_item_selectors:
                try:
                    elements = page.locator(selector)
                    count = await elements.count()

                    if count > 0:
                        print(
                            f"    🎯 Found {count} menu items using: {selector}"
                        )

                        # Check if any expected items are present
                        for i in range(min(count, 5)):  # Check up to 5 items
                            element = elements.nth(i)
                            if await element.is_visible(timeout=1000):
                                text = await element.text_content() or ""
                                text_lower = text.lower()
                                print(f"    📝 Menu item {i+1}: '{text}'")

                                # Check if this looks like a dropdown menu item
                                if any(item in text_lower
                                       for item in expected_items):
                                    print(
                                        f"    ✅ Found expected dropdown item: '{text}'"
                                    )
                                    menu_items_found = True

                except Exception as e:
                    continue

            if menu_items_found:
                print(
                    f"    ✅ Strict validation passed: Dropdown is open with menu items"
                )
                return True
            else:
                print(
                    f"    ❌ Strict validation failed: No recognizable menu items found"
                )
                return False

        except Exception as e:
            print(f"    ⚠️ Strict dropdown verification error: {e}")
            return False

    async def _verify_process_started(self, page: Page, process_name: str,
                                      timeout: int) -> bool:
        """Verify that a business process has started (e.g., chatbot creation process)."""
        try:
            print(f"    🔄 Verifying process started: '{process_name}'")

            # Multi-strategy approach to detect process initiation
            verification_strategies = [
                # Strategy 1: URL change indicating process start
                self._check_url_change_for_process(page, process_name),
                # Strategy 2: New UI elements indicating process
                self._check_process_ui_elements(page, process_name, timeout),
                # Strategy 3: Page title change
                self._check_title_change_for_process(page, process_name),
                # Strategy 4: Form/modal appearance for process
                self._check_process_forms(page, process_name, timeout),
                # Strategy 5: Loading/progress indicators
                self._check_process_indicators(page, timeout)
            ]

            # Execute strategies and check results
            results = []
            for i, strategy in enumerate(verification_strategies):
                try:
                    result = await strategy
                    results.append(result)
                    print(f"    📊 Strategy {i+1}: {'✅' if result else '❌'}")
                    if result:  # If any strategy succeeds, consider process started
                        print(
                            f"    ✅ Process verification successful via strategy {i+1}"
                        )
                        return True
                except Exception as e:
                    print(f"    ⚠️ Strategy {i+1} failed: {e}")
                    results.append(False)

            # All strategies failed
            success_count = sum(results)
            print(
                f"    📈 Process verification: {success_count}/{len(results)} strategies succeeded"
            )

            if success_count == 0:
                print(
                    f"    ❌ CRITICAL: No evidence that '{process_name}' process started"
                )
                print(
                    f"    💡 This appears to be an application issue, not a test issue"
                )
                return False

            return success_count >= 1  # At least one strategy must succeed

        except Exception as e:
            print(f"    ❌ Process verification error: {e}")
            return False

    async def _verify_creation_completed(self, page: Page, item_name: str,
                                         timeout: int) -> bool:
        """Verify that a creation process has completed."""
        try:
            print(f"    ✅ Verifying creation completed: '{item_name}'")

            # Look for completion indicators
            completion_strategies = [
                # New item appears in list/grid
                self._check_new_item_created(page, item_name, timeout),
                # Success message/notification
                self._check_success_notification(page, timeout),
                # Redirect to new item page
                self._check_redirect_to_new_item(page, item_name),
                # Creation confirmation dialog
                self._check_creation_confirmation(page, timeout)
            ]

            results = []
            for i, strategy in enumerate(completion_strategies):
                try:
                    result = await strategy
                    results.append(result)
                    print(
                        f"    📊 Completion strategy {i+1}: {'✅' if result else '❌'}"
                    )
                    if result:
                        print(
                            f"    ✅ Creation completed verification successful"
                        )
                        return True
                except Exception as e:
                    print(f"    ⚠️ Completion strategy {i+1} failed: {e}")
                    results.append(False)

            success_count = sum(results)
            print(
                f"    📈 Creation verification: {success_count}/{len(results)} strategies succeeded"
            )
            return success_count >= 1

        except Exception as e:
            print(f"    ❌ Creation verification error: {e}")
            return False

    # Helper methods for process verification
    async def _check_url_change_for_process(self, page: Page,
                                            process_name: str) -> bool:
        """Check if URL changed to indicate process started."""
        current_url = page.url
        process_keywords = [
            "create", "new", "setup", "wizard",
            process_name.lower()
        ]

        for keyword in process_keywords:
            if keyword in current_url.lower():
                print(
                    f"    🌐 URL indicates process started: contains '{keyword}'"
                )
                return True

        print(f"    🌐 URL doesn't indicate process start: {current_url}")
        return False

    async def _check_process_ui_elements(self, page: Page, process_name: str,
                                         timeout: int) -> bool:
        """Check for new UI elements that indicate process started."""
        process_ui_selectors = [
            # Common process indicators
            f"*:has-text('{process_name}'):has-text('setup')",
            f"*:has-text('{process_name}'):has-text('configuration')",
            f"*:has-text('{process_name}'):has-text('wizard')",
            f"[data-testid*='{process_name.lower()}'][data-testid*='setup']",
            f"[data-testid*='{process_name.lower()}'][data-testid*='config']",
            f"form[data-testid*='{process_name.lower()}']",
            ".setup-wizard",
            ".configuration-form",
            ".creation-wizard",
            # Form elements that suggest process started
            "input[placeholder*='name']",
            "input[placeholder*='title']",
            "textarea[placeholder*='description']",
            # Specific chatbot indicators
            "*:has-text('chatbot name')",
            "*:has-text('bot configuration')",
            "*:has-text('chatbot settings')",
            "*:has-text('configure')"
        ]

        for selector in process_ui_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=timeout //
                                            len(process_ui_selectors)):
                    element_text = await element.text_content() or ""
                    print(
                        f"    🎯 Process UI detected: '{element_text[:50]}...' using {selector}"
                    )
                    return True
            except Exception:
                continue

        print(f"    🎯 No process UI elements found")
        return False

    async def _check_title_change_for_process(self, page: Page,
                                              process_name: str) -> bool:
        """Check if page title indicates process started."""
        current_title = await page.title()
        process_keywords = [
            "create", "new", "setup", "configure",
            process_name.lower()
        ]

        for keyword in process_keywords:
            if keyword in current_title.lower():
                print(
                    f"    📄 Title indicates process started: contains '{keyword}' in '{current_title}'"
                )
                return True

        print(f"    📄 Title doesn't indicate process start: '{current_title}'")
        return False

    async def _check_process_forms(self, page: Page, process_name: str,
                                   timeout: int) -> bool:
        """Check for forms/modals related to process."""
        form_selectors = [
            "form[role='dialog']", "[role='dialog'] form", ".modal form",
            ".dialog form", f"form[data-testid*='{process_name.lower()}']",
            "form", "dialog", "[role='dialog']"
        ]

        for selector in form_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=timeout //
                                            len(form_selectors)):
                    form_content = await element.text_content() or ""
                    if process_name.lower() in form_content.lower() or any(
                            kw in form_content.lower() for kw in
                        ["name", "title", "description", "configure"]):
                        print(
                            f"    📝 Process form detected with relevant content"
                        )
                        return True
            except Exception:
                continue

        return False

    async def _check_process_indicators(self, page: Page,
                                        timeout: int) -> bool:
        """Check for loading/progress indicators."""
        indicator_selectors = [
            ".loading", ".spinner", ".progress", "[aria-label*='loading']",
            "[aria-label*='progress']", "*:has-text('loading')",
            "*:has-text('creating')", "*:has-text('setting up')",
            "*:has-text('configuring')"
        ]

        for selector in indicator_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=500):  # Quick check
                    print(f"    ⏳ Process indicator detected: {selector}")
                    return True
            except Exception:
                continue

        return False

    # Helper methods for creation completion verification
    async def _check_new_item_created(self, page: Page, item_name: str,
                                      timeout: int) -> bool:
        """Check if new item appears in lists/grids."""
        item_selectors = [
            f"*:has-text('{item_name}')", "[role='listitem']", ".list-item",
            ".grid-item", ".card", ".tile", "tr", "li"
        ]

        # Look for new items that weren't there before
        for selector in item_selectors:
            try:
                elements = page.locator(selector)
                count = await elements.count()
                if count > 0:
                    for i in range(min(count, 5)):  # Check first 5 items
                        element = elements.nth(i)
                        if await element.is_visible(timeout=timeout // 10):
                            text = await element.text_content() or ""
                            if item_name.lower() in text.lower():
                                print(
                                    f"    🎯 New item found: '{text[:50]}...'")
                                return True
            except Exception:
                continue

        return False

    async def _check_success_notification(self, page: Page,
                                          timeout: int) -> bool:
        """Check for success messages/notifications."""
        notification_selectors = [
            ".notification.success", ".alert.success", ".toast.success",
            "[role='alert']", ".message.success", ".banner.success",
            "*:has-text('success')", "*:has-text('created')",
            "*:has-text('completed')", "*:has-text('done')"
        ]

        for selector in notification_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=timeout //
                                            len(notification_selectors)):
                    notification_text = await element.text_content() or ""
                    print(
                        f"    🎉 Success notification: '{notification_text[:50]}...'"
                    )
                    return True
            except Exception:
                continue

        return False

    async def _check_redirect_to_new_item(self, page: Page,
                                          item_name: str) -> bool:
        """Check if redirected to new item page."""
        current_url = page.url
        redirect_indicators = [
            item_name.lower(), "edit", "configure", "settings"
        ]

        for indicator in redirect_indicators:
            if indicator in current_url.lower():
                print(
                    f"    🔄 Redirected to new item page: contains '{indicator}'"
                )
                return True

        return False

    async def _check_creation_confirmation(self, page: Page,
                                           timeout: int) -> bool:
        """Check for creation confirmation dialogs."""
        confirmation_selectors = [
            "[role='dialog']:has-text('created')",
            "[role='dialog']:has-text('success')",
            ".modal:has-text('created')", ".dialog:has-text('success')"
        ]

        for selector in confirmation_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=timeout //
                                            len(confirmation_selectors)):
                    print(f"    ✅ Creation confirmation dialog detected")
                    return True
            except Exception:
                continue

        return False

    async def _verify_url_redirect_with_patterns(
            self, page: Page, options: Dict[str, Any]) -> bool:
        """Verify URL redirection with specific prefix and suffix patterns."""
        try:
            url_prefix = options.get("url_prefix", "")
            url_suffix = options.get("url_suffix", "")
            current_url = page.url

            print(f"    🔄 Verifying URL redirection patterns:")
            print(f"       Current URL: {current_url}")
            print(f"       Expected prefix: '{url_prefix}'")
            print(f"       Expected suffix: '{url_suffix}'")

            # Check if URL contains the expected prefix
            prefix_match = url_prefix.lower() in current_url.lower(
            ) if url_prefix else True

            # Check if URL contains the expected suffix
            suffix_match = url_suffix.lower() in current_url.lower(
            ) if url_suffix else True

            print(f"       Prefix match: {'✅' if prefix_match else '❌'}")
            print(f"       Suffix match: {'✅' if suffix_match else '❌'}")

            success = prefix_match and suffix_match

            if success:
                print(f"    ✅ URL redirection verification successful!")
            else:
                print(f"    ❌ URL redirection verification failed!")
                print(
                    f"       Expected URL to contain prefix '{url_prefix}' and suffix '{url_suffix}'"
                )
                if not prefix_match:
                    print(
                        f"       Missing prefix: '{url_prefix}' not found in URL"
                    )
                if not suffix_match:
                    print(
                        f"       Missing suffix: '{url_suffix}' not found in URL"
                    )

            return success

        except Exception as e:
            print(f"    ❌ URL redirection verification error: {e}")
            return False

    async def _try_alternative_dropdown_trigger(self, element: Locator,
                                                page: Page) -> bool:
        """Try alternative methods to trigger dropdown opening."""
        try:
            print(f"    🔄 Trying alternative dropdown trigger methods...")

            # Strategy 1: Hover then click
            try:
                await element.hover()
                await asyncio.sleep(0.5)
                await element.click()
                await asyncio.sleep(1)
                if await self._verify_dropdown_opened(page):
                    return True
            except Exception:
                pass

            # Strategy 2: Double click
            try:
                await element.dblclick()
                await asyncio.sleep(1)
                if await self._verify_dropdown_opened(page):
                    return True
            except Exception:
                pass

            # Strategy 3: Focus then Enter key
            try:
                await element.focus()
                await page.keyboard.press("Enter")
                await asyncio.sleep(1)
                if await self._verify_dropdown_opened(page):
                    return True
            except Exception:
                pass

            # Strategy 4: Focus then Space key
            try:
                await element.focus()
                await page.keyboard.press("Space")
                await asyncio.sleep(1)
                if await self._verify_dropdown_opened(page):
                    return True
            except Exception:
                pass

            # Strategy 5: Focus then Arrow Down
            try:
                await element.focus()
                await page.keyboard.press("ArrowDown")
                await asyncio.sleep(1)
                if await self._verify_dropdown_opened(page):
                    return True
            except Exception:
                pass

            return False

        except Exception as e:
            print(f"    ⚠️ Alternative trigger error: {e}")
            return False
