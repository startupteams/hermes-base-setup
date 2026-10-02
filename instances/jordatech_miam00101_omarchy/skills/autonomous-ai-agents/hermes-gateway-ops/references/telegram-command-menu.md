# Telegram command-menu internals (verified 2026-10-02, hermes-agent repo)

Session evidence from `~/.hermes/hermes-agent/` (agent-local install; line numbers valid
as of that checkout). Proven by running the real code path with the profile's
`HERMES_HOME` — not by reading alone.

## Code line map — `hermes_cli/commands.py`

| Lines | What |
|---|---|
| 595 | `_telegram_command_menu_config()` — normalizes `platforms.telegram.extra.command_menu`; reads via `read_raw_config()` → `get_hermes_home()/config.yaml` |
| 611–616 | `max_commands` clamp: 1..100, default `_DEFAULT_TELEGRAM_MENU_MAX_COMMANDS` (60) |
| 618–620 | `priority_mode` ∈ {prepend, append, replace}, default prepend |
| 622–626 | `priority` must be a YAML LIST — dicts silently become `[]` |
| 651 | `_telegram_effective_priority()` — prepend: configured + defaults; append: defaults + configured; replace: configured only; all deduped/sanitized |
| 666 | `_prioritize_telegram_menu_commands()` — stable sort applied to CORE commands |
| 703 | `_sanitize_telegram_name()` — lowercase, hyphen→underscore, strip invalid (Telegram Bot API constraint) |
| 764 | `_collect_gateway_skill_entries()` — Tier 1 plugins (priority-irrelevant here), Tier 2 skills |
| 848–868 | skill filter chain: `SKILLS_DIR` + `skills.external_dirs` prefixes, `.hub` excluded, per-platform disabled excluded |
| 876–880 | **Skills fill remaining slots alphabetically, trimmed at cap — the ONLY trimmed tier** |
| 906 | priority reorder applied HERE only: `_prioritize_telegram_menu_commands(list(telegram_bot_commands()))` |

Menu composition: `core_commands` (52 typical) + plugin commands + skill commands (71
typical) → alphabetical fill until `max_commands`, then trim.

## Why priority can't hoist a skill

`_prioritize_telegram_menu_commands()` is called exactly once (line 906), on
`telegram_bot_commands()` output = core `COMMAND_REGISTRY` entries. The skill tier is
appended later, alphabetically, and trimmed. Upstream tests
(`tests/hermes_cli/test_commands.py` ~1160+) exercise priority with a PLUGIN command
(`lcm` via `ctx.register_command`) — plugin commands land in `COMMAND_REGISTRY` and get
true priority treatment; skills never do. `cli-config.yaml.example` (~line 776) likewise
documents `priority: [my_plugin_command]`.

## Measured (profile agent_stea004_entrepreneur)

- Core commands: 52. Skill commands: 71 (incl. `/claude-code`, `/claude-code-orchestration`).
- `/claude-code` is the 9th skill alphabetically (after acms-project-framework,
  acms-project-operations, agent-manager-vm114, armory, axolotl, baoyu-comic,
  business-idea-systems, caveman).
- cap=60 → menu 60, `claude_code` ABSENT (8 skill slots consumed by the first 8 skills).
- cap=61 → `claude_code` present at index 60 (last). cap 62–70 → same position (still the
  only new entry; next skill would need further slots).
- With `priority: [claude-code]`, priority_mode=prepend: `_telegram_effective_priority()`
  head = `('claude_code', 'help', 'new', 'stop')` — config parses and resolves fine; the
  menu still omits the entry (tier mechanism, not a config error).

## Adapter registration

`plugins/platforms/telegram/adapter.py` (~2759–2779): builds `BotCommand` list from
`telegram_menu_commands(max_commands=telegram_menu_max_commands())` and registers against
scopes Default / AllPrivateChats / AllGroupChats. Runs at gateway start — menu changes
require a gateway restart after config+probe pass.

## Working recipes

Surface a skill command:
- `max_commands: 61` (or higher) → enters at the bottom alphabetically; Telegram allows
  up to 100.
- Wrap as a plugin command → real priority treatment → can sit at the top.

Config block (both modes use `platforms.telegram.extra.command_menu`):

```yaml
platforms:
  telegram:
    extra:
      command_menu:
        max_commands: 61        # 100 = Telegram hard max
        priority_mode: prepend  # prepend | append | replace
        priority:
          - claude-code         # effective for core/plugin commands only
```

## Non-obvious facts

- The existing top-level `telegram:` key and `platforms.telegram:` are SEPARATE YAML
  keys; adding the platforms block is not a merge into the telegram block.
- `display.platforms.telegram.*` (nested under display) is yet another key — hence the
  `^platforms:` anchored existence check.
- The gateway unit carries `HERMES_HOME=<profile>` → profile config is authoritative for
  the running gateway; `~/.hermes/config.yaml` edits are inert for it.
- In-gateway restart block: `tools/terminal_tool.py` ~2237 blocks on the command STRING
  (`_contains_gateway_lifecycle_command`, `hermes_cli/cron.py` ~24 regex) — detached
  wrappers included. Restart = user `/restart` or external
  `systemctl --user restart hermes-gateway-<profile>.service`.
