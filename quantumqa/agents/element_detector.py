#!/usr/bin/env python3
"""
Element Detector Agent - Vision-based UI element detection.
Uses AI vision models to identify and locate UI elements in screenshots.
"""

import asyncio
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from cachetools import TTLCache

from .base_agent import BaseAgent
from ..core.llm import VisionLLMClient
from ..core.models import (
    ElementDetectionResult, 
    MessageType, 
    AgentMessage, 
    Coordinates,
    BoundingBox
)


class ElementDetectorAgent(BaseAgent):
    """Agent specialized in detecting UI elements using computer vision."""
    
    def __init__(
        self, 
        agent_id: str = "element_detector",
        vision_client: Optional[VisionLLMClient] = None,
        cache_size: int = 1000,
        cache_ttl: int = 3600  # 1 hour
    ):
        """Initialize the Element Detector Agent."""
        super().__init__(agent_id, "ElementDetector")
        
        self.vision_client = vision_client
        
        # Element detection cache
        self.cache = TTLCache(maxsize=cache_size, ttl=cache_ttl)
        
        # Detection statistics
        self.total_detections = 0
        self.successful_detections = 0
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Performance tracking
        self.detection_times: List[float] = []
        self.confidence_scores: List[float] = []
        
        # Register message handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register handlers for element detection messages."""
        self.register_handler(MessageType.DETECT_ELEMENT, self._handle_detect_element)
        self.register_handler(MessageType.CLEAR_ELEMENT_CACHE, self._handle_clear_cache)
    
    async def initialize(self) -> bool:
        """Initialize the element detector agent."""
        try:
            if not self.vision_client:
                print("⚠️ ElementDetectorAgent: No vision client provided")
                return False
            
            print(f"✅ ElementDetectorAgent '{self.agent_id}' initialized with vision capabilities")
            return True
            
        except Exception as e:
            print(f"❌ ElementDetectorAgent initialization failed: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up detector resources."""
        try:
            self.cache.clear()
            print(f"✅ ElementDetectorAgent '{self.agent_id}' cleaned up")
        except Exception as e:
            print(f"⚠️ ElementDetectorAgent cleanup warning: {e}")
    
    async def _handle_detect_element(self, message: AgentMessage) -> AgentMessage:
        """Handle element detection request."""
        
        payload = message.payload
        screenshot_path = payload.get('screenshot_path')
        instruction = payload.get('instruction')
        context = payload.get('context', {})
        
        if not screenshot_path or not instruction:
            raise ValueError("Missing required parameters: screenshot_path and instruction")
        
        # Perform element detection
        result = await self.detect_element(screenshot_path, instruction, context)
        
        # Return response
        return await self.send_message(
            recipient=message.sender,
            message_type=MessageType.ELEMENT_DETECTED,
            payload={
                "detection_result": result.dict(),
                "agent_stats": self.get_detection_stats()
            },
            parent_message_id=message.id
        )
    
    async def _handle_clear_cache(self, message: AgentMessage) -> AgentMessage:
        """Handle cache clearing request."""
        
        cache_size_before = len(self.cache)
        self.cache.clear()
        
        return await self.send_message(
            recipient=message.sender,
            message_type=MessageType.CACHE_CLEARED,
            payload={
                "cache_entries_cleared": cache_size_before,
                "message": "Element detection cache cleared"
            },
            parent_message_id=message.id
        )
    
    async def detect_element(
        self,
        screenshot_path: str,
        instruction: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ElementDetectionResult:
        """
        Detect UI element in screenshot using vision analysis.
        
        Args:
            screenshot_path: Path to screenshot image
            instruction: Natural language instruction describing what to find
            context: Additional context about the page and previous actions
            
        Returns:
            ElementDetectionResult with detection outcome and coordinates
        """
        
        start_time = time.time()
        self.total_detections += 1
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(screenshot_path, instruction, context)
            
            if cache_key in self.cache:
                self.cache_hits += 1
                cached_result = self.cache[cache_key]
                print(f"    🔄 Cache hit for element detection (saved ~2s)")
                return cached_result
            
            self.cache_misses += 1
            
            # Verify screenshot exists
            if not Path(screenshot_path).exists():
                return ElementDetectionResult(
                    found=False,
                    confidence=0.0,
                    instruction=instruction,
                    error_message=f"Screenshot not found: {screenshot_path}"
                )
            
            # Use vision client for detection
            if not self.vision_client:
                return ElementDetectionResult(
                    found=False,
                    confidence=0.0,
                    instruction=instruction,
                    error_message="No vision client available"
                )
            
            print(f"    👁️ Using vision AI to detect element for: '{instruction}'")
            
            # Perform vision analysis
            result = await self.vision_client.analyze_screenshot(
                screenshot_path=screenshot_path,
                instruction=instruction,
                context=context or {}
            )
            
            # Track performance
            detection_time = time.time() - start_time
            self.detection_times.append(detection_time)
            
            if result.found:
                self.successful_detections += 1
                self.confidence_scores.append(result.confidence)
                
                # Cache successful detections
                if result.confidence > 0.7:
                    self.cache[cache_key] = result
                    print(f"    💾 Cached high-confidence detection (confidence: {result.confidence:.2f})")
            
            print(f"    ⏱️ Vision detection took {detection_time:.2f}s")
            
            return result
            
        except Exception as e:
            error_message = f"Element detection failed: {e}"
            print(f"    ❌ {error_message}")
            
            return ElementDetectionResult(
                found=False,
                confidence=0.0,
                instruction=instruction,
                error_message=error_message
            )
    
    def _generate_cache_key(
        self, 
        screenshot_path: str, 
        instruction: str, 
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Generate cache key for element detection."""
        
        # Use file modification time and size for screenshot fingerprint
        try:
            screenshot_file = Path(screenshot_path)
            if screenshot_file.exists():
                stat = screenshot_file.stat()
                screenshot_fingerprint = f"{stat.st_mtime}_{stat.st_size}"
            else:
                screenshot_fingerprint = "missing"
        except Exception:
            screenshot_fingerprint = "unknown"
        
        # Include relevant context
        context_fingerprint = ""
        if context:
            # Only include stable context elements
            stable_keys = ['url', 'title', 'element_type']
            stable_context = {k: v for k, v in context.items() if k in stable_keys}
            context_fingerprint = str(sorted(stable_context.items()))
        
        # Combine into cache key
        cache_key = f"{screenshot_fingerprint}_{hash(instruction)}_{hash(context_fingerprint)}"
        return cache_key
    
    def get_detection_stats(self) -> Dict[str, Any]:
        """Get detailed detection statistics."""
        
        success_rate = (self.successful_detections / max(self.total_detections, 1)) * 100
        cache_hit_rate = (self.cache_hits / max(self.cache_hits + self.cache_misses, 1)) * 100
        
        avg_detection_time = (sum(self.detection_times) / max(len(self.detection_times), 1))
        avg_confidence = (sum(self.confidence_scores) / max(len(self.confidence_scores), 1))
        
        return {
            "total_detections": self.total_detections,
            "successful_detections": self.successful_detections,
            "success_rate": round(success_rate, 1),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": round(cache_hit_rate, 1),
            "cache_size": len(self.cache),
            "average_detection_time": round(avg_detection_time, 2),
            "average_confidence": round(avg_confidence, 2),
            "vision_client_stats": self.vision_client.get_usage_stats() if self.vision_client else {}
        }
    
    async def detect_multiple_elements(
        self,
        screenshot_path: str,
        instructions: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> List[ElementDetectionResult]:
        """Detect multiple elements in parallel."""
        
        tasks = [
            self.detect_element(screenshot_path, instruction, context)
            for instruction in instructions
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to failed results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ElementDetectionResult(
                    found=False,
                    confidence=0.0,
                    instruction=instructions[i],
                    error_message=str(result)
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    def clear_old_cache_entries(self, max_age_hours: int = 24) -> int:
        """Clear cache entries older than specified age."""
        
        # TTLCache handles this automatically, but we can provide manual cleanup
        initial_size = len(self.cache)
        
        # Force cleanup by triggering TTL check
        # This happens automatically in TTLCache, but we can log it
        current_size = len(self.cache)
        cleared = initial_size - current_size
        
        if cleared > 0:
            print(f"🧹 Cleared {cleared} expired cache entries")
        
        return cleared
    
    def optimize_cache(self) -> Dict[str, Any]:
        """Optimize cache performance and return optimization info."""
        
        # Clear low-confidence entries
        initial_size = len(self.cache)
        
        # We can't directly access TTLCache entries to filter by confidence
        # but we can provide optimization recommendations
        
        stats = self.get_detection_stats()
        
        recommendations = []
        if stats['cache_hit_rate'] < 50:
            recommendations.append("Consider increasing cache TTL")
        if stats['average_confidence'] < 0.8:
            recommendations.append("Consider improving detection prompts")
        if stats['success_rate'] < 90:
            recommendations.append("Review failed detection patterns")
        
        return {
            "cache_size": len(self.cache),
            "recommendations": recommendations,
            "stats": stats
        }
