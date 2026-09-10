# Proxmox Ubuntu LXC & Hermes Agent Deployment SOP

A comprehensive Standard Operating Procedure (SOP) for deploying and configuring the **Hermes Agent** inside an Ubuntu LXC container on Proxmox, complete with automated profile onboarding, systemd service management, periodic memory synchronization, and GitHub authentication guidance.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Deployment Procedure](#deployment-procedure)
  - [1. Obtain Telegram Credentials](#1-obtain-telegram-credentials)
  - [2. Create Container & Install System Dependencies](#2-create-container--install-system-dependencies)
  - [3. Clone Repository & Set Permissions](#3-clone-repository--set-permissions)
  - [4. Set Up Python Virtual Environment](#4-set-up-python-virtual-environment)
  - [5. Configure Secrets & LLM Settings](#5-configure-secrets--llm-settings)
  - [6. Onboard Profile, Branch & Symlink](#6-onboard-profile-branch--symlink)
  - [7. Enable systemd Persistence](#7-enable-systemd-persistence)
  - [8. Automate Branch Memory Synchronization](#8-automate-branch-memory-synchronization)
- [Verification & Monitoring](#verification--monitoring)
- [Deployment Completion Checklist](#deployment-completion-checklist)
- [Basic Troubleshooting](#basic-troubleshooting)
- [GitHub Authentication & Personal Access Token (PAT) Setup](#github-authentication--personal-access-token-pat-setup)

---

## Prerequisites

Before beginning the deployment, ensure the following are available:

- **Proxmox VE** instance with permission to create and manage LXC containers.
- **GitHub Personal Access Token (PAT)** with repository read/write access.
- **OpenRouter API Key** for LLM backend services.
- **Telegram Account** for bot setup and chat interface.

> **Security:** Treat Telegram bot tokens, OpenRouter API keys, GitHub PATs, and other credentials as secrets. Never commit them to Git or place them in publicly accessible files.

---

# Deployment Procedure

## 1. Obtain Telegram Credentials

### 1.1 Create the Telegram Bot

1. Search for `@BotFather` on Telegram.
2. Send `/newbot`.
3. Follow the setup prompts.
4. Save the HTTP API token.

> **Example:**
> `"8929783253:AAF80DFFfdRSVH9WYz0hT91JoDUJhk010mX0"`

> **Note:** Always wrap tokens containing colons in double quotes when placing them in configuration files.

### 1.2 Obtain the User/Chat ID

1. Search for `@userinfobot` on Telegram.
2. Send `/start`.
3. Save the numeric user/chat ID.

> **Example:**
> `5323393142`

---

## 2. Create Container & Install System Dependencies

### 2.1 Create the Ubuntu LXC Container

Create an Ubuntu LXC container in Proxmox VE using your organization's standard container sizing, networking, storage, and access configuration.

### 2.2 Install Prerequisites

Update the operating system, add the Deadsnakes PPA, and install Python 3.11 and required system dependencies:

```bash
apt update && apt upgrade -y
apt install -y software-properties-common curl git build-essential
add-apt-repository ppa:deadsnakes/ppa -y || apt update
apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
```

---

## 3. Clone Repository & Set Permissions

### 3.1 Clone the Repository

Clone the Hermes base setup repository into `/opt/hermes`:

```bash
git clone https://github.com/startupteams/hermes-base-setup.git /opt/hermes
cd /opt/hermes
```

### 3.2 Set File Permissions

Ensure the main agent, onboarding script, and memory synchronization script are executable:

```bash
chmod +x /opt/hermes/main.py
chmod +x /opt/hermes/init_employee.py
chmod +x /opt/hermes/scripts/sync_memory.sh
```

---

## 4. Set Up Python Virtual Environment

Create and activate the Python 3.11 virtual environment, then install the required packages:

```bash
python3.11 -m venv /opt/hermes/.venv
source /opt/hermes/.venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
pip install python-dotenv requests
```

---

## 5. Configure Secrets & LLM Settings

### 5.1 Populate Environment Secrets

Create `/opt/hermes/.env`:

```bash
cat << 'EOF' > /opt/hermes/.env
OPENROUTER_API_KEY="your_actual_openrouter_api_key_here"
TELEGRAM_BOT_TOKEN="your_default_telegram_bot_token_here"
TELEGRAM_ALLOWED_USERS="your_numeric_user_id_here"
EOF
```

> **Important:** Always quote tokens containing colons.

### 5.2 Configure Global LLM Settings

Create the repository-level configuration:

```bash
cat << 'EOF' > /opt/hermes/config.yaml
llm:
  provider: openrouter
  model: openrouter/free # change to your preferred model
EOF
```

Create the user-level Hermes configuration:

```bash
mkdir -p ~/.hermes
cat << 'EOF' > ~/.hermes/config.yaml
llm:
  provider: openrouter
  model: openrouter/free # change to your preferred model
EOF
```

---

## 6. Onboard Profile, Branch & Symlink

### 6.1 Initialize the Employee Profile

Run `init_employee.py` to create a dedicated Git branch, build the profile configuration, and push the resulting changes to the remote repository:

```bash
/opt/hermes/.venv/bin/python init_employee.py \
  --name <employee_name> \
  --role "<role_description>" \
  --template <template_key> \
  --chat-id <telegram_chat_id>
```

### 6.2 Supported Template Keys

Use one of the following values for `--template`:

| Template Key | Profile Template |
|---|---|
| `admin` | `AGENT_STEA001_ADMIN` |
| `fullstack` | `AGENT_STEA002_FULL_STACK_SOFTWARE_ENGINEER` |
| `aiml` | `AGENT_STEA003_AI_ML_SOFTWARE_ENGINEER` |
| `entrepreneur` | `AGENT_STEA004_ENTREPRENEUR` |
| `systems` | `AGENT_STEA005_SYSTEMS_ENGINEER` |
| `sales` | `AGENT_STEA006_SALES_AND_MARKETING` |
| `pm` | `AGENT_STEA007_PROGRAM_MANAGEMENT` |
| `network` | `AGENT_STEA008_NETWORK_ENGINEER` |

### 6.3 Example Onboarding Command

```bash
/opt/hermes/.venv/bin/python init_employee.py \
  --name biraj \
  --role "AI/ML Intern" \
  --template aiml \
  --chat-id 5323393142
```

### 6.4 Create the Runtime Profile Symlink

Symlink the generated profile folder into `~/.hermes/profiles/` for runtime path resolution:

```bash
mkdir -p ~/.hermes/profiles
ln -sfn /opt/hermes/profiles/<employee_name> ~/.hermes/profiles/<employee_name>
```

---

## 7. Enable systemd Persistence

### 7.1 Configure the systemd Service Template

Copy the service template into the systemd unit directory, point it to the Python virtual environment, and load the environment file:

```bash
cp /opt/hermes/deploy/hermes-agent@.service /etc/systemd/system/hermes-agent@.service
sed -i 's|/usr/bin/python3|/opt/hermes/.venv/bin/python|g' /etc/systemd/system/hermes-agent@.service
sed -i '/\[Service\]/a EnvironmentFile=/opt/hermes/.env' /etc/systemd/system/hermes-agent@.service
```

### 7.2 Enable and Start the Service

Reload systemd and enable the employee-specific service:

```bash
systemctl daemon-reload
systemctl enable --now hermes-agent@<employee_name>
```

---

## 8. Automate Branch Memory Synchronization

### 8.1 Create executable Synchronization Script


```bash
chmod +x /opt/hermes/scripts/sync_memory.sh
```

### 8.2 Schedule Synchronization Every 15 Minutes

Install a cron entry that runs the memory synchronization script every 15 minutes:

```bash
(crontab -l 2>/dev/null; echo "*/15 * * * * /opt/hermes/scripts/sync_memory.sh") | crontab -
```

> **Operational consideration:** The synchronization command may produce a non-zero result when there are no changes to commit. Monitor cron output if you need to distinguish normal no-change runs from actual synchronization failures.

---

# Verification & Monitoring

After deployment, confirm that the service is enabled, running, and producing expected logs.

## Check Service Status

Replace `<employee_name>` with the onboarded profile name:

```bash
systemctl status hermes-agent@<employee_name>
```

## Stream Live Logs

Use `journalctl` to inspect the agent in real time:

```bash
journalctl -u hermes-agent@<employee_name> -f
```

---

# Deployment Completion Checklist

Use the following checklist to confirm that all deployment steps have been completed:

- [ ] Ubuntu LXC container created and reachable.
- [ ] Python 3.11 and required system dependencies installed.
- [ ] Hermes repository cloned to `/opt/hermes`.
- [ ] Python virtual environment created and dependencies installed.
- [ ] OpenRouter and Telegram secrets configured.
- [ ] Global and user-level LLM configuration files created.
- [ ] Employee profile initialized and pushed to its Git branch.
- [ ] Profile symlink created under `~/.hermes/profiles/`.
- [ ] systemd service template installed and configured.
- [ ] Employee-specific Hermes service enabled and running.
- [ ] Memory synchronization script installed and executable.
- [ ] 15-minute cron job configured.
- [ ] Service status and live logs verified.

---

# Basic Troubleshooting

| Symptom | Recommended Checks |
|---|---|
| Service fails to start | Run `systemctl status hermes-agent@<employee_name>` and `journalctl -u hermes-agent@<employee_name> -n 100 --no-pager`. Verify the Python path, environment file, profile symlink, and configuration. |
| Missing Python dependency | Activate `/opt/hermes/.venv` and reinstall `requirements.txt`. Confirm that the service uses `/opt/hermes/.venv/bin/python`. |
| Telegram authentication/configuration issue | Verify `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_USERS` in `/opt/hermes/.env` and confirm that the Telegram chat/user ID is correct. |
| LLM requests fail | Verify `OPENROUTER_API_KEY` and the configured model/provider in both `config.yaml` locations. |
| Memory sync does not push | Run `/opt/hermes/scripts/sync_memory.sh` manually and inspect Git credentials, current branch, repository status, and remote access. |

---

# GitHub Authentication & Personal Access Token (PAT) Setup

During the employee onboarding and memory synchronization process, GitHub may prompt for credentials when pushing a branch to the remote repository.

GitHub does **not** use your normal account password for Git operations over HTTPS. When prompted:

- Enter your **GitHub username** as the username.
- Enter your **Personal Access Token (PAT)** as the password.

> **Important:** The PAT is used in place of your normal GitHub password.

## What You May Encounter

When running the onboarding process or a Git push, you may see prompts similar to:

```text
Username for 'https://github.com': <your_github_username>
Password for 'https://<your_github_username>@github.com': <paste_your_PAT_here>
```

Enter your GitHub username at the first prompt.

At the password prompt, paste the PAT instead of your normal GitHub password. The token will normally **not be displayed** while typing or pasting it.

---

## How to Create a GitHub Personal Access Token

### Step 1: Sign in to GitHub

Sign in to the GitHub account that has access to the Hermes repository.

### Step 2: Open Developer Settings

Navigate to:

**Profile Picture → Settings → Developer settings**

### Step 3: Open Personal Access Tokens

Select:

**Personal access tokens → Fine-grained tokens**

Fine-grained tokens are recommended because repository access and permissions can be restricted.

### Step 4: Generate a New Token

Click:

**Generate new token**

Provide a descriptive name, for example:

```text
Hermes LXC Deployment
```

### Step 5: Set an Expiration Date

Choose an appropriate expiration period according to your organization's security policy.

Avoid unnecessarily long-lived tokens.

### Step 6: Restrict Repository Access

Under **Repository access**, select:

**Only select repositories**

Then select the Hermes repository when possible.

### Step 7: Configure Repository Permissions

Grant the minimum permissions required for the deployment.

For HTTPS Git push operations, ensure the token has:

```text
Repository permissions
└── Contents: Read and write
```

Additional permissions should only be granted when required by the repository workflow.

### Step 8: Generate the Token

Review the token configuration and click:

**Generate token**

### Step 9: Copy the Token

Copy the generated token immediately and store it securely.

> **Important:** GitHub may not display the full token again after you leave the page.

---

## Use the PAT When Git Prompts for Credentials

Return to the Ubuntu LXC terminal and repeat the Git operation requiring authentication.

For example:

```bash
git push origin <branch_name>
```

When prompted:

```text
Username for 'https://github.com': <your_github_username>
Password for 'https://<your_github_username>@github.com': <paste_your_PAT_here>
```

If authentication succeeds, the branch and its commits should be pushed to the configured GitHub remote.

---

## PAT Security Best Practices

- Use a **fine-grained PAT** whenever possible.
- Restrict the token to the required repository.
- Grant only the permissions required for Git operations.
- Set an expiration date and rotate the token when required.
- Never share the PAT through chat, email, screenshots, or source code.
- Never commit the PAT to Git.
- Never place the PAT directly inside repository configuration files.
- Do not place the PAT inside `/opt/hermes/.env` unless the deployment specifically requires it.
- If the token is exposed, revoke it immediately and create a replacement.

> **Security Warning:** A PAT can provide access to repositories and other GitHub resources depending on its permissions. Treat it like a password.

---

## If GitHub Rejects the PAT

If GitHub reports an authentication or permission error, verify the following:

- The GitHub username is correct.
- The PAT has not expired or been revoked.
- The PAT has access to the Hermes repository.
- The token has `Contents: Read and write` permission for the repository.
- Your Git remote points to the expected GitHub repository.
- Your GitHub account has permission to push to the target repository.

Check the configured remote:

```bash
git remote -v
```

Check the current repository status:

```bash
git status
```

Check the active branch:

```bash
git branch --show-current
```

After correcting the credentials or permissions, retry the push operation:

```bash
git push origin <branch_name>
```

---

## Final Security Reminder

Never place a GitHub PAT directly into a Git command, script, repository file, or configuration file where it could be committed or exposed.

If a PAT is accidentally exposed:

1. Revoke the exposed token immediately in GitHub.
2. Generate a new fine-grained PAT.
3. Restrict it to the required repository and permissions.
4. Retry the Git operation using the new token.
