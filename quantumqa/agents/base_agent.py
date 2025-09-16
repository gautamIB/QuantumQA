#!/usr/bin/env python3
"""
Base Agent class for QuantumQA multi-agent system.
Provides common functionality for all specialized agents.
"""

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, List

from ..core.models import AgentMessage, MessageType, Priority


class BaseAgent(ABC):
    """Base class for all QuantumQA agents."""
    
    def __init__(self, agent_id: str, agent_type: str):
        """Initialize base agent."""
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.created_at = datetime.now()
        
        # Message handling
        self.message_handlers = {}
        self.message_history: List[AgentMessage] = []
        
        # Performance tracking
        self.total_executions = 0
        self.total_execution_time = 0.0
        self.success_count = 0
        self.error_count = 0
        
        # State
        self.is_busy = False
        self.current_task = None
        
        print(f"🤖 {self.agent_type} agent '{agent_id}' initialized")
    
    async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle incoming message from another agent."""
        
        # Record message
        self.message_history.append(message)
        
        # Find appropriate handler
        handler = self.message_handlers.get(message.message_type)
        if handler:
            try:
                self.is_busy = True
                self.current_task = message.message_type.value
                start_time = time.time()
                
                # Execute handler
                response = await handler(message)
                
                # Track performance
                execution_time = time.time() - start_time
                self.total_executions += 1
                self.total_execution_time += execution_time
                self.success_count += 1
                
                return response
                
            except Exception as e:
                self.error_count += 1
                print(f"❌ {self.agent_type} agent error handling {message.message_type}: {e}")
                
                # Return error response
                return AgentMessage(
                    id=str(uuid.uuid4()),
                    sender=self.agent_id,
                    recipient=message.sender,
                    message_type=MessageType.ERROR_OCCURRED,
                    payload={
                        "error": str(e),
                        "original_message": message.id
                    },
                    timestamp=datetime.now(),
                    parent_message_id=message.id
                )
            finally:
                self.is_busy = False
                self.current_task = None
        else:
            print(f"⚠️ {self.agent_type} agent: No handler for message type {message.message_type}")
            return None
    
    def register_handler(self, message_type: MessageType, handler_func):
        """Register a handler function for a specific message type."""
        self.message_handlers[message_type] = handler_func
        print(f"📝 {self.agent_type} agent: Registered handler for {message_type}")
    
    async def send_message(
        self, 
        recipient: str, 
        message_type: MessageType, 
        payload: Dict[str, Any],
        priority: Priority = Priority.NORMAL,
        parent_message_id: Optional[str] = None
    ) -> AgentMessage:
        """Send message to another agent."""
        
        message = AgentMessage(
            id=str(uuid.uuid4()),
            sender=self.agent_id,
            recipient=recipient,
            message_type=message_type,
            payload=payload,
            timestamp=datetime.now(),
            parent_message_id=parent_message_id,
            priority=priority
        )
        
        # Record outgoing message
        self.message_history.append(message)
        
        return message
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent performance statistics."""
        avg_execution_time = (self.total_execution_time / max(self.total_executions, 1))
        success_rate = (self.success_count / max(self.total_executions, 1)) * 100
        
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "created_at": self.created_at.isoformat(),
            "is_busy": self.is_busy,
            "current_task": self.current_task,
            "total_executions": self.total_executions,
            "total_execution_time": round(self.total_execution_time, 2),
            "average_execution_time": round(avg_execution_time, 2),
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": round(success_rate, 1),
            "messages_handled": len(self.message_history)
        }
    
    def get_recent_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent message history."""
        recent = self.message_history[-limit:] if self.message_history else []
        return [
            {
                "id": msg.id,
                "type": msg.message_type.value,
                "sender": msg.sender,
                "recipient": msg.recipient,
                "timestamp": msg.timestamp.isoformat(),
                "payload_keys": list(msg.payload.keys()) if msg.payload else []
            }
            for msg in recent
        ]
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize agent-specific components."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up agent resources."""
        pass
    
    def __str__(self) -> str:
        return f"{self.agent_type}Agent(id='{self.agent_id}', busy={self.is_busy})"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(agent_id='{self.agent_id}', agent_type='{self.agent_type}')"
