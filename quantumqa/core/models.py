"""
Core data models for QuantumQA framework.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Dict, List
from pydantic import BaseModel


class MessageType(Enum):
    """Types of messages agents can send to each other."""
    # Core workflow messages
    INSTRUCTION_RECEIVED = "instruction_received"
    STEPS_DECOMPOSED = "steps_decomposed"
    PLAN_CREATED = "plan_created"
    PLAN_APPROVED = "plan_approved"
    PLAN_REJECTED = "plan_rejected"
    PLAN_READY = "plan_ready"
    
    # Navigation messages
    NAVIGATE_REQUEST = "navigate_request"
    NAVIGATE_RESPONSE = "navigate_response"
    GET_CURRENT_URL = "get_current_url"
    URL_INFO = "url_info"
    
    # Element detection messages
    DETECT_ELEMENT = "detect_element"
    ELEMENT_DETECTED = "element_detected"
    CLEAR_ELEMENT_CACHE = "clear_element_cache"
    CACHE_CLEARED = "cache_cleared"
    
    # Action execution messages
    EXECUTE_ACTION = "execute_action"
    ACTION_EXECUTED = "action_executed"
    GET_ACTION_HISTORY = "get_action_history"
    ACTION_HISTORY = "action_history"
    
    # Validation messages
    VALIDATE_OUTCOME = "validate_outcome"
    VALIDATION_RESULT = "validation_result"
    VALIDATE_ELEMENT_STATE = "validate_element_state"
    ELEMENT_VALIDATION_RESULT = "element_validation_result"
    
    # Legacy/General messages
    DECOMPOSITION_REQUEST = "decomposition_request"
    DECOMPOSITION_RESPONSE = "decomposition_response"
    EXECUTION_REQUEST = "execution_request"
    EXECUTION_RESPONSE = "execution_response"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    ERROR_OCCURRED = "error_occurred"


class Priority(Enum):
    """Message priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TestStatus(Enum):
    """Test execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    """Individual step status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ActionType(Enum):
    """Types of actions that can be performed."""
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    WAIT = "wait"
    VERIFY = "verify"


@dataclass
class AgentMessage:
    """Message passed between agents."""
    id: str
    sender: str
    recipient: str
    message_type: MessageType
    payload: Dict[str, Any]
    timestamp: datetime
    parent_message_id: Optional[str] = None
    priority: Priority = Priority.NORMAL


@dataclass
class Coordinates:
    """Screen coordinates."""
    x: int
    y: int


@dataclass
class BoundingBox:
    """Bounding box for UI elements."""
    x: int
    y: int
    width: int
    height: int


class AtomicStep(BaseModel):
    """A single atomic step in a test."""
    step_number: int
    instruction: str
    action_type: ActionType
    target_description: str
    input_data: Optional[str] = None
    expected_outcome: Optional[str] = None


class StepResult(BaseModel):
    """Result of executing a single step."""
    step_number: int
    instruction: str
    status: StepStatus
    execution_time: float
    agent_used: str
    screenshot_path: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0


class ElementDetectionResult(BaseModel):
    """Result of element detection."""
    found: bool
    confidence: float
    instruction: str
    coordinates: Optional[Coordinates] = None
    center_coordinates: Optional[Coordinates] = None
    bounding_box: Optional[BoundingBox] = None
    element_type: Optional[str] = None
    visible_text: Optional[str] = None
    attributes: Dict[str, Any] = {}
    interaction_type: str = "click"
    page_analysis: Dict[str, Any] = {}
    recommendation: str = ""
    alternative_elements: List[Dict[str, Any]] = []
    error_message: Optional[str] = None


class TestResult(BaseModel):
    """Complete test execution result."""
    test_id: str
    instructions: List[str]
    status: TestStatus
    execution_time: float
    steps: List[StepResult]
    artifacts: List[str] = []
    cost_estimate: float = 0.0
    
    def summary(self) -> str:
        """Generate a human-readable summary."""
        status_emoji = {"COMPLETED": "✅", "FAILED": "❌", "RUNNING": "🔄"}.get(self.status.value.upper(), "❓")
        passed_steps = len([s for s in self.steps if s.status == StepStatus.COMPLETED])
        total_steps = len(self.steps)
        
        return f"""
{status_emoji} Test {self.status.value.upper()}

📊 Results:
  • Steps: {passed_steps}/{total_steps} passed
  • Duration: {self.execution_time:.1f}s
  • Cost: ${self.cost_estimate:.3f}
  
📋 Instructions executed:
{chr(10).join(f"  {i+1}. {inst}" for i, inst in enumerate(self.instructions))}
"""

    def save_artifacts(self, path: str) -> None:
        """Save test artifacts to specified path."""
        import os
        os.makedirs(path, exist_ok=True)
        # Implementation will be added later
        pass
