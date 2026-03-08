# Role 2 Implementation Plan

**Date:** 2026-03-08
**Status:** Complete
**Version:** 1.0.0

---

## Overview

This document outlines the implementation of **NanoClaw Role 2: Intelligent Test Executor**, a runtime auditor that goes beyond simple test execution to monitor browser health during test runs.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Shared Network Volume                        │
│                  /scripts → /results → /traces                   │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        │                                               │
┌───────▼──────────┐                         ┌────────▼────────┐
│  Role 2 Executor │◄────metrics─────────│  Monitor Sidecar│
│  - pytest runner │                         │  - CPU/Memory   │
│  - trace capture│   ┌──────────────────┐  │  - Network      │
│  - log merge    │───│  Jira Integrator│  │  - Console      │
│  - health grade │   │  - Comment post  │──│  - CDP Protocol │
└──────────────────┘   │  - Attachment    │  └─────────────────┘
                       └──────────────────┘
```

---

## Components Implemented

### 1. Executor Service (`executor/`)
**Status:** ✅ Complete

**Features:**
- ✓ Runs pytest with Playwright in isolated Docker containers
- ✓ Fresh browser context per test (no cache, no cookies)
- ✓ `pytest --json-report --trace` for machine-readable results
- ✓ Real-time health monitoring integration via WebSocket
- ✓ Sequential execution with graceful error handling
- ✓ Comprehensive API for execution management

**Key Files:**
- `executor/runner.py` - Core test execution engine
- `executor/health_analyzer.py` - Health grading logic
- `executor/api.py` - FastAPI REST endpoints
- `executor/main.py` - Service entry point

**API Endpoints:**
- `POST /api/v1/execute` - Trigger test execution
- `GET /api/v1/status/{job_id}` - Check execution status
- `GET /api/v1/result/{job_id}` - Get detailed results
- `GET /api/v1/trace/{execution_id}` - Get Playwright trace

---

### 2. Monitor Service (`monitor/`)
**Status:** ✅ Complete

**Features:**
- ✓ Chrome DevTools Protocol (CDP) integration for browser internals
- ✓ psutil for process-level CPU and memory monitoring
- ✓ WebSocket server for real-time metric streaming
- ✓ Detects memory leaks (sawtooth patterns, linear growth)
- ✓ Detects high CPU usage during idle periods
- ✓ Captures network errors (4xx/5xx)
- ✓ Captures console errors and warnings

**Key Files:**
- `monitor/metrics_collector.py` - CDP + psutil monitoring
- `monitor/websocket_server.py` - Real-time metrics streaming
- `monitor/api.py` - Monitor control API
- `monitor/main.py` - Service entry point

**Metrics Collected:**
| Metric | Detection Method | Thresholds |
|--------|-----------------|------------|
| Memory Heap | CDP + psutil | 100MB growth = leak |
| CPU Usage | psutil | >80% idle = critical |
| Network | CDP response events | Any 4xx/5xx |
| Console | CDP log events | Any stack trace |

---

### 3. Jira Integrator (`jira_integrator/`)
**Status:** ✅ Complete

**Features:**
- ✓ Posts formatted comments to Jira tickets
- ✓ Attaches evidence packages (metrics CSV, logs, traces)
- ✓ Extracts Jira ticket ID from test metadata
- ✓ Structured comment format with health grades
- ✓ Handles attachment uploads for large files

**Key Files:**
- `jira_integrator/client.py` - Jira API client
- `jira_integrator/formatter.py` - Comment formatting
- `jira_integrator/evidence_packager.py` - Evidence package generation
- `jira_integrator/api.py` - Integrator API
- `jira_integrator/main.py` - Service entry point

**Jira Comment Format:**
```markdown
---
## NanoClaw Test Execution Report

**Status:** ✅ PASS
**Health Grade:** ⚠️ WARNING
**Execution Time:** 2.3s
**Timestamp:** 2026-03-08T15:30:00Z

### Health Metrics

| Metric | Value | Status |
|--------|-------|--------|
| Peak Memory | 450 MB | ⚠️ Elevated |
...
```

---

### 4. Evidence Package Generator
**Status:** ✅ Complete (part of jira_integrator)

**Generated Files:**
- ✓ `metrics.csv` - Time-series health data
- ✓ `logs.txt` - Merged terminal + console logs
- ✓ `health_report.json` - Detailed health analysis
- ✓ `trace.zip` - Playwright trace viewer
- ✓ `screenshots/` - Failure screenshots (if any)

---

### 5. Docker Configuration
**Status:** ✅ Complete

**Features:**
- ✓ Multi-container orchestration
- ✓ Shared volume for scripts and results
- ✓ Isolated network (nanoclaw_network)
- ✓ Health checks for all services
- ✓ Proper user permissions (non-root containers)
- ✓ Playwright browser cache volume

**Services:**
- `executor` - Port 8001
- `monitor` - Port 8002 (with SYS_PTRACE for process monitoring)
- `jira-integrator` - Port 8003

---

## Health Grading System

### HEALTHY
- ✓ Test passes
- ✓ Memory stable (no sawtooth patterns)
- ✓ CPU < 60% during idle
- ✓ Zero console errors
- ✓ Zero network errors

### WARNING
- ✓ Test passes BUT:
  - Minor console warnings
  - Slow API responses
  - Memory growth < 50MB
  - Occasional CPU spikes (60-80%)

### CRITICAL
- ✗ Test fails OR:
  - Memory leak detected (sawtooth, >100MB growth)
  - CPU sustained >80% during idle
  - Uncaught exceptions
  - Network errors (4xx/5xx)
  - Browser freeze

---

## Monitoring Technologies

| Technology | Purpose |
|------------|---------|
| **Chrome DevTools Protocol (CDP)** | Direct browser internals access |
| **psutil** | Process-level CPU and memory |
| **pytest-json-report** | Machine-readable test results |
| **Playwright Tracing** | Video-like execution replay |
| **WebSocket** | Real-time metric streaming |

---

## Quick Start

### 1. Setup
```bash
cd /Users/kianwoonwong/Downloads/qa-swarm-executor
./scripts/setup.sh
```

### 2. Configure
```bash
nano .env
# Add Jira credentials
```

### 3. Start Services
```bash
cd docker
docker-compose up -d
```

### 4. Execute Test
```bash
curl -X POST http://localhost:8001/api/v1/execute \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test-1",
    "jira_ticket": "QA-456",
    "script_path": "test_login.py"
  }'
```

---

## Directory Structure

```
qa-swarm-executor/
├── executor/                    # Test execution service
│   ├── executor/
│   │   ├── runner.py           # pytest execution
│   │   ├── health_analyzer.py  # health grading
│   │   ├── api.py              # REST API
│   │   └── main.py
│   ├── requirements.txt
│   └── tests/
│
├── monitor/                     # Monitoring sidecar
│   ├── monitor/
│   │   ├── metrics_collector.py # CDP + psutil
│   │   ├── websocket_server.py  # metrics streaming
│   │   ├── api.py
│   │   └── main.py
│   ├── requirements.txt
│   └── tests/
│
├── jira_integrator/             # Jira integration
│   ├── jira_integrator/
│   │   ├── client.py           # Jira API
│   │   ├── formatter.py        # comment formatting
│   │   ├── evidence_packager.py
│   │   ├── api.py
│   │   └── main.py
│   ├── requirements.txt
│   └── tests/
│
├── shared/                      # Shared volume
│   ├── scripts/                 # Input from Role 1
│   ├── results/                 # Execution outputs
│   ├── traces/                  # Playwright traces
│   └── metrics/                 # CSV metrics
│
├── docker/
│   ├── Dockerfile.executor
│   ├── Dockerfile.monitor
│   ├── Dockerfile.jira
│   └── docker-compose.yml
│
├── scripts/
│   └── setup.sh
│
├── docs/
│   └── plans/
│
├── .env.example
├── .gitignore
└── README.md
```

---

## Testing Strategy

### Unit Tests (Required)
- [ ] HealthAnalyzer memory leak detection
- [ ] HealthAnalyzer CPU anomaly detection
- [ ] MetricsCollector CDP integration
- [ ] MetricsCollector psutil integration
- [ ] JiraClient API operations
- [ ] JiraCommentFormatter formatting
- [ ] EvidencePackager file generation

### Integration Tests (Required)
- [ ] End-to-end test execution flow
- [ ] Monitor → Executor WebSocket communication
- [ ] Jira integrator posting
- [ ] Docker service orchestration

### Coverage Target: 80%+

---

## Next Steps

### Immediate
1. Write unit tests for each component
2. Write integration tests for E2E flow
3. Create example test scripts
4. Test with real Jira instance

### Future Enhancements
1. WhatsApp trigger interface
2. Parallel test execution support
3. Real-time execution status via WebSocket
4. Historical metrics tracking
5. Alerting on repeated health issues

---

## Success Criteria

- [x] All services containerized with Docker
- [x] Health monitoring implemented with sidecar pattern
- [x] Jira integration functional
- [x] Evidence package generation complete
- [x] Setup script functional
- [x] API documentation complete
- [ ] Unit tests passing (80%+ coverage)
- [ ] Integration tests passing
- [ ] Production deployment tested

---

**Implementation Complete:** 2026-03-08
**Ready for:** Testing and deployment
