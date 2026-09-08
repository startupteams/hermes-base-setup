# Proxmox LXC & Hermes Agent Setup

## 1. Create and Configure the LXC Container

## 2. Install Python Version Compatibility Prerequisites
Update package lists and install system build utilities and software properties dependencies:

```bash
apt update && apt upgrade -y
apt install -y software-properties-common curl git build-essential
```

**Compatibility Note:** If the default OS repository Python version conflicts with Hermes requirements, add the deadsnakes PPA (on Ubuntu) or install/compile the required compatible version. For standard setups:

```bash
apt install -y python3 python3-pip python3-venv python3-dev
```

## 3. Clone the Repository & Setup Virtual Environment
Clone the target repository into `/opt/hermes/`:

```bash
git clone https://github.com/startupteams/hermes-base-setup.git /opt/hermes
cd /opt/hermes
```

Initialize and activate the virtual environment using the verified compatible Python binary:

```bash
python3 -m venv /opt/hermes/.venv
source /opt/hermes/.venv/bin/activate
pip install --upgrade pip
```

Install package dependencies and support modules:

```bash
pip install -e .
pip install python-dotenv requests
```

## 4. Create a Working Branch
Create and switch to your own dedicated feature branch for modifications:

```bash
git checkout -b <your-branch-name>
```

## 5. Configure Environment & Profile Files
Create the global environment configuration file at `/opt/hermes/.env` using placeholder tokens:

```bash
cat << 'EOF' > /opt/hermes/.env
TELEGRAM_BOT_TOKEN=your_default_bot_token_here
TELEGRAM_BOT_TOKEN_<AGENT_NAME>=your_profile_bot_token_here
TELEGRAM_ALLOWED_USERS=your_numeric_user_id_here
OPENAI_API_KEY=your_openai_api_key_here
EOF
```

Create the profile-specific configuration directory and file at `/opt/hermes/profiles/<agent_name>/config.yaml`:

```bash
mkdir -p /opt/hermes/profiles/<agent_name>
cat << 'EOF' > /opt/hermes/profiles/<agent_name>/config.yaml
llm:
  provider: openai
  model: gpt-4o
EOF
```

## 6. Create the Profile Wrapper Script (main.py)
Write the intermediary Python script to handle dynamic environment variable mapping per profile (bridging multi-profile secrets to the upstream gateway execution):

```bash
cat << 'EOF' > /opt/hermes/main.py
import os
import argparse
import subprocess
from dotenv import load_dotenv

parser = argparse.ArgumentParser()
parser.add_argument("--profile", "-p", required=True)
args = parser.parse_args()

load_dotenv("/opt/hermes/.env")

profile_token_key = f"TELEGRAM_BOT_TOKEN_{args.profile.upper()}"
if os.getenv(profile_token_key):
    os.environ["TELEGRAM_BOT_TOKEN"] = os.getenv(profile_token_key)

env = os.environ.copy()
cmd = ["/opt/hermes/.venv/bin/hermes", "-p", args.profile, "gateway", "run"]

process = subprocess.Popen(cmd, env=env)
process.wait()
EOF
chmod +x /opt/hermes/main.py
```

## 7. Set Up Systemd Service for 24/7 Telegram Bot Persistence
Create the systemd template service file at `/etc/systemd/system/hermes-agent@.service`:

```bash
cat << 'EOF' > /etc/systemd/system/hermes-agent@.service
[Unit]
Description=Hermes AI Agent Service for %i
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/hermes
ExecStart=/opt/hermes/.venv/bin/python /opt/hermes/main.py --profile %i
Restart=always
RestartSec=5
EnvironmentFile=/opt/hermes/.env

[Install]
WantedBy=multi-user.target
EOF
```

Reload systemd and enable/start the service using your target profile name (replace `<agent_name>` with your actual profile identifier):

```bash
systemctl daemon-reload
systemctl enable --now hermes-agent@<agent_name>
```

## 8. Verification and Log Monitoring
Check live system status and stream log output to verify execution:

```bash
systemctl status hermes-agent@<agent_name>
journalctl -u hermes-agent@<agent_name> -f
```
