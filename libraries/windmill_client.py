"""
Windmill API Client for common use across cogs
Handles API communication, error handling, and URL validation
"""
import logging
import aiohttp
import json
import os
import asyncio
from typing import Optional, Dict, Any

log = logging.getLogger("red.tanx.windmill_client")


class WindmillClient:
    """
    A reusable client for interacting with Windmill API.
    Handles authentication, error handling, and URL validation.
    """
    
    def __init__(self):
        """Initialize the Windmill client with credentials from environment variables"""
        self.token = os.getenv("WINDMILL_TOKEN")
        self.url = os.getenv("WINDMILL_URL")
        
        if not self.token:
            log.warning("WINDMILL_TOKEN environment variable not set.")
        if not self.url:
            log.warning("WINDMILL_URL environment variable not set.")
    
    def is_configured(self) -> bool:
        """Check if Windmill client is properly configured"""
        return bool(self.token and self.url)
    
    async def is_url_accessible(self, url: str, timeout: int = 10) -> bool:
        """
        Validate that a URL is accessible.
        Useful for checking Discord attachment URLs before sending to Windmill.
        
        Args:
            url (str): URL to validate
            timeout (int): Timeout in seconds
            
        Returns:
            bool: True if URL is accessible, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                    return response.status == 200
        except Exception as e:
            log.warning(f"URL validation failed for {url}: {e}")
            return False
    
    async def call_api(
        self, 
        body: Dict[str, Any],
        path: str,
        timeout: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Make a POST request to the Windmill API.
        
        Args:
            body (Dict): Request body to send
            path (str): API endpoint path (required, will be appended to WINDMILL_URL)
            timeout (int): Timeout in seconds
            
        Returns:
            Dict: Parsed JSON response, or None if error occurred
            
        Raises:
            ValueError: If path is empty or None
        """
        if not path or not path.strip():
            raise ValueError("path parameter is mandatory and cannot be empty or None")
        
        if not self.is_configured():
            log.error("Windmill client not configured. Set WINDMILL_TOKEN and WINDMILL_URL.")
            return None
        
        # Construct the full URL
        api_url = f"{self.url.rstrip('/')}/{path.lstrip('/')}"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    api_url, 
                    json=body, 
                    headers=headers, 
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        log.error(f"Windmill API returned status {response.status}: {error_text}")
                        return None
                    
                    return await response.json()
        
        except asyncio.TimeoutError:
            log.error("Windmill API request timed out")
            return None
        except aiohttp.ClientError as e:
            log.error(f"Failed to connect to Windmill API: {e}")
            return None
        except json.JSONDecodeError as e:
            log.error(f"Failed to parse Windmill API response: {e}")
            return None
        except Exception as e:
            log.error(f"Unexpected error in Windmill API call: {e}", exc_info=True)
            return None
    

# Singleton instance for convenience
_windmill_client = None


def get_windmill_client() -> WindmillClient:
    """Get or create the singleton Windmill client instance"""
    global _windmill_client
    if _windmill_client is None:
        _windmill_client = WindmillClient()
    return _windmill_client
