# Vigil

**Execution-time health gate for automated UI testing**

---

## The Problem

A test that passes functionally can still fail operationally.

Traditional test runners answer one question:

> **Did the scripted flow pass?**

They don't tell you:
- Did the browser remain healthy?
- Did the application throw hidden errors?
- Is this release introducing memory leaks?
- Is there enough evidence for audit review?

Your tests pass in CI but degrade in production. You see intermittent failures that you can't reproduce. You ship code that "works" but makes the browser progressively slower.

---

## What Vigil Does

Vigil executes Playwright-based tests in an isolated environment and evaluates both **functional outcomes** and **runtime health**.

**Standard Runner:**
```
Test passes ✓ → Ship it
```

**Vigil:**
```
Test passes ✓ BUT browser memory leaked 500MB ✗ → FAIL
Test passes ✓ BUT console has uncaught exceptions ✗ → WARNING
Test passes ✓ AND all health metrics clean ✓ → SHIP
```

Vigil turns test execution into a health gate.

---

## Why Vigil

| Question | Traditional Runner | Vigil |
|----------|-------------------|-------|
| Did the flow pass? | ✅ | ✅ |
| Did the browser remain healthy? | ❓ | ✅ |
| Did the app throw hidden errors? | ❓ | ✅ |
| Is there evidence for audit review? | ❓ | ✅ |

**For regulated QA teams**, this difference is critical. A banking app can pass all functional tests but still have memory leaks, console exceptions, or network instability that would fail regulatory review—or cause production incidents.

Vigil catches what functional tests miss.

---

## One-Line Positioning

**Vigil is a runtime health auditor for automated UI tests.**

It evaluates not just whether tests pass, but whether the application and browser remain healthy during execution.

---

## How It Works: End-to-End Example

### 1. Trigger a Test

**Via MS Teams:**
```
/run QA-456
```

**Via API:**
```bash
curl -X POST http://localhost:8001/api/v1/execute \
  -H "Content-Type: application/json" \
  -d '{"job_id": "QA-456", "jira_ticket": "QA-456"}'
```

### 2. Execution with Monitoring

Vigil spins up a fresh browser context and runs the test while the monitoring sidecar collects:

| Metric | What It Detects | Threshold |
|--------|----------------|-----------|
| Memory Heap | Sawtooth patterns = memory leak | Growing > 100MB in 60s |
| CPU Usage | Bad JS loops, infinite recursion | >80% during idle |
| Network | Background API failures | Any 4xx/5xx |
| Console | Uncaught errors, warnings | Any stack trace |

### 3. Runtime Metrics Snapshot

During execution, Vigil streams real-time metrics:

```json
{
  "timestamp": "2026-03-10T15:30:00Z",
  "memory_heap_mb": 234.5,
  "cpu_percent": 45.2,
  "network_errors": [],
  "console_errors": []
}
```

### 4. Final Health Grade

After test completion, Vigil calculates:

```
HEALTHY
- Test: PASS ✓
- Memory: Stable (no leaks)
- CPU: Normal (<50% idle)
- Console: Clean (0 errors)
- Network: Clean (0 errors)
```

### 5. Jira Update

Vigil posts a structured comment to your Jira ticket:

```
## Vigil Test Execution Report

**Status:** ✅ PASS
**Health Grade:** ✓ HEALTHY
**Execution Time:** 2.3s
**Timestamp:** 2026-03-10T15:30:00Z

### Health Metrics

| Metric | Value | Status |
|--------|-------|--------|
| Peak Memory | 234 MB | ✓ Normal |
| Peak CPU | 45% | ✓ Normal |
| Network Errors | 0 | ✓ Clean |
| Console Errors | 0 | ✓ Clean |

### Evidence Package

Attached:
- metrics.csv - Time-series health data
- trace.zip - Playwright trace (open in Chrome)
- logs.txt - Full execution logs
```

### 6. Evidence Package Tree

```
results/{job_id}/
├── metrics.csv          # Time-series health data
├── logs.txt            # Terminal + console merged
├── trace.zip           # Playwright trace
├── screenshot/         # Failure screenshots
└── health_report.json  # Overall health grade
```

---

## Health Grading Model

### How Scoring Works

Vigil evaluates **5 dimensions** of runtime health, each contributing to the final grade:

| Dimension | Weight | What We Measure |
|-----------|--------|----------------|
| Test Result | 30% | Pass/Fail from pytest |
| Memory Stability | 25% | Sawtooth patterns, absolute growth |
| CPU Behavior | 20% | Idle usage, spike frequency |
| Console Cleanliness | 15% | Uncaught errors, deprecation warnings |
| Network Reliability | 10% | 4xx/5xx responses, timeouts |

### Grade Calculations

**HEALTHY** (Score: 90-100%)
- Test passes ✓
- All dimensions within normal bounds
- Zero hard-fail indicators

**WARNING** (Score: 60-89%)
- Test passes ✓ BUT one or more:
  - Minor console warnings (non-blocking)
  - Slow API responses (>2s but <5s)
  - Memory growth < 50MB over test duration
  - Occasional CPU spikes (60-80%)

**CRITICAL** (Score: 0-59%)
- Test fails ✗ OR any hard-fail indicator:
  - Memory leak detected (sawtooth pattern, >100MB growth)
  - CPU sustained >80% during idle
  - Uncaught exceptions in console
  - Network errors (4xx/5xx)
  - Browser freeze detected

### Hard Fail vs Soft Fail

| Indicator | Type | Impact |
|-----------|------|--------|
| Test failure | Hard | Immediate CRITICAL, blocks deployment |
| Memory leak >100MB | Hard | CRITICAL regardless of test result |
| Uncaught exception | Hard | CRITICAL regardless of test result |
| Network 5xx | Hard | CRITICAL regardless of test result |
| Console deprecation warning | Soft | WARNING if test passes |
| CPU spike 60-80% | Soft | WARNING if test passes |
| Slow API (>2s) | Soft | WARNING if test passes |

### Baseline Differences

Vigil normalizes thresholds by environment:

| Metric | Local Dev | CI/CD | UAT/Staging |
|--------|-----------|-------|-------------|
| Memory baseline | Relaxed | Standard | Strict |
| CPU tolerance | Higher | Normal | Lower |
| Network timeout | 10s | 5s | 3s |
| Console warnings | Allowed | Logged | Flagged |

**Why?** CI environments have consistent resources, UAT mimics production constraints, and local dev tolerates more noise.

### False Positive Handling

Vigil suppresses noisy findings through:

1. **Pattern matching** - Known benign warnings are filtered
2. **Context awareness** - Third-party script errors are flagged separately
3. **Trend analysis** - Single spikes are less concerning than sustained issues
4. **Environment normalization** - Thresholds adjust per environment

---

## Relationship with TestForge

**TestForge** = Test Generation
- Generates Playwright test scripts from Jira tickets
- Converts requirements into executable test cases

**Vigil** = Execution + Runtime Audit
- Executes tests in isolated environments
- Monitors runtime health during execution
- Packages evidence and updates Jira

**Together** = Complete AI QA Pipeline
```
Jira Ticket → TestForge → Test Script → Vigil → Health Grade → Jira Update
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    TestForge: Test Generator                      │
│                   (testforge-project)                            │
│                      Shared Volume                               │
│                         ↓                                        │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │   Shared Network      │
                    │   Drive /scripts      │
                    └───────────┬───────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        │                                               │
┌───────▼──────────┐                         ┌────────▼────────┐
│  Vigil Executor  │◄────metrics─────────│  Monitor Sidecar│
│  - pytest runner │                         │  - CPU/Memory   │
│  - trace capture│   ┌──────────────────┐  │  - Network      │
│  - log merge    │───│  Jira Integrator│  │  - Console      │
│  - health grade │   │  - Comment post  │──│  - CDP Protocol │
└──────────────────┘   │  - Attachment    │  └─────────────────┘
                       └──────────────────┘
                                │
                        ┌───────▼────────┐
                        │  MS Teams Bot  │
                        │  - Trigger cmd │
                        │  - Status notif│
                        └────────────────┘
```

---

## Quick Start

### Option 1: Interactive Setup Wizard (Recommended)

```bash
cd /path/to/vigil

# Install CLI dependencies
pip install -r requirements-cli.txt

# Run the setup wizard
./scripts/setup-wizard.sh
# or
python -m cli.setup
```

The wizard will:
- Let you select which services to configure (Jira, Teams)
- Validate all inputs in real-time
- Test connections before saving
- Automatically generate your `.env` file

### Option 2: Manual Configuration

```bash
# Clone and setup
cd /path/to/vigil
./scripts/setup.sh

# Configure environment
cp .env.example .env
nano .env

# Start services
cd docker
docker-compose up -d
```

**Services Started:**
- `executor` - Test execution engine (port 8001)
- `monitor` - Health monitoring sidecar (port 8002)
- `jira-integrator` - Jira update service (port 8003)
- `teams` - MS Teams integration service (port 8004)

### Execute Your First Test

**Via MS Teams:**
```
/run abc-123
```

**Via API:**
```bash
curl -X POST http://localhost:8001/api/v1/execute \
  -H "Content-Type: application/json" \
  -d '{"job_id": "abc-123", "jira_ticket": "QA-456"}'
```

---

## Core Components

### 1. Executor Service (`executor/`)
Runs pytest with Playwright in isolated Docker containers.

**Features:**
- Fresh browser context per test (no cache, no cookies)
- `pytest --json-report --trace` for machine-readable results
- Real-time health monitoring integration
- Sequential execution with error handling

### 2. Monitor Sidecar (`monitor/`)
Watches browser vitals during test execution.

**Technology:**
- `psutil` for process metrics
- Chrome DevTools Protocol (CDP) for browser internals
- Streaming metrics via WebSocket to executor

**Why Sidecar?** Running monitoring inside the test container only sees container limits, not actual browser pain. The sidecar observes the host system, catching resource exhaustion that containers miss.

### 3. Jira Integrator (`jira_integrator/`)
Updates Jira tickets with structured test results and evidence packages.

### 4. Evidence Packager
Builds forensic evidence folders for audit review and debugging.

### 5. MS Teams Integration
Trigger tests and monitor results directly in Microsoft Teams with rich Adaptive Cards.

See [Teams Integration Guide](docs/teams-integration.md) for detailed setup.

---

## What's New

### ✅ Recent Implementations

| Feature | Issue | Status |
|---------|-------|--------|
| Interactive Setup Wizard | [#3](https://github.com/kianwoon/vigil/issues/3) | ✅ Implemented |
| MS Teams Integration | [#2](https://github.com/kianwoon/vigil/issues/2) | ✅ Implemented |

**v1.1.0** (2026-03-08)
- ✨ Added interactive `/setup` command for environment configuration
- ✨ Added MS Teams Bot integration with Adaptive Cards
- ✨ Added connection testing during setup
- 📝 Updated documentation with CLI commands

---

## API Endpoints

### Executor API (port 8001)

**POST /api/v1/execute**
Execute a test script.

```json
{
  "job_id": "abc-123-def",
  "jira_ticket": "QA-456",
  "script_path": "/shared/scripts/test_login.py"
}
```

**GET /api/v1/status/{execution_id}**
Get execution status with health grade and metrics.

**GET /api/v1/trace/{execution_id}**
Serve Playwright trace viewer for debugging.

### Monitor API (port 8002)

**WS /ws/metrics**
WebSocket endpoint for real-time metric streaming during execution.

---

## Testing

```bash
# Run all tests with coverage
./scripts/test.sh

# Run only unit tests
./scripts/test.sh unit

# Run only integration tests
./scripts/test.sh integration
```

Current coverage target: **80%+**

---

## Directory Structure

```
vigil/
├── cli/                         # Interactive CLI setup wizard
├── executor/                    # Executor service
├── monitor/                     # Monitoring sidecar
├── jira_integrator/             # Jira service
├── teams/                       # MS Teams integration
├── shared/                      # Shared volume
│   ├── scripts/                 # Input from testforge
│   ├── results/                 # Execution outputs
│   ├── traces/                  # Playwright traces
│   └── metrics/                 # CSV metrics
├── docker/                      # Docker configurations
├── scripts/                     # Setup and utility scripts
├── docs/                        # Documentation
└── tests/                       # Integration tests
```

---

## License

Internal use only - Bank QA Automation Team
