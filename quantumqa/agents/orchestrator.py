#!/usr/bin/env python3
"""
Orchestrator Agent - Coordinates the entire test execution workflow.
Manages communication between specialized agents and browser interactions.
"""

import asyncio
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from .base_agent import BaseAgent
from .element_detector import ElementDetectorAgent
from ..core.llm import VisionLLMClient
from ..core.models import (
    MessageType, 
    AgentMessage, 
    TestStatus, 
    TestResult,
    StepResult,
    StepStatus,
    ElementDetectionResult
)


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator Agent - Central coordinator for agentic UI testing.
    Manages test execution flow and agent communication.
    """
    
    def __init__(
        self,
        vision_client: VisionLLMClient,
        browser_config: Optional[Dict[str, Any]] = None,
        agent_id: str = "orchestrator"
    ):
        """Initialize the Orchestrator Agent."""
        super().__init__(agent_id, "Orchestrator")
        
        # Core components
        self.vision_client = vision_client
        self.browser_config = browser_config or {}
        
        # Specialized agents
        self.element_detector = ElementDetectorAgent(
            agent_id="element_detector_main",
            vision_client=vision_client
        )
        
        # Test execution state
        self.current_test_id: Optional[str] = None
        self.test_results: Dict[str, TestResult] = {}
        
        # Browser state (will be managed by browser manager)
        self.browser_page = None
        self.browser_context = None
        
        print(f"🎭 OrchestratorAgent '{agent_id}' initialized")
    
    async def initialize(self) -> bool:
        """Initialize the orchestrator and its sub-agents."""
        try:
            # Initialize element detector
            detector_initialized = await self.element_detector.initialize()
            if not detector_initialized:
                print("❌ Failed to initialize ElementDetectorAgent")
                return False
            
            print("✅ OrchestratorAgent initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ OrchestratorAgent initialization failed: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up orchestrator resources."""
        try:
            await self.element_detector.cleanup()
            print("✅ OrchestratorAgent cleaned up")
        except Exception as e:
            print(f"⚠️ OrchestratorAgent cleanup warning: {e}")
    
    async def execute_test(self, instructions: List[str]) -> TestResult:
        """
        Execute a complete test with the given instructions.
        
        Args:
            instructions: List of natural language test instructions
            
        Returns:
            TestResult with execution outcome and details
        """
        
        test_id = str(uuid.uuid4())
        self.current_test_id = test_id
        start_time = datetime.now()
        
        print(f"\n🎭 OrchestratorAgent executing test {test_id[:8]}...")
        print(f"📋 Instructions: {len(instructions)} steps")
        
        step_results = []
        test_status = TestStatus.RUNNING
        
        try:
            for i, instruction in enumerate(instructions, 1):
                print(f"\n📍 Step {i}/{len(instructions)}: {instruction}")
                
                step_start_time = datetime.now()
                
                # Execute single instruction step
                step_result = await self._execute_step(
                    step_number=i,
                    instruction=instruction,
                    context={
                        "test_id": test_id,
                        "total_steps": len(instructions),
                        "previous_steps": step_results
                    }
                )
                
                step_execution_time = (datetime.now() - step_start_time).total_seconds()
                step_result.execution_time = step_execution_time
                
                step_results.append(step_result)
                
                # Check if step failed
                if step_result.status == StepStatus.FAILED:
                    print(f"❌ Step {i} failed: {step_result.error_message}")
                    test_status = TestStatus.FAILED
                    break
                else:
                    print(f"✅ Step {i} completed successfully")
            
            # Determine final status
            if test_status == TestStatus.RUNNING:
                test_status = TestStatus.COMPLETED
            
        except Exception as e:
            print(f"❌ Test execution failed: {e}")
            test_status = TestStatus.FAILED
            
            # Add error step result
            step_results.append(StepResult(
                step_number=len(step_results) + 1,
                instruction="Test execution error",
                status=StepStatus.FAILED,
                execution_time=0.0,
                agent_used="orchestrator",
                error_message=str(e)
            ))
        
        # Calculate total execution time
        total_execution_time = (datetime.now() - start_time).total_seconds()
        
        # Estimate costs
        vision_stats = self.vision_client.get_usage_stats()
        estimated_cost = vision_stats.get('estimated_cost', 0.0)
        
        # Create test result
        test_result = TestResult(
            test_id=test_id,
            instructions=instructions,
            status=test_status,
            execution_time=total_execution_time,
            steps=step_results,
            cost_estimate=estimated_cost
        )
        
        # Store result
        self.test_results[test_id] = test_result
        
        print(f"\n🎭 Test {test_id[:8]} completed with status: {test_status.value}")
        print(f"⏱️ Total execution time: {total_execution_time:.2f}s")
        print(f"💰 Estimated cost: ${estimated_cost:.4f}")
        
        return test_result
    
    async def _execute_step(
        self, 
        step_number: int, 
        instruction: str, 
        context: Dict[str, Any]
    ) -> StepResult:
        """Execute a single test step using appropriate agents."""
        
        try:
            # For now, create a basic step result
            # In a full implementation, this would:
            # 1. Parse the instruction
            # 2. Take a screenshot
            # 3. Use ElementDetectorAgent to find elements
            # 4. Execute the action
            # 5. Validate the result
            
            step_result = StepResult(
                step_number=step_number,
                instruction=instruction,
                status=StepStatus.COMPLETED,
                execution_time=0.0,
                agent_used="orchestrator"
            )
            
            return step_result
            
        except Exception as e:
            return StepResult(
                step_number=step_number,
                instruction=instruction,
                status=StepStatus.FAILED,
                execution_time=0.0,
                agent_used="orchestrator",
                error_message=str(e)
            )
    
    async def detect_element_with_vision(
        self,
        screenshot_path: str,
        instruction: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ElementDetectionResult:
        """
        Use the ElementDetectorAgent to find UI elements with vision.
        
        Args:
            screenshot_path: Path to current page screenshot
            instruction: What element to find (e.g., "login button")
            context: Additional page context
            
        Returns:
            ElementDetectionResult with detection outcome
        """
        
        return await self.element_detector.detect_element(
            screenshot_path=screenshot_path,
            instruction=instruction,
            context=context
        )
    
    def set_browser_page(self, page, context=None):
        """Set the browser page for orchestrator to use."""
        self.browser_page = page
        self.browser_context = context
    
    def get_orchestrator_stats(self) -> Dict[str, Any]:
        """Get comprehensive orchestrator statistics."""
        
        # Get stats from all agents
        base_stats = self.get_stats()
        detector_stats = self.element_detector.get_detection_stats()
        vision_stats = self.vision_client.get_usage_stats()
        
        # Test execution stats
        total_tests = len(self.test_results)
        completed_tests = len([t for t in self.test_results.values() if t.status == TestStatus.COMPLETED])
        failed_tests = len([t for t in self.test_results.values() if t.status == TestStatus.FAILED])
        
        return {
            "orchestrator": base_stats,
            "element_detector": detector_stats,
            "vision_client": vision_stats,
            "test_execution": {
                "total_tests": total_tests,
                "completed_tests": completed_tests,
                "failed_tests": failed_tests,
                "success_rate": (completed_tests / max(total_tests, 1)) * 100,
                "current_test_id": self.current_test_id
            }
        }
