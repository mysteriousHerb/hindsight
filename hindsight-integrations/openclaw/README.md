# Hindsight Memory Plugin for OpenClaw

Biomimetic long-term memory for [OpenClaw](https://openclaw.ai) using [Hindsight](https://vectorize.io/hindsight). Automatically captures conversations and intelligently recalls relevant context.

## Quick Start

```bash
# 1. Configure your LLM provider for memory extraction
# Option A: OpenAI
export OPENAI_API_KEY="sk-your-key"

# Option B: Claude Code (no API key needed)
export HINDSIGHT_API_LLM_PROVIDER=claude-code

# Option C: OpenAI Codex (no API key needed)
export HINDSIGHT_API_LLM_PROVIDER=openai-codex

# 2. Install and enable the plugin
openclaw plugins install @vectorize-io/hindsight-openclaw

# 3. Start OpenClaw
openclaw gateway
```

That's it! The plugin will automatically start capturing and recalling memories.

## Features

- **Auto-capture** and **auto-recall** of memories each turn
- **Memory isolation** — configurable per agent, channel, user, or provider via `dynamicBankGranularity`
- **Retention controls** — choose which message roles to retain and toggle auto-retain on/off

## Configuration

Optional settings in `~/.openclaw/openclaw.json` under `plugins.entries.hindsight-openclaw.config`:

| Option | Default | Description |
|--------|---------|-------------|
| `apiPort` | `9077` | Port for the local Hindsight daemon |
| `daemonIdleTimeout` | `0` | Seconds before daemon shuts down from inactivity (0 = never) |
| `embedVersion` | `"latest"` | hindsight-embed version |
| `bankMission` | — | Agent identity/purpose stored on the memory bank. Helps the engine understand context for better fact extraction. Set once per bank — not a recall prompt. |
| `dynamicBankId` | `true` | Enable per-context memory banks |
| `bankIdPrefix` | — | Prefix for bank IDs (e.g. `"prod"`) |
| `dynamicBankGranularity` | `["agent", "channel", "user"]` | Fields used to derive bank ID. Options: `agent`, `channel`, `user`, `provider` |
| `excludeProviders` | `[]` | Message providers to skip for recall/retain (e.g. `slack`, `telegram`, `discord`) |
| `autoRecall` | `true` | Auto-inject memories before each turn. Set to `false` when the agent has its own recall tool. |
| `autoRetain` | `true` | Auto-retain conversations after each turn |
| `retainRoles` | `["user", "assistant"]` | Which message roles to retain. Options: `user`, `assistant`, `system`, `tool` |
| `recallBudget` | `"mid"` | Recall effort: `low`, `mid`, or `high`. Higher budgets use more retrieval strategies. |
| `recallMaxTokens` | `2048` | Max tokens for recall response. Controls how much memory context is injected per turn. |
| `recallTypes` | `["world", "experience"]` | Memory types to recall. Options: `world`, `experience`, `observation`. Excludes verbose `observation` entries by default. |
| `recallTopK` | — | Max number of memories to inject per turn. Applied after API response as a hard cap. |
| `hindsightApiUrl` | — | External Hindsight API URL (skips local daemon) |
| `hindsightApiToken` | — | Auth token for external API |

## Documentation

For full documentation, configuration options, troubleshooting, and development guide, see:

**[OpenClaw Integration Documentation](https://vectorize.io/hindsight/sdks/integrations/openclaw)**

## Development

To test local changes to the Hindsight package before publishing:

1. Add `embedPackagePath` to your plugin config in `~/.openclaw/openclaw.json`:
```json
{
  "plugins": {
    "entries": {
      "hindsight-openclaw": {
        "enabled": true,
        "config": {
          "embedPackagePath": "/path/to/hindsight-wt3/hindsight-embed"
        }
      }
    }
  }
}
```

2. The plugin will use `uv run --directory <path> hindsight-embed` instead of `uvx hindsight-embed@latest`

3. To use a specific profile for testing:
```bash
# Check daemon status
uvx hindsight-embed@latest -p openclaw daemon status

# View logs
tail -f ~/.hindsight/profiles/openclaw.log

# List profiles
uvx hindsight-embed@latest profile list
```

## Links

- [Hindsight Documentation](https://vectorize.io/hindsight)
- [OpenClaw Documentation](https://openclaw.ai)
- [GitHub Repository](https://github.com/vectorize-io/hindsight)

## License

MIT
