"""
Unit tests for HealthAnalyzer.

Tests memory leak detection, CPU analysis, and health grading.
"""

import pytest
from datetime import datetime, timedelta

from executor.models import (
    BrowserMetrics,
    HealthGrade,
    HealthAnalysis,
    MemoryLeakDetection,
    CPUDetection,
)
from executor.health_analyzer import HealthAnalyzer


class TestHealthAnalyzer:
    """Test suite for HealthAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create HealthAnalyzer instance for testing."""
        return HealthAnalyzer(
            memory_leak_threshold_mb=100,
            memory_leak_window_seconds=60,
            cpu_warning_percent=60,
            cpu_critical_percent=80,
            cpu_idle_window_seconds=5,
        )

    @pytest.fixture
    def healthy_metrics(self):
        """Create healthy browser metrics."""
        base_time = datetime.utcnow()
        return [
            BrowserMetrics(
                timestamp=base_time + timedelta(seconds=i * 0.1),
                memory_heap_mb=200.0 + (i * 0.5),  # Small growth
                memory_total_mb=250.0 + (i * 0.5),
                cpu_percent=30.0 + (i * 0.1),
                network_errors=[],
                console_errors=[],
                console_warnings=[],
            )
            for i in range(100)  # 10 seconds of data
        ]

    @pytest.fixture
    def memory_leak_metrics(self):
        """Create metrics showing memory leak (sawtooth pattern)."""
        base_time = datetime.utcnow()
        metrics = []

        for i in range(100):
            # Sawtooth pattern: grow to 300, drop to 250, repeat
            cycle = i % 30
            if cycle < 20:
                memory = 250.0 + (cycle * 2.5)  # Grow to 300
            else:
                memory = 300.0 - ((cycle - 20) * 10)  # Drop to 250

            metrics.append(BrowserMetrics(
                timestamp=base_time + timedelta(seconds=i * 0.1),
                memory_heap_mb=memory,
                memory_total_mb=memory + 50,
                cpu_percent=40.0,
                network_errors=[],
                console_errors=[],
                console_warnings=[],
            ))

        return metrics

    @pytest.fixture
    def high_cpu_metrics(self):
        """Create metrics showing high CPU usage."""
        base_time = datetime.utcnow()
        return [
            BrowserMetrics(
                timestamp=base_time + timedelta(seconds=i * 0.1),
                memory_heap_mb=200.0,
                memory_total_mb=250.0,
                cpu_percent=85.0 if i < 50 else 90.0,  # High CPU
                network_errors=[],
                console_errors=[],
                console_warnings=[],
            )
            for i in range(100)
        ]

    @pytest.fixture
    def error_metrics(self):
        """Create metrics with network and console errors."""
        base_time = datetime.utcnow()

        network_error = {
            "timestamp": base_time.isoformat(),
            "url": "https://api.example.com/error",
            "status_code": 500,
            "method": "GET",
        }

        console_error = {
            "timestamp": base_time.isoformat(),
            "level": "error",
            "message": "Uncaught TypeError: Cannot read property",
        }

        return [
            BrowserMetrics(
                timestamp=base_time + timedelta(seconds=i * 0.1),
                memory_heap_mb=200.0,
                memory_total_mb=250.0,
                cpu_percent=30.0,
                network_errors=[network_error] if i == 50 else [],
                console_errors=[console_error] if i == 50 else [],
                console_warnings=[],
            )
            for i in range(100)
        ]

    def test_analyze_healthy_metrics(self, analyzer, healthy_metrics):
        """Test analysis of healthy metrics returns HEALTHY grade."""
        result = analyzer.analyze(healthy_metrics)

        assert isinstance(result, HealthAnalysis)
        assert result.grade == HealthGrade.HEALTHY
        assert len(result.issues) == 0
        assert result.metrics_summary["memory"]["is_leaking"] is False
        assert result.metrics_summary["cpu"]["is_abnormal"] is False

    def test_analyze_memory_leak(self, analyzer, memory_leak_metrics):
        """Test memory leak detection with sawtooth pattern."""
        result = analyzer.analyze(memory_leak_metrics)

        assert result.grade == HealthGrade.CRITICAL
        assert any("memory leak" in issue.lower() for issue in result.issues)
        assert result.metrics_summary["memory"]["is_leaking"] is True
        assert result.metrics_summary["memory"]["pattern"] in ["sawtooth", "linear_growth"]

    def test_analyze_high_cpu(self, analyzer, high_cpu_metrics):
        """Test high CPU detection."""
        result = analyzer.analyze(high_cpu_metrics)

        assert result.grade == HealthGrade.CRITICAL
        assert any("cpu" in issue.lower() for issue in result.issues)
        assert result.metrics_summary["cpu"]["is_abnormal"] is True
        assert result.metrics_summary["cpu"]["peak_percent"] >= 80

    def test_analyze_errors(self, analyzer, error_metrics):
        """Test network and console error detection."""
        result = analyzer.analyze(error_metrics)

        assert result.grade == HealthGrade.CRITICAL
        assert any("network" in issue.lower() for issue in result.issues)
        assert any("console" in issue.lower() for issue in result.issues)
        assert result.metrics_summary["network_errors"] > 0
        assert result.metrics_summary["console_errors"] > 0

    def test_detect_memory_pattern_sawtooth(self, analyzer):
        """Test sawtooth pattern detection."""
        # Create clear sawtooth pattern
        values = []
        for cycle in range(3):
            values.extend([200 + i for i in range(50)])  # Grow
            values.extend([250 - i for i in range(50)])  # Shrink

        pattern = analyzer._detect_memory_pattern(values)
        assert pattern == "sawtooth"

    def test_detect_memory_pattern_linear_growth(self, analyzer):
        """Test linear growth pattern detection."""
        values = [200 + i for i in range(100)]  # Steady growth
        pattern = analyzer._detect_memory_pattern(values)
        assert pattern == "linear_growth"

    def test_detect_memory_pattern_stable(self, analyzer):
        """Test stable memory pattern detection."""
        values = [200 + (i % 10) for i in range(100)]  # Small fluctuations
        pattern = analyzer._detect_memory_pattern(values)
        assert pattern == "stable"

    def test_analyze_empty_metrics(self, analyzer):
        """Test analysis with no metrics returns WARNING."""
        result = analyzer.analyze([])

        assert result.grade == HealthGrade.WARNING
        assert len(result.issues) > 0
        assert "No metrics collected" in result.issues[0]

    def test_analyze_insufficient_metrics(self, analyzer):
        """Test analysis with insufficient data points."""
        metrics = [
            BrowserMetrics(
                timestamp=datetime.utcnow(),
                memory_heap_mb=200.0,
                memory_total_mb=250.0,
                cpu_percent=30.0,
                network_errors=[],
                console_errors=[],
                console_warnings=[],
            )
        ]

        result = analyzer.analyze(metrics)

        # Should return some grade but indicate insufficient data
        assert isinstance(result, HealthAnalysis)

    def test_cpu_idle_detection(self, analyzer):
        """Test CPU usage during idle periods."""
        base_time = datetime.utcnow()

        # Normal CPU during test, high CPU during idle (last 5 seconds)
        metrics = [
            BrowserMetrics(
                timestamp=base_time + timedelta(seconds=i * 0.1),
                memory_heap_mb=200.0,
                memory_total_mb=250.0,
                cpu_percent=40.0 if i < 50 else 85.0,  # High during idle
                network_errors=[],
                console_errors=[],
                console_warnings=[],
            )
            for i in range(100)
        ]

        cpu_analysis = analyzer._analyze_cpu(metrics)

        assert cpu_analysis.is_abnormal is True
        assert cpu_analysis.idle_high_cpu_seconds > 0

    def test_determine_grade_healthy(self, analyzer):
        """Test grade determination for healthy metrics."""
        grade = analyzer._determine_grade(
            memory_leak=False,
            cpu_abnormal=False,
            network_errors=False,
            console_errors=False,
            has_warnings=False,
        )

        assert grade == HealthGrade.HEALTHY

    def test_determine_grade_warning(self, analyzer):
        """Test grade determination with warnings only."""
        grade = analyzer._determine_grade(
            memory_leak=False,
            cpu_abnormal=False,
            network_errors=False,
            console_errors=False,
            has_warnings=True,
        )

        assert grade == HealthGrade.WARNING

    def test_determine_grade_critical_memory_leak(self, analyzer):
        """Test grade determination with memory leak."""
        grade = analyzer._determine_grade(
            memory_leak=True,
            cpu_abnormal=False,
            network_errors=False,
            console_errors=False,
            has_warnings=False,
        )

        assert grade == HealthGrade.CRITICAL

    def test_determine_grade_critical_cpu(self, analyzer):
        """Test grade determination with high CPU."""
        grade = analyzer._determine_grade(
            memory_leak=False,
            cpu_abnormal=True,
            network_errors=False,
            console_errors=False,
            has_warnings=False,
        )

        assert grade == HealthGrade.CRITICAL

    def test_determine_grade_critical_network_errors(self, analyzer):
        """Test grade determination with network errors."""
        grade = analyzer._determine_grade(
            memory_leak=False,
            cpu_abnormal=False,
            network_errors=True,
            console_errors=False,
            has_warnings=False,
        )

        assert grade == HealthGrade.CRITICAL

    def test_memory_leak_detection_threshold(self, analyzer, healthy_metrics):
        """Test memory leak threshold is correctly applied."""
        # Growth is small (50MB), should not trigger leak
        result = analyzer.analyze(healthy_metrics)

        assert result.metrics_summary["memory"]["is_leaking"] is False

    def test_memory_leak_detection_above_threshold(self, analyzer):
        """Test memory leak is detected when growth exceeds threshold."""
        base_time = datetime.utcnow()

        # Growth exceeds 100MB threshold
        metrics = [
            BrowserMetrics(
                timestamp=base_time + timedelta(seconds=i * 0.1),
                memory_heap_mb=200.0 + (i * 1.5),  # 150MB growth
                memory_total_mb=250.0 + (i * 1.5),
                cpu_percent=30.0,
                network_errors=[],
                console_errors=[],
                console_warnings=[],
            )
            for i in range(100)
        ]

        result = analyzer.analyze(metrics)

        assert result.metrics_summary["memory"]["is_leaking"] is True
