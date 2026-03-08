"""
Jira API client for NanoClaw.

Handles communication with Jira for posting comments and attachments.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from base64 import b64encode

import httpx


logger = logging.getLogger(__name__)


class JiraClient:
    """
    Client for interacting with Jira API.

    Supports:
    - Posting comments to tickets
    - Uploading attachments
    - Getting ticket information
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        email: Optional[str] = None,
        api_token: Optional[str] = None,
    ):
        """
        Initialize Jira client.

        Args:
            base_url: Jira instance base URL
            email: Jira account email
            api_token: Jira API token
        """
        self.base_url = base_url or os.getenv("JIRA_BASE_URL")
        self.email = email or os.getenv("JIRA_EMAIL")
        self.api_token = api_token or os.getenv("JIRA_API_TOKEN")

        if not all([self.base_url, self.email, self.api_token]):
            raise ValueError(
                "Jira credentials not provided. "
                "Set JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN environment variables."
            )

        # Create HTTP client with authentication
        self._http_client: Optional[httpx.AsyncClient] = None

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            # Create auth header
            auth_string = f"{self.email}:{self.api_token}"
            auth_header = b64encode(auth_string.encode()).decode()

            self._http_client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=30.0,
            )

        return self._http_client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def post_comment(
        self,
        ticket_id: str,
        comment: str,
    ) -> Dict[str, Any]:
        """
        Post a comment to a Jira ticket.

        Args:
            ticket_id: Jira ticket ID (e.g., "QA-456")
            comment: Comment body (supports markdown/Atlassian wiki)

        Returns:
            Response from Jira API

        Raises:
            httpx.HTTPStatusError: If request fails
        """
        logger.info(f"Posting comment to {ticket_id}")

        url = f"/rest/api/3/issue/{ticket_id}/comment"
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": comment,
                            }
                        ],
                    }
                ],
            }
        }

        try:
            response = await self.http_client.post(url, json=payload)
            response.raise_for_status()

            result = response.json()
            logger.info(f"Comment posted successfully to {ticket_id}")
            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to post comment to {ticket_id}: {e}")
            raise

    async def add_attachment(
        self,
        ticket_id: str,
        file_path: str,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Attach a file to a Jira ticket.

        Args:
            ticket_id: Jira ticket ID
            file_path: Path to file to attach
            filename: Optional custom filename

        Returns:
            Response from Jira API

        Raises:
            httpx.HTTPStatusError: If request fails
        """
        logger.info(f"Attaching file to {ticket_id}: {file_path}")

        url = f"/rest/api/3/issue/{ticket_id}/attachments"

        # Read file
        with open(file_path, "rb") as f:
            file_content = f.read()

        # Prepare multipart form data
        files = {
            "file": (filename or os.path.basename(file_path), file_content),
        }

        # Note: Attachments endpoint uses different headers
        headers = {
            "X-Atlassian-Token": "nocheck",  # Bypass XSRF check
        }

        try:
            # Create new client for multipart request
            auth_string = f"{self.email}:{self.api_token}"
            auth_header = b64encode(auth_string.encode()).decode()

            async with httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Basic {auth_header}",
                    **headers,
                },
                timeout=60.0,  # Longer timeout for file uploads
            ) as client:
                response = await client.post(url, files=files)
                response.raise_for_status()

            result = response.json()
            logger.info(f"File attached successfully to {ticket_id}")
            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to attach file to {ticket_id}: {e}")
            raise

    async def add_attachments(
        self,
        ticket_id: str,
        file_paths: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Attach multiple files to a Jira ticket.

        Args:
            ticket_id: Jira ticket ID
            file_paths: List of file paths to attach

        Returns:
            List of responses from Jira API
        """
        results = []

        for file_path in file_paths:
            try:
                result = await self.add_attachment(ticket_id, file_path)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to attach {file_path}: {e}")
                # Continue with other files

        return results

    async def get_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """
        Get ticket information from Jira.

        Args:
            ticket_id: Jira ticket ID

        Returns:
            Ticket information

        Raises:
            httpx.HTTPStatusError: If request fails
        """
        logger.info(f"Getting ticket info for {ticket_id}")

        url = f"/rest/api/3/issue/{ticket_id}"

        try:
            response = await self.http_client.get(url)
            response.raise_for_status()

            result = response.json()
            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get ticket {ticket_id}: {e}")
            raise

    async def update_ticket_status(
        self,
        ticket_id: str,
        status_name: str,
    ) -> Dict[str, Any]:
        """
        Update ticket status.

        Args:
            ticket_id: Jira ticket ID
            status_name: New status name (must exist in workflow)

        Returns:
            Response from Jira API

        Raises:
            httpx.HTTPStatusError: If request fails
        """
        logger.info(f"Updating {ticket_id} status to {status_name}")

        # First, get the ticket to find transition ID
        ticket = await self.get_ticket(ticket_id)
        transitions_url = f"/rest/api/3/issue/{ticket_id}/transitions"

        try:
            # Get available transitions
            response = await self.http_client.get(transitions_url)
            response.raise_for_status()
            transitions_data = response.json()

            # Find transition ID for target status
            transition_id = None
            for transition in transitions_data.get("transitions", []):
                if transition["to"]["name"] == status_name:
                    transition_id = transition["id"]
                    break

            if not transition_id:
                raise ValueError(f"Transition to '{status_name}' not available for {ticket_id}")

            # Perform transition
            payload = {
                "transition": {
                    "id": transition_id,
                }
            }

            response = await self.http_client.post(transitions_url, json=payload)
            response.raise_for_status()

            logger.info(f"Ticket {ticket_id} status updated to {status_name}")
            return {"status": "success", "new_status": status_name}

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update {ticket_id} status: {e}")
            raise
