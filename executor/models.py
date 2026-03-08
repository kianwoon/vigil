"""
Core data models for NanoClaw Role 2 (Intelligent Test Executor).

Shared models used across executor, monitor, and jira_integrator services.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import uuid4


class ExecutionStatus(str, Enum):
    """Current status of test execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class HealthGrade(str, Enum):
    """Health grade based on execution metrics."""
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class TestResult(str, Enum):
    """Test execution result."""
    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


@dataclass
class TestCase:
    """Test case metadata."""
    name: str
    jira_ticket: str
    author: Optional[str] = None
    priority: Optional[str] = None
    scope: Optional[str] = None
    specifications: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate required fields."""
        if not self.name:
            raise ValueError("Test case name is required")
        if not self.jira_ticket:
            raise ValueError("Jira ticket ID is required")


@dataclass
class ExecutionRequest:
    """Request to execute a test script."""
    job_id: str
    jira_ticket: str
    script_path: str
    timeout_seconds: int = 300
    browser_headless: bool = True
    trace_enabled: bool = True

    def __post_init__(self):
        """Validate execution request."""
        if not self.job_id:
            raise ValueError("Job ID is required")
        if not self.jira_ticket:
            raise ValueError("Jira ticket is required")
        if not self.script_path:
            raise ValueError("Script path is required")


@dataclass
class BrowserMetrics:
    """Real-time browser metrics from monitoring sidecar."""
    timestamp: datetime
    memory_heap_mb: float
    memory_total_mb: float
    cpu_percent: float
    network_errors: List[Dict[str, Any]] = field(default_factory=list)
    console_errors: List[Dict[str, Any]] = field(default_factory=list)
    console_warnings: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "memory_heap_mb": self.memory_heap_mb,
            "memory_total_mb": self.memory_total_mb,
            "cpu_percent": self.cpu_percent,
            "network_errors_count": len(self.network_errors),
            "console_errors_count": len(self.console_errors),
            "console_warnings_count": len(self.console_warnings),
        }


@dataclass
class HealthAnalysis:
    """Health analysis results."""
    grade: HealthGrade
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metrics_summary: Dict[str, Any] = field(default_factory=dict)

    def is_healthy(self) -> bool:
        """Check if execution is healthy."""
        return self.grade == HealthGrade.HEALTHY

    def has_warnings(self) -> bool:
        """Check if execution has warnings."""
        return self.grade == HealthGrade.WARNING

    def is_critical(self) -> bool:
        """Check if execution is critical."""
        return self.grade == HealthGrade.CRITICAL


@dataclass
class ExecutionResult:
    """Complete execution result with health analysis."""
    execution_id: str
    job_id: str
    jira_ticket: str
    status: ExecutionStatus
    test_result: TestResult
    health_analysis: HealthAnalysis
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    error_message: Optional[str] = None

    # Metrics collected during execution
    peak_memory_mb: float = 0.0
    peak_cpu_percent: float = 0.0
    total_network_errors: int = 0
    total_console_errors: int = 0
    total_console_warnings: int = 0

    # Evidence package paths
    trace_path: Optional[str] = None
    logs_path: Optional[str] = None
    metrics_path: Optional[str] = None
    screenshot_path: Optional[str] = None

    def __post_init__(self):
        """Generate execution ID if not provided."""
        if not self.execution_id:
            self.execution_id = f"exec-{uuid4().hex[:12]}"

    def to_summary_dict(self) -> Dict[str, Any]:
        """Convert to summary dictionary for API responses."""
        return {
            "execution_id": self.execution_id,
            "job_id": self.job_id,
            "jira_ticket": self.jira_ticket,
            "status": self.status.value,
            "test_result": self.test_result.value,
            "health_grade": self.health_analysis.grade.value,
            "duration_seconds": self.duration_seconds,
            "metrics": {
                "peak_memory_mb": self.peak_memory_mb,
                "peak_cpu_percent": self.peak_cpu_percent,
                "network_errors": self.total_network_errors,
                "console_errors": self.total_console_errors,
                "console_warnings": self.total_console_warnings,
            },
            "evidence_package": {
                "trace": self.trace_path,
                "logs": self.logs_path,
                "metrics": self.metrics_path,
                "screenshot": self.screenshot_path,
            },
            "error": self.error_message,
        }


@dataclass
class EvidencePackage:
    """Evidence package for Jira attachment."""
    execution_id: str
    job_id: str
    jira_ticket: str
    test_name: str

    # File paths
    metrics_csv_path: str
    logs_txt_path: str
    trace_zip_path: str
    health_report_json_path: str
    screenshot_dir: Optional[str] = None

    # Generated files
    created_at: datetime = field(default_factory=datetime.utcnow)

    def get_attachment_paths(self) -> List[str]:
        """Get list of all attachment file paths."""
        attachments = [
            self.metrics_csv_path,
            self.logs_txt_path,
            self.trace_zip_path,
            self.health_report_json_path,
        ]
        if self.screenshot_dir:
            attachments.append(self.screenshot_dir)
        return attachments

    def get_attachment_descriptions(self) -> Dict[str, str]:
        """Get descriptions for each attachment."""
        return {
            "metrics_csv": "Time-series health metrics (memory, CPU, network)",
            "logs_txt": "Merged terminal output and browser console logs",
            "trace_zip": "Playwright trace viewer file (open in chrome://tracing)",
            "health_report": "Detailed health analysis and issue detection",
            "screenshots": "Failure screenshots (if any)",
        }


@dataclass
class JiraComment:
    """Formatted Jira comment."""
    ticket_id: str
    status_emoji: str
    status: str
    health_grade_emoji: str
    health_grade: str
    execution_time: str
    timestamp: str
    metrics_table: str
    issues_list: str
    evidence_description: str
    trace_view_instructions: str

    def to_markdown(self) -> str:
        """Convert to markdown format for Jira comment."""
        return f"""---
## NanoClaw Test Execution Report

**Status:** {self.status_emoji} {self.status}
**Health Grade:** {self.health_grade_emoji} {self.health_grade}
**Execution Time:** {self.execution_time}
**Timestamp:** {self.timestamp}

### Health Metrics

{self.metrics_table}

### Issues Detected

{self.issues_list}

### Evidence Package

{self.evidence_description}

**View Trace:** {self.trace_view_instructions}
---
"""


@dataclass
class MemoryLeakDetection:
    """Memory leak analysis result."""
    is_leaking: bool
    growth_mb: float
    window_seconds: int
    pattern: Optional[str] = None  # "sawtooth", "linear_growth", "stable"
    samples: List[float] = field(default_factory=list)

    def __str__(self) -> str:
        """String representation."""
        if self.is_leaking:
            return f"Memory leak detected: +{self.growth_mb:.1f}MB over {self.window_seconds}s ({self.pattern})"
        return f"Memory stable: {self.growth_mb:.1f}MB over {self.window_seconds}s"


@dataclass
class CPUDetection:
    """CPU usage analysis result."""
    is_abnormal: bool
    peak_percent: float
    average_percent: float
    idle_high_cpu_seconds: float = 0.0

    def __str__(self) -> str:
        """String representation."""
        if self.is_abnormal:
            return f"High CPU detected: peak {self peak_percent:.1f}%, avg {self.average_percent:.1f}%, {self.idle_high_cpu_seconds:.1f}s at >80% during idle"
        return f"CPU normal: peak {self.peak_percent:.1f}%, avg {self.average_percent:.1f}%"


@dataclass
class NetworkError:
    """Network error detected during execution."""
    timestamp: datetime
    url: str
    status_code: int
    method: str
    error_type: str  # "4xx", "5xx", "timeout", "network_error"
    response_time_ms: Optional[float] = None


@dataclass
class ConsoleError:
    """Console error/warning detected during execution."""
    timestamp: datetime
    level: str  # "error", "warning", "info"
    message: str
    source_url: Optional[str] = None
    line_number: Optional[int] = None
    stack_trace: Optional[str] = None
