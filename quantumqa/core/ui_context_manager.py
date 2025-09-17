#!/usr/bin/env python3
"""
UI Context Manager - Tracks UI state and context between test steps.
Maintains awareness of opened dropdowns, modals, and other interactive regions.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set
from enum import Enum


class UIElementType(Enum):
    """Types of UI elements that can affect context."""
    DROPDOWN = "dropdown"
    MODAL = "modal"
    POPUP = "popup"
    SIDEBAR = "sidebar"
    TAB = "tab"
    ACCORDION = "accordion"
    TOOLTIP = "tooltip"


class UIState(Enum):
    """States of UI elements."""
    OPENED = "opened"
    CLOSED = "closed"
    EXPANDED = "expanded"
    COLLAPSED = "collapsed"
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass
class UIElementContext:
    """Context information for a UI element."""
    element_type: UIElementType
    state: UIState
    step_opened: int
    target_description: str
    region_hint: Optional[str] = None
    expected_lifetime: int = 5  # How many steps this context should persist
    action_keywords: Set[str] = field(default_factory=set)


class UIContextManager:
    """
    Manages UI context and state tracking between test steps.
    Helps maintain awareness of opened dropdowns, modals, etc.
    """
    
    def __init__(self):
        self.active_contexts: Dict[str, UIElementContext] = {}
        self.context_history: List[Dict[str, Any]] = []
        
        # Patterns to detect context-creating actions
        self.dropdown_patterns = [
            r"click.*dropdown", r"open.*dropdown", r"expand.*dropdown",
            r"click.*create.*dropdown", r"click.*menu", r"open.*menu"
        ]
        
        self.modal_patterns = [
            r"open.*modal", r"open.*dialog", r"show.*popup",
            r"click.*settings", r"click.*profile"
        ]
        
        # Patterns to detect context-dependent actions
        self.scoped_action_patterns = [
            r"click.*from.*dropdown", r"select.*from.*dropdown",
            r"click.*from.*menu", r"select.*from.*menu",
            r"click.*button.*from.*dropdown", r"click.*option"
        ]
    
    def analyze_step_for_context(self, step_number: int, instruction: str) -> Optional[UIElementContext]:
        """
        Analyze a step instruction to detect if it creates new UI context.
        
        Args:
            step_number: Current step number
            instruction: The instruction text
            
        Returns:
            UIElementContext if the step creates new context, None otherwise
        """
        instruction_lower = instruction.lower()
        
        # Check for dropdown context creation
        for pattern in self.dropdown_patterns:
            if re.search(pattern, instruction_lower):
                # Extract the target description
                target = self._extract_target_from_instruction(instruction)
                
                context = UIElementContext(
                    element_type=UIElementType.DROPDOWN,
                    state=UIState.OPENED,
                    step_opened=step_number,
                    target_description=target,
                    region_hint=f"dropdown opened in step {step_number}",
                    action_keywords={"dropdown", "menu", "option", "select"}
                )
                
                context_key = f"dropdown_{step_number}"
                self.active_contexts[context_key] = context
                
                print(f"    🎯 UIContextManager: Detected dropdown context creation - {target}")
                return context
        
        # Check for modal context creation
        for pattern in self.modal_patterns:
            if re.search(pattern, instruction_lower):
                target = self._extract_target_from_instruction(instruction)
                
                context = UIElementContext(
                    element_type=UIElementType.MODAL,
                    state=UIState.OPENED,
                    step_opened=step_number,
                    target_description=target,
                    region_hint=f"modal opened in step {step_number}",
                    action_keywords={"modal", "dialog", "popup"}
                )
                
                context_key = f"modal_{step_number}"
                self.active_contexts[context_key] = context
                
                print(f"    🎯 UIContextManager: Detected modal context creation - {target}")
                return context
        
        return None
    
    def check_if_step_needs_context(self, step_number: int, instruction: str) -> Optional[Dict[str, Any]]:
        """
        Check if a step needs to be executed within a specific UI context.
        
        Args:
            step_number: Current step number
            instruction: The instruction text
            
        Returns:
            Dictionary with context information if step needs scoping, None otherwise
        """
        instruction_lower = instruction.lower()
        
        # Check if this is a context-dependent action
        is_scoped_action = any(re.search(pattern, instruction_lower) for pattern in self.scoped_action_patterns)
        
        if not is_scoped_action:
            return None
        
        # Find the most relevant active context
        relevant_context = self._find_relevant_context(step_number, instruction_lower)
        
        if relevant_context:
            context_info = {
                "ui_context_type": relevant_context.element_type.value,
                "ui_context_state": relevant_context.state.value,
                "ui_context_opened_step": relevant_context.step_opened,
                "ui_context_target": relevant_context.target_description,
                "ui_context_region_hint": relevant_context.region_hint,
                "search_scope": f"within the {relevant_context.element_type.value} that was opened in step {relevant_context.step_opened}",
                "context_keywords": list(relevant_context.action_keywords)
            }
            
            print(f"    🎯 UIContextManager: Step {step_number} requires {relevant_context.element_type.value} context from step {relevant_context.step_opened}")
            return context_info
        
        return None
    
    def _extract_target_from_instruction(self, instruction: str) -> str:
        """Extract the target element description from instruction."""
        instruction_lower = instruction.lower()
        
        # Look for common patterns
        if "click on" in instruction_lower:
            parts = instruction_lower.split("click on", 1)
            if len(parts) > 1:
                target = parts[1].strip()
                # Clean up the target description
                target = re.sub(r'\s+dropdown.*$', '', target)
                target = re.sub(r'\s+button.*$', '', target)
                return target.strip()
        
        if "click" in instruction_lower:
            # Extract text between "click" and common endings
            match = re.search(r'click\s+(.*?)(?:\s+dropdown|\s+button|\s+from|$)', instruction_lower)
            if match:
                return match.group(1).strip()
        
        # Fallback - return the whole instruction cleaned up
        return re.sub(r'^(click|open|select)\s+', '', instruction_lower).strip()
    
    def _find_relevant_context(self, step_number: int, instruction_lower: str) -> Optional[UIElementContext]:
        """Find the most relevant active context for the current step."""
        
        # Clean up expired contexts first
        self._cleanup_expired_contexts(step_number)
        
        if not self.active_contexts:
            return None
        
        # Look for keyword matches
        best_context = None
        best_score = 0
        
        for context_key, context in self.active_contexts.items():
            score = 0
            
            # Score based on keyword matches
            for keyword in context.action_keywords:
                if keyword in instruction_lower:
                    score += 2
            
            # Score based on proximity (prefer more recent contexts)
            step_distance = step_number - context.step_opened
            if step_distance <= 3:  # Very recent context
                score += 3
            elif step_distance <= 5:  # Recent context
                score += 1
            
            # Score based on context type relevance
            if context.element_type == UIElementType.DROPDOWN and any(word in instruction_lower for word in ["from", "dropdown", "option", "select"]):
                score += 3
            
            if score > best_score:
                best_score = score
                best_context = context
        
        return best_context if best_score > 0 else None
    
    def _cleanup_expired_contexts(self, current_step: int):
        """Remove contexts that have exceeded their expected lifetime."""
        expired_keys = []
        
        for context_key, context in self.active_contexts.items():
            steps_since_opened = current_step - context.step_opened
            if steps_since_opened > context.expected_lifetime:
                expired_keys.append(context_key)
        
        for key in expired_keys:
            expired_context = self.active_contexts.pop(key)
            print(f"    🧹 UIContextManager: Expired {expired_context.element_type.value} context from step {expired_context.step_opened}")
    
    def close_context(self, context_key: str):
        """Manually close a specific context."""
        if context_key in self.active_contexts:
            closed_context = self.active_contexts.pop(context_key)
            print(f"    🚪 UIContextManager: Closed {closed_context.element_type.value} context from step {closed_context.step_opened}")
    
    def get_active_contexts(self) -> Dict[str, UIElementContext]:
        """Get all currently active contexts."""
        return self.active_contexts.copy()
    
    def clear_all_contexts(self):
        """Clear all active contexts."""
        self.active_contexts.clear()
        print("    🧹 UIContextManager: Cleared all contexts")
    
    def get_context_summary(self) -> str:
        """Get a human-readable summary of active contexts."""
        if not self.active_contexts:
            return "No active UI contexts"
        
        summaries = []
        for context_key, context in self.active_contexts.items():
            summary = f"{context.element_type.value} ({context.target_description}) opened in step {context.step_opened}"
            summaries.append(summary)
        
        return "; ".join(summaries)
