"""
Image processing tool using ImageMagick via Windmill API.
"""
from typing import Dict, Any
import os
import sys
import asyncio
import aiohttp
import base64
import logging
import concurrent.futures

# Add parent directory to path to import libraries
cog_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if cog_root not in sys.path:
    sys.path.insert(0, cog_root)

try:
    from libraries.windmill_client import WindmillClient
except ImportError:
    # Fallback: try importing from absolute path
    import importlib.util
    windmill_path = os.path.join(cog_root, 'libraries', 'windmill_client.py')
    spec = importlib.util.spec_from_file_location("windmill_client", windmill_path)
    windmill_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(windmill_module)
    WindmillClient = windmill_module.WindmillClient

from .base import BaseTool

log = logging.getLogger("red.tanx.llm.tools.image_processor")


class ImageProcessorTool(BaseTool):
    """Tool for processing images using ImageMagick via Windmill API."""
    
    def __init__(self):
        self.windmill_client = WindmillClient()
    
    @property
    def name(self) -> str:
        return "process_image"
    
    @property
    def description(self) -> str:
        return (
            "Process an image using ImageMagick commands. Use this when a user wants to edit, transform, "
            "or manipulate an image (resize, rotate, apply effects, convert format, add text, etc.). "
            "You must provide the image URL and the ImageMagick command to execute."
        )
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "URL of the image to process (can be a Discord CDN URL or any accessible image URL)"
                },
                "magick_command": {
                    "type": "string",
                    "description": (
                        "ImageMagick command to execute (without 'magick' prefix). "
                        "Always include input and output file names as 'input_img' and 'output_img' in the command. "
                        "Remember to always include the input and output file names in the command."
                        "Example: 'convert input_img -resize 50% output_img' or "
                        "'-rotate 90 -quality 85'."
                    )
                }
            },
            "required": ["image_url", "magick_command"]
        }
    
    def execute(self, arguments: Dict[str, Any]) -> str:
        """
        Process an image using ImageMagick via Windmill API.
        
        Args:
            arguments: Dict with 'image_url' and 'magick_command'
            
        Returns:
            Special formatted string with base64 image data or error message
        """
        if not self.windmill_client.is_configured():
            return (
                "Image processing is not configured. To enable image processing:\n"
                "1. Set WINDMILL_TOKEN environment variable\n"
                "2. Set WINDMILL_URL environment variable\n"
                "3. Ensure Windmill has an image processing endpoint\n"
                "4. Restart the bot"
            )
        
        image_url = arguments.get("image_url", "")
        magick_command = arguments.get("magick_command", "")
        
        if not image_url:
            return "Error: No image URL provided"
        
        if not magick_command:
            return "Error: No ImageMagick command provided"
        
        # Run async operations in a way that works with or without a running event loop
        return self._run_async(self._execute_async(image_url, magick_command))
    
    def _run_async(self, coro):
        """
        Run an async coroutine, handling both running and non-running event loop cases.
        
        Args:
            coro: Coroutine to execute
            
        Returns:
            Result of the coroutine
        """
        try:
            # Check if there's already a running event loop
            loop = asyncio.get_running_loop()
            # We're in a running loop, need to use a thread to avoid "loop already running" error
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        except RuntimeError:
            # No running loop, safe to use asyncio.run()
            return asyncio.run(coro)
    
    async def _execute_async(self, image_url: str, magick_command: str) -> str:
        """
        Execute the full image processing workflow asynchronously.
        
        Args:
            image_url: URL of the image to process
            magick_command: ImageMagick command to execute
            
        Returns:
            Result string
        """
        # Check if URL is accessible
        is_accessible = await self.windmill_client.is_url_accessible(image_url, timeout=10)
        
        if not is_accessible:
            return f"Error: Image URL is not accessible: {image_url}"
        
        # Process image via Windmill API
        return await self._process_image_async(image_url, magick_command)
    
    async def _process_image_async(self, image_url: str, magick_command: str) -> str:
        """
        Call Windmill API to process the image.
        
        Args:
            image_url: URL of the image to process
            magick_command: ImageMagick command to execute
            
        Returns:
            Formatted string with image data or error message
        """
        body = {
            "imageUrl": image_url,
            "magickCommand": magick_command
        }
        
        try:
            result = await self.windmill_client.call_api(
                body=body,
                path="/api/w/main/jobs/run_wait_result/f/f/media/edit_image_flow",
                timeout=60  # Image processing might take longer
            )
            
            if not result:
                return "Error: Failed to process image (no response from Windmill API)"
            
            # Check if result contains base64 image data
            if "image_base64" in result:
                base64_data = result["image_base64"]
                # Strip any whitespace from base64 data to ensure clean parsing
                base64_data = base64_data.strip().replace("\n", "").replace("\r", "").replace(" ", "")
                format_type = result.get("format", "png")
                
                # Return special formatted string that the bot will parse
                return f"[IMAGE_PROCESSED]\nFormat: {format_type}\nData: {base64_data}\n[/IMAGE_PROCESSED]"
            
            elif "error" in result:
                return f"Error processing image: {result['error']}"
            
            else:
                return f"Image processing completed but no image data returned. Response: {result}"
                
        except Exception as e:
            log.error(f"Error calling Windmill API for image processing: {e}")
            return f"Error processing image: {str(e)}"
