# MS Teams Integration Guide

Complete guide for setting up and configuring Microsoft Teams integration with NanoClaw Test Executor.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Azure Bot Registration](#azure-bot-registration)
4. [Environment Configuration](#environment-configuration)
5. [Service Setup](#service-setup)
6. [Teams App Installation](#teams-app-installation)
7. [Using the Bot](#using-the-bot)
8. [Adaptive Cards](#adaptive-cards)
9. [Troubleshooting](#troubleshooting)
10. [Security Considerations](#security-considerations)

---

## Overview

The NanoClaw Teams integration allows you to trigger test executions, monitor status, and receive results directly within Microsoft Teams. The bot supports both channel conversations and 1:1 chats, with rich Adaptive Cards providing visual health status indicators.

### Key Features

- **Rich Adaptive Cards** with health grade badges (HEALTHY/WARNING/CRITICAL)
- **Real-time status updates** with progress indicators
- **Evidence package sharing** with direct Jira ticket links
- **Channel and 1:1 support** for flexible team workflows
- **Command-based interaction** for quick test management

### Architecture

```
Teams Client
    │
    ├─► /run {job_id}      ──► Teams Bot (Port 8004)
    ├─► /status {job_id}   ──►       │
    ├─► /results {job_id}  ──►       ├──► Command Processor
    ├─► /list             ──►       │        │
    └─► /help             ──►       │        ├──► Executor API (8001)
                                         │        └──► Jira API (8003)
```

---

## Prerequisites

Before setting up the Teams integration, ensure you have:

- **Azure Account** with active subscription
- **Microsoft Teams Admin** permissions (for org-wide app deployment)
- **Docker** installed on the host machine
- **NanoClaw Executor** already configured and running
- **Python 3.11+** (for local development)

### Required Accounts

| Account | Purpose | Permissions |
|---------|---------|-------------|
| Azure | Bot registration | Create Azure Bot resource |
| Teams App Studio | App manifest | Create and upload app package |
| NanoClaw Executor | Test execution | API access |

---

## Azure Bot Registration

### Step 1: Create Azure Bot Resource

1. Navigate to [Azure Portal](https://portal.azure.com)
2. Search for **"Azure Bot"** in the search bar
3. Click **Create** → **Azure Bot**
4. Fill in the required fields:
   - **Bot handle**: `nanoclaw-test-executor` (must be globally unique)
   - **Pricing tier**: Free (F0) or Standard (S1)
   - **Type of App**: Multi-tenant
   - **Location**: Choose nearest region
5. Click **Review + Create**, then **Create**

### Step 2: Configure Microsoft App ID

1. After creation, navigate to your bot resource
2. Click **Configuration** → **Microsoft App ID**
3. Click **Manage password** to create a new client secret
4. Copy and save the following:
   - **Application (client) ID** → This is your `TEAMS_APP_ID`
   - **Client secret** → This is your `TEAMS_APP_PASSWORD`

> **IMPORTANT**: Store the client secret securely. You won't be able to view it again after leaving the page.

### Step 3: Enable Teams Channel

1. In your bot resource, click **Channels** → **Teams**
2. Click the Teams icon to add the channel
3. Accept the terms of service
4. Save the configuration

### Step 4: Configure Messaging Endpoint

1. In your bot resource, click **Configuration**
2. Set **Messaging endpoint** to your publicly accessible URL:
   ```
   https://your-domain.com/api/teams/messages
   ```
3. For local development, use a tunneling service like [ngrok](https://ngrok.com):
   ```bash
   ngrok http 8004
   # Use the https URL from ngrok as your endpoint
   ```

### Step 5: Assign API Permissions

1. Navigate to **App registrations** in Azure Portal
2. Find your app (search by the App ID)
3. Click **API permissions** → **Add a permission**
4. Select **Microsoft Graph** → **Delegated permissions**
5. Add these permissions:
   - `Chat.Send` - Send messages in chats
   - `Chat.ReadWrite` - Read and write chat messages
6. Click **Add permissions** and **Grant admin consent**

---

## Environment Configuration

### 1. Update `.env` File

Add the following variables to your `.env` file:

```bash
# Microsoft Teams Configuration
TEAMS_APP_ID=your-microsoft-app-id-here
TEAMS_APP_PASSWORD=your-client-secret-here
TEAMS_PORT=8004
TEAMS_HOST=0.0.0.0

# Teams Bot Settings
TEAMS_ENABLE_CARDS=true
TEAMS_WELCOME_MESSAGE_ENABLED=true

# Executor API (for triggering tests)
EXECUTOR_API_URL=http://executor:8001

# Jira API (for fetching results)
JIRA_API_URL=http://jira-integrator:8003
```

### 2. Update `docker-compose.yml`

Add the Teams service to your Docker Compose configuration:

```yaml
services:
  # ... existing services ...

  teams:
    build:
      context: ../teams
      dockerfile: ../docker/Dockerfile.teams
    container_name: nanoclaw-teams
    ports:
      - "8004:8004"
    environment:
      - TEAMS_APP_ID=${TEAMS_APP_ID}
      - TEAMS_APP_PASSWORD=${TEAMS_APP_PASSWORD}
      - TEAMS_PORT=8004
      - EXECUTOR_API_URL=http://executor:8001
      - JIRA_API_URL=http://jira-integrator:8003
    networks:
      - nanoclaw-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8004/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## Service Setup

### Option A: Docker Deployment (Recommended)

1. **Build and start the service:**
   ```bash
   cd docker
   docker-compose up -d teams
   ```

2. **Verify the service is running:**
   ```bash
   docker-compose logs teams
   docker-compose ps
   ```

3. **Check health status:**
   ```bash
   curl http://localhost:8004/health
   ```

### Option B: Local Development Setup

1. **Install dependencies:**
   ```bash
   cd teams
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export TEAMS_APP_ID="your-app-id"
   export TEAMS_APP_PASSWORD="your-app-password"
   export TEAMS_PORT=8004
   ```

3. **Run the service:**
   ```bash
   python -m teams.main
   ```

4. **Expose local port (for Azure endpoint):**
   ```bash
   ngrok http 8004
   ```

---

## Teams App Installation

### Using App Studio (Recommended)

1. **Install App Studio in Teams:**
   - Open Microsoft Teams
   - Click **Apps** → **Manage your apps**
   - Search for **"App Studio"**
   - Click **Add**

2. **Create a new app:**
   - Open App Studio
   - Click **Manifest editor** → **Create a new app**
   - Fill in basic information:
     - **Short name**: NanoClaw Executor
     - **Full name**: NanoClaw Test Executor Bot
     - **Version**: 1.0.0
     - **Description**: Automated test execution with health monitoring
     - **Developer name**: Your Team Name
     - **Website URL**: Your organization's URL

3. **Configure app features:**
   - **App features** → **Bot**
   - Click **Create a new bot**
   - Enter your Azure bot handle
   - Select **Personal** and **Team** scopes
   - Save

4. **Generate app package:**
   - Click **Finish** → **Test and distribute**
   - Click **Download the app package**

5. **Install the app:**
   - In Teams, click **Apps** → **Manage your apps** → **Upload an app**
   - Select the downloaded `.zip` file
   - Click **Add**

### Using Direct Bot Link (Quick Test)

For quick testing without full app creation:

1. In Azure Portal, navigate to your bot
2. Click **Channels** → **Teams**
3. Click the link under **"Add the bot to a team"**
4. Select a team to add the bot to

---

## Using the Bot

### Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/run {job_id}` | Execute a test script | `/run login-test-123` |
| `/status {job_id}` | Check execution status | `/status login-test-123` |
| `/results {job_id}` | Get execution results | `/results login-test-123` |
| `/list` | List all executions | `/list` |
| `/help` | Show help message | `/help` |

### Command Examples

#### Execute a Test

```
/run test-login-flow
```

**Response:**
```adaptive
Test Execution Started

Job ID: test-login-flow
Execution ID: exec-20240308-153045
Started at: 2024-03-08 15:30:45

[Check Status Button]
```

#### Check Status

```
/status test-login-flow
```

**Response:**
```adaptive
Execution Status

Job ID: test-login-flow
Status: RUNNING
Started: 2024-03-08 15:30:45

[Get Results Button]
```

#### Get Results

```
/results test-login-flow
```

**Response:**
```adaptive
Execution Results

Job ID: test-login-flow
Execution ID: exec-20240308-153045
Test Result: PASS
Health Grade: HEALTHY
Duration: 2.3s

Metrics
Peak Memory: 234 MB
Peak CPU: 45%
Network Errors: 0
Console Errors: 0

[View in Jira Button]
```

---

## Adaptive Cards

The NanoClaw Teams bot uses Microsoft Adaptive Cards to provide rich, interactive responses.

### Health Grade Badges

Health grades are displayed with color-coded indicators:

| Grade | Color | Description |
|-------|-------|-------------|
| **HEALTHY** | Green | All metrics within normal thresholds |
| **WARNING** | Yellow | Some metrics elevated but test passed |
| **CRITICAL** | Red | Test failed or severe health issues |

### Card Types

#### 1. Help Card
- Lists all available commands
- Provides usage examples
- Quick action buttons

#### 2. Execution Started Card
- Job ID and Execution ID
- Start timestamp
- Check Status button

#### 3. Status Card
- Current execution status
- Progress bar (when available)
- Real-time health indicator

#### 4. Results Card
- Test result (PASS/FAIL)
- Health grade with badge
- Metrics table
- Jira link button

#### 5. Error Card
- Error message with details
- Help button
- Action suggestions

### Custom Card Example

```json
{
  "type": "AdaptiveCard",
  "body": [
    {
      "type": "TextBlock",
      "text": "Test Execution Results",
      "size": "Large",
      "weight": "Bolder"
    },
    {
      "type": "Container",
      "style": "Good",
      "items": [
        {
          "type": "TextBlock",
          "text": "HEALTHY",
          "size": "ExtraLarge",
          "color": "Good",
          "horizontalAlignment": "Center"
        }
      ]
    },
    {
      "type": "FactSet",
      "facts": [
        {"title": "Job ID:", "value": "test-123"},
        {"title": "Result:", "value": "PASS"},
        {"title": "Duration:", "value": "2.3s"}
      ]
    }
  ],
  "actions": [
    {
      "type": "Action.OpenUrl",
      "title": "View in Jira",
      "url": "https://jira.example.com/browse/QA-456"
    }
  ],
  "version": "1.4"
}
```

---

## Troubleshooting

### Common Issues

#### Bot Not Responding to Messages

**Symptoms:** Messages sent to bot show no response

**Solutions:**
1. Verify bot service is running:
   ```bash
   curl http://localhost:8004/health
   ```
2. Check Azure Bot messaging endpoint is correct
3. Verify ngrok tunnel is active (for local dev)
4. Check Teams bot logs:
   ```bash
   docker-compose logs teams -f
   ```

#### Authentication Errors

**Symptoms:** "Unauthorized" or "401" errors in logs

**Solutions:**
1. Verify `TEAMS_APP_ID` and `TEAMS_APP_PASSWORD` in `.env`
2. Regenerate client secret in Azure Portal if needed
3. Ensure Microsoft App ID is correctly configured in bot settings

#### Commands Not Recognized

**Symptoms:** Bot responds with "Unknown command" for valid commands

**Solutions:**
1. Check command_processor.py for command parsing logic
2. Verify message text is being received correctly (check logs)
3. Ensure no extra whitespace in commands

#### Adaptive Cards Not Rendering

**Symptoms:** Cards display as raw JSON or don't render

**Solutions:**
1. Verify Adaptive Card schema version (should be 1.4)
2. Test card JSON at [Adaptive Cards Designer](https://adaptivecards.io/designer/)
3. Check Teams client version (update if needed)

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
# In docker-compose.yml
environment:
  - LOG_LEVEL=DEBUG

# Or for local development
export LOG_LEVEL=DEBUG
python -m teams.main
```

### Health Check

Verify all components are accessible:

```bash
# Teams service health
curl http://localhost:8004/health

# Executor API health
curl http://localhost:8001/health

# Jira integrator health
curl http://localhost:8003/health
```

---

## Security Considerations

### Credential Management

- **Never commit credentials** to version control
- Use `.env` files (add to `.gitignore`)
- Rotate client secrets periodically (Azure recommends 90 days)
- Use Azure Key Vault for production deployments

### API Security

- The Teams service runs on port 8004 internally
- External access should go through Azure Bot Framework
- Enable HTTPS for all production endpoints
- Implement rate limiting to prevent abuse

### Teams Permissions

| Permission | Required | Purpose |
|------------|----------|---------|
| `Chat.Send` | Yes | Send messages to users |
| `Chat.ReadWrite` | Yes | Receive and process commands |
| `Team.ReadBasic.All` | Optional | List teams (for admin features) |

### Network Security

```yaml
# Recommended Docker network configuration
networks:
  nanoclaw-network:
    driver: bridge
    internal: false  # Set to true for complete isolation
    ipam:
      config:
        - subnet: 172.28.0.0/16
```

### Audit Logging

The Teams service logs all command interactions:

```python
# Logs include:
- User ID (Azure AD Object ID)
- Command executed
- Timestamp
- Execution ID
- Response status
```

---

## Advanced Configuration

### Custom Command Prefix

Change the default command prefix from `/` to something else:

```python
# In teams/teams/command_processor.py
COMMAND_PREFIX = "!"  # Use !run, !status, etc.
```

### Adaptive Card Theme

Customize card colors and styling:

```python
# In teams/teams/adaptive_cards.py
THEME_CONFIG = {
    "HEALTHY": {"color": "Good", "icon": "HEALTHY"},
    "WARNING": {"color": "Warning", "icon": "WARNING"},
    "CRITICAL": {"color": "Attention", "icon": "CRITICAL"},
}
```

### Webhook Notifications

Configure webhook notifications for test completion:

```bash
# .env
TEAMS_WEBHOOK_URL=https://your-webhook-url
TEAMS_NOTIFY_ON_COMPLETE=true
TEAMS_NOTIFY_ON_FAILURE=true
```

---

## Production Deployment

### Azure Container Instances (ACI)

```bash
# Deploy to ACI
az container create \
  --resource-group nanoclaw-rg \
  --name nanoclaw-teams \
  --image your-registry/nanoclaw-teams:latest \
  --cpu 1 \
  --memory 1 \
  --ports 8004 \
  --environment-variables \
    TEAMS_APP_ID=$TEAMS_APP_ID \
    TEAMS_APP_PASSWORD=$TEAMS_APP_PASSWORD
```

### Kubernetes (AKS)

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nanoclaw-teams
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nanoclaw-teams
  template:
    metadata:
      labels:
        app: nanoclaw-teams
    spec:
      containers:
      - name: teams
        image: your-registry/nanoclaw-teams:latest
        ports:
        - containerPort: 8004
        env:
        - name: TEAMS_APP_ID
          valueFrom:
            secretKeyRef:
              name: teams-secrets
              key: app-id
        - name: TEAMS_APP_PASSWORD
          valueFrom:
            secretKeyRef:
              name: teams-secrets
              key: app-password
```

---

## Support and Resources

### Documentation

- [Microsoft Bot Framework Documentation](https://docs.microsoft.com/en-us/azure/bot-service/)
- [Adaptive Cards Documentation](https://adaptivecards.io/)
- [Teams Developer Platform](https://docs.microsoft.com/en-us/microsoftteams/platform/overview)

### Tools

- [Bot Framework Emulator](https://github.com/microsoft/BotFramework-Emulator)
- [Adaptive Cards Designer](https://adaptivecards.io/designer/)
- [App Studio](https://docs.microsoft.com/en-us/microsoftteams/platform/concepts/build-and-test/app-studio-overview)

### Community

- [Microsoft Teams Developers Community](https://techcommunity.microsoft.com/t5/Microsoft-Teams-Developers/ct-p/MicrosoftTeamsDevelopers)
- [Stack Overflow - microsoft-teams tag](https://stackoverflow.com/questions/tagged/microsoft-teams)

---

## Changelog

### Version 1.0.0 (2024-03-08)

- Initial Teams integration release
- Core commands: `/run`, `/status`, `/results`, `/list`, `/help`
- Adaptive Cards support with health grade badges
- Docker deployment support
- Jira integration for results linking
