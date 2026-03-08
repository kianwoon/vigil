"""
Prompt definitions for setup wizard.

Defines all interactive questions and configuration prompts.
"""

from typing import Any, Dict, List, Optional

try:
    import questionary
    from questionary import Choice
except ImportError:
    questionary = None
    Choice = None

from rich.console import Console

from .validators import (
    validate_email,
    validate_host,
    validate_jira_url,
    validate_path,
    validate_port,
    validate_positive_int,
    validate_project_key,
    validate_token,
    validate_url,
)

console = Console()

# Default values
DEFAULTS = {
    # Jira
    "JIRA_BASE_URL": "https://yourcompany.atlassian.net",
    "JIRA_PROJECT_KEY": "QA",
    # Services
    "SHARED_VOLUME_PATH": "~/vigil-shared",
    "EXECUTOR_HOST": "0.0.0.0",
    "EXECUTOR_PORT": "8001",
    "MONITOR_HOST": "0.0.0.0",
    "MONITOR_PORT": "8002",
    "JIRA_INTEGRATOR_HOST": "0.0.0.0",
    "JIRA_INTEGRATOR_PORT": "8003",
    "TEAMS_PORT": "8004",
    "EXECUTOR_LOG_LEVEL": "INFO",
    "MONITOR_LOG_LEVEL": "INFO",
    "MONITOR_SAMPLE_INTERVAL_MS": "100",
    # Health Thresholds
    "HEALTH_MEMORY_LEAK_THRESHOLD_MB": "100",
    "HEALTH_MEMORY_LEAK_WINDOW_SECONDS": "60",
    "HEALTH_CPU_WARNING_PERCENT": "60",
    "HEALTH_CPU_CRITICAL_PERCENT": "80",
    "HEALTH_CPU_IDLE_WINDOW_SECONDS": "5",
    # Execution
    "EXECUTION_TIMEOUT_SECONDS": "300",
    "BROWSER_HEADLESS": "true",
    # Docker
    "DOCKER_NETWORK": "vigil_network",
}


def select_services() -> List[str]:
    """Ask user which services to configure."""
    return questionary.checkbox(
        "Which services do you want to configure?",
        choices=[
            Choice("Jira Integration", value="jira", checked=True),
            Choice("MS Teams Bot", value="teams", checked=False),
            Choice("WhatsApp Notifications", value="whatsapp", checked=False),
            Choice("Custom Health Thresholds", value="health", checked=False),
            Choice("Advanced Settings", value="advanced", checked=False),
        ],
        instruction="(Use Space to select, Enter to confirm)",
    ).ask() or []


def configure_jira() -> Dict[str, str]:
    """Configure Jira integration."""
    console.print("\n[bold cyan]Jira Configuration[/bold cyan]")
    console.print("[dim]Configure connection to your Jira instance[/dim]\n")

    config = {}

    # Base URL
    base_url = questionary.text(
        "Jira Base URL:",
        default=DEFAULTS["JIRA_BASE_URL"],
        validate=lambda x: validate_jira_url(x)[0],
    ).ask()

    if base_url:
        config["JIRA_BASE_URL"] = base_url.strip().rstrip("/")

    # Email
    email = questionary.text(
        "Jira Email:",
        default="",
        validate=lambda x: validate_email(x)[0],
    ).ask()

    if email:
        config["JIRA_EMAIL"] = email.strip()

    # API Token (hidden input)
    api_token = questionary.password(
        "Jira API Token:",
        instruction="(Input hidden - get from https://id.atlassian.com/manage-profile/security/api-tokens)",
        validate=lambda x: validate_token(x, min_length=8)[0],
    ).ask()

    if api_token:
        config["JIRA_API_TOKEN"] = api_token

    # Project Key
    project_key = questionary.text(
        "Jira Project Key:",
        default=DEFAULTS["JIRA_PROJECT_KEY"],
        validate=lambda x: validate_project_key(x)[0],
    ).ask()

    if project_key:
        config["JIRA_PROJECT_KEY"] = project_key.strip().upper()

    return config


def configure_teams() -> Dict[str, str]:
    """Configure MS Teams Bot."""
    console.print("\n[bold cyan]MS Teams Bot Configuration[/bold cyan]")
    console.print("[dim]Configure Microsoft Teams integration[/dim]")
    console.print("[dim]Get these from Azure Portal > Azure Bot > Configuration[/dim]\n")

    config = {}

    # App ID
    app_id = questionary.text(
        "Teams App ID:",
        default="",
        instruction="(GUID from Azure Bot configuration)",
    ).ask()

    if app_id:
        config["TEAMS_APP_ID"] = app_id.strip()

    # App Password (hidden)
    app_password = questionary.password(
        "Teams App Password:",
        instruction="(Client secret from Azure Bot - only shown once when created)",
        validate=lambda x: len(x) >= 10 if x else True,
    ).ask()

    if app_password:
        config["TEAMS_APP_PASSWORD"] = app_password

    # Service URL
    service_url = questionary.text(
        "Teams Service URL:",
        default="http://localhost:8004",
        validate=lambda x: validate_url(x)[0],
    ).ask()

    if service_url:
        config["TEAMS_SERVICE_URL"] = service_url.strip()

    config["TEAMS_PORT"] = DEFAULTS["TEAMS_PORT"]

    return config


def configure_whatsapp() -> Dict[str, str]:
    """Configure WhatsApp notifications."""
    console.print("\n[bold cyan]WhatsApp Configuration[/bold cyan]")
    console.print("[dim]Configure WhatsApp webhook for notifications[/dim]\n")

    config = {}

    # Webhook URL
    webhook_url = questionary.text(
        "WhatsApp Webhook URL:",
        default="",
        validate=lambda x: validate_url(x)[0] if x else True,
    ).ask()

    if webhook_url:
        config["WHATSAPP_WEBHOOK_URL"] = webhook_url.strip()

    # Auth Token
    auth_token = questionary.password(
        "WhatsApp Auth Token:",
        instruction="(Optional - leave empty if not required)",
    ).ask()

    if auth_token:
        config["WHATSAPP_AUTH_TOKEN"] = auth_token

    return config


def configure_health_thresholds() -> Dict[str, str]:
    """Configure custom health thresholds."""
    console.print("\n[bold cyan]Health Thresholds[/bold cyan]")
    console.print("[dim]Configure health monitoring thresholds[/dim]\n")

    config = {}

    # Memory leak threshold
    memory_threshold = questionary.text(
        "Memory Leak Threshold (MB):",
        default=DEFAULTS["HEALTH_MEMORY_LEAK_THRESHOLD_MB"],
        validate=lambda x: validate_positive_int(x, "Memory threshold")[0],
    ).ask()

    if memory_threshold:
        config["HEALTH_MEMORY_LEAK_THRESHOLD_MB"] = memory_threshold

    # Memory leak window
    memory_window = questionary.text(
        "Memory Leak Window (seconds):",
        default=DEFAULTS["HEALTH_MEMORY_LEAK_WINDOW_SECONDS"],
        validate=lambda x: validate_positive_int(x, "Memory window")[0],
    ).ask()

    if memory_window:
        config["HEALTH_MEMORY_LEAK_WINDOW_SECONDS"] = memory_window

    # CPU Warning
    cpu_warning = questionary.text(
        "CPU Warning Threshold (%):",
        default=DEFAULTS["HEALTH_CPU_WARNING_PERCENT"],
        validate=lambda x: 0 <= float(x) <= 100 if x else True,
    ).ask()

    if cpu_warning:
        config["HEALTH_CPU_WARNING_PERCENT"] = cpu_warning

    # CPU Critical
    cpu_critical = questionary.text(
        "CPU Critical Threshold (%):",
        default=DEFAULTS["HEALTH_CPU_CRITICAL_PERCENT"],
        validate=lambda x: 0 <= float(x) <= 100 if x else True,
    ).ask()

    if cpu_critical:
        config["HEALTH_CPU_CRITICAL_PERCENT"] = cpu_critical

    return config


def configure_advanced() -> Dict[str, str]:
    """Configure advanced settings."""
    console.print("\n[bold cyan]Advanced Settings[/bold cyan]")
    console.print("[dim]Configure service hosts, ports, and execution settings[/dim]\n")

    config = {}

    # Executor
    console.print("[dim]Executor Service:[/dim]")
    executor_host = questionary.text(
        "Executor Host:",
        default=DEFAULTS["EXECUTOR_HOST"],
        validate=lambda x: validate_host(x)[0],
    ).ask()
    if executor_host:
        config["EXECUTOR_HOST"] = executor_host

    executor_port = questionary.text(
        "Executor Port:",
        default=DEFAULTS["EXECUTOR_PORT"],
        validate=lambda x: validate_port(x)[0],
    ).ask()
    if executor_port:
        config["EXECUTOR_PORT"] = executor_port

    # Monitor
    console.print("\n[dim]Monitor Service:[/dim]")
    monitor_host = questionary.text(
        "Monitor Host:",
        default=DEFAULTS["MONITOR_HOST"],
        validate=lambda x: validate_host(x)[0],
    ).ask()
    if monitor_host:
        config["MONITOR_HOST"] = monitor_host

    monitor_port = questionary.text(
        "Monitor Port:",
        default=DEFAULTS["MONITOR_PORT"],
        validate=lambda x: validate_port(x)[0],
    ).ask()
    if monitor_port:
        config["MONITOR_PORT"] = monitor_port

    # Execution settings
    console.print("\n[dim]Execution Settings:[/dim]")
    timeout = questionary.text(
        "Execution Timeout (seconds):",
        default=DEFAULTS["EXECUTION_TIMEOUT_SECONDS"],
        validate=lambda x: validate_positive_int(x, "Timeout")[0],
    ).ask()
    if timeout:
        config["EXECUTION_TIMEOUT_SECONDS"] = timeout

    headless = questionary.confirm(
        "Run browser in headless mode?",
        default=True,
    ).ask()
    config["BROWSER_HEADLESS"] = "true" if headless else "false"

    return config


def configure_shared_volume() -> Dict[str, str]:
    """Configure shared volume path."""
    console.print("\n[bold cyan]Shared Volume[/bold cyan]")
    console.print("[dim]Path for sharing test scripts and results with Role 1[/dim]\n")

    config = {}

    volume_path = questionary.text(
        "Shared Volume Path:",
        default=DEFAULTS["SHARED_VOLUME_PATH"],
        instruction="(Will be created if it doesn't exist)",
    ).ask()

    if volume_path:
        config["SHARED_VOLUME_PATH"] = volume_path.strip()
        # Derived paths
        config["SHARED_SCRIPTS_DIR"] = f"${{SHARED_VOLUME_PATH}}/egress"
        config["SHARED_RESULTS_DIR"] = f"${{SHARED_VOLUME_PATH}}/results"

    return config


def confirm_configuration(config: Dict[str, str]) -> bool:
    """Show configuration summary and ask for confirmation."""
    console.print("\n[bold]Configuration Summary[/bold]\n")

    # Group by service
    jira_vars = ["JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_PROJECT_KEY", "JIRA_API_TOKEN"]
    teams_vars = ["TEAMS_APP_ID", "TEAMS_SERVICE_URL", "TEAMS_PORT"]
    whatsapp_vars = ["WHATSAPP_WEBHOOK_URL", "WHATSAPP_AUTH_TOKEN"]
    health_vars = [
        "HEALTH_MEMORY_LEAK_THRESHOLD_MB",
        "HEALTH_CPU_WARNING_PERCENT",
        "HEALTH_CPU_CRITICAL_PERCENT",
    ]
    volume_vars = ["SHARED_VOLUME_PATH"]

    def show_group(name: str, vars_list: List[str]):
        group_config = {k: v for k, v in config.items() if k in vars_list}
        if group_config:
            console.print(f"[cyan]{name}:[/cyan]")
            for key, value in group_config.items():
                # Mask sensitive values
                if "TOKEN" in key or "PASSWORD" in key or "SECRET" in key:
                    display_value = "*" * 8
                else:
                    display_value = value
                console.print(f"  {key}={display_value}")
            console.print()

    show_group("Jira", jira_vars)
    show_group("Teams", teams_vars)
    show_group("WhatsApp", whatsapp_vars)
    show_group("Health Thresholds", health_vars)
    show_group("Shared Volume", volume_vars)

    return questionary.confirm(
        "Save this configuration?",
        default=True,
    ).ask()


def ask_test_connections() -> bool:
    """Ask if user wants to test connections."""
    return questionary.confirm(
        "Test connections before saving?",
        default=True,
        instruction="(Recommended - verifies your credentials work)",
    ).ask()
