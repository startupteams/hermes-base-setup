#!/usr/bin/env python3
"""
Hermes AI Agent - Employee Onboarding Utility
Generates isolated profile environments in profiles/<employee_name>/
using minimalist SOUL.md blueprints on a dedicated Git branch.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

# Short-key mapping for quick CLI usage
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


def run_git_command(cmd, cwd):
    try:
        res = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {' '.join(cmd)}\nError: {e.stderr.strip()}", file=sys.stderr)
        return None


def init_employee(
    name: str, 
    role: str, 
    chat_id: str,
    template_folder: str, 
    root_dir: Path, 
    create_branch: bool = True,
    push_remote: bool = True
):
    name_clean = name.strip().lower().replace(" ", "_")
    branch_name = f"{name_clean}"
    profile_dir = root_dir / "profiles" / name_clean
    template_soul = root_dir / "templates" / template_folder / "SOUL.md"

    # Load root .env variables to fetch profile credentials if present
    load_dotenv(root_dir / ".env")
    env_token_key = f"TELEGRAM_BOT_TOKEN_{name_clean.upper()}"
    bot_token_val = os.getenv(env_token_key, "")

    print(f"\n==================================================")
    print(f" Initializing Hermes Agent Profile for: {name}")
    print(f" Target Folder: profiles/{name_clean}/")
    print(f" Role: {role}")
    print(f" Template: {template_folder}")
    print(f" Target Branch: {branch_name if create_branch else 'current'}")
    print(f"==================================================\n")

    # 1. Switch or create local git branch BEFORE creating files
    if create_branch:
        print(f"[*] Creating and checking out local Git branch '{branch_name}'...")
        run_git_command(["git", "checkout", "-b", branch_name], cwd=root_dir)

    # 2. Build profile subdirectories
    profile_dir.mkdir(parents=True, exist_ok=True)
    memories_dir = profile_dir / "memories"
    memories_dir.mkdir(parents=True, exist_ok=True)

    # 3. Copy blueprint SOUL.md or write a fallback
    profile_soul = profile_dir / "SOUL.md"
    if template_soul.exists():
        print(f"[*] Copying blueprint persona from '{template_folder}/SOUL.md'...")
        shutil.copy(template_soul, profile_soul)
    else:
        print(f"[!] Warning: '{template_soul}' not found. Generating basic SOUL.md.")
        soul_md_content = f"""# Hermes Agent Persona for {name}
You are {name}'s dedicated AI Technical Partner ({role}) at Startup Teams.
Directives:
- Provide direct, pragmatically sharp, and runnable code or commands.
- Record environment discoveries and conventions into `memories/MEMORY.md`.
"""
        profile_soul.write_text(soul_md_content, encoding="utf-8")

    # 4. Write profile config.yaml
    profile_config_content = f"""# Profile Configuration for {name}
agent:
  name: "{name.title()} - {role} Bot"

telegram:
  enabled: true
  bot_token: "{bot_token_val}"
  bot_token_env: {env_token_key}
  allowed_chat_id: {chat_id if chat_id else 0}
  dm_policy: open
  telegram_allowed_users: {chat_id if chat_id else 0}

onboarding:
  seen:
    profile_build_offered: true

model:
  provider: openrouter
  default: openrouter/free
  max_tokens: 8192

providers:
  openrouter:
    api: https://openrouter.ai/api/v1/chat/completions
    key_env: OPENROUTER_API_KEY
"""
    config_file = profile_dir / "config.yaml"
    config_file.write_text(profile_config_content, encoding="utf-8")
    print(f"[+] Created: {config_file.relative_to(root_dir)}")

    # 5. Write personalized USER.md
    user_md_content = f"""# User Profile: {name}

- **Name:** {name}
- **Role:** {role}
- **Organization:** Startup Teams
- **Preferences:**
  - Concise, structured technical answers.
  - Actionable CLI and development commands.
  - Provide root-cause explanations for technical issues.
"""
    user_file = memories_dir / "USER.md"
    user_file.write_text(user_md_content, encoding="utf-8")
    print(f"[+] Created: {user_file.relative_to(root_dir)}")

    # 6. Write personalized MEMORY.md
    memory_md_content = f"""# Working Memory for {name}

- **Branch:** `{branch_name if create_branch else 'main'}`
- **Active Role:** {role}
"""
    mem_file = memories_dir / "MEMORY.md"
    mem_file.write_text(memory_md_content, encoding="utf-8")
    print(f"[+] Created: {mem_file.relative_to(root_dir)}")

    # 7. Commit & push branch to GitHub
    if create_branch:
        print(f"[*] Staging and committing profile files to '{branch_name}'...")
        run_git_command(["git", "add", f"profiles/{name_clean}"], cwd=root_dir)
        run_git_command(["git", "commit", "-m", f"feat(profile): initialize agent environment for {name_clean}"], cwd=root_dir)

        if push_remote:
            print(f"[*] Pushing branch '{branch_name}' to GitHub...")
            push_res = run_git_command(["git", "push", "-u", "origin", branch_name], cwd=root_dir)
            if push_res is not None:
                print(f"[+] Successfully published '{branch_name}' to GitHub remote.")

    print(f"\n[+] Successfully onboarded {name} into profiles/{name_clean}/ on branch '{branch_name}'")
    print(f"    Run agent using: python main.py --profile {name_clean}\n")


def main():
    parser = argparse.ArgumentParser(description="Initialize isolated Hermes AI Agent Profile for an Employee")
    parser.add_argument("--name", required=True, help="Employee name (e.g. biraj, robin)")
    parser.add_argument("--role", default="Software Engineer", help="Human-readable role description (e.g. 'AI/ML Intern')")
    parser.add_argument("--chat-id", default="", help="Telegram numeric Chat ID")
    parser.add_argument(
        "--template", 
        default="fullstack", 
        help=f"Template key/alias ({', '.join(TEMPLATE_MAP.keys())}) or folder name"
    )
    parser.add_argument("--no-branch", action="store_true", help="Do not create git branch")
    parser.add_argument("--no-push", action="store_true", help="Do not push branch to GitHub automatically")

    args = parser.parse_args()
    root_dir = Path(__file__).resolve().parent

    template_folder = TEMPLATE_MAP.get(args.template.lower(), args.template)

    init_employee(
        name=args.name,
        role=args.role,
        chat_id=args.chat_id,
        template_folder=template_folder,
        root_dir=root_dir,
        create_branch=not args.no_branch,
        push_remote=not args.no_push
    )


if __name__ == "__main__":
    main()