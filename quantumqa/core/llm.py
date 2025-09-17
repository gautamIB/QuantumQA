#!/usr/bin/env python3
"""
Vision-LLM Client for screenshot analysis and element detection.
Integrates with OpenAI GPT-4V for intelligent UI element identification.
"""

import base64
import json
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import io
from PIL import Image

try:
    import openai
except ImportError:
    print("⚠️ OpenAI package not installed. Install with: pip install openai")
    openai = None

from ..core.models import ElementDetectionResult, BoundingBox, Coordinates
from ..utils.credentials_loader import get_openai_credentials


class VisionLLMClient:
    """Client for Vision-Language Model operations using OpenAI GPT-4V."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, max_retries: int = 3):
        """
        Initialize the Vision-LLM client.
        
        Args:
            api_key: OpenAI API key. If None, loads from credentials file.
            model: Model to use. If None, loads from credentials file.
            max_retries: Number of retry attempts for failed requests.
        """
        if not openai:
            raise ImportError("OpenAI package required for vision functionality")
        
        # Load credentials from file if not provided
        if api_key is None or model is None:
            print("🔑 Loading OpenAI credentials from configuration...")
            creds = get_openai_credentials()
            
            if not creds.get('api_key'):
                raise ValueError("No OpenAI API key found in credentials file or environment")
            
            api_key = api_key or creds['api_key']
            model = model or creds.get('model', 'gpt-4o-mini')
            
            print(f"✅ Loaded OpenAI credentials: model={model}")
        
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = model
        self.max_retries = max_retries
        
        # Cost tracking
        self.total_requests = 0
        self.estimated_cost = 0.0
        
        print(f"🔮 VisionLLMClient initialized with model: {model}")
    
    async def analyze_screenshot(
        self, 
        screenshot_path: str, 
        instruction: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ElementDetectionResult:
        """
        Analyze screenshot to find UI elements for the given instruction.
        
        Args:
            screenshot_path: Path to screenshot image
            instruction: Natural language instruction to execute
            context: Additional context about the page/previous actions
            
        Returns:
            ElementDetectionResult with detected elements and coordinates
        """
        
        # Prepare image for analysis
        image_base64 = await self._prepare_image(screenshot_path)
        
        # Generate vision prompt
        prompt = self._generate_vision_prompt(instruction, context or {})
        
        # Call vision model with retry logic
        response = await self._call_vision_model_with_retry(image_base64, prompt)
        
        # Parse response into structured result
        return await self._parse_vision_response(response, instruction)
    
    async def _prepare_image(self, screenshot_path: str) -> str:
        """Prepare screenshot image for vision analysis."""
        
        try:
            # Load and optionally resize image
            with Image.open(screenshot_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large (OpenAI has size limits)
                max_size = 2048
                if img.width > max_size or img.height > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                    print(f"    🔄 Resized image to {img.width}x{img.height} for analysis")
                
                # Convert to base64
                buffer = io.BytesIO()
                img.save(buffer, format='PNG', optimize=True)
                image_bytes = buffer.getvalue()
                
                return base64.b64encode(image_bytes).decode('utf-8')
                
        except Exception as e:
            raise Exception(f"Failed to prepare image {screenshot_path}: {e}")
    
    def _generate_vision_prompt(self, instruction: str, context: Dict[str, Any]) -> str:
        """Generate context-aware prompt for vision analysis."""
        
        # Extract context information
        url = context.get('url', 'Unknown')
        previous_action = context.get('previous_action', 'None')
        page_title = context.get('title', 'Unknown')
        
        # Check for UI context (dropdown, modal, etc.)
        ui_context_type = context.get('ui_context_type')
        ui_context_target = context.get('ui_context_target')
        ui_context_opened_step = context.get('ui_context_opened_step')
        search_scope = context.get('search_scope')
        
        # Build the base prompt
        prompt = f"""
Analyze this webpage screenshot to help execute the instruction: "{instruction}"

**Page Context:**
- URL: {url}
- Title: {page_title}
- Previous action: {previous_action}"""
        
        # Add UI context information if available
        if ui_context_type and search_scope:
            prompt += f"""

**🎯 IMPORTANT UI CONTEXT:**
- A {ui_context_type} was opened in a previous step (step {ui_context_opened_step})
- Target element: {ui_context_target}
- SCOPE REQUIREMENT: {search_scope}

**SEARCH STRATEGY:**
- First, identify the {ui_context_type} region that was previously opened
- Look for the {ui_context_type} containing options/buttons related to "{ui_context_target}"
- ONLY search within that {ui_context_type} region for the target element
- DO NOT click elements outside the {ui_context_type} region
- If multiple {ui_context_type}s exist, choose the one that matches the context from step {ui_context_opened_step}"""
        
        prompt += f"""

**Task:** Find the UI element(s) that should be interacted with to execute the instruction."""
        
        # Add specific instructions for context-aware search
        if ui_context_type:
            prompt += f"""

**Context-Aware Instructions:**
1. FIRST: Locate the {ui_context_type} region that was opened previously
2. THEN: Search within that {ui_context_type} for the target element
3. Provide precise coordinates ONLY for elements within the {ui_context_type}
4. Ignore similar elements outside the {ui_context_type}
5. Assess confidence based on element being in correct context"""
        else:
            prompt += """

**Instructions:**
1. Identify the most relevant UI element for the given instruction
2. Provide precise bounding box coordinates (x, y, width, height)
3. Include center coordinates for clicking
4. Assess confidence level (0.0-1.0)
5. Identify element type and any visible text"""
        
        prompt += """

**Response Format (JSON only):**
{{
    "elements": [
        {{
            "element_type": "button|input|link|dropdown|tab|text|etc",
            "description": "Brief description of the element",
            "bounding_box": {{"x": 0, "y": 0, "width": 0, "height": 0}},
            "center_coordinates": {{"x": 0, "y": 0}},
            "confidence": 0.95,
            "visible_text": "text content if any",
            "attributes": {{"class": "button-class", "placeholder": "hint text"}},
            "interaction_type": "click|type|hover|scroll\""""
        
        # Add context-specific fields if UI context exists
        if ui_context_type:
            prompt += f""",
            "ui_context_match": "true|false - whether element is in correct {ui_context_type}",
            "context_region": {{"x": 0, "y": 0, "width": 0, "height": 0}} // bounding box of the {ui_context_type} region"""
        
        prompt += """
        }}
    ],
    "page_analysis": {{
        "layout_type": "form|dashboard|list|search|landing|etc",
        "main_content_area": {{"x": 0, "y": 0, "width": 0, "height": 0}},
        "notable_elements": ["list of other important elements visible"],
        "potential_issues": ["any automation challenges detected"]"""
        
        # Add context analysis if UI context exists
        if ui_context_type:
            prompt += f""",
        "ui_context_analysis": {{
            "context_type": "{ui_context_type}",
            "context_found": "true|false",
            "context_region": {{"x": 0, "y": 0, "width": 0, "height": 0}},
            "context_confidence": 0.95
        }}"""
        
        prompt += """
    }},
    "overall_confidence": 0.85,
    "recommendation": "Primary action to take based on analysis"
}}

**Important:** """
        
        # Add context-specific importance notes
        if ui_context_type:
            prompt += f"""
- CRITICAL: Element MUST be within the {ui_context_type} that was opened in step {ui_context_opened_step}
- Ignore any similar elements outside the {ui_context_type} region
- If no suitable element found in {ui_context_type}, set confidence to 0.0"""
        
        prompt += """
- Be precise with coordinates - they will be used for automation
- If multiple similar elements exist, choose the most appropriate one
- Consider context and typical user workflows
- Return ONLY valid JSON, no additional text"""
        
        
        return prompt
    
    async def _call_vision_model_with_retry(self, image_base64: str, prompt: str) -> Dict[str, Any]:
        """Call vision model with retry logic."""
        
        for attempt in range(self.max_retries):
            try:
                print(f"    🔮 Calling vision model (attempt {attempt + 1}/{self.max_retries})")
                
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{image_base64}",
                                        "detail": "high"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=1500,
                    temperature=0.1  # Low temperature for consistent results
                )
                
                # Track usage for cost estimation
                self.total_requests += 1
                if hasattr(response, 'usage'):
                    # Rough cost estimation (GPT-4V pricing)
                    input_tokens = response.usage.prompt_tokens
                    output_tokens = response.usage.completion_tokens
                    cost = (input_tokens * 0.01 / 1000) + (output_tokens * 0.03 / 1000)
                    self.estimated_cost += cost
                
                content = response.choices[0].message.content.strip()
                
                # Parse JSON response
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    # Try to extract JSON from response if wrapped in text
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group())
                    else:
                        raise ValueError(f"Invalid JSON response: {content[:200]}...")
                
            except Exception as e:
                print(f"    ⚠️ Vision model call failed (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    raise Exception(f"Vision model failed after {self.max_retries} attempts: {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    async def _parse_vision_response(self, response: Dict[str, Any], instruction: str) -> ElementDetectionResult:
        """Parse vision model response into structured result."""
        
        try:
            # Extract primary element
            elements = response.get('elements', [])
            if not elements:
                return ElementDetectionResult(
                    found=False,
                    confidence=0.0,
                    instruction=instruction,
                    error_message="No elements detected in screenshot"
                )
            
            primary_element = elements[0]  # Take the first/best element
            
            # Extract coordinates
            bounding_box_data = primary_element.get('bounding_box', {})
            center_coords_data = primary_element.get('center_coordinates', {})
            
            bounding_box = BoundingBox(
                x=bounding_box_data.get('x', 0),
                y=bounding_box_data.get('y', 0),
                width=bounding_box_data.get('width', 0),
                height=bounding_box_data.get('height', 0)
            )
            
            center_coordinates = Coordinates(
                x=center_coords_data.get('x', 0),
                y=center_coords_data.get('y', 0)
            )
            
            # Build result
            result = ElementDetectionResult(
                found=True,
                confidence=primary_element.get('confidence', 0.8),
                element_type=primary_element.get('element_type', 'unknown'),
                bounding_box=bounding_box,
                center_coordinates=center_coordinates,
                visible_text=primary_element.get('visible_text'),
                attributes=primary_element.get('attributes', {}),
                instruction=instruction,
                interaction_type=primary_element.get('interaction_type', 'click'),
                page_analysis=response.get('page_analysis', {}),
                recommendation=response.get('recommendation', ''),
                alternative_elements=[elem for elem in elements[1:]]  # Other options
            )
            
            print(f"    ✅ Vision detected: {result.element_type} at ({center_coordinates.x}, {center_coordinates.y}) confidence={result.confidence:.2f}")
            
            return result
            
        except Exception as e:
            return ElementDetectionResult(
                found=False,
                confidence=0.0,
                instruction=instruction,
                error_message=f"Failed to parse vision response: {e}"
            )
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for cost tracking."""
        return {
            "total_requests": self.total_requests,
            "estimated_cost": round(self.estimated_cost, 4),
            "model": self.model
        }


class VisionLLMPool:
    """Pool of vision clients for load balancing and failover."""
    
    def __init__(self, api_keys: List[str], model: str = "gpt-4o"):
        self.clients = [VisionLLMClient(key, model) for key in api_keys]
        self.current_client = 0
    
    async def analyze_screenshot(self, screenshot_path: str, instruction: str, context: Optional[Dict[str, Any]] = None) -> ElementDetectionResult:
        """Analyze screenshot using round-robin client selection."""
        
        # Try current client first
        client = self.clients[self.current_client]
        try:
            result = await client.analyze_screenshot(screenshot_path, instruction, context)
            self.current_client = (self.current_client + 1) % len(self.clients)
            return result
        except Exception as e:
            print(f"⚠️ Primary vision client failed: {e}")
            
            # Try other clients
            for i, backup_client in enumerate(self.clients):
                if i != self.current_client:
                    try:
                        result = await backup_client.analyze_screenshot(screenshot_path, instruction, context)
                        self.current_client = i  # Switch to working client
                        return result
                    except Exception as backup_error:
                        print(f"⚠️ Backup client {i} failed: {backup_error}")
            
            # All clients failed
            raise Exception("All vision clients failed")
    
    def get_total_usage_stats(self) -> Dict[str, Any]:
        """Get combined usage statistics from all clients."""
        total_requests = sum(client.total_requests for client in self.clients)
        total_cost = sum(client.estimated_cost for client in self.clients)
        
        return {
            "total_requests": total_requests,
            "estimated_cost": round(total_cost, 4),
            "active_clients": len(self.clients),
            "model": self.clients[0].model if self.clients else "unknown"
        }
