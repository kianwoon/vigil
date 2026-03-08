"""
Connection testing functions for setup wizard.

Tests API connections to configured services before saving configuration.
"""

import asyncio
from typing import Optional, Tuple
from urllib.parse import urljoin

import requests
from rich.console import Console

console = Console()


def test_jira_connection(
    base_url: str,
    email: str,
    api_token: str,
    timeout: int = 10,
) -> Tuple[bool, Optional[str]]:
    """
    Test Jira API connection.

    Args:
        base_url: Jira base URL
        email: User email
        api_token: API token
        timeout: Request timeout in seconds

    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Clean URL
        base_url = base_url.strip().rstrip("/")

        # Test endpoint: get current user
        api_url = urljoin(base_url, "/rest/api/3/myself")

        console.print(f"  [dim]Testing Jira connection to {base_url}...[/dim]")

        response = requests.get(
            api_url,
            auth=(email, api_token),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

        if response.status_code == 200:
            user_data = response.json()
            display_name = user_data.get("displayName", email)
            console.print(f"  [green]✓[/green] Connected as: {display_name}")
            return True, None

        elif response.status_code == 401:
            return False, "Authentication failed - check email and API token"

        elif response.status_code == 403:
            return False, "Access forbidden - check API token permissions"

        elif response.status_code == 404:
            return False, "Jira API not found - check base URL"

        else:
            return False, f"Connection failed with status {response.status_code}"

    except requests.exceptions.Timeout:
        return False, f"Connection timed out after {timeout}s"

    except requests.exceptions.ConnectionError as e:
        return False, f"Connection error: {str(e)[:100]}"

    except Exception as e:
        return False, f"Unexpected error: {str(e)[:100]}"


def test_jira_project(
    base_url: str,
    email: str,
    api_token: str,
    project_key: str,
    timeout: int = 10,
) -> Tuple[bool, Optional[str]]:
    """
    Test access to a specific Jira project.

    Args:
        base_url: Jira base URL
        email: User email
        api_token: API token
        project_key: Project key to test
        timeout: Request timeout in seconds

    Returns:
        Tuple of (success, error_message)
    """
    try:
        base_url = base_url.strip().rstrip("/")
        project_key = project_key.strip().upper()

        api_url = urljoin(base_url, f"/rest/api/3/project/{project_key}")

        console.print(f"  [dim]Testing project access: {project_key}...[/dim]")

        response = requests.get(
            api_url,
            auth=(email, api_token),
            headers={"Accept": "application/json"},
            timeout=timeout,
        )

        if response.status_code == 200:
            project_data = response.json()
            project_name = project_data.get("name", project_key)
            console.print(f"  [green]✓[/green] Project: {project_name}")
            return True, None

        elif response.status_code == 404:
            return False, f"Project '{project_key}' not found"

        elif response.status_code == 403:
            return False, f"No access to project '{project_key}'"

        else:
            return False, f"Failed with status {response.status_code}"

    except Exception as e:
        return False, f"Error: {str(e)[:100]}"


def test_teams_connection(
    app_id: str,
    app_password: str,
    timeout: int = 10,
) -> Tuple[bool, Optional[str]]:
    """
    Test Microsoft Teams Bot connection.

    Validates the App ID and password format. Full connection testing
    requires the Bot Framework which needs the bot to be running.

    Args:
        app_id: Teams App ID (GUID)
        app_password: Teams App Password
        timeout: Request timeout in seconds

    Returns:
        Tuple of (success, error_message)
    """
    import re

    try:
        console.print("  [dim]Validating Teams credentials...[/dim]")

        # Validate App ID format (should be a GUID)
        guid_pattern = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"

        if not re.match(guid_pattern, app_id):
            return False, "App ID must be a valid GUID (e.g., 12345678-1234-1234-1234-123456789012)"

        # Validate password length (Microsoft generates 40-character passwords)
        if len(app_password) < 20:
            return False, "App password seems too short - check your Azure Bot configuration"

        # Note: Full authentication test requires OAuth token exchange
        # which is done when the bot starts. Here we just validate format.

        console.print(f"  [green]✓[/green] App ID format valid: {app_id[:8]}...{app_id[-4:]}")
        console.print("  [dim]Note: Full connection test happens when bot starts[/dim]")

        return True, None

    except Exception as e:
        return False, f"Validation error: {str(e)[:100]}"


def test_whatsapp_webhook(
    webhook_url: str,
    timeout: int = 10,
) -> Tuple[bool, Optional[str]]:
    """
    Test WhatsApp webhook URL reachability.

    Args:
        webhook_url: WhatsApp webhook URL
        timeout: Request timeout in seconds

    Returns:
        Tuple of (success, error_message)
    """
    try:
        console.print(f"  [dim]Testing webhook reachability...[/dim]")

        # Just test if the URL is reachable (HEAD request)
        response = requests.head(webhook_url, timeout=timeout, allow_redirects=True)

        # Any response means the URL is reachable
        console.print(f"  [green]✓[/green] Webhook reachable (status {response.status_code})")
        return True, None

    except requests.exceptions.Timeout:
        return False, f"Webhook timed out after {timeout}s"

    except requests.exceptions.ConnectionError:
        return False, "Could not reach webhook URL"

    except Exception as e:
        return False, f"Error: {str(e)[:100]}"


def test_shared_volume(
    volume_path: str,
    create_if_missing: bool = True,
) -> Tuple[bool, Optional[str]]:
    """
    Test shared volume path accessibility.

    Args:
        volume_path: Path to shared volume
        create_if_missing: Create directory if it doesn't exist

    Returns:
        Tuple of (success, error_message)
    """
    import os
    from pathlib import Path

    try:
        expanded_path = os.path.expanduser(volume_path)
        path = Path(expanded_path)

        console.print(f"  [dim]Checking shared volume: {expanded_path}...[/dim]")

        if path.exists():
            # Check if writable
            if os.access(expanded_path, os.W_OK):
                console.print(f"  [green]✓[/green] Volume path exists and is writable")
                return True, None
            else:
                return False, "Volume path exists but is not writable"

        elif create_if_missing:
            try:
                path.mkdir(parents=True, exist_ok=True)
                console.print(f"  [green]✓[/green] Created volume directory")
                return True, None
            except PermissionError:
                return False, "Permission denied - cannot create directory"

        else:
            return False, "Volume path does not exist"

    except Exception as e:
        return False, f"Error: {str(e)[:100]}"
