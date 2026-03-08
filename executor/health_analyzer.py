"""
Health analyzer for browser execution metrics.

Analyzes collected metrics to determine health grade and detect issues.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from models import (
    BrowserMetrics,
    HealthAnalysis,
    HealthGrade,
    MemoryLeakDetection,
    CPUDetection,
)


logger = logging.getLogger(__name__)


class HealthAnalyzer:
    """
    Analyzes browser metrics to determine execution health.

    Detects:
    - Memory leaks (sawtooth patterns, continuous growth)
    - High CPU usage (bad JS loops, infinite recursion)
    - Network errors (4xx/5xx responses)
    - Console errors (uncaught exceptions)
    """

    def __init__(
        self,
        memory_leak_threshold_mb: float = 100,
        memory_leak_window_seconds: int = 60,
        cpu_warning_percent: float = 60,
        cpu_critical_percent: float = 80,
        cpu_idle_window_seconds: int = 5,
    ):
        """
        Initialize health analyzer.

        Args:
            memory_leak_threshold_mb: Memory growth threshold for leak detection
            memory_leak_window_seconds: Time window to analyze for leaks
            cpu_warning_percent: CPU usage threshold for WARNING grade
            cpu_critical_percent: CPU usage threshold for CRITICAL grade
            cpu_idle_window_seconds: Time window considered "idle" for CPU analysis
        """
        self.memory_leak_threshold_mb = memory_leak_threshold_mb
        self.memory_leak_window_seconds = memory_leak_window_seconds
        self.cpu_warning_percent = cpu_warning_percent
        self.cpu_critical_percent = cpu_critical_percent
        self.cpu_idle_window_seconds = cpu_idle_window_seconds

    def analyze(self, metrics: List[BrowserMetrics]) -> HealthAnalysis:
        """
        Analyze collected metrics and determine health grade.

        Args:
            metrics: List of browser metrics collected during execution

        Returns:
            HealthAnalysis with grade and detected issues
        """
        if not metrics:
            return HealthAnalysis(
                grade=HealthGrade.WARNING,
                issues=["No metrics collected - unable to analyze health"],
                warnings=["Health analysis requires monitoring sidecar"],
            )

        issues = []
        warnings = []
        metrics_summary = {}

        # Analyze memory
        memory_analysis = self._analyze_memory(metrics)
        metrics_summary["memory"] = memory_analysis.__dict__

        if memory_analysis.is_leaking:
            issues.append(str(memory_analysis))

        # Analyze CPU
        cpu_analysis = self._analyze_cpu(metrics)
        metrics_summary["cpu"] = cpu_analysis.__dict__

        if cpu_analysis.is_abnormal:
            issues.append(str(cpu_analysis))
        elif cpu_analysis.peak_percent > self.cpu_warning_percent:
            warnings.append(f"High CPU usage detected: peak {cpu_analysis.peak_percent:.1f}%")

        # Analyze network errors
        network_errors = self._analyze_network_errors(metrics)
        metrics_summary["network_errors"] = network_errors

        if network_errors > 0:
            issues.append(f"Network errors detected: {network_errors} requests failed (4xx/5xx)")

        # Analyze console errors
        console_errors, console_warnings = self._analyze_console_errors(metrics)
        metrics_summary["console_errors"] = console_errors
        metrics_summary["console_warnings"] = console_warnings

        if console_errors > 0:
            issues.append(f"Console errors detected: {console_errors} uncaught exceptions")

        if console_warnings > 0:
            warnings.append(f"Console warnings present: {console_warnings} warnings")

        # Determine overall grade
        grade = self._determine_grade(
            memory_leak=memory_analysis.is_leaking,
            cpu_abnormal=cpu_analysis.is_abnormal,
            network_errors=network_errors > 0,
            console_errors=console_errors > 0,
            has_warnings=len(warnings) > 0,
        )

        return HealthAnalysis(
            grade=grade,
            issues=issues,
            warnings=warnings,
            metrics_summary=metrics_summary,
        )

    def _analyze_memory(self, metrics: List[BrowserMetrics]) -> MemoryLeakDetection:
        """
        Analyze memory metrics for leak detection.

        Detects:
        - Sawtooth patterns (GC not freeing memory)
        - Linear growth (continuous memory increase)

        Args:
            metrics: List of browser metrics

        Returns:
            MemoryLeakDetection with analysis results
        """
        if len(metrics) < 2:
            return MemoryLeakDetection(
                is_leaking=False,
                growth_mb=0,
                window_seconds=0,
                pattern="insufficient_data",
            )

        # Extract memory values
        memory_values = [m.memory_heap_mb for m in metrics]
        timestamps = [m.timestamp for m in metrics]

        # Calculate time window
        time_window = (timestamps[-1] - timestamps[0]).total_seconds()
        memory_growth = memory_values[-1] - memory_values[0]

        # Detect pattern
        pattern = self._detect_memory_pattern(memory_values)

        # Determine if leaking
        is_leaking = False
        if pattern == "sawtooth" and memory_growth > self.memory_leak_threshold_mb:
            is_leaking = True
        elif pattern == "linear_growth" and memory_growth > self.memory_leak_threshold_mb:
            is_leaking = True

        return MemoryLeakDetection(
            is_leaking=is_leaking,
            growth_mb=memory_growth,
            window_seconds=int(time_window),
            pattern=pattern,
            samples=memory_values,
        )

    def _detect_memory_pattern(self, values: List[float]) -> str:
        """
        Detect memory allocation pattern.

        Args:
            values: List of memory samples

        Returns:
            Pattern name: "sawtooth", "linear_growth", "stable", or "fluctuating"
        """
        if len(values) < 3:
            return "insufficient_data"

        # Calculate trends
        initial_avg = sum(values[:len(values)//3]) / (len(values)//3)
        middle_avg = sum(values[len(values)//3:2*len(values)//3]) / (len(values)//3)
        final_avg = sum(values[2*len(values)//3:]) / (len(values) - 2*len(values)//3)

        # Check for sawtooth pattern (up and down cycles)
        # by counting local maxima and minima
        peaks = 0
        valleys = 0
        for i in range(1, len(values) - 1):
            if values[i] > values[i-1] and values[i] > values[i+1]:
                peaks += 1
            elif values[i] < values[i-1] and values[i] < values[i+1]:
                valleys += 1

        # Determine pattern
        if peaks >= 2 and valleys >= 2:
            return "sawtooth"
        elif final_avg > initial_avg * 1.5:
            return "linear_growth"
        elif final_avg < initial_avg * 1.1:
            return "stable"
        else:
            return "fluctuating"

    def _analyze_cpu(self, metrics: List[BrowserMetrics]) -> CPUDetection:
        """
        Analyze CPU usage for anomalies.

        Detects:
        - Sustained high CPU during idle periods
        - CPU spikes

        Args:
            metrics: List of browser metrics

        Returns:
            CPUDetection with analysis results
        """
        if not metrics:
            return CPUDetection(
                is_abnormal=False,
                peak_percent=0,
                average_percent=0,
            )

        cpu_values = [m.cpu_percent for m in metrics]
        peak_cpu = max(cpu_values)
        avg_cpu = sum(cpu_values) / len(cpu_values)

        # Detect high CPU during idle
        # (assuming last 5 seconds of test are "idle" - test finished)
        idle_samples = cpu_values[-min(50, len(cpu_values)):]  # Last ~5 seconds at 100ms intervals
        idle_high_cpu = sum(1 for v in idle_samples if v > self.cpu_critical_percent)
        idle_high_cpu_seconds = idle_high_cpu * 0.1  # Convert to seconds

        # Determine if abnormal
        is_abnormal = False
        if peak_cpu > self.cpu_critical_percent:
            is_abnormal = True
        elif avg_cpu > self.cpu_warning_percent:
            is_abnormal = True
        elif idle_high_cpu_seconds > self.cpu_idle_window_seconds:
            is_abnormal = True

        return CPUDetection(
            is_abnormal=is_abnormal,
            peak_percent=peak_cpu,
            average_percent=avg_cpu,
            idle_high_cpu_seconds=idle_high_cpu_seconds,
        )

    def _analyze_network_errors(self, metrics: List[BrowserMetrics]) -> int:
        """
        Count total network errors across all metrics.

        Args:
            metrics: List of browser metrics

        Returns:
            Total count of network errors
        """
        return sum(len(m.network_errors) for m in metrics)

    def _analyze_console_errors(self, metrics: List[BrowserMetrics]) -> tuple[int, int]:
        """
        Count console errors and warnings.

        Args:
            metrics: List of browser metrics

        Returns:
            Tuple of (error_count, warning_count)
        """
        errors = sum(len(m.console_errors) for m in metrics)
        warnings = sum(len(m.console_warnings) for m in metrics)
        return errors, warnings

    def _determine_grade(
        self,
        memory_leak: bool,
        cpu_abnormal: bool,
        network_errors: bool,
        console_errors: bool,
        has_warnings: bool,
    ) -> HealthGrade:
        """
        Determine overall health grade from individual checks.

        Args:
            memory_leak: Memory leak detected
            cpu_abnormal: Abnormal CPU usage
            network_errors: Network errors present
            console_errors: Console errors present
            has_warnings: Any warnings present

        Returns:
            HealthGrade enum value
        """
        # Critical issues
        if memory_leak or cpu_abnormal or network_errors or console_errors:
            return HealthGrade.CRITICAL

        # Warnings only
        if has_warnings:
            return HealthGrade.WARNING

        # All good
        return HealthGrade.HEALTHY
