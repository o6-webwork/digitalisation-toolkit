import httpx
import asyncio
from typing import Dict, Any, List
from .logger import app_logger

class APIClient:
    """Centralized async API client for external services with connection pooling"""

    def __init__(self, base_url: str, authorization: str, timeout: int = 600):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {authorization}"
        }
        self.timeout = timeout
        self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client with connection pooling"""
        if self._client is None or self._client.is_closed:
            limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=limits,
                headers=self.headers
            )
        return self._client

    async def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make async POST request to API endpoint"""
        url = f"{self.base_url}{endpoint}"

        try:
            app_logger.info(f"Making async POST request to {url}")
            client = await self._get_client()
            response = await client.post(url, json=data)

            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"Request failed with status code {response.status_code}"
                app_logger.error(error_msg)
                raise httpx.HTTPStatusError(error_msg, request=response.request, response=response)

        except httpx.TimeoutException:
            error_msg = "Request timed out"
            app_logger.error(error_msg)
            raise
        except httpx.RequestError as e:
            error_msg = f"Network error: {str(e)}"
            app_logger.error(error_msg)
            raise
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            app_logger.error(error_msg)
            raise

    async def post_batch(self, endpoint: str, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Make multiple async POST requests concurrently"""
        tasks = [self.post(endpoint, data) for data in data_list]
        return await asyncio.gather(*tasks)

    async def close(self):
        """Close the HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()