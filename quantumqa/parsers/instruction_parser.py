#!/usr/bin/env python3
"""
Generic Instruction Parser - Converts natural language to structured actions
Works with any application by using pattern matching and NLP techniques
"""

import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List


class InstructionParser:
    """Generic instruction parser using configurable patterns."""

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.action_patterns = self._load_action_patterns()
        self.context_hints = self._load_context_hints()

    async def parse(self, instruction: str) -> Dict[str, Any]:
        """Parse natural language instruction into structured action plan."""

        instruction = instruction.strip()

        # Skip comment lines and section headers
        if instruction.startswith('#') or instruction.startswith(
                '//') or not instruction:
            return {
                "action": "comment",
                "raw_instruction": instruction,
                "confidence": 1.0,
                "skip": True
            }

        instruction_lower = instruction.lower()

        # Try each action pattern until we find a match
        for action_type, patterns in self.action_patterns.items():
            for pattern in patterns:
                # Special handling for run_function to preserve case
                if action_type == "run_function":
                    # print(
                    #     f"DEBUG: Trying run_function pattern: {pattern['regex']}"
                    # )
                    # print(f"DEBUG: Against instruction: {instruction}")
                    match = re.search(pattern["regex"], instruction,
                                      re.IGNORECASE)
                    # if match:
                    #     print(f"DEBUG: Match found! Groups: {match.groups()}")
                else:
                    match = re.search(pattern["regex"], instruction_lower)

                if match:
                    result = self._build_action_plan(
                        action_type, instruction, match,
                        pattern.get("extractor", {}))

                    # Debug output for run_function results
                    # if action_type == "run_function":
                    #     print(f"DEBUG: Action plan: {result}")

                    return result

        # Fallback: unknown instruction
        return {
            "action": "unknown",
            "raw_instruction": instruction,
            "confidence": 0.0
        }

    def _build_action_plan(self, action_type: str, instruction: str,
                           match: re.Match, extractor: Dict) -> Dict[str, Any]:
        """Build structured action plan from regex match."""

        plan = {
            "action": action_type,
            "raw_instruction": instruction,
            "confidence": 0.9
        }

        # Extract parameters based on action type
        if action_type == "navigate":
            plan.update(
                self._extract_navigation_params(instruction, match, extractor))

        elif action_type == "click":
            plan.update(
                self._extract_click_params(instruction, match, extractor))

        elif action_type == "type":
            plan.update(
                self._extract_type_params(instruction, match, extractor))

        elif action_type == "upload":
            plan.update(
                self._extract_upload_params(instruction, match, extractor))

        elif action_type in [
                "send", "select", "explore", "test", "confirm", "close"
        ]:
            plan.update(
                self._extract_generic_target_params(instruction, match,
                                                    extractor))

        elif action_type == "verify":
            plan.update(
                self._extract_verify_params(instruction, match, extractor))

        elif action_type == "wait":
            plan.update(
                self._extract_wait_params(instruction, match, extractor))

        elif action_type == "run_function":
            # Special handling for run_function
            function_call = ""
            arguments = ""

            # Extract function call from match groups
            if "function_call" in extractor and isinstance(
                    extractor["function_call"], int):
                group_idx = extractor["function_call"]
                if group_idx <= len(match.groups()):
                    function_call = match.group(group_idx)
                    # print(f"DEBUG: Extracted function_call: '{function_call}'")

            # Extract arguments from match groups
            if "arguments" in extractor and isinstance(extractor["arguments"],
                                                       int):
                group_idx = extractor["arguments"]
                if group_idx <= len(match.groups()):
                    arguments = match.group(group_idx) or ""
                    # print(f"DEBUG: Extracted arguments: '{arguments}'")

            # Update plan with extracted values
            plan.update({
                "function_call": function_call,
                "arguments": arguments
            })
            # print(f"DEBUG: Final run_function plan: {plan}")

        return plan

    def _extract_navigation_params(self, instruction: str, match: re.Match,
                                   extractor: Dict) -> Dict[str, Any]:
        """Extract navigation parameters."""

        # Try to find URL in the instruction
        url_patterns = [
            r'https?://[^\s]+', r'www\.[^\s]+',
            r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^\s]*'
        ]

        url = None
        for pattern in url_patterns:
            url_match = re.search(pattern, instruction)
            if url_match:
                url = url_match.group(0)
                break

        return {"url": url, "wait_until": "domcontentloaded", "timeout": 30000}

    def _extract_click_params(self, instruction: str, match: re.Match,
                              extractor: Dict) -> Dict[str, Any]:
        """Extract click parameters."""
        
        # Define stop words that should be filtered from targets
        STOP_WORDS = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'were', 'will', 'with', 'would', 'this', 'these',
            'those', 'they', 'there', 'their', 'then', 'than', 'them'
        }
        
        # Extract target element text
        target = None
        
        # Try common click patterns with better stop word handling
        click_patterns = [
            # First priority: Extract exact quoted text
            r'click (?:on )?["\']([^"\']+)["\']',
            # Second priority: Common elements with specific endings  
            r'click (?:on )?(?:the )?([^"\']+?)(?:\s+(?:button|link|element|field|area|input|dropdown|tab|option))',
            # Third priority: General patterns
            r'click (?:on )?(?:the )?([^"\']+?)(?:\s+in\s+|\s*$)',
            r'click\s+(.+?)(?:\s+button|\s+link|\s+element|$)',
        ]
        
        for pattern in click_patterns:
            target_match = re.search(pattern, instruction.lower())
            if target_match:
                raw_target = target_match.group(1).strip()
                
                # Filter out stop words from the beginning and end
                target_words = raw_target.split()
                # Remove leading stop words
                while target_words and target_words[0] in STOP_WORDS:
                    target_words.pop(0)
                # Remove trailing stop words
                while target_words and target_words[-1] in STOP_WORDS:
                    target_words.pop()
                
                if target_words:
                    target = ' '.join(target_words)
                    # Strip trailing punctuation such as commas or quotes that leak from sentence
                    target = target.rstrip(",.'\"”’`)")
                    break
                else:
                    # If all words were stop words, keep the original
                    # Strip trailing punctuation for robustness
                    target = raw_target.rstrip(",.'\"”’`)")
                    break
        
        
        # Extract context clues
        context = self._extract_context_clues(instruction)

        return {
            "target": target,
            "context": context,
            "click_options": {
                "force": context.get("requires_force", False),
                "timeout": 5000
            }
        }

    def _extract_type_params(self, instruction: str, match: re.Match,
                             extractor: Dict) -> Dict[str, Any]:
        """Extract typing parameters."""
        
        # Check if this is a combined click and type action
        if extractor.get("combined_action"):
            # Extract from regex match groups
            target_group = extractor.get("target", 1)
            text_group = extractor.get("text", 2)
            
            target = match.group(target_group).strip() if match and match.groups() else ""
            text = match.group(text_group).strip() if match and match.groups() else ""
            
            # Clean up target (remove quotes if present)
            target = target.strip('"\'')
            
            # For combined actions, use the target as the field and add click action
            return {
                "text": text,
                "field": target,  # The same target we click on
                "target": target,  # Also set as target for click
                "combined_action": True,
                "field_type": None
            }
        
        # Standard type action: "Type [text] in [field]" - Use original instruction to preserve case
        type_pattern = r'type\s+["\']?([^"\']+?)["\']?\s+(?:in|into)\s+(.+?)(?:\s+field|$)'
        type_match = re.search(
            type_pattern, instruction, re.IGNORECASE
        )  # Case insensitive matching but preserve original text

        if type_match:
            text = type_match.group(
                1).strip()  # This preserves the original case
            field = type_match.group(2).strip()

            # Determine field type (use lowercase for field type detection)
            field_type = None
            field_lower = field.lower()
            if "email" in field_lower:
                field_type = "email"
            elif "password" in field_lower:
                field_type = "password"
            elif "search" in field_lower:
                field_type = "search"

            return {
                "text": text,  # Original case preserved!
                "field": field,
                "field_type": field_type
            }

        return {}

    def _extract_upload_params(self, instruction: str, match: re.Match,
                               extractor: Dict) -> Dict[str, Any]:
        """Extract file upload parameters."""

        # Get file path from extractor
        file_path = None
        if extractor.get("file_path"):
            group_num = extractor["file_path"]
            if isinstance(group_num, int) and group_num <= len(match.groups()):
                file_path = match.group(group_num)

        return {"file_path": file_path, "upload_type": "file"}

    def _extract_generic_target_params(self, instruction: str, match: re.Match,
                                       extractor: Dict) -> Dict[str, Any]:
        """Extract generic target parameters for send, select, explore, test, confirm, close actions."""

        # Get target from extractor
        target = None
        if extractor.get("target"):
            target_ref = extractor["target"]
            if isinstance(target_ref, str):
                target = target_ref  # Direct string value
            elif isinstance(target_ref, int) and target_ref <= len(
                    match.groups()):
                target = match.group(target_ref)  # Regex group reference

        return {"target": target, "action_context": instruction.lower()}

    def _extract_verify_params(self, instruction: str, match: re.Match,
                               extractor: Dict) -> Dict[str, Any]:
        """Extract verification parameters."""

        # 🔧 FIX: Use extractor information from YAML first!
        verification_type = extractor.get("verification_type", "generic")
        expected_value = None
        instruction_lower = instruction.lower()

        # If extractor specifies expected_value index, extract it from match groups
        if "expected_value" in extractor and match and match.groups():
            expected_value_index = extractor["expected_value"]
            if isinstance(expected_value_index, int) and len(
                    match.groups()) >= expected_value_index:
                expected_value = match.group(expected_value_index).strip()

        # Handle special URL redirection verification with prefix/suffix
        verification_options = {"timeout": 10000}
        if verification_type == "url_redirect_with_patterns" and match and match.groups(
        ):
            if "url_prefix" in extractor and len(
                    match.groups()) >= extractor["url_prefix"]:
                verification_options["url_prefix"] = match.group(
                    extractor["url_prefix"]).strip()
            if "url_suffix" in extractor and len(
                    match.groups()) >= extractor["url_suffix"]:
                verification_options["url_suffix"] = match.group(
                    extractor["url_suffix"]).strip()

        # Fallback: legacy hardcoded detection (only if no extractor information)
        if verification_type == "generic":
            if "loads successfully" in instruction_lower:
                verification_type = "page_load"
            elif "title contains" in instruction_lower:
                verification_type = "title_contains"
                # Extract expected title text
                title_match = re.search(
                    r'title contains\s+["\']?([^"\']+)["\']?',
                    instruction_lower)
                if title_match:
                    expected_value = title_match.group(1)
            elif "url" in instruction_lower and "change" in instruction_lower:
                verification_type = "url_change"
                # Extract expected URL pattern
                url_match = re.search(
                    r'(?:url|page).*?(?:change|contain).*?["\']?([^"\']+)["\']?',
                    instruction_lower)
                if url_match:
                    expected_value = url_match.group(1)
            elif "downloaded" in instruction_lower or "download" in instruction_lower:
                verification_type = "file_downloaded"
                # Extract file type if mentioned
                file_type_match = re.search(
                    r'(csv|pdf|excel|xlsx|json|xml|txt) file',
                    instruction_lower)
                if file_type_match:
                    expected_value = file_type_match.group(1)
                else:
                    expected_value = "file"

            elif "visible" in instruction_lower:
                verification_type = "element_visible"
                # Enhanced element extraction for complex visibility checks

                # Try different patterns to extract the key element
                patterns = [
                    # "Verify that [element] is visible"
                    r'verify\s+that\s+([^"\']+?)\s+(?:is\s+)?visible',
                    # "Verify [element] visible"
                    r'verify\s+([^"\']+?)\s+visible',
                    # Extract key nouns from complex statements
                    r'verify.*?(button|tab|menu|dropdown|panel|page|form|field).*?visible',
                    # Extract quoted elements
                    r'verify.*?["\']([^"\']+)["\'].*?visible',
                ]

                for pattern in patterns:
                    visible_match = re.search(pattern, instruction_lower)
                    if visible_match:
                        expected_value = visible_match.group(1).strip()
                        break

                # If still not found, extract key terms from the instruction
                if not expected_value:
                    # Look for important UI elements mentioned
                    key_elements = [
                        'button', 'dropdown', 'tab', 'panel', 'menu', 'create',
                        'purple', 'deploy', 'review', 'data'
                    ]
                    found_elements = [
                        elem for elem in key_elements
                        if elem in instruction_lower
                    ]
                    if found_elements:
                        expected_value = ' '.join(found_elements)
            elif "has" in instruction_lower and ("button" in instruction_lower
                                                 or "option"
                                                 in instruction_lower):
                verification_type = "contains_elements"
                # Extract what should be contained
                contains_match = re.search(
                    r'has.*?(?:button|option).*?for\s+([^"\']+)',
                    instruction_lower)
                if contains_match:
                    expected_value = contains_match.group(1).strip()

        return {
            "verification_type": verification_type,
            "expected_value": expected_value,
            "verification_options": verification_options
        }

    def _extract_wait_params(self, instruction: str, match: re.Match,
                             extractor: Dict) -> Dict[str, Any]:
        """Extract wait parameters."""

        # Extract duration if specified
        duration_match = re.search(r'(\d+)(?:\s*seconds?)?', instruction)
        duration = int(duration_match.group(1)) if duration_match else 2

        wait_type = "time"
        if "load" in instruction.lower():
            wait_type = "page_load"
        elif "appear" in instruction.lower() or "visible" in instruction.lower(
        ):
            wait_type = "element_visible"

        return {"wait_type": wait_type, "duration": duration}

    def _extract_context_clues(self, instruction: str) -> Dict[str, Any]:
        """Extract context clues to improve element finding."""

        context = {}
        instruction_lower = instruction.lower()

        # Location context - more specific positioning with exclusions
        if "top right corner" in instruction_lower or "top right most corner" in instruction_lower:
            context["position"] = "top-right-corner"
            context["exclude_tabs"] = True  # Don't match navigation tabs
            context["exclude_left"] = True  # Avoid left-side elements
        elif "top right" in instruction_lower:
            context["position"] = "top-right"
            context["exclude_tabs"] = True
            context["exclude_left"] = True
        elif "top left" in instruction_lower:
            context["position"] = "top-left"
        elif "bottom" in instruction_lower:
            context["position"] = "bottom"

        # Explicit exclusions from instruction text
        if "avoid" in instruction_lower and "left" in instruction_lower:
            context["exclude_left"] = True
        if "not in left" in instruction_lower or "not in left-side" in instruction_lower:
            context["exclude_left"] = True
        if "avoid any left-side" in instruction_lower:
            context["exclude_left"] = True

        # Color context
        if "purple" in instruction_lower:
            context["color"] = "purple"
        elif "blue" in instruction_lower:
            context["color"] = "blue"
        elif "red" in instruction_lower:
            context["color"] = "red"

        # Element type context - more specific detection with visual cues
        if ("dropdown arrow" in instruction_lower
                or "with dropdown" in instruction_lower
                or ("border" in instruction_lower
                    and "dropdown" in instruction_lower)):
            context["element_type"] = "dropdown-button"
            context["has_dropdown"] = True
            context["has_border"] = True
            context["requires_force"] = True
        elif "dropdown" in instruction_lower:
            context["element_type"] = "dropdown"
            context[
                "requires_force"] = True  # Dropdown items often need force click
        elif "button" in instruction_lower and "border" in instruction_lower:
            context["element_type"] = "bordered-button"
            context["has_border"] = True
        elif "button" in instruction_lower:
            context["element_type"] = "button"
        elif "link" in instruction_lower:
            context["element_type"] = "link"
        elif "tab" in instruction_lower and not context.get("exclude_tabs"):
            context["element_type"] = "tab"

        # Visual characteristics
        if "border" in instruction_lower or "boundary" in instruction_lower:
            context["has_border"] = True
        if "arrow" in instruction_lower:
            context["has_arrow"] = True

        # Action context
        if "from dropdown" in instruction_lower or "dropdown option" in instruction_lower:
            context["parent_type"] = "dropdown"
            context["requires_force"] = True

        # Extract specific element from dropdown context
        if "from dropdown" in instruction_lower:
            # Extract the main element name before "from dropdown"
            dropdown_match = re.search(
                r'(\w+)\s+(?:button|option)?\s*from\s+dropdown',
                instruction_lower)
            if dropdown_match:
                context["dropdown_target"] = dropdown_match.group(1)

        return context

    def _load_action_patterns(self) -> Dict[str, List[Dict]]:
        """Load action patterns from config file."""

        patterns_file = self.config_dir / "action_patterns.yaml"

        # Default patterns if config file doesn't exist
        default_patterns = {
            "navigate": [{
                "regex": r"navigate\s+to\s+(.+)",
                "description": "Navigate to URL"
            }, {
                "regex": r"go\s+to\s+(.+)",
                "description": "Go to URL"
            }],
            "click": [{
                "regex": r"click\s+(?:on\s+)?(.+)",
                "description": "Click on element"
            }],
            "type": [{
                "regex": r"type\s+(.+?)\s+(?:in|into)\s+(.+)",
                "description": "Type text in field"
            }],
            "verify": [{
                "regex": r"verify\s+(.+)",
                "description": "Verify condition"
            }, {
                "regex": r"check\s+(.+)",
                "description": "Check condition"
            }],
            "wait": [{
                "regex": r"wait\s+(?:for\s+)?(.+)",
                "description": "Wait for condition"
            }]
        }

        try:
            if patterns_file.exists():
                with open(patterns_file, 'r') as f:
                    return yaml.safe_load(f)
            else:
                # Create default config file
                patterns_file.parent.mkdir(parents=True, exist_ok=True)
                with open(patterns_file, 'w') as f:
                    yaml.dump(default_patterns, f, default_flow_style=False)
                return default_patterns
        except Exception as e:
            print(f"⚠️ Could not load action patterns: {e}")
            return default_patterns

    def _load_context_hints(self) -> Dict[str, Any]:
        """Load context hints for better parsing."""

        context_file = self.config_dir / "context_hints.yaml"

        default_hints = {
            "position_keywords": ["top", "bottom", "left", "right", "center"],
            "color_keywords": ["purple", "blue", "red", "green", "yellow"],
            "element_types":
            ["button", "link", "dropdown", "tab", "input", "field"],
            "action_modifiers": ["force", "double", "right"]
        }

        try:
            if context_file.exists():
                with open(context_file, 'r') as f:
                    return yaml.safe_load(f)
            else:
                # Create default config file
                context_file.parent.mkdir(parents=True, exist_ok=True)
                with open(context_file, 'w') as f:
                    yaml.dump(default_hints, f, default_flow_style=False)
                return default_hints
        except Exception as e:
            print(f"⚠️ Could not load context hints: {e}")
            return default_hints
