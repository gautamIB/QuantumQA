#!/usr/bin/env python3
"""
Smart Element Finder - Intelligent element detection using multiple strategies
Works across any application without hardcoded selectors
"""

import asyncio
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List
from playwright.async_api import Page, Locator


class ElementFinder:
    """Smart element finder using AI-like strategies."""

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.selector_strategies = self._load_selector_strategies()

    async def find_clickable_element(
            self,
            page: Page,
            target: str,
            context: Dict[str, Any] = None) -> Optional[Locator]:
        """Find clickable element using intelligent strategies."""

        context = context or {}
        print(f"    🔍 Smart search for clickable: '{target}'")

        # Generate multiple selector strategies
        selectors = self._generate_click_selectors(target, context)

        # Try each selector in priority order
        for i, selector_info in enumerate(selectors):
            try:
                selector = selector_info["selector"]
                strategy = selector_info["strategy"]

                element = page.locator(selector).first

                # Check if element exists and is visible with increased timeout for export buttons
                timeout = 5000 if "export" in selector.lower() else 2000
                if await element.count() > 0 and await element.is_visible(
                        timeout=timeout):
                    # print(f"    ✅ Found using {strategy}: {selector} {element} {element.text_content()}")
                    print(f"    ✅ Found using {strategy}: {selector}")

                    # Additional validation for complex elements
                    if context.get("element_type") == "dropdown":
                        # For dropdown items, be more lenient - check if it's in a dropdown context
                        is_in_dropdown = context.get(
                            "parent_type"
                        ) == "dropdown" or "dropdown" in target.lower()

                        if is_in_dropdown:
                            # For dropdown items, visibility is often sufficient
                            print(
                                f"    🎯 Dropdown context detected - returning element for specialized handling"
                            )
                            return element
                        else:
                            # For non-dropdown items, use strict validation
                            is_clickable = await self._validate_clickable_element(
                                element)
                            if is_clickable:
                                return element
                            else:
                                print(
                                    f"    ⚠️ Element not truly clickable, continuing search..."
                                )
                                continue

                    return element

            except Exception as e:
                # Continue to next selector silently
                pass

        print(f"    ❌ Could not find clickable element: '{target}'")

        # Special handling for dropdown items - they might need time to appear
        if "dropdown" in target.lower() or context.get(
                "parent_type") == "dropdown":
            print(f"    🔄 Attempting dropdown-specific search with wait...")
            return await self._find_dropdown_item_with_wait(page, target)

        return None

    async def _find_dropdown_item_with_wait(self, page: Page,
                                            target: str) -> Optional[Locator]:
        """Specialized finder for dropdown items with wait strategies."""

        print(f"    ⏳ Waiting for dropdown items to appear...")

        # Wait for dropdown to be fully rendered
        await asyncio.sleep(1)

        # Enhanced selectors specifically for dropdown items
        dropdown_selectors = [
            # Most specific - role-based
            f"[role='menuitem']:has-text('{target}')",
            f"button[role='menuitem']:has-text('{target}')",
            f"[role='option']:has-text('{target}')",

            # Structure-based with role - more specific
            f"[role='menu'] button:has-text('{target}')",
            f"[role='menu'] [role='menuitem']:has-text('{target}')",
            f"[role='menu'] a:has-text('{target}')",
            f"[role='menu'] div:has-text('{target}')",
            f"ul[role='menu'] li:has-text('{target}')",
            f"div[role='menu'] *:has-text('{target}')",

            # Expanded state selectors - more comprehensive
            f"[aria-expanded='true'] ~ * button:has-text('{target}')",
            f"[aria-expanded='true'] + * [role='menuitem']:has-text('{target}')",
            f"[aria-expanded='true'] + * *:has-text('{target}')",

            # Generic visible dropdown patterns - expanded
            f".dropdown-menu button:has-text('{target}')",
            f".dropdown-menu a:has-text('{target}')",
            f".dropdown-menu *:has-text('{target}')",
            f".dropdown-content *:has-text('{target}')",
            f"[data-testid*='menu'] *:has-text('{target}')",
            f"[data-testid*='dropdown'] *:has-text('{target}')",

            # Find any parent that contains the text and has clickable children
            f"*:has-text('{target}'):has(button)",
            f"*:has-text('{target}'):has([role='menuitem'])",
            f"*:has-text('{target}'):has(a)",

            # Last resort - any visible element with text that might be clickable
            f"*:has-text('{target}'):visible",
            f"div:has-text('{target}'):visible",
            f"span:has-text('{target}'):visible",
            f"li:has-text('{target}'):visible",
        ]

        for selector in dropdown_selectors:
            try:
                elements = page.locator(selector)
                count = await elements.count()

                if count > 0:
                    for i in range(count):
                        element = elements.nth(i)

                        # Check if element is actually visible
                        if await element.is_visible(timeout=1000):
                            # Additional validation for dropdown items
                            is_in_dropdown = await element.evaluate("""
                                el => {
                                    // Check if element is inside a dropdown-like container
                                    let parent = el.closest('[role="menu"], .dropdown-menu, .dropdown-content, [data-testid*="menu"], [data-testid*="dropdown"]');
                                    return parent !== null;
                                }
                            """)

                            if is_in_dropdown:
                                # For dropdown items, be more liberal about clickability
                                print(
                                    f"    ✅ Found dropdown item using: {selector}"
                                )

                                # Try to check if it's enabled, but don't be strict
                                try:
                                    is_enabled = await element.is_enabled(
                                        timeout=500)
                                    if is_enabled:
                                        print(
                                            f"    🎯 Element appears enabled - returning as-is"
                                        )
                                        return element
                                    else:
                                        print(
                                            f"    ⚠️ Element appears disabled, but trying clickable parent..."
                                        )
                                        # Try to find clickable parent
                                        clickable_parent = await self._find_clickable_parent(
                                            element)
                                        if clickable_parent:
                                            print(
                                                f"    ✅ Found clickable parent for dropdown item"
                                            )
                                            return clickable_parent
                                        else:
                                            print(
                                                f"    🔄 No clickable parent found, returning original element for specialized clicking"
                                            )
                                            return element  # Let specialized dropdown clicking handle it
                                except Exception:
                                    print(
                                        f"    🎯 Clickability check failed, but returning element for dropdown-specific handling"
                                    )
                                    return element  # Return anyway for dropdown-specific strategies
            except Exception as e:
                continue

        print(
            f"    ❌ Could not find dropdown item: '{target}' even with specialized search"
        )
        return None

    async def _find_clickable_parent(self,
                                     element: Locator) -> Optional[Locator]:
        """Find a clickable parent element for a non-clickable child."""
        try:
            # Try to find clickable parents by traversing up the DOM
            parent_selectors = [
                "xpath=./..",  # Direct parent
                "xpath=./../../..",  # Grandparent 
                "xpath=./../../../..",  # Great-grandparent
            ]

            for parent_selector in parent_selectors:
                try:
                    parent = element.locator(parent_selector)
                    if await parent.is_visible(timeout=500
                                               ) and await parent.is_enabled(
                                                   timeout=500):
                        # Check if parent looks clickable (has click handlers, proper role, etc.)
                        is_clickable = await parent.evaluate("""
                            el => {
                                const style = window.getComputedStyle(el);
                                const hasClickHandlers = el.onclick !== null || 
                                                        el.addEventListener !== undefined;
                                const hasClickableCursor = style.cursor === 'pointer';
                                const hasClickableRole = el.getAttribute('role') === 'menuitem' ||
                                                        el.getAttribute('role') === 'button' ||
                                                        el.tagName.toLowerCase() === 'button' ||
                                                        el.tagName.toLowerCase() === 'a';
                                
                                return hasClickableCursor || hasClickableRole || hasClickHandlers;
                            }
                        """)

                        if is_clickable:
                            return parent
                except Exception:
                    continue

            return None

        except Exception:
            return None

    async def find_input_field(
            self,
            page: Page,
            field_description: str,
            field_type: Optional[str] = None) -> Optional[Locator]:
        """Find input field using intelligent strategies."""

        print(f"    🔍 Smart search for input field: '{field_description}'")

        # Generate field selectors based on description and type
        selectors = self._generate_field_selectors(field_description,
                                                   field_type)

        for selector_info in selectors:
            try:
                selector = selector_info["selector"]
                strategy = selector_info["strategy"]

                element = page.locator(selector).first

                if await element.count() > 0 and await element.is_visible(
                        timeout=2000):
                    # Verify it's actually an input field
                    tag_name = await element.evaluate(
                        "el => el.tagName.toLowerCase()")
                    if tag_name in ["input", "textarea"]:
                        print(
                            f"    ✅ Found input field using {strategy}: {selector}"
                        )
                        return element

            except Exception:
                continue

        print(f"    ❌ Could not find input field: '{field_description}'")
        return None

    def _generate_click_selectors(
            self, target: str, context: Dict[str,
                                             Any]) -> List[Dict[str, Any]]:
        """Generate intelligent click selectors based on target and context."""

        selectors = []
        target_lower = target.lower()

        # Split target into words for partial matching later
        target_words = target.split()
        first_word = target_words[0] if target_words else target

        # Strategy 1: Direct text matching (highest priority)
        selectors.extend([
            {
                "selector": f"text='{target}'",
                "strategy": "exact_text",
                "priority": 1
            },
            {
                "selector": f"text={target}",
                "strategy": "text_contains",
                "priority": 2
            },
        ])

        # Strategy 2: Enhanced semantic element matching with visual cues
        if (context.get("element_type") in ["dropdown-button", "dropdown"]
                or context.get("has_dropdown") or "dropdown" in target_lower):
            # Prioritize dropdown buttons with visual indicators (border + arrow)
            selectors.extend([
                # Highest priority: buttons with actual dropdown functionality
                {
                    "selector":
                    f"button:has-text('{target}')[aria-haspopup='true']:not([role='tab'])",
                    "strategy": "dropdown_button_aria",
                    "priority": 1
                },
                {
                    "selector":
                    f"button:has-text('{target}')[aria-expanded]:not([role='tab'])",
                    "strategy": "dropdown_button_expanded",
                    "priority": 1
                },

                # High priority: buttons with visual borders and dropdown indicators
                {
                    "selector":
                    f"button:has-text('{target}')[class*='border'][aria-haspopup='true']",
                    "strategy": "bordered_dropdown_aria",
                    "priority": 2
                },
                {
                    "selector":
                    f"button:has-text('{target}')[style*='border'][aria-haspopup='true']",
                    "strategy": "styled_dropdown_aria",
                    "priority": 2
                },
                {
                    "selector":
                    f"button:has-text('{target}'):has(svg, [class*='arrow'], [class*='chevron'])",
                    "strategy": "button_with_arrow",
                    "priority": 2
                },

                # Medium priority: general dropdown indicators
                {
                    "selector":
                    f"button:has-text('{target}')[class*='dropdown']:not([role='tab'])",
                    "strategy": "dropdown_button_class",
                    "priority": 3
                },
                {
                    "selector":
                    f"button:has-text('{target}')[data-toggle='dropdown']:not([role='tab'])",
                    "strategy": "dropdown_toggle",
                    "priority": 3
                },

                # Lower priority: exclude tabs but include buttons
                {
                    "selector":
                    f"button:has-text('{target}'):not([role='tab']):not([class*='tab'])",
                    "strategy": "button_not_tab",
                    "priority": 4
                },
                {
                    "selector":
                    f"[role='button']:has-text('{target}'):not([role='tab']):not([class*='tab'])",
                    "strategy": "role_button_not_tab",
                    "priority": 5
                },
            ])
        elif context.get("element_type") == "bordered-button" or context.get(
                "has_border"):
            # Prioritize buttons with visual borders/boundaries
            selectors.extend([
                {
                    "selector":
                    f"button:has-text('{target}')[class*='border']:not([role='tab'])",
                    "strategy": "bordered_button",
                    "priority": 2
                },
                {
                    "selector":
                    f"button:has-text('{target}')[style*='border']:not([role='tab'])",
                    "strategy": "styled_border_button",
                    "priority": 2
                },
                {
                    "selector":
                    f"button:has-text('{target}')[class*='outline']:not([role='tab'])",
                    "strategy": "outlined_button",
                    "priority": 2
                },
                {
                    "selector":
                    f"button:has-text('{target}'):not([role='tab']):not([class*='tab'])",
                    "strategy": "button_not_tab",
                    "priority": 3
                },
            ])
        elif context.get(
                "element_type") == "button" or "button" in target_lower:
            if context.get("exclude_tabs"):
                # Explicitly exclude tab elements
                selectors.extend([
                    {
                        "selector":
                        f"button:has-text('{target}'):not([role='tab'])",
                        "strategy": "button_not_tab",
                        "priority": 3
                    },
                    {
                        "selector":
                        f"[role='button']:has-text('{target}'):not([role='tab'])",
                        "strategy": "role_button_not_tab",
                        "priority": 3
                    },
                ])
            else:
                # Regular button matching
                selectors.extend([
                    {
                        "selector": f"button:has-text('{target}')",
                        "strategy": "button_text",
                        "priority": 3
                    },
                    {
                        "selector": f"[role='button']:has-text('{target}')",
                        "strategy": "button_role",
                        "priority": 4
                    },
                ])

        # Strategy 3: Link matching
        if context.get("element_type") == "link" or any(
                word in target_lower
                for word in ["sign in", "login", "register"]):
            selectors.extend([
                {
                    "selector": f"a:has-text('{target}')",
                    "strategy": "link_text",
                    "priority": 5
                },
                {
                    "selector": f"[href*='{target.lower()}']",
                    "strategy": "link_href",
                    "priority": 6
                },
            ])

        # Special handling for Submit buttons in dialogs
        if "submit" in target_lower and ("dialog" in target_lower
                                         or "modal" in target_lower
                                         or "popup" in target_lower):
            print(
                f"    🔍 Adding special selectors for submit buttons in dialogs"
            )
            selectors.extend([{
                "selector":
                ".dialog__actions__content__primary button.primary",
                "strategy": "dialog_primary_button",
                "priority": 1
            }, {
                "selector": "button[data-target='submitButton']",
                "strategy": "submit_button_target",
                "priority": 1
            }, {
                "selector": ".dialog button.primary",
                "strategy": "dialog_primary",
                "priority": 2
            }, {
                "selector": ".modal button.primary",
                "strategy": "modal_primary",
                "priority": 2
            }, {
                "selector":
                "button.primary:has-text('Submit'), button.primary:has-text('Export')",
                "strategy": "primary_submit_export",
                "priority": 3
            }])

        # Strategy 3.5: Fallback for multi-word targets - try first word or partial match (only used if exact matches fail)
        if len(target_words) > 1:
            print(f"    🔍 Adding fallback selectors for partial text matching")
            # Add fallback selectors with much lower priority
            selectors.extend([
                {
                    "selector": f"text='{first_word}'",
                    "strategy": "first_word_exact",
                    "priority": 15
                },
                {
                    "selector": f"text={first_word}",
                    "strategy": "first_word_contains",
                    "priority": 16
                },
                {
                    "selector": f"button:has-text('{first_word}')",
                    "strategy": "button_first_word",
                    "priority": 17
                },
                {
                    "selector": f"a:has-text('{first_word}')",
                    "strategy": "link_first_word",
                    "priority": 18
                },
                {
                    "selector": f"*:has-text('{first_word}'):visible",
                    "strategy": "generic_first_word",
                    "priority": 19
                },
            ])

            # Strategy 4: Special handling for icon buttons with tooltips/data-content
        if "export" in target_lower or "download" in target_lower:
            print(
                f"    🔍 Adding special selectors for export/download buttons")
            selectors.extend([
                {
                    "selector": "[data-content='Export']",
                    "strategy": "export_data_content",
                    "priority": 1  # Increased priority
                },
                {
                    "selector":
                    "[data-content='export']",  # Added lowercase variant
                    "strategy": "export_data_content_lowercase",
                    "priority": 1
                },
                {
                    "selector":
                    "[data-content*='Export' i]",  # Added case-insensitive variant
                    "strategy": "export_data_content_insensitive",
                    "priority": 1
                },
                {
                    "selector": "button.tooltip[data-content='Export']",
                    "strategy": "export_tooltip_button",
                    "priority": 2
                },
                {
                    "selector":
                    "button[data-content='Export']",  # Added button-specific selector
                    "strategy": "export_button_data_content",
                    "priority": 1
                },
                {
                    "selector":
                    "*[data-content='Export']",  # Added wildcard selector
                    "strategy": "export_any_data_content",
                    "priority": 2
                },
                {
                    "selector":
                    "button:has(.fa-file-download), button:has(.icon-export)",
                    "strategy": "download_icon_button",
                    "priority": 2
                },
                {
                    "selector":
                    "[data-ui-tooltip='true']:has(.fa-file-download)",
                    "strategy": "tooltip_download_icon",
                    "priority": 2
                },
                {
                    "selector":
                    "[aria-label*='export' i], [aria-label*='download' i]",
                    "strategy": "export_aria_label",
                    "priority": 3
                },
                {
                    "selector": "button.ui.button.primary:has-text('Export')",
                    "strategy": "export_primary_button",
                    "priority": 1
                },
                {
                    "selector":
                    ".dialog__actions__content__primary button:has-text('Export')",
                    "strategy": "dialog_export_button",
                    "priority": 1
                },
                {
                    "selector": "button[data-target='submitButton']",
                    "strategy": "submit_button_target",
                    "priority": 1
                }
            ])

        # Strategy 5: Context-aware matching
        if context.get("color"):
            color = context["color"]
            selectors.extend([
                {
                    "selector":
                    f"button[class*='{color}']:has-text('{target}')",
                    "strategy": f"{color}_button",
                    "priority": 7
                },
                {
                    "selector":
                    f"[class*='{color}'][class*='button']:has-text('{target}')",
                    "strategy": f"{color}_class",
                    "priority": 8
                },
            ])

        # Strategy 5: Enhanced position-aware matching
        if context.get("position"):
            position = context["position"]

            if position in ["top-right", "top-right-corner"]:
                # Build exclusion selectors for left-side elements
                left_exclusions = ""
                if context.get("exclude_left"):
                    left_exclusions = ":not([class*='left']):not([class*='nav']):not([class*='sidebar']):not([class*='menu']):not([data-testid*='nav']):not([data-testid*='left'])"

                # High-priority selectors for top-right positioned elements with left exclusions
                selectors.extend([
                    # Most specific - top right combination classes
                    {
                        "selector":
                        f"[class*='top'][class*='right'] button:has-text('{target}')",
                        "strategy": "top_right_specific",
                        "priority": 1
                    },

                    # Header and toolbar areas (most likely for top-right buttons)
                    {
                        "selector":
                        f"header button:has-text('{target}'){left_exclusions}",
                        "strategy": "header_button",
                        "priority": 2
                    },
                    {
                        "selector":
                        f"[class*='header'] button:has-text('{target}'){left_exclusions}",
                        "strategy": "header_class",
                        "priority": 2
                    },
                    {
                        "selector":
                        f"[class*='toolbar'] button:has-text('{target}'){left_exclusions}",
                        "strategy": "toolbar_button",
                        "priority": 2
                    },
                    {
                        "selector":
                        f"[class*='action'] button:has-text('{target}'){left_exclusions}",
                        "strategy": "action_button",
                        "priority": 2
                    },

                    # Exclude tabs and left-side elements completely
                    {
                        "selector":
                        f"button:has-text('{target}'):not([role='tab']):not([class*='tab']){left_exclusions}",
                        "strategy": "button_not_tab_not_left",
                        "priority": 3
                    },

                    # Position-based with strong right-side preference
                    {
                        "selector":
                        f"[class*='right'] button:has-text('{target}'){left_exclusions}",
                        "strategy": "right_positioned",
                        "priority": 4
                    },

                    # Generic but with exclusions
                    {
                        "selector":
                        f"button:has-text('{target}'){left_exclusions}",
                        "strategy": "button_no_left",
                        "priority": 8
                    },
                ])
            else:
                # Generic position matching for other positions
                selectors.extend([
                    {
                        "selector":
                        f"[class*='{position}'] *:has-text('{target}')",
                        "strategy": f"{position}_positioned",
                        "priority": 9
                    },
                ])

        # Strategy 6: Enhanced dropdown-specific matching (for menu items)
        if context.get(
                "parent_type"
        ) == "dropdown" or "dropdown" in target_lower or "from dropdown" in target_lower:
            selectors.extend([
                # High priority - exact role matching
                {
                    "selector": f"[role='menuitem']:has-text('{target}')",
                    "strategy": "menuitem",
                    "priority": 1
                },
                {
                    "selector":
                    f"button[role='menuitem']:has-text('{target}')",
                    "strategy": "button_menuitem",
                    "priority": 1
                },
                {
                    "selector": f"[role='option']:has-text('{target}')",
                    "strategy": "option",
                    "priority": 2
                },

                # Medium priority - structural matching
                {
                    "selector": f"li[role='menuitem']:has-text('{target}')",
                    "strategy": "li_menuitem",
                    "priority": 3
                },
                {
                    "selector": f"[role='menu'] button:has-text('{target}')",
                    "strategy": "menu_button",
                    "priority": 3
                },
                {
                    "selector":
                    f"[role='menu'] [role='menuitem']:has-text('{target}')",
                    "strategy": "nested_menuitem",
                    "priority": 3
                },

                # Lower priority - broader matching
                {
                    "selector": f"[role='menu'] *:has-text('{target}')",
                    "strategy": "menu_child",
                    "priority": 5
                },
                {
                    "selector": f"ul[role='menu'] li:has-text('{target}')",
                    "strategy": "menu_list_item",
                    "priority": 6
                },
                {
                    "selector": f"div[role='menu'] *:has-text('{target}')",
                    "strategy": "div_menu_child",
                    "priority": 7
                },

                # Fallback - visible dropdown items
                {
                    "selector":
                    f"[aria-expanded='true'] + * [role='menuitem']:has-text('{target}')",
                    "strategy": "expanded_menuitem",
                    "priority": 8
                },
                {
                    "selector":
                    f"[data-state='open'] [role='menuitem']:has-text('{target}')",
                    "strategy": "open_menuitem",
                    "priority": 8
                },
            ])

        # Strategy 7: Advanced attribute matching
        selectors.extend([
            {
                "selector": f"[aria-label*='{target}' i]",
                "strategy": "aria_label",
                "priority": 10
            },
            {
                "selector": f"[title*='{target}' i]",
                "strategy": "title_attr",
                "priority": 11
            },
            {
                "selector":
                f"[data-testid*='{target.lower().replace(' ', '-')}']",
                "strategy": "test_id",
                "priority": 12
            },
        ])

        # Strategy 8: Generic element matching (lowest priority)
        selectors.extend([
            {
                "selector": f"*:has-text('{target}')",
                "strategy": "generic_text",
                "priority": 15
            },
        ])

        # Sort by priority (lower number = higher priority)
        selectors.sort(key=lambda x: x["priority"])

        return selectors

    def _generate_field_selectors(
            self, field_description: str,
            field_type: Optional[str]) -> List[Dict[str, Any]]:
        """Generate intelligent field selectors with priority for text inputs."""

        selectors = []
        field_lower = field_description.lower()

        # Strategy 1: Prioritize text inputs and textareas (MOST IMPORTANT)
        if "message" in field_lower or "input" in field_lower or "text" in field_lower:
            selectors.extend([
                {
                    "selector": "input[type='text']:visible",
                    "strategy": "text_input",
                    "priority": 1
                },
                {
                    "selector": "textarea:visible",
                    "strategy": "textarea",
                    "priority": 1
                },
                {
                    "selector":
                    "input:not([type='checkbox']):not([type='radio']):not([type='submit']):not([type='button']):visible",
                    "strategy": "generic_input",
                    "priority": 2
                },
            ])

        # Strategy 2: Type-specific selectors (high priority)
        if field_type:
            selectors.append({
                "selector": f"input[type='{field_type}']:visible",
                "strategy": f"{field_type}_type",
                "priority": 1
            })

        # Strategy 3: Placeholder matching
        selectors.extend([
            {
                "selector":
                f"input[placeholder*='{field_description}' i]:not([type='checkbox']):not([type='radio'])",
                "strategy": "placeholder",
                "priority": 3
            },
            {
                "selector": f"textarea[placeholder*='{field_description}' i]",
                "strategy": "textarea_placeholder",
                "priority": 3
            },
        ])

        # Strategy 4: Name attribute matching
        field_name = field_description.lower().replace(" ", "").replace(
            "field", "")
        selectors.extend([
            {
                "selector":
                f"input[name*='{field_name}']:not([type='checkbox']):not([type='radio'])",
                "strategy": "name_attr",
                "priority": 4
            },
            {
                "selector":
                f"input[name='{field_name}']:not([type='checkbox']):not([type='radio'])",
                "strategy": "name_exact",
                "priority": 4
            },
        ])

        # Strategy 5: ID attribute matching
        selectors.extend([
            {
                "selector":
                f"input[id*='{field_name}']:not([type='checkbox']):not([type='radio'])",
                "strategy": "id_attr",
                "priority": 5
            },
            {
                "selector":
                f"input[id='{field_name}']:not([type='checkbox']):not([type='radio'])",
                "strategy": "id_exact",
                "priority": 5
            },
        ])

        # Strategy 6: Label-based matching
        selectors.extend([
            {
                "selector":
                f"input[aria-label*='{field_description}' i]:not([type='checkbox']):not([type='radio'])",
                "strategy": "aria_label",
                "priority": 6
            },
            {
                "selector":
                f"label:has-text('{field_description}') + input:not([type='checkbox']):not([type='radio'])",
                "strategy": "adjacent_label",
                "priority": 7
            },
            {
                "selector":
                f"label:has-text('{field_description}') input:not([type='checkbox']):not([type='radio'])",
                "strategy": "nested_label",
                "priority": 8
            },
        ])

        # Strategy 6: Common field patterns
        if "email" in field_lower:
            selectors.extend([
                {
                    "selector": "input[type='email']",
                    "strategy": "email_type",
                    "priority": 1
                },
                {
                    "selector": "input[name*='email']",
                    "strategy": "email_name",
                    "priority": 2
                },
            ])

        if "password" in field_lower:
            selectors.extend([
                {
                    "selector": "input[type='password']",
                    "strategy": "password_type",
                    "priority": 1
                },
                {
                    "selector": "input[name*='password']",
                    "strategy": "password_name",
                    "priority": 2
                },
            ])

        # Strategy 7: Generic input matching (lowest priority)
        selectors.extend([
            {
                "selector": "input",
                "strategy": "generic_input",
                "priority": 20
            },
            {
                "selector": "textarea",
                "strategy": "generic_textarea",
                "priority": 21
            },
        ])

        # Sort by priority
        selectors.sort(key=lambda x: x["priority"])

        return selectors

    async def _validate_clickable_element(self, element: Locator) -> bool:
        """Validate that element is truly clickable."""

        try:
            # Check if element is visible and enabled
            is_visible = await element.is_visible()
            is_enabled = await element.is_enabled()

            if not (is_visible and is_enabled):
                return False

            # Check element properties that indicate clickability
            tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
            has_click_handler = await element.evaluate("""
                el => el.onclick !== null || 
                      el.addEventListener || 
                      ['button', 'a', 'input'].includes(el.tagName.toLowerCase()) ||
                      el.hasAttribute('role') && ['button', 'menuitem', 'option'].includes(el.getAttribute('role'))
            """)

            return has_click_handler or tag_name in ["button", "a", "input"]

        except Exception:
            return False

    def _load_selector_strategies(self) -> Dict[str, Any]:
        """Load selector strategies from config."""

        strategies_file = self.config_dir / "selector_strategies.yaml"

        default_strategies = {
            "text_matching": {
                "exact_text": "text='{target}'",
                "partial_text": "text*='{target}'",
                "case_insensitive": "[text~='{target}' i]"
            },
            "attribute_matching": {
                "aria_label": "[aria-label*='{target}' i]",
                "title": "[title*='{target}' i]",
                "data_testid": "[data-testid*='{target}']"
            },
            "semantic_matching": {
                "button": "button:has-text('{target}')",
                "link": "a:has-text('{target}')",
                "menuitem": "[role='menuitem']:has-text('{target}')"
            }
        }

        try:
            if strategies_file.exists():
                with open(strategies_file, 'r') as f:
                    return yaml.safe_load(f)
            else:
                # Create default config file
                strategies_file.parent.mkdir(parents=True, exist_ok=True)
                with open(strategies_file, 'w') as f:
                    yaml.dump(default_strategies, f, default_flow_style=False)
                return default_strategies
        except Exception as e:
            print(f"⚠️ Could not load selector strategies: {e}")
            return default_strategies

    async def find_ui_panel(self, page: Page,
                            panel_type: str) -> Optional[Locator]:
        """Find UI panel elements (left, center, right panels)."""

        print(f"    🎯 Smart search for UI panel: '{panel_type}'")

        # Generate panel-specific selectors
        selectors = self._generate_panel_selectors(panel_type)

        # Try each selector strategy
        for selector_info in selectors:
            try:
                selector = selector_info["selector"]
                strategy = selector_info["strategy"]

                element = page.locator(selector).first
                if await element.count() > 0 and await element.is_visible(
                        timeout=1000):
                    print(f"    ✅ Found {panel_type} panel using {strategy}")
                    return element

            except Exception:
                continue

        print(f"    ❌ Could not find {panel_type} panel")
        return None

    def _generate_panel_selectors(self,
                                  panel_type: str) -> List[Dict[str, Any]]:
        """Generate selectors for UI panels based on type."""

        selectors = []
        panel_lower = panel_type.lower()

        if "left" in panel_lower:
            selectors.extend([
                # File/navigation panels
                {
                    "selector": "[class*='sidebar']",
                    "strategy": "sidebar_class"
                },
                {
                    "selector": "[class*='nav']",
                    "strategy": "nav_class"
                },
                {
                    "selector": "[class*='left']",
                    "strategy": "left_class"
                },
                {
                    "selector": "[class*='file']",
                    "strategy": "file_class"
                },
                {
                    "selector": "[data-testid*='sidebar']",
                    "strategy": "sidebar_testid"
                },
                {
                    "selector": "[data-testid*='nav']",
                    "strategy": "nav_testid"
                },
                {
                    "selector": "[data-testid*='left']",
                    "strategy": "left_testid"
                },
                {
                    "selector": "[role='navigation']",
                    "strategy": "nav_role"
                },
                # Structure-based (first child of main container)
                {
                    "selector": "main > div:first-child",
                    "strategy": "main_first_child"
                },
                {
                    "selector": "[class*='container'] > div:first-child",
                    "strategy": "container_first_child"
                },
            ])

        elif "center" in panel_lower:
            selectors.extend([
                # Document/content panels
                {
                    "selector": "[class*='content']",
                    "strategy": "content_class"
                },
                {
                    "selector": "[class*='center']",
                    "strategy": "center_class"
                },
                {
                    "selector": "[class*='main']",
                    "strategy": "main_class"
                },
                {
                    "selector": "[class*='document']",
                    "strategy": "document_class"
                },
                {
                    "selector": "[class*='preview']",
                    "strategy": "preview_class"
                },
                {
                    "selector": "[data-testid*='content']",
                    "strategy": "content_testid"
                },
                {
                    "selector": "[data-testid*='center']",
                    "strategy": "center_testid"
                },
                {
                    "selector": "[data-testid*='main']",
                    "strategy": "main_testid"
                },
                # Upload areas
                {
                    "selector": "[class*='upload']",
                    "strategy": "upload_class"
                },
                {
                    "selector": "[class*='drop']",
                    "strategy": "drop_class"
                },
                {
                    "selector": "text='NO FILES ADDED YET'",
                    "strategy": "upload_text"
                },
                {
                    "selector": "text='Drop anywhere to upload'",
                    "strategy": "drop_text"
                },
                # Structure-based (middle child)
                {
                    "selector": "main > div:nth-child(2)",
                    "strategy": "main_middle_child"
                },
                {
                    "selector": "[class*='container'] > div:nth-child(2)",
                    "strategy": "container_middle_child"
                },
            ])

        elif "right" in panel_lower:
            selectors.extend([
                # Chat/conversation panels
                {
                    "selector": "[class*='chat']",
                    "strategy": "chat_class"
                },
                {
                    "selector": "[class*='conversation']",
                    "strategy": "conversation_class"
                },
                {
                    "selector": "[class*='right']",
                    "strategy": "right_class"
                },
                {
                    "selector": "[class*='message']",
                    "strategy": "message_class"
                },
                {
                    "selector": "[data-testid*='chat']",
                    "strategy": "chat_testid"
                },
                {
                    "selector": "[data-testid*='conversation']",
                    "strategy": "conversation_testid"
                },
                {
                    "selector": "[data-testid*='right']",
                    "strategy": "right_testid"
                },
                {
                    "selector": "[data-testid*='message']",
                    "strategy": "message_testid"
                },
                # Sample prompts areas
                {
                    "selector": "text='Sample Prompts'",
                    "strategy": "sample_prompts_text"
                },
                {
                    "selector": "[class*='prompt']",
                    "strategy": "prompt_class"
                },
                # Structure-based (last child)
                {
                    "selector": "main > div:last-child",
                    "strategy": "main_last_child"
                },
                {
                    "selector": "[class*='container'] > div:last-child",
                    "strategy": "container_last_child"
                },
            ])

        # Generic panel selectors (lowest priority)
        selectors.extend([
            {
                "selector": f"[class*='{panel_lower}']",
                "strategy": f"{panel_lower}_generic_class"
            },
            {
                "selector": f"[data-testid*='{panel_lower}']",
                "strategy": f"{panel_lower}_generic_testid"
            },
            {
                "selector": f"*:has-text('{panel_type}')",
                "strategy": f"{panel_lower}_text_match"
            },
        ])

        return selectors
