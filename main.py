#!/usr/bin/env python3
"""
Hermes AI Agent - Native Gateway Runner
Boots the Hermes Gateway service for a specific employee profile directory.
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path
from dotenv import load_dotenv


# Explicitly load environment variables from /opt/hermes/.env
load_dotenv("/opt/hermes/.env")

env = os.environ.copy()

def main():
    parser = argparse.ArgumentParser(description="Run an isolated employee Hermes Gateway instance.")
    parser.add_argument("--profile", required=True, help="Name of the employee profile folder (e.g., robin, dave)")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    profile_dir = root_dir / "profiles" / args.profile

    if not profile_dir.exists():
        print(f"[Error] Profile directory '{profile_dir}' does not exist!", file=sys.stderr)
        sys.exit(1)

    profile_config = profile_dir / "config.yaml"
    if not profile_config.exists():
        print(f"[Error] Missing config.yaml in profile '{args.profile}'", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Launching Hermes Gateway for profile: [{args.profile}]...")

    # Map telegram token explicitly
    profile_token_key = f"TELEGRAM_BOT_TOKEN_{args.profile.upper()}"
    if profile_token_key in env:
        env["TELEGRAM_BOT_TOKEN"] = env[profile_token_key]

    
    # Execute native Hermes Gateway targeting the profile configuration
    cmd = [
    	"/opt/hermes/.venv/bin/hermes", "gateway", "run",
     	"--profile", args.profile
    ]

    try:
        # Hand off process execution to the gateway daemon
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print(f"\n[*] Shutting down Gateway for [{args.profile}] gracefully.")
    except subprocess.CalledProcessError as e:
        print(f"[Error] Hermes Gateway exited with code {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)

if __name__ == "__main__":
    main()
