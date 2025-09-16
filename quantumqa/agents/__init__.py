"""
Multi-Agent System for QuantumQA.
Provides specialized agents for different aspects of UI testing.
"""

from .base_agent import BaseAgent
from .element_detector import ElementDetectorAgent
from .orchestrator import OrchestratorAgent

__all__ = [
    "BaseAgent",
    "ElementDetectorAgent",
    "OrchestratorAgent"
]
