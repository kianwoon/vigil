"""
Input validation functions for setup wizard.

Provides validation for URLs, emails, paths, tokens, and other configuration values.
"""

import os
import re
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse


def validate_url(value: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a URL string.

    Args:
        value: URL string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not value or not value.strip():
        return False, "URL cannot be empty"

    value = value.strip()

    try:
        result = urlparse(value)
        if not result.scheme:
            return False, "URL must include scheme (https://)"
        if result.scheme not in ("http", "https"):
            return False, "URL must use http or https scheme"
        if not result.netloc:
            return False, "URL must include a valid host"
        return True, None
    except Exception as e:
        return False, f"Invalid URL format: {e}"


def validate_jira_url(value: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a Jira base URL.

    Args:
        value: Jira URL to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    is_valid, error = validate_url(value)
    if not is_valid:
        return is_valid, error

    value = value.strip().rstrip("/")

    # Check for common Jira patterns
    jira_patterns = [
        r".*\.atlassian\.net$",  # Atlassian Cloud
        r".*\.jira\.com$",       # Jira Cloud alternative
        r".*/jira$",             # Jira Server/Data Center
        r".*/jira/.*$",          # Jira Server with context path
    ]

    is_jira = any(re.match(pattern, value, re.IGNORECASE) for pattern in jira_patterns)

    if not is_jira:
        # Allow but warn - might be custom domain
        pass

    return True, None


def validate_email(value: str) -> Tuple[bool, Optional[str]]:
    """
    Validate an email address.

    Args:
        value: Email string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not value or not value.strip():
        return False, "Email cannot be empty"

    value = value.strip()

    # RFC 5322 simplified pattern
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    if not re.match(email_pattern, value):
        return False, "Invalid email format"

    return True, None


def validate_path(value: str, must_exist: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Validate a file system path.

    Args:
        value: Path string to validate
        must_exist: Whether the path must exist on disk

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not value or not value.strip():
        return False, "Path cannot be empty"

    value = value.strip()

    # Expand user home directory
    expanded = os.path.expanduser(value)

    if must_exist and not os.path.exists(expanded):
        return False, f"Path does not exist: {expanded}"

    return True, None


def validate_token(value: str, min_length: int = 8) -> Tuple[bool, Optional[str]]:
    """
    Validate an API token.

    Args:
        value: Token string to validate
        min_length: Minimum token length

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not value:
        return False, "Token cannot be empty"

    if len(value) < min_length:
        return False, f"Token must be at least {min_length} characters"

    # Check for placeholder values
    placeholders = [
        "your_api_token_here",
        "your_auth_token_here",
        "your-teams-app-password",
        "your-teams-app-id",
        "<token>",
        "[token]",
    ]

    if value.lower() in [p.lower() for p in placeholders]:
        return False, "Please enter your actual token, not the placeholder"

    return True, None


def validate_project_key(value: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a Jira project key.

    Args:
        value: Project key to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not value or not value.strip():
        return False, "Project key cannot be empty"

    value = value.strip().upper()

    # Jira project keys: 2-10 uppercase letters and numbers, must start with letter
    if not re.match(r"^[A-Z][A-Z0-9]{1,9}$", value):
        return False, "Project key must be 2-10 characters, start with letter, uppercase only"

    return True, None


def validate_port(value: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a port number.

    Args:
        value: Port string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not value or not value.strip():
        return False, "Port cannot be empty"

    try:
        port = int(value.strip())
        if port < 1 or port > 65535:
            return False, "Port must be between 1 and 65535"
        if port < 1024:
            return False, "Port below 1024 requires root privileges"
        return True, None
    except ValueError:
        return False, "Port must be a number"


def validate_percentage(value: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a percentage value (0-100).

    Args:
        value: Percentage string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not value or not value.strip():
        return False, "Percentage cannot be empty"

    try:
        pct = float(value.strip())
        if pct < 0 or pct > 100:
            return False, "Percentage must be between 0 and 100"
        return True, None
    except ValueError:
        return False, "Percentage must be a number"


def validate_positive_int(value: str, field_name: str = "Value") -> Tuple[bool, Optional[str]]:
    """
    Validate a positive integer.

    Args:
        value: Integer string to validate
        field_name: Name of the field for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not value or not value.strip():
        return False, f"{field_name} cannot be empty"

    try:
        num = int(value.strip())
        if num <= 0:
            return False, f"{field_name} must be a positive number"
        return True, None
    except ValueError:
        return False, f"{field_name} must be a number"


def validate_host(value: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a host address.

    Args:
        value: Host string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not value or not value.strip():
        return False, "Host cannot be empty"

    value = value.strip()

    # Allow localhost, 0.0.0.0, or IP/hostname
    valid_patterns = [
        r"^localhost$",
        r"^0\.0\.0\.0$",
        r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",  # IPv4
        r"^[a-zA-Z0-9][a-zA-Z0-9.-]*[a-zA-Z0-9]$",  # Hostname
    ]

    if not any(re.match(pattern, value) for pattern in valid_patterns):
        return False, "Invalid host format"

    return True, None
