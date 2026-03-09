"""
Integration tests for Vigil Executor.

Tests end-to-end workflows across components.
"""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta

from executor.models import (
    BrowserMetrics,
    ExecutionRequest,
    ExecutionStatus,
    TestResult,
    HealthGrade,
)
from executor.health_analyzer import HealthAnalyzer
from executor.whatsapp_interface import (
    WhatsAppCommandProcessor,
    WhatsAppMessage,
)


class TestExecutionFlow:
    """Integration tests for execution flow."""

    @pytest.fixture
    def temp_dirs(self, tmp_path):
        """Create temporary directories for testing."""
        scripts_dir = tmp_path / "scripts"
        results_dir = tmp_path / "results"
        scripts_dir.mkdir()
        results_dir.mkdir()
        return scripts_dir, results_dir

    @pytest.fixture
    def sample_script(self, temp_dirs):
        """Create sample test script."""
        scripts_dir, _ = temp_dirs
        script_path = scripts_dir / "test_example.py"

        script_content = '''
"""
Test: Login Test
Jira Ticket: QA-123
Author: Test User
"""

import pytest
from playwright.async_api import async_playwright

@pytest.mark.asyncio
async def test_login():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://example.com")
        assert await page.title() != ""
        await browser.close()
'''

        script_path.write_text(script_content)
        return script_path

    def test_health_analysis_with_realistic_metrics(self):
        """Test health analysis with realistic metric sequence."""
        # Simulate a test run with realistic patterns
        base_time = datetime.utcnow()
        metrics = []

        for i in range(100):
            # Realistic pattern: CPU spikes during actions, memory grows slightly
            if i < 20:
                cpu = 40.0  # Initial setup
            elif i < 50:
                cpu = 70.0  # Test execution
            else:
                cpu = 35.0  # Cleanup and idle

            memory = 200.0 + (i * 0.3)  # Slight growth (30MB over 10s)

            metrics.append(BrowserMetrics(
                timestamp=base_time + timedelta(seconds=i * 0.1),
                memory_heap_mb=memory,
                memory_total_mb=memory + 50,
                cpu_percent=cpu,
                network_errors=[],
                console_errors=[],
                console_warnings=[],
            ))

        analyzer = HealthAnalyzer()
        result = analyzer.analyze(metrics)

        # Should be healthy - no memory leak, CPU normal
        assert result.grade in [HealthGrade.HEALTHY, HealthGrade.WARNING]
        assert not result.metrics_summary["memory"]["is_leaking"]

    def test_health_analysis_detects_real_leak(self):
        """Test memory leak detection with realistic leak pattern."""
        base_time = datetime.utcnow()
        metrics = []

        for i in range(100):
            # Simulate memory leak: growth exceeds 100MB without GC reclaiming
            memory = 200.0 + (i * 1.2)  # 120MB growth

            metrics.append(BrowserMetrics(
                timestamp=base_time + timedelta(seconds=i * 0.1),
                memory_heap_mb=memory,
                memory_total_mb=memory + 50,
                cpu_percent=45.0,
                network_errors=[],
                console_errors=[],
                console_warnings=[],
            ))

        analyzer = HealthAnalyzer(memory_leak_threshold_mb=100)
        result = analyzer.analyze(metrics)

        # Should detect leak
        assert result.grade == HealthGrade.CRITICAL
        assert result.metrics_summary["memory"]["is_leaking"] is True

    def test_whatsapp_command_flow(self):
        """Test full WhatsApp command flow."""
        processor = WhatsAppCommandProcessor(
            executor_api_url="http://localhost:8001",
            jira_api_url="http://localhost:8003",
        )

        # User sends run command
        message = WhatsAppMessage(
            phone_number="+1234567890",
            message_body="/run integration-test",
        )

        response = processor._handle_run_command(
            recipient=message.phone_number,
            job_id="integration-test",
        )

        # Verify execution was created
        assert "integration-test" in processor.active_executions
        assert processor.active_executions["integration-test"]["status"] == "running"

        # User checks status
        status_response = processor._handle_status_command(
            recipient=message.phone_number,
            job_id="integration-test",
        )

        assert "integration-test" in status_response.message
        assert "RUNNING" in status_response.message

        # Simulate completion
        processor.active_executions["integration-test"]["status"] = "completed"
        processor.active_executions["integration-test"]["jira_ticket"] = "QA-999"

        # User gets results
        results_response = processor._handle_results_command(
            recipient=message.phone_number,
            job_id="integration-test",
        )

        assert "QA-999" in results_response.message

    def test_metrics_buffer_integration(self):
        """Test metrics are properly buffered during execution simulation."""
        base_time = datetime.utcnow()
        metrics_buffer = []

        # Simulate collecting metrics during test execution
        for i in range(50):
            metric = BrowserMetrics(
                timestamp=base_time + timedelta(seconds=i * 0.1),
                memory_heap_mb=200.0 + i,
                memory_total_mb=250.0 + i,
                cpu_percent=30.0 + (i % 20),
                network_errors=[],
                console_errors=[],
                console_warnings=[],
            )
            metrics_buffer.append(metric)

        # Analyze the buffered metrics
        analyzer = HealthAnalyzer()
        result = analyzer.analyze(metrics_buffer)

        # Verify analysis completed
        assert isinstance(result, HealthAnalysis)
        assert result.metrics_summary is not None
        assert "memory" in result.metrics_summary
        assert "cpu" in result.metrics_summary

    def test_error_scenario_network_failure(self):
        """Test health grading with network failures."""
        base_time = datetime.utcnow()
        metrics = []

        for i in range(50):
            # Add network error at i=25
            network_errors = []
            if i == 25:
                network_errors.append({
                    "timestamp": base_time.isoformat(),
                    "url": "https://api.example.com/endpoint",
                    "status_code": 500,
                    "method": "POST",
                })

            metrics.append(BrowserMetrics(
                timestamp=base_time + timedelta(seconds=i * 0.1),
                memory_heap_mb=200.0,
                memory_total_mb=250.0,
                cpu_percent=35.0,
                network_errors=network_errors,
                console_errors=[],
                console_warnings=[],
            ))

        analyzer = HealthAnalyzer()
        result = analyzer.analyze(metrics)

        # Should be critical due to network error
        assert result.grade == HealthGrade.CRITICAL
        assert any("network" in issue.lower() for issue in result.issues)

    def test_error_scenario_console_exception(self):
        """Test health grading with console exceptions."""
        base_time = datetime.utcnow()
        metrics = []

        for i in range(50):
            # Add console error at i=30
            console_errors = []
            if i == 30:
                console_errors.append({
                    "timestamp": base_time.isoformat(),
                    "level": "error",
                    "message": "Uncaught ReferenceError: variable not defined",
                    "source_url": "https://example.com/app.js",
                    "line_number": 123,
                })

            metrics.append(BrowserMetrics(
                timestamp=base_time + timedelta(seconds=i * 0.1),
                memory_heap_mb=200.0,
                memory_total_mb=250.0,
                cpu_percent=35.0,
                network_errors=[],
                console_errors=console_errors,
                console_warnings=[],
            ))

        analyzer = HealthAnalyzer()
        result = analyzer.analyze(metrics)

        # Should be critical due to console error
        assert result.grade == HealthGrade.CRITICAL
        assert any("console" in issue.lower() for issue in result.issues)

    def test_warning_scenario_minor_issues(self):
        """Test health grading with warnings only."""
        base_time = datetime.utcnow()
        metrics = []

        for i in range(50):
            # Add console warnings (not errors)
            console_warnings = [
                {
                    "timestamp": base_time.isoformat(),
                    "level": "warning",
                    "message": f"Deprecation warning {i}",
                }
                for _ in range(3)
            ]

            metrics.append(BrowserMetrics(
                timestamp=base_time + timedelta(seconds=i * 0.1),
                memory_heap_mb=200.0 + (i * 0.5),  # 25MB growth
                memory_total_mb=250.0 + (i * 0.5),
                cpu_percent=55.0,  # Slightly elevated but below warning threshold
                network_errors=[],
                console_errors=[],
                console_warnings=console_warnings,
            ))

        analyzer = HealthAnalyzer(cpu_warning_percent=60, cpu_critical_percent=80)
        result = analyzer.analyze(metrics)

        # Should be warning (not critical)
        assert result.grade == HealthGrade.WARNING
        assert len(result.warnings) > 0

    def test_multi_user_whatsapp_scenarios(self):
        """Test WhatsApp processor handling multiple users."""
        processor = WhatsAppCommandProcessor(
            executor_api_url="http://localhost:8001",
            jira_api_url="http://localhost:8003",
        )

        # User 1 runs test
        processor.active_executions["user1-test"] = {
            "status": "running",
            "execution_id": "exec-1",
            "started_at": datetime.utcnow().isoformat(),
            "phone_number": "+1111111111",
        }

        # User 2 runs different test
        processor.active_executions["user2-test"] = {
            "status": "completed",
            "execution_id": "exec-2",
            "started_at": datetime.utcnow().isoformat(),
            "phone_number": "+2222222222",
            "jira_ticket": "QA-456",
        }

        # User 1 lists executions - should see both
        list_response = processor._handle_list_command("+1111111111")

        assert "user1-test" in list_response.message
        assert "user2-test" in list_response.message

        # User 1 checks their own status
        status_response = processor._handle_status_command(
            recipient="+1111111111",
            job_id="user1-test",
        )

        assert "user1-test" in status_response.message

        # User 2 gets their results
        results_response = processor._handle_results_command(
            recipient="+2222222222",
            job_id="user2-test",
        )

        assert "QA-456" in results_response.message


class TestHealthAnalysisScenarios:
    """Integration tests for realistic health analysis scenarios."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer with production-like thresholds."""
        return HealthAnalyzer(
            memory_leak_threshold_mb=100,
            memory_leak_window_seconds=60,
            cpu_warning_percent=60,
            cpu_critical_percent=80,
            cpu_idle_window_seconds=5,
        )

    def test_scenario_healthy_test_execution(self, analyzer):
        """Test scenario: Healthy test with no issues."""
        base_time = datetime.utcnow()
        metrics = []

        for i in range(100):
            metrics.append(BrowserMetrics(
                timestamp=base_time + timedelta(seconds=i * 0.1),
                memory_heap_mb=200.0 + (i * 0.2),  # 20MB growth
                memory_total_mb=250.0 + (i * 0.2),
                cpu_percent=35.0 + (i % 15),  # Normal fluctuation
                network_errors=[],
                console_errors=[],
                console_warnings=[],
            ))

        result = analyzer.analyze(metrics)

        assert result.grade == HealthGrade.HEALTHY
        assert len(result.issues) == 0

    def test_scenario_slow_api_responses(self, analyzer):
        """Test scenario: Test passes but API is slow."""
        base_time = datetime.utcnow()
        metrics = []

        for i in range(100):
            # CPU elevated due to waiting for slow API
            cpu = 65.0 if 20 < i < 60 else 35.0

            metrics.append(BrowserMetrics(
                timestamp=base_time + timedelta(seconds=i * 0.1),
                memory_heap_mb=200.0 + (i * 0.3),  # 30MB growth
                memory_total_mb=250.0 + (i * 0.3),
                cpu_percent=cpu,
                network_errors=[],
                console_errors=[],
                console_warnings=[],
            ))

        result = analyzer.analyze(metrics)

        # Should be WARNING (elevated CPU but below critical)
        assert result.grade == HealthGrade.WARNING
        assert any("cpu" in warning.lower() or "elevated" in warning.lower()
                   for warning in result.warnings)

    def test_scenario_memory_leak_during_test(self, analyzer):
        """Test scenario: Memory leak causes browser to become unresponsive."""
        base_time = datetime.utcnow()
        metrics = []

        for i in range(100):
            # Memory grows continuously without GC reclaiming
            memory = 200.0 + (i * 1.5)  # 150MB growth

            metrics.append(BrowserMetrics(
                timestamp=base_time + timedelta(seconds=i * 0.1),
                memory_heap_mb=memory,
                memory_total_mb=memory + 50,
                cpu_percent=90.0 if i > 80 else 40.0,  # CPU spikes near end
                network_errors=[],
                console_errors=[],
                console_warnings=[],
            ))

        result = analyzer.analyze(metrics)

        # Should be CRITICAL
        assert result.grade == HealthGrade.CRITICAL
        assert result.metrics_summary["memory"]["is_leaking"] is True
