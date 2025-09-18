#!/usr/bin/env python3
"""
GIF Creator Utility - Creates animated GIFs from accumulated screenshots
"""

import os
import time
from pathlib import Path
from typing import List, Optional
from PIL import Image


class GifCreator:
    """Creates animated GIFs from a sequence of screenshots."""
    
    def __init__(self):
        self.accumulated_screenshots: List[str] = []
        self.gif_settings = {
            'duration': 750,  # milliseconds per frame (doubled speed from 1500ms)
            'loop': 0,  # infinite loop
            'optimize': True,
            'save_all': True
        }
        # Track last screenshot per step to avoid duplicates
        self._step_screenshots = {}  # step_number -> screenshot_path
    
    def add_screenshot(self, screenshot_path: str) -> None:
        """Add a screenshot to the accumulation list."""
        if screenshot_path and os.path.exists(screenshot_path):
            self.accumulated_screenshots.append(screenshot_path)
            print(f"    📸 Screenshot added to GIF queue: {os.path.basename(screenshot_path)}")
    
    def add_step_screenshot(self, screenshot_path: str, step_number: int, screenshot_type: str = "step") -> None:
        """
        Add a step-specific screenshot, replacing any previous screenshot for the same step.
        This helps avoid multiple screenshots per step in the GIF.
        
        Args:
            screenshot_path: Path to the screenshot file
            step_number: The step number this screenshot belongs to
            screenshot_type: Type of screenshot (step, action, analysis, etc.)
        """
        if not screenshot_path or not os.path.exists(screenshot_path):
            return
            
        # If we already have a screenshot for this step, remove the old one
        if step_number in self._step_screenshots:
            old_screenshot = self._step_screenshots[step_number]
            if old_screenshot in self.accumulated_screenshots:
                self.accumulated_screenshots.remove(old_screenshot)
                print(f"    🔄 Replaced step {step_number} screenshot in GIF queue")
        
        # Add the new screenshot
        self.accumulated_screenshots.append(screenshot_path)
        self._step_screenshots[step_number] = screenshot_path
        print(f"    📸 Step {step_number} ({screenshot_type}) screenshot added to GIF queue: {os.path.basename(screenshot_path)}")
    
    def create_gif(self, output_path: str, title: str = "Test Execution", custom_filename: Optional[str] = None) -> Optional[str]:
        """
        Create an animated GIF from accumulated screenshots.
        
        Args:
            output_path: Path where GIF should be saved
            title: Title for the GIF (used in filename if output_path is a directory)
            custom_filename: Optional custom filename (overrides title-based naming)
            
        Returns:
            Path to created GIF file, or None if creation failed
        """
        if not self.accumulated_screenshots:
            print("    ⚠️ No screenshots accumulated - cannot create GIF")
            return None
        
        try:
            # Ensure output directory exists
            output_path = Path(output_path)
            if output_path.is_dir():
                # If output_path is a directory, create filename
                if custom_filename:
                    # Use custom filename if provided
                    if not custom_filename.endswith('.gif'):
                        custom_filename += '.gif'
                    filename = custom_filename
                else:
                    # Use title-based naming with timestamp
                    timestamp = int(time.time())
                    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).strip()
                    safe_title = safe_title.replace(' ', '_').lower()
                    filename = f"{safe_title}_{timestamp}.gif"
                gif_path = output_path / filename
            else:
                # output_path is a full file path
                gif_path = output_path
                gif_path.parent.mkdir(parents=True, exist_ok=True)
            
            print(f"\n🎬 Creating GIF from {len(self.accumulated_screenshots)} screenshots...")
            print(f"    📁 Output: {gif_path}")
            
            # Load and process images
            images = []
            target_size = None
            
            for i, screenshot_path in enumerate(self.accumulated_screenshots):
                try:
                    img = Image.open(screenshot_path)
                    
                    # Convert to RGB if necessary (for GIF compatibility)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Resize to a reasonable size for GIF (to reduce file size)
                    if target_size is None:
                        # Use first image to determine target size
                        width, height = img.size
                        # Scale down if too large (keep aspect ratio)
                        max_width, max_height = 1200, 800
                        if width > max_width or height > max_height:
                            ratio = min(max_width / width, max_height / height)
                            target_size = (int(width * ratio), int(height * ratio))
                        else:
                            target_size = (width, height)
                    
                    # Resize image to target size
                    img = img.resize(target_size, Image.Resampling.LANCZOS)
                    images.append(img)
                    
                except Exception as e:
                    print(f"    ⚠️ Could not process screenshot {i+1}: {e}")
                    continue
            
            if not images:
                print("    ❌ No valid images to create GIF")
                return None
            
            # Create GIF
            first_image = images[0]
            remaining_images = images[1:] if len(images) > 1 else []
            
            first_image.save(
                str(gif_path),
                format='GIF',
                append_images=remaining_images,
                **self.gif_settings
            )
            
            # Get file size for reporting
            file_size = gif_path.stat().st_size
            size_mb = file_size / (1024 * 1024)
            
            print(f"    ✅ GIF created successfully!")
            print(f"    📊 Frames: {len(images)}, Size: {size_mb:.2f} MB")
            print(f"    🎯 Duration: {len(images) * self.gif_settings['duration'] / 1000:.1f} seconds")
            
            return str(gif_path)
            
        except Exception as e:
            print(f"    ❌ Failed to create GIF: {e}")
            return None
    
    def clear_screenshots(self) -> None:
        """Clear the accumulated screenshots list."""
        count = len(self.accumulated_screenshots)
        self.accumulated_screenshots.clear()
        self._step_screenshots.clear()
        print(f"    🧹 Cleared {count} screenshots from GIF queue")
    
    def set_gif_settings(self, duration: int = None, loop: int = None, optimize: bool = None) -> None:
        """
        Update GIF creation settings.
        
        Args:
            duration: Milliseconds per frame
            loop: Number of loops (0 = infinite)
            optimize: Whether to optimize GIF size
        """
        if duration is not None:
            self.gif_settings['duration'] = duration
        if loop is not None:
            self.gif_settings['loop'] = loop
        if optimize is not None:
            self.gif_settings['optimize'] = optimize
        
        print(f"    ⚙️ GIF settings updated: {self.gif_settings}")
    
    def get_screenshot_count(self) -> int:
        """Get the number of accumulated screenshots."""
        return len(self.accumulated_screenshots)
