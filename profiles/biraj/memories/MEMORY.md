User manages profiles under /opt/hermes with git remotes to startupteams repos (hermes-base-setup); uses system-level cron for sync_memory.sh; interested in pulling skills from agent_stea004_entrepreneur profile (jordatech_crmmiam02_906 branch) into biraj profile.
§
User directs: profile-config tasks → use profile skills (/opt/hermes/profiles/biraj/skills/). Non-profile / general tasks → use global skills (/opt/hermes/skills/) plus the agent's own skillset. Both storage locations are active; choose based on task domain.
§
Skill update 2026-09-14: patched profile cron-management (devops) with LLAP/Proxmox access, system-vs-Hermes cron pitfall, two-skills-storage check. Overlap with global proxmox-cluster-infrastructure.
§
User operates in profile-configuration context with preference for global skills (not profile-specific). System-level cron jobs preferred over Hermes-managed cron jobs. Skills folder at /opt/hermes/skills/ is primary reference. Prefers minimal intervention - only disable/pause broken jobs rather than remove entirely. Values verification of system state before making changes.