---
name: hermes-gateway-ops
description: "Operate Hermes gateway platform integrations: config propagation (the running gateway reads the PROFILE config via HERMES_HOME, not ~/.hermes/config.yaml), Telegram command-menu mechanics (priority reorders core/plugin commands only; skills are alphabetical Tier-2 trimmed at the cap), nested-list config-edit workflow (hermes config set cannot grow lists; patch tool refuses Hermes configs), in-gateway restart hard-block + external restart paths, and the no-restart E2E menu verification probe. Load for 'add X to the Telegram command menu', gateway config edits that 'didn't take effect', or any platforms.* change."
version: 1.0.0
author: Hermes Agent (agent-created, STEA-004)
license: MIT
metadata:
  hermes:
    tags: [hermes-agent, gateway, telegram, command-menu, config, restart, verification]
---

# Hermes Gateway Platform Operations

## Why this exists

The bundled `hermes-agent` skill covers gateway install/start/status basics. This skill
holds the operational mechanics discovered while actually changing platform behavior:
where the running gateway really reads config from, why a correct-looking config edit
"doesn't take", what the Telegram command menu can and cannot express, and how to verify
menu changes without burning a restart cycle.

## When to Use

- "Add X to the Telegram command menu" / menu tuning (priority, cap)
- A gateway config change appeared correct but had no effect
- Gateway restart requested from inside a gateway session
- Any `platforms.<platform>.*` setting change

## Config propagation: PROFILE, not main (CRITICAL)

The gateway systemd unit runs with `HERMES_HOME=<profile dir>`:

```
systemctl --user cat hermes-gateway-<profile>.service
→ Environment="HERMES_HOME=/home/jordatech/.hermes/profiles/<profile>"
```

Platform config (`platforms.telegram.extra.*`, etc.) is read via
`get_hermes_home()/config.yaml` — the **PROFILE** config. Editing `~/.hermes/config.yaml`
alone changes nothing for the running gateway. Editing both files is only useful when the
change should survive profile re-clones; for the live gateway the profile file is
authoritative.

## Config edits: sanctioned paths and their limits

- The `patch`/`write_file` tools **hard-refuse Hermes config.yaml paths** ("security-
  sensitive configuration") — no override flag.
- `hermes config set` supports dotted keys but **cannot grow YAML lists**: `_set_nested`
  requires list indices to already exist; a numeric path on a missing list silently
  writes a dict that list-reading code ignores via `isinstance(list)` checks.
- Nested-LIST config (e.g. `command_menu.priority: [...]`) therefore requires a direct
  file edit. Working path (needs EXPLICIT user consent — the approval system blocks
  scripted writes otherwise): backup → line-anchored asserts → write → YAML verify →
  deep-compare vs backup. Full recipe lives in the `file-write-verification` skill.

## Telegram command menu mechanics (summary)

Menu composition: core commands (from `COMMAND_REGISTRY`, priority-reorderable) + plugin
commands (priority-reorderable) + skill commands (**alphabetical Tier-2, trimmed at the
cap — never reordered**). Code line map, cap measurements, and working alternatives:
`references/telegram-command-menu.md`.

- Default cap 60 (Telegram Bot API allows 100). Typical profile: ~52 core commands →
  only 8 skill slots; everything else hidden.
- `command_menu.priority` affecting a **skill** name is a silent no-op — priority only
  reaches the core/plugin tiers.
- To surface a skill command: raise `max_commands` (it enters alphabetically at the
  bottom), or wrap it as a **plugin command** (plugin tier gets real priority treatment —
  this is what upstream tests cover).
- Names are sanitized for Telegram: hyphen→underscore (`claude-code` → `claude_code`);
  supply raw names in config, the pipeline handles them.

## E2E verification probe (no restart needed)

Build the menu exactly as the adapter will, with the profile's `HERMES_HOME`:

```bash
V=~/.hermes/hermes-agent/venv/bin/python
HERMES_HOME=~/.hermes/profiles/<profile> $V -c "
from hermes_cli.commands import telegram_menu_commands, _telegram_effective_priority
print('priority head:', _telegram_effective_priority()[:4])
menu, hidden = telegram_menu_commands(max_commands=60)
names = [n for n, _ in menu]
print('menu:', len(menu), 'hidden:', hidden, '| claude_code in menu:', 'claude_code' in names)"
```

If the probe doesn't show the entry, a restart will not fix it — fix the mechanism first.
This probe caught exactly that in 2026-10-02: config valid, priority resolved, entry
still absent (tier mechanism, not a config error).

## Restart procedures

- The gateway **cannot restart itself**: `tools/terminal_tool.py` (~line 2237) hard-blocks
  gateway lifecycle commands when `_HERMES_GATEWAY=1`, matching the command STRING — even
  detached `systemd-run` wrappers are refused pre-execution.
- Correct paths: the user sends `/restart` in chat, or an external shell runs
  `systemctl --user restart hermes-gateway-<profile>.service`.
- Menu/platform config is read at gateway start — restart AFTER the config edit and the
  probe, not before.

## Pitfalls

- Top-level key existence checks must be line-anchored: `re.search(r'^platforms:', text,
  re.M)`. Substring checks false-positive on nested keys (`display.platforms:`).
- Never hardcode `_config_version` (or other per-file values) in post-write assertions —
  main config and profile config sit at different versions; compare against the backup.
- `hermes config set platform.x.y.0 value` on a fresh list SUCCEEDS while writing the
  wrong shape (dict) — always re-read the file after any `config set` on nested paths.
- Restarting before probing wastes a restart cycle and can mask the real (tier-level)
  cause.

## Related

- `file-write-verification` — the general write/verify discipline this skill's config-edit
  workflow builds on.
- `debugging-hermes-tui-commands` — TUI slash-command debugging; overlaps on the fact that
  `COMMAND_REGISTRY` feeds the Telegram menu.
- `telegram-send-file` — delivering handoff documents over Telegram (Bot API path).
