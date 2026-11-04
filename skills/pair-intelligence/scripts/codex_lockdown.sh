# shellcheck shell=bash
# Sourced by pair.sh and codex_review.sh: the Codex features a second-opinion
# run must not have.
#
# --ignore-user-config drops the user's MCP servers and plugins from config.toml,
# but these features are on by default without any config (codex-cli 0.165,
# `codex features list`). Measured 2026-11-04: with --ignore-user-config alone, a
# read-only consult listed the account's ChatGPT app connectors
# (list_mcp_resources -> server "codex_apps"), which act through the user's
# account outside the sandbox; with these off, it listed none. Browser and
# computer use drive a real browser or desktop, hooks run local commands, and a
# reviewer needs no image generation or plugin installs.
#
# -c features.<name>=false rather than --disable <name>: a name a later Codex
# drops is then an unknown config key, not an unknown flag.
CODEX_LOCKDOWN=()
for _feature in apps plugins remote_plugin plugin_sharing browser_use browser_use_external \
    browser_use_full_cdp_access computer_use in_app_browser in_app_local_automation hooks \
    image_generation skill_mcp_dependency_install tool_suggest; do
  CODEX_LOCKDOWN+=(-c "features.$_feature=false")
done
unset _feature
