# Proxmox Ubuntu LXC & Hermes Agent Deployment SOP

A comprehensive Standard Operating Procedure (SOP) for deploying and configuring the **Hermes Agent** inside an Ubuntu LXC container on Proxmox, complete with automated profile onboarding, systemd service management, and periodic memory synchronization.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Deployment Steps](#deployment-steps)
  - [1. Obtain Telegram Credentials](#1-obtain-telegram-credentials)
  - [2. Create Container & Install System Dependencies](#2-create-container--install-system-dependencies)
  - [3. Clone Repository with PAT Authentication](#3-clone-repository-with-pat-authentication)
  - [4. Setup Python Virtual Environment](#4-setup-python-virtual-environment)
  - [5. Configure Secrets & Fallbacks](#5-configure-secrets--fallbacks)
  - [6. Onboard Profile, Branch, & Symlink](#6-onboard-profile-branch--symlink)
  - [7. Enable Systemd Persistence](#7-enable-systemd-persistence)
  - [8. Automate Branch Memory Synchronization](#8-automate-branch-memory-synchronization)
- [Verification & Monitoring](#verification--monitoring)

---

## Prerequisites

- **Proxmox VE** instance with permissions to create LXC containers.
- **GitHub Personal Access Token (PAT)** with repository read/write access.
- **OpenRouter API Key** for LLM backend services.
- **Telegram Account** for bot setup and chat interface.

---

## Deployment Steps

### 1. Obtain Telegram Credentials

1. **Bot Token**: Search for `@BotFather` on Telegram, send `/newbot`, follow the setup prompts, and save the HTTP API token (wrap in double quotes if it contains colons).
   > *Example:* `"8929783253:AAF80DFFfdRSVH9WYz0hT91JoDUJhk010mX0"`
2. **User/Chat ID**: Search for `@userinfobot` on Telegram, send `/start`, and save your numeric ID.
   > *Example:* `5323393142`

---

### 2. Create Container & Install System Dependencies

1. **Create Container**: Create an Ubuntu LXC container in Proxmox


2. **Install Prerequisites**: Update packages, add the Deadsnakes PPA, and install Python 3.11:
   ```bash
   apt update && apt upgrade -y
   apt install -y software-properties-common curl git build-essential
   add-apt-repository ppa:deadsnakes/ppa -y || apt update
   apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
   ```

---

### 3. Clone Repository with PAT Authentication


1. **Clone Repository**:
   ```bash
   git clone https://github.com/startupteams/hermes-base-setup.git /opt/hermes
   cd /opt/hermes
   ```

3. **Set File Permissions**:
   ```bash
   chmod +x /opt/hermes/main.py
   chmod +x /opt/hermes/init_employee.py
   chmod +x /opt/hermes/scripts/sync_memory.sh
   ```

---

### 4. Setup Python Virtual Environment

Create and activate the virtual environment, then install required Python packages:

```bash
python3.11 -m venv /opt/hermes/.venv
source /opt/hermes/.venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
pip install python-dotenv requests
```

---

### 5. Configure Secrets & Fallbacks

1. **Populate Environment Secrets** (`/opt/hermes/.env`):
   *(Always quote tokens containing colons)*
   ```bash
   cat << 'EOF' > /opt/hermes/.env
   OPENROUTER_API_KEY="your_actual_openrouter_api_key_here"
   TELEGRAM_BOT_TOKEN="your_default_telegram_bot_token_here"
   TELEGRAM_ALLOWED_USERS="your_numeric_user_id_here"
   EOF
   ```

2. **Configure Global LLM Settings**:
   ```bash
   cat << 'EOF' > /opt/hermes/config.yaml
   llm:
     provider: openrouter
     model: openrouter/free # change to your preferred model
   EOF

   mkdir -p ~/.hermes
   cat << 'EOF' > ~/.hermes/config.yaml
   llm:
     provider: openrouter
     model: openrouter/free # change to your preferred model
   EOF
   ```

---

### 6. Onboard Profile, Branch, & Symlink

1. **Initialize Employee Profile**:
   Execute `init_employee.py` to create a dedicated Git branch, build profile configurations, and push changes to remote:
   ```bash
   /opt/hermes/.venv/bin/python init_employee.py \
     --name <employee_name> \
     --role "<role_description>" \
     --template <template_key> \
     --chat-id <telegram_chat_id>
   ```
   
   ```python
    # Use one of the following keys for the flag --template
    TEMPLATE_MAP = {
      "admin": "AGENT_STEA001_ADMIN",
      "fullstack": "AGENT_STEA002_FULL_STACK_SOFTWARE_ENGINEER",
      "aiml": "AGENT_STEA003_AI_ML_SOFTWARE_ENGINEER",
      "entrepreneur": "AGENT_STEA004_ENTREPRENEUR",
      "systems": "AGENT_STEA005_SYSTEMS_ENGINEER",
      "sales": "AGENT_STEA006_SALES_AND_MARKETING",
      "pm": "AGENT_STEA007_PROGRAM_MANAGEMENT",
      "network": "AGENT_STEA008_NETWORK_ENGINEER",
    }
```

   *Example Command:*
   ```bash
   /opt/hermes/.venv/bin/python init_employee.py \
     --name biraj \
     --role "AI/ML Intern" \
     --template aiml \
     --chat-id 5323393142
   ```

2. **Symlink Profile Directory**:
   Symlink the generated profile folder into `~/.hermes/profiles/` for runtime path resolution:
   ```bash
   mkdir -p ~/.hermes/profiles
   ln -sfn /opt/hermes/profiles/<employee_name> ~/.hermes/profiles/<employee_name>
   ```

---

### 7. Enable Systemd Persistence

1. **Configure Systemd Service Template**:
   ```bash
   cp /opt/hermes/deploy/hermes-agent@.service /etc/systemd/system/hermes-agent@.service
   sed -i 's|/usr/bin/python3|/opt/hermes/.venv/bin/python|g' /etc/systemd/system/hermes-agent@.service
   sed -i '/\[Service\]/a EnvironmentFile=/opt/hermes/.env' /etc/systemd/system/hermes-agent@.service
   ```

2. **Enable and Start Service**:
   ```bash
   systemctl daemon-reload
   systemctl enable --now hermes-agent@<employee_name>
   ```

---

### 8. Automate Branch Memory Synchronization

1. **Create Synchronization Script**:
   ```bash
   cat << 'EOF' > /opt/hermes/scripts/sync_memory.sh
   #!/bin/bash
   cd /opt/hermes || exit
   CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
   git add profiles/
   git commit -m "chore(memory): sync agent state [skip ci]"
   git push origin "$CURRENT_BRANCH"
   EOF

   chmod +x /opt/hermes/scripts/sync_memory.sh
   ```

2. **Schedule Cron Job** (Every 15 Minutes):
   ```bash
   (crontab -l 2>/dev/null; echo "*/15 * * * * /opt/hermes/scripts/sync_memory.sh") | crontab -
   ```

---

## Verification & Monitoring

Check the operational status and inspect live logs for the agent service:

- **Check Service Status**:
  ```bash
  systemctl status hermes-agent@<employee_name>
  ```

- **Stream Live Logs**:
  ```bash
  journalctl -u hermes-agent@<employee_name> -f
  ```
